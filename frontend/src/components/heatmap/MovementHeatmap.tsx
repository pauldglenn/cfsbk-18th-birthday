import { useMemo, useState } from "react";

import type { Aggregates, MovementDayEntry } from "../../types";
import { MonthlyHeatmap } from "./MonthlyHeatmap";

export function MovementHeatmap({ movement, aggregates }: { movement: string; aggregates: Aggregates; inline?: boolean }) {
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

  const calendarEntriesForMonth = (year: string, monthIdx: number): MovementDayEntry[] => {
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
      <div className="year-chart" role="list" aria-label="Yearly history">
        {years.map((y, idx) => {
          const val = values[idx];
          const pct = Math.max(0, Math.min(100, (val / max) * 100));
          const active = yearOpen === y;
          return (
            <button
              key={y}
              type="button"
              role="listitem"
              className={`year-chart__item ${active ? "year-chart__item--active" : ""}`}
              title={`${y}: ${val}`}
              onClick={() => {
                const next = active ? null : y;
                setYearOpen(next);
                setMonthOpen(null);
              }}
            >
              <div className="year-chart__bar-wrap" aria-hidden="true">
                <div className="year-chart__bar" style={{ height: `${pct}%` }} />
              </div>
              <div className="year-chart__year">{y}</div>
              <div className="year-chart__value">{val}</div>
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
