import { useMemo, useState } from "react";
import { loadPrescriptions } from "../dataLoader";
import type { Prescription, SearchItem } from "../types";

const PAGE_SIZE = 20;

export function QuickFinder({ search }: { search: SearchItem[] }) {
  const [query, setQuery] = useState("");
  const [year, setYear] = useState("");
  const [movement, setMovement] = useState("");
  const [format, setFormat] = useState("");
  const [scope, setScope] = useState("workouts");
  const [requestedPage, setPage] = useState(1);
  const [prescriptions, setPrescriptions] = useState<Record<string, Record<string, Prescription[]>>>({});
  const [failed, setFailed] = useState<string[]>([]);

  const dates = useMemo(() => [...search].sort((a, b) => b.date.localeCompare(a.date) || b.id - a.id), [search]);
  const years = useMemo(() => [...new Set(dates.map((item) => item.date.slice(0, 4)))], [dates]);
  const movements = useMemo(() => [...new Set(search.flatMap((item) => item.movements))].sort(), [search]);
  const formats = useMemo(() => [...new Set(search.flatMap((item) => item.formats ?? (item.format ? [item.format] : [])))].sort(), [search]);
  const results = useMemo(() => {
    const terms = query.toLowerCase().trim().split(/\s+/).filter(Boolean);
    return dates.filter((item) => {
      if (scope === "workouts" && item.extraction_status && !["extracted", "reviewed"].includes(item.extraction_status)) return false;
      if (scope === "review" && item.extraction_status !== "needs_review") return false;
      if (year && !item.date.startsWith(year)) return false;
      if (movement && !item.movements.includes(movement)) return false;
      if (format && !(item.formats ?? [item.format]).includes(format)) return false;
      const haystack = [item.title, item.date, item.summary, ...item.movements, ...item.component_tags].join(" ").toLowerCase();
      return terms.every((term) => haystack.includes(term));
    });
  }, [dates, query, year, movement, format, scope]);

  const pageCount = Math.max(1, Math.ceil(results.length / PAGE_SIZE));
  const page = Math.min(requestedPage, pageCount);

  async function loadYear(entryYear: string) {
    if (prescriptions[entryYear]) return;
    setFailed((previous) => previous.filter((value) => value !== entryYear));
    try {
      const data = await loadPrescriptions(entryYear);
      setPrescriptions((previous) => ({ ...previous, [entryYear]: data }));
    } catch {
      setFailed((previous) => [...previous, entryYear]);
    }
  }

  return (
    <div className="finder">
      <label className="finder__field">
        Search the archive
        <input className="input" placeholder="Try Murph or 2025-06-14" value={query} onChange={(e) => { setQuery(e.target.value); setPage(1); }} />
      </label>
      <div className="finder__filters">
        <label className="finder__field">Year
          <select className="input" value={year} onChange={(e) => { setYear(e.target.value); setPage(1); }}>
            <option value="">All years</option>
            {years.map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label className="finder__field">Movement
          <select className="input" value={movement} onChange={(e) => { setMovement(e.target.value); setPage(1); }}>
            <option value="">All movements</option>
            {movements.map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label className="finder__field">Format
          <select className="input" value={format} onChange={(e) => { setFormat(e.target.value); setPage(1); }}>
            <option value="">All formats</option>
            {formats.map((value) => <option key={value} value={value}>{["amrap", "emom"].includes(value) ? value.toUpperCase() : value}</option>)}
          </select>
        </label>
        <label className="finder__field">Show
          <select className="input" value={scope} onChange={(e) => { setScope(e.target.value); setPage(1); }}>
            <option value="workouts">Indexed workouts</option>
            <option value="review">Needs review</option>
            <option value="all">All posts</option>
          </select>
        </label>
      </div>
      <div className="muted" role="status">{results.length.toLocaleString()} {results.length === 1 ? "result" : "results"}</div>
      <div className="finder__list">
        {results.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE).map((item) => {
          const entryYear = item.date.slice(0, 4);
          const entries = prescriptions[entryYear]?.[item.id];
          const hasPrescription = item.workout_no != null || Boolean(item.summary && item.extraction_status === "needs_review");
          return (
            <details key={item.id} className="finder__item" onToggle={(event) => {
              if (event.currentTarget.open && hasPrescription) void loadYear(entryYear);
            }}>
              <summary>
                <span className="finder__title">{item.title}</span>
                <span className="muted finder__meta">
                  {item.date}{item.movements.length ? ` · ${item.movements.slice(0, 4).join(", ")}` : ""}
                  {item.extraction_status === "needs_review" ? " · Needs review" : ""}
                </span>
              </summary>
              <div className="finder__details">
                {entries?.map((entry, i) => (
                  <section key={i}>
                    <h3>{entry.component}</h3>
                    <p className="finder__prescription">{entry.details}</p>
                    {entry.notes && <details className="finder__notes">
                      <summary>Coaching notes and scaling</summary>
                      <p className="finder__prescription">{entry.notes}</p>
                    </details>}
                  </section>
                ))}
                {!entries && (failed.includes(entryYear)
                  ? <div><p>{item.summary || "Workout text could not be loaded."}</p><button type="button" className="btn btn--ghost" onClick={() => void loadYear(entryYear)}>Retry</button></div>
                  : hasPrescription && <p>{prescriptions[entryYear] ? item.summary || "Workout text unavailable." : "Loading workout…"}</p>)}
                <a href={item.link} target="_blank" rel="noreferrer">Read the original post</a>
              </div>
            </details>
          );
        })}
      </div>
      {pageCount > 1 && <div className="finder__pages">
        <button type="button" className="btn btn--ghost" onClick={() => setPage(page - 1)} disabled={page === 1}>Previous</button>
        <span>Page {page} of {pageCount}</span>
        <button type="button" className="btn btn--ghost" onClick={() => setPage(page + 1)} disabled={page === pageCount}>Next</button>
      </div>}
    </div>
  );
}
