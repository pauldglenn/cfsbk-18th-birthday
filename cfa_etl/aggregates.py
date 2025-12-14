from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List

from .movements import extract_rep_scheme


def _itertools_pairs(seq: List[str]):
    import itertools

    return itertools.combinations(seq, 2)


def aggregate(canonical: List[Dict]) -> Dict[str, Dict]:
    movements_days = Counter()
    movement_pairs = Counter()
    yearly_counts = Counter()
    weekday_counts = Counter()
    movement_yearly = defaultdict(lambda: Counter())
    movement_weekday = defaultdict(lambda: Counter())
    movement_monthly = defaultdict(lambda: defaultdict(Counter))
    movement_calendar = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for item in canonical:
        date = item.get("date") or ""
        if date:
            yearly_counts[date[:4]] += 1
            try:
                dt_obj = datetime.fromisoformat(date)
                weekday = dt_obj.strftime("%A")
                weekday_counts[weekday] += 1
            except Exception:
                pass

        movs = set(item.get("movements") or [])
        rep_summary = extract_rep_scheme(item.get("components") or [])

        for m in movs:
            movements_days[m] += 1
            if date:
                movement_yearly[m][date[:4]] += 1
                try:
                    dt_obj = datetime.fromisoformat(date)
                    weekday = dt_obj.strftime("%A")
                    movement_weekday[m][weekday] += 1
                    movement_monthly[m][dt_obj.year][dt_obj.month] += 1
                    movement_calendar[m][dt_obj.year][dt_obj.month].append(
                        {
                            "day": dt_obj.day,
                            "date": date,
                            "title": item.get("title"),
                            "summary": rep_summary,
                            "link": item.get("link"),
                        }
                    )
                except Exception:
                    pass

        for a, b in _itertools_pairs(sorted(movs)):
            movement_pairs[(a, b)] += 1

    top_movements = movements_days.most_common(100)
    top_pairs = [
        {"a": a, "b": b, "count": cnt} for (a, b), cnt in movement_pairs.most_common(200)
    ]

    return {
        "top_movements": [{"movement": m, "days": d} for m, d in top_movements],
        "top_pairs": top_pairs,
        "yearly_counts": dict(yearly_counts),
        "weekday_counts": dict(weekday_counts),
        "movement_yearly": {m: dict(c) for m, c in movement_yearly.items()},
        "movement_weekday": {m: dict(c) for m, c in movement_weekday.items()},
        "movement_monthly": {
            m: {
                str(y): {str(mon): count for mon, count in months.items()}
                for y, months in years.items()
            }
            for m, years in movement_monthly.items()
        },
        "movement_calendar": {
            m: {str(y): {str(mon): entries for mon, entries in months.items()} for y, months in years.items()}
            for m, years in movement_calendar.items()
        },
    }

