"""
ETL pipeline for CrossFit workouts.

Commands:
    uv run python etl.py fetch [--max-pages N]     # fetch raw posts to data/raw/
    uv run python etl.py build                     # parse raw posts -> canonical + aggregates
    uv run python etl.py all                       # fetch + build
"""

import argparse
import time
from typing import Dict

from cfa_etl.aggregates import aggregate
from cfa_etl.canonical import build_canonical
from cfa_etl.comments import fetch_all_comments
from cfa_etl.comments_analysis import build_comments_analysis
from cfa_etl.io import fetch_comment_counts, fetch_raw, load_raw_posts, write_artifacts
from cfa_etl.movements import (
    component_tag,
    detect_format,
    extract_rep_scheme,
    is_rest_day,
    is_workout_component,
    load_movement_patterns,
    movement_text_from_components,
    tag_movements,
)
from cfa_etl.named_workouts import build_named_workouts


def _build_with_comment_analysis(raw: list[dict]) -> None:
    print("[etl] Fetching comments (metadata-only) for analytics…")
    comments = list(fetch_all_comments(pause=0.0, include_content=False, log_progress=True, log_every_pages=25))
    print(f"[etl] Fetched {len(comments)} comments; aggregating…")
    counts: Dict[int, int] = {}
    for c in comments:
        pid = c.get("post_id")
        if not pid:
            continue
        pid_int = int(pid)
        counts[pid_int] = counts.get(pid_int, 0) + 1
    print(f"[etl] Building canonical for {len(raw)} posts…")
    canonical = build_canonical(raw, counts)
    print("[etl] Building aggregates…")
    aggregates = aggregate(canonical)
    print("[etl] Building comment analysis…")
    comments_analysis = build_comments_analysis(canonical, comments)
    print("[etl] Writing artifacts…")
    write_artifacts(canonical, aggregates, comments_analysis=comments_analysis)


def cmd_fetch(args: argparse.Namespace) -> None:
    fetch_raw(max_pages=args.max_pages)


def cmd_build(_: argparse.Namespace) -> None:
    raw = list(load_raw_posts())
    if getattr(_, "with_comment_analysis", False):
        _build_with_comment_analysis(raw)
        return

    comment_counts: Dict[int, int] | None = None
    if getattr(_, "with_comments", False):
        comment_counts = fetch_comment_counts(raw)
    canonical = build_canonical(raw, comment_counts)
    aggregates = aggregate(canonical)
    write_artifacts(canonical, aggregates)


def cmd_all(args: argparse.Namespace) -> None:
    raw_path = fetch_raw(max_pages=args.max_pages)
    time.sleep(0.1)
    raw = list(load_raw_posts())
    if getattr(args, "with_comment_analysis", False):
        _build_with_comment_analysis(raw)
        return

    comment_counts: Dict[int, int] | None = None
    if getattr(args, "with_comments", False):
        comment_counts = fetch_comment_counts(raw)
    canonical = build_canonical(raw, comment_counts)
    aggregates = aggregate(canonical)
    write_artifacts(canonical, aggregates)


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL for CFSBK workouts.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fetch = sub.add_parser("fetch", help="Fetch raw posts to data/raw.")
    p_fetch.add_argument("--max-pages", type=int, default=None, help="Limit pages (testing).")
    p_fetch.set_defaults(func=cmd_fetch)

    p_build = sub.add_parser("build", help="Build canonical + aggregates from latest raw.")
    p_build.add_argument("--with-comments", action="store_true", help="Fetch comment counts (hits API).")
    p_build.add_argument(
        "--with-comment-analysis",
        action="store_true",
        help="Fetch full comments and write comments_analysis.json (hits API).",
    )
    p_build.set_defaults(func=cmd_build)

    p_all = sub.add_parser("all", help="Fetch then build.")
    p_all.add_argument("--max-pages", type=int, default=None, help="Limit pages (testing).")
    p_all.add_argument("--with-comments", action="store_true", help="Fetch comment counts (hits API).")
    p_all.add_argument(
        "--with-comment-analysis",
        action="store_true",
        help="Fetch full comments and write comments_analysis.json (hits API).",
    )
    p_all.set_defaults(func=cmd_all)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
