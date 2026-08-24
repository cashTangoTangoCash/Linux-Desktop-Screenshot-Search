#!/usr/bin/bash
set -euo pipefail

# Default values
SEARCH_TERM=""
SEARCH_FOLDER="$HOME/Documents/2026/screenshots"

# Function to display help text
show_help() {
    cat << EOF
Usage: $(basename "$0") -s "SEARCH_TERM" [-f FOLDER]

Searches OCR full-text sidecar files (.full.txt) using ripgrep, launches an
interactive fzf preview panel, and opens the selected screenshot in Eye of GNOME (eog).

Options:
  -s, --search-term TERM   Search pattern or string for ripgrep (required)
  -f, --folder PATH        Directory to search (default: ~/Documents/2026/screenshots)
  -h, --help               Display this help message and exit
EOF
}

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -s|--search-term)
            SEARCH_TERM="$2"
            shift 2
            ;;
        -f|--folder)
            SEARCH_FOLDER="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Error: Unknown option $1" >&2
            show_help
            exit 1
            ;;
    esac
done

# --- Input & Dependency Checks ---

if [[ -z "$SEARCH_TERM" ]]; then
    echo "Error: --search-term (-s) is required." >&2
    show_help
    exit 1
fi

if [[ ! -d "$SEARCH_FOLDER" ]]; then
    echo "Error: Directory '$SEARCH_FOLDER' does not exist." >&2
    exit 1
fi

for cmd in rg fzf sed eog; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "Error: Required command '$cmd' is not installed or not in PATH." >&2
        exit 1
    fi
done

# --- Script Logic ---

# Run ripgrep to grab matching .full.txt files
matches=$(rg -i "$SEARCH_TERM" --glob '*.full.txt' "$SEARCH_FOLDER" -l || true)

if [[ -z "$matches" ]]; then
    echo "No matching screenshots found for term: '$SEARCH_TERM'"
    exit 0
fi

# Pipe results to fzf, strip .full.txt, and view image in eog
echo "$matches" | \
    fzf --preview 'cat {}' | \
    sed 's/\.full\.txt$//' | \
    xargs -r eog
