#!/usr/bin/env python3
import argparse
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

# Paths
DB_PATH = Path.home() / "Documents" / "screenshots.db"
RESULT_DIR = Path.home() / ".cache" / "screenshot_search_results"

def setup_result_dir(target_dir: Path):
    """Ensures the result directory exists and is empty."""
    target_dir.mkdir(parents=True, exist_ok=True)
    for child in target_dir.iterdir():
        if child.is_symlink() or child.is_file():
            child.unlink()

def search_db(db_path: Path, query: str) -> list[Path]:
    """Queries FTS5 database for matching screenshot image paths."""
    if not db_path.is_file():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Query matching OCR text via FTS5 index
    sql = """
        SELECT s.abs_path
        FROM screenshots s
        JOIN ocr_fts f ON s.id = f.screenshot_id
        WHERE f.ocr_text MATCH ?
        ORDER BY s.id DESC;
    """
    
    try:
        cursor.execute(sql, (query,))
        rows = cursor.fetchall()
        return [Path(r[0]) for r in rows if Path(r[0]).is_file()]
    except sqlite3.OperationalError as e:
        print(f"SQLite error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(description="Search screenshot DB and open results in Dired.")
    parser.add_argument("query", type=str, help="FTS5 search query (e.g., 'stumpjumper OR rockhopper')")
    parser.add_argument("--open-eog", action="store_true", help="Launch Eye of GNOME instead of emacsclient")
    args = parser.parse_args()

    matches = search_db(DB_PATH, args.query)
    print(f"Found {len(matches)} matching screenshot(s).")

    if not matches:
        return

    setup_result_dir(RESULT_DIR)

    # Populate directory with symlinks to images and optional sidecars
    for idx, img_path in enumerate(matches, start=1):
        # Prefixing filename with index helps maintain order in file managers
        link_name = f"{idx:03d}_{img_path.name}"
        symlink_path = RESULT_DIR / link_name
        
        try:
            symlink_path.symlink_to(img_path)
            
            # Symlink sidecars if they exist alongside original
            txt_sidecar = img_path.with_suffix(img_path.suffix + ".txt")
            if txt_sidecar.is_file():
                (RESULT_DIR / f"{link_name}.txt").symlink_to(txt_sidecar)
                
        except OSError as e:
            print(f"Failed to symlink {img_path}: {e}", file=sys.stderr)

    print(f"Symlinks created in {RESULT_DIR}")

    # Launch viewer
    if args.open_eog:
        subprocess.Popen(["eog", str(RESULT_DIR)])
    else:
        # Open in Emacs Dired via emacsclient
        subprocess.Popen(["emacsclient", "-n", str(RESULT_DIR)])

if __name__ == "__main__":
    main()
