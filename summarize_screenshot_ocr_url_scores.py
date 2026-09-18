#!/usr/bin/env python3
import csv
import json
from pathlib import Path

WORK_DIR = Path.cwd()
OUTPUT_CSV = WORK_DIR / "url_scores_summary.csv"


def gather_url_data() -> tuple[list[dict], int]:
    """Reads all *.url.json files in WORK_DIR, assigns 1-based image indices,

    and flattens candidate scores.
    """
    json_files = sorted(WORK_DIR.glob("*.url.json"))
    total_images = len(json_files)
    records = []

    for img_idx, jf in enumerate(json_files, start=1):
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            best_url = data.get("best_url", "")
            candidates = data.get("candidates", [])

            for rank, cand in enumerate(candidates, start=1):
                records.append({
                    "image_index": img_idx,
                    "total_images": total_images,
                    "image_file": jf.name.replace(".url.json", ""),
                    "best_url": best_url,
                    "is_winner": (rank == 1),
                    "rank": rank,
                    "rect_name": cand.get("rect_name", ""),
                    "score": cand.get("score", 0),
                    "candidate_text": cand.get("text", ""),
                    "report": " | ".join(cand.get("scoring_report", [])),
                })
        except Exception as e:
            print(f"Warning: Failed to parse {jf.name}: {e}")

    return records, total_images


def write_csv(records: list[dict]):
    """Exports candidate records to CSV with proper field quoting and image index."""
    if not records:
        print("No records found to write.")
        return

    fieldnames = [
        "image_index", "total_images", "image_file", "is_winner", 
        "rank", "rect_name", "score", "candidate_text", "best_url", "report"
    ]
    
    with open(OUTPUT_CSV, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(records)

    print(f"Summary CSV written to: {OUTPUT_CSV} ({len(records)} candidate rows)")


def render_split_candidate_histogram(records: list[dict], bins: int = 10):
    """Histogram of all candidate scores showing Winners (#) vs Losers (.)."""
    if not records:
        return

    scores = [r["score"] for r in records]
    min_s, max_s = min(scores), max(scores)
    
    if min_s == max_s:
        print(f"All scores are identical: {min_s}")
        return

    step = (max_s - min_s) / bins
    
    # Track counts separately
    win_counts = [0] * bins
    lose_counts = [0] * bins

    for r in records:
        s = r["score"]
        idx = int((s - min_s) / step)
        if idx >= bins:
            idx = bins - 1
            
        if r["is_winner"]:
            win_counts[idx] += 1
        else:
            lose_counts[idx] += 1

    print("\n" + "=" * 65)
    print(" CANDIDATE SCORE HISTOGRAM (Legend: # = Winner [Rank 1], . = Loser)")
    print("=" * 65)

    total_counts = [win_counts[i] + lose_counts[i] for i in range(bins)]
    max_count = max(total_counts) if max(total_counts) > 0 else 1
    max_bar_len = 30

    for i in range(bins):
        low = min_s + (i * step)
        high = low + step
        
        w_cnt = win_counts[i]
        l_cnt = lose_counts[i]
        tot = total_counts[i]

        w_bar_len = int((w_cnt / max_count) * max_bar_len)
        l_bar_len = int((l_cnt / max_count) * max_bar_len)

        bar = ("#" * w_bar_len) + ("." * l_bar_len)
        print(f"[{low:6.1f} to {high:6.1f}] : {tot:3d} (W:{w_cnt:2d} L:{l_cnt:2d}) | {bar}")


def render_score_diff_histogram(records: list[dict], bins: int = 10):
    """Histogram of (Winner Score - Runner-Up Score) per screenshot."""
    # Group by screenshot
    images = {}
    for r in records:
        img = r["image_file"]
        images.setdefault(img, []).append(r)

    diffs = []
    for img, cands in images.items():
        # Sort candidates by rank
        sorted_cands = sorted(cands, key=lambda x: x["rank"])
        if len(sorted_cands) >= 2:
            winner_score = sorted_cands[0]["score"]
            runner_up_score = sorted_cands[1]["score"]
            diffs.append(winner_score - runner_up_score)
        elif len(sorted_cands) == 1:
            diffs.append(sorted_cands[0]["score"])

    if not diffs:
        return

    min_d, max_d = min(diffs), max(diffs)
    
    print("\n" + "=" * 65)
    print(" SCORE DIFFERENCE HISTOGRAM (Winner Score - Runner-Up Score)")
    print(" High diff = Clear win | Low diff (near 0) = Fragile win / Tie")
    print("=" * 65)

    if min_d == max_d:
        print(f"All score differences are identical: {min_d}")
        return

    step = (max_d - min_d) / bins
    counts = [0] * bins

    for d in diffs:
        idx = int((d - min_d) / step)
        if idx >= bins:
            idx = bins - 1
        counts[idx] += 1

    max_count = max(counts) if max(counts) > 0 else 1
    max_bar_len = 30

    for i in range(bins):
        low = min_d + (i * step)
        high = low + step
        cnt = counts[i]
        bar_len = int((cnt / max_count) * max_bar_len)
        bar = "=" * bar_len
        print(f"[{low:6.1f} to {high:6.1f}] diff : {cnt:3d} | {bar}")


def render_low_scoring_winners(records: list[dict], threshold: int = 15):
    """Spotlights winning candidates with low scores along with their inspector index."""
    winners = [r for r in records if r["is_winner"]]
    low_winners = sorted([w for w in winners if w["score"] <= threshold], key=lambda x: x["score"])

    print("\n" + "=" * 70)
    print(f" SUSPECT / LOW-QUALITY WINNERS (Score <= {threshold})")
    print("=" * 70)
    if not low_winners:
        print(f"None! All winning URLs scored above {threshold}.")
        return

    for w in low_winners:
        idx_str = f"[{w['image_index']}/{w['total_images']}]"
        print(f"Idx: {idx_str:10s} | Score: {w['score']:4d} | Text: '{w['candidate_text'][:55]}'")
        

def main():
    records, total_images = gather_url_data()
    if not records:
        print(f"No *.url.json sidecar files found in {WORK_DIR}")
        return

    # 1. Export CSV
    write_csv(records)

    # 2. Render Reports
    render_split_candidate_histogram(records)
    render_score_diff_histogram(records)
    render_low_scoring_winners(records, threshold=15)


if __name__ == "__main__":
    main()
