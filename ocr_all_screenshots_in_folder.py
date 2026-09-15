#!/usr/bin/env python3
import argparse
import csv
import json
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

WORK_DIR = Path.cwd()
TIMING_LOG = WORK_DIR / "ocr_timing.csv"
RECTANGLES_CSV = Path("/home/dad84/Documents/2026/screenshots/rectangles.csv")

# Fallback / Static pre-defined rectangles: (WIDTH, HEIGHT, X, Y)
FALLBACK_RECT_MATE = (1536, 56, 447, 81)  # Fallback Rectangle 1: MATE layout
RECT_I3 = (1531, 53, 447, 79)            # Rectangle 2: i3 layout

COMMON_DOMAINS = [
    "google.com", "github.com", "reddit.com", "wikipedia.org", 
    "youtube.com", "amazon.com", "stackoverflow.com"
]

PC_SCREENSHOT_PATTERN = re.compile(r".*\.jpg$", re.IGNORECASE)
DATE_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2}-\d{2}:\d{2}-\d{2})")


def parse_timestamp_from_filename(filename: str) -> datetime | None:
    """Extracts timestamp from screenshot filenames (e.g. 2026-09-13-10:55-19_2528x1368.jpg)."""
    match = DATE_PATTERN.search(filename)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d-%H:%M-%S")
        except ValueError:
            return None
    return None


def get_dynamic_rectangle(image_path: Path) -> tuple[int, int, int, int]:
    """Finds rectangle coordinates from rectangles.csv that are newest,

    but not newer than the given screenshot timestamp.
    Falls back to FALLBACK_RECT_MATE if no matching or valid row exists.
    """
    target_dt = parse_timestamp_from_filename(image_path.name)
    if not target_dt or not RECTANGLES_CSV.is_file():
        return FALLBACK_RECT_MATE

    best_coords: tuple[int, int, int, int] | None = None
    best_dt: datetime | None = None

    try:
        with open(RECTANGLES_CSV, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                filepath_str = row.get("filename", "")
                row_dt = parse_timestamp_from_filename(Path(filepath_str).name)
                if not row_dt:
                    continue

                # Must be <= target timestamp (newest, but not newer)
                if row_dt <= target_dt:
                    if best_dt is None or row_dt > best_dt:
                        try:
                            x = int(row["x"])
                            y = int(row["y"])
                            w = int(row["w"])
                            h = int(row["h"])
                            best_coords = (w, h, x, y)
                            best_dt = row_dt
                        except (KeyError, ValueError):
                            continue
    except Exception as e:
        print(f"Warning: Failed to read {RECTANGLES_CSV}: {e}")

    return best_coords if best_coords is not None else FALLBACK_RECT_MATE


def get_rectangles_for_image(image_path: Path) -> list[dict]:
    """Returns candidate rectangles combining the CSV-driven rectangle and canned i3 rectangle."""
    dynamic_mate = get_dynamic_rectangle(image_path)
    return [
        {"name": "mate_dynamic", "coords": dynamic_mate},
        {"name": "i3", "coords": RECT_I3},
    ]


def run_single_crop_ocr(image_path: Path, crop_coords: tuple[int, int, int, int]) -> str:
    """Cropped URL bar OCR using ImageMagick + Tesseract for a specific rectangle."""
    w, h, x, y = crop_coords
    cmd = (
        f'magick "{image_path}" '
        f'-crop {w}x{h}+{x}+{y} +repage '
        f'-colorspace Gray -resize 200% tif:- | '
        f'tesseract stdin stdout --dpi 300 --psm 7'
    )
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip().lower()
    except subprocess.CalledProcessError as e:
        print(f"Warning: URL OCR failed for {image_path.name} with crop {crop_coords}: {e}")
        return ""


def is_readable_search_query(text: str) -> bool:
    """Checks if a string looks like a clean, human-typed search query."""
    cleaned = re.sub(r"^[a-z]\s+[v>]\s+", "", text, flags=re.IGNORECASE).strip()
    
    words = [w for w in re.split(r"\s+", cleaned) if len(w) > 1]
    if not words:
        return False
        
    valid_words = 0
    for w in words:
        if not re.search(r"(.)\1\1", w) and not re.search(r"[a-z]{3,}\d+[a-z]+", w):
            valid_words += 1
            
    return (valid_words >= 2) and (valid_words / len(words) >= 0.7)


def score_url_candidate(text: str) -> tuple[int, list[str]]:
    score = 0
    report = []

    # 1. High-value Domain Check
    if re.search(r'\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:gov|com|org|net|edu|io|php)\b', text, re.I):
        score += 100
        report.append("+100: Strong domain match")

    # 2. Path & Query Structure
    if '/' in text:
        score += 15
        report.append("+15: Contains path slash '/'")

    # 3. Clean spaces penalty
    if re.search(r'\s', text):
        score -= 10
        report.append("-10: Contains whitespace")

    # 4. Symbol Noise
    bad_symbols = re.findall(r'[^\w\s\.\/:\?&=-]', text)
    if bad_symbols:
        penalty = len(bad_symbols) * 10
        score -= penalty
        report.append(f"-{penalty}: Contains {len(bad_symbols)} non-URL symbol(s)")

    return score, report


def process_url_candidates(image_path: Path) -> dict:
    candidates = []
    rectangles = get_rectangles_for_image(image_path)

    for rect_info in rectangles:
        coords = rect_info["coords"]
        extracted_text = run_single_crop_ocr(image_path, coords)
        
        score, report = score_url_candidate(extracted_text)

        candidates.append({
            "rect_name": rect_info["name"],
            "crop_coords": {"w": coords[0], "h": coords[1], "x": coords[2], "y": coords[3]},
            "text": extracted_text,
            "score": score,
            "scoring_report": report
        })

    candidates.sort(key=lambda c: c["score"], reverse=True)

    return {
        "best_url": candidates[0]["text"],
        "candidates": candidates
    }


def run_full_image_ocr(image_path: Path) -> tuple[str, float]:
    """Runs Tesseract on the entire screenshot and measures execution time in seconds."""
    cmd = ["tesseract", str(image_path), "stdout"]
    start_time = time.perf_counter()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        elapsed = time.perf_counter() - start_time
        return result.stdout.strip(), elapsed
    except subprocess.CalledProcessError as e:
        elapsed = time.perf_counter() - start_time
        print(f"Warning: Full OCR failed for {image_path.name}: {e}")
        return "", elapsed


def log_timing(image_name: str, seconds: float):
    """Appends full image Tesseract timing data to CSV."""
    file_exists = TIMING_LOG.is_file()
    with open(TIMING_LOG, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "filename", "duration_seconds"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), image_name, f"{seconds:.4f}"])

def parse_args():
    parser = argparse.ArgumentParser(
        prog="ocr_indexer",
        description="Extract URLs and full-page text from desktop screenshots using ImageMagick and Tesseract OCR.",
        epilog="Example: python3 ocr_script.py -r -f",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-r",
        "--recurse",
        action="store_true",
        help="recurse into subdirectories to discover and process image files",
    )
    parser.add_argument(
        "-f",
        "--force-urls",
        action="store_true",
        help="force re-processing and overwriting of existing .url.txt and .url.json sidecar files",
    )
    return parser.parse_args()

def process_ocr():
    args = parse_args()

    # Inform the user about directory search mode
    if args.recurse:
        print("Directory traversal: RECURSIVE (searching working directory and subdirectories)")
        file_list = WORK_DIR.rglob("*")
    else:
        print("Directory traversal: NON-RECURSIVE (searching top-level directory only)")
        file_list = WORK_DIR.glob("*")

    pc_images = sorted([
        f for f in file_list
        if f.is_file() and PC_SCREENSHOT_PATTERN.match(f.name)
    ])

    if not pc_images:
        print(f"No PC screenshots found to index in {WORK_DIR}")
        return

    print(f"Starting OCR indexing for {len(pc_images)} screenshot(s)...")
    if args.force_urls:
        print("--> Overwriting existing URL sidecars with new scoring logic.\n")

    indexed_count = 0
    for image_path in pc_images:
        url_txt_path = image_path.parent / f"{image_path.name}.url.txt"
        url_json_path = image_path.parent / f"{image_path.name}.url.json"
        full_txt_path = image_path.parent / f"{image_path.name}.full.txt"

        if args.force_urls or not url_txt_path.is_file() or not url_json_path.is_file():
            url_data = process_url_candidates(image_path)
            
            url_json_path.write_text(json.dumps(url_data, indent=2), encoding="utf-8")
            url_txt_path.write_text(url_data["best_url"], encoding="utf-8")
            print(f"Updated URL sidecars for: {image_path.relative_to(WORK_DIR)}")

        if not full_txt_path.is_file():
            full_text, duration = run_full_image_ocr(image_path)
            full_txt_path.write_text(full_text, encoding="utf-8")
            log_timing(image_path.name, duration)
            print(f"Indexed full image '{image_path.relative_to(WORK_DIR)}' ({duration:.2f}s)")
            indexed_count += 1

    print("\nOCR Indexing Complete.")


if __name__ == "__main__":
    process_ocr()
