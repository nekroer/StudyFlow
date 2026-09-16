from PySide6.QtWidgets import (
    QMainWindow,
    QStackedWidget,
    QDialog,
)

from PySide6.QtGui import QIcon
from pathlib import Path

from app.ui.dashboard import DashboardPage
from app.ui.session_page import SessionPage
from app.ui.video_page import VideoPage
from app.ui.scheduler_page import SchedulerPage
from app.ui.sprint_page import SprintPage
from app.ui.journal_page import JournalPage
from app.ui.stats_page import StatsPage
from app.ui.settings_page import SettingsPage

from app.backend.youtube.launcher import stop_everything
from app.utils.volume_controller import restore_volume
from app.backend.transition.controller import TransitionController
from app.backend.transition.transition_dialog import TransitionDialog


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        icon_path = (
                Path(__file__).parent
                / "app"
                / "assets"
                / "icons"
                / "logo.ico"
            )

        self.setWindowTitle("StudyFlow")
        self.setWindowIcon(
            QIcon(str(Path(icon_path)))
        )

        self.resize(1250, 780)

        # Initialize Transition Controller & Wire Signals
        self.transition_controller = TransitionController(self)
        self.transition_controller.transition_completed.connect(self._on_transition_completed)
        self.transition_controller.transition_cancelled.connect(self._on_transition_cancelled)
        self.transition_controller.show_dialog_requested.connect(self._on_show_transition_dialog)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # ---------------- Pages ---------------- #

        self.dashboard = DashboardPage(self)

        self.session = SessionPage(
            show_dashboard_cb=self.show_dashboard,
            parent=self
        )
        self.session.session_ended.connect(self.on_session_completed)

        self.video = VideoPage(self)

        self.scheduler = SchedulerPage(self)
        self.scheduler.navigate_to_dashboard.connect(self.show_dashboard)
        if hasattr(self.scheduler, 'back_requested'):
            self.scheduler.back_requested.connect(self.show_dashboard)
        else:
            self.scheduler.show_dashboard_cb = self.show_dashboard
        
        # Wire up scheduler signals for journal and session navigation
        self.scheduler.navigate_to_journal.connect(self.show_journal)
        self.scheduler.navigate_to_session.connect(self.start_scheduler_session)

        self.sprints = SprintPage(self)
        self.sprints.back_requested.connect(self.show_dashboard)
        
        # Connected to match start_study_session_requested signal from SprintPage
        self.sprints.start_study_session_requested.connect(self.start_task_session)

        self.journal = JournalPage(self)

        self.stats = StatsPage(self)

        self.settings = SettingsPage(self)

        # ---------------- Stack ---------------- #

        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.session)
        self.stack.addWidget(self.video)
        self.stack.addWidget(self.scheduler)
        self.stack.addWidget(self.sprints)
        self.stack.addWidget(self.journal)
        self.stack.addWidget(self.stats)
        self.stack.addWidget(self.settings)

        self.show_dashboard()

    # ---------------- Navigation ---------------- #

    def show_dashboard(self):
        self.stack.setCurrentWidget(self.dashboard)

    def show_session(self):
        self.stack.setCurrentWidget(self.session)

    def show_video(self):
        self.stack.setCurrentWidget(self.video)

    def show_scheduler(self):
        self.scheduler.refresh_scheduler_view()  # Reloads saved progress and tasks
        self.stack.setCurrentWidget(self.scheduler)
        

    def show_sprints(self):
        self.sprints.refresh_board()  # Reloads saved progress from file
        self.stack.setCurrentWidget(self.sprints)

    def show_journal(self):
        self.stack.setCurrentWidget(self.journal)

    def show_stats(self):
        self.stack.setCurrentWidget(self.stats)

    def show_settings(self):
        self.stack.setCurrentWidget(self.settings)

    def start_task_session(self, task_id: str = "", title: str = ""):
        """Switches to session page and optionally passes sprint task info if supported."""
        if hasattr(self.session, "load_task"):
            self.session.load_task(task_id, title)
        elif hasattr(self.session, "set_task"):
            self.session.set_task(task_id, title)

        self.show_session()

    def start_scheduler_session(self, task_name: str, details: dict):
        """
        Intercepts scheduled session launch and triggers the TransitionController pipeline.
        The controller will manage volume fading and emit show_dialog_requested.
        """
        # Safely pull duration from any of the possible key names in scheduler.json or payload
        duration = (
            details.get("duration") or 
            details.get("planned_duration_min") or 
            details.get("duration_mins") or 
            25
        )
        
        # Obtain actual Sprint task ID separately from quest_id
        task_id = details.get("task_id", "")
        quest_id = details.get("quest_id", "")
        
        session_payload = {
            "task_id": task_id,
            "quest_id": quest_id,
            "task_name": task_name,
            "title": task_name,
            "duration_mins": duration,
            "task_details": details.get("description", "Scheduled Session")
        }

        # Kick off the state machine / volume fade sequence
        self.transition_controller.start_transition_sequence(session_payload)

    def _on_show_transition_dialog(self, session_payload: dict):
        """Called by TransitionController when the dialog should be presented to the user."""
        # Pull the configured countdown duration (default to 120 if unavailable)
        countdown = 120
        if self.transition_controller and hasattr(self.transition_controller, "countdown_sec"):
            countdown = self.transition_controller.countdown_sec
        else:
            # Fallback check directly from config file if controller doesn't expose it yet
            try:
                from app.backend.paths import TRANSITION_CONFIG_FILE
                import json
                if TRANSITION_CONFIG_FILE.exists():
                    cfg = json.loads(TRANSITION_CONFIG_FILE.read_text(encoding="utf-8"))
                    countdown = cfg.get("countdown_sec", 120)
            except Exception:
                pass

        # Pass the configured countdown seconds into the dialog
        dialog = TransitionDialog(countdown_seconds=countdown, parent=self)
        
        # Run the dialog modally; exec() returns QDialog.Accepted if completed successfully
        if dialog.exec() == QDialog.Accepted:
            # Pass collected user inputs to the controller to finish the sequence
            self.transition_controller.complete_transition(dialog.result_data())
        else:
            self.transition_controller.cancel_transition()

    def _on_transition_cancelled(self):
        """Handles cancellation cleanly by ensuring user returns safely to scheduler/dashboard."""
        print("Transition sequence cancelled by user.")
        self.show_scheduler()

    def on_session_completed(self, elapsed_minutes: int = 0):
        """Refreshes the scheduler board and resets the transition state whenever a session is completed."""
        # Reset transition controller so it can handle subsequent sessions today
        if hasattr(self, "transition_controller"):
            self.transition_controller.reset_to_idle()

        if hasattr(self.scheduler, "refresh_board"):
            self.scheduler.refresh_board()
        elif hasattr(self.scheduler, "refresh_scheduler_view"):
            self.scheduler.refresh_scheduler_view()

    def _on_transition_completed(self, final_session_data: dict):
        """Called when TransitionController finishes successfully; handoff payload to SessionPage and trigger prep timer."""
        task_id = final_session_data.get("task_id", "")
        
        title = (
            final_session_data.get("title") or 
            final_session_data.get("task_name") or 
            "Focus Session"
        )
        
        # Safely catch duration from any possible key variant and fallback safely
        duration_mins = (
            final_session_data.get("duration_mins") or 
            final_session_data.get("duration") or 
            final_session_data.get("planned_duration_min") or 
            25
        )
        
        task_details = final_session_data.get("task_details", "Scheduled Session")

        # 1. Switch the view to the Session Page
        self.show_session()

        # 2. Load the task into the SessionPage with the exact duration from scheduler
        if hasattr(self.session, "load_task"):
            self.session.load_task(
                task_id=task_id,
                title=title,
                details=task_details,
                target_minutes=duration_mins  # Use duration_mins here
            )

        # 3. Store the full transition payload so it gets logged later
        self.session.active_session_data = final_session_data

        # 4. Trigger start_timer() which opens the PrepDialog preparation countdown
        if hasattr(self.session, "start_timer"):
            self.session.start_timer()

    # ---------------- Cleanup ---------------- #

    def closeEvent(self, event):

        print("StudyFlow closing...")

        try:
            restore_volume()
        except Exception as e:
            print(e)

        try:
            stop_everything()
        except Exception as e:
            print(e)

        event.accept()