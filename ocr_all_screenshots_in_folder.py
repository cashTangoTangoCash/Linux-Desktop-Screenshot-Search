#!/usr/bin/env python3
import csv
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

WORK_DIR = Path.cwd()
TIMING_LOG = WORK_DIR / "ocr_timing.csv"

# Exact crop coordinates for Firefox URL bar (2560x1440)
CROP_W = 1836
CROP_H = 33
CROP_X = 230
CROP_Y = 50

# PC_SCREENSHOT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-.*_\d+x\d+\.jpg$", re.IGNORECASE)
#PC_SCREENSHOT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}.*\.jpg$", re.IGNORECASE)
PC_SCREENSHOT_PATTERN = re.compile(r".*\.jpg$", re.IGNORECASE)

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

def process_ocr():
    # rglob("*") recursively finds matching screenshots at any directory depth
    pc_images = sorted([
        f for f in WORK_DIR.rglob("*")
        if f.is_file() and PC_SCREENSHOT_PATTERN.match(f.name)
    ])

    if not pc_images:
        print(f"No PC screenshots found to index in {WORK_DIR}")
        return

    print(f"Starting OCR indexing for {len(pc_images)} screenshot(s)...\n")

    indexed_count = 0
    for image_path in pc_images:
        # Save sidecars next to the image file itself (whether in root or a subfolder)
        url_txt_path = image_path.parent / f"{image_path.name}.url.txt"
        full_txt_path = image_path.parent / f"{image_path.name}.full.txt"

        if not url_txt_path.is_file():
            url_text = run_url_ocr(image_path)
            url_txt_path.write_text(url_text, encoding="utf-8")

        if not full_txt_path.is_file():
            full_text, duration = run_full_image_ocr(image_path)
            full_txt_path.write_text(full_text, encoding="utf-8")
            log_timing(image_path.name, duration)
            print(f"Indexed '{image_path.relative_to(WORK_DIR)}' ({duration:.2f}s)")
            indexed_count += 1
        else:
            print(f"Skipped '{image_path.relative_to(WORK_DIR)}' (already indexed)")

    print(f"\nOCR Indexing Complete. {indexed_count} new file(s) processed.")

if __name__ == "__main__":
    process_ocr()
