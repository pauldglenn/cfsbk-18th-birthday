from __future__ import annotations

import time
from typing import Dict, Iterable, List, Optional

import requests

from .paths import COMMENTS_API

DEFAULT_HEADERS = {
    # WP Engine blocks the default python-requests UA on some endpoints.
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain;q=0.9,*/*;q=0.8",
}


def fetch_all_comments(
    *,
    per_page: int = 100,
    max_pages: int | None = None,
    pause: float = 0.0,
    include_content: bool = True,
    log_progress: bool = False,
    log_every_pages: int = 25,
    session: Optional[requests.Session] = None,
) -> Iterable[Dict]:
    """
    Fetch all comments across the site via the WP v2 comments API.

    Notes:
    - Uses pagination headers (X-WP-TotalPages) when present.
    - Requests minimal fields by normalizing output.
    """
    sess = session or requests.Session()
    sess.headers.update(DEFAULT_HEADERS)

    page = 1
    total_pages: int | None = None
    fetched = 0
    started = time.monotonic()
    if log_progress:
        mode = "full" if include_content else "metadata-only"
        print(f"[comments] Fetching {mode} comments via WP API (per_page={per_page})…")
    while True:
        params = {
            "per_page": per_page,
            "page": page,
            "order": "asc",
            "orderby": "date",
        }
        if not include_content:
            params["_fields"] = "id,post,date,author_name"
        resp = sess.get(
            COMMENTS_API,
            params=params,
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
            fetched += 1
            yield normalize_comment(item, include_content=include_content)

        if log_progress and (page == 1 or page % max(log_every_pages, 1) == 0):
            elapsed = max(time.monotonic() - started, 0.001)
            rate = fetched / elapsed
            tp = total_pages if total_pages is not None else "?"
            print(f"[comments] page {page}/{tp} · fetched {fetched} · {rate:.1f}/s")

        page += 1
        if max_pages is not None and page > max_pages:
            break
        if total_pages is not None and page > total_pages:
            break
        if pause:
            time.sleep(pause)

    if log_progress:
        elapsed = max(time.monotonic() - started, 0.001)
        rate = fetched / elapsed
        print(f"[comments] done · fetched {fetched} in {elapsed:.1f}s · {rate:.1f}/s")


def normalize_comment(raw: Dict, *, include_content: bool = True) -> Dict:
    rendered = ""
    if include_content:
        content = raw.get("content") or {}
        rendered = content.get("rendered") or ""
    return {
        "id": raw.get("id"),
        "post_id": raw.get("post"),
        "date": (raw.get("date") or "")[:10],
        "author_name": raw.get("author_name") or "Anonymous",
        "content_html": rendered,
    }
