from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Tuple

from .movements import extract_rep_scheme


HERO_NAMES = [
    "murph",
    "dt",
    "chad",
    "holleyman",
    "badger",
    "nate",
    "randy",
    "griff",
    "hidalgo",
    "jerry",
    "bull",
    "glen",
    "josh",
    "michael",
    "whitten",
    "jt",
    "lumberjack 20",
    "victoria",
    "mcghee",
    "abbate",
    "white",
    "kalsu",
    "manion",
    "morrison",
    "tommy v",
    "coe",
    "wittman",
    "mccluskey",
    "nick",
    "small",
    "roy",
    "gator",
    "garrett",
    "carse",
    "riley",
    "danny",
    "lorenza",
    "zeitoun",
    "murphy",
    "ship",
    "hansel",
    "jared",
    "peggy",
    "rhodesian",
    "tk",
    "tyler",
    "wood",
    "ryan",
    "camelot",
    "helm",
    "brenton",
]

GIRL_NAMES = [
    "angie",
    "barbara",
    "chelsea",
    "diane",
    "elizabeth",
    "fran",
    "helen",
    "isabel",
    "jackie",
    "karen",
    "linda",
    "mary",
    "nancy",
    "annie",
    "christine",
    "eva",
    "gwen",
    "hope",
    "nicole",
    "cindy",
    "kelly",
    "lynne",
    "amanda",
    "maggie",
    "lila",
    "ingrid",
    "lyla",
    "grace",
    "tiff",
    "vera",
    "ariane",
]


def _compile_name_patterns(names: List[str]) -> List[Tuple[str, re.Pattern]]:
    patterns = []
    for name in names:
        escaped = re.escape(name).replace("\\ ", r"\s+")
        pat = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
        patterns.append((name.title(), pat))
    return patterns


def _normalize_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def build_named_workouts(canonical: List[Dict]) -> Dict[str, List[Dict]]:
    hero_hits = defaultdict(list)
    girl_hits = defaultdict(list)
    hero_patterns = _compile_name_patterns(HERO_NAMES)
    girl_patterns = _compile_name_patterns(GIRL_NAMES)

    ignores = (
        "training cycle",
        "upcoming",
        "schedule",
        "news",
        "notes",
        "recap",
        "tomorrow",
    )

    for item in canonical:
        title_l = (item.get("title") or "").lower()
        component_names: List[str] = []
        for comp in item.get("components") or []:
            name = (comp.get("component") or "").lower()
            if not name:
                continue
            if any(ig in name for ig in ignores):
                continue
            component_names.append(name)

        summary = extract_rep_scheme(item.get("components") or [])
        entry = {
            "date": item.get("date"),
            "title": item.get("title"),
            "link": item.get("link"),
            "summary": summary,
        }

        matches_hero = []
        for name, pat in hero_patterns:
            name_norm = _normalize_name(name)
            title_hit = bool(pat.search(title_l))
            comp_hit = any(_normalize_name(c) == name_norm for c in component_names)
            if not (title_hit or comp_hit):
                continue
            if name_norm == "murph" and not title_hit:
                summary_l = summary.lower()
                if not (
                    ("pull" in summary_l and "push" in summary_l and "squat" in summary_l)
                    or "1 mile" in summary_l
                    or "1-mile" in summary_l
                ):
                    continue
            matches_hero.append(name)

        matches_girl = []
        for name, pat in girl_patterns:
            name_norm = _normalize_name(name)
            if pat.search(title_l) or any(_normalize_name(c) == name_norm for c in component_names):
                matches_girl.append(name)

        for m in matches_hero:
            if _normalize_name(m) == "murph":
                summary_l = summary.lower()
                if not (
                    ("pull" in summary_l and "push" in summary_l and "squat" in summary_l)
                    or "1 mile" in summary_l
                    or "1-mile" in summary_l
                ):
                    continue
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

    murph_entries = []
    for item in canonical:
        if "murph" in (item.get("title") or "").lower():
            summary = extract_rep_scheme(item.get("components") or [])
            murph_entries.append(
                {
                    "date": item.get("date"),
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "summary": summary,
                }
            )
    if murph_entries:
        hero_hits["Murph"] = murph_entries

    return {"heroes": build_list(hero_hits), "girls": build_list(girl_hits)}

