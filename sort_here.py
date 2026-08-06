#!/usr/bin/env python3
import os
import re
import shutil
from pathlib import Path
from datetime import datetime
import pytesseract
from PIL import Image

# Working directory is wherever the command was executed
WORK_DIR = Path.cwd()

# Rules mapping: (Regex pattern -> Subfolder name)
# RULES = [
#     (r"craigslist\.org", "Craigslist"),
#     (r"github\.com", "GitHub"),
#     (r"invoice|receipt|order summary", "Financial"),
# ]

RULES = [
    (r"craigslist\.org", "craigslist")
]


def batch_sort():
    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    # Only pick up image files directly inside the current directory
    image_files = [
        f for f in WORK_DIR.iterdir() 
        if f.is_file() and f.suffix.lower() in image_extensions
    ]

    if not image_files:
        print(f"No unprocessed images found in {WORK_DIR}")
        return

    print(f"Processing {len(image_files)} image(s) in {WORK_DIR}...\n")

    for image_path in image_files:
        try:
            img = Image.open(image_path)
            extracted_text = pytesseract.image_to_string(img).lower()
        except Exception as e:
            print(f"Warning: Could not process {image_path.name}: {e}")
            extracted_text = ""

        # Check rules
        subfolder_name = None
        for pattern, folder in RULES:
            if re.search(pattern, extracted_text):
                subfolder_name = folder
                break

        # Fallback to YYYY-MM if no rules match
        if not subfolder_name:
            # mtime = datetime.fromtimestamp(image_path.getmtime())
            # subfolder_name = mtime.strftime("%Y-%m")
            subfolder_name=WORK_DIR

        target_dir = WORK_DIR / subfolder_name
        target_dir.mkdir(parents=True, exist_ok=True)

        destination = target_dir / image_path.name
        shutil.move(str(image_path), str(destination))
        print(f"Moved '{image_path.name}' -> {subfolder_name}/")

if __name__ == "__main__":
    batch_sort()
