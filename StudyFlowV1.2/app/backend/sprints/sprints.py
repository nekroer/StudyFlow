import json
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pathlib import Path
from app.backend.paths import SPRINTS_FILE, SPRINTS_DONE_FILE

CATEGORIES = ["URGENT", "DEADLINES", "ADMIN", "CREATIVE"]

class Sprint:
    def __init__(self, sprint_id: str, title: str, category: str = "URGENT", 
                 logged_minutes: int = 0, created_at: Optional[str] = None,
                 completed: bool = False, notes: str = "", 
                 sessions: Optional[List[Dict[str, Any]]] = None,
                 due_date: Optional[str] = None):
        self.id = sprint_id
        self.title = title
        self.category = category if category in CATEGORIES else "URGENT"
        self.logged_minutes = logged_minutes
        self.created_at = created_at or datetime.now().isoformat()
        self.completed = completed
        self.notes = notes
        self.sessions = sessions if sessions is not None else []
        self.due_date = due_date

    @property
    def days_remaining(self) -> Optional[int]:
        if not self.due_date:
            return None
        try:
            due_dt = datetime.strptime(self.due_date, "%d-%m-%Y").date()
            return (due_dt - date.today()).days
        except ValueError:
            try:
                due_dt = datetime.strptime(self.due_date, "%Y-%m-%d").date()
                return (due_dt - date.today()).days
            except ValueError:
                return None

    def add_session_log(self, duration_mins: int):
        self.logged_minutes += duration_mins
        self.sessions.append({
            "timestamp": datetime.now().isoformat(),
            "duration_minutes": duration_mins
        })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "logged_minutes": self.logged_minutes,
            "created_at": self.created_at,
            "completed": self.completed,
            "notes": self.notes,
            "sessions": self.sessions,
            "due_date": self.due_date
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Sprint":
        return cls(
            sprint_id=data.get("id", ""),
            title=data.get("title", "Untitled Task"),
            category=data.get("category", "URGENT"),
            logged_minutes=data.get("logged_minutes", 0),
            created_at=data.get("created_at"),
            completed=data.get("completed", False),
            notes=data.get("notes", ""),
            sessions=data.get("sessions", []),
            due_date=data.get("due_date")
        )


class SprintManager:
    def __init__(self, storage_path: str | None = None):
        self.storage_path = storage_path or str(SPRINTS_FILE)
        self.sprints: List[Sprint] = []
        self._ensure_storage_directories()
        self.load_sprints()

    def _ensure_storage_directories(self):
        for path in [SPRINTS_FILE, SPRINTS_DONE_FILE]:
            directory = os.path.dirname(path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

    def auto_rebalance_sprints(self):
        changed = False
        for sprint in self.sprints:
            if sprint.completed or not sprint.due_date:
                continue

            days_left = sprint.days_remaining
            if days_left is None:
                continue

            if days_left <= 3 and sprint.category == "DEADLINES":
                sprint.category = "URGENT"
                changed = True
            elif days_left > 3 and sprint.category == "URGENT":
                sprint.category = "DEADLINES"
                changed = True

        if changed:
            self.save_sprints()

    def load_sprints(self) -> List[Sprint]:
        self.sprints = []
        if not os.path.exists(SPRINTS_FILE):
            return self.sprints

        try:
            with open(SPRINTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    s = Sprint.from_dict(item)
                    if not s.completed:
                        self.sprints.append(s)
            self.auto_rebalance_sprints()
        except (json.JSONDecodeError, OSError):
            self.sprints = []
        return self.sprints

    def save_sprints(self):
        self._ensure_storage_directories()
        
        active_sprints = [s.to_dict() for s in self.sprints if not s.completed]
        with open(SPRINTS_FILE, "w", encoding="utf-8") as f:
            json.dump(active_sprints, f, indent=4)

        completed_sprints = [s.to_dict() for s in self.sprints if s.completed]
        if completed_sprints:
            existing_done = []
            if os.path.exists(SPRINTS_DONE_FILE):
                try:
                    with open(SPRINTS_DONE_FILE, "r", encoding="utf-8") as f:
                        existing_done = json.load(f)
                except Exception:
                    existing_done = []
            
            done_dict = {item.get("id"): item for item in existing_done}
            for cs in completed_sprints:
                done_dict[cs["id"]] = cs

            with open(SPRINTS_DONE_FILE, "w", encoding="utf-8") as f:
                json.dump(list(done_dict.values()), f, indent=4)

    def add_sprint(self, title: str, category: str = "URGENT", notes: str = "", due_date: Optional[str] = None) -> Sprint:
        if due_date:
            try:
                due_dt = datetime.strptime(due_date, "%d-%m-%Y").date()
                days_left = (due_dt - date.today()).days
                category = "URGENT" if days_left <= 3 else "DEADLINES"
            except ValueError:
                try:
                    due_dt = datetime.strptime(due_date, "%Y-%m-%d").date()
                    days_left = (due_dt - date.today()).days
                    category = "URGENT" if days_left <= 3 else "DEADLINES"
                except ValueError:
                    pass

        sprint_id = f"task_{int(datetime.now().timestamp())}"
        new_sprint = Sprint(
            sprint_id=sprint_id,
            title=title,
            category=category,
            notes=notes,
            due_date=due_date
        )
        self.sprints.append(new_sprint)
        self.save_sprints()
        return new_sprint

    def log_session(self, sprint_id: str, duration_minutes: int):
        self.load_sprints()
        for sprint in self.sprints:
            if sprint.id == sprint_id:
                sprint.add_session_log(duration_minutes)
                self.save_sprints()
                return sprint
        return None

    def mark_completed(self, sprint_id: str) -> bool:
        self.load_sprints()
        for sprint in self.sprints:
            if sprint.id == sprint_id:
                sprint.completed = True
                self.save_sprints()
                self.sprints = [s for s in self.sprints if s.id != sprint_id]
                return True
        return False

    def delete_sprint(self, sprint_id: str) -> bool:
        self.load_sprints()
        initial_count = len(self.sprints)
        self.sprints = [s for s in self.sprints if s.id != sprint_id]
        if len(self.sprints) < initial_count:
            self.save_sprints()
            return True
        return False

    def toggle_completed(self, sprint_id: str):
        self.load_sprints()
        for sprint in self.sprints:
            if str(sprint.id) == str(sprint_id):
                sprint.completed = not sprint.completed
                self.save_sprints()
                break