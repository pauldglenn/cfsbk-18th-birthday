import { useMemo, useState } from "react";

import type { CommentsAnalysis } from "../types";
import { numberWithCommas } from "../utils/format";

type HoverPoint = { month: string; count: number; x: number; y: number } | null;

export function CommentsAnalysisCard({ analysis }: { analysis: CommentsAnalysis | null }) {
  if (!analysis) {
    return (
      <div className="card comments-card">
        <div className="comments-card__header">
          <div>
            <h3 className="trend-title">Comments</h3>
            <p className="muted">Comment analytics aren’t available yet. Run `uv run python etl.py build --with-comment-analysis`.</p>
          </div>
        </div>
      </div>
    );
  }

  const { monthly, top_commenters, total_comments } = analysis;

  const chart = useMemo(() => {
    const width = 900;
    const height = 160;
    const padding = { left: 24, right: 12, top: 12, bottom: 22 };
    const innerW = width - padding.left - padding.right;
    const innerH = height - padding.top - padding.bottom;

    const values = monthly.map((m) => m.count);
    const max = Math.max(...values, 1);
    const xFor = (i: number) => padding.left + (i / Math.max(monthly.length - 1, 1)) * innerW;
    const yFor = (v: number) => padding.top + (1 - v / max) * innerH;

    const path = monthly
      .map((m, i) => `${i === 0 ? "M" : "L"} ${xFor(i).toFixed(2)} ${yFor(m.count).toFixed(2)}`)
      .join(" ");

    return { width, height, padding, innerW, innerH, max, xFor, yFor, path };
  }, [monthly]);

  const [hover, setHover] = useState<HoverPoint>(null);

  return (
    <div className="card comments-card">
      <div className="comments-card__header">
        <div>
          <h3 className="trend-title">Comments</h3>
          <p className="muted">{numberWithCommas(total_comments)} total comments across the full history.</p>
        </div>
      </div>

      <div className="comments-card__grid">
        <div className="comments-card__panel">
          <div className="comments-card__panel-title">Monthly comment volume</div>
          <div className="comments-chart">
            <svg
              className="comments-chart__svg"
              viewBox={`0 0 ${chart.width} ${chart.height}`}
              preserveAspectRatio="none"
              onMouseLeave={() => setHover(null)}
              onMouseMove={(e) => {
                const rect = (e.currentTarget as SVGSVGElement).getBoundingClientRect();
                const x = e.clientX - rect.left;
                const rel = (x / rect.width) * chart.width;
                const i = Math.max(
                  0,
                  Math.min(
                    monthly.length - 1,
                    Math.round(((rel - chart.padding.left) / chart.innerW) * (monthly.length - 1))
                  )
                );
                const m = monthly[i];
                if (!m) return;
                setHover({ month: m.month, count: m.count, x: chart.xFor(i), y: chart.yFor(m.count) });
              }}
            >
              <path className="comments-chart__path" d={chart.path} />
              {hover && (
                <>
                  <circle className="comments-chart__dot" cx={hover.x} cy={hover.y} r={4} />
                  <line
                    className="comments-chart__vline"
                    x1={hover.x}
                    x2={hover.x}
                    y1={chart.padding.top}
                    y2={chart.height - chart.padding.bottom}
                  />
                </>
              )}
            </svg>
            {hover && (
              <div className="comments-chart__hover">
                <span className="chip chip--ghost">{hover.month}</span>
                <span className="muted">{numberWithCommas(hover.count)} comments</span>
              </div>
            )}
          </div>
        </div>

        <div className="comments-card__panel">
          <div className="comments-card__panel-title">Top commenters</div>
          <div className="comments-leaderboard">
            {top_commenters.slice(0, 10).map((c, idx) => (
              <div key={`${c.name}-${idx}`} className="comments-leaderboard__row">
                <div className="comments-leaderboard__rank">#{idx + 1}</div>
                <div className="comments-leaderboard__main">
                  <div className="comments-leaderboard__name">{c.name}</div>
                  <div className="muted">{numberWithCommas(c.count)} comments</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
