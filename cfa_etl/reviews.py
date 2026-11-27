"""Apply source-bound selections made by a reviewer."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .extraction import Block
from .paths import CONFIG_DIR

REVIEW_PATH = CONFIG_DIR / "workout_reviews.json"


def source_digest(title: str, blocks: list[Block]) -> str:
    evidence = [title, [[block.number, block.kind, block.text] for block in blocks]]
    return hashlib.sha256(json.dumps(evidence, ensure_ascii=False).encode()).hexdigest()


def load_reviews(path: Path = REVIEW_PATH) -> dict[int, dict]:
    if not path.exists():
        return {}
    reviews: dict[int, dict] = {}
    for record in json.loads(path.read_text(encoding="utf-8")):
        post_id = record["id"]
        if type(post_id) is not int or post_id in reviews:
            raise ValueError(f"Invalid or duplicate review ID: {post_id}")
        reviews[post_id] = record
    return reviews


def resolve_selection(title: str, blocks: list[Block], selection: dict) -> tuple[str, list[dict]]:
    """Validate the reviewer response and copy text directly out of its source blocks."""
    status = selection["status"]
    selections = selection["components"]
    if status not in {"reviewed", "rest_day", "non_workout", "needs_review"}:
        raise ValueError(f"Invalid review status: {status}")
    if not isinstance(selections, list) or bool(selections) != (status == "reviewed"):
        raise ValueError("A reviewed workout must identify at least one component")

    by_number = {block.number: block for block in blocks}
    last = 0
    components: list[dict] = []
    for component in selections:
        heading = component["heading"]
        prescription = component["prescription"]
        notes = component["notes"]
        if type(heading) is not int or heading < -1 or not isinstance(prescription, list) or not prescription or not isinstance(notes, list):
            raise ValueError("Invalid component selection")
        ids = ([heading] if heading > 0 else []) + prescription + notes
        if any(type(i) is not int or i not in by_number or not by_number[i].text or by_number[i].kind not in {"text", "heading"} for i in ids):
            raise ValueError("Selections must refer to text from the source post")
        if ids != sorted(set(ids)) or ids[0] <= last:
            raise ValueError("Selections must be unique and in source order")
        last = ids[-1]
        label = title if heading == -1 else by_number[heading].text if heading > 0 else "Workout"
        if "\n" in label:
            raise ValueError("Select a single line as the heading")
        components.append(
            {
                "component": label,
                "details": "\n".join(by_number[i].text for i in prescription),
                "notes": "\n".join(by_number[i].text for i in notes),
                "source_blocks": ids,
            }
        )
    return status, components
