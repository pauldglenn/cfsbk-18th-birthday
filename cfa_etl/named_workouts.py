from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List

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


def _normalize_name(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def build_named_workouts(canonical: List[Dict]) -> Dict[str, List[Dict]]:
    hero_hits = defaultdict(list)
    girl_hits = defaultdict(list)

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
        if item.get("extraction_status") not in {None, "extracted", "reviewed"}:
            continue
        title_l = (item.get("title") or "").lower()
        quoted = re.findall(r'["“]([^"”]+)["”]', title_l)
        title_parts = [title_l, *quoted, *re.split(r"\s*\|\s*", title_l)]
        title_names = {_normalize_name(part) for part in title_parts}
        if re.match(r"^(?:(?:monday|sunday) \d{1,2}\.\d{1,2}\.\d{2,4} |\d+(?:st|nd|rd|th) annual )?memorial day murph(?: \d{4})?$", title_l):
            title_names.add("murph")
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

        component_names_normalized = {_normalize_name(name) for name in component_names}
        names = title_names | component_names_normalized
        for entries, benchmarks in ((hero_hits, HERO_NAMES), (girl_hits, GIRL_NAMES)):
            for name in benchmarks:
                if _normalize_name(name) in names:
                    entries[name].append(entry)

    def build_list(hit_map: Dict[str, List[Dict]]) -> List[Dict]:
        data = []
        for name, entries in hit_map.items():
            entries_sorted = sorted(entries, key=lambda e: e.get("date") or "", reverse=True)
            data.append(
                {
                    "name": name.upper() if name == "dt" else name.title(),
                    "count": len(entries_sorted),
                    "latest_date": entries_sorted[0].get("date"),
                    "latest_link": entries_sorted[0].get("link"),
                    "occurrences": entries_sorted,
                }
            )
        return sorted(data, key=lambda x: (-x["count"], x["name"]))

    return {"heroes": build_list(hero_hits), "girls": build_list(girl_hits)}

