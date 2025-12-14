"""
Internal ETL modules for this repo.

`etl.py` remains the CLI entrypoint and re-exports a few helpers used by tests,
but the implementation lives in `cfa_etl/*` to keep the codebase maintainable.
"""

from .aggregates import aggregate
from .canonical import build_canonical
from .io import ensure_dirs, fetch_comment_counts, fetch_raw, load_raw_posts, write_artifacts
from .movements import (
    component_tag,
    detect_format,
    extract_rep_scheme,
    is_rest_day,
    is_workout_component,
    load_movement_patterns,
    movement_text_from_components,
    tag_movements,
)
from .named_workouts import build_named_workouts

__all__ = [
    "aggregate",
    "build_canonical",
    "build_named_workouts",
    "component_tag",
    "detect_format",
    "ensure_dirs",
    "extract_rep_scheme",
    "fetch_comment_counts",
    "fetch_raw",
    "is_rest_day",
    "is_workout_component",
    "load_movement_patterns",
    "load_raw_posts",
    "movement_text_from_components",
    "tag_movements",
    "write_artifacts",
]

