from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

import requests

from scrape_cfsbk import fetch_posts

from .comments import DEFAULT_HEADERS
from .movements import extract_rep_scheme
from .named_workouts import build_named_workouts
from .paths import COMMENTS_API, DERIVED_DIR, RAW_DIR


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)


def fetch_raw(max_pages: int | None) -> Path:
    ensure_dirs()
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out_path = RAW_DIR / f"posts-{ts}.jsonl"
    total = 0
    with out_path.open("w", encoding="utf-8") as f:
        for posts in fetch_posts(max_pages=max_pages):
            for post in posts:
                json.dump(post, f, ensure_ascii=False)
                f.write("\n")
                total += 1
    print(f"Fetched {total} posts -> {out_path}")
    return out_path


def fetch_comment_counts(posts: List[Dict], pause: float = 0.05) -> Dict[int, int]:
    """
    Fetch comment counts per post via the WP comments API using X-WP-Total.
    Keeps payload small by requesting per_page=1.
    """
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    counts: Dict[int, int] = {}
    for post in posts:
        pid = post.get("id")
        if not pid:
            continue
        resp = session.get(
            COMMENTS_API,
            params={"post": pid, "per_page": 1},
            timeout=15,
        )
        if resp.status_code == 200:
            try:
                counts[pid] = int(resp.headers.get("X-WP-Total", 0))
            except Exception:
                counts[pid] = 0
        if pause:
            time.sleep(pause)
    return counts


def load_raw_posts() -> Iterable[Dict]:
    latest = RAW_DIR / "latest.jsonl"
    if latest.exists():
        path = latest
    else:
        files = sorted(RAW_DIR.glob("posts-*.jsonl"), reverse=True)
        if not files:
            raise SystemExit("No raw files found in data/raw. Run `uv run python etl.py fetch` first.")
        path = files[0]
    with path.open() as f:
        for line in f:
            yield json.loads(line)


def write_artifacts(
    canonical: List[Dict],
    aggregates: Dict[str, Dict],
    *,
    comments_analysis: Dict | None = None,
) -> None:
    ensure_dirs()
    canonical_path = DERIVED_DIR / "workouts.jsonl"
    with canonical_path.open("w", encoding="utf-8") as f:
        for item in canonical:
            json.dump(item, f, ensure_ascii=False)
            f.write("\n")

    for name, data in aggregates.items():
        out_path = DERIVED_DIR / f"{name}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    search_path = DERIVED_DIR / "search_index.json"
    search_data = [
        {
            "id": item.get("id"),
            "seq_no": item.get("seq_no"),
            "workout_no": item.get("workout_no"),
            "milestones": item.get("milestones") or [],
            "date": item.get("date"),
            "title": item.get("title"),
            "link": item.get("link"),
            "summary": extract_rep_scheme(item.get("components") or []),
            "movements": item.get("movements"),
            "component_tags": item.get("component_tags"),
            "format": item.get("format"),
            "cycle_info": item.get("cycle_info"),
        }
        for item in canonical
    ]
    with search_path.open("w", encoding="utf-8") as f:
        json.dump(search_data, f, ensure_ascii=False)

    version_path = DERIVED_DIR / "data_version.json"
    total_workouts = sum(1 for item in canonical if not item.get("is_rest_day"))
    version = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_workouts": total_workouts,
        "total_posts": len(canonical),
    }
    with version_path.open("w", encoding="utf-8") as f:
        json.dump(version, f, indent=2)

    named_path = DERIVED_DIR / "named_workouts.json"
    with named_path.open("w", encoding="utf-8") as f:
        json.dump(build_named_workouts(canonical), f, ensure_ascii=False, indent=2)

    if comments_analysis is not None:
        comments_path = DERIVED_DIR / "comments_analysis.json"
        with comments_path.open("w", encoding="utf-8") as f:
            json.dump(comments_analysis, f, ensure_ascii=False, indent=2)

    print(f"Wrote canonical -> {canonical_path}")
    print(f"Wrote aggregates -> {DERIVED_DIR}")
