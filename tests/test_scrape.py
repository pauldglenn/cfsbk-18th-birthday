import pathlib
import sys

import pytest
from bs4 import BeautifulSoup

# Ensure project root on path for module imports
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrape_cfsbk import derive_workout_date, parse_components
from scrape_cfsbk import process_post
from etl import (
    extract_rep_scheme,
    movement_text_from_components,
    tag_movements,
    load_movement_patterns,
)


def test_derive_workout_date_prefers_title():
    post = {
        "title": {"rendered": "Friday 11-7-25"},
        "slug": "friday-11-7-25",
        "link": "https://example.com/workout-of-the-day/2025/11/06/friday-11-7-25.html/",
        "date": "2025-11-06T12:00:00",
    }
    assert derive_workout_date(post, "2025-11-06") == "2025-11-07"


def test_extract_rep_scheme_prefers_numbered_lines():
    comps = [
        {"component": "Metcon", "details": "For Time:\n30 Snatches\nNotes etc."},
        {"component": "Strength", "details": "3x5 Back Squat"},
    ]
    rep = extract_rep_scheme(comps)
    assert "For Time" in rep and "30 Snatches" in rep


def test_movement_text_skips_future_mentions():
    comps = [
        {"component": "Notes", "details": "Tomorrow we have running and clusters"},
        {"component": "Metcon", "details": "5 Rounds for time of: Run 400m\n8 Clusters"},
    ]
    text = movement_text_from_components(comps)
    assert "Tomorrow we have" not in text
    assert "Run 400m" in text


def test_parse_components_fallback_when_missing_headings():
    html = """
    <div>
      <p><strong>5 rounds for time</strong></p>
      <p>Run 400m</p>
      <p>10 Pull-Ups</p>
    </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    comps = parse_components(soup)
    assert len(comps) == 1
    assert "Run 400m" in comps[0]["details"]


def test_process_post_unescapes_title_entities():
    post = {
        "id": 999,
        "title": {"rendered": "Front Squat / Jerk | &#8220;Annie&#8221;"},
        "slug": "front-squat-jerk-annie",
        "link": "https://example.com/workout-of-the-day/2012/01/01/front-squat-jerk-annie.html/",
        "date": "2012-01-01T12:00:00",
        "content": {"rendered": "<div><p><strong>Workout</strong></p><p>For Time: 50 DU</p></div>"},
    }
    item = process_post(post)
    assert "“Annie”" in item["title"]


def test_kettlebell_swings_not_lost():
    title = "Tuesday 7.15.25"
    comps = [
        {
            "component": "METCON",
            "details": "3 Rounds for time:\n400 m Run\n24 Hand to Hand KB Swings (24/16kg; 12 per arm)\n12 Alternating Renegade Rows",
        }
    ]
    movement_text = movement_text_from_components(comps)
    tags = tag_movements(f"{title} {movement_text}".lower(), load_movement_patterns())
    assert "kettlebell swing" in tags
    assert "run" in tags


def test_deadlift_not_from_promo():
    title = "WOD 6.20.19"
    comps = [
        {
            "component": "WOD",
            "details": (
                "Every Minute on the Minute x 24: 1) 5 Wall Balls 2) 1 Hang Power Clean "
                "Use a heavier load... Post work to comments. Exposure 3 of 6 "
                "Cam and crew will compete in Pull for Pride, a Deadlift-only event to benefit AFC."
            ),
        }
    ]
    movement_text = movement_text_from_components(comps)
    tags = tag_movements(f"{title} {movement_text}".lower(), load_movement_patterns())
    assert "deadlift" not in tags
    assert "wall ball" in tags
    assert "clean" in tags


def test_instructional_clean_deadlift_not_tagged():
    title = "Bench Press / Bent-Over Row | WOD 7.25.16"
    comps = [
        {
            "component": "Bench Press / Bent-Over Row Superset",
            "details": (
                "1A) Barbell Bench Press\n"
                "1B) Barbell Bent-Over Row\n"
                "1) Set up like a Clean and Deadlift the bar up.\n"
                "3 Rounds for Time: 15 Front Squats 95/65\n"
                "15 Push Presses 95/65\n"
                "15 Pull-Ups"
            ),
        }
    ]
    movement_text = movement_text_from_components(comps)
    tags = tag_movements(f"{title} {movement_text}".lower(), load_movement_patterns())
    assert "clean" not in tags
    assert "deadlift" not in tags
    assert "bench press" in tags
    assert "row (weighted)" in tags


def test_yesterdays_whiteboard_link_not_tagged_as_clean():
    title = "Push Press | WOD 1.25.16"
    comps = [
        {
            "component": "Push Press",
            "details": (
                "Push Press 5-3-3-2-1-1-1\n"
                "5 Rounds for Reps:\n"
                "1 Minute Max Push Press at 70% of your heavy single\n"
                "1 Minute Max Calories Rowed"
            ),
        },
        {
            "component": "The Return of the Monthly Egg CSA!",
            "details": (
                "Yesterday's Whiteboard: Clean | Deadlifts, Hang Power Cleans, Burpees, Kettlebell Swings, Toes-to-Bars"
            ),
        },
    ]
    movement_text = movement_text_from_components(comps)
    tags = tag_movements(f"{title} {movement_text}".lower(), load_movement_patterns())
    assert "clean" not in tags
    assert "push press" in tags
    assert "row (erg)" in tags


def test_recaps_with_wod_in_title_not_tagged():
    title = "Push Press | WOD 1.25.16"
    comps = [
        {
            "component": "Push Press",
            "details": "Push Press 5-3-3-2-1-1-1\n5 Rounds for Reps: 1 Minute Max Push Press\n1 Minute Max Calories Rowed",
        },
        {
            "component": "Wodapalooza 2016: A Recap",
            "details": "The competition had events with Power Snatches, Thrusters, Deadlifts, and Clean and Jerks.",
        },
    ]
    movement_text = movement_text_from_components(comps)
    tags = tag_movements(f"{title} {movement_text}".lower(), load_movement_patterns())
    assert "clean" not in tags
    assert "thruster" not in tags
    assert "push press" in tags
    assert "row (erg)" in tags


def test_named_workouts_include_grace_and_murph_counts():
    from etl import build_named_workouts

    # Load canonical from derived data for integration check
    import json
    from pathlib import Path

    canonical = [json.loads(line) for line in (Path(__file__).resolve().parents[1] / "data" / "derived" / "workouts.jsonl").read_text().splitlines()]
    named = build_named_workouts(canonical)

    grace = next((w for w in named["girls"] if w["name"].lower() == "grace"), None)
    assert grace is not None
    assert any(occ["date"] == "2025-11-13" for occ in grace["occurrences"])

    murph = next((w for w in named["heroes"] if w["name"].lower() == "murph"), None)
    assert murph is not None
    assert murph["count"] == 17


def test_named_workouts_skip_tomorrow_components():
    from etl import build_named_workouts

    canonical = [
        {
            "date": "2020-05-24",
            "title": "WOD 5.24.20",
            "link": "https://example.com/tomorrow",
            "components": [
                {"component": "Tomorrow: Memorial Day \"Murph\"", "details": "promo copy"},
                {"component": "Workout", "details": "Not murph"},
            ],
        },
        {
            "date": "2020-05-25",
            "title": "\"Murph\"",
            "link": "https://example.com/murph",
            "components": [
                {"component": "Workout", "details": "1 Mile Run 100 Pull-Ups 200 Push-Ups 300 Squats 1 Mile Run"},
            ],
        },
    ]
    named = build_named_workouts(canonical)
    murph = next((w for w in named["heroes"] if w["name"].lower() == "murph"), None)
    assert murph is not None
    assert murph["count"] == 1
    assert murph["occurrences"][0]["date"] == "2020-05-25"


def test_named_workouts_captures_grace_component_quotes():
    from etl import build_named_workouts

    canonical = [
        {
            "date": "2025-11-13",
            "title": "Thursday 11.13.25",
            "link": "https://example.com/grace",
            "components": [
                {"component": "STRENGTH", "details": "Other work"},
                {"component": "“GRACE”", "details": "For Time: 30 Clean and Jerks"},
            ],
        }
    ]
    named = build_named_workouts(canonical)
    grace = next((w for w in named["girls"] if w["name"].lower() == "grace"), None)
    assert grace is not None
    assert grace["count"] == 1
    assert grace["occurrences"][0]["date"] == "2025-11-13"


def test_burpee_not_from_tomorrow_note():
    title = "Floater Strength"
    comps = [
        {
            "component": "FLOATER STRENGTH",
            "details": "A. Power Clean and Push Jerk\nE. Deadlift 3x4-6 Across\nNotes\nTomorrow we have running, wall balls, sit-ups, burpees, and kipping pull-ups.",
        }
    ]
    movement_text = movement_text_from_components(comps)
    tags = tag_movements(f"{title} {movement_text}".lower(), load_movement_patterns())
    assert "burpee" not in tags
    assert "deadlift" in tags


def test_workout_no_skips_rest_days_for_milestones():
    from cfa_etl.canonical import build_canonical

    raw_posts = [
        {
            "id": 1,
            "date": "2020-01-01T12:00:00",
            "link": "https://example.com/1",
            "slug": "wod-1",
            "title": {"rendered": "WOD 1.1.20"},
            "content": {"rendered": "<p><strong>Workout</strong></p><p>For Time: 10 Burpees</p>"},
        },
        {
            "id": 2,
            "date": "2020-01-02T12:00:00",
            "link": "https://example.com/2",
            "slug": "rest",
            "title": {"rendered": "Rest Day"},
            "content": {"rendered": "<p>Rest Day</p>"},
        },
        {
            "id": 3,
            "date": "2020-01-03T12:00:00",
            "link": "https://example.com/3",
            "slug": "wod-3",
            "title": {"rendered": "WOD 1.3.20"},
            "content": {"rendered": "<p><strong>Workout</strong></p><p>For Time: 10 Burpees</p>"},
        },
    ]
    canonical = build_canonical(raw_posts)
    w1 = next(i for i in canonical if i["id"] == 1)
    r = next(i for i in canonical if i["id"] == 2)
    w3 = next(i for i in canonical if i["id"] == 3)
    assert w1["workout_no"] == 1
    assert r["is_rest_day"] is True
    assert r["workout_no"] is None
    assert w3["workout_no"] == 2
