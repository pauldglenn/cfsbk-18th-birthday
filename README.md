# CrossFit South Brooklyn Workout Archive

A searchable archive of CrossFit South Brooklyn’s daily programming from 2007 through November 2026. See the [extraction review](EXTRACTION_REVIEW.md) for source examples, known limits, and the review workflow.

## Usage (uv)
```bash
# Install deps into .venv
uv sync

# Run the scraper
uv run python scrape_cfsbk.py --output workouts.jsonl
```

Flags:
- `--per-page` (default 100): API page size (max WordPress allows).
- `--max-pages`: limit pages for quick tests.
- `--pause` (default 0.2): seconds to sleep between requests.

## Movement frequency visualization
After generating `movement_counts.csv` (from the analysis snippet), plot the top movements:
```bash
uv run python visualize_movements.py --input movement_counts.csv --top 20 --output movement_counts.png
```

## Named workouts (Heroes & Girls)
- The ETL emits `data/derived/named_workouts.json` capturing Hero WODs and Girl benchmarks (occurrences, counts, latest date/link, summaries).
- Matching uses workout titles and component headings (ignores “tomorrow”/promo components) with word-boundary regexes to avoid false positives.
- In the frontend, these appear as expandable cards with the workout text and clickable dates to the source blog posts.

## Tests
```bash
# Backend/tests
uv run pytest

# Frontend tests
cd frontend
npm test -- --run
```

## ETL pipeline
```bash
# Fetch latest posts and build canonical + aggregates
uv run python etl.py all

# (Optional) Fetch comment metadata and write comment analytics
uv run python etl.py build --with-comment-analysis
```
Artifacts land in `data/derived/`:
- `workouts.jsonl` (canonical with movements/format/component tags/seq_no)
- `top_movements.json`, `top_pairs.json`, `yearly_counts.json`, `weekday_counts.json`
- `movement_yearly.json`, `movement_weekday.json`, `movement_monthly.json`, `movement_calendar.json`
- `search_index.json`, `data_version.json`, and per-year `prescriptions/*.json` for the finder
- `comment_count` is included on each workout when running with `--with-comments` or `--with-comment-analysis` (hits the WP comments API)
- `comments_analysis.json` is written when running with `--with-comment-analysis` (monthly totals, most-commented posts, top commenters)

## Source review and historical tagging audit

The archive builds from WordPress text and reviewed selections in `config/workout_reviews.json`. To get model proposals for selected posts, use a model with Structured Outputs and an OpenAI API key.

```bash
uv run python scripts/propose_workout_reviews.py --model YOUR_MODEL --id 10754 --output proposals.json
```

Compare each proposal to its original post before copying it into the reviewed configuration. Use one record per post ID. Run `uv run python etl.py build` and sync the frontend after changes.

The previous tagging script and its saved outputs are available for comparison at `#/llm-audit`.

1) Provide an OpenAI key (either works):
```bash
export OPENAI_API_KEY="..."
```
or add it to `.env` (gitignored) as `OPENAI_API_KEY=...`.

2) Generate LLM tags for a date range (start small to control cost):
```bash
uv run python scripts/llm_tag_workouts.py --start-date 2016-01-01 --end-date 2016-01-31 --max-posts 50 --workers 4
```

This writes gitignored artifacts:
- `data/derived/llm_tags.jsonl` (append-only)
- `data/derived/llm_tags.json` (JSON array for the frontend)
- `data/llm_cache/` (per-post cached responses)

### Judge pass (second opinion)
You can optionally run a second-pass "judge" LLM that sees:
- The full blog post text
- The regex result (`data/derived/search_index.json`)
- The first-pass LLM result

By default it only judges posts where regex and first-pass LLM disagree (to control cost):
```bash
uv run python etl.py build
uv run python scripts/llm_tag_workouts.py --start-date 2016-01-01 --end-date 2016-01-31 --judge
```

Outputs (gitignored):
- `data/derived/llm_judged_tags.jsonl`
- `data/derived/llm_judged_tags.json`

### Saving historical audit results
The historical audit loads these files when present:
- `data/derived/llm_tags.json`
- `data/derived/llm_judged_tags.json`

(The per-post cache and `.jsonl` files remain gitignored.)

3) Sync derived data into the dev server and reload:
```bash
cd frontend
npm run sync-data
npm run dev
```

Then open the **LLM Tagging Audit** section to review differences between regex tags and LLM tags.

## Frontend (React/Vite)
Scaffold lives in `frontend/`.
```bash
cd frontend
npm install
npm run sync-data   # copies data/derived into public/data for local dev
npm run dev
```
