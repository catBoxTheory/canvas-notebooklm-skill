"""
notebooklm_uploader.py

Uploads newly downloaded course files to Google NotebookLM.
Each course gets its own notebook named "CityU - <COURSE_NAME>".

Checks performed before every upload:
  1. Local file exists on disk — skips with warning if missing
  2. File already uploaded to the notebook (by filename) — skips if duplicate
  3. File already recorded as uploaded in state.json — skips

Requires one-time auth setup:
    notebooklm auth
"""

import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

# NotebookLM supported source file types
NOTEBOOKLM_SUPPORTED_EXTENSIONS = {
    ".pdf", ".txt", ".md", ".docx", ".pptx",
    ".epub", ".html", ".htm"
}


def _get_or_create_notebook(client, notebook_name: str):
    """
    Returns an existing notebook by name, or creates a new one if it doesn't exist.
    """
    try:
        notebooks = client.list_notebooks()
        for nb in notebooks:
            if nb.title == notebook_name:
                logger.info(f"NotebookLM: Found existing notebook '{notebook_name}'")
                return nb
    except Exception as e:
        logger.warning(f"NotebookLM: Could not list notebooks: {e}")

    logger.info(f"NotebookLM: Creating new notebook '{notebook_name}' ...")
    try:
        notebook = client.create_notebook(title=notebook_name)
        return notebook
    except Exception as e:
        logger.error(f"NotebookLM: Failed to create notebook '{notebook_name}': {e}")
        return None


def _get_existing_source_titles(notebook) -> set[str]:
    """Returns a set of filenames already uploaded as sources in the notebook."""
    try:
        sources = notebook.sources
        return {s.title for s in sources}
    except Exception as e:
        logger.warning(f"NotebookLM: Could not fetch existing sources: {e}")
        return set()


def upload_course_files(
    client,
    course_name: str,
    notebook_prefix: str,
    new_files: list[Path],
    state: dict,
) -> None:
    """
    Upload a list of newly downloaded files into a course notebook on NotebookLM.
    """
    if not new_files:
        logger.info(f"[{course_name}] No new files to upload to NotebookLM.")
        return

    notebook_name = f"{notebook_prefix} - {course_name}"
    notebook = _get_or_create_notebook(client, notebook_name)
    if notebook is None:
        logger.error(f"[{course_name}] Could not get or create notebook — skipping upload.")
        return

    existing_sources = _get_existing_source_titles(notebook)
    uploaded_state = state.setdefault("uploaded", {})

    for local_file in new_files:
        filename = local_file.name
        file_key = str(local_file)

        # Check 1: Ensure the file actually exists on disk
        if not local_file.exists():
            logger.warning(f"[{course_name}] SKIP (file not on disk): {local_file}")
            continue

        # Check 2: Skip unsupported file types (NotebookLM only accepts certain formats)
        file_ext = local_file.suffix.lower()
        if file_ext not in NOTEBOOKLM_SUPPORTED_EXTENSIONS:
            logger.info(
                f"[{course_name}] SKIP (unsupported by NotebookLM): {filename} ({file_ext})"
            )
            continue

        # Check 3: Skip if already uploaded to the notebook
        if filename in existing_sources:
            logger.info(f"[{course_name}] SKIP (already in NotebookLM): {filename}")
            uploaded_state[file_key] = {
                "filename": filename,
                "notebook": notebook_name,
                "skipped_existing": True,
                "timestamp": datetime.now().isoformat(),
            }
            continue

        # Check 4: Skip if already recorded in state.json as uploaded
        if file_key in uploaded_state and not uploaded_state[file_key].get("error"):
            logger.info(f"[{course_name}] SKIP (in state.json as uploaded): {filename}")
            continue

        # Upload the file
        logger.info(f"[{course_name}] Uploading to NotebookLM: {filename}")
        try:
            notebook.add_source(file_path=str(local_file))
            logger.info(f"[{course_name}] Uploaded: {filename}")
            existing_sources.add(filename)

            uploaded_state[file_key] = {
                "filename": filename,
                "notebook": notebook_name,
                "course": course_name,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"[{course_name}] Failed to upload {filename}: {e}")
            uploaded_state[file_key] = {
                "filename": filename,
                "notebook": notebook_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    state["uploaded"] = uploaded_state


def run_upload(config: dict, state: dict, new_files_by_course: dict[str, list[Path]]) -> None:
    """
    Run the NotebookLM upload step for all courses that have new files.
    """
    notebooklm_cfg = config.get("notebooklm", {})
    if not notebooklm_cfg.get("enabled", True):
        logger.info("NotebookLM upload is disabled in config.yaml — skipping.")
        return

    notebook_prefix = notebooklm_cfg.get("notebook_prefix", "CityU")

    logger.info("Connecting to NotebookLM ...")
    try:
        from notebooklm import NotebookLM
        client = NotebookLM()
    except ImportError:
        logger.error(
            "notebooklm-py is not installed. Run: pip install notebooklm-py"
        )
        return
    except Exception as e:
        logger.error(
            f"NotebookLM login failed: {e}\n"
            "Make sure you have run 'notebooklm auth' at least once."
        )
        return

    for course_name, new_files in new_files_by_course.items():
        upload_course_files(
            client=client,
            course_name=course_name,
            notebook_prefix=notebook_prefix,
            new_files=new_files,
            state=state,
        )
        logger.info(
            f"[{course_name}] NotebookLM upload complete "
            f"({len(new_files)} file(s) attempted)."
        )
