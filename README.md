# Local Desktop Snapshot Search

> *"Why be jealous of Windows Recall, when you can vibe-code your own local, plain-text-friendly (emacs-centric) version on Linux?"*

A local-first, privacy-respecting screenshot indexing and search suite for Linux. You run scripts to capture, OCR, and index desktop screenshots into a local SQLite database, allowing fast full-text searching, and seamlessly generating search result folders.

---

### 🚧 Under Construction 🚧

<div align="center">
  <pre>
     ______
    /      \     
   |  o  o  |    [ WORK IN PROGRESS ]
   |   ||   |    
   |  \__/  |    A more complete technical README is under construction!
    \______/
  </pre>
</div>

---

## 💡 Origin & Inspiration

A while back, I heard about **Microsoft Recall**—a Windows feature designed to continuously screenshot your desktop, OCR the text, and let you search back through everything you've seen. As a Linux user, I was jealous of the capability (though not the telemetry or privacy implications!). 

Knowing almost nothing about how Windows built Recall beyond a brief description, I decided to try my hand at "vibe coding" my own version tailored strictly to my workflow:

- **100% Local & Private:** No cloud APIs or telemetry—just local Tesseract OCR, Python, and SQLite.
- **Keyboard & Plain-Text Native:** Built to query screenshot text via terminal/SQL and output structured, linkable `README.org` search reports directly into Emacs.
- **Sidecar Preserved:** Keeps raw `.txt` and extracted browser URLs sitting right alongside image files for easy shell scripting.

## 🔍 The High-Level Idea

1. **Capture & OCR:** Screenshots are processed in batches using Tesseract to produce `.full.txt` sidecar text files.
2. **Index:** Metadata, URLs, and text tokens are indexed into a local SQLite FTS5 database.
3. **Search & Assemble:** Running a query extracts matching screenshots and sidecars, symlinks them into a target results folder, and opens an Org-mode log file in Emacs with full, comma-escaped OCR transcripts.

---

*Detailed usage instructions, installation requirements, and script breakdowns could be added later.*

## Development Status

2026-09-20: I think most of it is working, but has not been tested
much at all.  I think that the scripts are likely quite personalized /
specific to my particular screenshot setup, which is not yet described
here.  It would be quite interesting if a leading AI chatbot could
figure out how to use these scripts simply by 'reading' them.

## How it was Developed

This script was built through an iterative dialogue with Gemini (free
version). For a detailed look at the logic, the alternative approaches
considered, and the evolution of the code, check the contents of the
chat/ folder in this repository.

## License

See LICENSE file
