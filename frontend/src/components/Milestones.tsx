import { useState } from "react";

import { numberWithCommas } from "../utils/format";

import type { SearchItem } from "../types";

export function Milestones({ total, search }: { total: number; search: SearchItem[] }) {
  const targets = [1, 500, 1000, 2500, 5000, total].filter((n, i, arr) => arr.indexOf(n) === i);

  const byWorkoutNo = new Map<number, SearchItem>();
  for (const item of search) {
    if (typeof item.workout_no === "number") byWorkoutNo.set(item.workout_no, item);
  }

  const [open, setOpen] = useState<number | null>(null);
  const openEntry = open ? byWorkoutNo.get(open) : null;

  return (
    <div className="milestones">
      <div className="pill-row">
        {targets.map((m) => {
          const entry = byWorkoutNo.get(m);
          const label = m === total ? `Latest (#${m})` : ordinal(m);
          const disabled = !entry;
          const active = open === m;
          return (
            <button
              key={m}
              type="button"
              className={`pill pill--clickable ${active ? "pill--active" : ""}`}
              disabled={disabled}
              onClick={() => setOpen(active ? null : m)}
              title={disabled ? "No workout found" : entry?.title}
            >
              {label}
            </button>
          );
        })}
      </div>

      {openEntry && (
        <div className="milestone-expander">
          <div className="milestone-expander__header">
            <div>
              <div className="milestone-expander__title">{openEntry.title}</div>
              <div className="muted">{openEntry.date}</div>
            </div>
            <a className="btn btn--ghost" href={openEntry.link} target="_blank" rel="noreferrer">
              Open blog post
            </a>
          </div>
          {openEntry.summary && <div className="milestone-expander__summary">{openEntry.summary}</div>}
          {openEntry.movements?.length ? (
            <div className="milestone-expander__chips">
              {openEntry.movements.slice(0, 8).map((m) => (
                <span key={m} className="chip">
                  {m}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

function ordinal(n: number) {
  const mod100 = n % 100;
  if (mod100 >= 11 && mod100 <= 13) return `${numberWithCommas(n)}th`;
  switch (n % 10) {
    case 1:
      return `${numberWithCommas(n)}st`;
    case 2:
      return `${numberWithCommas(n)}nd`;
    case 3:
      return `${numberWithCommas(n)}rd`;
    default:
      return `${numberWithCommas(n)}th`;
  }
}
