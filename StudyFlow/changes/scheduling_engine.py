from app.backend.sprints.sprints import SprintManager

class SchedulingEngine:
    """Core business logic for sessions, progress metrics, and timeline layout.
    Connects directly to SprintManager as the single source of truth."""
    
    def __init__(self, storage, sprint_manager: SprintManager = None):
        self.storage = storage
        self.sprint_manager = sprint_manager or SprintManager()

    def get_layout(self) -> dict:
        """Load data and prepare layout dictionary for the timeline canvas."""
        data = self.storage.load()
        sessions = data.get("sessions", [])
        
        processed_sessions = []
        for session in sessions:
            if session.get("completed") is True:
                continue
            updated_session = self._derive_session_status(session)
            processed_sessions.append(updated_session)
            
        return {
            "version": data.get("version", "1.0"),
            "quests": processed_sessions
        }

    def complete_session(self, quest_id: str) -> bool:
        """Mark a scheduled session occurrence as completed by quest_id."""
        data = self.storage.load()
        sessions = data.get("sessions", [])
        saved = False
        for session in sessions:
            if session.get("quest_id") == quest_id:
                session["completed"] = True
                saved = True
                break
        if saved:
            return self.storage.save(data)
        return False

    def get_available_sprint_tasks(self) -> list:
        """
        Pull live, incomplete tasks directly from SprintManager where completed is false.
        """
        self.sprint_manager.load_sprints()
        active_tasks = []
        
        for sprint in self.sprint_manager.sprints:
            if sprint.completed is False:
                active_tasks.append({
                    "task_id": sprint.id,
                    "title": sprint.title,
                    "category": sprint.category.lower(),
                    "logged_minutes": sprint.logged_minutes,
                    "notes": sprint.notes
                })
        return active_tasks

    def get_schedulable_tasks(self) -> list:
        """Alias for method compatibility."""
        return self.get_available_sprint_tasks()

    def check_collision(self, new_start_mins: int, new_duration: int, exclude_session_id: str = None) -> bool:
        """
        Validates whether a proposed session collides or overlaps with any existing session.
        Returns True if a collision/overlap is detected, False otherwise.
        """
        data = self.storage.load()
        sessions = data.get("sessions", [])
        new_end_mins = new_start_mins + new_duration

        for session in sessions:
            if exclude_session_id and session.get("quest_id") == exclude_session_id:
                continue
            
            start_str = session.get("start_time", "09:00")
            try:
                parts = start_str.split(":")
                exist_start_mins = int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                exist_start_mins = 540

            exist_duration = session.get("planned_duration_min", 60)
            exist_end_mins = exist_start_mins + exist_duration

            # Overlap condition: (StartA < EndB) and (EndA > StartB)
            if new_start_mins < exist_end_mins and new_end_mins > exist_start_mins:
                return True  # Collision detected

        return False

    def add_session(self, session_data: dict) -> bool:
        """Add a new study session after verifying no collisions occur."""
        start_str = session_data.get("start_time", "09:00")
        try:
            parts = start_str.split(":")
            start_mins = int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            start_mins = 540

        duration = session_data.get("planned_duration_min", 60)

        if self.check_collision(start_mins, duration):
            return False  # Blocked due to overlap

        data = self.storage.load()
        data.setdefault("sessions", []).append(session_data)
        return self.storage.save(data)

    def update_session(self, session_id: str, updated_fields: dict) -> bool:
        """Update fields for a specific session with overlap checks if time changes."""
        data = self.storage.load()
        sessions = data.get("sessions", [])
        
        target_session = None
        for session in sessions:
            if session.get("quest_id") == session_id:
                target_session = session
                break
                
        if not target_session:
            return False

        # If time or duration is being updated, verify collisions
        new_start_str = updated_fields.get("start_time", target_session.get("start_time", "09:00"))
        new_duration = updated_fields.get("planned_duration_min", target_session.get("planned_duration_min", 60))
        
        try:
            parts = new_start_str.split(":")
            new_start_mins = int(parts[0]) * 60 + int(parts[1])
        except (ValueError, IndexError):
            new_start_mins = 540

        if self.check_collision(new_start_mins, new_duration, exclude_session_id=session_id):
            return False  # Collision detected on update

        found = False
        for session in sessions:
            if session.get("quest_id") == session_id:
                session.update(updated_fields)
                found = True
                break
                
        if found:
            return self.storage.save(data)
        return False

    def delete_session(self, session_id: str) -> bool:
        """Remove a session by ID."""
        data = self.storage.load()
        sessions = data.get("sessions", [])
        
        new_sessions = [s for s in sessions if s.get("quest_id") != session_id]
        if len(new_sessions) < len(sessions):
            data["sessions"] = new_sessions
            return self.storage.save(data)
        return False

    def _derive_session_status(self, session: dict) -> dict:
        if "derived_status" not in session:
            session["derived_status"] = "FUTURE"
        return session