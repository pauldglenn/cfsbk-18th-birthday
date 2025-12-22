export type MovementDay = { movement: string; days: number };
export type Pair = { a: string; b: string; count: number };

export type Aggregates = {
  top_movements: MovementDay[];
  top_pairs: Pair[];
  yearly_counts: Record<string, number>;
  weekday_counts: Record<string, number>;
  movement_yearly: Record<string, Record<string, number>>;
  movement_weekday: Record<string, Record<string, number>>;
  movement_monthly: Record<string, Record<string, Record<string, number>>>;
  movement_calendar: Record<string, Record<string, Record<string, MovementDayEntry[]>>>;
};

export type MovementDayEntry = { day: number; date: string; title: string; summary: string; link: string };

export type SearchItem = {
  id: number;
  seq_no?: number;
  workout_no?: number | null;
  milestones?: string[];
  date: string;
  title: string;
  link: string;
  summary?: string;
  movements: string[];
  component_tags: string[];
  format: string;
  cycle_info: string[];
};

export type NamedWorkoutOccurrence = { date: string; title: string; link: string; summary: string };
export type NamedWorkout = {
  name: string;
  count: number;
  latest_date?: string;
  latest_link?: string;
  occurrences: NamedWorkoutOccurrence[];
};

export type NamedWorkouts = {
  heroes: NamedWorkout[];
  girls: NamedWorkout[];
};

export type CommentsMonthlyPoint = { month: string; count: number };

export type MostCommentedPost = {
  id: number;
  date: string;
  title: string;
  link: string;
  comment_count: number;
  summary: string;
};

export type TopCommenter = {
  name: string;
  count: number;
};

export type CommentsAnalysis = {
  generated_at: string;
  total_comments: number;
  monthly: CommentsMonthlyPoint[];
  top_posts: MostCommentedPost[];
  top_commenters: TopCommenter[];
};

export type LLMTaggedComponent = { component: string; details: string };
export type LLMTag = {
  id: number | null;
  date: string | null;
  title: string;
  link: string;
  is_rest_day: boolean;
  components: LLMTaggedComponent[];
  component_tags: string[];
  format: string;
  movements: string[];
  unmapped_movements: string[];
  notes: string;
};

export type DataBundle = {
  version: string;
  aggregates: Aggregates;
  search: SearchItem[];
  namedWorkouts: NamedWorkouts;
  commentsAnalysis: CommentsAnalysis | null;
  llmTags?: LLMTag[] | null;
  llmJudgedTags?: LLMTag[] | null;
};
