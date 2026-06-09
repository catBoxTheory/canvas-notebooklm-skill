"""
Interactive setup wizard for Canvas → NotebookLM Sync.
Guides new users through configuration step by step.
"""

import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.yaml"
ENV_FILE = BASE_DIR / ".env"
ENV_EXAMPLE = BASE_DIR / ".env.example"


def print_header(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def step_canvas_token() -> None:
    print_header("Step 1: Canvas API Token")
    print("To get your Canvas API token:")
    print("  1. Log in to your Canvas portal")
    print("  2. Go to Account → Settings → New Access Token")
    print("  3. Give it a name (e.g., 'notebooklm-sync')")
    print("  4. Copy the generated token\n")

    if ENV_FILE.exists():
        load_dotenv(ENV_FILE)
        existing = os.getenv("CANVAS_TOKEN", "")
        if existing:
            print(f"  Current token: {existing[:8]}...{existing[-4:]}")
            keep = input("  Keep existing token? (y/n): ").strip().lower()
            if keep == "y":
                return

    token = input("  Paste your Canvas API token: ").strip()
    if not token:
        print("  ERROR: Token cannot be empty.")
        sys.exit(1)

    with open(ENV_FILE, "w") as f:
        f.write(f"CANVAS_TOKEN={token}\n")
    print("  ✓ Token saved to .env")


def step_canvas_url() -> str:
    print_header("Step 2: Canvas URL")
    print("Enter your university's Canvas URL.")
    print("Examples:")
    print("  - https://canvas.cityu.edu.hk")
    print("  - https://canvas.instructure.com")
    print("  - https://canvas.university.edu\n")

    url = input("  Canvas URL: ").strip()
    if not url.startswith("http"):
        url = f"https://{url}"
    return url


def step_discover_courses(canvas_url: str) -> list[dict]:
    print_header("Step 3: Discover Courses")
    print(f"Connecting to {canvas_url} ...\n")

    try:
        from canvasapi import Canvas
        load_dotenv(ENV_FILE)
        canvas = Canvas(canvas_url, os.getenv("CANVAS_TOKEN", ""))
        user = canvas.get_current_user()
        print(f"  Logged in as: {user.name}\n")
    except Exception as e:
        print(f"  ERROR: {e}")
        print("  Check your Canvas URL and token.")
        sys.exit(1)

    courses = []
    print(f"  {'#':<4} {'ID':<12} {'Course Code':<15} {'Course Name'}")
    print(f"  {'-' * 65}")

    for i, course in enumerate(canvas.get_courses(enrollment_state="active"), 1):
        code = getattr(course, "course_code", "N/A")
        name = getattr(course, "name", "N/A")
        print(f"  {i:<4} {course.id:<12} {code:<15} {name}")
        courses.append({"id": course.id, "code": code, "name": name})

    return courses


def step_select_courses(courses: list[dict]) -> list[dict]:
    print_header("Step 4: Select Courses")
    print("Enter the numbers of courses to sync (comma-separated).")
    print("Example: 1,3,5 or 'all' for everything\n")

    selection = input("  Select courses: ").strip()
    if selection.lower() == "all":
        return courses

    indices = [int(x.strip()) - 1 for x in selection.split(",") if x.strip().isdigit()]
    return [courses[i] for i in indices if 0 <= i < len(courses)]


def step_local_paths(selected: list[dict]) -> list[dict]:
    print_header("Step 5: Local Paths")
    print("For each course, enter the local folder path where files should be saved.")
    print("Press Enter for the suggested default path.\n")

    for course in selected:
        default = str(Path.home() / "Documents" / "University" / course["code"])
        path = input(f"  {course['code']} [{default}]: ").strip()
        course["local_path"] = path if path else default

    return selected


def step_notebooklm_prefix() -> str:
    print_header("Step 6: NotebookLM Prefix")
    print("Each course will get its own NotebookLM notebook.")
    print("Enter a prefix for notebook names.")
    print("Example: 'University' → notebooks named 'University - CS101'\n")

    prefix = input("  Notebook prefix [University]: ").strip()
    return prefix or "University"


def generate_config(canvas_url: str, courses: list[dict], prefix: str) -> None:
    config = {
        "canvas": {"url": canvas_url},
        "courses": {},
        "file_types": [
            ".pdf", ".pptx", ".ppt", ".docx", ".doc",
            ".xlsx", ".xls", ".ipynb", ".csv", ".sql", ".zip"
        ],
        "notebooklm": {"enabled": True, "notebook_prefix": prefix},
        "schedule": {"time": "08:00"},
    }

    for course in courses:
        config["courses"][course["code"]] = {
            "canvas_id": course["id"],
            "local_path": course["local_path"],
        }

    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    print(f"\n  ✓ Config saved to {CONFIG_FILE}")


def step_test_sync() -> None:
    print_header("Step 7: Test Run")
    print("Ready to run your first sync!")
    print("  python sync.py --download-only    # Test download only")
    print("  python sync.py                    # Full sync (download + upload)")
    print("  python sync.py --upload-only      # Upload only\n")

    run = input("  Run a test download now? (y/n): ").strip().lower()
    if run == "y":
        os.system(f"cd {BASE_DIR} && python sync.py --download-only")


def main() -> None:
    print_header("Canvas → NotebookLM Sync Setup Wizard")
    print("This wizard will help you configure the sync tool.\n")

    step_canvas_token()
    canvas_url = step_canvas_url()
    courses = step_discover_courses(canvas_url)
    selected = step_select_courses(courses)
    selected = step_local_paths(selected)
    prefix = step_notebooklm_prefix()
    generate_config(canvas_url, selected, prefix)

    print_header("Setup Complete!")
    print("Next steps:")
    print("  1. Run: python sync.py --download-only")
    print("  2. Check that files downloaded correctly")
    print("  3. Run: python sync.py  (full sync with NotebookLM upload)")
    print("  4. Optional: set up daily scheduling with launchd\n")
    print("For NotebookLM upload, make sure you've run: notebooklm auth\n")


if __name__ == "__main__":
    main()
