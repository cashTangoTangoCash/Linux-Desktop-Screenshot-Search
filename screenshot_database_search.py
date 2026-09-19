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
    """Converts search query or filename into a clean filename-safe slug."""
    text = text.lower()
    text = re.sub(r'["\'\*]', '', text)
    slug = re.sub(r'[^a-z0-9]+', '-', text).strip('-')
    return slug[:50]

def resolve_effort_folder(target_dir: Path | None, slug_text: str, custom_name: str | None) -> Path:
    """Resolves target directory: uses existing if provided, otherwise creates a new one."""
    if target_dir:
        effort_dir = target_dir.expanduser().resolve()
        if not effort_dir.is_dir():
            print(f"Error: Specified effort directory does not exist: {effort_dir}", file=sys.stderr)
            sys.exit(1)
        return effort_dir

    # Generate a new effort directory under BASE_DOCS_DIR
    datestamp = datetime.datetime.now().strftime("%Y%m%d")
    if custom_name:
        slug = slugify(custom_name)
    else:
        slug = f"screenshot-search-{slugify(slug_text)}"
        
    folder_name = f"{datestamp}-{slug}"
    effort_dir = BASE_DOCS_DIR / folder_name
    effort_dir.mkdir(parents=True, exist_ok=True)
    return effort_dir

def execute_query(db_path: Path, sql: str, params: tuple = ()) -> list[dict]:
    """Executes SQL query against SQLite DB and returns matching records."""
    if not db_path.is_file():
        print(f"Error: Database not found at {db_path}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        results = []
        for r in rows:
            abs_path = r[0]
            url = r[1] if len(r) > 1 and r[1] else ""
            db_ocr = r[2] if len(r) > 2 and r[2] else ""
            
            if Path(abs_path).is_file():
                results.append({
                    "abs_path": abs_path,
                    "url": url,
                    "db_ocr": db_ocr
                })
        return results
    except sqlite3.OperationalError as e:
        print(f"SQLite error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

def get_ocr_text(img_path: Path, db_ocr: str) -> str:
    """Retrieves full OCR text from .full.txt sidecar, fallback to .txt sidecar, or DB text."""
    # 1. Try <filename>.jpg.full.txt
    full_sidecar = img_path.parent / f"{img_path.name}.full.txt"
    if full_sidecar.is_file():
        try:
            return full_sidecar.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            pass

    # 2. Try <filename>.jpg.txt
    std_sidecar = img_path.parent / f"{img_path.name}.txt"
    if std_sidecar.is_file():
        try:
            return std_sidecar.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            pass

    # 3. Fallback to DB ocr_text
    return db_ocr.strip()

def write_log(effort_dir: Path, query_label: str, sql: str, matches_data: list[dict]):
    """Writes or overwrites README.org inside the effort directory with embedded OCR text."""
    log_path = effort_dir / "README.org"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        f"#+TITLE: Screenshot Search: {query_label}",
        f"#+DATE: [{now_str}]",
        "#+CATEGORY: effort",
        "",
        "* Search Metadata",
        f"- **Query / File:** ~{query_label}~",
        f"- **Executed At:** {now_str}",
        f"- **Matches Found:** {len(matches_data)}",
        f"- **Database Used:** ~{DB_PATH}~",
        "",
        "* SQL Executed",
        "#+BEGIN_SRC sql",
        sql.strip(),
        "#+END_SRC",
        "",
        "* Matched Items",
    ]

    for item in matches_data:
        idx = item["idx"]
        path_str = item["orig_path"]
        url = item["url"]
        ocr_text = item["ocr_text"]
        img_symlink = item["img_symlink"]

        lines.append(f"** Match {idx:03d}: [[file:{img_symlink.name}][{img_symlink.name}]]")
        lines.append(f"- **Original Path:** ~{path_str}~")
        if url:
            lines.append(f"- **Source URL:** {url}")
        
        lines.append("")
        lines.append(f"*** OCR Text for Match {idx:03d}")
        if ocr_text:
            lines.append(ocr_text)
        else:
            lines.append("/[No OCR text recorded for this screenshot]/")
            
        lines.append("")

    log_path.write_text("\n".join(lines), encoding="utf-8")

def main():
    parser = argparse.ArgumentParser(description="Search screenshot DB and populate an effort folder.")
    parser.add_argument("query", type=str, nargs="?", help="FTS5 search string query (ignored if -f/--file is supplied)")
    parser.add_argument("-f", "--file", type=Path, help="Path to a .sql file containing the query")
    parser.add_argument("-e", "--effort-dir", type=Path, help="Path to a pre-existing effort folder to populate")
    parser.add_argument("-n", "--name", type=str, help="Custom effort folder slug override (if auto-generating folder)")
    args = parser.parse_args()

    # 1. Determine query source and ensure SELECT includes s.abs_path, s.best_url, f.ocr_text
    if args.file:
        if not args.file.is_file():
            print(f"Error: SQL file not found at {args.file}", file=sys.stderr)
            sys.exit(1)
        
        user_sql = args.file.read_text(encoding="utf-8").strip()
        query_params = ()
        query_label = args.file.name

        sql_query = user_sql
        if "f.ocr_text" not in sql_query.lower() and "ocr_text" not in sql_query.lower():
            sql_query = re.sub(
                r"(?i)SELECT\s+s\.abs_path,\s*s\.best_url", 
                "SELECT s.abs_path, s.best_url, f.ocr_text", 
                user_sql
            )
    elif args.query:
        sql_query = """
            SELECT s.abs_path, s.best_url, f.ocr_text
            FROM screenshots s
            JOIN ocr_fts f ON s.id = f.screenshot_id
            WHERE f.ocr_text MATCH ?
            ORDER BY s.id DESC;
        """
        query_params = (args.query,)
        query_label = args.query
    else:
        parser.error("You must supply either a positional search query or a SQL file via -f/--file.")

    # 2. Execute SQL query
    matches = execute_query(DB_PATH, sql_query, query_params)
    print(f"Found {len(matches)} matching screenshot(s).")

    if not matches:
        return

    # 3. Resolve target directory
    effort_dir = resolve_effort_folder(args.effort_dir, query_label, args.name)
    print(f"Target effort folder: {effort_dir}")

    matches_data = []

    # 4. Process matches, create symlinks, and read .full.txt sidecars
    for idx, item in enumerate(matches, start=1):
        img_path = Path(item["abs_path"])
        link_name = f"{idx:03d}_{img_path.name}"
        img_symlink = effort_dir / link_name
        
        try:
            if not img_symlink.exists():
                img_symlink.symlink_to(img_path)
            
            # Link .full.txt sidecar into effort folder if present
            full_txt = img_path.parent / f"{img_path.name}.full.txt"
            if full_txt.is_file():
                sidecar_symlink = effort_dir / f"{link_name}.full.txt"
                if not sidecar_symlink.exists():
                    sidecar_symlink.symlink_to(full_txt)

        except OSError as e:
            print(f"Warning: Failed to symlink {img_path}: {e}", file=sys.stderr)

        # Read actual OCR content from sidecar file or fallback to DB
        ocr_content = get_ocr_text(img_path, item["db_ocr"])

        matches_data.append({
            "idx": idx,
            "orig_path": item["abs_path"],
            "url": item["url"],
            "ocr_text": ocr_content,
            "img_symlink": img_symlink
        })

    # 5. Write Org log record inside target folder
    write_log(effort_dir, query_label, user_sql if args.file else sql_query, matches_data)

    # 6. Focus effort directory in Emacs via emacsclient
    subprocess.Popen(["emacsclient", "-n", str(effort_dir)])

if __name__ == "__main__":
    main()
