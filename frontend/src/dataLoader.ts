import type { Aggregates, SearchItem } from "./types";

const BASE = "/data/derived";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${path}: ${res.status}`);
  }
  return res.json();
}

export async function loadAggregates(): Promise<Aggregates> {
  const [top_movements, top_pairs, yearly_counts, weekday_counts, movement_yearly, movement_weekday] =
    await Promise.all([
      fetchJson(`${BASE}/top_movements.json`),
      fetchJson(`${BASE}/top_pairs.json`),
      fetchJson(`${BASE}/yearly_counts.json`),
      fetchJson(`${BASE}/weekday_counts.json`),
      fetchJson(`${BASE}/movement_yearly.json`),
      fetchJson(`${BASE}/movement_weekday.json`),
      // movement_monthly loaded separately below
    ]);
  const [movement_monthly, movement_calendar] = await Promise.all([
    fetchJson<Record<string, Record<string, Record<string, number>>>>(`${BASE}/movement_monthly.json`),
    fetchJson<Record<string, Record<string, Record<string, any>>>>(`${BASE}/movement_calendar.json`),
  ]);
  return {
    top_movements,
    top_pairs,
    yearly_counts,
    weekday_counts,
    movement_yearly,
    movement_weekday,
    movement_monthly,
    movement_calendar,
  };
}

export async function loadSearchIndex(): Promise<SearchItem[]> {
  return fetchJson(`${BASE}/search_index.json`);
}

export async function loadDataBundle() {
  const [aggregates, search] = await Promise.all([loadAggregates(), loadSearchIndex()]);
  return { aggregates, search };
}
