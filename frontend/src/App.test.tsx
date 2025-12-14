import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import App from "./App";

const mockAggregates = {
  top_movements: [
    { movement: "run", days: 5 },
    { movement: "pull-up", days: 3 },
  ],
  top_pairs: [],
  yearly_counts: { "2025": 2 },
  weekday_counts: {},
  movement_yearly: { run: { "2025": 2 } },
  movement_weekday: {},
  movement_monthly: { run: { "2025": { "11": 1 } } },
  movement_calendar: {
    run: {
      "2025": {
        "11": [
          { day: 8, date: "2025-11-08", title: "Saturday 11.8.25", summary: "Run 400m", link: "http://example.com" },
        ],
      },
    },
  },
};

const mockSearch = [
  {
    id: 1,
    seq_no: 2,
    workout_no: 2,
    milestones: ["2th workout"],
    date: "2025-11-08",
    title: "Saturday 11.8.25",
    link: "http://example.com",
    movements: ["run"],
    component_tags: ["conditioning"],
    format: "for time",
    cycle_info: [],
  },
];

const mockNamed = {
  heroes: [],
  girls: [],
};

const mockCommentsAnalysis = {
  generated_at: "2025-12-14T00:00:00Z",
  total_comments: 3,
  monthly: [
    { month: "2025-10", count: 1 },
    { month: "2025-11", count: 2 },
  ],
  top_posts: [
    {
      id: 1,
      date: "2025-11-08",
      title: "Saturday 11.8.25",
      link: "http://example.com",
      comment_count: 2,
      summary: "Run 400m",
    },
  ],
  top_commenters: [
    { name: "Pat", count: 2 },
  ],
};

describe("App scrollytelling interactions", () => {
  let fetchSpy: any;

  beforeEach(() => {
    fetchSpy = vi.spyOn(global, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      const body =
        url.includes("top_movements") ? mockAggregates.top_movements :
        url.includes("top_pairs") ? mockAggregates.top_pairs :
        url.includes("yearly_counts") ? mockAggregates.yearly_counts :
        url.includes("weekday_counts") ? mockAggregates.weekday_counts :
        url.includes("movement_yearly") ? mockAggregates.movement_yearly :
        url.includes("movement_weekday") ? mockAggregates.movement_weekday :
        url.includes("movement_monthly") ? mockAggregates.movement_monthly :
        url.includes("movement_calendar") ? mockAggregates.movement_calendar :
        url.includes("search_index") ? mockSearch :
        url.includes("named_workouts") ? mockNamed :
        url.includes("comments_analysis") ? mockCommentsAnalysis :
        [];
      return {
        ok: true,
        headers: { get: () => "application/json" },
        json: async () => body,
      } as unknown as Response;
    });
  });

  afterEach(() => {
    fetchSpy.mockRestore();
  });

  it("expands movement -> year -> month -> calendar", async () => {
    render(<App />);

    await waitFor(() => expect(screen.getByText(/cataloging every workout/i)).toBeInTheDocument());

    const bar = (await screen.findAllByRole("button", { name: /run/i }))[0];
    fireEvent.click(bar);

    const yearButton = await screen.findByTitle(/2025:/);
    fireEvent.click(yearButton);

    const monthCell = await screen.findByText("Nov");
    fireEvent.click(monthCell);

    const dayCell = await screen.findByText("8");
    expect(dayCell).toBeInTheDocument();
  });
});
