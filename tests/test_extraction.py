import json

import pytest
from bs4 import BeautifulSoup

from cfa_etl.canonical import build_canonical
from cfa_etl.extraction import source_blocks
from cfa_etl.io import load_raw_posts
from cfa_etl.reviews import load_reviews, resolve_selection
from scrape_cfsbk import process_post


@pytest.fixture(scope="module")
def posts():
    ids = {348, 374, 10418, 10754, 11430, 12240, 12953, 13127}
    return {post["id"]: post for post in load_raw_posts() if post["id"] in ids}


def test_extracts_unheaded_modern_programming_without_article(posts):
    record = process_post(posts[12953])
    assert record["extraction_status"] == "extracted"
    component, = record["components"]
    assert component["details"].splitlines() == [
        "5 Rounds for time of:", "Run 400m", "8 Clusters (+/155/135/95/75/-)", "12 Kipping Pull-Ups"
    ]
    assert "Bar Muscle-Ups" in component["notes"]
    assert "The Cluster" not in component["notes"]


def test_preserves_strength_subsections_after_notes(posts):
    record = process_post(posts[10418])
    strength_a, strength_b, partner = record["components"]
    assert strength_a["details"] == "A1) Barbell RDL: 4 x 6-8"
    assert strength_b["details"] == "A2) Incline Dumbbell Bench Press: 3 x 9-12"
    assert partner["component"] == "PARTNER METCON"


def test_keeps_prescription_and_tags_consistent(posts):
    workouts = {w["id"]: w for w in build_canonical(posts.values(), reviewed=load_reviews())}
    assert workouts[348]["workout_no"] is None
    assert workouts[10754]["extraction_status"] == "needs_review"
    assert workouts[10754]["workout_no"] is None
    assert workouts[374]["extraction_status"] == "reviewed"
    assert "sumo deadlift high pull" in workouts[374]["movements"]
    assert workouts[11430]["formats"] == ["emom"]
    assert "handstand push-up" in workouts[11430]["movements"]
    assert "push-up" not in workouts[11430]["movements"]
    assert "row (weighted)" not in workouts[12240]["movements"]
    assert "Renegade Rows" in workouts[12240]["components"][1]["notes"]
    assert workouts[13127]["components"][0]["component"] == "At Home Workout"


def test_review_rejects_unavailable_or_reordered_evidence():
    blocks = source_blocks(BeautifulSoup("<h4>METCON</h4><p>For time: 10 burpees</p>", "html.parser"))
    with pytest.raises(ValueError, match="source post"):
        resolve_selection("Monday", blocks, {"status": "reviewed", "components": [{"heading": 1, "prescription": [900], "notes": []}]})
    with pytest.raises(ValueError, match="source order"):
        resolve_selection("Monday", blocks, {"status": "reviewed", "components": [{"heading": 2, "prescription": [1], "notes": []}]})


def test_changed_source_disables_previously_reviewed_programming(posts):
    post = json.loads(json.dumps(posts[374]))
    post["content"]["rendered"] = "<p>There was a new post here.</p>"
    record = process_post(post, review=load_reviews()[374])
    assert record["extraction_status"] == "needs_review"
    assert not record["components"]
