import { useState } from "react";

import type { Aggregates } from "../types";
import { numberWithCommas } from "../utils/format";
import { MovementHeatmap } from "./heatmap/MovementHeatmap";

export function TopMovements({ aggregates }: { aggregates: Aggregates }) {
  const top20 = aggregates.top_movements.slice(0, 20);
  const max = Math.max(...top20.map((m) => m.days));
  const [selected, setSelected] = useState<string | null>(null);
  return (
    <div className="bars">
      {top20.map((m) => {
        const active = selected === m.movement;
        return (
          <div key={m.movement} className="bar-item">
            <button className={`bar-row ${active ? "bar-row--active" : ""}`} onClick={() => setSelected(active ? null : m.movement)}>
              <div className="bar-label">{m.movement}</div>
              <div className="bar-track">
                <div className="bar-fill" style={{ width: `${(m.days / max) * 100}%` }} />
              </div>
              <div className="bar-value">{numberWithCommas(m.days)}</div>
            </button>
            <div className={`bar-panel ${active ? "bar-panel--open" : ""}`}>{active && <MovementHeatmap movement={m.movement} aggregates={aggregates} />}</div>
          </div>
        );
      })}
    </div>
  );
}
