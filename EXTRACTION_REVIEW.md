# CrossFit South Brooklyn workout extraction

The archive uses the gym’s WordPress Workout of the Day category. The 2025 checkout kept 6,465 source posts and generated two separate sets of model tags. In the deployed code, the browser could swap in those tags for search and movement counts while retaining the original regex summaries and benchmark results. That meant two parts of the site could describe different workouts from the same post.

## Source checks

| Post | What the extraction needs to preserve |
| --- | --- |
| 2007 Fight Gone Bad | Written station order, work and rest timing, and both published load options. This edition has kettlebell swings. [Source](https://crossfitsouthbrooklyn.com/workout-of-the-day/2007/12/23/20071223wod-122307-html.html/) |
| 2008 charity 5K announcement | This is an announcement about a member’s upcoming race. [Source](https://crossfitsouthbrooklyn.com/workout-of-the-day/2008/04/09/200849michele-willingly-runs-a-5k-html.html/) |
| 2010 front squat | The lift is named in the title. The rowing, deadlifts and burpees are another component after the instruction to post scores. [Source](https://crossfitsouthbrooklyn.com/workout-of-the-day/2010/06/16/2010616front-squat-html.html/) |
| 2014 front squat | Performance and Fitness have different rep schemes and movements. Both belong in the archive under their original labels. [Source](https://crossfitsouthbrooklyn.com/workout-of-the-day/2014/02/17/2014217front-squat-html.html/) |
| 2019 Open workout | Ground-to-overhead is the prescription. Snatch and clean and jerk are techniques allowed by the notes. Keep the cap and scaled loading with the workout. [Source](https://crossfitsouthbrooklyn.com/workout-of-the-day/2019/10/11/wod-10-12-19.html/) |
| 2020 Friday programming | CrossFit has its own metcon and strength work. The same post lists distinct CFSBK @ Home and Fit55 sessions. [Source](https://crossfitsouthbrooklyn.com/workout-of-the-day/2020/09/04/7840.html/) |
| 2023 Memorial Day Murph | The prescription is an embedded image. Verifying the sets, reps and loading requires the source image. The archive routes it to review. [Source](https://crossfitsouthbrooklyn.com/workout-of-the-day/2023/05/28/memorial-day-murph-2023.html/) |
| 2024 floater strength | Tomorrow’s workout appears in a note. A separate note describes renegade rows where today’s written prescription says dumbbell bench press. The archive shows both source texts and counts the written prescription. [Source](https://crossfitsouthbrooklyn.com/workout-of-the-day/2024/12/14/sunday-12-15-24.html/) |
| 2025 partner metcon | The rowing distance and couplet are both prescribed. The notes explain simultaneous work, switching partners, and when to stop. [Source](https://crossfitsouthbrooklyn.com/workout-of-the-day/2025/06/13/saturday-6-14-25.html/) |

## How the rebuild works

- The parser preserves paragraph and line breaks in the programming, isolates coaching notes, and records the original post ID and URL. Formatting whitespace is normalized. Source selections point to numbered blocks of text.
- The build derives the search index, movement and format tags, benchmarks, milestones, and charts from the same canonical records. Counts refer to indexed posts. Movements listed as prescribed alternatives may both be counted.
- Cases without enough textual evidence stay visible in the finder under **Needs review** and are excluded from workout statistics. Automatically extracted records can still be incomplete, especially where older posts use inconsistent markup or embed content in images.
- `config/workout_reviews.json` contains source selections checked against 22 posts. The build rejects selections for changed source blocks. Structural validation verifies that the text came from the post. A reviewer still needs to decide whether it belongs to that day’s programming.
- `scripts/propose_workout_reviews.py` can request numbered selections from a model using structured output. It writes a separate proposal file. Check it against the source, then copy accepted selections into the reviewed configuration. Compare candidates on a dated sample that includes both common templates and ambiguous posts before running a larger batch. Measure exact prescription completeness, irrelevant-text inclusion, and movement and format accuracy independently.

The 2026 update uses the newest four WordPress category pages, which overlap the existing raw snapshot, with posts deduplicated by WordPress ID. The comment dashboard shows the original comment snapshot. The older model outputs remain accessible at `#/llm-audit`. The new model proposal command requires an OpenAI API key. Its API-backed run is pending.
