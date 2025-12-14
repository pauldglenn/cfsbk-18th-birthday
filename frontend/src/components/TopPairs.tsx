import type { Aggregates } from "../types";
import { numberWithCommas } from "../utils/format";

export function TopPairs({ aggregates }: { aggregates: Aggregates }) {
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

