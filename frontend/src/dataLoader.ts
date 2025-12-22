import type { Aggregates, SearchItem, NamedWorkouts, CommentsAnalysis, LLMTag, MovementDayEntry } from "./types";

const BASE = `${import.meta.env.BASE_URL}data/derived`;

const WEEKDAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"] as const;

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) {
    throw new Error(`Failed to fetch ${path}: ${res.status}`);
  }
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    // Vite dev server can return index.html (200) for missing assets; surface a clearer error.
    const text = await res.text();
    throw new Error(`Expected JSON from ${path} but got ${contentType}: ${text.slice(0, 120)}`);
  }
  return res.json();
}

async function fetchJsonOptional<T>(path: string): Promise<T | null> {
  const res = await fetch(path);
  if (!res.ok) {
    if (res.status === 404) return null;
    throw new Error(`Failed to fetch ${path}: ${res.status}`);
  }
  const contentType = res.headers.get("content-type") || "";
  if (!contentType.includes("application/json")) {
    return null;
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

export async function loadCommentsAnalysis(): Promise<CommentsAnalysis | null> {
  return fetchJsonOptional(`${BASE}/comments_analysis.json`);
}

export async function loadLLMTags(): Promise<LLMTag[] | null> {
  return fetchJsonOptional(`${BASE}/llm_tags.json`);
}

export async function loadLLMJudgedTags(): Promise<LLMTag[] | null> {
  return fetchJsonOptional(`${BASE}/llm_judged_tags.json`);
}

function mergeTagsIntoSearch(search: SearchItem[], llmTags: LLMTag[] | null, llmJudgedTags: LLMTag[] | null): SearchItem[] {
  const llmById = new Map<number, LLMTag>();
  for (const t of llmTags || []) {
    if (t.id != null) llmById.set(t.id, t);
  }
  const judgeById = new Map<number, LLMTag>();
  for (const t of llmJudgedTags || []) {
    if (t.id != null) judgeById.set(t.id, t);
  }

  return search.map((s) => {
    const override = judgeById.get(s.id) ?? llmById.get(s.id);
    if (!override) return s;
    return {
      ...s,
      movements: override.movements || [],
      component_tags: override.component_tags || [],
      format: override.format || "",
    };
  });
}

function computeAggregatesFromSearch(search: SearchItem[]): Aggregates {
  const yearly_counts: Record<string, number> = {};
  const weekday_counts: Record<string, number> = {};
  const movement_yearly: Record<string, Record<string, number>> = {};
  const movement_weekday: Record<string, Record<string, number>> = {};
  const movement_monthly: Record<string, Record<string, Record<string, number>>> = {};
  const movement_calendar: Record<string, Record<string, Record<string, MovementDayEntry[]>>> = {};

  const movementTotals = new Map<string, number>();
  const pairCounts = new Map<string, number>();

  for (const item of search) {
    if (typeof item.workout_no !== "number") continue;
    const date = item.date;
    const [yearStr, monthStr, dayStr] = date.split("-");
    if (!yearStr || !monthStr || !dayStr) continue;
    const year = String(Number(yearStr));
    const month = String(Number(monthStr));
    const day = Number(dayStr);

    yearly_counts[year] = (yearly_counts[year] || 0) + 1;

    const dow = new Date(`${date}T00:00:00Z`).getUTCDay();
    const weekday = WEEKDAYS[dow] || "Monday";
    weekday_counts[weekday] = (weekday_counts[weekday] || 0) + 1;

    const movements = Array.from(new Set(item.movements || [])).filter(Boolean).sort();
    for (const m of movements) {
      movementTotals.set(m, (movementTotals.get(m) || 0) + 1);

      if (!movement_yearly[m]) movement_yearly[m] = {};
      movement_yearly[m][year] = (movement_yearly[m][year] || 0) + 1;

      if (!movement_weekday[m]) movement_weekday[m] = {};
      movement_weekday[m][weekday] = (movement_weekday[m][weekday] || 0) + 1;

      if (!movement_monthly[m]) movement_monthly[m] = {};
      if (!movement_monthly[m][year]) movement_monthly[m][year] = {};
      movement_monthly[m][year][month] = (movement_monthly[m][year][month] || 0) + 1;

      if (!movement_calendar[m]) movement_calendar[m] = {};
      if (!movement_calendar[m][year]) movement_calendar[m][year] = {};
      if (!movement_calendar[m][year][month]) movement_calendar[m][year][month] = [];
      movement_calendar[m][year][month].push({ day, date, title: item.title, summary: item.summary || "", link: item.link });
    }

    for (let i = 0; i < movements.length; i++) {
      for (let j = i + 1; j < movements.length; j++) {
        const a = movements[i];
        const b = movements[j];
        const key = `${a}|||${b}`;
        pairCounts.set(key, (pairCounts.get(key) || 0) + 1);
      }
    }
  }

  // Sort calendar entries within each month.
  for (const movement of Object.keys(movement_calendar)) {
    const byYear = movement_calendar[movement];
    for (const y of Object.keys(byYear)) {
      const byMonth = byYear[y];
      for (const m of Object.keys(byMonth)) {
        byMonth[m].sort((a, b) => (a.date || "").localeCompare(b.date || ""));
      }
    }
  }

  const top_movements = Array.from(movementTotals.entries())
    .map(([movement, days]) => ({ movement, days }))
    .sort((a, b) => b.days - a.days || a.movement.localeCompare(b.movement));

  const top_pairs = Array.from(pairCounts.entries())
    .map(([key, count]) => {
      const [a, b] = key.split("|||");
      return { a, b, count };
    })
    .sort((a, b) => b.count - a.count || a.a.localeCompare(b.a) || a.b.localeCompare(b.b));

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

export async function loadDataBundle() {
  const [search, namedWorkouts, commentsAnalysis, llmTags, llmJudgedTags] = await Promise.all([
    loadSearchIndex(),
    loadNamedWorkouts(),
    loadCommentsAnalysis(),
    loadLLMTags(),
    loadLLMJudgedTags(),
  ]);

  const hasOverrides = (llmJudgedTags && llmJudgedTags.length > 0) || (llmTags && llmTags.length > 0);
  if (hasOverrides) {
    const mergedSearch = mergeTagsIntoSearch(search, llmTags, llmJudgedTags);
    const aggregates = computeAggregatesFromSearch(mergedSearch);
    return { aggregates, search: mergedSearch, namedWorkouts, commentsAnalysis, llmTags, llmJudgedTags };
  }

  const aggregates = await loadAggregates();
  return { aggregates, search, namedWorkouts, commentsAnalysis, llmTags, llmJudgedTags };
}
