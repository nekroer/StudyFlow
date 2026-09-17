import math
import struct
from pathlib import Path
from datetime import datetime
import json
from PySide6.QtCore import QTimer, Qt, QByteArray, Signal as pyqtSignal
from PySide6.QtGui import QColor, QFont
from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QDialog,
    QLineEdit,
    QTextEdit,
    QFormLayout,
    QDialogButtonBox,
    QMessageBox,
    QFrame,
    QApplication,
)
from app.ui.components.circular_timer import CircularTimer
from app.backend.sprints.sprints import SprintManager
from app.backend.paths import TASKS_DONE_FILE, TIMER_SIZE_CONFIG_FILE
from app.backend.transition.early_exit_dialog import EarlyExitDialog


class FloatingTimerWindow(QWidget):
    """
    An Always-on-Top Independent Floating Mini Timer window that stays visible 
    over other applications while you work in the background.
    """
    pauseRequested = pyqtSignal()
    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(None)
        self.setWindowTitle("StudyFlow Mini Timer")
        self.setFixedSize(320, 380)
        
        self.setWindowFlags(
            Qt.WindowType.Window | 
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.CustomizeWindowHint | 
            Qt.WindowType.WindowTitleHint | 
            Qt.WindowType.WindowCloseButtonHint
        )
        
        self.setStyleSheet("background-color: #18181c; color: white;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        self.task_label = QLabel("Focus Session", self)
        self.task_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #0096D6;")
        self.task_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.task_label)

        self.mini_timer = CircularTimer(self)
        self.mini_timer.setFixedSize(220, 220)
        self.mini_timer.setEnabled(False)
        layout.addWidget(self.mini_timer, alignment=Qt.AlignmentFlag.AlignCenter)

        self.time_label = QLabel("00:00", self)
        self.time_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #ffffff;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.time_label)

        btn_layout = QHBoxLayout()
        self.btn_pause = QPushButton("Pause", self)
        self.btn_pause.setStyleSheet("""
            QPushButton {
                background-color: #E67E22; color: white;
                font-size: 13px; font-weight: bold; border-radius: 6px; padding: 7px 14px;
            }
            QPushButton:hover { background-color: #D35400; }
        """)
        self.btn_pause.clicked.connect(self.pauseRequested.emit)
        btn_layout.addWidget(self.btn_pause)

        self.btn_dock = QPushButton("Dock Back", self)
        self.btn_dock.setStyleSheet("""
            QPushButton {
                background-color: #2b2b36; color: #e0e0e0;
                font-size: 13px; font-weight: bold; border-radius: 6px; padding: 7px 14px;
                border: 1px solid #3f3f4e;
            }
            QPushButton:hover { background-color: #3f3f4e; color: white; }
        """)
        self.btn_dock.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_dock)

        layout.addLayout(btn_layout)

    def update_display(self, task_name: str, seconds: int, max_seconds: int, theme_key: str, theme_hex: str, is_paused: bool):
        self.task_label.setText(task_name if task_name else "Focus Session")
        self.mini_timer.set_duration(seconds)
        self.mini_timer.set_theme(theme_key, theme_hex)
        
        mins = seconds // 60
        secs = seconds % 60
        self.time_label.setText(f"{mins:02d}:{secs:02d}")

        if is_paused:
            self.btn_pause.setText("Resume")
            self.btn_pause.setStyleSheet("""
                QPushButton {
                    background-color: #27AE60; color: white;
                    font-size: 13px; font-weight: bold; border-radius: 6px; padding: 7px 14px;
                }
                QPushButton:hover { background-color: #1E8449; }
            """)
        else:
            self.btn_pause.setText("Pause")
            self.btn_pause.setStyleSheet("""
                QPushButton {
                    background-color: #E67E22; color: white;
                    font-size: 13px; font-weight: bold; border-radius: 6px; padding: 7px 14px;
                }
                QPushButton:hover { background-color: #D35400; }
            """)

    def closeEvent(self, event):
        self.closed.emit()
        super().closeEvent(event)


class StartTaskDialog(QDialog):
    def __init__(self, task_name: str = "", task_details: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Start Focus Mission")
        self.setMinimumWidth(360)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e24; color: white; }
            QLabel { color: #e0e0e0; font-size: 14px; font-weight: bold; }
            QLineEdit, QTextEdit {
                background-color: #2b2b36; color: white;
                border: 1px solid #3f3f4e; border-radius: 6px; padding: 8px; font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus { border: 1px solid #0096D6; }
        """)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.task_name_input = QLineEdit(self)
        self.task_name_input.setText(str(task_name) if task_name else "")
        self.task_name_input.setPlaceholderText("e.g. Physics - Electrostatics")

        self.task_details_input = QTextEdit(self)
        self.task_details_input.setPlainText(str(task_details) if task_details else "")
        self.task_details_input.setPlaceholderText("e.g. Solving 20 PYQs (Optional)")
        self.task_details_input.setMaximumHeight(100)

        form.addRow("Task Name *:", self.task_name_input)
        form.addRow("Details:", self.task_details_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def validate_and_accept(self):
        if not self.task_name_input.text().strip():
            QMessageBox.warning(self, "Required Field", "Please enter a Task Name to begin.")
            return
        self.accept()

    def get_data(self):
        return {
            "task_name": self.task_name_input.text().strip(),
            "task_details": self.task_details_input.toPlainText().strip(),
        }


class PrepDialog(QDialog):
    def __init__(self, task_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preparation Phase")
        self.setFixedSize(450, 380)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
        self.setStyleSheet("background-color: #18181c; color: white;")

        self.prep_seconds_remaining = 120
        self.total_prep_seconds = 0
        self.is_overtime = False
        self.tick_counter = 0

        self.audio_sink = None
        self.audio_io = None
        self._init_audio()

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(25, 25, 25, 25)

        title_label = QLabel(f"Preparing for: <b>{task_name}</b>", self)
        title_label.setStyleSheet("font-size: 16px; color: #0096D6;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        sub_label = QLabel("Clear desk • Open materials • Grab water", self)
        sub_label.setStyleSheet("font-size: 13px; color: #a0a0a0; margin-bottom: 15px;")
        sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_label)

        self.timer_label = QLabel("02:00", self)
        self.timer_label.setStyleSheet("font-size: 56px; font-weight: bold; color: #27AE60; margin: 10px 0;")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.timer_label)

        self.btn_ready = QPushButton("I'm Ready — Begin Session", self)
        self.btn_ready.setStyleSheet("""
            QPushButton {
                background-color: #27AE60; color: white;
                font-size: 18px; font-weight: bold; border-radius: 10px; padding: 14px 28px;
            }
            QPushButton:hover { background-color: #1E8449; }
        """)
        self.btn_ready.clicked.connect(self.accept_ready)
        layout.addWidget(self.btn_ready)

        self.prep_timer = QTimer(self)
        self.prep_timer.setInterval(200)
        self.prep_timer.timeout.connect(self._tick)
        self.prep_timer.start()

    def _init_audio(self):
        fmt = QAudioFormat()
        fmt.setSampleRate(44100)
        fmt.setChannelCount(1)
        fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

        default_device = QMediaDevices.defaultAudioOutput()
        if not default_device.isNull():
            self.audio_sink = QAudioSink(default_device, fmt, self)
            self.audio_io = self.audio_sink.start()

    def _play_tick_sound(self):
        if not self.audio_sink or not self.audio_io:
            return

        sample_rate = 44100
        num_samples = int(sample_rate * 0.03)
        freq = 1200 if self.is_overtime else 800

        byte_data = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            val = int(32767 * math.sin(2 * math.pi * freq * t) * math.exp(-t * 180))
            byte_data.extend(struct.pack("<h", val))

        if self.audio_io.isOpen():
            self.audio_io.write(QByteArray(bytes(byte_data)))

    def _tick(self):
        self.tick_counter += 1

        if self.tick_counter % 5 == 0:
            if not self.is_overtime:
                self.prep_seconds_remaining -= 1
                if self.prep_seconds_remaining <= 0:
                    self.is_overtime = True
                    self.timer_label.setStyleSheet("font-size: 56px; font-weight: bold; color: #E74C3C; margin: 10px 0;")
            
            self.total_prep_seconds += 1

        if self.is_overtime:
            overtime_sec = self.total_prep_seconds - 120
            self.timer_label.setText(f"-{overtime_sec // 60:02d}:{overtime_sec % 60:02d}")
        else:
            self.timer_label.setText(f"{self.prep_seconds_remaining // 60:02d}:{self.prep_seconds_remaining % 60:02d}")

        if self.is_overtime:
            if self.tick_counter % 2 == 0:
                self._play_tick_sound()
        elif 90 < self.prep_seconds_remaining <= 120:
            if self.tick_counter % 15 == 0:
                self._play_tick_sound()
        elif 60 < self.prep_seconds_remaining <= 90:
            if self.tick_counter % 10 == 0:
                self._play_tick_sound()
        elif 20 < self.prep_seconds_remaining <= 60:
            if self.tick_counter % 5 == 0:
                self._play_tick_sound()
        elif 0 <= self.prep_seconds_remaining <= 20:
            if self.tick_counter % 3 == 0:
                self._play_tick_sound()

    def _stop_audio_and_timer(self):
        if self.prep_timer.isActive():
            self.prep_timer.stop()
        if self.audio_sink:
            self.audio_sink.stop()
            self.audio_sink = None

    def accept_ready(self):
        self._stop_audio_and_timer()
        self.accept()

    def reject(self):
        self._stop_audio_and_timer()
        super().reject()

    def closeEvent(self, event):
        self._stop_audio_and_timer()
        super().closeEvent(event)

    def get_prep_duration_sec(self) -> int:
        return self.total_prep_seconds


class SessionPage(QWidget):
    session_ended = pyqtSignal(int)

    def __init__(self, show_dashboard_cb=None, parent=None):
        super().__init__(parent)
        self.show_dashboard_cb = show_dashboard_cb

        self.default_seconds = 3600
        self.remaining_seconds = self.default_seconds
        self.initial_target_seconds = self.default_seconds
        
        self.active_session_data = None
        self.is_session_active = False
        self.floating_window = None
        self._session_end_emitted = False

        self.themes = [
            {"key": "light_blue", "name": "Light Blue", "hex": "#0096D6"},
            {"key": "dark_green", "name": "Dark Green", "hex": "#1E8449"},
            {"key": "classic_red", "name": "Classic Red", "hex": "#E74C3C"},
            {"key": "rainbow", "name": "Rainbow", "hex": None},
        ]
        self.theme_index = 0

        self.sprint_task_id = None
        self.prefilled_task_name = ""
        self.prefilled_task_details = ""

        # Main Layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 10)
        main_layout.setSpacing(10)

        # 1. Top Navigation Bar
        top_bar = QHBoxLayout()
        nav_btn_style = """
            QPushButton {
                background-color: #2b2b36; color: #e0e0e0;
                font-size: 13px; font-weight: bold;
                border: 1px solid #3f3f4e; border-radius: 6px; padding: 6px 14px;
            }
            QPushButton:hover { background-color: #3f3f4e; color: white; }
        """
        self.btn_dashboard = QPushButton("← Dashboard", self)
        self.btn_theme_toggle = QPushButton(f"🎨 Theme: {self.themes[self.theme_index]['name']}", self)
        self.btn_popout = QPushButton("🗗 Popout Floating Timer", self)
        self.btn_view_logs = QPushButton("📁 View Tasks Done List", self)

        self.btn_dashboard.setStyleSheet(nav_btn_style)
        self.btn_theme_toggle.setStyleSheet(nav_btn_style)
        self.btn_popout.setStyleSheet(nav_btn_style)
        self.btn_view_logs.setStyleSheet(nav_btn_style)

        top_bar.addWidget(self.btn_dashboard)
        top_bar.addWidget(self.btn_theme_toggle)
        top_bar.addWidget(self.btn_popout)
        top_bar.addStretch()
        top_bar.addWidget(self.btn_view_logs)
        main_layout.addLayout(top_bar)

        # 2. Main Content Center Container
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(10)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)

        # Circular Timer Instance (Self-managed dimensions from config)
        self.circular_timer = CircularTimer(self)
        self.circular_timer.set_duration(self.default_seconds)
        
        current_theme = self.themes[self.theme_index]
        self.circular_timer.set_theme(current_theme["key"], current_theme["hex"])
        
        center_layout.addWidget(self.circular_timer, alignment=Qt.AlignmentFlag.AlignCenter)

        # White Digital Time Display Below Circular Timer
        self.time_label = QLabel(self._format_time(self.default_seconds), self)
        self.time_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #ffffff; margin-top: 2px;")
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.time_label)

        # Completion Badge Overlay
        self.completion_badge = QLabel(self)
        self.completion_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.completion_badge.setStyleSheet("""
            QLabel {
                background-color: #27AE60; color: white;
                font-size: 15px; font-weight: bold;
                border-radius: 8px; padding: 6px 14px;
            }
        """)
        self.completion_badge.setVisible(False)
        center_layout.addWidget(self.completion_badge, alignment=Qt.AlignmentFlag.AlignCenter)

        # Active Task Status Label
        self.task_status_label = QLabel("Set time with needle and press Start", self)
        self.task_status_label.setStyleSheet("font-size: 13px; color: #a0a0a0; margin-bottom: 4px;")
        self.task_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.task_status_label)

        # --- Reflection Panel for Goal, Thoughts & Distractions ---
        self.reflection_frame = QFrame(self)
        self.reflection_frame.setObjectName("reflectionFrame")
        self.reflection_frame.setStyleSheet("""
            QFrame#reflectionFrame {
                background-color: #252530;
                border: 1px solid #3f3f4e;
                border-radius: 8px;
                padding: 8px 12px;
                margin-bottom: 6px;
            }
        """)
        self.reflection_frame.setFixedWidth(460)
        reflection_layout = QVBoxLayout(self.reflection_frame)
        reflection_layout.setContentsMargins(10, 8, 10, 8)
        reflection_layout.setSpacing(4)

        self.goal_display_label = QLabel("<b>Goal:</b> None", self)
        self.thought_display_label = QLabel("<b>Thoughts:</b> None", self)
        self.distraction_display_label = QLabel("<b>Distractions to Avoid:</b> None", self)

        for lbl in [self.goal_display_label, self.thought_display_label, self.distraction_display_label]:
            lbl.setWordWrap(True)
            lbl.setStyleSheet("font-size: 12px; color: #d0d0d8; background: transparent;")
            reflection_layout.addWidget(lbl)

        center_layout.addWidget(self.reflection_frame, alignment=Qt.AlignmentFlag.AlignCenter)

        # Control Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)

        self.btn_start = QPushButton("Start", self)
        self.btn_pause = QPushButton("Pause", self)
        self.btn_finish = QPushButton("Finish Session", self)
        self.btn_reset = QPushButton("Reset", self)

        button_layout.addWidget(self.btn_start)
        button_layout.addWidget(self.btn_pause)
        button_layout.addWidget(self.btn_finish)
        button_layout.addWidget(self.btn_reset)

        center_layout.addLayout(button_layout)
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

        # Connections
        self.btn_dashboard.clicked.connect(self.go_to_dashboard)
        self.btn_theme_toggle.clicked.connect(self.toggle_ring_theme)
        self.btn_popout.clicked.connect(self.toggle_floating_timer)
        self.btn_view_logs.clicked.connect(self.show_log_location_dialog)

        self.btn_start.clicked.connect(self.start_timer)
        self.btn_pause.clicked.connect(self.toggle_pause_timer)
        self.btn_finish.clicked.connect(self.finish_session_manually)
        self.btn_reset.clicked.connect(self.reset_timer)

        self.circular_timer.timeChanged.connect(self.on_user_dragged_knob)

        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.tick)

        # Monitor application focus/activation changes for auto popout
        app_instance = QApplication.instance()
        if app_instance:
            app_instance.applicationStateChanged.connect(self._handle_application_state_changed)

        self._apply_button_styles()
        self._update_button_states()

    def _get_btn_style(self, bg_color: str, hover_color: str) -> str:
        return f"""
            QPushButton {{
                background-color: {bg_color}; color: white;
                font-size: 14px; font-weight: bold; border-radius: 8px; padding: 9px 20px;
            }}
            QPushButton:hover {{ background-color: {hover_color}; }}
            QPushButton:disabled {{ background-color: #3f3f4e; color: #7f7f8f; }}
        """

    def _apply_button_styles(self):
        self.btn_start.setStyleSheet(self._get_btn_style("#0096D6", "#007bb5"))
        self.btn_finish.setStyleSheet(self._get_btn_style("#27AE60", "#1E8449"))
        self.btn_reset.setStyleSheet(self._get_btn_style("#7F8C8D", "#687373"))
        self._update_pause_button_style()

    def _update_pause_button_style(self):
        if self.timer.isActive():
            self.btn_pause.setText("Pause")
            self.btn_pause.setStyleSheet(self._get_btn_style("#E67E22", "#D35400"))
        else:
            self.btn_pause.setText("Resume")
            self.btn_pause.setStyleSheet(self._get_btn_style("#27AE60", "#1E8449"))

    def toggle_ring_theme(self):
        self.theme_index = (self.theme_index + 1) % len(self.themes)
        current_theme = self.themes[self.theme_index]

        self.circular_timer.set_theme(current_theme["key"], current_theme["hex"])
        self.btn_theme_toggle.setText(f"🎨 Theme: {current_theme['name']}")
        self._update_floating_window_display()

    def toggle_floating_timer(self):
        """Opens or closes the Always-on-Top Floating Mini Timer window."""
        if self.floating_window is not None:
            self.floating_window.close()
            self.floating_window = None
            self.btn_popout.setText("🗗 Popout Floating Timer")
            return

        self.floating_window = FloatingTimerWindow(None)
        self.floating_window.pauseRequested.connect(self.toggle_pause_timer)
        self.floating_window.closed.connect(self._on_floating_window_closed)
        
        self._update_floating_window_display()
        self.floating_window.show()
        self.btn_popout.setText("📌 Dock Floating Timer")

    def _on_floating_window_closed(self):
        self.floating_window = None
        self.btn_popout.setText("🗗 Popout Floating Timer")

    def _update_floating_window_display(self):
        if self.floating_window:
            task_name = self.active_session_data.get("task_name", "Focus Session") if self.active_session_data else self.prefilled_task_name
            current_theme = self.themes[self.theme_index]
            is_paused = not self.timer.isActive() and self.is_session_active
            
            self.floating_window.update_display(
                task_name=task_name,
                seconds=self.remaining_seconds,
                max_seconds=self.default_seconds,
                theme_key=current_theme["key"],
                theme_hex=current_theme["hex"],
                is_paused=is_paused
            )

    def hideEvent(self, event):
        """Automatically pop out the mini timer when navigating away from SessionPage while active."""
        if self.is_session_active and self.timer.isActive() and not self.floating_window:
            self.toggle_floating_timer()
        super().hideEvent(event)

    def showEvent(self, event):
        """Automatically dock/close the floating timer when returning to SessionPage."""
        if self.floating_window and self.is_session_active:
            self.floating_window.close()
            self.floating_window = None
            self.btn_popout.setText("🗗 Popout Floating Timer")
        super().showEvent(event)

    def _handle_application_state_changed(self, state):
        """Automatically pop out when minimizing or switching away from StudyFlow if timer is running."""
        if state == Qt.ApplicationState.ApplicationSuspended or state == Qt.ApplicationState.ApplicationInactive:
            if self.is_session_active and self.timer.isActive() and not self.floating_window:
                self.toggle_floating_timer()

    def load_planned_task_and_start(self, task_id: str, title: str, duration_mins: int):
        self.load_task(
            task_id=task_id,
            title=title,
            details="Auto Planned Session",
            target_minutes=duration_mins
        )
        self.start_planned_session(task_id, title, duration_mins)

    def start_planned_session(self, task_id: str, title: str, duration_mins: int, transition_data: dict = None):
        self._session_end_emitted = False
        self.sprint_task_id = str(task_id) if task_id else ""
        target_secs = duration_mins * 60 if duration_mins > 0 else 3600
        self.default_seconds = target_secs
        self.sync_timer(target_secs)

        self.initial_target_seconds = target_secs
        
        self.active_session_data = {
            "task_name": title,
            "task_details": "Auto Planned Session",
            "prep_duration_sec": 0,
            "start_time": datetime.now(),
            "planned_duration_sec": target_secs,
        }

        if transition_data and isinstance(transition_data, dict):
            self.active_session_data.update(transition_data)
            if transition_data.get("task_details"):
                self.active_session_data["task_details"] = transition_data["task_details"]

        self.goal_display_label.setText(f"<b>Goal:</b> {self.active_session_data.get('goal', 'None')}")
        self.thought_display_label.setText(f"<b>Thoughts:</b> {self.active_session_data.get('thought', 'None')}")
        self.distraction_display_label.setText(f"<b>Distractions to Avoid:</b> {self.active_session_data.get('distraction', 'None')}")

        self.is_session_active = True
        self.circular_timer.setEnabled(False)
        self.task_status_label.setText(f"Active Task: {title}")
        
        self.timer.start()
        self._update_pause_button_style()
        self._update_button_states()
        self._update_floating_window_display()

    def sync_timer(self, seconds: int):
        self.remaining_seconds = max(0, min(self.default_seconds, seconds))
        self.circular_timer.set_duration(self.remaining_seconds)
        self.time_label.setText(self._format_time(self.remaining_seconds))
        self._update_floating_window_display()

    def load_task(self, task_id: str = "", title: str = "", details: str = "", target_minutes: int = 60):
        self.sprint_task_id = str(task_id) if task_id else ""
        
        # Immediately query SprintManager using task_id to fetch the correct title and duration
        if self.sprint_task_id:
            try:
                mgr = SprintManager()
                items = []
                for attr in ["sprints", "tasks", "list_sprints", "get_sprints"]:
                    val = getattr(mgr, attr, None)
                    if callable(val):
                        try: items = val(); break
                        except: pass
                    elif isinstance(val, list):
                        items = val; break
                
                if not items:
                    for loader in ["load_sprints", "load_tasks", "get_tasks"]:
                        load_fn = getattr(mgr, loader, None)
                        if callable(load_fn):
                            try: items = load_fn(); break
                            except: pass

                for item in items:
                    if isinstance(item, dict) and str(item.get("id")) == str(self.sprint_task_id):
                        fetched_title = item.get("title", "") or item.get("name", "")
                        if fetched_title:
                            title = fetched_title
                        
                        dur = item.get("duration") or item.get("duration_mins") or item.get("minutes")
                        if dur and isinstance(dur, (int, float)):
                            target_minutes = int(dur)
                        break
            except Exception as e:
                print(f"Error looking up task from SprintManager: {e}")

        if not title or title.strip() == "" or title.lower() == "focus session":
            title = "Focus Session"

        self.prefilled_task_name = str(title)
        self.prefilled_task_details = str(details) if details else ""

        target_secs = target_minutes * 60 if isinstance(target_minutes, int) and target_minutes > 0 else 3600
        
        self.default_seconds = target_secs
        self.sync_timer(target_secs)
        self.initial_target_seconds = target_secs

        if hasattr(self, "active_session_data") and self.active_session_data:
            self.goal_display_label.setText(f"<b>Goal:</b> {self.active_session_data.get('goal', 'None')}")
            self.thought_display_label.setText(f"<b>Thoughts:</b> {self.active_session_data.get('thought', 'None')}")
            self.distraction_display_label.setText(f"<b>Distractions to Avoid:</b> {self.active_session_data.get('distraction', 'None')}")
        else:
            self.goal_display_label.setText("<b>Goal:</b> Focus Session")
            self.thought_display_label.setText("<b>Thoughts:</b> None")
            self.distraction_display_label.setText("<b>Distractions to Avoid:</b> None")

        if self.prefilled_task_name:
            self.task_status_label.setText(f"Task Ready: {self.prefilled_task_name}")

    def go_to_dashboard(self):
        if self.floating_window:
            self.floating_window.close()
        if self.show_dashboard_cb:
            self.show_dashboard_cb()

    def show_log_location_dialog(self):
        content = "No logs recorded yet."
        if TASKS_DONE_FILE.exists():
            with open(TASKS_DONE_FILE, "r", encoding="utf-8") as f:
                content = f.read()

        dialog = QDialog(self)
        dialog.setWindowTitle("Tasks Done List Storage")
        dialog.setMinimumSize(500, 350)
        dialog.setStyleSheet("background-color: #1e1e24; color: white;")

        dlg_layout = QVBoxLayout(dialog)
        path_label = QLabel(f"<b>File Location:</b><br>{TASKS_DONE_FILE}")
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path_label.setStyleSheet("color: #0096D6; font-size: 13px; margin-bottom: 10px;")
        dlg_layout.addWidget(path_label)

        log_preview = QTextEdit()
        log_preview.setReadOnly(True)
        log_preview.setPlainText(content)
        log_preview.setStyleSheet("background-color: #2b2b36; color: #e0e0e0; font-size: 13px; border-radius: 6px;")
        dlg_layout.addWidget(log_preview)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background-color: #0096D6; color: white; padding: 6px 16px; border-radius: 6px;")
        close_btn.clicked.connect(dialog.accept)
        dlg_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

        dialog.exec()

    def start_timer(self):
        # If active_session_data was already populated by transition or planned session mode, 
        # ensure we honor its name/details and skip the manual wizard.
        if self.active_session_data and self.is_session_active:
            return

        if self.active_session_data and not self.is_session_active:
            # Planned session data is already loaded; just run the prep dialog and launch directly
            task_title = self.active_session_data.get("task_name", "Focus Session")
            prep_dialog = PrepDialog(task_title, self)
            if prep_dialog.exec() == QDialog.DialogCode.Accepted:
                self._session_end_emitted = False
                prep_duration_sec = prep_dialog.get_prep_duration_sec()
                self.initial_target_seconds = self.remaining_seconds
                
                # Keep the existing task name & details intact instead of resetting them
                self.active_session_data.update({
                    "task_name": task_title,
                    "task_details": self.active_session_data.get("task_details", "Auto Planned Session"),
                    "prep_duration_sec": prep_duration_sec,
                    "start_time": datetime.now(),
                    "planned_duration_sec": self.initial_target_seconds,
                })

                self.goal_display_label.setText(f"<b>Goal:</b> {self.active_session_data.get('goal', 'None')}")
                self.thought_display_label.setText(f"<b>Thoughts:</b> {self.active_session_data.get('thought', 'None')}")
                self.distraction_display_label.setText(f"<b>Distractions to Avoid:</b> {self.active_session_data.get('distraction', 'None')}")

                self.is_session_active = True
                self.circular_timer.setEnabled(False)
                self.task_status_label.setText(f"Active Task: {task_title}")
                
                self.timer.start()
                self._update_pause_button_style()
                self._update_button_states()
                self._update_floating_window_display()
            return

        # Fallback to standard manual flow if started manually without a pre-loaded task
        if not self.is_session_active:
            dialog = StartTaskDialog(self.prefilled_task_name, self.prefilled_task_details, self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                task_info = dialog.get_data()
                
                prep_dialog = PrepDialog(task_info["task_name"], self)
                if prep_dialog.exec() == QDialog.DialogCode.Accepted:
                    self._session_end_emitted = False
                    prep_duration_sec = prep_dialog.get_prep_duration_sec()
                    self.initial_target_seconds = self.remaining_seconds
                    
                    if not self.active_session_data:
                        self.active_session_data = {}

                    self.active_session_data.update({
                        "task_name": task_info["task_name"],
                        "task_details": task_info["task_details"],
                        "prep_duration_sec": prep_duration_sec,
                        "start_time": datetime.now(),
                        "planned_duration_sec": self.initial_target_seconds,
                    })

                    self.goal_display_label.setText(f"<b>Goal:</b> {self.active_session_data.get('goal', 'None')}")
                    self.thought_display_label.setText(f"<b>Thoughts:</b> {self.active_session_data.get('thought', 'None')}")
                    self.distraction_display_label.setText(f"<b>Distractions to Avoid:</b> {self.active_session_data.get('distraction', 'None')}")

                    self.is_session_active = True
                    self.circular_timer.setEnabled(False)
                    self.task_status_label.setText(f"Active Task: {task_info['task_name']}")
                    
                    self.timer.start()
                    self._update_pause_button_style()
                    self._update_button_states()
                    self._update_floating_window_display()

    def toggle_pause_timer(self):
        if not self.is_session_active:
            return

        if self.timer.isActive():
            self.timer.stop()
        else:
            self.timer.start()

        self._update_pause_button_style()
        self._update_floating_window_display()

    def finish_session_manually(self):
        if self.is_session_active:
            elapsed_minutes = (self.initial_target_seconds - self.remaining_seconds) // 60
            
            goal_val = self.active_session_data.get("goal", "") if self.active_session_data else ""
            thought_val = self.active_session_data.get("thought", "") if self.active_session_data else ""

            dialog = EarlyExitDialog(
                session_title=self.active_session_data.get("task_name", "Focus Session") if self.active_session_data else "Focus Session",
                goal=goal_val,
                thought=thought_val,
                elapsed_minutes=elapsed_minutes,
                parent=self
            )
            
            if dialog.exec() == EarlyExitDialog.DialogCode.Accepted:
                exit_data = dialog.get_exit_data()
                action = exit_data.get("action")
                
                if action == "end":
                    reason_desc = exit_data.get("reason", "Completed / Stopped Early")
                    if self.floating_window:
                        self.floating_window.close()
                    self._complete_and_log_session(status=reason_desc)
                elif action == "continue":
                    pass

    def reset_timer(self):
        """Stops active timers, clears cached transition session state, and restores clean defaults."""
        if self.timer.isActive():
            self.timer.stop()

        self.is_session_active = False
        self.active_session_data = None
        self.sprint_task_id = ""
        self.prefilled_task_name = ""
        self.prefilled_task_details = ""

        # Revert durations back to default 60 minutes
        self.default_seconds = 3600
        self.remaining_seconds = 3600
        self.initial_target_seconds = 3600

        # Reset UI timer widget and enable interaction
        self.circular_timer.set_duration(3600)
        self.sync_timer(3600)
        self.circular_timer.setEnabled(True)

        # Reset labels
        self.task_status_label.setText("Set time with needle and press Start")
        self.goal_display_label.setText("<b>Goal:</b> None")
        self.thought_display_label.setText("<b>Thoughts:</b> None")
        self.distraction_display_label.setText("<b>Distractions to Avoid:</b> None")

        if self.floating_window:
            self.floating_window.close()
            self.floating_window = None
            self.btn_popout.setText("🗗 Popout Floating Timer")

        self._update_button_states()
        self._update_floating_window_display()

    def tick(self):
        if self.remaining_seconds > 0:
            self.sync_timer(self.remaining_seconds - 1)
        else:
            self.timer.stop()
            if self.floating_window:
                self.floating_window.close()
            self._complete_and_log_session(status="Timer Completed")

    def on_user_dragged_knob(self, seconds: int):
        if not self.is_session_active:
            self.sync_timer(seconds)
            self.initial_target_seconds = self.remaining_seconds

    def _update_button_states(self):
        if self.is_session_active:
            self.btn_start.setEnabled(False)
            self.btn_pause.setEnabled(True)
            self.btn_finish.setEnabled(True)
            self.btn_reset.setEnabled(True)
        else:
            self.btn_start.setEnabled(True)
            self.btn_pause.setEnabled(False)
            self.btn_finish.setEnabled(False)
            self.btn_reset.setEnabled(True)

    def _complete_and_log_session(self, status="Completed"):
        self.timer.stop()
        
        if not self.active_session_data:
            self.reset_timer()
            return

        session_data_copy = dict(self.active_session_data)
        self.active_session_data = {}  # Mark session as no longer active
        self.is_session_active = False  # Ensure session state is marked inactive immediately
        
        end_time = datetime.now()
        start_time = session_data_copy["start_time"]
        prep_sec = session_data_copy["prep_duration_sec"]
        planned_sec = session_data_copy["planned_duration_sec"]
        actual_sec = planned_sec - self.remaining_seconds
        actual_min = math.ceil(actual_sec / 60) if actual_sec > 0 else 0

        if self.sprint_task_id and actual_min > 0:
            try:
                mgr = SprintManager()
                mgr.log_session(self.sprint_task_id, actual_min)
            except Exception as e:
                print(f"Error logging sprint session: {e}")

        prep_str = self._format_time(prep_sec)
        if prep_sec > 120:
            prep_str += f" ({prep_sec - 120}s overtime)"

        session_record = {
            "start_time": start_time.strftime('%Y-%m-%d %I:%M %p'),
            "end_time": end_time.strftime('%I:%M %p'),
            "task_name": session_data_copy['task_name'],
            "task_details": session_data_copy['task_details'] or 'None',
            "goal": session_data_copy.get('goal', 'None'),
            "thought": session_data_copy.get('thought', 'None'),
            "distraction": session_data_copy.get('distraction', 'None'),
            "prep_time": prep_str,
            "planned_time": self._format_time(planned_sec),
            "spent_time": self._format_time(actual_sec),
            "status": status
        }

        try:
            if TASKS_DONE_FILE.exists() and TASKS_DONE_FILE.stat().st_size > 0:
                with open(TASKS_DONE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
            else:
                data = []
        except (json.JSONDecodeError, Exception):
            data = []

        data.append(session_record)

        TASKS_DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TASKS_DONE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

        if not self._session_end_emitted:
            self._session_end_emitted = True
            self.session_ended.emit(actual_min)

        self._trigger_completion_badge(actual_min)

    def _trigger_completion_badge(self, actual_min: int):
        self.completion_badge.setText(f"✓ Great work! Session Saved • +{actual_min} mins added")
        self.completion_badge.setVisible(True)

        QTimer.singleShot(1800, self._hide_completion_badge_and_reset)

    def _hide_completion_badge_and_reset(self):
        self.completion_badge.setVisible(False)
        if not self.is_session_active:
            self.reset_timer()

    def _format_time(self, seconds: int) -> str:
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"