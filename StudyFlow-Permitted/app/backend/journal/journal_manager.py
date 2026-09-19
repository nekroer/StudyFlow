import re
from datetime import datetime

from app.backend.sprints.sprints import SprintManager
from app.backend.paths import JOURNAL_DIR

SPRINT_MANAGER = SprintManager()

# ----------------------------------------
# Timestamp
# ----------------------------------------

def timestamp():
    return datetime.now().strftime("%I:%M %p")


# ----------------------------------------
# Helpers
# ----------------------------------------

def today_name():
    return datetime.now().strftime("%d-%m-%Y")


def today_file():
    return JOURNAL_DIR / f"{today_name()}.md"


# ----------------------------------------
# Create today's journal if missing
# ----------------------------------------

def ensure_today_exists():

    file = today_file()

    if file.exists():
        return

    header = (
        f"# {datetime.now().strftime('%A, %d %B %Y')}\n\n"
        f"{timestamp()}\n\n"
    )

    file.write_text(
        header,
        encoding="utf-8"
    )


# ----------------------------------------
# Load today's journal
# ----------------------------------------

def load_today():

    ensure_today_exists()

    return today_file().read_text(
        encoding="utf-8"
    )


# ----------------------------------------
# Task Parsing & Save journal text (Idempotent)
# ----------------------------------------

def process_journal_entry(text: str) -> str:
    """
    Parses journal text for tasks starting with 'todo:' or '- [ ] todo:'.
    Extracts tags, creates sprints, and marks imported items as 'imported:'
    so they are never processed twice. Returns the updated text.
    """
    
    # Matches lines starting with 'todo:' or '- [ ] todo:' (case-insensitive)
    todo_pattern = re.compile(r'^(?P<prefix>\s*(?:-\s*\[\s*\]\s*)?)todo:\s*(?P<task>.*)$', re.IGNORECASE | re.MULTILINE)
    
    def replace_todo(match):
        prefix = match.group('prefix')
        raw_task = match.group('task').strip()
        if not raw_task:
            return match.group(0)
            
        due_date = None
        category = "URGENT"  # Default category for undated backlog tasks
        
        # 1. Parse due date tag like :01-08-2026 or :1-8-2026
        date_match = re.search(r':(\d{1,2}-\d{1,2}-\d{4})', raw_task)
        if date_match:
            due_date = date_match.group(1)
            raw_task = raw_task.replace(date_match.group(0), "").strip()
            
        # 2. Parse category tags (#admin or #creative)
        if "#admin" in raw_task.lower():
            category = "ADMIN"
            raw_task = re.sub(r'#admin', '', raw_task, flags=re.IGNORECASE).strip()
        elif "#creative" in raw_task.lower():
            category = "CREATIVE"
            raw_task = re.sub(r'#creative', '', raw_task, flags=re.IGNORECASE).strip()

        # Clean up double spaces left over from removing tags
        clean_title = " ".join(raw_task.split())
        
        if clean_title:
            SPRINT_MANAGER.add_sprint(
                title=clean_title,
                category=category,
                due_date=due_date
            )
            # Rewrite line to mark it as imported so it isn't parsed again next time
            return f"{prefix}imported: {raw_task}"
            
        return match.group(0)

    updated_text = todo_pattern.sub(replace_todo, text)
    return updated_text


def save_today(text):

    ensure_today_exists()

    processed_text = process_journal_entry(text)

    today_file().write_text(
        processed_text,
        encoding="utf-8"
    )
    return processed_text


# ----------------------------------------
# List journals
# ----------------------------------------

def list_journals():

    ensure_today_exists()

    valid_files = []

    for file in JOURNAL_DIR.glob("*.md"):
        try:
            datetime.strptime(file.stem, "%d-%m-%Y")
            valid_files.append(file)
        except ValueError:
            continue

    files = sorted(
        valid_files,
        key=lambda f: datetime.strptime(f.stem, "%d-%m-%Y"),
        reverse=True
    )

    return [f.stem for f in files]


# ----------------------------------------
# Load any journal
# ----------------------------------------

def load_journal(name):

    file = JOURNAL_DIR / f"{name}.md"

    if file.exists():
        return file.read_text(
            encoding="utf-8"
        )

    return ""

def save_journal(name: str, text: str):
    file = JOURNAL_DIR / f"{name}.md"

    processed_text = process_journal_entry(text)

    file.write_text(
        processed_text,
        encoding="utf-8"
    )
    return processed_text