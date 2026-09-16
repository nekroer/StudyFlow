from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QSplitter, QScrollArea
)
from PySide6.QtCore import Qt, QTimer, Signal

from app.backend.paths import SCHEDULER_FILE, SESSIONS_FILE
from app.backend.scheduler.scheduler_storage import SchedulerStorage
from app.backend.scheduler.scheduling_engine import SchedulingEngine
from app.backend.scheduler.timeline_canvas import TimelineCanvas, build_scheduler_ui_layout
from app.backend.scheduler.add_scheduled_block_dialog import AddScheduledBlockDialog

class SchedulerPage(QWidget):
    """UI Controller linking storage, sprint task connector engine, and timeline renderer view with modern progress bar, sidebar inspector, and journal redirect."""
    
    navigate_to_journal = Signal()
    navigate_to_session = Signal(str, dict)  # (task_name, details)
    navigate_to_dashboard = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.storage = SchedulerStorage(SCHEDULER_FILE)
        self.engine = SchedulingEngine(self.storage)
        
        self.current_time_mins = self._get_current_minutes()
        self.selected_session_id = None
        
        # Optional callback to query MainWindow's TransitionController state
        self.get_transition_state_cb = None
        
        self._init_ui()
        
        # Timer to update daily progress bar & playhead every second
        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self._on_periodic_refresh)
        self.progress_timer.start(1000)

        self.refresh_scheduler_view()

    def _get_current_minutes(self) -> int:
        now = datetime.now()
        return now.hour * 60 + now.minute

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # ----------------------------------------------------
        # 1. Modern Daily Progress Bar (Top)
        # ----------------------------------------------------
        progress_container = QWidget()
        progress_container.setFixedHeight(36)
        progress_container.setStyleSheet("""
            QWidget {
                background-color: #1a1a20;
                border: 1px solid #2d2d38;
                border-radius: 6px;
            }
        """)
        prog_layout = QHBoxLayout(progress_container)
        prog_layout.setContentsMargins(12, 0, 12, 0)

        self.prog_label = QLabel("Day Progress:")
        self.prog_label.setStyleSheet("color: #a0a0b0; font-size: 11px; border: none;")
        prog_layout.addWidget(self.prog_label)

        self.prog_bar_bg = QFrame()
        self.prog_bar_bg.setFixedHeight(8)
        self.prog_bar_bg.setStyleSheet("background-color: #272730; border-radius: 4px; border: none;")
        self.prog_bar_fill = QFrame(self.prog_bar_bg)
        self.prog_bar_fill.setFixedHeight(8)
        self.prog_bar_fill.setStyleSheet("background-color: #4F8EF7; border-radius: 4px; border: none;")
        self.prog_bar_fill.setFixedWidth(0)
        prog_layout.addWidget(self.prog_bar_bg, stretch=1)

        self.prog_pct_lbl = QLabel("0%")
        self.prog_pct_lbl.setStyleSheet("color: #ffffff; font-size: 11px; font-weight: bold; border: none;")
        prog_layout.addWidget(self.prog_pct_lbl)

        main_layout.addWidget(progress_container)

        # ----------------------------------------------------
        # 2. Top Toolbar & Action Controls
        # ----------------------------------------------------
        toolbar_layout = QHBoxLayout()
        
        date_str = datetime.now().strftime("%A, %B %d")
        title_lbl = QLabel(f"Today · {date_str}")
        title_lbl.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold; font-family: 'Segoe UI';")
        toolbar_layout.addWidget(title_lbl)
        
        toolbar_layout.addStretch()

        self.back_dashboard_btn = QPushButton("← Dashboard")
        self.back_dashboard_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e24;
                color: #ffffff;
                border: 1px solid #2d2d38;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #272730; }
        """)
        self.back_dashboard_btn.clicked.connect(self.navigate_to_dashboard.emit)
        toolbar_layout.addWidget(self.back_dashboard_btn)

        # Temporary Debug Button
        self.debug_btn = QPushButton("🐛 Debug State")
        self.debug_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e24;
                color: #ffffff;
                border: 1px solid #2d2d38;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #272730; }
        """)
        self.debug_btn.clicked.connect(self._on_debug_clicked)
        toolbar_layout.addWidget(self.debug_btn)

        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e24;
                color: #ffffff;
                border: 1px solid #2d2d38;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #272730; }
        """)
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        toolbar_layout.addWidget(self.reset_btn)

        self.add_btn = QPushButton("+ Plan Session")
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4F8EF7;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QPushButton:hover { background-color: #3b75e0; }
        """)
        self.add_btn.clicked.connect(self.open_add_dialog_default)
        toolbar_layout.addWidget(self.add_btn)

        main_layout.addLayout(toolbar_layout)

        # ----------------------------------------------------
        # 3. Main Splitter Area (Timeline Canvas + Inspector Sidebar)
        # ----------------------------------------------------
        self.canvas = TimelineCanvas(self)

        self.inspector_panel = QWidget()
        self.inspector_panel.setStyleSheet("""
            QWidget {
                background-color: #141417;
                border: 1px solid #2d2d38;
                border-radius: 8px;
            }
            QLabel { color: #a0a0b0; border: none; }
        """)
        
        insp_layout = QVBoxLayout(self.inspector_panel)
        insp_layout.setContentsMargins(16, 16, 16, 16)
        insp_layout.setSpacing(12)

        self.insp_title = QLabel("Select a session")
        self.insp_title.setStyleSheet("color: #ffffff; font-size: 15px; font-weight: bold; border: none;")
        insp_layout.addWidget(self.insp_title)

        self.insp_meta = QLabel("Duration: -- | Completion: --%")
        insp_layout.addWidget(self.insp_meta)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #2d2d38; border: none;")
        insp_layout.addWidget(sep)

        insp_layout.addWidget(QLabel("Micro-Objectives Breakdown:"))
        
        self.objectives_scroll = QScrollArea()
        self.objectives_scroll.setWidgetResizable(True)
        self.objectives_scroll.setStyleSheet("border: none; background: transparent;")
        self.objectives_content = QWidget()
        self.objectives_layout = QVBoxLayout(self.objectives_content)
        self.objectives_layout.setContentsMargins(0, 0, 0, 0)
        self.objectives_scroll.setWidget(self.objectives_content)
        insp_layout.addWidget(self.objectives_scroll, stretch=1)

        self.start_session_btn = QPushButton("Start Session")
        self.start_session_btn.setEnabled(False)
        self.start_session_btn.setStyleSheet("""
            QPushButton {
                background-color: #10b981;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #272730;
                color: #52525b;
            }
            QPushButton:hover:enabled { background-color: #059669; }
        """)
        self.start_session_btn.clicked.connect(self._on_start_session_clicked)
        insp_layout.addWidget(self.start_session_btn)

        splitter = build_scheduler_ui_layout(self, self.canvas, self.inspector_panel)
        splitter.setSizes([700, 320])

        main_layout.addWidget(splitter, stretch=1)

        # ----------------------------------------------------
        # Connect Signals (Only once, after self.canvas exists)
        # ----------------------------------------------------
        self.canvas.block_selected.connect(self.open_add_dialog_at_time)
        self.canvas.quest_selected.connect(self.handle_session_selected)
        
        # ----------------------------------------------------
        # 4. Floating Brain Dump Button (Bottom Left Overlay)
        # ----------------------------------------------------
        self.brain_dump_btn = QPushButton("🧠 Brain Dump", self)
        self.brain_dump_btn.setFixedSize(130, 42)
        self.brain_dump_btn.setStyleSheet("""
            QPushButton {
                background-color: #4F8EF7;
                color: white;
                border: none;
                border-radius: 21px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #3b75e0; }
        """)
        self.brain_dump_btn.clicked.connect(self._on_brain_dump_clicked)
        self._update_brain_dump_position()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_brain_dump_position()

    def _update_brain_dump_position(self):
        self.brain_dump_btn.move(24, self.height() - 66)
        self.brain_dump_btn.raise_()

    def _on_periodic_refresh(self):
        self.current_time_mins = self._get_current_minutes()
        total_day_mins = 24 * 60
        pct = min(100.0, (self.current_time_mins / total_day_mins) * 100)
        
        fill_width = int((self.prog_bar_bg.width() * pct) / 100) if self.prog_bar_bg.width() > 0 else 0
        self.prog_bar_fill.setFixedWidth(fill_width)
        self.prog_pct_lbl.setText(f"{pct:.1f}%")

        self.refresh_scheduler_view()

    def refresh_scheduler_view(self):
        layout_data = self.engine.get_layout()
        self.canvas.render_timeline(layout_data, self.current_time_mins)

    def _on_reset_clicked(self):
        """Resets the scheduler by clearing all sessions in storage, engine, and canvas."""
        default_data = self.storage._default_schema()
        default_data["sessions"] = []
        self.storage.save(default_data)

        if hasattr(self.engine, "quests"):
            self.engine.quests = []
        if hasattr(self.engine, "sessions"):
            self.engine.sessions = []

        self.selected_session_id = None
        if hasattr(self, "handle_session_selected"):
            self.handle_session_selected("")
            
        self.refresh_scheduler_view()

    def _on_debug_clicked(self):
        """Temporary debug button handler to print TransitionController state."""
        state = "UNKNOWN"
        if self.get_transition_state_cb:
            try:
                state = self.get_transition_state_cb()
            except Exception:
                pass
        else:
            # Fallback path checking parent hierarchy for transition_controller
            p = self.parent()
            while p:
                if hasattr(p, "transition_controller") and p.transition_controller:
                    tc = p.transition_controller
                    state = getattr(tc, "state", "UNKNOWN")
                    break
                p = p.parent() if hasattr(p, "parent") else None

        if hasattr(state, "name"):
            state = state.name
        elif hasattr(state, "value"):
            state = state.value

        print(f"[StudyFlow DEBUG] Transition State: {state}")

    def open_add_dialog_default(self):
        self.open_add_dialog_at_time("academics", max(540, self.current_time_mins))

    def open_add_dialog_at_time(self, category: str, start_mins: int, duration_min: int = 60):
        if start_mins < self.current_time_mins:
            return  # Past lockout check

        sprint_tasks = self.engine.get_available_sprint_tasks()
        existing_sessions = self.engine.get_layout().get("quests", [])
        
        dialog = AddScheduledBlockDialog(
            sprint_tasks=sprint_tasks, 
            existing_sessions=existing_sessions,
            default_category=category, 
            default_start_mins=start_mins,
            default_duration_min=duration_min,
            parent=self
        )
        if dialog.exec():
            session_data = dialog.get_session_data()
            if session_data:
                self.engine.add_session(session_data)
                self.refresh_scheduler_view()

    def handle_session_selected(self, session_id: str):
        self.selected_session_id = session_id
        if session_id:
            self.canvas.select_quest(session_id)
        
        layout_data = self.engine.get_layout()
        selected_session = None
        for s in layout_data.get("quests", []):
            if s.get("quest_id") == session_id:
                selected_session = s
                break
                
        if selected_session:
            self.insp_title.setText(selected_session.get("title", "Session"))
            duration = selected_session.get("planned_duration_min", 60)
            comp_pct = selected_session.get("completion_percentage", 0)
            self.insp_meta.setText(f"Duration: {duration} mins | Completion: {comp_pct}%")
            
            while self.objectives_layout.count():
                item = self.objectives_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
            objectives = selected_session.get("objectives", [
                "Review core prerequisite notes",
                "Execute primary problem set / workflow",
                "Verify final output & log progress"
            ])
            for obj in objectives:
                lbl = QLabel(f"▪ {obj}")
                lbl.setStyleSheet("color: #d0d0d8; font-size: 12px; border: none; padding: 2px 0;")
                self.objectives_layout.addWidget(lbl)
            self.objectives_layout.addStretch()

            self.start_session_btn.setEnabled(True)
        else:
            self.insp_title.setText("Select a session")
            self.insp_meta.setText("Duration: -- | Completion: --%")
            while self.objectives_layout.count():
                item = self.objectives_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.objectives_layout.addStretch()
            self.start_session_btn.setEnabled(False)

    def _on_start_session_clicked(self):
        if not self.selected_session_id:
            return
        layout_data = self.engine.get_layout()
        session_to_start = None
        for s in layout_data.get("quests", []):
            if s.get("quest_id") == self.selected_session_id:
                session_to_start = s
                break
        if session_to_start:
            task_name = session_to_start.get("title", "Study Session")
            details = {
                "duration": session_to_start.get("planned_duration_min", 60),
                "category": session_to_start.get("category", "academics"),
                "objectives": session_to_start.get("objectives", [])
            }
            self.navigate_to_session.emit(task_name, details)

    def _on_brain_dump_clicked(self):
        self.navigate_to_journal.emit()