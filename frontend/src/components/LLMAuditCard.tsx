import { useMemo, useState } from "react";

import type { LLMTag, SearchItem } from "../types";

type Mode = "llm" | "judge";

type Diff = {
  id: number;
  date: string;
  title: string;
  link: string;
  anyDiff: boolean;
  restMismatch: boolean;
  formatMismatch: boolean;
  missingInRegex: string[];
  extraInRegex: string[];
  missingTagsInRegex: string[];
  extraTagsInRegex: string[];
  selected: LLMTag;
  llm: LLMTag | null;
  judge: LLMTag | null;
  regex: SearchItem;
};

function setDiff(a: string[], b: string[]) {
  const as = new Set(a);
  const bs = new Set(b);
  const missing = Array.from(as).filter((x) => !bs.has(x)).sort();
  const extra = Array.from(bs).filter((x) => !as.has(x)).sort();
  return { missing, extra };
}

export function LLMAuditCard({
  llmTags,
  llmJudgedTags,
  search,
}: {
  llmTags: LLMTag[] | null;
  llmJudgedTags: LLMTag[] | null;
  search: SearchItem[];
}) {
  const [mode, setMode] = useState<Mode>(() => (llmJudgedTags ? "judge" : "llm"));
  const [onlyDiffs, setOnlyDiffs] = useState(true);
  const [q, setQ] = useState("");

  const { diffs, all, totals } = useMemo(() => {
    const byId = new Map<number, SearchItem>();
    for (const s of search) byId.set(s.id, s);

    const llmById = new Map<number, LLMTag>();
    for (const t of llmTags || []) {
      if (t.id != null) llmById.set(t.id, t);
    }

    const judgeById = new Map<number, LLMTag>();
    for (const t of llmJudgedTags || []) {
      if (t.id != null) judgeById.set(t.id, t);
    }

    const computedDiffs: Diff[] = [];
    const computedAll: Diff[] = [];
    let compared = 0;
    let exact = 0;
    let withDiff = 0;

    const selected = mode === "judge" ? llmJudgedTags : llmTags;

    for (const llm of selected || []) {
      if (llm.id == null) continue;
      const regex = byId.get(llm.id);
      if (!regex) continue;
      compared += 1;

      const regexRest = regex.workout_no == null;
      const restMismatch = llm.is_rest_day !== regexRest;
      const formatMismatch = (llm.format || "") !== (regex.format || "");

      const mov = setDiff(llm.movements || [], regex.movements || []);
      const tags = setDiff(llm.component_tags || [], regex.component_tags || []);

      const anyDiff =
        restMismatch || formatMismatch || mov.missing.length > 0 || mov.extra.length > 0 || tags.missing.length > 0 || tags.extra.length > 0;

      if (!anyDiff) exact += 1;
      else withDiff += 1;

      const item: Diff = {
        id: llm.id,
        date: llm.date || regex.date,
        title: llm.title || regex.title,
        link: llm.link || regex.link,
        anyDiff,
        restMismatch,
        formatMismatch,
        missingInRegex: mov.missing,
        extraInRegex: mov.extra,
        missingTagsInRegex: tags.missing,
        extraTagsInRegex: tags.extra,
        selected: llm,
        llm: llmById.get(llm.id) || null,
        judge: judgeById.get(llm.id) || null,
        regex,
      };

      computedAll.push(item);
      if (anyDiff) computedDiffs.push(item);
    }

    computedDiffs.sort((a, b) => a.date.localeCompare(b.date));
    computedAll.sort((a, b) => a.date.localeCompare(b.date));

    return { diffs: computedDiffs, all: computedAll, totals: { compared, exact, withDiff } };
  }, [llmTags, llmJudgedTags, mode, search]);

  const filtered = useMemo(() => {
    const query = q.trim().toLowerCase();
    let items = onlyDiffs ? diffs : all;
    if (query) {
      items = items.filter((d) => {
        const llmMovs = (d.llm?.movements || []).join(" ");
        const judgeMovs = (d.judge?.movements || []).join(" ");
        const hay = `${d.title} ${d.date} ${llmMovs} ${judgeMovs} ${(d.regex.movements || []).join(" ")}`.toLowerCase();
        return hay.includes(query);
      });
    }
    // Avoid rendering thousands of rows accidentally.
    if (!onlyDiffs && !query) return items.slice(-200);
    return items;
  }, [all, diffs, onlyDiffs, q]);

  const [open, setOpen] = useState<number | null>(null);

  const selected = mode === "judge" ? llmJudgedTags : llmTags;

  if (!selected) {
    return (
      <div className="card llm-audit">
        <h3 className="trend-title">LLM audit</h3>
        <p className="muted">
          {mode === "judge"
            ? "No judge tags found. Generate `data/derived/llm_judged_tags.json` by running `uv run python scripts/llm_tag_workouts.py --judge ...`, then run `cd frontend && npm run sync-data`."
            : "No LLM tags found. Generate `data/derived/llm_tags.json` via `scripts/llm_tag_workouts.py`, then run `cd frontend && npm run sync-data`."}
        </p>
      </div>
    );
  }

  return (
    <div className="card llm-audit">
      <div className="llm-audit__header">
        <div>
          <h3 className="trend-title">{mode === "judge" ? "Judge vs regex" : "LLM vs regex"}</h3>
          <p className="muted">
            Compared {totals.compared} posts · Exact matches {totals.exact} · Differences {totals.withDiff}
          </p>
        </div>
        <div className="llm-audit__controls">
          <div className="llm-audit__toggle">
            <button className={`btn btn--ghost ${mode === "llm" ? "is-active" : ""}`} onClick={() => setMode("llm")}>
              First-pass LLM
            </button>
            <button
              className={`btn btn--ghost ${mode === "judge" ? "is-active" : ""}`}
              onClick={() => setMode("judge")}
              disabled={!llmJudgedTags}
              title={!llmJudgedTags ? "Generate judge results to enable" : undefined}
            >
              Judge
            </button>
          </div>
          <label className="llm-audit__checkbox">
            <input type="checkbox" checked={onlyDiffs} onChange={(e) => setOnlyDiffs(e.target.checked)} />
            Show diffs only
          </label>
          <input
            className="llm-audit__search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Filter by date/title/movement…"
          />
        </div>
      </div>

      {filtered.length === 0 ? (
        <p className="muted">{onlyDiffs ? "No differences found for the current filter." : "No matches found for the current filter."}</p>
      ) : (
        <div className="llm-audit__list">
          {filtered.map((d) => {
            const isOpen = open === d.id;
            const movementDelta = d.missingInRegex.length + d.extraInRegex.length;
            const tagDelta = d.missingTagsInRegex.length + d.extraTagsInRegex.length;
            const flags = [
              d.restMismatch ? "rest" : null,
              d.formatMismatch ? "format" : null,
              movementDelta ? "movements" : null,
              tagDelta ? "tags" : null,
            ].filter(Boolean) as string[];

            return (
              <div key={d.id} className="llm-audit__row">
                <button className="llm-audit__row-btn" onClick={() => setOpen(isOpen ? null : d.id)}>
                  <div className="llm-audit__row-main">
                    <div className="llm-audit__row-title">
                      <span className="llm-audit__date">{d.date}</span>
                      <span className="llm-audit__title">{d.title}</span>
                    </div>
                    <div className="llm-audit__chips">
                      {flags.map((f) => (
                        <span key={f} className="chip chip--ghost">
                          {f}
                        </span>
                      ))}
                    </div>
                  </div>
                </button>

                {isOpen && (
                  <div className="llm-audit__details">
                    <div className="llm-audit__cols">
                      <div className="llm-audit__col">
                        <div className="llm-audit__col-title">Regex</div>
                        <div className="muted">format: {d.regex.format || "—"}</div>
                        <div className="llm-audit__pillset">
                          {(d.regex.movements || []).slice().sort().map((m) => (
                            <span key={m} className="chip">
                              {m}
                            </span>
                          ))}
                        </div>
                      </div>
                      {d.llm && (
                        <div className="llm-audit__col">
                          <div className="llm-audit__col-title">First-pass LLM</div>
                          <div className="muted">format: {d.llm.format || "—"}</div>
                          <div className="llm-audit__pillset">
                            {(d.llm.movements || []).slice().sort().map((m) => (
                              <span key={`llm:${m}`} className="chip">
                                {m}
                              </span>
                            ))}
                          </div>
                          {(d.llm.unmapped_movements || []).length > 0 && (
                            <div className="muted">Unmapped: {d.llm.unmapped_movements.join(", ")}</div>
                          )}
                          {d.llm.notes && <div className="muted">Notes: {d.llm.notes}</div>}
                        </div>
                      )}
                      {d.judge && (
                        <div className="llm-audit__col">
                          <div className="llm-audit__col-title">Judge</div>
                          <div className="muted">format: {d.judge.format || "—"}</div>
                          <div className="llm-audit__pillset">
                            {(d.judge.movements || []).slice().sort().map((m) => (
                              <span key={`judge:${m}`} className="chip">
                                {m}
                              </span>
                            ))}
                          </div>
                          {(d.judge.unmapped_movements || []).length > 0 && (
                            <div className="muted">Unmapped: {d.judge.unmapped_movements.join(", ")}</div>
                          )}
                          {d.judge.notes && <div className="muted">Notes: {d.judge.notes}</div>}
                        </div>
                      )}
                    </div>

                    {(d.missingInRegex.length > 0 || d.extraInRegex.length > 0) && (
                      <div className="llm-audit__delta">
                        {d.missingInRegex.length > 0 && (
                          <div className="muted">Missing in regex: {d.missingInRegex.join(", ")}</div>
                        )}
                        {d.extraInRegex.length > 0 && <div className="muted">Extra in regex: {d.extraInRegex.join(", ")}</div>}
                      </div>
                    )}

                    <div className="llm-audit__links">
                      <a className="btn btn--ghost" href={d.link} target="_blank" rel="noreferrer">
                        Open blog post
                      </a>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
