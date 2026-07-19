from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSlider,
    QCheckBox
)

from PySide6.QtCore import Qt

from pathlib import Path
import json
import webbrowser
import subprocess

from app.backend.youtube.launcher import (
    start_everything,
    stop_everything,
)

CONFIG_PATH = (
    Path(__file__).parent.parent /
    "backend" /
    "youtube" /
    "config.json"
)


class VideoPage(QWidget):

    def __init__(self, window):
        super().__init__()

        self.window = window

        self.config = self.load_config()

        layout = QVBoxLayout(self)

        # ------------------------------------------------
        # Title
        # ------------------------------------------------

        title = QLabel("Video Lecture Note Taking")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:24px;
            font-weight:bold;
        """)
        layout.addWidget(title)

        layout.addSpacing(20)

        # ------------------------------------------------
        # Enable
        # ------------------------------------------------

        self.enable = QCheckBox("Enable Video Lecture Note Taking")
        self.enable.stateChanged.connect(self.toggle_backend)
        layout.addWidget(self.enable)

        layout.addSpacing(20)

        # ------------------------------------------------
        # Status
        # ------------------------------------------------

        self.status = QLabel("🔴 Disabled")
        self.status.setStyleSheet("font-size:16px;")
        layout.addWidget(self.status)

        layout.addSpacing(20)

        # ------------------------------------------------
        # Playing Volume
        # ------------------------------------------------

        layout.addWidget(QLabel("Playing Volume"))

        self.play_slider = QSlider(Qt.Horizontal)
        self.play_slider.setRange(0, 200)
        self.play_slider.setValue(self.config["low_volume"])
        self.play_slider.valueChanged.connect(self.play_changed)

        layout.addWidget(self.play_slider)

        self.play_value = QLabel(f'{self.config["low_volume"]}%')
        layout.addWidget(self.play_value)

        layout.addSpacing(20)

        # ------------------------------------------------
        # Paused Volume
        # ------------------------------------------------

        layout.addWidget(QLabel("Paused Volume"))

        self.pause_slider = QSlider(Qt.Horizontal)
        self.pause_slider.setRange(0, 200)
        self.pause_slider.setValue(self.config["high_volume"])
        self.pause_slider.valueChanged.connect(self.pause_changed)

        layout.addWidget(self.pause_slider)

        self.pause_value = QLabel(f'{self.config["high_volume"]}%')
        layout.addWidget(self.pause_value)

        layout.addSpacing(20)

        # ------------------------------------------------
        # Buttons
        # ------------------------------------------------

        row = QHBoxLayout()

        self.open_vlc = QPushButton("Open VLC")
        self.open_vlc.clicked.connect(self.open_vlc_clicked)

        self.http = QPushButton("Open Web Interface")
        self.http.clicked.connect(self.open_http)

        row.addWidget(self.open_vlc)
        row.addWidget(self.http)

        layout.addLayout(row)

        layout.addStretch()

        back = QPushButton("← Dashboard")
        back.clicked.connect(self.window.show_dashboard)
        layout.addWidget(back)

    # ==================================================
    # Config
    # ==================================================

    def load_config(self):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)

    def save_config(self):
        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=4)

    # ==================================================
    # Slider callbacks
    # ==================================================

    def play_changed(self, value):
        self.play_value.setText(f"{value}%")
        self.config["low_volume"] = value
        self.save_config()

    def pause_changed(self, value):
        self.pause_value.setText(f"{value}%")
        self.config["high_volume"] = value
        self.save_config()

    # ==================================================
    # Backend
    # ==================================================

    def toggle_backend(self, state):

        if state:

            self.status.setText("🟡 Starting...")

            try:
                start_everything()
                self.status.setText("🟢 Running")

            except Exception as e:
                self.status.setText(str(e))

        else:

            stop_everything()

            self.status.setText("🔴 Disabled")

    # ==================================================
    # Buttons
    # ==================================================

    def open_http(self):
        webbrowser.open("http://:mypassword@127.0.0.1:8080")

    def open_vlc_clicked(self):

        possible = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
        ]

        for exe in possible:
            if Path(exe).exists():
                subprocess.Popen([exe])
                return