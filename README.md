# Local Desktop Snapshot Search

> *"Why be jealous of the Windows Recall photographic memory-like experience, when you can vibe-code your own local, plain-text-friendly (emacs-centric, no-AI) version on Linux?"*

A local-first, privacy-respecting screenshot indexing and search suite for Linux. You run scripts to capture, OCR, and index desktop screenshots into a local SQLite database, allowing fast full-text, SQL query searching, and seamlessly generating search result folders.

---

### 🚧 Under Construction 🚧

<div align="center">
  <pre>
     ______
    /      \     
   |  o  o  |    [ WORK IN PROGRESS ]
   |   ||   |    
   |  \__/  |    A more complete README is under construction!
    \______/
  </pre>
</div>

---

## 💡 Origin & Inspiration

A while back, I read or heard about **Microsoft Recall**—a Windows
feature designed to continuously screenshot your desktop, OCR the
text, and let you search back through everything you've seen via
natural language queries (AI-enabled). As a Linux user, I was jealous
of the capability (though not the telemetry or privacy implications) -
it could be a little like having a photographic memory.

Knowing almost nothing about how Windows built Recall beyond a brief
description, I decided to try my hand at "vibe coding" my own version
tailored strictly to my workflow:

- **100% Local & Private:** No cloud APIs or telemetry—just local Tesseract OCR, Python, and SQLite.
- **Keyboard & Plain-Text Native:** Built to query screenshot text via terminal/SQL and output structured, linkable `README.org` search reports directly into Emacs.
- **Sidecar Preserved:** Keeps raw `.txt` OCR data files sitting right alongside image files for easy shell scripting.

I already had many years of screenshots piled up on my Linux machine,
ready for indexing and searching.

## 🔍 The High-Level Idea

1. **Capture & OCR:** Screenshots are processed in batches using Tesseract to produce `.full.txt` sidecar text files (`.url.txt` for browser address bar content).
2. **Index:** Metadata, URLs, and text tokens are indexed into a local SQLite FTS5 database.
3. **Search & Assemble:** Running a query extracts matching screenshots and sidecars, symlinks them into a target results folder, and opens an Org-mode log file in Emacs with detailed search results and data.

---

## 📁 Directory & Sidecar Layout Conventions

The indexing and search scripts assume a structured layout based on year and month subdirectories, with companion "sidecar" text files created alongside each image:

```text
~/Documents/2026/screenshots/
└── 202601/
    ├── TODO-code-to-write/
    │   ├── 2026-01-08-20:36-40_2560x1349.jpg
    │   ├── 2026-01-08-20:36-40_2560x1349.jpg.full.txt   <-- Raw OCR transcript
    │   └── 2026-01-08-20:36-40_2560x1349.jpg.url.txt    <-- Extracted web page URL
    └── hledger/
        ├── 2026-01-09-00:31-45_2560x1380.jpg
        ├── 2026-01-09-00:31-45_2560x1380.jpg.full.txt
        └── 2026-01-09-00:31-45_2560x1380.jpg.url.txt
```

In fact, the scripts carry out the sorting of screenshots and sidecars
into named folders, using rules text files that you create.

### Key Conventions:

* **Datestamped Filenames:** Images follow a timestamped naming structure (e.g., `YYYY-MM-DD-HH:MM-SS_WIDTHxHEIGHT.jpg`).
* **Year/Month Buckets:** Files are organized into `YYYY/screenshots/YYYYMM/` topic or task folders.
* **Sidecar Extensions:**
* `.jpg.full.txt`: Stores the complete, unformatted Tesseract OCR text extracted from the screenshot.
* `.jpg.url.txt`: Stores browser address bar URLs obtained via cropping then OCR.

---

*Detailed usage instructions, installation requirements, and script breakdowns to be added later.*

## Development Status

2026-09-20: I think most of the scripts are working as intended, but
they are minimally tested at this time.  This README is leaving out
all the step by step usage instructions.  The included AI chat
actually contains all of that information, but is too long for a
normal user to read.

## How it was Developed

This script was built through an iterative dialogue with Gemini (free
version). For a detailed look at the logic, the alternative approaches
considered, and the evolution of the code, check the contents of the
chat/ folder in this repository.

## License

See LICENSE file
