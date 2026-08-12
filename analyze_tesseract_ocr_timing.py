#!/usr/bin/env python3
import csv
import math
import statistics
from pathlib import Path

LOG_FILE = Path("ocr_timing.csv")

def analyze():
    if not LOG_FILE.is_file():
        print(f"No timing file found at {LOG_FILE.resolve()}")
        return

    durations = []
    with open(LOG_FILE, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                durations.append(float(row["duration_seconds"]))
            except (KeyError, ValueError):
                continue

    if not durations:
        print("No timing data recorded yet.")
        return

    n = len(durations)
    mean_val = statistics.mean(durations)
    median_val = statistics.median(durations)
    stdev_val = statistics.stdev(durations) if n > 1 else 0.0
    min_val = min(durations)
    max_val = max(durations)

    print("=" * 50)
    print("      TESSERACT FULL-IMAGE TIMING ANALYSIS      ")
    print("=" * 50)
    print(f" Total Samples   : {n}")
    print(f" Min Time        : {min_val:.2f}s")
    print(f" Max Time        : {max_val:.2f}s")
    print(f" Mean Time       : {mean_val:.2f}s")
    print(f" Median Time     : {median_val:.2f}s")
    print(f" Std Dev         : {stdev_val:.2f}s")
    print("=" * 50)
    print("\n--- Execution Time Histogram (ASCII) ---")

    # Build 10 bin histogram
    num_bins = 10
    bin_width = (max_val - min_val) / num_bins if max_val != min_val else 1.0
    bins = [0] * num_bins

    for val in durations:
        idx = min(int((val - min_val) / bin_width), num_bins - 1)
        bins[idx] += 1

    max_count = max(bins)
    max_bar_len = 30  # Max characters wide

    for i in range(num_bins):
        low = min_val + i * bin_width
        high = low + bin_width
        count = bins[i]
        bar_len = int((count / max_count) * max_bar_len) if max_count > 0 else 0
        bar = "█" * bar_len
        print(f"[{low:5.2f}s - {high:5.2f}s) | {bar:<30} ({count})")

if __name__ == "__main__":
    analyze()
