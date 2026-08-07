#!/usr/bin/env python3
import os
import re
import shutil
from pathlib import Path
import pytesseract
from PIL import Image

# Working directory is wherever the command was executed
WORK_DIR = Path.cwd()

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
        # Define companion text file path (e.g. screenshot.png.txt)
        txt_path = WORK_DIR / f"{image_path.name}.txt"

        # Read cached text or perform OCR
        if txt_path.is_file():
            try:
                extracted_text = txt_path.read_text(encoding="utf-8")
            except Exception as e:
                print(f"Warning: Could not read cached text for {image_path.name}: {e}")
                extracted_text = ""
        else:
            try:
                img = Image.open(image_path)
                extracted_text = pytesseract.image_to_string(img).lower()
                # Save extracted text to sidecar file
                txt_path.write_text(extracted_text, encoding="utf-8")
            except Exception as e:
                print(f"Warning: Could not process {image_path.name}: {e}")
                extracted_text = ""

        # Check rules
        subfolder_name = None
        for pattern, folder in RULES:
            if re.search(pattern, extracted_text):
                subfolder_name = folder
                break

        # Move both image and text sidecar if a rule matched; otherwise, leave in place
        if subfolder_name:
            target_dir = WORK_DIR / subfolder_name
            target_dir.mkdir(parents=True, exist_ok=True)

            # Move image
            destination_img = target_dir / image_path.name
            shutil.move(str(image_path), str(destination_img))

            # Move sidecar text file alongside image
            if txt_path.is_file():
                destination_txt = target_dir / txt_path.name
                shutil.move(str(txt_path), str(destination_txt))

            print(f"Moved '{image_path.name}' -> {subfolder_name}/")
        else:
            print(f"Skipped '{image_path.name}' (no rule matched, cached text retained)")

if __name__ == "__main__":
    batch_sort()
