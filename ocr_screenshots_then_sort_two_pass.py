#!/usr/bin/env python3
import csv
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

WORK_DIR = Path.cwd()
TIMING_LOG = WORK_DIR / "ocr_timing.csv"

# Exact GIMP crop coordinates for Firefox URL bar (2560x1440)
CROP_W = 1836
CROP_H = 33
CROP_X = 230
CROP_Y = 50

# Rules mapping: (Regex pattern -> Subfolder name)
RULES = [
    (r"craigslist\.org", "craigslist"),
    (r"wikipedia\.org", "wikipedia"),
    (r"howard\s*hanna|mls\s*#?\s*[a-z]?\d{6,8}|new\s*listing", "housing-listings"),
    (r"news\.google\.com", "google-news"),
    (r"cambriabike\.com", "shopping-cambria-bike"),
    (r"jensonusa\.com", "shopping-jenson-usa-bike"),
    (r"amazon\.com", "shopping-amazon"),
    (r"bikeradar\.com", "shopping-bikeradar-bike"),
    (r"rottentomatoes\.com", "movies"),
    (r"audioclassics\.com", "audioclassics"),
    (r"forecast\.weather\.gov", "weather"),
    (r"npr\.org", "news"),
    (r"ebay\.com", "shopping-ebay"),
    (r"github\.com", "github"),
    (r"arstechnica\.com", "technology"),
    (r"gizmodo\.com", "news"),
    (r"nytimes\.com", "news"),
    (r"theguardian\.com", "news"),
    (r"techcrunch\.com", "technology"),
]

# Regex matching PC screenshot naming convention (e.g. 2026-08-02-12:02-44_2560x1440.jpg)
PC_SCREENSHOT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-.*_\d+x\d+\.jpg$", re.IGNORECASE)

def run_url_ocr(image_path: Path) -> str:
    """Cropped URL bar OCR using ImageMagick + Tesseract."""
    cmd = (
        f'magick "{image_path}" '
        f'-crop {CROP_W}x{CROP_H}+{CROP_X}+{CROP_Y} +repage '
        f'-colorspace Gray -resize 200% tif:- | '
        f'tesseract stdin stdout --dpi 300 --psm 7'
    )
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=True
        )
        return result.stdout.strip().lower()
    except subprocess.CalledProcessError as e:
        print(f"Warning: URL OCR failed for {image_path.name}: {e}")
        return ""

def run_full_image_ocr(image_path: Path) -> tuple[str, float]:
    """Runs Tesseract on the entire screenshot and measures execution time in seconds."""
    cmd = ["tesseract", str(image_path), "stdout"]
    start_time = time.perf_counter()
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        elapsed_time = time.perf_counter() - start_time
        return result.stdout.strip().lower(), elapsed_time
    except subprocess.CalledProcessError as e:
        elapsed_time = time.perf_counter() - start_time
        print(f"Warning: Full OCR failed for {image_path.name}: {e}")
        return "", elapsed_time

def log_timing(image_name: str, seconds: float):
    """Appends full image Tesseract timing data to CSV."""
    file_exists = TIMING_LOG.is_file()
    with open(TIMING_LOG, mode="a", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(["timestamp", "filename", "duration_seconds"])
        writer.writerow([datetime.now().isoformat(timespec="seconds"), image_name, f"{seconds:.4f}"])

def match_rules(text: str) -> str | None:
    """Checks text against rules mapping and returns matching folder name."""
    for pattern, folder in RULES:
        if re.search(pattern, text):
            return folder
    return None

def batch_sort():
    pc_images = [
        f for f in WORK_DIR.iterdir()
        if f.is_file() and PC_SCREENSHOT_PATTERN.match(f.name)
    ]

    if not pc_images:
        print(f"No unprocessed PC screenshots found in {WORK_DIR}")
        return

    print(f"Processing {len(pc_images)} PC screenshot(s) in {WORK_DIR}...\n")

    for image_path in pc_images:
        url_txt_path = WORK_DIR / f"{image_path.name}.url.txt"
        full_txt_path = WORK_DIR / f"{image_path.name}.full.txt"

        subfolder_name = None

        # --- PASS 1: URL Bar OCR ---
        if url_txt_path.is_file():
            url_text = url_txt_path.read_text(encoding="utf-8", errors="ignore")
        else:
            url_text = run_url_ocr(image_path)
            url_txt_path.write_text(url_text, encoding="utf-8")

        subfolder_name = match_rules(url_text)

        # --- PASS 2: Full Screenshot OCR (Only if Pass 1 had no match) ---
        if not subfolder_name:
            if full_txt_path.is_file():
                full_text = full_txt_path.read_text(encoding="utf-8", errors="ignore")
            else:
                full_text, duration = run_full_image_ocr(image_path)
                full_txt_path.write_text(full_text, encoding="utf-8")
                log_timing(image_path.name, duration)
                print(f"Full OCR on '{image_path.name}' took {duration:.2f}s")

            subfolder_name = match_rules(full_text)

        # --- File Relocation ---
        if subfolder_name:
            target_dir = WORK_DIR / subfolder_name
            target_dir.mkdir(parents=True, exist_ok=True)

            shutil.move(str(image_path), str(target_dir / image_path.name))
            if url_txt_path.is_file():
                shutil.move(str(url_txt_path), str(target_dir / url_txt_path.name))
            if full_txt_path.is_file():
                shutil.move(str(full_txt_path), str(target_dir / full_txt_path.name))

            print(f"Moved '{image_path.name}' -> {subfolder_name}/")
        else:
            print(f"Skipped '{image_path.name}' (no rule matched in URL or Full OCR)")

if __name__ == "__main__":
    batch_sort()
