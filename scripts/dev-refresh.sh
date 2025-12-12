#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Running ETL build..."
cd "$ROOT"
uv run python etl.py build

echo "Syncing data to frontend/public/data..."
cd "$ROOT/frontend"
npm run sync-data

echo "Starting Vite dev server..."
npm run dev
