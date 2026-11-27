from __future__ import annotations

from typing import Dict, Iterable, List

from scrape_cfsbk import process_post

from .extraction import workout_formats
from .movements import component_tag, load_movement_patterns, tag_movements


def build_canonical(
    raw_posts: Iterable[Dict],
    comment_counts: Dict[int, int] | None = None,
    reviewed: Dict[int, Dict] | None = None,
) -> List[Dict]:
    compiled_movements = load_movement_patterns()
    canonical: List[Dict] = []

    for post in raw_posts:
        review = (reviewed or {}).get(post.get("id"))
        base = process_post(post, compiled_movements, review=review)
        movements: set[str] = set()
        formats: set[str] = set()
        component_tags: set[str] = set()

        for component in base["components"]:
            label = component["component"]
            details = component["details"]
            component_moves = {
                movement
                for line in (label + "\n" + details).splitlines()
                for movement in tag_movements(line, compiled_movements)
            }
            component_formats = workout_formats(label + "\n" + details)
            tags = {component_tag(label)} - {""}
            if component_formats and label == "Workout":
                tags.add("conditioning")
            if "partner" in label.lower() or "team" in label.lower():
                tags.add("partner")
            component.update(movements=sorted(component_moves), formats=component_formats, tags=sorted(tags))
            movements.update(component_moves)
            formats.update(component_formats)
            component_tags.update(tags)

        is_workout = base["extraction_status"] in {"extracted", "reviewed"}
        all_formats = sorted(formats) if is_workout else []
        base.update(
            movements=sorted(movements) if is_workout else [],
            formats=all_formats,
            format=next((value for value in ("amrap", "for time", "emom", "interval", "not for time", "for reps") if value in all_formats), ""),
            component_tags=sorted(component_tags) if is_workout else [],
            is_rest_day=base["extraction_status"] == "rest_day",
            comment_count=(comment_counts or {}).get(base["id"], 0),
        )
        canonical.append(base)

    canonical.sort(key=lambda item: (item["date"] or "", item["id"] or 0))

    workout_no = 0
    for idx, item in enumerate(canonical, start=1):
        item["seq_no"] = idx
        if item["extraction_status"] in {"extracted", "reviewed"}:
            workout_no += 1
            item["workout_no"] = workout_no
        else:
            item["workout_no"] = None

    milestone_targets = {1000, 2500, 5000, workout_no}
    for item in canonical:
        number = item["workout_no"]
        if number in milestone_targets:
            item["milestones"] = [f"{number}th workout"]

    return canonical
