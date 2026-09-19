#!/usr/bin/env python3
import argparse
import datetime
import os
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

# Base Paths
DB_PATH = Path.home() / "Documents" / "screenshots.db"
BASE_DOCS_DIR = Path.home() / "Documents" / "2026"

def slugify(text: str) -> str:
    """Converts search query into a clean filename-safe slug."""
    text = text.lower()
    # Remove special SQLite search characters like quotes and wildcard asterisks
    text = re.sub(r'["\'\*]', '', text)
    # Replace non-alphanumeric blocks with dashes
    slug = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return slug[:50]  # Cap length to keep directory names reasonable

def create_effort_folder(query: str, custom_name: str | None) -> Path:
    """Creates YYYYMMDD-screenshot-search-slug directory under ~/Documents/2026."""
    datestamp = datetime.datetime.now().strftime("%Y%m%d")
    
    if custom_name:
        slug = slugify(custom_name)
    else:
        slug = f"screenshot-search-{slugify(query)}"
        
    folder_name = f"{datestamp}-{slug}"
    effort_dir = BASE_DOCS_DIR / folder_name
    effort_dir.mkdir(parents=True, exist_ok=True)
    return effort_dir

def search_db(db_path: Path, query: str) -> tuple[list[tuple[str, str]], str]:
    """Queries FTS5 database for matching paths and OCR snippets."""
    if not db_path.is_file():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    sql = """
        SELECT s.abs_path, s.best_url
        FROM screenshots s
        JOIN ocr_fts f ON s.id = f.screenshot_id
        WHERE f.ocr_text MATCH ?
        ORDER BY s.id DESC;
    """
    
    try:
        cursor.execute(sql, (query,))
        rows = cursor.fetchall()
        return [(r[0], r[1] or "") for r in rows if Path(r[0]).is_file()], sql
    except sqlite3.OperationalError as e:
        print(f"SQLite error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

def write_log(effort_dir: Path, query: str, sql: str, matches: list[tuple[str, str]]):
    """Writes a detailed Org-mode log file inside the effort directory."""
    log_path = effort_dir / "README.org"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"#+TITLE: Screenshot Search: {query}",
        f"#+DATE: [{now_str}]",
        "#+CATEGORY: effort",
        "",
        "* Search Metadata",
        f"- **Query String:** ~{query}~",
        f"- **Executed At:** {now_str}",
        f"- **Matches Found:** {len(matches)}",
        f"- **Database Used:** ~{DB_PATH}~",
        "",
        "* SQL Executed",
        "#+BEGIN_SRC sql",
        sql.strip(),
        "#+END_SRC",
        "",
        "* Matched Items",
    ]

    for idx, (path_str, url) in enumerate(matches, start=1):
        lines.append(f"** Match {idx:03d}")
        lines.append(f"- **Original Path:** ~{path_str}~")
        if url:
            lines.append(f"- **Source URL:** {url}")
        lines.append("")

    log_path.write_text("\n".join(lines), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Create an effort folder for screenshot search results.")
    parser.add_argument("query", type=str, help="FTS5 search query")
    parser.add_argument("--name", "-n", type=str, help="Custom slug name override")
    args = parser.parse_args()

    matches, sql_query = search_db(DB_PATH, args.query)
    print(f"Found {len(matches)} matching screenshot(s).")

    if not matches:
        return

    effort_dir = create_effort_folder(args.query, args.name)
    print(f"Created effort folder: {effort_dir}")

    # Create Symlinks for images and sidecar files
    for idx, (path_str, _) in enumerate(matches, start=1):
        img_path = Path(path_str)
        
        # Name symlink with index prefix to keep chronological order in Dired
        link_name = f"{idx:03d}_{img_path.name}"
        
        try:
            (effort_dir / link_name).symlink_to(img_path)
            
            # Symlink matching .txt OCR sidecar if present
            txt_sidecar = img_path.with_suffix(img_path.suffix + ".txt")
            if txt_sidecar.is_file():
                (effort_dir / f"{link_name}.txt").symlink_to(txt_sidecar)
        except OSError as e:
            print(f"Warning: Failed to symlink {img_path}: {e}", file=sys.stderr)

    # Write Org log record
    write_log(effort_dir, args.query, sql_query, matches)

    # Open the new effort directory in Emacs via emacsclient
    subprocess.Popen(["emacsclient", "-n", str(effort_dir)])

if __name__ == "__main__":
    main()
