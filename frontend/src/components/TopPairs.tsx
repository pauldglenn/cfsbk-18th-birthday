import { useMemo, useState } from "react";

import type { Aggregates, MovementDayEntry, Pair } from "../types";
import { numberWithCommas } from "../utils/format";

export function TopPairs({ aggregates }: { aggregates: Aggregates }) {
  const top20 = aggregates.top_pairs.slice(0, 20);
  const [openKey, setOpenKey] = useState<string | null>(null);

  const totalDays = useMemo(
    () => Object.values(aggregates.yearly_counts).reduce((a, b) => a + b, 0),
    [aggregates.yearly_counts]
  );

  const movementTotalDays = useMemo(() => {
    const cache = new Map<string, number>();
    return (movement: string) => {
      const cached = cache.get(movement);
      if (cached !== undefined) return cached;
      const yearly = aggregates.movement_yearly[movement] || {};
      const total = Object.values(yearly).reduce((a, b) => a + b, 0);
      cache.set(movement, total);
      return total;
    };
  }, [aggregates.movement_yearly]);

  const sharedByKey = useMemo(() => {
    const cache = new Map<string, MovementDayEntry[]>();

    const entriesForMovement = (movement: string): MovementDayEntry[] => {
      const cal = aggregates.movement_calendar[movement] || {};
      const out: MovementDayEntry[] = [];
      Object.values(cal).forEach((months) => {
        Object.values(months).forEach((entries) => out.push(...entries));
      });
      return out;
    };

    const sharedEntries = (pair: Pair): MovementDayEntry[] => {
      const aEntries = entriesForMovement(pair.a);
      const bEntries = entriesForMovement(pair.b);
      const byDate = new Map(aEntries.map((e) => [e.date, e]));
      const shared: MovementDayEntry[] = [];
      for (const e of bEntries) {
        const hit = byDate.get(e.date);
        if (hit) shared.push(hit);
      }
      shared.sort((x, y) => (y.date || "").localeCompare(x.date || ""));
      return shared;
    };

    return {
      get(pair: Pair) {
        const key = `${pair.a}|||${pair.b}`;
        const existing = cache.get(key);
        if (existing) return existing;
        const computed = sharedEntries(pair);
        cache.set(key, computed);
        return computed;
      },
    };
  }, [aggregates.movement_calendar]);

  function pct(n: number, d: number) {
    if (!d) return "0%";
    return `${Math.round((n / d) * 100)}%`;
  }

  return (
    <div className="grid">
      {top20.map((p, idx) => {
        const key = `${p.a}|||${p.b}`;
        const open = openKey === key;
        const shared = open ? sharedByKey.get(p) : null;
        const aDays = movementTotalDays(p.a);
        const bDays = movementTotalDays(p.b);
        const together = shared?.length ?? 0;
        const jaccard = aDays + bDays - together > 0 ? pct(together, aDays + bDays - together) : "0%";
        return (
          <div key={`${p.a}-${p.b}-${idx}`} className="pair-item">
            <button type="button" className={`chip-row pair-row ${open ? "pair-row--open" : ""}`} onClick={() => setOpenKey(open ? null : key)}>
              <span className="chip">{p.a}</span>
              <span className="chip">{p.b}</span>
              <span className="muted">{numberWithCommas(p.count)} days</span>
              <span className="pair-row__chev">{open ? "▾" : "▸"}</span>
            </button>
            {open && shared && (
              <div className="pair-expander">
                <div className="pair-expander__meta muted">
                  {numberWithCommas(together)} days together · {numberWithCommas(aDays)} days with {p.a} · {numberWithCommas(bDays)} days with {p.b}
                  {" · "}
                  overlap: {pct(together, aDays)} of {p.a}, {pct(together, bDays)} of {p.b} · jaccard {jaccard}
                  {totalDays ? ` · across ${numberWithCommas(totalDays)} total days` : ""}
                </div>
                <div className="pair-expander__list">
                  {shared.slice(0, 60).map((e, i) => (
                    <a key={`${e.date}-${e.link}-${i}`} className="pair-expander__item" href={e.link} target="_blank" rel="noreferrer">
                      <span className="pair-expander__date">{e.date}</span>
                      <span className="pair-expander__title">{e.title}</span>
                    </a>
                  ))}
                </div>
                {shared.length > 60 && <div className="muted">Showing 60 most recent.</div>}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
