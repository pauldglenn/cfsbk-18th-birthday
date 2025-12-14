from __future__ import annotations

from typing import Dict, Iterable, List

from scrape_cfsbk import process_post

from .movements import (
    component_tag,
    detect_format,
    is_rest_day,
    load_movement_patterns,
    movement_text_from_components,
    tag_movements,
)


def build_canonical(
    raw_posts: Iterable[Dict],
    comment_counts: Dict[int, int] | None = None,
) -> List[Dict]:
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

    canonical.sort(key=lambda x: (x.get("date") or "", x.get("id") or 0))
    for idx, item in enumerate(canonical, start=1):
        item["seq_no"] = idx
        if idx in {1000, 2500, 5000} or idx == len(canonical):
            item.setdefault("milestones", []).append(f"{idx}th workout")

    return canonical

