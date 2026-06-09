# Canvas → NotebookLM Auto-Sync

Automatically download course materials from any Canvas LMS and upload them to Google NotebookLM for AI-powered studying. Works with any university that uses Canvas.

## What It Does

1. Connects to your university's Canvas via API token
2. Discovers your enrolled courses
3. Downloads lecture slides, assignments, and files into organized `Lesson_NN/` folders
4. Uploads everything to Google NotebookLM — one notebook per course
5. Tracks state so it never re-downloads or re-uploads duplicates

## Prerequisites

- Python 3.10+
- A Canvas LMS account (any university)
- A Google account (for NotebookLM)

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get Your Canvas API Token

1. Log in to your university's Canvas portal
2. Go to **Account** → **Settings** → **New Access Token**
3. Give it a name (e.g., "notebooklm-sync") and copy the token

```bash
cp .env.example .env
# Open .env and paste your token
```

### 3. Discover Your Courses

```bash
python discover_courses.py
```

This lists all your enrolled courses with their IDs:

```
ID           Course Code     Course Name
----------------------------------------------------------------------
12345        CS101           Introduction to Computer Science
12346        MATH201         Linear Algebra
```

### 4. Configure Your Courses

Edit `config.yaml` — add your Canvas URL and the courses you want to sync:

```yaml
canvas:
  url: https://canvas.youruniversity.edu  # Your Canvas URL

courses:
  CS101:
    canvas_id: 12345                       # From Step 3
    local_path: ~/Documents/University/CS101
  MATH201:
    canvas_id: 12346
    local_path: ~/Documents/University/MATH201

file_types:
  - .pdf
  - .pptx
  - .docx
  - .ipynb
  - .xlsx
  - .csv

notebooklm:
  enabled: true
  notebook_prefix: "University"  # Notebooks named "University - CS101"
```

### 5. Authenticate NotebookLM (One-Time)

```bash
notebooklm auth
```

Opens a browser for Google login. Cookies are saved for future runs.

### 6. Test Run

```bash
python sync.py --download-only
```

Verify files downloaded correctly, then run the full sync:

```bash
python sync.py
```

---

## Daily Usage

| Command | Description |
|---------|-------------|
| `python sync.py` | Full sync (download + upload) |
| `python sync.py --download-only` | Download from Canvas only |
| `python sync.py --upload-only` | Upload existing files to NotebookLM |

---

## How Files Are Organized

Downloaded files go into a smart folder structure:

```
CourseFolder/
├── Lesson_01/
│   ├── lecture/       ← slides, lecture PDFs
│   ├── lab/           ← tutorials, practicals
│   ├── assignment/    ← homework, projects
│   └── other/         ← everything else
├── Lesson_02/
│   └── ...
└── new_files/         ← unmatched files
```

The tool automatically extracts lesson numbers from filenames (`lec01`, `Lecture 5`, `tutorial_12`, etc.) and categorizes files by Canvas folder type.

---

## Scheduling (macOS)

To sync daily at 8 AM:

```bash
cp com.cityu.canvas_sync.plist ~/Library/LaunchAgents/
# Edit the plist to point to your sync.py path, then:
launchctl load ~/Library/LaunchAgents/com.cityu.canvas_sync.plist
```

To stop:

```bash
launchctl unload ~/Library/LaunchAgents/com.cityu.canvas_sync.plist
```

---

## File Reference

| File | Purpose |
|------|---------|
| `sync.py` | Main entry point |
| `canvas_downloader.py` | Canvas download logic |
| `notebooklm_uploader.py` | NotebookLM upload logic |
| `discover_courses.py` | List enrolled courses with IDs |
| `setup_wizard.py` | Interactive setup for new users |
| `config.yaml` | Configuration (courses, paths, settings) |
| `state.json` | Auto-generated: tracks downloaded/uploaded files |
| `logs/` | Daily log files |

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `CANVAS_TOKEN not set` | Check `.env` file exists with your token |
| `Canvas login failed` | Token expired — generate a new one in Canvas Settings |
| `NotebookLM login failed` | Run `notebooklm auth` again |
| Files not downloading | Check `file_types` in config.yaml, verify course IDs |
| Upload skipped (unsupported) | NotebookLM doesn't accept XLSX/CSV — download only |

---

## Tips

- Run `python discover_courses.py` at the start of each semester for new course IDs
- Delete `state.json` to force a full re-sync
- Logs are in `logs/sync_YYYY-MM-DD.log` for debugging
- The tool is idempotent — safe to run multiple times
- NotebookLM supports: PDF, TXT, MD, DOCX, PPTX, EPUB, HTML

---

## License

MIT
