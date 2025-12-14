"""
ETL pipeline for CrossFit workouts.

Commands:
    uv run python etl.py fetch [--max-pages N]     # fetch raw posts to data/raw/
    uv run python etl.py build                     # parse raw posts -> canonical + aggregates
    uv run python etl.py all                       # fetch + build
"""

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import yaml
import requests

from scrape_cfsbk import (
    fetch_posts,
    process_post,
)

ROOT = Path(__file__).parent
RAW_DIR = ROOT / "data" / "raw"
DERIVED_DIR = ROOT / "data" / "derived"
CONFIG_DIR = ROOT / "config"
COMMENTS_API = "https://crossfitsouthbrooklyn.com/wp-json/wp/v2/comments"
HERO_NAMES = [
    "murph", "dt", "chad", "holleyman", "badger", "nate", "randy", "griff", "hidalgo", "jerry", "bull",
    "glen", "josh", "michael", "whitten", "jt", "lumberjack 20", "victoria", "mcghee", "abbate", "white",
    "kalsu", "manion", "morrison", "tommy v", "coe", "wittman", "mccluskey", "nick", "small", "roy",
    "gator", "garrett", "carse", "riley", "danny", "lorenza", "zeitoun", "murphy", "ship",
    "hansel", "jared", "peggy", "rhodesian", "tk", "tyler", "wood", "ryan", "camelot", "helm", "brenton",
]
GIRL_NAMES = [
    "angie", "barbara", "chelsea", "diane", "elizabeth", "fran", "helen", "isabel", "jackie", "karen",
    "linda", "mary", "nancy", "annie", "christine", "eva", "gwen", "hope", "nicole", "cindy", "kelly",
    "lynne", "amanda", "maggie", "lila", "ingrid", "lyla", "grace", "tiff", "vera", "ariane",
]

def compile_name_patterns(names: List[str]) -> List[Tuple[str, re.Pattern]]:
    patterns = []
    for name in names:
        escaped = re.escape(name).replace("\\ ", r"\s+")
        pat = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
        patterns.append((name.title(), pat))
    return patterns


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DERIVED_DIR.mkdir(parents=True, exist_ok=True)


def load_movement_patterns() -> List[Tuple[str, List[re.Pattern]]]:
    config_path = CONFIG_DIR / "movements.yml"
    with config_path.open() as f:
        data = yaml.safe_load(f) or []
    compiled = []
    for entry in data:
        name = entry.get("name")
        patterns = entry.get("patterns") or []
        regexes = [re.compile(pat, re.IGNORECASE) for pat in patterns]
        if name and regexes:
            compiled.append((name, regexes))
    return compiled


def tag_movements(text: str, compiled: List[Tuple[str, List[re.Pattern]]]) -> List[str]:
    found = []
    text_lower = text.lower()
    instructional_clean_deadlift = (
        "set up like a clean" in text_lower and "deadlift the bar up" in text_lower
    )
    for name, regexes in compiled:
        if name in {"clean", "deadlift"} and instructional_clean_deadlift:
            # Avoid tagging instructional language for rows (not an actual clean/deadlift)
            continue
        if name == "deadlift":
            # Skip deadlift tag if it's a clean/snatch deadlift
            if "clean deadlift" in text_lower or "snatch deadlift" in text_lower:
                continue
        if any(r.search(text_lower) for r in regexes):
            found.append(name)
    return found


def movement_text_from_components(components: List[Dict]) -> str:
    """
    Build a text blob for movement detection but drop lines that reference
    future workouts (e.g., "tomorrow we have running").
    """
    apostrophe_replacements = str.maketrans({"’": "'", "‘": "'"})
    skip_markers = (
        "tomorrow",
        "next week",
        "next day",
        "next cycle",
        "tomorrows",
        "training cycle",
        "our new cycle starts",
        "monday:",
        "tuesday:",
        "wednesday:",
        "thursday:",
        "friday:",
        "saturday:",
        "sunday:",
    )
    workout_components = [
        c for c in (components or []) if is_workout_component(c.get("component") or "")
    ]
    source_components = workout_components if workout_components else (components or [])
    lines: List[str] = []
    promo_breaks = [
        "pull for pride",
        "east coast gambit",
        "iron maidens",
        "registration will open",
        "next level weightlifting",
        "subway series",
        "our new cycle starts",
        "training cycle dates",
        "goals:",
    ]

    for comp in source_components:
        detail = comp.get("details") or ""
        # Drop blog extras after separator lines (e.g., trivia, links)
        if "___" in detail:
            detail = detail.split("___", 1)[0]
        detail_lower = detail.lower()
        for marker in promo_breaks + ["post work to comments", "post loads to comments", "post load to comments", "post to comments"]:
            idx = detail_lower.find(marker)
            if idx > 0:
                detail = detail[:idx]
                detail_lower = detail_lower[:idx]
                break
        for line in detail.split("\n"):
            if not line.strip():
                continue
            lc = line.lower()
            lc_norm = " ".join(lc.replace("\xa0", " ").translate(apostrophe_replacements).split())
            if any(mark in lc for mark in skip_markers):
                continue
            # Skip obvious non-workout trivia/questions like numbered Q lists
            if "trivia" in lc or (re.match(r"^\d+\.", lc.strip()) and "?" in line):
                continue
            promo_hit = False
            for marker in promo_breaks:
                if marker in lc_norm:
                    promo_hit = True
                    break
            if promo_hit:
                break
            m = re.search(r"post\s+.*comments", lc_norm)
            if m:
                cut_index = m.start()
                lines.append(line[:cut_index].strip())
                break
            if "post" in lc_norm and "comments" in lc_norm:
                cut_index = lc.lower().find("post")
                lines.append(line[:cut_index].strip())
                break
            if re.search(r"weeks\s+1-2", lc_norm):
                break
            if "exposure" in lc_norm:
                lines.append(line.split("exposure", 1)[0].strip())
                break
            # Drop link lists like "Yesterday's Whiteboard: Clean | Deadlifts..."
            if "whiteboard" in lc_norm and "yesterday" in lc_norm:
                continue
            lines.append(line)
    if lines:
        return " ".join(lines)
    if source_components:
        return " ".join((c.get("details") or "") for c in source_components)
    return ""


def is_workout_component(name: str) -> bool:
    name_l = name.lower()
    ignore = (
        "training cycle",
        "upcoming",
        "schedule",
        "news",
        "notes",
        "recap",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )
    if any(k in name_l for k in ignore):
        return False
    if component_tag(name):
        return True
    if re.search(r"(press|squat|deadlift|clean|snatch|row|run|bike|burpee|swing|pull[- ]?up|push[- ]?up)", name_l):
        return True
    if any(k in name_l for k in ["wod", "workout", "metcon", "conditioning", "cash out", "buy in", "cash-out", "cashout"]):
        return True
    return False


def is_rest_day(components: List[Dict], title: str = "") -> bool:
    """
    Heuristic rest-day detector: if the combined component text mentions "rest day"
    and contains no rep schemes/numbers, treat as rest and skip movement tagging.
    """
    if "rest day" in (title or "").lower():
        return True
    text = " ".join((c.get("component") or "") + " " + (c.get("details") or "") for c in components or "").lower()
    if "rest day" not in text:
        return False
    # if it looks like a workout (numbers + for time etc), don't treat as rest
    if re.search(r"\d", text) and ("for time" in text or "amrap" in text or "emom" in text):
        return False
    return True


def extract_rep_scheme(components: List[Dict]) -> str:
    """
    Heuristic: pull lines from component details that look like rep schemes
    (numbers, AMRAP, For Time, EMOM). If nothing matches, fallback to the
    first 120 chars of the first component.
    """
    keywords = ("amrap", "for time", "emom", "every", "round", "rounds", "minutes", "minute")
    lines = []
    for comp in components or []:
        detail = comp.get("details") or ""
        for line in detail.split("\n"):
            line_clean = line.strip()
            if not line_clean:
                continue
            lc = line_clean.lower()
            if any(k in lc for k in keywords) or re.search(r"\d", line_clean):
                lines.append(f"{comp.get('component') or ''}: {line_clean}".strip(": "))
    if lines:
        return " | ".join(lines)[:400]
    # fallback
    if components:
        first = (components[0].get("component") or "") + ": " + (components[0].get("details") or "")
        return first[:200]
    return ""


def detect_format(text: str) -> str:
    text_l = text.lower()
    if "amrap" in text_l:
        return "amrap"
    if "for time" in text_l:
        return "for time"
    if "emom" in text_l or "every minute" in text_l:
        return "emom"
    if "interval" in text_l or "tabata" in text_l:
        return "interval"
    return ""


def component_tag(name: str) -> str:
    name_l = name.lower()
    if "floater strength" in name_l:
        return "floater_strength"
    if "strength" in name_l:
        return "strength"
    if "assistance" in name_l or "accessory" in name_l or "bodybuilding" in name_l:
        return "assistance"
    if "metcon" in name_l or "conditioning" in name_l or "workout" in name_l:
        return "conditioning"
    if "partner" in name_l or "team" in name_l:
        return "partner"
    return ""


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


def build_canonical(raw_posts: Iterable[Dict], comment_counts: Dict[int, int] | None = None) -> List[Dict]:
    compiled_movements = load_movement_patterns()
    canonical: List[Dict] = []
    for post in raw_posts:
        base = process_post(post)
        if is_rest_day(base.get("components") or [], base.get("title") or ""):
            base.update({"movements": [], "format": "", "component_tags": []})
            if comment_counts:
                base["comment_count"] = comment_counts.get(base.get("id"), 0)
            canonical.append(base)
            continue
        movement_text = movement_text_from_components(base.get("components") or [])
        movement_source = f"{base.get('title') or ''} {movement_text}".strip()
        movements = tag_movements(movement_source.lower(), compiled_movements)
        formats = detect_format(movement_source.lower())
        component_tags = list(
            {
                component_tag(c.get("component") or "")
                for c in base.get("components") or []
                if component_tag(c.get("component") or "")
            }
        )
        base.update(
            {
                "movements": movements,
                "format": formats,
                "component_tags": component_tags,
                "comment_count": comment_counts.get(base.get("id"), 0) if comment_counts else 0,
            }
        )
        canonical.append(base)
    # seq_no by date then id
    canonical.sort(key=lambda x: (x.get("date") or "", x.get("id") or 0))
    for idx, item in enumerate(canonical, start=1):
        item["seq_no"] = idx
        if idx in {1000, 2500, 5000} or idx == len(canonical):
            item.setdefault("milestones", []).append(f"{idx}th workout")
    return canonical


def aggregate(canonical: List[Dict]) -> Dict[str, Dict]:
    movements_days = Counter()
    movement_pairs = Counter()
    yearly_counts = Counter()
    weekday_counts = Counter()
    movement_yearly = defaultdict(lambda: Counter())
    movement_weekday = defaultdict(lambda: Counter())
    movement_monthly = defaultdict(lambda: defaultdict(Counter))
    movement_calendar = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for item in canonical:
        date = item.get("date") or ""
        if date:
            yearly_counts[date[:4]] += 1
            try:
                dt_obj = datetime.fromisoformat(date)
                weekday = dt_obj.strftime("%A")
                weekday_counts[weekday] += 1
                ym = dt_obj.strftime("%Y-%m")
            except Exception:
                pass
        movs = set(item.get("movements") or [])
        summary = " ".join(
            (c.get("component") or "") + ": " + (c.get("details") or "")
            for c in item.get("components") or []
        )
        rep_summary = extract_rep_scheme(item.get("components") or [])
        for m in movs:
            movements_days[m] += 1
            if date:
                movement_yearly[m][date[:4]] += 1
                try:
                    dt_obj = datetime.fromisoformat(date)
                    weekday = dt_obj.strftime("%A")
                    movement_weekday[m][weekday] += 1
                    ym = dt_obj.strftime("%Y-%m")
                    movement_monthly[m][dt_obj.year][dt_obj.month] += 1
                    movement_calendar[m][dt_obj.year][dt_obj.month].append(
                        {
                            "day": dt_obj.day,
                            "date": date,
                            "title": item.get("title"),
                            "summary": rep_summary,
                            "link": item.get("link"),
                        }
                    )
                except Exception:
                    pass
        for a, b in itertools_pairs(sorted(movs)):
            movement_pairs[(a, b)] += 1

    top_movements = movements_days.most_common(100)
    top_pairs = [
        {"a": a, "b": b, "count": cnt} for (a, b), cnt in movement_pairs.most_common(200)
    ]

    return {
        "top_movements": [{"movement": m, "days": d} for m, d in top_movements],
        "top_pairs": top_pairs,
        "yearly_counts": dict(yearly_counts),
        "weekday_counts": dict(weekday_counts),
        "movement_yearly": {m: dict(c) for m, c in movement_yearly.items()},
        "movement_weekday": {m: dict(c) for m, c in movement_weekday.items()},
        "movement_monthly": {
            m: {str(y): {str(mon): count for mon, count in months.items()} for y, months in years.items()}
            for m, years in movement_monthly.items()
        },
        "movement_calendar": {
            m: {str(y): {str(mon): entries for mon, entries in months.items()} for y, months in years.items()}
            for m, years in movement_calendar.items()
        },
    }


def itertools_pairs(seq: List[str]):
    import itertools

    return itertools.combinations(seq, 2)


def build_named_workouts(canonical: List[Dict]) -> Dict[str, List[Dict]]:
    hero_hits = defaultdict(list)
    girl_hits = defaultdict(list)
    hero_patterns = compile_name_patterns(HERO_NAMES)
    girl_patterns = compile_name_patterns(GIRL_NAMES)

    for item in canonical:
        title_text = (item.get("title") or "").lower()
        matches_hero = [name for name, pat in hero_patterns if pat.search(title_text)]
        matches_girl = [name for name, pat in girl_patterns if pat.search(title_text)]
        summary = extract_rep_scheme(item.get("components") or [])
        entry = {
            "date": item.get("date"),
            "title": item.get("title"),
            "link": item.get("link"),
            "summary": summary,
        }
        for m in matches_hero:
            hero_hits[m].append(entry)
        for m in matches_girl:
            girl_hits[m].append(entry)

    def build_list(hit_map: Dict[str, List[Dict]]) -> List[Dict]:
        data = []
        for name, entries in hit_map.items():
            entries_sorted = sorted(entries, key=lambda e: e.get("date") or "", reverse=True)
            data.append(
                {
                    "name": name,
                    "count": len(entries_sorted),
                    "latest_date": entries_sorted[0].get("date"),
                    "latest_link": entries_sorted[0].get("link"),
                    "occurrences": entries_sorted,
                }
            )
        return sorted(data, key=lambda x: (-x["count"], x["name"]))

    return {"heroes": build_list(hero_hits), "girls": build_list(girl_hits)}


def write_artifacts(canonical: List[Dict], aggregates: Dict[str, Dict]) -> None:
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
    # Search bundle: slim fields for UI search
    search_path = DERIVED_DIR / "search_index.json"
    search_data = [
        {
            "id": item.get("id"),
            "date": item.get("date"),
            "title": item.get("title"),
            "link": item.get("link"),
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
    version = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_workouts": len(canonical),
    }
    with version_path.open("w", encoding="utf-8") as f:
        json.dump(version, f, indent=2)
    # Named workout collections (Hero WODs + Girls)
    named_path = DERIVED_DIR / "named_workouts.json"
    with named_path.open("w", encoding="utf-8") as f:
        json.dump(build_named_workouts(canonical), f, ensure_ascii=False, indent=2)
    print(f"Wrote canonical -> {canonical_path}")
    print(f"Wrote aggregates -> {DERIVED_DIR}")


def cmd_fetch(args: argparse.Namespace) -> None:
    fetch_raw(max_pages=args.max_pages)


def cmd_build(_: argparse.Namespace) -> None:
    raw = list(load_raw_posts())
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
    p_build.set_defaults(func=cmd_build)

    p_all = sub.add_parser("all", help="Fetch then build.")
    p_all.add_argument("--max-pages", type=int, default=None, help="Limit pages (testing).")
    p_all.add_argument("--with-comments", action="store_true", help="Fetch comment counts (hits API).")
    p_all.set_defaults(func=cmd_all)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
