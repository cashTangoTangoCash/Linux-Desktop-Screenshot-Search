#!/usr/bin/env python3
import os
import re
import shutil
import subprocess
import sys
import tty
import termios
from pathlib import Path
import time

WORK_DIR = Path.cwd()
PC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-.*_\d+x\d+\.jpg$", re.IGNORECASE)

def get_terminal_window_id() -> str | None:
    """Retrieves the X11 Window ID for the terminal emulator running this script."""
    # 1. Check if the terminal emulator exposes $WINDOWID directly
    win_id = os.environ.get("WINDOWID")
    if win_id:
        return win_id
    
    # 2. Fall back to xdotool querying the active window at startup
    try:
        out = subprocess.check_output(["xdotool", "getactivewindow"], text=True).strip()
        return out if out else None
    except Exception:
        return None

def restore_terminal_focus(term_win_id: str | None):
    """Restores X11 focus and activates the terminal window running the pager."""
    if not term_win_id:
        return
    try:
        subprocess.run(
            ["xdotool", "windowactivate", "--sync", term_win_id],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        pass  # xdotool not installed, fail gracefully

def read_sidecar(path: Path) -> str:
    """Reads sidecar text file safely."""
    if not path.is_file():
        return "[FILE NOT FOUND]"
    try:
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        return text if text else "[EMPTY / NO TEXT DETECTED]"
    except Exception as e:
        return f"<Failed to read: {e}>"

def custom_pager(title: str, url_text: str, full_text: str) -> str:
    """Unified Pager UI using standard input()."""
    url_lines = [f"URL OCR: {url_text}", "-" * 60]
    full_lines = full_text.splitlines()
    all_content = url_lines + full_lines

    line_pointer = 0
    while True:
        term_cols, term_rows = shutil.get_terminal_size(fallback=(80, 24))
        chunk_size = max(5, term_rows - 6)
        
        os.system("clear")
        print(f"=== {title} ===")
        print("=" * 60)

        page_lines = all_content[line_pointer : line_pointer + chunk_size]

        for line in page_lines:
            print(line[:term_cols])

        for _ in range(chunk_size - len(page_lines)):
            print("")

        total_lines = len(all_content)
        end_idx = min(line_pointer + chunk_size, total_lines)
        pct = int((end_idx / total_lines) * 100) if total_lines else 100

        print("=" * 60)
        print(f"PAGER [{line_pointer + 1}-{end_idx}/{total_lines} L ({pct}%)]")
        print("[f/Enter] Screen Down | [b] Screen Up | [j] Line Down | [k] Line Up")
        print("[p] Prev Card | [n] Next Card | [m] Move | [d] Delete | [q] Quit")
        
        choice = input("Choice -> ").strip().lower()

        # --- Screenful (Page) Controls ---
        if choice in ('f', '', 'pgdn'):
            if line_pointer + chunk_size < total_lines:
                # Advance by chunk_size, but don't scroll past the bottom content
                line_pointer = min(total_lines - chunk_size, line_pointer + chunk_size)
            else:
                return "next"  # Paging past the bottom advances to the next card

        elif choice in ('b', 'pgup'):
            line_pointer = max(0, line_pointer - chunk_size)

        # --- Line-by-Line Controls ---
        elif choice in ('j', 'down'):
            if line_pointer + chunk_size < total_lines:
                line_pointer += 1
            else:
                return "next"

        elif choice in ('k', 'up'):
            line_pointer = max(0, line_pointer - 1)

        # --- Flashcard Workflow Actions ---
        elif choice in ('p', 'prev', 'back'):
            return "prev"
        elif choice in ('n', 'next'):
            return "next"
        elif choice in ('m', 'move'):
            return "move"
        elif choice in ('d', 'del', 'delete'):
            return "delete"
        elif choice in ('q', 'quit'):
            return "quit"

def review_flashcards():
    items = []
    for img in sorted(WORK_DIR.iterdir()):
        if img.is_file() and PC_PATTERN.match(img.name):
            url_txt = WORK_DIR / f"{img.name}.url.txt"
            full_txt = WORK_DIR / f"{img.name}.full.txt"
            if url_txt.is_file() or full_txt.is_file():
                items.append([img, url_txt, full_txt])

    if not items:
        print("No screenshots with sidecar text files found to review.")
        return

    term_win_id = get_terminal_window_id()
    feh_proc = None
    idx = 0

    try:
        while 0 <= idx < len(items):
            img_path, url_txt_path, full_txt_path = items[idx]

            # 1. Close previous feh instance
            if feh_proc and feh_proc.poll() is None:
                feh_proc.terminate()
                feh_proc.wait()

            time.sleep(.1)

            # 2. Spawn new feh process - stdin=DEVNULL prevents feh from locking terminal input
            feh_proc = subprocess.Popen(
                ["feh", "--title", "feh_flashcard_review", "-F", "--auto-zoom", str(img_path.resolve())],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            time.sleep(.1)
            restore_terminal_focus(term_win_id)

            url_text = read_sidecar(url_txt_path)
            full_text = read_sidecar(full_txt_path)
            title_str = f"Flashcard ({idx + 1}/{len(items)}) - {img_path.name}"

            action = custom_pager(title_str, url_text, full_text)
            if action == "quit":
                break
            elif action == "next":
                idx += 1
            elif action == "prev":
                if idx > 0:
                    idx -= 1
                else:
                    print("\nAlready at the first card!")
                    time.sleep(0.8)
            elif action == "move":
                print("\n")
                target_folder = input("Enter subfolder name to move into: ").strip()
                if target_folder:
                    dest = WORK_DIR / target_folder
                    dest.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(img_path), str(dest / img_path.name))
                    if url_txt_path.is_file():
                        shutil.move(str(url_txt_path), str(dest / url_txt_path.name))
                    if full_txt_path.is_file():
                        shutil.move(str(full_txt_path), str(dest / full_txt_path.name))
                    
                    items.pop(idx)  # Remove from queue; next item shifts into current idx
            elif action == "delete":
                url_txt_path.unlink(missing_ok=True)
                full_txt_path.unlink(missing_ok=True)
                # Note: keeping image, unlinking sidecars as per original script
                items.pop(idx)  # Remove from queue

    finally:
        if feh_proc and feh_proc.poll() is None:
            feh_proc.terminate()

        os.system("clear")
        print("Flashcard review complete.")
    
if __name__ == "__main__":
    review_flashcards()
