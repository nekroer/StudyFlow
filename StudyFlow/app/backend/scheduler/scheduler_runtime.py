from datetime import datetime, time
from PySide6.QtCore import QObject, Signal, QTimer


class SchedulerRuntime(QObject):
    """
    Monitors current time against scheduled sessions and triggers transitions
    at the correct offset (fade duration + countdown duration).
    """
    transition_trigger_requested = Signal(dict)  # Emits session dict when transition should start
    session_missed = Signal(dict)                # Emits session dict if missed past grace period
    runtime_error = Signal(str)

    def __init__(self, scheduling_engine, fade_duration_sec: int = 180, countdown_sec: int = 120, parent=None):
        super().__init__(parent)
        self.engine = scheduling_engine
        self.fade_duration_sec = fade_duration_sec
        self.countdown_sec = countdown_sec
        self.total_transition_sec = fade_duration_sec + countdown_sec  # e.g., 300s = 5 mins
        
        self._triggered_sessions = set()  # Track session IDs/keys triggered today to prevent duplicates
        
        # Poll clock every 1 second
        self.poll_timer = QTimer(self)
        self.poll_timer.setInterval(1000)
        self.poll_timer.timeout.connect(self._check_schedule)

    def start_monitoring(self):
        """Starts the runtime clock monitoring loop."""
        if not self.poll_timer.isActive():
            self.poll_timer.start()

    def stop_monitoring(self):
        """Stops the runtime clock monitoring loop."""
        if self.poll_timer.isActive():
            self.poll_timer.stop()

    def _parse_time_str(self, time_str: str) -> time:
        """Parses 'HH:MM' string into a datetime.time object."""
        try:
            parts = time_str.strip().split(":")
            return time(int(parts[0]), int(parts[1]))
        except Exception:
            return None

    def _check_schedule(self):
        """Evaluates current system time against today's loaded sessions."""
        try:
            now = datetime.now()
            current_time = now.time()
            
            # Fetch sessions scheduled for today via the scheduling engine
            sessions = self.engine.get_today_sessions() if hasattr(self.engine, "get_today_sessions") else []
            
            for session in sessions:
                session_id = session.get("quest_id") or session.get("task_id") or session.get("title")
                start_time_str = session.get("start_time")
                
                if not start_time_str:
                    continue
                
                target_time = self._parse_time_str(start_time_str)
                if not target_time:
                    continue
                
                # Convert times to total seconds since midnight for clean comparisons
                now_secs = current_time.hour * 3600 + current_time.minute * 60 + current_time.second
                target_secs = target_time.hour * 3600 + target_time.minute * 60 + target_time.second
                
                # Calculate when the transition sequence must begin (target_time minus total transition window)
                transition_start_secs = target_secs - self.total_transition_sec
                
                session_key = f"{session_id}_{start_time_str}_{now.date().isoformat()}"
                
                if session_key in self._triggered_sessions:
                    continue

                # Case 1: Exact window hit to start transition sequence
                if transition_start_secs <= now_secs < target_secs:
                    self._triggered_sessions.add(session_key)
                    session["derived_status"] = "TRANSITIONING"
                    self.transition_trigger_requested.emit(session)
                    break
                
                # Case 2: Application launched late (Grace Period policy: up to 10 mins past start time)
                grace_period_secs = 600
                if target_secs <= now_secs <= (target_secs + grace_period_secs):
                    self._triggered_sessions.add(session_key)
                    session["derived_status"] = "TRANSITIONING"
                    self.transition_trigger_requested.emit(session)
                    break
                elif now_secs > (target_secs + grace_period_secs):
                    # Missed past grace period
                    if session.get("derived_status") != "MISSED":
                        session["derived_status"] = "MISSED"
                        self._triggered_sessions.add(session_key)
                        self.session_missed.emit(session)

        except Exception as e:
                self.runtime_error.emit(str(e))