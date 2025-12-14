import { useMemo } from "react";

import type { Aggregates } from "../types";

type Padding = { top: number; right: number; bottom: number; left: number };

const COLORS = [
  "#22d3ee",
  "#60a5fa",
  "#a78bfa",
  "#f472b6",
  "#fb7185",
  "#fbbf24",
  "#34d399",
  "#38bdf8",
  "#fda4af",
  "#c4b5fd",
];

function clamp(n: number, min: number, max: number) {
  return Math.max(min, Math.min(max, n));
}

export function MovementBumpChart({
  aggregates,
  movements,
  topN = 10,
}: {
  aggregates: Aggregates;
  movements: string[];
  topN?: number;
}) {
  const years = useMemo(
    () => Object.keys(aggregates.yearly_counts).map(Number).sort((a, b) => a - b).map(String),
    [aggregates.yearly_counts],
  );

  const ranks = useMemo(() => {
    const rankByYear: Record<string, Map<string, number>> = {};
    const countByYear: Record<string, Map<string, number>> = {};
    const movementYearly = aggregates.movement_yearly;

    years.forEach((year) => {
      const entries: { movement: string; count: number }[] = [];
      Object.entries(movementYearly).forEach(([movement, counts]) => {
        const c = counts[year] || 0;
        if (c) entries.push({ movement, count: c });
      });
      entries.sort((a, b) => b.count - a.count || a.movement.localeCompare(b.movement));

      const rankMap = new Map<string, number>();
      const countMap = new Map<string, number>();
      entries.forEach((e, idx) => {
        rankMap.set(e.movement, idx + 1);
        countMap.set(e.movement, e.count);
      });
      rankByYear[year] = rankMap;
      countByYear[year] = countMap;
    });

    return { rankByYear, countByYear };
  }, [aggregates.movement_yearly, years]);

  const chart = useMemo(() => {
    const padding: Padding = { top: 16, right: 16, bottom: 26, left: 44 };
    const height = 260;
    const stepX = 40;
    const width = padding.left + padding.right + stepX * Math.max(0, years.length - 1);
    const innerW = Math.max(1, width - padding.left - padding.right);
    const innerH = Math.max(1, height - padding.top - padding.bottom);

    const xForYearIndex = (idx: number) => padding.left + (idx / Math.max(1, years.length - 1)) * innerW;
    const yForRank = (rank: number) => padding.top + ((rank - 1) / Math.max(1, topN - 1)) * innerH;

    const movementLines = movements.map((movement, idx) => {
      const color = COLORS[idx % COLORS.length];
      const points = years.map((year, yearIdx) => {
        const rank = ranks.rankByYear[year]?.get(movement);
        if (!rank || rank > topN) return null;
        const count = ranks.countByYear[year]?.get(movement) || 0;
        return {
          year,
          rank,
          count,
          x: xForYearIndex(yearIdx),
          y: yForRank(rank),
        };
      });

      const segments: string[] = [];
      let d = "";
      points.forEach((p) => {
        if (!p) {
          if (d) segments.push(d);
          d = "";
          return;
        }
        d = d ? `${d} L ${p.x.toFixed(2)} ${p.y.toFixed(2)}` : `M ${p.x.toFixed(2)} ${p.y.toFixed(2)}`;
      });
      if (d) segments.push(d);

      return { movement, color, points, segments };
    });

    const yearTicks = years.map((y, idx) => ({ year: y, x: xForYearIndex(idx) }));
    const rankTicks = Array.from({ length: topN }, (_, i) => i + 1).map((r) => ({ rank: r, y: yForRank(r) }));

    return { padding, width, height, yearTicks, rankTicks, movementLines };
  }, [movements, ranks, topN, years]);

  const svgWidth = clamp(chart.width, 520, 1200);

  return (
    <div className="bump">
      <div className="bump__header">
        <h4 className="bump__title">Top 10 rank over time</h4>
        <div className="muted bump__sub">Ranks are shown only in years where a movement is in that year’s top 10.</div>
      </div>
      <div className="bump__scroll" role="img" aria-label="Bump chart for top movements by year">
        <svg className="bump__svg" viewBox={`0 0 ${svgWidth} ${chart.height}`} preserveAspectRatio="xMidYMid meet">
          <g className="bump__grid">
            {chart.rankTicks.map((t) => (
              <g key={t.rank}>
                <line x1={chart.padding.left} y1={t.y} x2={svgWidth - chart.padding.right} y2={t.y} />
                <text x={chart.padding.left - 10} y={t.y + 4} textAnchor="end">
                  {t.rank}
                </text>
              </g>
            ))}
          </g>

          <g className="bump__x">
            {chart.yearTicks.map((t, idx) => {
              const isLabel = years.length <= 12 || idx % 2 === 0 || idx === years.length - 1;
              return (
                <g key={t.year}>
                  <line x1={t.x} y1={chart.padding.top} x2={t.x} y2={chart.height - chart.padding.bottom} />
                  {isLabel && (
                    <text x={t.x} y={chart.height - 8} textAnchor="middle">
                      {t.year}
                    </text>
                  )}
                </g>
              );
            })}
          </g>

          <g className="bump__lines">
            {chart.movementLines.map((line) => (
              <g key={line.movement}>
                {line.segments.map((d, idx) => (
                  <path key={idx} d={d} stroke={line.color} />
                ))}
                {line.points.map((p, idx) =>
                  p ? <circle key={`${line.movement}-${idx}`} cx={p.x} cy={p.y} r={3.5} fill={line.color} /> : null,
                )}
              </g>
            ))}
          </g>
        </svg>
      </div>
      <div className="bump__legend" aria-label="Legend">
        {chart.movementLines.map((l) => (
          <div key={l.movement} className="bump__legend-item">
            <span className="bump__swatch" style={{ background: l.color }} aria-hidden="true" />
            <span className="bump__legend-name">{l.movement}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
