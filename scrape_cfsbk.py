"""
Scrape the CrossFit South Brooklyn blog for all Workout of the Day entries.

The script uses the public WordPress REST API to pull every post in the
"Workout of the Day" category, parses the rendered HTML to extract the workout
components (Strength, Assistance, Conditioning, etc.), and writes one JSON
object per line with the date, title, cycle info, and component text.
"""

import argparse
import json
import re
import time
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

API_URL = "https://crossfitsouthbrooklyn.com/wp-json/wp/v2/posts"
CATEGORY_ID = 1  # "Workout of the Day"
DEFAULT_PER_PAGE = 100
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
)

# Examples: (WK4/8), (Week 6/8), (wk 3 / 6)
CYCLE_PATTERN = re.compile(r"\((?:wk|week)\s*\d+\s*/\s*\d+\)", re.IGNORECASE)


def clean_text(text: str) -> str:
    """Collapse whitespace inside a string."""
    return " ".join(text.split())


def fetch_posts(
    per_page: int = DEFAULT_PER_PAGE, max_pages: Optional[int] = None, pause: float = 0.2
) -> Iterable[List[Dict]]:
    """
    Yield pages of posts from the WP API.

    The API returns the total page count in X-WP-TotalPages so we stop when we
    reach the end or when max_pages is hit.
    """
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    page = 1
    total_pages: Optional[int] = None

    while True:
        if max_pages is not None and page > max_pages:
            break

        resp = session.get(
            API_URL,
            params={"categories": CATEGORY_ID, "per_page": per_page, "page": page},
            timeout=20,
        )

        # WordPress returns 400 when the page number exceeds the max
        if resp.status_code == 400 and "rest_post_invalid_page_number" in resp.text:
            break

        resp.raise_for_status()
        posts = resp.json()
        if not posts:
            break

        if total_pages is None:
            try:
                total_pages = int(resp.headers.get("X-WP-TotalPages", 0)) or None
            except (TypeError, ValueError):
                total_pages = None

        yield posts

        if total_pages is not None and page >= total_pages:
            break

        page += 1
        if pause:
            time.sleep(pause)


def extract_cycle_info(text_blob: str) -> List[str]:
    """Return unique cycle markers like '(WK4/8)' in the order they appear."""
    seen = []
    for match in CYCLE_PATTERN.findall(text_blob):
        marker = match.strip()
        if marker not in seen:
            seen.append(marker)
    return seen


def collect_component_text(start_node: Tag) -> str:
    """
    Gather text following a component heading until the next heading or <hr/>.
    """
    parts: List[str] = []
    cursor = start_node.next_sibling

    while cursor:
        if isinstance(cursor, Tag) and cursor.name in {"h2", "h3", "h4", "h5", "h6", "hr"}:
            break

        if isinstance(cursor, Tag):
            text = cursor.get_text(" ", strip=True)
        elif isinstance(cursor, NavigableString):
            text = str(cursor).strip()
        else:
            text = ""

        if text:
            parts.append(text)

        cursor = cursor.next_sibling

    return clean_text(" ".join(parts))


def parse_components(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """
    Extract workout components that follow the "Workout of the Day" heading.
    """
    wod_heading = soup.find(
        lambda tag: tag.name in {"h2", "h3"}
        and "workout of the day" in tag.get_text(" ", strip=True).lower()
    )
    if not wod_heading:
        # Fallback: older posts often omit the heading, so try to pull any
        # heading-delimited sections. If none exist, capture the whole body.
        sections: List[Dict[str, str]] = []
        for heading in soup.find_all(lambda t: t.name in {"h2", "h3", "h4", "h5", "h6"}):
            heading_text = heading.get_text(" ", strip=True)
            if not heading_text:
                continue
            details = collect_component_text(heading)
            sections.append({"component": heading_text, "details": details})

        if sections:
            return sections

        blob = clean_text(soup.get_text(" ", strip=True))
        return [{"component": "Workout", "details": blob}] if blob else []

    components: List[Dict[str, str]] = []
    node = wod_heading.next_sibling

    while node:
        if isinstance(node, Tag):
            heading_text = node.get_text(" ", strip=True)

            # Stop once we hit the next major section.
            if node.name in {"h2", "h3"} and "workout of the day" not in heading_text.lower():
                break

            if node.name in {"h3", "h4", "h5", "h6"} and heading_text:
                details = collect_component_text(node)
                components.append({"component": heading_text, "details": details})

        node = node.next_sibling

    if components:
        return components

    # If nothing was captured under the WOD heading, fallback to a single blob.
    blob = clean_text(soup.get_text(" ", strip=True))
    return [{"component": "Workout", "details": blob}] if blob else []


def process_post(post: Dict) -> Dict:
    """Build a structured record for a single post."""
    content_html = post.get("content", {}).get("rendered") or ""
    soup = BeautifulSoup(content_html, "html.parser")
    text_blob = soup.get_text(" ", strip=True)
    post_date = (post.get("date") or "")[:10]

    return {
        "id": post.get("id"),
        "post_date": post_date,
        "date": derive_workout_date(post, post_date),
        "title": post.get("title", {}).get("rendered"),
        "link": post.get("link"),
        "cycle_info": extract_cycle_info(text_blob),
        "components": parse_components(soup),
    }


def derive_workout_date(post: Dict, fallback: str) -> str:
    """
    Workouts are often posted a day in advance. Derive the intended date from
    the title/slug first, then the permalink path; otherwise fall back to publish date.
    """
    title = (post.get("title", {}) or {}).get("rendered") or ""
    slug = post.get("slug") or ""

    def parse_ymd(text: str) -> str | None:
        m = re.search(r"(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})", text)
        if not m:
            return None
        month, day, year = m.groups()
        if len(year) == 2:
            year_int = int(year)
            year = f"20{year.zfill(2)}" if year_int < 70 else f"19{year.zfill(2)}"
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # Prefer explicit date in title or slug (often the real workout date)
    date_from_title = parse_ymd(title) or parse_ymd(slug)
    # If the parsed year is in the future relative to publish date, treat it as a typo and fall back
    # Also, if parsed year is before 2007, fall back to publish year (likely an abbreviated year typo).
    if date_from_title and fallback:
        try:
            pub_year = int(fallback[:4])
            parsed_year = int(date_from_title[:4])
            if parsed_year - pub_year > 2 or parsed_year < 2007:
                date_from_title = None
        except Exception:
            pass
    if date_from_title:
        return date_from_title

    link = post.get("link") or ""
    m = re.search(r"/(20\d{2})/(\d{2})/(\d{2})/", link)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    return fallback


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape CFSBK workouts via the WP API.")
    parser.add_argument(
        "--output",
        default="workouts.jsonl",
        help="Path to write newline-delimited JSON records.",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=DEFAULT_PER_PAGE,
        help="How many posts to fetch per API page (max 100).",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Optional limit for number of API pages to fetch (for quick tests).",
    )
    parser.add_argument(
        "--pause",
        type=float,
        default=0.2,
        help="Seconds to sleep between page requests to be polite.",
    )
    args = parser.parse_args()

    total_posts = 0
    with open(args.output, "w", encoding="utf-8") as f:
        for posts in fetch_posts(per_page=args.per_page, max_pages=args.max_pages, pause=args.pause):
            for post in posts:
                record = process_post(post)
                json.dump(record, f, ensure_ascii=False)
                f.write("\n")
                total_posts += 1

    print(f"Saved {total_posts} workouts to {args.output}")


if __name__ == "__main__":
    main()
