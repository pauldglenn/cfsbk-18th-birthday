# CrossFit South Brooklyn Workout Scraper

Python helper that pulls the full history of CrossFit South Brooklyn "Workout of the Day" posts via the site's WordPress API and extracts the workout components (Strength, Assistance, Conditioning, etc.), the date, and any cycle markers like `(WK4/8)`.

## Plan
- Use the WordPress REST API (`wp-json/wp/v2/posts`) scoped to the `Workout of the Day` category (ID 1) to avoid brittle HTML pagination.
- Fetch posts in pages of up to 100 items, respecting the `X-WP-TotalPages` header and pausing slightly between requests.
- Parse each post's rendered HTML with BeautifulSoup; find the `Workout of the Day` heading and capture subsequent component headings (h3–h6) and their text until the next heading.
- Detect cycle information with regex patterns such as `(WK4/8)` or `(Week 6/8)` and include it on every record.
- Emit newline-delimited JSON so the data can be transformed later into a richer model.

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
- `search_index.json`, `data_version.json`
- `comment_count` is included on each workout when running with `--with-comments` or `--with-comment-analysis` (hits the WP comments API)
- `comments_analysis.json` is written when running with `--with-comment-analysis` (monthly totals, most-commented posts, top commenters)

## LLM tagging (audit mode)
The regex-based tagger is the source of truth for the site. For auditing, you can generate a second set of tags using an LLM and compare them in the frontend.

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

### Deploying LLM results
If you don’t want to re-run LLM tagging in prod, commit these to the repo after generating them locally:
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
