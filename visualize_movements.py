"""
Create a bar chart of movement frequency from movement_counts.csv.

Usage:
    uv run python visualize_movements.py --input movement_counts.csv --top 20 --output movement_counts.png
"""

import argparse
import csv
from pathlib import Path

import matplotlib.pyplot as plt


def load_counts(path: Path) -> list[tuple[str, int]]:
    rows: list[tuple[str, int]] = []
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                count = int(row["days"])
            except (KeyError, ValueError):
                continue
            rows.append((row["movement"], count))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Visualize movement frequencies.")
    parser.add_argument("--input", default="movement_counts.csv", help="Path to CSV from analyzer.")
    parser.add_argument("--output", default="movement_counts.png", help="Path to save the chart PNG.")
    parser.add_argument("--top", type=int, default=20, help="Number of top movements to display.")
    args = parser.parse_args()

    rows = load_counts(Path(args.input))
    if not rows:
        raise SystemExit(f"No data found in {args.input}")

    rows = sorted(rows, key=lambda x: x[1], reverse=True)[: args.top]
    labels, counts = zip(*rows)

    plt.figure(figsize=(10, 6))
    bars = plt.barh(range(len(counts)), counts, color="#4c72b0")
    plt.gca().invert_yaxis()
    plt.xlabel("Days programmed")
    plt.title(f"Top {len(labels)} movements by day count")
    plt.yticks(range(len(labels)), labels)

    for bar, count in zip(bars, counts):
        plt.text(count + max(counts) * 0.01, bar.get_y() + bar.get_height() / 2, str(count), va="center")

    plt.tight_layout()
    plt.savefig(args.output, dpi=200)
    print(f"Saved chart to {args.output}")


if __name__ == "__main__":
    main()
