import json
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSpinBox, QSlider, QHBoxLayout
from PySide6.QtCore import Qt
from app.backend.paths import TRANSITION_CONFIG_FILE, TIMER_SIZE_CONFIG_FILE

TRANSITION_DEFAULT_CONFIG = {
    "fade_start_offset_min": 7,  # Start fading 7 minutes before session
    "fade_duration_sec": 300,    # Fade over 5 minutes (300 seconds)
    "countdown_sec": 120,        # Show dialog 2 minutes before session (120 seconds)
}

TIMER_SIZE_DEFAULT_CONFIG = {
    "timer_size": 420,           # Default main window timer size in pixels
}

class SettingsPage(QWidget):

    def __init__(self, window):
        super().__init__()

        self.window = window

        layout = QVBoxLayout(self)

        title = QLabel("Settings")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:24px;font-weight:bold;")

        layout.addWidget(title)

        # Load current settings from files
        self.settings_data = self._load_settings()
        self.timer_settings_data = self._load_timer_settings()

        # --- Timer Display Settings Dropdown Toggle ---
        self.timer_toggle_btn = QPushButton("▼ Timer Display Settings")
        self.timer_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e24;
                color: #0096D6;
                font-size: 16px;
                font-weight: bold;
                text-align: left;
                padding: 10px;
                border: 1px solid #333;
                border-radius: 6px;
                margin-top: 15px;
            }
            QPushButton:hover {
                background-color: #282832;
            }
        """)
        self.timer_toggle_btn.clicked.connect(self._toggle_timer_section)
        layout.addWidget(self.timer_toggle_btn)

        # --- Timer Display Settings Container Widget ---
        self.timer_container = QWidget()
        self.timer_container.setStyleSheet("background-color: #151519; border: 1px solid #282832; border-radius: 6px; padding: 10px;")
        timer_layout = QVBoxLayout(self.timer_container)

        size_layout = QHBoxLayout()
        size_label_text = QLabel("Main Window Timer Size (px):")
        self.size_value_label = QLabel(str(self.timer_settings_data.get("timer_size", TIMER_SIZE_DEFAULT_CONFIG["timer_size"])))
        self.size_value_label.setStyleSheet("color: #0096D6; font-weight: bold; font-size: 14px;")
        
        size_layout.addWidget(size_label_text)
        size_layout.addStretch()
        size_layout.addWidget(self.size_value_label)
        timer_layout.addLayout(size_layout)

        self.timer_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.timer_size_slider.setRange(300, 600)
        self.timer_size_slider.setValue(self.timer_settings_data.get("timer_size", TIMER_SIZE_DEFAULT_CONFIG["timer_size"]))
        self.timer_size_slider.setTickInterval(25)
        self.timer_size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.timer_size_slider.valueChanged.connect(self._on_timer_size_changed)
        timer_layout.addWidget(self.timer_size_slider)

        # Add container to main layout (start hidden by default)
        self.timer_container.setVisible(False)
        layout.addWidget(self.timer_container)

        # --- Transition Settings Dropdown Toggle ---
        self.transition_toggle_btn = QPushButton("▼ Transition Settings")
        self.transition_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e1e24;
                color: #0096D6;
                font-size: 16px;
                font-weight: bold;
                text-align: left;
                padding: 10px;
                border: 1px solid #333;
                border-radius: 6px;
                margin-top: 15px;
            }
            QPushButton:hover {
                background-color: #282832;
            }
        """)
        self.transition_toggle_btn.clicked.connect(self._toggle_transition_section)
        layout.addWidget(self.transition_toggle_btn)

        # --- Transition Settings Container Widget ---
        self.transition_container = QWidget()
        self.transition_container.setStyleSheet("background-color: #151519; border: 1px solid #282832; border-radius: 6px; padding: 10px;")
        transition_layout = QVBoxLayout(self.transition_container)

        # Fade Start Offset SpinBox
        offset_layout = QHBoxLayout()
        offset_label = QLabel("Fade Start Offset (minutes before session):")
        self.offset_spinbox = QSpinBox()
        self.offset_spinbox.setRange(1, 60)
        self.offset_spinbox.setValue(self.settings_data.get("fade_start_offset_min", TRANSITION_DEFAULT_CONFIG["fade_start_offset_min"]))
        self.offset_spinbox.valueChanged.connect(self._save_transition_settings)
        offset_layout.addWidget(offset_label)
        offset_layout.addWidget(self.offset_spinbox)
        transition_layout.addLayout(offset_layout)

        # Fade Duration SpinBox
        fade_layout = QHBoxLayout()
        fade_label = QLabel("Volume Fade Duration (seconds):")
        self.fade_spinbox = QSpinBox()
        self.fade_spinbox.setRange(10, 600)
        self.fade_spinbox.setValue(self.settings_data.get("fade_duration_sec", TRANSITION_DEFAULT_CONFIG["fade_duration_sec"]))
        self.fade_spinbox.valueChanged.connect(self._save_transition_settings)
        fade_layout.addWidget(fade_label)
        fade_layout.addWidget(self.fade_spinbox)
        transition_layout.addLayout(fade_layout)

        # Countdown Duration SpinBox
        countdown_layout = QHBoxLayout()
        countdown_label = QLabel("Transition Countdown (seconds):")
        self.countdown_spinbox = QSpinBox()
        self.countdown_spinbox.setRange(10, 600)
        self.countdown_spinbox.setValue(self.settings_data.get("countdown_sec", TRANSITION_DEFAULT_CONFIG["countdown_sec"]))
        self.countdown_spinbox.valueChanged.connect(self._save_transition_settings)
        countdown_layout.addWidget(countdown_label)
        countdown_layout.addWidget(self.countdown_spinbox)
        transition_layout.addLayout(countdown_layout)

        # Add container to main layout (start hidden by default)
        self.transition_container.setVisible(False)
        layout.addWidget(self.transition_container)

        layout.addStretch()

        back = QPushButton("← Dashboard")
        back.clicked.connect(window.show_dashboard)

        layout.addWidget(back)

    def _on_timer_size_changed(self, value: int):
        self.size_value_label.setText(str(value))
        self._save_timer_settings()
        
        # Look for session_page across common attribute names on the main window
        session_page = None
        if hasattr(self.window, "session_page"):
            session_page = self.window.session_page
        elif hasattr(self.window, "sessionPage"):
            session_page = self.window.sessionPage
        elif hasattr(self.window, "stack"):
            # If using a QStackedWidget, find it among the widgets
            for i in range(self.window.stack.count()):
                widget = self.window.stack.widget(i)
                if widget.__class__.__name__ == "SessionPage":
                    session_page = widget
                    break

        if session_page and hasattr(session_page, "circular_timer"):
            session_page.circular_timer.update_size(value)

    def _toggle_timer_section(self):
        is_visible = self.timer_container.isVisible()
        self.timer_container.setVisible(not is_visible)
        if not is_visible:
            self.timer_toggle_btn.setText("▲ Timer Display Settings")
        else:
            self.timer_toggle_btn.setText("▼ Timer Display Settings")

    def _toggle_transition_section(self):
        is_visible = self.transition_container.isVisible()
        self.transition_container.setVisible(not is_visible)
        if not is_visible:
            self.transition_toggle_btn.setText("▲ Transition Settings")
        else:
            self.transition_toggle_btn.setText("▼ Transition Settings")

    def _load_settings(self) -> dict:
        config = TRANSITION_DEFAULT_CONFIG.copy()
        if TRANSITION_CONFIG_FILE.exists():
            try:
                data = json.loads(TRANSITION_CONFIG_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    config.update(data)
            except Exception:
                pass
        return config

    def _load_timer_settings(self) -> dict:
        config = TIMER_SIZE_DEFAULT_CONFIG.copy()
        if TIMER_SIZE_CONFIG_FILE.exists():
            try:
                data = json.loads(TIMER_SIZE_CONFIG_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    config.update(data)
            except Exception:
                pass
        return config

    def _save_transition_settings(self):
        self.settings_data["fade_start_offset_min"] = self.offset_spinbox.value()
        self.settings_data["fade_duration_sec"] = self.fade_spinbox.value()
        self.settings_data["countdown_sec"] = self.countdown_spinbox.value()
        try:
            TRANSITION_CONFIG_FILE.write_text(json.dumps(self.settings_data, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"Error saving transition settings: {e}")

    def _save_timer_settings(self):
        self.timer_settings_data["timer_size"] = self.timer_size_slider.value()
        try:
            TIMER_SIZE_CONFIG_FILE.write_text(json.dumps(self.timer_settings_data, indent=4), encoding="utf-8")
        except Exception as e:
            print(f"Error saving timer settings: {e}")