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


def _details_look_like_workout(details: str) -> bool:
    if not details:
        return False
    d = details.lower()
    if any(k in d for k in ["amrap", "for time", "emom", "every", "interval", "tabata"]):
        return True
    if re.search(r"\bcal(?:ories)?\b", d) and ("bike" in d or "row" in d):
        return True
    if re.search(r"\b\d+\b", d) and re.search(
        r"(row|run|bike|burpee|squat|deadlift|snatch|clean|press|pull[- ]?up|push[- ]?up|thruster|swing)",
        d,
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
        c
        for c in (components or [])
        if is_workout_component(c.get("component") or "")
        or _details_look_like_workout(c.get("details") or "")
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
        # Some older posts collapse multiple workout sections into a single block of text
        # separated by underscores/hyphens or phrases like "Post loads to comments. Exposure X of Y".
        # Normalize these into line breaks so we don't accidentally drop the metcon portion.
        detail = re.sub(r"\s*_{3,}\s*", "\n", detail)
        detail = re.sub(r"\s*-{3,}\s*", "\n", detail)
        detail = re.sub(r"(?i)\bpost\s+(?:loads?|work)\s+to\s+comments\.?", "\n", detail)
        detail = re.sub(r"(?i)\bpost\s+to\s+comments\.?", "\n", detail)
        detail = re.sub(r"(?i)\bexposure\s+\d+\s+of\s+\d+\b", "\n", detail)
        for line in detail.split("\n"):
            if not line.strip():
                continue
            lc = line.lower()
            lc_norm = " ".join(
                lc.replace("\xa0", " ").translate(apostrophe_replacements).split()
            )
            if re.fullmatch(r"[_\-\s]+", lc_norm):
                continue
            if any(mark in lc for mark in skip_markers):
                continue
            if "trivia" in lc or (re.match(r"^\d+\.", lc.strip()) and "?" in line):
                continue
            if any(marker in lc_norm for marker in promo_breaks):
                break
            m = re.search(r"post\s+.*comments", lc_norm)
            if m:
                prefix = line[: m.start()].strip()
                if prefix:
                    lines.append(prefix)
                continue
            if "post" in lc_norm and "comments" in lc_norm:
                cut_index = lc.lower().find("post")
                prefix = line[:cut_index].strip()
                if prefix:
                    lines.append(prefix)
                continue
            if re.search(r"weeks\s+1-2", lc_norm):
                break
            if "exposure" in lc_norm:
                prefix = line.split("exposure", 1)[0].strip()
                if prefix:
                    lines.append(prefix)
                continue
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
    # Many posts include "Yesterday's Whiteboard: Rest Day" in blog/news content;
    # don't treat those as actual rest days. Only consider "rest day" early in the post.
    intro = " ".join(
        ((c.get("component") or "") + " " + (c.get("details") or "")).strip()
        for c in (components or [])[:2]
    ).lower()
    if "rest day" not in intro:
        return False

    # If the intro still looks like a real workout, it's not a rest day.
    if _details_look_like_workout(intro):
        return False

    # Otherwise, treat it as a rest day.
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
