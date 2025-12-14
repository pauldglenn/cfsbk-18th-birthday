from __future__ import annotations

import re
from typing import Dict, List, Tuple

import yaml

from .paths import CONFIG_DIR


def load_movement_patterns(config_dir=CONFIG_DIR) -> List[Tuple[str, List[re.Pattern]]]:
    config_path = config_dir / "movements.yml"
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
            continue
        if name == "deadlift":
            if "clean deadlift" in text_lower or "snatch deadlift" in text_lower:
                continue
        if any(r.search(text_lower) for r in regexes):
            found.append(name)
    return found


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


def is_workout_component(name: str) -> bool:
    name_l = name.lower()
    name_norm = re.sub(r"[^\w\s]", " ", name_l)
    ignore = (
        "training cycle",
        "upcoming",
        "schedule",
        "news",
        "notes",
        "recap",
        "tomorrow",
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )
    if any(k in name_norm for k in ignore):
        return False
    if component_tag(name):
        return True
    if re.search(
        r"(press|squat|deadlift|clean|snatch|row|run|bike|burpee|swing|pull[- ]?up|push[- ]?up)",
        name_norm,
    ):
        return True
    if any(
        k in name_norm
        for k in ["wod", "workout", "metcon", "conditioning", "cash out", "buy in", "cash-out", "cashout"]
    ):
        return True
    return False


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
        if "___" in detail:
            detail = detail.split("___", 1)[0]
        detail_lower = detail.lower()
        for marker in promo_breaks + [
            "post work to comments",
            "post loads to comments",
            "post load to comments",
            "post to comments",
        ]:
            idx = detail_lower.find(marker)
            if idx > 0:
                detail = detail[:idx]
                detail_lower = detail_lower[:idx]
                break
        for line in detail.split("\n"):
            if not line.strip():
                continue
            lc = line.lower()
            lc_norm = " ".join(
                lc.replace("\xa0", " ").translate(apostrophe_replacements).split()
            )
            if any(mark in lc for mark in skip_markers):
                continue
            if "trivia" in lc or (re.match(r"^\d+\.", lc.strip()) and "?" in line):
                continue
            if any(marker in lc_norm for marker in promo_breaks):
                break
            m = re.search(r"post\s+.*comments", lc_norm)
            if m:
                lines.append(line[: m.start()].strip())
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
            if "whiteboard" in lc_norm and "yesterday" in lc_norm:
                continue
            lines.append(line)

    if lines:
        return " ".join(lines)
    if source_components:
        return " ".join((c.get("details") or "") for c in source_components)
    return ""


def is_rest_day(components: List[Dict], title: str = "") -> bool:
    """
    Heuristic rest-day detector: if the combined component text mentions "rest day"
    and contains no rep schemes/numbers, treat as rest and skip movement tagging.
    """
    if "rest day" in (title or "").lower():
        return True
    text = " ".join(
        (c.get("component") or "") + " " + (c.get("details") or "")
        for c in (components or [])
    ).lower()
    if "rest day" not in text:
        return False
    if re.search(r"\d", text) and ("for time" in text or "amrap" in text or "emom" in text):
        return False
    return True


def extract_rep_scheme(components: List[Dict]) -> str:
    """
    Heuristic: pull lines from component details that look like rep schemes
    (numbers, AMRAP, For Time, EMOM). If nothing matches, fallback to the
    first 200 chars of the first component.
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
