import type { NamedWorkout } from "../types";

export function NamedWorkoutCard({ title, items }: { title: string; items: NamedWorkout[] | undefined }) {
  if (!items || !items.length) return null;
  return (
    <div className="card hero-card">
      <div className="hero-card__header">
        <div>
          <h3 className="trend-title">{title}</h3>
          <p className="muted">Tap to see the workout and when it was programmed.</p>
        </div>
      </div>
      <div className="hero-card__list">
        {items.map((h) => (
          <details key={h.name} className="hero-card__item">
            <summary className="hero-card__summary">
              <div className="hero-card__name">{h.name}</div>
              <div className="hero-card__count">{h.count} runs</div>
              {h.latest_date && <span className="hero-card__latest">Last on {h.latest_date}</span>}
            </summary>
            <div className="hero-card__body">
              {h.occurrences.length > 0 && (
                <div className="hero-card__workout">
                  <div className="muted">Workout</div>
                  <div>{h.occurrences[0].summary || "No summary available"}</div>
                </div>
              )}
              <div className="hero-card__dates">
                <div className="muted">Dates run</div>
                <div className="hero-card__chips">
                  {h.occurrences.map((occ, idx) => (
                    <a
                      key={`${occ.date}-${idx}`}
                      className="chip chip--ghost hero-card__date-link"
                      href={occ.link}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {occ.date}
                    </a>
                  ))}
                </div>
              </div>
              {h.latest_link && (
                <a className="hero-card__link" href={h.latest_link} target="_blank" rel="noreferrer">
                  View most recent post
                </a>
              )}
            </div>
          </details>
        ))}
      </div>
    </div>
  );
}

