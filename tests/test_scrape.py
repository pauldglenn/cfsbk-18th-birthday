import pathlib
import sys

import pytest
from bs4 import BeautifulSoup

# Ensure project root on path for module imports
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scrape_cfsbk import derive_workout_date, parse_components
from etl import extract_rep_scheme, movement_text_from_components


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
