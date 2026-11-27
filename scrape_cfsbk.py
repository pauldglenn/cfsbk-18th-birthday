"""
Scrape the CrossFit South Brooklyn blog for all Workout of the Day entries.

The script uses the public WordPress REST API to pull every post in the
"Workout of the Day" category, parses the rendered HTML to extract the workout
components (Strength, Assistance, Conditioning, etc.), and writes one JSON
object per line with the date, title, cycle info, and component text.
"""

import argparse
import html
import json
import re
import time
from datetime import date
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup


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


def post_title(post: Dict) -> str:
    rendered = (post.get("title") or {}).get("rendered") or ""
    return html.unescape(BeautifulSoup(rendered, "html.parser").get_text()).strip()


def parse_components(soup: BeautifulSoup) -> List[Dict]:
    """Extract today's programming from the supplied post body."""
    from cfa_etl.extraction import extract_programming, source_blocks
    from cfa_etl.movements import load_movement_patterns

    return extract_programming(source_blocks(soup), "", load_movement_patterns())[1]


def process_post(post: Dict, patterns=None, *, review: Dict | None = None) -> Dict:
    """Build a structured record for a single post."""
    from cfa_etl.extraction import extract_programming, source_blocks
    from cfa_etl.movements import load_movement_patterns
    from cfa_etl.reviews import resolve_selection, source_digest

    content_html = post.get("content", {}).get("rendered") or ""
    soup = BeautifulSoup(content_html, "html.parser")
    text_blob = soup.get_text(" ", strip=True)
    post_date = (post.get("date") or "")[:10]
    title = post_title(post)
    blocks = source_blocks(soup)
    review_matches = review is not None and review["source_digest"] == source_digest(title, blocks)
    if review_matches:
        status, components = resolve_selection(title, blocks, review)
    else:
        status, components = extract_programming(
            blocks, title, patterns if patterns is not None else load_movement_patterns()
        )
        if review is not None:
            status = "needs_review"
    return {
        "id": post.get("id"),
        "post_date": post_date,
        "date": derive_workout_date(post, post_date),
        "title": title,
        "link": post.get("link"),
        "cycle_info": extract_cycle_info(text_blob),
        "components": components,
        "extraction_status": status,
    }


def derive_workout_date(post: Dict, fallback: str) -> str:
    """
    Workouts are often posted a day in advance. Derive the intended date from
    the title/slug first, then the permalink path; otherwise fall back to publish date.
    """
    from cfa_etl.extraction import valid_date

    title = (post.get("title", {}) or {}).get("rendered") or ""
    slug = post.get("slug") or ""

    def parse_ymd(text: str) -> str | None:
        m = re.search(r"(?<!\d)(\d{1,2})[./-](\d{1,2})[./-](\d{4}|\d{2})(?!\d)", text)
        if not m:
            return None
        month, day, year = m.groups()
        if len(year) == 2:
            year_int = int(year)
            year = f"20{year.zfill(2)}" if year_int < 70 else f"19{year.zfill(2)}"
        return valid_date(f"{year}-{month.zfill(2)}-{day.zfill(2)}")

    # Prefer explicit date in title or slug (often the real workout date)
    date_from_title = parse_ymd(title) or parse_ymd(slug)
    if date_from_title and fallback and valid_date(fallback):
        skew = abs((date.fromisoformat(date_from_title) - date.fromisoformat(fallback)).days)
        if skew > 31:
            date_from_title = None
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
