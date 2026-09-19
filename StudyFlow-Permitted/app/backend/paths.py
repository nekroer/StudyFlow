"""
StudyFlow Path Manager
----------------------

This module is the ONLY place that knows where user data lives.

Never hardcode paths anywhere else.

Usage:
    from app.backend.paths import SPRINTS_FILE
"""

import os
import json
from pathlib import Path

# ============================================================
# Root Data Directory
# ============================================================

# Windows Local AppData
# Example:
# C:\Users\nelgi\AppData\Local\StudyFlowV1.0
APP_NAME = "StudyFlow"
APP_VERSION = "1.0"

LOCALAPPDATA = Path(
    os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local")
)

DATA_DIR = LOCALAPPDATA / f"{APP_NAME}V{APP_VERSION}"
DATA_DIR.mkdir(parents=True, exist_ok=True)
# ============================================================
# Subdirectories
# ============================================================

SPRINT_DIR = DATA_DIR / "sprints"
SCHEDULER_DIR = DATA_DIR / "scheduler"
LEARNING_DIR = DATA_DIR / "learning"
JOURNAL_DIR = DATA_DIR / "journal"
SETTINGS_DIR = DATA_DIR / "settings"
CACHE_DIR = DATA_DIR / "cache"
EXPORT_DIR = DATA_DIR / "exports"
TRANSITION_DIR = DATA_DIR / "transition"
SESSION_DIR = DATA_DIR / "session"

for folder in (
    SPRINT_DIR,
    SCHEDULER_DIR,
    LEARNING_DIR,
    JOURNAL_DIR,
    SETTINGS_DIR,
    CACHE_DIR,
    EXPORT_DIR,
    TRANSITION_DIR,
    SESSION_DIR,
):
    folder.mkdir(parents=True, exist_ok=True)

# ============================================================
# Sprint Files
# ============================================================

SPRINTS_FILE = SPRINT_DIR / "sprints.json"
SPRINTS_DONE_FILE = SPRINT_DIR / "sprints_done.json"
TASKS_DONE_FILE = SPRINT_DIR / "tasks_done.json"

# ============================================================
# Scheduler Files
# ============================================================

SCHEDULER_FILE = SCHEDULER_DIR / "scheduler.json"
SESSIONS_FILE = SCHEDULER_DIR / "sessions.json"

# ============================================================
# Learning Files
# ============================================================

LEARNING_PROFILE_FILE = LEARNING_DIR / "learning_profile.json"
STATISTICS_FILE = LEARNING_DIR / "statistics.json"

# ============================================================
# Journal Files
# ============================================================

JOURNAL_FILE = JOURNAL_DIR / "journal.json"
NOTES_FILE = JOURNAL_DIR / "notes.json"

# ============================================================
# Settings Files
# ============================================================

SETTINGS_FILE = SETTINGS_DIR / "settings.json"
THEME_FILE = SETTINGS_DIR / "theme.json"

# ============================================================
# Cache Files
# ============================================================

CACHE_FILE = CACHE_DIR / "cache.json"

# ============================================================
# Export Folder
# ============================================================

EXPORTS_FOLDER = EXPORT_DIR

# ============================================================
# Transition Folder
# ============================================================

TRANSITION_FOLDER = TRANSITION_DIR
TRANSITION_CONFIG_FILE = TRANSITION_DIR / "transition_config.json"

TRANSITION_DEFAULT_CONFIG = {
    "fade_start_offset_min": 7,  # Start fading 7 minutes before session
    "fade_duration_sec": 300,    # Fade over 5 minutes (300 seconds)
    "countdown_sec": 120,        # Show dialog 2 minutes before session (120 seconds)
}

transition_needs_default = False

if not TRANSITION_CONFIG_FILE.exists():
    transition_needs_default = True
else:
    try:
        t_data = json.loads(TRANSITION_CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(t_data, dict) or not t_data:
            transition_needs_default = True
        elif any(key not in t_data for key in TRANSITION_DEFAULT_CONFIG):
            transition_needs_default = True
    except Exception:
        transition_needs_default = True

if transition_needs_default:
    TRANSITION_CONFIG_FILE.write_text(
        json.dumps(TRANSITION_DEFAULT_CONFIG, indent=4),
        encoding="utf-8"
    )

# ============================================================
# Session / Timer Size Configuration
# ============================================================

SESSION_FOLDER = SESSION_DIR
TIMER_SIZE_CONFIG_FILE = SESSION_DIR / "timer_size_config.json"

TIMER_SIZE_DEFAULT_CONFIG = {
    "timer_size": 420,  # Default main window timer size in pixels
}

timer_size_needs_default = False

if not TIMER_SIZE_CONFIG_FILE.exists():
    timer_size_needs_default = True
else:
    try:
        ts_data = json.loads(TIMER_SIZE_CONFIG_FILE.read_text(encoding="utf-8"))
        if not isinstance(ts_data, dict) or not ts_data:
            timer_size_needs_default = True
        elif any(key not in ts_data for key in TIMER_SIZE_DEFAULT_CONFIG):
            timer_size_needs_default = True
    except Exception:
        timer_size_needs_default = True

if timer_size_needs_default:
    TIMER_SIZE_CONFIG_FILE.write_text(
        json.dumps(TIMER_SIZE_DEFAULT_CONFIG, indent=4),
        encoding="utf-8"
    )

# ============================================================
# YouTube
# ============================================================

YOUTUBE_DIR = DATA_DIR / "youtube"
YOUTUBE_DIR.mkdir(parents=True, exist_ok=True)
YOUTUBE_CONFIG_FILE = YOUTUBE_DIR / "config.json"
DEFAULT_CONFIG = {
    "vlc_password": "mypassword",
    "vlc_url": "http://mypassword@127.0.0.1:8080/requests/status.json",
    "vlc_web_url": "http://127.0.0.1:8080/",
    "playing_volume": 36,
    "paused_volume": 80,
    "fade_time": 0.01,
    "fade_steps": 20,
    "ignore_pause_ms": 0,
    "backend_port": 5000,
    "auto_launch_vlc": True,
    "auto_open_http": True,
    "auto_start_backend": True,
}

needs_default = False

if not YOUTUBE_CONFIG_FILE.exists():
    needs_default = True
else:
    try:
        data = json.loads(YOUTUBE_CONFIG_FILE.read_text(encoding="utf-8"))

        # Empty JSON or not a dictionary
        if not isinstance(data, dict) or not data:
            needs_default = True

        # Missing required keys
        elif any(key not in data for key in DEFAULT_CONFIG):
            needs_default = True

    except Exception:
        # Invalid JSON
        needs_default = True

if needs_default:
    YOUTUBE_CONFIG_FILE.write_text(
        json.dumps(DEFAULT_CONFIG, indent=4),
        encoding="utf-8"
    )
# ============================================================
# Ensure every file exists
# ============================================================

JSON_FILES = [
    SPRINTS_FILE,
    SPRINTS_DONE_FILE,
    SCHEDULER_FILE,
    SESSIONS_FILE,
    LEARNING_PROFILE_FILE,
    STATISTICS_FILE,
    JOURNAL_FILE,
    NOTES_FILE,
    SETTINGS_FILE,
    THEME_FILE,
    CACHE_FILE,
    TASKS_DONE_FILE,
    YOUTUBE_CONFIG_FILE,
    TRANSITION_CONFIG_FILE,
    TIMER_SIZE_CONFIG_FILE,
]


def _create_file(file: Path):
    if file.exists():
        return

    if file.suffix.lower() == ".json":
        file.write_text("{}", encoding="utf-8")
    else:
        file.write_text("", encoding="utf-8")


for file in JSON_FILES:
    _create_file(file)