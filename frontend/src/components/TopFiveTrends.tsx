import { useMemo } from "react";

import type { Aggregates } from "../types";

export function TopFiveTrends({ aggregates }: { aggregates: Aggregates }) {
  const years = useMemo(
    () => Object.keys(aggregates.yearly_counts).map(Number).sort((a, b) => a - b).map(String),
    [aggregates]
  );

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
          <p className="muted">
            Mobile-friendly cards show each year’s top five and how ranks changed vs. the prior year.
          </p>
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
                  const trend = delta === null ? "new" : delta > 0 ? `↑${delta}` : delta < 0 ? `↓${Math.abs(delta)}` : "•";
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

