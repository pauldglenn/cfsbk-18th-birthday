from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Tuple

from .movements import extract_rep_scheme


def build_comments_analysis(canonical: List[Dict], comments: Iterable[Dict]) -> Dict:
    posts_by_id: Dict[int, Dict] = {}
    for item in canonical:
        pid = item.get("id")
        if isinstance(pid, int):
            posts_by_id[pid] = item

    comment_list = [c for c in comments if c.get("post_id")]
    total_comments = len(comment_list)

    month_counts = Counter()
    post_counts = Counter()
    commenter_counts = Counter()

    for c in comment_list:
        date = c.get("date") or ""
        if date and len(date) >= 7:
            month_counts[date[:7]] += 1
        pid = c.get("post_id")
        if pid:
            post_counts[int(pid)] += 1
        author = (c.get("author_name") or "Anonymous").strip() or "Anonymous"
        commenter_counts[author] += 1

    monthly_series = build_month_series(month_counts)

    top_posts = []
    for pid, cnt in post_counts.most_common(5):
        post = posts_by_id.get(pid) or {}
        top_posts.append(
            {
                "id": pid,
                "date": post.get("date") or "",
                "title": post.get("title") or f"Post {pid}",
                "link": post.get("link") or "",
                "comment_count": cnt,
                "summary": post_summary(post),
            }
        )

    top_commenters = []
    for name, cnt in commenter_counts.most_common(20):
        top_commenters.append(
            {
                "name": name,
                "count": cnt,
            }
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total_comments": total_comments,
        "monthly": monthly_series,
        "top_posts": top_posts,
        "top_commenters": top_commenters,
    }


def build_month_series(month_counts: Counter) -> List[Dict]:
    if not month_counts:
        return []
    months_sorted = sorted(month_counts.keys())
    start_y, start_m = map(int, months_sorted[0].split("-"))
    end_y, end_m = map(int, months_sorted[-1].split("-"))

    series = []
    y, m = start_y, start_m
    while (y, m) <= (end_y, end_m):
        key = f"{y:04d}-{m:02d}"
        series.append({"month": key, "count": int(month_counts.get(key, 0))})
        m += 1
        if m == 13:
            y += 1
            m = 1
    return series


def post_summary(post: Dict) -> str:
    components = post.get("components") or []
    if components:
        summary = extract_rep_scheme(components)
        if summary:
            return summary
        first = (components[0].get("details") or "").strip()
        return " ".join(first.split())[:220]
    return ""
