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

## ETL pipeline
```bash
# Fetch latest posts and build canonical + aggregates
uv run python etl.py all
```
Artifacts land in `data/derived/`:
- `workouts.jsonl` (canonical with movements/format/component tags/seq_no)
- `top_movements.json`, `top_pairs.json`, `yearly_counts.json`, `weekday_counts.json`
- `movement_yearly.json`, `movement_weekday.json`, `movement_monthly.json`, `movement_calendar.json`
- `search_index.json`, `data_version.json`
- `comment_count` is included on each workout (fetched via the WP comments API)

## Frontend (React/Vite)
Scaffold lives in `frontend/`.
```bash
cd frontend
npm install
npm run sync-data   # copies data/derived into public/data for local dev
npm run dev
```
