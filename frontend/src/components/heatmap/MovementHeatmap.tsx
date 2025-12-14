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
                style={{ background: `rgba(37, 99, 235, ${0.15 + (intensity / 100) * 0.85})` }}
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

