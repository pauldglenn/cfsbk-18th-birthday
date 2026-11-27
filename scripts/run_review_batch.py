"""Run and checkpoint model proposals for the archive review queue."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from propose_workout_reviews import load_raw_posts, propose

MODEL = "gpt-5-mini"


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
    search = json.loads(Path("data/derived/search_index.json").read_text())
    ids = {row["id"] for row in search if row["extraction_status"] == "needs_review"}
    posts = [post for post in load_raw_posts() if post["id"] in ids]
    output = Path("review-output")
    output.mkdir(exist_ok=True)
    with (output / "proposals.jsonl").open("w") as proposals, (output / "errors.jsonl").open("w") as errors:
        first, *remaining = posts
        proposals.write(json.dumps(select(first), ensure_ascii=False) + "\n")
        proposals.flush()
        print(f"{MODEL} accepted first post. Reviewing {len(posts)} posts.", flush=True)
        with ThreadPoolExecutor(max_workers=8) as workers:
            tasks = {workers.submit(select, post): post["id"] for post in remaining}
            for index, future in enumerate(as_completed(tasks), start=2):
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
