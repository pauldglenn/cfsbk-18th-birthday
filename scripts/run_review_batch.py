"""Run and checkpoint model proposals for the archive review queue."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

import propose_workout_reviews as reviewer
from propose_workout_reviews import load_raw_posts, propose

MODEL = "gpt-5-mini"
reviewer.INSTRUCTIONS += """
If notes interrupt a prescription, split it into separate components so selected
IDs remain in strictly increasing order. Prefer heading 0 if the heading is
mixed with prescription text or spans multiple lines. If you cannot cleanly
select the evidence at block granularity, return needs_review.
"""


def select(post):
    for attempt in range(3):
        try:
            with requests.Session() as session:
                session.headers["Authorization"] = f"Bearer {os.environ['OPENAI_API_KEY']}"
                return propose(session, post, MODEL)
        except requests.HTTPError as error:
            code = error.response.status_code
            if code in {400, 401, 403, 404}:
                raise RuntimeError(f"OpenAI returned HTTP {code} ({error.response.json().get('error', {}).get('code')})") from None
            if code == 429 and error.response.json().get("error", {}).get("code") == "insufficient_quota":
                raise RuntimeError("OpenAI returned insufficient_quota") from None
        except (requests.Timeout, requests.ConnectionError, ValueError):
            pass
        time.sleep(2 ** attempt)
    raise RuntimeError("No valid response after three attempts")


def main():
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("This repository has no OPENAI_API_KEY available to the workflow.")
    ids = {1666, 1929, 785, 1172, 282, 1564, 6950, 1575, 7465, 5804, 1580, 1586, 1601, 7491, 327, 6736, 7384, 862, 6377, 6890, 1515, 1531, 1020, 6398}
    posts = [post for post in load_raw_posts() if post["id"] in ids]
    output = Path("review-output")
    output.mkdir(exist_ok=True)
    with (output / "proposals.jsonl").open("w") as proposals, (output / "errors.jsonl").open("w") as errors:
        print(f"{MODEL} reviewing {len(posts)} posts.", flush=True)
        with ThreadPoolExecutor(max_workers=8) as workers:
            tasks = {workers.submit(select, post): post["id"] for post in posts}
            for index, future in enumerate(as_completed(tasks), start=1):
                try:
                    proposals.write(json.dumps(future.result(), ensure_ascii=False) + "\n")
                    proposals.flush()
                except Exception as error:
                    errors.write(json.dumps({"id": tasks[future], "error": str(error)}) + "\n")
                    errors.flush()
                if index % 25 == 0 or index == len(posts):
                    print(f"Processed {index}/{len(posts)} posts.", flush=True)


if __name__ == "__main__":
    main()
