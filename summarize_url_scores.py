#!/usr/bin/env python3
import csv
import json
import re
from pathlib import Path

WORK_DIR = Path.cwd()
OUTPUT_CSV = WORK_DIR / "url_scores_summary.csv"


def gather_url_data() -> list[dict]:
    """Reads all *.url.json files in WORK_DIR and flattens candidate scores."""
    json_files = sorted(WORK_DIR.glob("*.url.json"))
    records = []

    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            best_url = data.get("best_url", "")
            candidates = data.get("candidates", [])

            for rank, cand in enumerate(candidates, start=1):
                records.append({
                    "image_file": jf.name.replace(".url.json", ""),
                    "best_url": best_url,
                    "is_winner": (cand.get("text") == best_url),
                    "rank": rank,
                    "rect_name": cand.get("rect_name", ""),
                    "score": cand.get("score", 0),
                    "candidate_text": cand.get("text", ""),
                    "report": " | ".join(cand.get("scoring_report", [])),
                })
        except Exception as e:
            print(f"Warning: Failed to parse {jf.name}: {e}")

    return records


def write_csv(records: list[dict]):
    """Exports flattened candidate records to CSV."""
    if not records:
        print("No records found to write.")
        return

    fieldnames = [
        "image_file", "is_winner", "rank", "rect_name", 
        "score", "candidate_text", "best_url", "report"
    ]
    
    with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    print(f"Summary CSV written to: {OUTPUT_CSV} ({len(records)} candidate rows)")


def render_ascii_histogram(scores: list[int], bins: int = 10):
    """Prints a terminal-based score distribution histogram."""
    if not scores:
        return

    min_s, max_s = min(scores), max(scores)
    if min_s == max_s:
        print(f"All scores are identical: {min_s}")
        return

    step = (max_s - min_s) / bins
    counts = [0] * bins

    for s in scores:
        idx = int((s - min_s) / step)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1

    print("\n" + "=" * 50)
    print(" SCORE DISTRIBUTION HISTOGRAM (All Candidates)")
    print("=" * 50)

    max_count = max(counts) if max(counts) > 0 else 1
    max_bar_len = 30

    for i in range(bins):
        low = min_s + (i * step)
        high = low + step
        cnt = counts[i]
        bar_len = int((cnt / max_count) * max_bar_len)
        bar = "#" * bar_len
        print(f"[{low:6.1f} to {high:6.1f}] : {cnt:3d} | {bar}")


def render_winning_rect_summary(records: list[dict]):
    """Prints how often each rectangle layout won best URL."""
    winners = [r for r in records if r["is_winner"]]
    counts = {}
    for w in winners:
        rect = w["rect_name"]
        counts[rect] = counts.get(rect, 0) + 1

    print("\n" + "=" * 50)
    print(" WINNING RECTANGLE BREAKDOWN")
    print("=" * 50)
    for rect, count in counts.items():
        pct = (count / len(winners) * 100) if winners else 0
        bar = "=" * int(pct / 2)
        print(f"{rect:15s} : {count:3d} ({pct:5.1f}%) | {bar}")


def render_top_bottom_outliers(records: list[dict], n: int = 5):
    """Displays top 5 highest and lowest scoring candidate texts."""
    sorted_recs = sorted(records, key=lambda x: x["score"], reverse=True)
    
    print("\n" + "=" * 50)
    print(f" TOP {n} HIGHEST SCORING CANDIDATES")
    print("=" * 50)
    for r in sorted_recs[:n]:
        print(f"Score: {r['score']:4d} | Rect: {r['rect_name']:12s} | Text: '{r['candidate_text'][:60]}'")

    print("\n" + "=" * 50)
    print(f" BOTTOM {n} LOWEST SCORING CANDIDATES")
    print("=" * 50)
    for r in sorted_recs[-n:]:
        print(f"Score: {r['score']:4d} | Rect: {r['rect_name']:12s} | Text: '{r['candidate_text'][:60]}'")


def main():
    records = gather_url_data()
    if not records:
        print(f"No *.url.json sidecar files found in {WORK_DIR}")
        return

    # 1. Export CSV
    write_csv(records)

    # 2. Terminal Visualizations
    scores = [r["score"] for r in records]
    render_ascii_histogram(scores)
    render_winning_rect_summary(records)
    render_top_bottom_outliers(records)


if __name__ == "__main__":
    main()
