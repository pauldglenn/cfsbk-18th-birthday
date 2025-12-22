import { useEffect, useState } from "react";
import "./App.css";
import { loadDataBundle } from "./dataLoader";
import type { Aggregates, SearchItem, NamedWorkouts, CommentsAnalysis, LLMTag } from "./types";
import { Milestones } from "./components/Milestones";
import { CommentsAnalysisCard } from "./components/CommentsAnalysisCard";
import { LLMAuditCard } from "./components/LLMAuditCard";
import { NamedWorkoutCard } from "./components/NamedWorkoutCard";
import { QuickFinder } from "./components/QuickFinder";
import { Section } from "./components/Section";
import { TopFiveTrends } from "./components/TopFiveTrends";
import { TopMovements } from "./components/TopMovements";
import { TopPairs } from "./components/TopPairs";
import { numberWithCommas } from "./utils/format";

type Status = "idle" | "loading" | "ready" | "error";

function useHashRoute() {
  const [hash, setHash] = useState(() => window.location.hash || "");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  if (hash.startsWith("#/")) return hash.slice(2) || "";
  return "";
}

function App() {
  const route = useHashRoute();
  const [status, setStatus] = useState<Status>("idle");
  const [aggregates, setAggregates] = useState<Aggregates | null>(null);
  const [searchIndex, setSearchIndex] = useState<SearchItem[]>([]);
  const [namedWorkouts, setNamedWorkouts] = useState<NamedWorkouts | null>(null);
  const [commentsAnalysis, setCommentsAnalysis] = useState<CommentsAnalysis | null>(null);
  const [llmTags, setLlmTags] = useState<LLMTag[] | null>(null);
  const [llmJudgedTags, setLlmJudgedTags] = useState<LLMTag[] | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    setStatus("loading");
    loadDataBundle()
      .then(({ aggregates, search, namedWorkouts, commentsAnalysis, llmTags, llmJudgedTags }) => {
        setAggregates(aggregates);
        setSearchIndex(search);
        setNamedWorkouts(namedWorkouts);
        setCommentsAnalysis(commentsAnalysis);
        setLlmTags(llmTags);
        setLlmJudgedTags(llmJudgedTags);
        setStatus("ready");
      })
      .catch((err) => {
        setError(err.message || "Failed to load data");
        setStatus("error");
      });
  }, []);

  if (status === "loading") {
    return <div className="loading">Loading data…</div>;
  }
  if (status === "error") {
    return <div className="error">Error: {error}</div>;
  }
  if (!aggregates || !namedWorkouts) return null;

  const total = Math.max(0, ...searchIndex.map((s) => (typeof s.workout_no === "number" ? s.workout_no : 0)));

  if (route === "llm-audit") {
    return (
      <div className="page">
        <div className="audit-page">
          <div className="audit-page__header">
            <div>
              <p className="kicker">Audit</p>
              <h1>LLM vs Regex</h1>
              <p className="muted">Compare first-pass LLM tags and/or judge-reviewed tags against the regex-based pipeline.</p>
            </div>
            <a className="btn btn--ghost" href="#movements">
              Back to story
            </a>
          </div>
          <LLMAuditCard llmTags={llmTags} llmJudgedTags={llmJudgedTags} search={searchIndex} />
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="story-container">
        <header className="hero story-slide">
          <div className="hero__content">
            <p className="kicker">18 Years of CrossFit South Brooklyn</p>
            <h1>Cataloging Every Workout</h1>
            <p className="lead">
              From 2007 to today, thousands of strength days, metcons, partner throwdowns, and floater sessions have
              been programmed at CFSBK. This project brings them together so members can explore trends, milestones, and
              movement stories across the entire history.
            </p>
            <p className="muted">
              Scroll to explore: milestones, top movements, common pairings, and search across all {numberWithCommas(total)} workouts.
            </p>
            <Milestones total={total} search={searchIndex} />
            <div className="hero__cta">
              <a className="btn btn--ghost" href="#/llm-audit">
                LLM audit
              </a>
            </div>
          </div>
        </header>

        <Section id="movements" title="Top Movements">
          <p className="muted">Click a movement to expand its history by year.</p>
          <TopMovements aggregates={aggregates} />
        </Section>

        <Section id="top5-trends" title="Top 5: Then vs Now">
          <TopFiveTrends aggregates={aggregates} />
        </Section>

        <Section id="heroes" title="Hero Workouts">
          <NamedWorkoutCard title="Hero Workouts" items={namedWorkouts.heroes} />
        </Section>

        <Section id="girls" title="The Girls">
          <NamedWorkoutCard title="The Girls" items={namedWorkouts.girls} />
        </Section>

        <Section id="pairs" title="Top Pairs">
          <TopPairs aggregates={aggregates} />
        </Section>

        <Section id="comments" title="Comments">
          <CommentsAnalysisCard analysis={commentsAnalysis} />
        </Section>

        <Section id="finder" title="Quick Finder">
          <QuickFinder search={searchIndex} />
        </Section>
      </div>
    </div>
  );
}

export default App;
