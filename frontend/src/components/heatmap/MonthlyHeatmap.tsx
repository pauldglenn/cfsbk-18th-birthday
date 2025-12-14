import type { MovementDayEntry } from "../../types";
import { MonthCalendar } from "./MonthCalendar";

export function MonthlyHeatmap({
  year,
  data,
  onSelect,
  openMonth,
  monthEntries,
}: {
  year: string;
  data: number[];
  onSelect: (idx: number) => void;
  openMonth: string | null;
  monthEntries: (idx: number) => MovementDayEntry[];
}) {
  const max = Math.max(...data, 1);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return (
    <div className="heatmap months">
      {data.map((val, idx) => {
        const intensity = Math.round((val / max) * 100);
        return (
          <div key={idx} className="month-block">
            <button
              className={`heatmap-cell ${openMonth === String(idx) ? "heatmap-cell--active" : ""}`}
              title={`${months[idx]} ${year}: ${val}`}
              onClick={() => onSelect(idx)}
            >
              <div
                className="heatmap-block"
                style={{ background: `rgba(37, 99, 235, ${0.15 + (intensity / 100) * 0.85})` }}
              />
              <div className="heatmap-year">{months[idx]}</div>
              <div className="heatmap-value">{val}</div>
            </button>
            {openMonth === String(idx) && <MonthCalendar year={year} monthIdx={idx} entries={monthEntries(idx)} />}
          </div>
        );
      })}
    </div>
  );
}

