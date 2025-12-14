from __future__ import annotations

import time
from typing import Dict, Iterable, List, Optional

import requests

from .paths import COMMENTS_API


def fetch_all_comments(
    *,
    per_page: int = 100,
    max_pages: int | None = None,
    pause: float = 0.0,
    session: Optional[requests.Session] = None,
) -> Iterable[Dict]:
    """
    Fetch all comments across the site via the WP v2 comments API.

    Notes:
    - Uses pagination headers (X-WP-TotalPages) when present.
    - Requests minimal fields by normalizing output.
    """
    sess = session or requests.Session()

    page = 1
    total_pages: int | None = None
    while True:
        resp = sess.get(
            COMMENTS_API,
            params={
                "per_page": per_page,
                "page": page,
                "order": "asc",
                "orderby": "date",
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch comments page={page}: {resp.status_code}")

        if total_pages is None:
            try:
                total_pages = int(resp.headers.get("X-WP-TotalPages", "0")) or None
            except Exception:
                total_pages = None

        data = resp.json() or []
        if not data:
            break

        for item in data:
            yield normalize_comment(item)

        page += 1
        if max_pages is not None and page > max_pages:
            break
        if total_pages is not None and page > total_pages:
            break
        if pause:
            time.sleep(pause)


def normalize_comment(raw: Dict) -> Dict:
    content = raw.get("content") or {}
    rendered = content.get("rendered") or ""
    return {
        "id": raw.get("id"),
        "post_id": raw.get("post"),
        "date": (raw.get("date") or "")[:10],
        "author_name": raw.get("author_name") or "Anonymous",
        "content_html": rendered,
    }

