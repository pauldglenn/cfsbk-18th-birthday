import { useEffect, useMemo, useState } from "react";
import "./App.css";
import { loadDataBundle } from "./dataLoader";
import type { Aggregates, SearchItem } from "./types";

type Status = "idle" | "loading" | "ready" | "error";

function numberWithCommas(n: number | string) {
  return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

function Section({ id, title, children }: { id: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="section">
      <div className="section__header">
        <h2>{title}</h2>
        <a href={`#${id}`} className="section__anchor">
          #
        </a>
      </div>
      <div className="section__body">{children}</div>
    </section>
  );
}

function Milestones({ total }: { total: number }) {
  const milestones = [1000, 2500, 5000, total].filter((n, i, arr) => arr.indexOf(n) === i);
  return (
    <div className="pill-row">
      {milestones.map((m) => (
        <span key={m} className="pill">
          {m === total ? `Latest (#${m})` : `${numberWithCommas(m)}th`}
        </span>
      ))}
    </div>
  );
}

function TopMovements({ aggregates }: { aggregates: Aggregates }) {
  const top20 = aggregates.top_movements.slice(0, 20);
  const max = Math.max(...top20.map((m) => m.days));
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <>
      <div className="bars">
        {top20.map((m) => {
          const active = selected === m.movement;
          return (
            <div key={m.movement} className="bar-item">
              <button
                className={`bar-row ${active ? "bar-row--active" : ""}`}
                onClick={() => setSelected(active ? null : m.movement)}
              >
                <div className="bar-label">{m.movement}</div>
                <div className="bar-track">
                  <div className="bar-fill" style={{ width: `${(m.days / max) * 100}%` }} />
                </div>
                <div className="bar-value">{numberWithCommas(m.days)}</div>
              </button>
              <div className={`bar-panel ${active ? "bar-panel--open" : ""}`}>
                {active && <MovementHeatmap movement={m.movement} aggregates={aggregates} inline />}
              </div>
            </div>
          );
        })}
      </div>
    </>
  );
}

function TopPairs({ aggregates }: { aggregates: Aggregates }) {
  const top20 = aggregates.top_pairs.slice(0, 20);
  return (
    <div className="grid">
      {top20.map((p, idx) => (
        <div key={`${p.a}-${p.b}-${idx}`} className="chip-row">
          <span className="chip">{p.a}</span>
          <span className="chip">{p.b}</span>
          <span className="muted">{numberWithCommas(p.count)} days</span>
        </div>
      ))}
    </div>
  );
}

function TopFiveTrends({ aggregates }: { aggregates: Aggregates }) {
  const years = useMemo(() => Object.keys(aggregates.yearly_counts).map(Number).sort((a, b) => a - b).map(String), [aggregates]);
  const [sortYear, setSortYear] = useState<string | null>(null);

  const topByYear = useMemo(() => {
    const movementYearly = aggregates.movement_yearly;
    const map: Record<string, { movement: string; count: number; rank: number }[]> = {};
    years.forEach((year) => {
      const entries: { movement: string; count: number }[] = [];
      Object.entries(movementYearly).forEach(([movement, counts]) => {
        const c = counts[year];
        if (c) entries.push({ movement, count: c });
      });
      entries.sort((a, b) => b.count - a.count || a.movement.localeCompare(b.movement));
      map[year] = entries.slice(0, 5).map((item, idx) => ({ ...item, rank: idx + 1 }));
    });
    return map;
  }, [aggregates.movement_yearly, years]);

  const allMovements = useMemo(() => {
    const seen = new Set<string>();
    const order: string[] = [];
    years.forEach((y) => {
      topByYear[y]?.forEach((entry) => {
        if (!seen.has(entry.movement)) {
          seen.add(entry.movement);
          order.push(entry.movement);
        }
      });
    });
    return order;
  }, [topByYear, years]);

  const movementOrder = useMemo(() => {
    if (!sortYear || !topByYear[sortYear]) return allMovements;
    const ranks = new Map(topByYear[sortYear]!.map((t) => [t.movement, t.rank]));
    const fallbackOrder = new Map(allMovements.map((m, idx) => [m, idx]));
    return [...allMovements].sort((a, b) => {
      const ra = ranks.get(a) ?? 999;
      const rb = ranks.get(b) ?? 999;
      if (ra !== rb) return ra - rb;
      return (fallbackOrder.get(a) ?? 0) - (fallbackOrder.get(b) ?? 0);
    });
  }, [allMovements, sortYear, topByYear]);

  const rankColor = (rank: number) => {
    if (rank === 1) return "#2563eb";
    if (rank === 2) return "#1d4ed8";
    if (rank === 3) return "#0ea5e9";
    if (rank === 4) return "#22d3ee";
    if (rank === 5) return "#38bdf8";
    return "transparent";
  };

  return (
    <div className="card trend-card">
      <div className="trend-header">
        <div>
          <h3 className="trend-title">Top 5 movements by year</h3>
          <p className="muted">Ranks show when a movement cracks the top five. Scroll to spot who stayed popular.</p>
        </div>
        <div className="legend">
          {[1, 2, 3, 4, 5].map((r) => (
            <span key={r} className="legend__item">
              <span className="legend__swatch" style={{ background: rankColor(r) }} /> Rank {r}
            </span>
          ))}
        </div>
      </div>
      <div className="trend-table" role="table" aria-label="Top 5 movements by year">
        <div className="trend-row trend-row--header" role="row">
          <div className="trend-cell trend-cell--movement" role="columnheader">
            Movement
          </div>
          {years.map((y) => (
            <button
              key={y}
              className={`trend-cell trend-cell--header ${sortYear === y ? "trend-cell--active" : ""}`}
              role="columnheader"
              onClick={() => setSortYear(sortYear === y ? null : y)}
              title="Click to sort by this year's ranks"
            >
              {y}
            </button>
          ))}
        </div>
        {movementOrder.map((movement) => (
          <div key={movement} className="trend-row" role="row">
            <div className="trend-cell trend-cell--movement" role="rowheader">
              {movement}
            </div>
            {years.map((y) => {
              const rank = topByYear[y]?.find((t) => t.movement === movement)?.rank || 0;
              return (
                <div
                  key={`${movement}-${y}`}
                  className={`trend-cell ${rank ? "trend-cell--hit" : "trend-cell--miss"}`}
                  style={{ background: rank ? rankColor(rank) : undefined }}
                  role="cell"
                  title={rank ? `${movement} ranked #${rank} in ${y}` : `${movement} not in top 5 in ${y}`}
                >
                  {rank ? `#${rank}` : ""}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function QuickFinder({ search }: { search: SearchItem[] }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    if (!query.trim()) return search.slice(0, 20);
    const q = query.toLowerCase();
    return search.filter(
      (w) =>
        w.title.toLowerCase().includes(q) ||
        (w.movements || []).some((m) => m.toLowerCase().includes(q)) ||
        (w.component_tags || []).some((c) => c.toLowerCase().includes(q))
    );
  }, [query, search]);
  return (
    <div className="finder">
      <input
        className="input"
        placeholder="Search by title/movement/tag…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="finder__list">
        {filtered.slice(0, 30).map((item) => (
          <a key={item.id} href={item.link} target="_blank" rel="noreferrer" className="finder__item">
            <div>
              <div className="finder__title">{item.title}</div>
              <div className="muted">
                {item.date} · {(item.movements || []).slice(0, 3).join(", ")}
                {item.movements && item.movements.length > 3 ? "…" : ""}
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

function MovementHeatmap({
  movement,
  aggregates,
}: {
  movement: string;
  aggregates: Aggregates;
  inline?: boolean;
}) {
  const years = useMemo(() => Object.keys(aggregates.yearly_counts).sort(), [aggregates.yearly_counts]);
  const yearCounts = aggregates.movement_yearly[movement] || {};
  const values = years.map((y) => yearCounts[y] || 0);
  const max = Math.max(...values, 1);
  const [yearOpen, setYearOpen] = useState<string | null>(null);
  const [monthOpen, setMonthOpen] = useState<string | null>(null);

  const monthlyForYear = (year: string) => {
    const byYear = aggregates.movement_monthly[movement] || {};
    const months = byYear[year] || {};
    return Array.from({ length: 12 }, (_, i) => months[String(i + 1)] || 0);
  };

  const calendarEntriesForMonth = (year: string, monthIdx: number) => {
    const cal = aggregates.movement_calendar[movement] || {};
    const months = cal[year] || {};
    return months[String(monthIdx + 1)] || [];
  };

  return (
    <div>
      <div className="heatmap-header">
        <h3>{movement}</h3>
        <span className="muted">Occurrences by year</span>
      </div>
      <div className="heatmap">
        {years.map((y, idx) => {
          const val = values[idx];
          const intensity = Math.round((val / max) * 100);
          return (
            <button
              key={y}
              className={`heatmap-cell ${yearOpen === y ? "heatmap-cell--active" : ""}`}
              title={`${y}: ${val}`}
              onClick={() => {
                const next = yearOpen === y ? null : y;
                setYearOpen(next);
                setMonthOpen(null);
              }}
            >
              <div
                className="heatmap-block"
                style={{ background: `rgba(37, 99, 235, ${0.15 + intensity / 100 * 0.85})` }}
              />
              <div className="heatmap-year">{y}</div>
              <div className="heatmap-value">{val}</div>
            </button>
          );
        })}
      </div>
      {yearOpen && (
        <MonthlyHeatmap
          year={yearOpen}
          data={monthlyForYear(yearOpen)}
          onSelect={(idx) => setMonthOpen(monthOpen === String(idx) ? null : String(idx))}
          openMonth={monthOpen}
          monthEntries={(idx) => calendarEntriesForMonth(yearOpen, idx)}
        />
      )}
    </div>
  );
}

function MonthlyHeatmap({
  year,
  data,
  onSelect,
  openMonth,
  monthEntries,
}: {
  year: string;
  data: number[];
  onSelect: (idx: number) => void;
  openMonth: string | null;
  monthEntries: (idx: number) => { day: number; date: string; title: string; summary: string; link: string }[];
}) {
  const max = Math.max(...data, 1);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return (
    <div className="heatmap months">
      {data.map((val, idx) => {
        const intensity = Math.round((val / max) * 100);
        return (
          <div key={idx} className="month-block">
            <button
              className={`heatmap-cell ${openMonth === String(idx) ? "heatmap-cell--active" : ""}`}
              title={`${months[idx]} ${year}: ${val}`}
              onClick={() => onSelect(idx)}
            >
              <div
                className="heatmap-block"
                style={{ background: `rgba(37, 99, 235, ${0.15 + intensity / 100 * 0.85})` }}
              />
              <div className="heatmap-year">{months[idx]}</div>
              <div className="heatmap-value">{val}</div>
            </button>
            {openMonth === String(idx) && (
              <MonthCalendar year={year} monthIdx={idx} entries={monthEntries(idx)} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function MonthCalendar({
  year,
  monthIdx,
  entries,
}: {
  year: string;
  monthIdx: number;
  entries: { day: number; date: string; title: string; summary: string; link: string }[];
}) {
  const daysInMonth = new Date(Number(year), monthIdx + 1, 0).getDate();
  const offset = new Date(Number(year), monthIdx, 1).getDay();
  const byDay = new Map(entries.map((e) => [e.day, e]));
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null);

  const cells: { day?: number; entry?: any; filler?: boolean }[] = [];
  for (let i = 0; i < offset; i++) cells.push({ filler: true });
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({ day: d, entry: byDay.get(d) });
  }

  return (
    <div className="calendar-wrapper">
      <div className="calendar">
        {cells.map((cell, idx) => {
          if (cell.filler) return <div key={idx} className="calendar-cell calendar-cell--filler" />;
          const entry = cell.entry;
          const text = entry ? `${entry.date} — ${entry.title}\n${entry.summary}` : "";
          return (
            <button
              key={idx}
              className={`calendar-cell ${entry ? "calendar-cell--hit" : ""}`}
              onMouseEnter={(e) => {
                if (!entry) return;
                setTooltip(positionTooltip(e, text));
              }}
              onMouseMove={(e) => {
                if (!entry) return;
                setTooltip(positionTooltip(e, text));
              }}
              onMouseLeave={() => setTooltip(null)}
              onClick={() => {
                if (entry?.link) window.open(entry.link, "_blank", "noopener");
              }}
            >
              <div className="calendar-day">{cell.day}</div>
            </button>
          );
        })}
      </div>
      {tooltip && (
        <div className="tooltip" style={{ top: tooltip.y, left: tooltip.x }}>
          {tooltip.text.split("\n").map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      )}
    </div>
  );
}

function positionTooltip(
  e: React.MouseEvent<HTMLElement>,
  text: string
): { text: string; x: number; y: number } {
  const padding = 12;
  const estWidth = 260;
  const estHeight = 140;
  let x = e.clientX + padding;
  let y = e.clientY + padding;
  if (x + estWidth > window.innerWidth) {
    x = e.clientX - estWidth - padding;
  }
  if (y + estHeight > window.innerHeight) {
    y = e.clientY - estHeight - padding;
  }
  return { text, x, y };
}

function App() {
  const [status, setStatus] = useState<Status>("idle");
  const [aggregates, setAggregates] = useState<Aggregates | null>(null);
  const [searchIndex, setSearchIndex] = useState<SearchItem[]>([]);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    setStatus("loading");
    loadDataBundle()
      .then(({ aggregates, search }) => {
        setAggregates(aggregates);
        setSearchIndex(search);
        setStatus("ready");
      })
      .catch((err) => {
        setError(err.message || "Failed to load data");
        setStatus("error");
      });
  }, []);

  if (status === "loading") {
    return <div className="loading">Loading data…</div>;
  }
  if (status === "error") {
    return <div className="error">Error: {error}</div>;
  }
  if (!aggregates) return null;

  const total = Object.values(aggregates.yearly_counts).reduce((a, b) => a + b, 0);

  return (
    <div className="page">
      <div className="story-container">
        <header className="hero story-slide">
          <div className="hero__content">
            <p className="kicker">18 Years of CrossFit South Brooklyn</p>
            <h1>Cataloging Every Workout</h1>
            <p className="lead">
              From 2007 to today, thousands of strength days, metcons, partner throwdowns, and floater sessions have
              been programmed at CFSBK. This project brings them together so members can explore trends, milestones, and
              movement stories across the entire history.
            </p>
            <p className="muted">
              Scroll to explore: milestones, top movements, common pairings, and search across all {numberWithCommas(total)} workouts.
            </p>
            <Milestones total={total} />
          </div>
        </header>

        <Section id="movements" title="Top Movements">
          <p className="muted">Click a movement to expand its history by year.</p>
          <TopMovements aggregates={aggregates} />
        </Section>

        <Section id="top5-trends" title="Top 5: Then vs Now">
          <TopFiveTrends aggregates={aggregates} />
        </Section>

        <Section id="pairs" title="Top Pairs">
          <TopPairs aggregates={aggregates} />
        </Section>

        <Section id="finder" title="Quick Finder">
          <QuickFinder search={searchIndex} />
        </Section>
      </div>
    </div>
  );
}

export default App;
