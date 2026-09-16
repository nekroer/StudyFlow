import json
from pathlib import Path
# Import the centralized secure path from paths.py
from app.backend.paths import SCHEDULER_FILE

class SchedulerStorage:
    """Handles JSON persistence, backups, and safe file writes for StudyFlow sessions."""
    
    def __init__(self, filepath: str = None):
        # Use SCHEDULER_FILE from paths.py by default, falling back if needed
        self.filepath = Path(filepath) if filepath else SCHEDULER_FILE
        
        # Ensure the parent directory exists in AppData
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict:
        """Load session data from disk, returning a default schema if file doesn't exist."""
        if not self.filepath.exists():
            return self._default_schema()
        
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and "sessions" in data:
                    return data
                return self._default_schema()
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Storage Warning] Could not parse {self.filepath}: {e}. Falling back to default.")
            return self._default_schema()

    def save(self, data: dict) -> bool:
        """Safely write session data to disk using an atomic write pattern."""
        temp_path = self.filepath.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
            temp_path.replace(self.filepath)
            return True
        except IOError as e:
            print(f"[Storage Error] Failed to save scheduler data: {e}")
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            return False

    def _default_schema(self) -> dict:
        return {
            "version": "1.0",
            "sessions": [],
            "sprint_tasks": [
                {"task_id": "task-1", "title": "Complete Chapter 4 Physics Problem Set", "category": "physics"},
                {"task_id": "task-2", "title": "Implement Timeline Zoom Bounds", "category": "coding"},
                {"task_id": "task-3", "title": "Review Lecture Notes on Thermodynamics", "category": "academics"}
            ]
        }