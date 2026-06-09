---
name: canvas-notebooklm
description: "Sync course materials from Canvas LMS to Google NotebookLM. Use this skill whenever a student mentions Canvas, wants to download course files, organize lecture materials, upload to NotebookLM, set up a study sync, or says things like 'sync my canvas', 'download lectures', 'canvas to notebooklm', 'organize course files', 'study materials sync', or 'notebooklm upload'. Also trigger when someone asks how to get their Canvas files into NotebookLM for AI-powered studying, or wants to automate downloading lecture slides and assignments. Works with ANY university Canvas instance — not just specific schools."
---

# Canvas LMS → NotebookLM Sync

Download course files from any Canvas LMS and upload them to Google NotebookLM for AI-powered studying. Files are organized into Lesson folders with smart categorization, and duplicates are never re-processed.

## Setup (New Users)

Guide the student through these steps in order. Each step must complete before moving to the next.

### 1. Install dependencies

```bash
pip install canvasapi notebooklm-py pyyaml python-dotenv requests
```

### 2. Create project directory and config

Ask the student for:
- Their Canvas URL (e.g., `canvas.cityu.edu.hk`, `canvas.instructure.com`)
- Which courses to sync

Then create the directory structure:

```bash
mkdir -p ~/canvas-notebooklm-sync
cd ~/canvas-notebooklm-sync
```

Create `.env` from the template in `scripts/.env.example` and ask the student to paste their Canvas API token.

### 3. Get Canvas API Token

Walk the student through:
1. Log in to their Canvas portal
2. Go to **Account** → **Settings** → **New Access Token**
3. Name it "notebooklm-sync" and copy the token
4. Paste into `.env`

### 4. Discover Course IDs

Run the discovery script to list all enrolled courses:

```bash
python <skill-path>/scripts/discover_courses.py
```

Or run inline Python if the script path is unwieldy:

```python
import os; from canvasapi import Canvas; from dotenv import load_dotenv
load_dotenv()
canvas = Canvas("https://CANVAS_URL", os.getenv("CANVAS_TOKEN"))
for c in canvas.get_courses(enrollment_state="active"):
    print(f"{c.id}  {getattr(c,'course_code','?')}  {getattr(c,'name','?')}")
```

Have the student pick which course IDs to include.

### 5. Create config.yaml

Generate `config.yaml` with the student's courses:

```yaml
canvas:
  url: https://their-canvas-url.edu

courses:
  COURSE_CODE:
    canvas_id: 12345
    local_path: ~/Documents/University/COURSE_CODE

file_types:
  - .pdf
  - .pptx
  - .ppt
  - .docx
  - .doc
  - .xlsx
  - .ipynb
  - .csv
  - .sql
  - .zip

notebooklm:
  enabled: true
  notebook_prefix: "University"

schedule:
  time: "08:00"
```

### 6. Authenticate NotebookLM (one-time)

```bash
notebooklm auth
```

This opens a browser for Google login. Cookies are saved for future runs.

### 7. Test Run

```bash
python <skill-path>/scripts/sync.py --download-only
```

Have the student verify files downloaded correctly before running the full sync.

## Running the Sync

| Command | What it does |
|---------|-------------|
| `python scripts/sync.py` | Full sync: download + upload |
| `python scripts/sync.py --download-only` | Download from Canvas only |
| `python scripts/sync.py --upload-only` | Upload existing files to NotebookLM |

## How It Works

### File Organization

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
    └── <canvas_folder_name>/
```

### Smart Features

- **Lesson extraction**: Parses `lec01`, `Lecture 5`, `tutorial_12`, `Lab3` etc. from filenames
- **Folder categorization**: Maps Canvas folder names to lecture/lab/assignment/other
- **Duplicate prevention**: Checks state.json + local files + NotebookLM sources
- **Idempotent**: Safe to run multiple times — never re-downloads or re-uploads

### NotebookLM Integration

- Each course gets its own notebook: `{prefix} - {course_name}`
- Supported formats: PDF, TXT, MD, DOCX, PPTX, EPUB, HTML
- Unsupported formats (XLSX, CSV) are downloaded but skipped for upload

## Scheduling (macOS)

To sync daily at 8 AM:

```bash
# Copy the launchd plist
cp <skill-path>/scripts/com.cityu.canvas_sync.plist ~/Library/LaunchAgents/

# Edit the path inside to point to your sync.py
# Then load it:
launchctl load ~/Library/LaunchAgents/com.cityu.canvas_sync.plist
```

Stop with: `launchctl unload ~/Library/LaunchAgents/com.cityu.canvas_sync.plist`

## Troubleshooting

| Error | Fix |
|-------|-----|
| `CANVAS_TOKEN not set` | Check `.env` file exists and has your token |
| `Canvas login failed` | Token expired — generate a new one in Canvas Settings |
| `NotebookLM login failed` | Run `notebooklm auth` again |
| Files not downloading | Check `file_types` in config.yaml, verify course IDs |
| Upload skipped (unsupported) | NotebookLM doesn't accept XLSX/CSV — download only |

## Tips

- Run discovery at the start of each semester for new course IDs
- Delete `state.json` to force a full re-sync
- Logs are in `logs/sync_YYYY-MM-DD.log`
- The tool is safe to run multiple times
