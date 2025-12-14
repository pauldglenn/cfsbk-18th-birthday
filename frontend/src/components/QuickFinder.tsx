import { useMemo, useState } from "react";

import type { SearchItem } from "../types";

export function QuickFinder({ search }: { search: SearchItem[] }) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    if (!query.trim()) return search.slice(0, 20);
    const q = query.toLowerCase();
    return search.filter(
      (w) =>
        w.title.toLowerCase().includes(q) ||
        (w.movements || []).some((m) => m.toLowerCase().includes(q)) ||
        (w.component_tags || []).some((c) => c.toLowerCase().includes(q))
    );
  }, [query, search]);
  return (
    <div className="finder">
      <input
        className="input"
        placeholder="Search by title/movement/tag…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="finder__list">
        {filtered.slice(0, 30).map((item) => (
          <a key={item.id} href={item.link} target="_blank" rel="noreferrer" className="finder__item">
            <div>
              <div className="finder__title">{item.title}</div>
              <div className="muted">
                {item.date} · {(item.movements || []).slice(0, 3).join(", ")}
                {item.movements && item.movements.length > 3 ? "…" : ""}
              </div>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}

