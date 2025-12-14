import { numberWithCommas } from "../utils/format";

import type { SearchItem } from "../types";

export function Milestones({ total, search }: { total: number; search: SearchItem[] }) {
  const targets = [1000, 2500, 5000, total].filter((n, i, arr) => arr.indexOf(n) === i);

  const bySeqNo = new Map<number, SearchItem>();
  for (const item of search) {
    if (typeof item.seq_no === "number") bySeqNo.set(item.seq_no, item);
  }

  return (
    <div className="pill-row">
      {targets.map((m) => {
        const entry = bySeqNo.get(m);
        const label = m === total ? `Latest (#${m})` : `${numberWithCommas(m)}th`;
        if (!entry?.link) {
          return (
            <span key={m} className="pill">
              {label}
            </span>
          );
        }
        return (
          <a key={m} className="pill pill--clickable" href={entry.link} target="_blank" rel="noreferrer" title={entry.title}>
            {label}
          </a>
        );
      })}
    </div>
  );
}
