"""
canvas_downloader.py

Downloads course files from CityU Canvas and saves them into local Lesson_XX folders.

Destination path logic (in priority order):
  1. File already exists anywhere in course folder (same name) → skip
  2. File already in state.json → skip
  3. Extract lesson number from filename → Lesson_NN/<subfolder>/
  4. No lesson number found → new_files/<canvas_folder_name>/

Subfolder mapping (based on Canvas folder name):
  lecture / slide / lec         → Lesson_NN/lecture/
  lab / tutorial / practical    → Lesson_NN/lab/
  practice / exercise / other   → Lesson_NN/other/
  assignment / hw / homework    → Lesson_NN/assignment/
  anything else                 → Lesson_NN/other/
"""

import os
import re
import json
import logging
import requests
from pathlib import Path
from datetime import datetime
from canvasapi import Canvas

logger = logging.getLogger(__name__)

STATE_FILE = Path(__file__).parent / "state.json"


def load_state() -> dict:
    """Load the download state from state.json."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"downloaded": {}, "uploaded": {}}


def save_state(state: dict) -> None:
    """Persist the download state to state.json."""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def _build_folder_map(course) -> dict:
    """Returns a dict mapping Canvas folder ID -> folder full_name string."""
    folder_map = {}
    try:
        for folder in course.get_folders():
            folder_map[folder.id] = folder.full_name
    except Exception as e:
        logger.warning(f"Could not fetch folder structure: {e}")
    return folder_map


def _strip_canvas_prefix(path_str: str) -> str:
    """Remove the leading 'course files/' prefix Canvas adds to folder names."""
    parts = Path(path_str).parts
    if parts and parts[0].lower() == "course files":
        return str(Path(*parts[1:])) if len(parts) > 1 else ""
    return path_str


def _canvas_folder_to_subfolder_type(canvas_folder_name: str) -> str:
    """
    Map a Canvas folder name to one of: lecture, lab, other, assignment.
    """
    name = canvas_folder_name.lower()
    if any(k in name for k in ["lecture", "slide", "lec", "topic"]):
        return "lecture"
    if any(k in name for k in ["lab", "tutorial", "practical"]):
        return "lab"
    if any(k in name for k in ["assignment", "homework", " hw"]):
        return "assignment"
    return "other"


def _extract_lesson_number(filename: str) -> int | None:
    """
    Extract a lesson/week/lab number from a filename.

    Recognises patterns such as:
      cs3402_lec01_2026.pdf        → 1
      Lecture_09_Reduction.pdf     → 9
      Lecture 2 Data.pdf           → 2
      practice08.pdf               → 8
      tutorial_7_TwoX.ipynb        → 7
      Tutorial 8 - Python.pdf      → 8
      Lab3.pdf                     → 3
      Topic 1-1 Prob.pdf           → 1
      Lecture 10 Innovation.pdf    → 10
    """
    name = Path(filename).stem  # drop extension

    # Pattern 1: explicit keyword followed by number
    # e.g. lec01, lec_01, lecture01, lecture_01, lecture 01
    m = re.search(
        r'(?:lec(?:ture)?|lab|practice|tutorial|week|topic|worksheet)'
        r'[\s_-]*0*(\d+)',
        name, re.IGNORECASE
    )
    if m:
        return int(m.group(1))

    # Pattern 2: _NN_ or -NN- or _NN at word boundary (e.g. cs3402_lec03_2026)
    m = re.search(r'[_\-\s]0*([1-9]\d?)(?:[_\-\s]|$)', name)
    if m:
        return int(m.group(1))

    return None


def _resolve_dest_folder(
    filename: str,
    canvas_folder_name: str,
    local_root: Path,
) -> Path:
    """
    Determine the local destination folder for a Canvas file following the
    Lesson_NN/<subfolder>/ structure.

    Falls back to new_files/<canvas_folder_name>/ if no lesson number found.
    """
    lesson_num = _extract_lesson_number(filename)
    subfolder_type = _canvas_folder_to_subfolder_type(canvas_folder_name)

    if lesson_num is not None:
        lesson_str = f"Lesson_{lesson_num:02d}"
        return local_root / lesson_str / subfolder_type

    # No lesson number — place in new_files/ so nothing is lost
    safe_folder = re.sub(r'[^\w\s-]', '', canvas_folder_name).strip() or "unfiled"
    return local_root / "new_files" / safe_folder


def _scan_existing_filenames(root: Path, allowed_extensions: list[str]) -> dict[str, Path]:
    """
    Scan the entire course folder and return filename -> Path for every file.
    Used to detect duplicates across subfolders before downloading.
    """
    existing: dict[str, Path] = {}
    if not root.exists():
        return existing
    for f in root.rglob("*"):
        if f.is_file() and f.suffix.lower() in allowed_extensions:
            existing[f.name] = f
    return existing


def download_course_files(
    canvas: Canvas,
    course_name: str,
    course_id: int,
    local_root: str,
    allowed_extensions: list[str],
    state: dict,
) -> list[Path]:
    """
    Download all new files for a single Canvas course into Lesson_NN/ folders.
    Returns a list of local Paths for files that were newly downloaded.
    """
    newly_downloaded: list[Path] = []
    local_root_path = Path(local_root)

    # Ensure course root exists
    if not local_root_path.exists():
        logger.info(f"[{course_name}] Creating course folder: {local_root_path}")
        local_root_path.mkdir(parents=True, exist_ok=True)

    # Scan all existing filenames across the whole course folder (duplicate guard)
    existing_filenames = _scan_existing_filenames(local_root_path, allowed_extensions)
    logger.info(
        f"[{course_name}] {len(existing_filenames)} existing files found in local folder."
    )

    logger.info(f"[{course_name}] Fetching file list from Canvas ...")
    try:
        course = canvas.get_course(course_id)
    except Exception as e:
        logger.error(f"[{course_name}] Cannot access course ID {course_id}: {e}")
        return newly_downloaded

    folder_map = _build_folder_map(course)

    try:
        files = list(course.get_files())
    except Exception as e:
        logger.error(f"[{course_name}] Cannot fetch files: {e}")
        return newly_downloaded

    downloaded_ids = state.get("downloaded", {})

    for canvas_file in files:
        file_id   = str(canvas_file.id)
        filename  = canvas_file.display_name
        file_ext  = Path(filename).suffix.lower()

        # Filter by allowed extensions
        if file_ext not in allowed_extensions:
            continue

        # Skip if already recorded in state.json
        if file_id in downloaded_ids:
            logger.debug(f"[{course_name}] SKIP (state.json): {filename}")
            continue

        # Skip if same filename already exists anywhere in the course folder
        if filename in existing_filenames:
            existing_path = existing_filenames[filename]
            canvas_size   = getattr(canvas_file, "size", None)
            if canvas_size is None or existing_path.stat().st_size == canvas_size:
                rel = existing_path.relative_to(local_root_path)
                logger.info(f"[{course_name}] SKIP (exists at {rel}): {filename}")
                downloaded_ids[file_id] = {
                    "filename":        filename,
                    "local_path":      str(existing_path),
                    "course":          course_name,
                    "skipped_existing": True,
                    "timestamp":       datetime.now().isoformat(),
                }
                continue

        # Resolve destination: Lesson_NN/<subfolder>/ using filename + Canvas folder name
        canvas_folder_id   = getattr(canvas_file, "folder_id", None)
        canvas_folder_name = ""
        if canvas_folder_id and canvas_folder_id in folder_map:
            raw = _strip_canvas_prefix(folder_map[canvas_folder_id])
            # Use only the last part of the Canvas folder path as the type hint
            canvas_folder_name = Path(raw).name if raw else ""

        dest_folder = _resolve_dest_folder(filename, canvas_folder_name, local_root_path)

        # Create destination folder if it does not exist
        if not dest_folder.exists():
            logger.info(f"[{course_name}] Creating folder: {dest_folder.relative_to(local_root_path)}")
            dest_folder.mkdir(parents=True, exist_ok=True)

        dest_file   = dest_folder / filename
        canvas_size = getattr(canvas_file, "size", None)

        # Skip if file already exists at the exact destination with same size
        if dest_file.exists():
            if canvas_size is None or dest_file.stat().st_size == canvas_size:
                logger.info(f"[{course_name}] SKIP (exact path exists): {filename}")
                downloaded_ids[file_id] = {
                    "filename":        filename,
                    "local_path":      str(dest_file),
                    "skipped_existing": True,
                    "timestamp":       datetime.now().isoformat(),
                }
                continue

        # Download
        logger.info(
            f"[{course_name}] Downloading: {filename}\n"
            f"            → {dest_file.relative_to(local_root_path)}"
        )
        try:
            response = requests.get(canvas_file.url, stream=True, timeout=60)
            response.raise_for_status()
            with open(dest_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"[{course_name}] Downloaded: {filename}")
            newly_downloaded.append(dest_file)
            existing_filenames[filename] = dest_file  # update in-memory index

            downloaded_ids[file_id] = {
                "filename":   filename,
                "local_path": str(dest_file),
                "course":     course_name,
                "timestamp":  datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"[{course_name}] Failed to download {filename}: {e}")

    state["downloaded"] = downloaded_ids
    return newly_downloaded


def run_download(config: dict, state: dict) -> dict[str, list[Path]]:
    """
    Run the download step for all configured courses.
    Returns a dict mapping course_name -> list of newly downloaded file Paths.
    """
    canvas_url   = config["canvas"]["url"]
    canvas_token = os.getenv("CANVAS_TOKEN")

    if not canvas_token:
        logger.error("CANVAS_TOKEN not set. Aborting download.")
        return {}

    allowed_extensions = [ext.lower() for ext in config.get("file_types", [])]

    logger.info(f"Connecting to Canvas at {canvas_url} ...")
    canvas = Canvas(canvas_url, canvas_token)

    try:
        user = canvas.get_current_user()
        logger.info(f"Canvas: logged in as {user.name}")
    except Exception as e:
        logger.error(f"Canvas login failed: {e}")
        return {}

    results: dict[str, list[Path]] = {}

    for course_name, course_cfg in config.get("courses", {}).items():
        course_id  = course_cfg.get("canvas_id")
        local_path = course_cfg.get("local_path")

        if not course_id:
            logger.warning(f"[{course_name}] canvas_id not set — skipping.")
            continue
        if not local_path:
            logger.warning(f"[{course_name}] local_path not set — skipping.")
            continue

        new_files = download_course_files(
            canvas=canvas,
            course_name=course_name,
            course_id=int(course_id),
            local_root=local_path,
            allowed_extensions=allowed_extensions,
            state=state,
        )
        results[course_name] = new_files
        logger.info(f"[{course_name}] {len(new_files)} new file(s) downloaded.")

    return results
