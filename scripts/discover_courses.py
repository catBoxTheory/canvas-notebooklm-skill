"""
discover_courses.py

One-time helper script: lists all your Canvas enrolled courses with their IDs.
Copy the IDs into config.yaml under each course's canvas_id field.

Usage:
    python discover_courses.py
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from canvasapi import Canvas

load_dotenv(Path(__file__).parent / ".env")

CANVAS_URL = "https://canvas.cityu.edu.hk"
CANVAS_TOKEN = os.getenv("CANVAS_TOKEN")

if not CANVAS_TOKEN:
    print("ERROR: CANVAS_TOKEN not found.")
    print("Please copy .env.example to .env and fill in your Canvas API token.")
    sys.exit(1)

print(f"Connecting to {CANVAS_URL} ...")
canvas = Canvas(CANVAS_URL, CANVAS_TOKEN)

try:
    user = canvas.get_current_user()
    print(f"Logged in as: {user.name}\n")
except Exception as e:
    print(f"ERROR: Failed to connect to Canvas — {e}")
    print("Check that your CANVAS_TOKEN in .env is correct.")
    sys.exit(1)

print(f"{'ID':<12} {'Course Code':<15} {'Course Name'}")
print("-" * 70)

courses = canvas.get_courses(enrollment_state="active")
for course in courses:
    course_code = getattr(course, "course_code", "N/A")
    course_name = getattr(course, "name", "N/A")
    print(f"{course.id:<12} {course_code:<15} {course_name}")

print("\nCopy the IDs above into config.yaml under each course's canvas_id field.")
