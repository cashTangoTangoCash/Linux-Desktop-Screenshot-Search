#!/usr/bin/env python3
import json
import sqlite3
import sys
from pathlib import Path

# Database path (adjust or place in a central config folder)
DB_PATH = Path.home() / "Documents" / "screenshots.db"

# Base search roots: scans ~/Documents/<YEAR>/screenshots
DOCS_DIR = Path.home() / "Documents"


def init_db(conn: sqlite3.Connection):
    """Creates the main table and FTS5 search index if they don't exist."""
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                abs_path TEXT UNIQUE NOT NULL,
                filename TEXT NOT NULL,
                folder_path TEXT NOT NULL,
                year_folder TEXT,
                month_folder TEXT,
                mtime REAL NOT NULL,
                best_url TEXT,
                url_score INTEGER,
                has_ocr INTEGER DEFAULT 0
            );
        """)

        # FTS5 virtual table for lightning-fast text searches
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS ocr_fts USING fts5(
                screenshot_id UNINDEXED,
                abs_path,
                ocr_text
            );
        """)


def sync_screenshot(conn: sqlite3.Connection, img_path: Path):
    """Inserts or updates a single screenshot record and its optional sidecars."""
    mtime = img_path.stat().st_mtime
    abs_path = str(img_path.resolve())

    # Check if file is already indexed and unchanged
    cur = conn.cursor()
    cur.execute("SELECT id, mtime FROM screenshots WHERE abs_path = ?", (abs_path,))
    row = cur.fetchone()

    if row and abs_path in row and row[1] == mtime:
        return  # Skip unchanged file

    screenshot_id = row[0] if row else None

    # Derive directory hierarchy (Year / Month)
    parts = img_path.parts
    year_folder = ""
    month_folder = ""
    for p in parts:
        if p.isdigit() and len(p) == 4:
            year_folder = p
        elif len(p) == 6 and p.isdigit():
            month_folder = p

    # 1. Read optional .url.json sidecar
    best_url = None
    url_score = None
    url_json_path = img_path.with_name(f"{img_path.name}.url.json")
    if url_json_path.is_file():
        try:
            url_data = json.loads(url_json_path.read_text(encoding="utf-8"))
            best_url = url_data.get("best_url")
            # Find score of the winning url
            for cand in url_data.get("candidates", []):
                if cand.get("text") == best_url:
                    url_score = cand.get("score")
                    break
        except Exception:
            pass

    # 2. Read optional .ocr.txt sidecar
    ocr_text = ""
    has_ocr = 0
    # Checks for either <file>.jpg.ocr.txt or <file>.ocr.txt
    ocr_path = img_path.with_suffix(img_path.suffix + ".ocr.txt")
    if not ocr_path.is_file():
        ocr_path = img_path.with_name(f"{img_path.stem}.ocr.txt")

    if ocr_path.is_file():
        try:
            ocr_text = ocr_path.read_text(encoding="utf-8", errors="replace").strip()
            has_ocr = 1 if ocr_text else 0
        except Exception:
            pass

    # 3. Upsert Metadata into SQLite
    with conn:
        if screenshot_id:
            conn.execute("""
                UPDATE screenshots
                SET filename=?, folder_path=?, year_folder=?, month_folder=?, 
                    mtime=?, best_url=?, url_score=?, has_ocr=?
                WHERE id=?
            """, (img_path.name, str(img_path.parent), year_folder, month_folder,
                  mtime, best_url, url_score, has_ocr, screenshot_id))
        else:
            cur = conn.execute("""
                INSERT INTO screenshots (abs_path, filename, folder_path, year_folder, 
                                        month_folder, mtime, best_url, url_score, has_ocr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (abs_path, img_path.name, str(img_path.parent), year_folder,
                  month_folder, mtime, best_url, url_score, has_ocr))
            screenshot_id = cur.lastrowid

        # Update FTS5 index
        conn.execute("DELETE FROM ocr_fts WHERE screenshot_id = ?", (screenshot_id,))
        conn.execute("""
            INSERT INTO ocr_fts (screenshot_id, abs_path, ocr_text)
            VALUES (?, ?, ?)
        """, (screenshot_id, abs_path, ocr_text))


def crawl_and_index():
    print(f"Connecting to database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    # Find screenshot directories matching ~/Documents/*/screenshots
    screenshot_dirs = list(DOCS_DIR.glob("*/screenshots"))
    if not screenshot_dirs:
        print("No screenshot directories found in ~/Documents/*/screenshots")
        return

    scanned_count = 0
    print(f"Found {len(screenshot_dirs)} screenshot root folders. Crawling...")

    for root_dir in screenshot_dirs:
        for ext in ("*.jpg", "*.jpeg", "*.png"):
            for img_path in root_dir.rglob(ext):
                sync_screenshot(conn, img_path)
                scanned_count += 1
                if scanned_count % 1000 == 0:
                    print(f"Processed {scanned_count} images...")

    conn.close()
    print(f"Finished indexing! Total images checked/updated: {scanned_count}")


if __name__ == "__main__":
    crawl_and_index()
