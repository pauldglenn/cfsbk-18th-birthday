# Developer Notes: Data + Frontend Pipeline

## ETL (Python / uv)
- Entry script: `etl.py`
  - `fetch [--max-pages N]`: Hit WP posts API (category 1), write `data/raw/posts-<timestamp>.jsonl`; CI copies latest to `data/raw/latest.jsonl`.
  - `build [--with-comments]`: Parse `data/raw/latest.jsonl` (or newest posts-*.jsonl) into canonical records (`data/derived/workouts.jsonl`) and aggregates in `data/derived/`. Comment counts optional via WP comments API.
  - `all [--max-pages N] [--with-comments]`: Fetch + build in one shot.
- Movement tagging: uses `config/movements.yml` regex patterns. `movement_text_from_components` filters promos/trivia/future mentions but includes titles. Rest-day heuristic skips movements.
- Cached raw: `.gitignore` ignores `data/raw/posts-*.jsonl` but tracks `data/raw/latest.jsonl` for builds without hitting the API. `data-refresh.yml` fetches and commits both `latest.jsonl` and `data/derived/`.

## Backend Tests
- Run: `uv run pytest`
- Location: `tests/test_scrape.py`
- Coverage: date derivation, rep-scheme extraction, movement text filtering (future notes, promos), fallback parsing, and regression cases (e.g., kettlebell swings present; deadlift not from promos; burpees not from “tomorrow” notes).

## Frontend (Vite/React/TS)
- Data loading: fetches from `import.meta.env.BASE_URL + "data/derived/*"` (Pages base-aware).
- Sync data: `npm run sync-data` copies `data/derived/` into `frontend/public/data`.
- Vite config: `base: "/cfsbk-18th-birthday/"`.
- Tests: `npm test -- --run` (Vitest + jsdom). Config in `frontend/vitest.config.ts`, setup in `frontend/src/setupTests.ts`.
- Pre-push hook: `.githooks/pre-push` runs `uv run pytest` and `npm test -- --run` (configured via `core.hooksPath .githooks`).

## CI/CD
- `ci.yml`: backend pytest + frontend vitest on push/PR to `main`.
- `data-refresh.yml`: scheduled/dispatch; runs `etl.py fetch`, copies newest raw to `latest.jsonl`, then `etl.py build --with-comments`, commits `data/derived/` + `data/raw/latest.jsonl`.
- `gh-pages.yml`: builds frontend and deploys `frontend/dist` to GitHub Pages. (Currently includes ETL; can be switched to consume committed `data/derived/` when parsing stabilizes.)

## Common Commands
- Local parse only (no API): `uv run python etl.py build`
- Full refresh (hits API): `uv run python etl.py all --with-comments`
- Frontend dev: `cd frontend && npm run sync-data && npm run dev`
- Frontend build: `cd frontend && npm run sync-data && npm run build`
- Backend tests: `uv run pytest`
- Frontend tests: `cd frontend && npm test -- --run`

## Regression Anchors (sampling)
- Kettlebell swings: e.g., 2025-07-15 should tag swings/run.
- Promo bleed: 2019-06-20 shouldn’t tag deadlift from Pull for Pride blurb.
- “Tomorrow” notes: avoid tagging burpees from future-note lines (e.g., floater strength notes).
- Cycle templates/promos: avoid tagging movements from training-cycle blocks.
