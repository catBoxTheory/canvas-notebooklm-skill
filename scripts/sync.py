"""
sync.py

Main entry point for the Canvas → Local Folders → NotebookLM sync system.

Usage:
    python sync.py                  # full sync (download + upload)
    python sync.py --download-only  # only download from Canvas
    python sync.py --upload-only    # only upload to NotebookLM (uses existing state.json)

Logs are written to logs/sync_YYYY-MM-DD.log
"""

import os
import sys
import json
import logging
import argparse
import yaml
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
LOG_DIR = BASE_DIR / "logs"
STATE_FILE = BASE_DIR / "state.json"
CONFIG_FILE = BASE_DIR / "config.yaml"


def setup_logging() -> None:
    LOG_DIR.mkdir(exist_ok=True)
    log_filename = LOG_DIR / f"sync_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        logging.error(f"config.yaml not found at {CONFIG_FILE}")
        sys.exit(1)
    with open(CONFIG_FILE, "r") as f:
        return yaml.safe_load(f)


def load_state() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"downloaded": {}, "uploaded": {}}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    logging.info(f"State saved to {STATE_FILE}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Canvas → Local Folders → NotebookLM Sync")
    parser.add_argument("--download-only", action="store_true", help="Only download from Canvas")
    parser.add_argument("--upload-only", action="store_true", help="Only upload to NotebookLM")
    args = parser.parse_args()

    setup_logging()
    load_dotenv(BASE_DIR / ".env")

    logger = logging.getLogger(__name__)
    logger.info("=" * 60)
    logger.info("Canvas Sync started")
    logger.info("=" * 60)

    config = load_config()
    state = load_state()

    new_files_by_course: dict = {}

    # --- Step 1: Download from Canvas ---
    if not args.upload_only:
        logger.info("--- STEP 1: Downloading from Canvas ---")
        from canvas_downloader import run_download
        new_files_by_course = run_download(config, state)
        save_state(state)

        total_new = sum(len(v) for v in new_files_by_course.values())
        logger.info(f"Download complete. {total_new} new file(s) downloaded in total.")
    else:
        # In upload-only mode, gather all previously downloaded files from state
        logger.info("Upload-only mode: reading previously downloaded files from state.json ...")
        from pathlib import Path as _Path
        for course_name in config.get("courses", {}):
            new_files_by_course[course_name] = [
                _Path(entry["local_path"])
                for entry in state.get("downloaded", {}).values()
                if entry.get("course") == course_name and not entry.get("skipped_existing")
            ]

    # --- Step 2: Upload to NotebookLM ---
    if not args.download_only:
        logger.info("--- STEP 2: Uploading to NotebookLM ---")
        from notebooklm_uploader import run_upload
        run_upload(config, state, new_files_by_course)
        save_state(state)
        logger.info("NotebookLM upload complete.")

    logger.info("=" * 60)
    logger.info("Canvas Sync finished successfully.")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
