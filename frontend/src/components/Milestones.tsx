import { numberWithCommas } from "../utils/format";

export function Milestones({ total }: { total: number }) {
  const milestones = [1000, 2500, 5000, total].filter((n, i, arr) => arr.indexOf(n) === i);
  return (
    <div className="pill-row">
      {milestones.map((m) => (
        <span key={m} className="pill">
          {m === total ? `Latest (#${m})` : `${numberWithCommas(m)}th`}
        </span>
      ))}
    </div>
  );
}

