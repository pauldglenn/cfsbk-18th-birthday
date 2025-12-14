import type { Aggregates, SearchItem, NamedWorkouts } from "./types";

const BASE = `${import.meta.env.BASE_URL}data/derived`;

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
      fetchJson<Aggregates["top_movements"]>(`${BASE}/top_movements.json`),
      fetchJson<Aggregates["top_pairs"]>(`${BASE}/top_pairs.json`),
      fetchJson<Aggregates["yearly_counts"]>(`${BASE}/yearly_counts.json`),
      fetchJson<Aggregates["weekday_counts"]>(`${BASE}/weekday_counts.json`),
      fetchJson<Aggregates["movement_yearly"]>(`${BASE}/movement_yearly.json`),
      fetchJson<Aggregates["movement_weekday"]>(`${BASE}/movement_weekday.json`),
      // movement_monthly loaded separately below
    ]);
  const [movement_monthly, movement_calendar] = await Promise.all([
    fetchJson<Aggregates["movement_monthly"]>(`${BASE}/movement_monthly.json`),
    fetchJson<Aggregates["movement_calendar"]>(`${BASE}/movement_calendar.json`),
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

export async function loadNamedWorkouts(): Promise<NamedWorkouts> {
  return fetchJson(`${BASE}/named_workouts.json`);
}

export async function loadDataBundle() {
  const [aggregates, search, namedWorkouts] = await Promise.all([
    loadAggregates(),
    loadSearchIndex(),
    loadNamedWorkouts(),
  ]);
  return { aggregates, search, namedWorkouts };
}
