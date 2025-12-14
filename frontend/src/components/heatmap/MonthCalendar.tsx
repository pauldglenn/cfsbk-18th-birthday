import { useState } from "react";

import type { MovementDayEntry } from "../../types";
import { positionTooltip } from "./positionTooltip";

type Tooltip = { text: string; x: number; y: number };
type CalendarCell = { day?: number; entry?: MovementDayEntry; filler?: boolean };

export function MonthCalendar({ year, monthIdx, entries }: { year: string; monthIdx: number; entries: MovementDayEntry[] }) {
  const daysInMonth = new Date(Number(year), monthIdx + 1, 0).getDate();
  const offset = new Date(Number(year), monthIdx, 1).getDay();
  const byDay = new Map(entries.map((e) => [e.day, e]));
  const [tooltip, setTooltip] = useState<Tooltip | null>(null);

  const cells: CalendarCell[] = [];
  for (let i = 0; i < offset; i++) cells.push({ filler: true });
  for (let d = 1; d <= daysInMonth; d++) {
    cells.push({ day: d, entry: byDay.get(d) });
  }

  return (
    <div className="calendar-wrapper">
      <div className="calendar">
        {cells.map((cell, idx) => {
          if (cell.filler) return <div key={idx} className="calendar-cell calendar-cell--filler" />;
          const entry = cell.entry;
          const text = entry ? `${entry.date} — ${entry.title}\n${entry.summary}` : "";
          return (
            <button
              key={idx}
              className={`calendar-cell ${entry ? "calendar-cell--hit" : ""}`}
              onMouseEnter={(e) => {
                if (!entry) return;
                setTooltip(positionTooltip(e, text));
              }}
              onMouseMove={(e) => {
                if (!entry) return;
                setTooltip(positionTooltip(e, text));
              }}
              onMouseLeave={() => setTooltip(null)}
              onClick={() => {
                if (entry?.link) window.open(entry.link, "_blank", "noopener");
              }}
            >
              <div className="calendar-day">{cell.day}</div>
            </button>
          );
        })}
      </div>
      {tooltip && (
        <div className="tooltip" style={{ top: tooltip.y, left: tooltip.x }}>
          {tooltip.text.split("\n").map((line, i) => (
            <div key={i}>{line}</div>
          ))}
        </div>
      )}
    </div>
  );
}

