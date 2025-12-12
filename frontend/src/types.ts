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
  date: string;
  title: string;
  link: string;
  movements: string[];
  component_tags: string[];
  format: string;
  cycle_info: string[];
};

export type DataBundle = {
  version: string;
  aggregates: Aggregates;
  search: SearchItem[];
};
