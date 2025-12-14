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

type HeroConfig = { name: string; aliases: RegExp[] };
const HERO_WORKOUTS: HeroConfig[] = [
  { name: "Murph", aliases: [/murph/i] },
  { name: "DT", aliases: [/^dt$/i, /\bdt\b/i] },
  { name: "Chad", aliases: [/chad\b/i, /1000\s*step-ups/i] },
  { name: "Holleyman", aliases: [/holleyman/i] },
  { name: "Badger", aliases: [/badger/i] },
  { name: "Nate", aliases: [/^nate$/i, /\bnate\b/i] },
  { name: "Randy", aliases: [/randy\b/i] },
  { name: "Griff", aliases: [/griff\b/i] },
  { name: "Hidalgo", aliases: [/hidalgo/i] },
  { name: "Jerry", aliases: [/jerry\b/i] },
  { name: "Bull", aliases: [/bull\b/i] },
  { name: "Glen", aliases: [/glen\b/i] },
  { name: "Josh", aliases: [/josh\b/i] },
  { name: "Michael", aliases: [/michael\b/i] },
  { name: "Whitten", aliases: [/whitten/i] },
  { name: "J.T.", aliases: [/^j\.?t\.?$/i, /\bj\.?t\.?\b/i] },
  { name: "Lumberjack 20", aliases: [/lumberjack\s*20/i] },
  { name: "Victoria", aliases: [/victoria\b/i] },
  { name: "McGhee", aliases: [/mcghee/i] },
  { name: "Abbate", aliases: [/abbate/i] },
  { name: "White", aliases: [/^white$/i, /\bwhite\b/i] },
  // Common benchmark often treated like a hero day at affiliates
  { name: "Grace", aliases: [/grace\b/i] },
];

function HeroWorkouts({ search }: { search: SearchItem[] }) {
  const heroes = useMemo(() => {
    const hits: { name: string; count: number; latestDate?: string; latestLink?: string }[] = [];
    HERO_WORKOUTS.forEach((hero) => {
      const matches = search.filter((w) => hero.aliases.some((r) => r.test(w.title)));
      if (!matches.length) return;
      const latest = matches.slice().sort((a, b) => (a.date > b.date ? -1 : 1))[0];
      hits.push({
        name: hero.name,
        count: matches.length,
        latestDate: latest.date,
        latestLink: latest.link,
      });
    });
    return hits.sort((a, b) => b.count - a.count || (b.latestDate || "").localeCompare(a.latestDate || ""));
  }, [search]);

  if (!heroes.length) return null;

  return (
    <div className="card hero-card">
      <div className="hero-card__header">
        <div>
          <h3 className="trend-title">Hero Workouts</h3>
          <p className="muted">Most common Hero WODs at CFSBK and the most recent time they were programmed.</p>
        </div>
      </div>
      <div className="hero-card__list">
        {heroes.map((h) => (
          <div key={h.name} className="hero-card__item">
            <div className="hero-card__name">{h.name}</div>
            <div className="hero-card__count">{h.count} runs</div>
            {h.latestDate && (
              <a className="hero-card__link" href={h.latestLink} target="_blank" rel="noreferrer">
                Last on {h.latestDate}
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function TopFiveTrends({ aggregates }: { aggregates: Aggregates }) {
  const years = useMemo(() => Object.keys(aggregates.yearly_counts).map(Number).sort((a, b) => a - b).map(String), [aggregates]);

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

  return (
    <div className="card trend-card">
      <div className="trend-header">
        <div>
          <h3 className="trend-title">Top 5 movements by year</h3>
          <p className="muted">Mobile-friendly cards show each year’s top five and how ranks changed vs. the prior year.</p>
        </div>
      </div>
      <div className="trend-cards">
        {years.map((year, idx) => {
          const entries = topByYear[year] || [];
          const prev = idx > 0 ? topByYear[years[idx - 1]] || [] : [];
          const prevRanks = new Map(prev.map((e) => [e.movement, e.rank]));
          return (
            <div key={year} className="trend-card__year">
              <div className="trend-card__year-header">
                <div className="trend-card__year-title">{year}</div>
                <div className="trend-card__year-sub">Top 5</div>
              </div>
              <ol className="trend-list">
                {entries.map((item) => {
                  const prevRank = prevRanks.get(item.movement);
                  const delta = prevRank ? prevRank - item.rank : null;
                  const trend =
                    delta === null ? "new" : delta > 0 ? `↑${delta}` : delta < 0 ? `↓${Math.abs(delta)}` : "•";
                  return (
                    <li key={item.movement} className="trend-list__item">
                      <span className={`trend-list__badge rank-${item.rank}`}>#{item.rank}</span>
                      <span className="trend-list__name">{item.movement}</span>
                      <span className="trend-list__trend">{trend}</span>
                    </li>
                  );
                })}
              </ol>
            </div>
          );
        })}
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

        <Section id="heroes" title="Hero Workouts">
          <HeroWorkouts search={searchIndex} />
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
