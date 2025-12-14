from cfa_etl.comments_analysis import build_comments_analysis


def test_build_comments_analysis_basic():
    canonical = [
        {
            "id": 123,
            "date": "2020-05-25",
            "title": "\"Murph\"",
            "link": "https://example.com/murph",
            "components": [{"component": "Workout", "details": "1 Mile Run\n100 Pull-Ups"}],
        }
    ]
    comments = [
        {
            "id": 1,
            "post_id": 123,
            "date": "2020-05-25",
            "author_name": "Alex",
        },
        {
            "id": 2,
            "post_id": 123,
            "date": "2020-06-01",
            "author_name": "Alex",
        },
        {
            "id": 3,
            "post_id": 123,
            "date": "2020-06-02",
            "author_name": "Sam",
        },
    ]

    analysis = build_comments_analysis(canonical, comments)
    assert analysis["total_comments"] == 3
    assert analysis["top_posts"][0]["id"] == 123
    assert analysis["top_posts"][0]["comment_count"] == 3
    assert analysis["top_commenters"][0]["name"] == "Alex"
    assert analysis["top_commenters"][0]["count"] == 2
    months = [m["month"] for m in analysis["monthly"]]
    assert months == ["2020-05", "2020-06"]
