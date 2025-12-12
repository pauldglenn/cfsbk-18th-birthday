# Crossfit Workouts Explorer – Implementation Plan

## Objectives
- Maintain a canonical, improvable dataset of all gym workouts (18+ years), with provenance and incremental updates.
- Produce UI-ready aggregates for an interactive React SPA with scrollytelling sections (movements, pairings, milestones, patterns).
- Keep the pipeline configurable (movement patterns, component tags), testable, and cheap to refresh.

## Data Pipeline
1) **Source & Ingestion**
   - Fetch via WP API (category=Workout of the Day). Support incremental fetch using `last_fetched_at`/`max_date`.
   - Persist raw responses (`data/raw/posts-YYYYMMDD.jsonl`) for auditing.
2) **Parsing & Canonical Model**
   - Parse HTML to components; fallback to whole-body capture for old posts.
   - Derive fields: `seq_no` (global ordering), `year`, `weekday`, `cycle_info`, `component_tags` (strength/conditioning/assistance/partner), `format` (AMRAP/For Time/EMOM/Interval).
   - Normalize movements via configurable patterns (YAML/JSON). Record `matched_text`, `pattern_id` for debugging.
3) **Derived Artifacts**
   - `workouts.jsonl` (canonical with derived fields).
   - `workouts.parquet` for analysis (optional).
   - UI bundles (JSON): `top_movements.json`, `pairings.json`, `yearly_counts.json`, `weekday_counts.json`, `milestones.json`, `formats.json`, `movement_trends.json`, `cooccurrence_top.json`, `search_index.json` (slimmed fields for search).
   - `data_version.json` with checksum/timestamp for cache-busting.
4) **Milestones**
   - Sort by date, assign `seq_no`; flag milestone indices (e.g., 1000th, 2500th, 5000th, latest).
5) **Quality & Tests**
   - Unit tests for parser, movement normalization, and format detection.
   - Regression checks (counts per year, % with movements, co-occurrence sanity) to catch parsing drift.

## Backend/ETL Implementation Steps
- Add `data/` layout:
  - `data/raw/` for ingested posts.
  - `data/derived/` for canonical/aggregates.
  - `config/movements.yml` for patterns/synonyms.
- Implement `etl.py` (uv runnable):
  - Commands: `fetch` (incremental), `build` (parse + derive + aggregates), `all` (fetch+build).
  - Shared helpers for movement tagging, format detection, milestone computation.
  - Emit `data_version.json`.
- Scripts:
  - `analyze_movements.py` (reuse current logic, pull from canonical).
  - `analyze_pairs.py` for co-occurrence bundles.
  - Keep `visualize_movements.py` for ad hoc plotting.

## Frontend (React/Vite/TS) Plan
- Stack: Vite + React + TypeScript; charts with `visx` or `nivo`; state via context/zustand; routing with hash/scroll anchors.
- Data loading: small boot JSON (`data_version.json` + `yearly_counts`) then lazy-load per-section bundles. Cache in browser and invalidate on version change.
- Sections (vertical scrollytelling):
  1. Overview: totals, span, sparkline per year, milestone callouts.
  2. Milestones timeline: clickable cards for 1k/2.5k/5k/etc.
  3. Movement frequency explorer: bar/treemap with year/weekday filter; trend sparkline on hover.
  4. Co-occurrence heatmap: top-N pairs; burpee-focused toggle.
  5. Patterns over time: line/area for selected movements and formats (AMRAP/For Time/EMOM).
  6. Workout finder: filters (movement include/exclude, partner/solo, format), virtualized results, deep link to blog post.
  7. Cycles/phases: display `(WKx/y)` density and calendar snippets.
  8. Format types: chips for AMRAP/For Time/EMOM/Interval with examples.
- Interactions: hover tooltips, brushing/zoom on heatmap, drill-down click to filtered list, per-section hash links, and skeleton loading states.
- Theming/layout: sticky section headers, responsive (mobile/desktop), code-splitting by section.

## Deliverables (initial milestone)
- `etl.py` with fetch/build/all commands and movement/config support.
- `config/movements.yml` with starter patterns.
- Derived outputs in `data/derived/` (canonical + aggregates + data_version.json).
- Frontend scaffold (`frontend/` via Vite + React + TS) with section stubs and data loader utilities.
- README updates for pipeline + frontend usage.
