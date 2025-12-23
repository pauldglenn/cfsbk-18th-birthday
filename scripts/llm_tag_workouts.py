#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from bs4 import BeautifulSoup
import requests

# Ensure project root on path for module imports when running as a script.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cfa_etl.llm_tagging import (
    LLMTaggingConfig,
    load_dotenv,
    load_canonical_movement_labels,
    _validate_llm_result,
    judge_post_tags_with_llm,
    tag_post_with_llm,
)
from scrape_cfsbk import derive_workout_date


def _post_text(post: Dict[str, Any]) -> str:
    content_html = (post.get("content") or {}).get("rendered") or ""
    soup = BeautifulSoup(content_html, "html.parser")
    # Keep it close to our existing extractor: plain text, compact whitespace.
    text = soup.get_text("\n", strip=True)
    text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return text


def _should_include(date: str, start: Optional[str], end: Optional[str]) -> bool:
    if start and date < start:
        return False
    if end and date > end:
        return False
    return True


def _load_search_index(path: Path) -> Dict[int, Dict[str, Any]]:
    if not path.exists():
        raise SystemExit(f"Missing regex baseline index: {path}. Run `uv run python etl.py build` first.")
    items = json.loads(path.read_text(encoding="utf-8"))
    by_id: Dict[int, Dict[str, Any]] = {}
    for item in items:
        pid = item.get("id")
        if isinstance(pid, int):
            by_id[pid] = item
    return by_id


def _regex_payload_from_search_item(item: Dict[str, Any]) -> Dict[str, Any]:
    # Convert our regex-derived search_index entry into the LLM schema, so the judge can
    # reason over it consistently (even though regex doesn't provide component details).
    workout_no = item.get("workout_no")
    return {
        "id": item.get("id"),
        "date": item.get("date"),
        "title": item.get("title") or "",
        "link": item.get("link") or "",
        "is_rest_day": workout_no is None,
        "components": [],
        "component_tags": item.get("component_tags") or [],
        "format": item.get("format") or "",
        "movements": item.get("movements") or [],
        "unmapped_movements": [],
        "notes": "Regex baseline (components not available in search_index).",
    }


def _should_judge(*, regex_payload: Dict[str, Any], llm_payload: Dict[str, Any]) -> bool:
    if bool(regex_payload.get("is_rest_day")) != bool(llm_payload.get("is_rest_day")):
        return True
    if (regex_payload.get("format") or "") != (llm_payload.get("format") or ""):
        return True
    if set(regex_payload.get("movements") or []) != set(llm_payload.get("movements") or []):
        return True
    if set(regex_payload.get("component_tags") or []) != set(llm_payload.get("component_tags") or []):
        return True
    if (llm_payload.get("unmapped_movements") or []):
        return True
    return False


def _read_seen_ids(path: Path) -> Set[int]:
    seen: Set[int] = set()
    if not path.exists():
        return seen
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                pid = obj.get("id")
                if isinstance(pid, int):
                    seen.add(pid)
            except Exception:
                continue
    return seen


def _append_jsonl(path: Path, obj: Dict[str, Any], lock: threading.Lock) -> None:
    with lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False)
            f.write("\n")


def _read_seen_ids_from_json_array(path: Path) -> Set[int]:
    """
    Read ids from a JSON array file like data/derived/llm_tags.json.
    (Used in GitHub Actions where we commit the .json array but not the .jsonl.)
    """
    seen: Set[int] = set()
    if not path.exists():
        return seen
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return seen
        for obj in data:
            if isinstance(obj, dict):
                pid = obj.get("id")
                if isinstance(pid, int):
                    seen.add(pid)
    except Exception:
        return seen
    return seen


def _ensure_jsonl_from_json_array(json_path: Path, jsonl_path: Path) -> None:
    """
    If only the JSON array exists (committed), reconstruct a local jsonl so we can:
    - efficiently append new records
    - regenerate the JSON array at the end from a single source of truth
    """
    if jsonl_path.exists() or not json_path.exists():
        return
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with jsonl_path.open("w", encoding="utf-8") as f:
            for obj in data:
                if not isinstance(obj, dict):
                    continue
                json.dump(obj, f, ensure_ascii=False)
                f.write("\n")
    except Exception:
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="LLM-based tagging for CFSBK workouts (local audit tool).")
    parser.add_argument("--input", default="data/raw/latest.jsonl", help="Input jsonl from WP API.")
    parser.add_argument("--out", default="data/derived/llm_tags.jsonl", help="Output jsonl (gitignored).")
    parser.add_argument(
        "--out-json",
        default="data/derived/llm_tags.json",
        help="Output JSON array for the frontend (gitignored).",
    )
    parser.add_argument("--cache-dir", default="data/llm_cache", help="Per-post cache directory (gitignored).")
    parser.add_argument("--start-date", default=None, help="YYYY-MM-DD inclusive")
    parser.add_argument("--end-date", default=None, help="YYYY-MM-DD inclusive")
    parser.add_argument("--max-posts", type=int, default=None, help="Limit posts processed (after filtering).")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--max-tokens", type=int, default=800)
    parser.add_argument("--timeout-s", type=int, default=60)
    parser.add_argument("--judge", action="store_true", help="Run a second-pass LLM judge (cost: extra API calls).")
    parser.add_argument(
        "--judge-all",
        action="store_true",
        help="Judge every post in range (default: only judge posts where regex and first-pass LLM differ).",
    )
    parser.add_argument("--judge-model", default=None, help="Model for judge pass (defaults to --model).")
    parser.add_argument("--judge-max-tokens", type=int, default=None, help="Max tokens for judge pass (defaults to --max-tokens).")
    parser.add_argument("--judge-timeout-s", type=int, default=None, help="Timeout seconds for judge pass (defaults to --timeout-s).")
    parser.add_argument("--judge-out", default="data/derived/llm_judged_tags.jsonl", help="Judge output jsonl (gitignored).")
    parser.add_argument(
        "--judge-out-json",
        default="data/derived/llm_judged_tags.json",
        help="Judge output JSON array for the frontend (gitignored).",
    )
    parser.add_argument(
        "--regex-index",
        default="data/derived/search_index.json",
        help="Regex baseline (built by `etl.py build`). Used by the judge for comparison.",
    )
    parser.add_argument("--workers", type=int, default=6, help="Parallel requests to run (I/O bound; watch rate limits).")
    parser.add_argument("--resume", action="store_true", help="Skip posts already in output or cache.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite output files instead of appending (rerun a range without duplicates).",
    )
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.out)
    out_json_path = Path(args.out_json)
    cache_dir = Path(args.cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    movement_labels = load_canonical_movement_labels()
    cfg = LLMTaggingConfig(model=args.model, max_tokens=args.max_tokens, timeout_s=args.timeout_s)
    judge_cfg = LLMTaggingConfig(
        model=args.judge_model or args.model,
        max_tokens=args.judge_max_tokens or args.max_tokens,
        timeout_s=args.judge_timeout_s or args.timeout_s,
    )

    regex_by_id: Dict[int, Dict[str, Any]] = {}
    if args.judge:
        regex_by_id = _load_search_index(Path(args.regex_index))

    if args.overwrite:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("", encoding="utf-8")
        if args.judge:
            Path(args.judge_out).write_text("", encoding="utf-8")
    seen_ids: Set[int] = set()
    seen_judge_ids: Set[int] = set()
    if args.resume and not args.overwrite:
        # In CI we often commit the JSON array but not the jsonl; reconstruct local jsonl so
        # resume and JSON regeneration work as expected.
        _ensure_jsonl_from_json_array(out_json_path, out_path)
        if args.judge:
            _ensure_jsonl_from_json_array(Path(args.judge_out_json), Path(args.judge_out))

        seen_ids = _read_seen_ids(out_path)
        seen_ids |= _read_seen_ids_from_json_array(out_json_path)
        if args.judge:
            seen_judge_ids = _read_seen_ids(Path(args.judge_out))
            seen_judge_ids |= _read_seen_ids_from_json_array(Path(args.judge_out_json))

    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Missing OPENAI_API_KEY. Example: export OPENAI_API_KEY='...'")

    # Pre-scan input and select candidates (keeps the threaded work focused on I/O).
    total = 0
    candidates: List[Tuple[int, str, str, str, str]] = []  # (id, date, title, link, text)
    with in_path.open() as f:
        for line in f:
            post = json.loads(line)
            pid = post.get("id")
            if not isinstance(pid, int):
                continue
            total += 1

            post_date = (post.get("date") or "")[:10]
            workout_date = derive_workout_date(post, post_date)
            if not workout_date or len(workout_date) != 10:
                continue
            if not _should_include(workout_date, args.start_date, args.end_date):
                continue

            title_rendered = (post.get("title") or {}).get("rendered") or ""
            title = html.unescape(title_rendered)
            link = post.get("link") or ""
            text = _post_text(post)
            candidates.append((pid, workout_date, title, link, text))

            if args.max_posts and len(candidates) >= args.max_posts:
                break

    out_lock = threading.Lock()
    judge_lock = threading.Lock()
    counts = {"llm_written": 0, "judge_written": 0}

    def worker(pid: int, workout_date: str, title: str, link: str, text: str) -> None:
        session = requests.Session()

        cache_path = cache_dir / f"{pid}.json"
        judge_cache_path = cache_dir / f"judge_{pid}.json"

        llm_result: Optional[Dict[str, Any]] = None
        if args.resume and cache_path.exists():
            try:
                llm_result = json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                llm_result = None

        if llm_result is None:
            if args.resume and (pid in seen_ids) and not args.judge:
                return
            print(f"[llm] {workout_date} id={pid} title={title[:60]!r}")
            llm_result = tag_post_with_llm(
                post_id=pid,
                date=workout_date,
                title=title,
                link=link,
                full_text=text,
                movement_labels=movement_labels,
                cfg=cfg,
                session=session,
            )
            cache_path.write_text(json.dumps(llm_result, ensure_ascii=False, indent=2), encoding="utf-8")

        # Ensure outputs can be rebuilt from cache (resume mode).
        if not (args.resume and pid in seen_ids):
            _append_jsonl(out_path, llm_result, out_lock)
            with out_lock:
                counts["llm_written"] += 1
                seen_ids.add(pid)

        if not args.judge:
            return

        regex_item = regex_by_id.get(pid)
        if not regex_item:
            return

        regex_payload = _regex_payload_from_search_item(regex_item)
        llm_payload = _validate_llm_result(llm_result, movement_labels=movement_labels)
        do_judge = args.judge_all or _should_judge(regex_payload=regex_payload, llm_payload=llm_payload)
        if not do_judge:
            return

        judged: Optional[Dict[str, Any]] = None
        if args.resume and judge_cache_path.exists():
            try:
                judged = json.loads(judge_cache_path.read_text(encoding="utf-8"))
            except Exception:
                judged = None

        if judged is None:
            if args.resume and pid in seen_judge_ids:
                return
            post_payload = {"id": pid, "date": workout_date, "title": title, "link": link, "text": text}
            print(f"[judge] {workout_date} id={pid} title={title[:60]!r}")
            judged = judge_post_tags_with_llm(
                post_payload=post_payload,
                regex_result=regex_payload,
                llm_result=llm_payload,
                movement_labels=movement_labels,
                cfg=judge_cfg,
                session=session,
            )
            judge_cache_path.write_text(json.dumps(judged, ensure_ascii=False, indent=2), encoding="utf-8")

        if not (args.resume and pid in seen_judge_ids):
            _append_jsonl(Path(args.judge_out), judged, judge_lock)
            with judge_lock:
                counts["judge_written"] += 1
                seen_judge_ids.add(pid)

    workers = max(1, int(args.workers))
    if workers == 1:
        for c in candidates:
            worker(*c)
    else:
        # Submit at most `workers` tasks at a time so we immediately enqueue a new
        # candidate whenever one finishes (instead of building a huge queue).
        it = iter(candidates)
        with ThreadPoolExecutor(max_workers=workers) as ex:
            running = set()
            for _ in range(min(workers, len(candidates))):
                try:
                    c = next(it)
                except StopIteration:
                    break
                running.add(ex.submit(worker, *c))

            while running:
                done, running = wait(running, return_when=FIRST_COMPLETED)
                for fut in done:
                    # Surface failures early (and fail fast).
                    fut.result()
                    try:
                        c = next(it)
                    except StopIteration:
                        continue
                    running.add(ex.submit(worker, *c))

    # Produce a JSON array for the frontend to fetch.
    items: List[Dict[str, Any]] = []
    if out_path.exists():
        with out_path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    # Normalize older cached results to current canonical mappings.
                    items.append(_validate_llm_result(obj, movement_labels=movement_labels))
                except Exception:
                    continue
    out_json_path.parent.mkdir(parents=True, exist_ok=True)
    out_json_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.judge:
        judge_out_path = Path(args.judge_out)
        judge_out_json_path = Path(args.judge_out_json)
        judge_items: List[Dict[str, Any]] = []
        if judge_out_path.exists():
            with judge_out_path.open() as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        judge_items.append(_validate_llm_result(obj, movement_labels=movement_labels))
                    except Exception:
                        continue
        judge_out_json_path.parent.mkdir(parents=True, exist_ok=True)
        judge_out_json_path.write_text(json.dumps(judge_items, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[llm] Done. Sync derived data to the frontend: (cd frontend && npm run sync-data), then reload.")
    print(f"[llm] Wrote {counts['llm_written']} records to {out_path} and {len(items)} total to {out_json_path} (scanned {total} posts).")
    if args.judge:
        print(
            f"[judge] Wrote {counts['judge_written']} records to {Path(args.judge_out)} and {len(judge_items)} total to {Path(args.judge_out_json)}."
        )


if __name__ == "__main__":
    main()
