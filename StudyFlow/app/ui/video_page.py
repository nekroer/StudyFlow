from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QSlider,
    QCheckBox,
)

from PySide6.QtCore import Qt

from pathlib import Path
import json
import webbrowser
import subprocess

from app.backend.paths import YOUTUBE_CONFIG_FILE

from app.backend.youtube.launcher import (
    start_everything,
    stop_everything,
)

from app.ui.components.card import Card
from app.ui.components.section import Section
from app.ui.components.status_chip import StatusChip


CONFIG_PATH = YOUTUBE_CONFIG_FILE


class VideoPage(QWidget):

    def __init__(self, window):
        super().__init__()

        self.window = window
        self.config = self.load_config()

        layout = QVBoxLayout(self)

        # ==================================================
        # Title
        # ==================================================

        title = QLabel("Video Lecture Note Taking")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:24px;
            font-weight:bold;
        """)
        layout.addWidget(title)

        layout.addSpacing(20)

        # ==================================================
        # Enable
        # ==================================================

        self.enable = QCheckBox(
            "Enable Video Lecture Note Taking"
        )

        self.enable.stateChanged.connect(
            self.toggle_backend
        )

        layout.addWidget(self.enable)

        layout.addSpacing(20)

        # ==================================================
        # Status Card
        # ==================================================

        status_card = Card()

        status_card.layout.addWidget(
            Section("System Status")
        )

        self.backend_status = StatusChip("Backend")
        self.vlc_status = StatusChip("VLC")
        self.extension_status = StatusChip(
            "Browser Extension"
        )

        status_card.layout.addWidget(
            self.backend_status
        )

        status_card.layout.addWidget(
            self.vlc_status
        )

        status_card.layout.addWidget(
            self.extension_status
        )

        layout.addWidget(status_card)

        layout.addSpacing(20)

        # ==================================================
        # Playing Volume
        # ==================================================

        layout.addWidget(
            QLabel("Playing Volume")
        )

        self.play_slider = QSlider(Qt.Horizontal)
        self.play_slider.setRange(0, 200)
        self.play_slider.setValue(
            self.config["playing_volume"]
        )

        self.play_slider.valueChanged.connect(
            self.play_changed
        )

        layout.addWidget(self.play_slider)

        self.play_value = QLabel(
            f'{self.config["playing_volume"]}%'
        )

        layout.addWidget(self.play_value)

        layout.addSpacing(20)

        # ==================================================
        # Paused Volume
        # ==================================================

        layout.addWidget(
            QLabel("Paused Volume")
        )

        self.pause_slider = QSlider(Qt.Horizontal)
        self.pause_slider.setRange(0, 200)
        self.pause_slider.setValue(
            self.config["paused_volume"]
        )

        self.pause_slider.valueChanged.connect(
            self.pause_changed
        )

        layout.addWidget(self.pause_slider)

        self.pause_value = QLabel(
            f'{self.config["paused_volume"]}%'
        )

        layout.addWidget(self.pause_value)

        layout.addSpacing(20)

        # ==================================================
        # Fade Duration
        # ==================================================

        layout.addWidget(
            QLabel("Fade Duration")
        )

        self.fade_slider = QSlider(Qt.Horizontal)
        self.fade_slider.setRange(1, 300)
        self.fade_slider.setValue(
            int(self.config["fade_time"] * 100)
        )

        self.fade_slider.valueChanged.connect(
            self.fade_changed
        )

        layout.addWidget(self.fade_slider)

        self.fade_value = QLabel(
            f'{self.config["fade_time"]:.2f} s'
        )

        layout.addWidget(self.fade_value)

        layout.addSpacing(20)

        # ==================================================
        # Ignore Short Pauses
        # ==================================================

        layout.addWidget(
            QLabel("Ignore Short Pauses")
        )

        self.ignore_slider = QSlider(Qt.Horizontal)
        self.ignore_slider.setRange(0, 3000)
        self.ignore_slider.setSingleStep(100)

        self.ignore_slider.setValue(
            self.config["ignore_pause_ms"]
        )

        self.ignore_slider.valueChanged.connect(
            self.ignore_changed
        )

        layout.addWidget(self.ignore_slider)

        self.ignore_value = QLabel(
            f'{self.config["ignore_pause_ms"]} ms'
        )

        layout.addWidget(self.ignore_value)

        layout.addSpacing(20)

        # ==================================================
        # Buttons
        # ==================================================

        row = QHBoxLayout()

        self.open_vlc = QPushButton("Open VLC")
        self.open_vlc.clicked.connect(
            self.open_vlc_clicked
        )

        self.http = QPushButton(
            "Open Web Interface"
        )

        self.http.clicked.connect(
            self.open_http
        )

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
    # Slider Callbacks
    # ==================================================

    def play_changed(self, value):
        self.play_value.setText(f"{value}%")
        self.config["playing_volume"] = value
        self.save_config()

    def pause_changed(self, value):
        self.pause_value.setText(f"{value}%")
        self.config["paused_volume"] = value
        self.save_config()

    def fade_changed(self, value):
        seconds = value / 100
        self.fade_value.setText(f"{seconds:.2f} s")
        self.config["fade_time"] = seconds
        self.save_config()

    def ignore_changed(self, value):
        self.ignore_value.setText(f"{value} ms")
        self.config["ignore_pause_ms"] = value
        self.save_config()

    # ==================================================
    # Backend
    # ==================================================

    def toggle_backend(self, state):
        print("Toggle:", state)

        if self.enable.isChecked():

            print("Calling launcher...")

            self.backend_status.set_starting()

            try:
                start_everything()

                self.backend_status.set_online()
                self.vlc_status.set_online()
                self.extension_status.set_online()

            except Exception as e:
                print(e)

                self.backend_status.set_offline()
                self.vlc_status.set_offline()
                self.extension_status.set_offline()

        else:

            stop_everything()

            self.backend_status.set_offline()
            self.vlc_status.set_offline()
            self.extension_status.set_offline()

    # ==================================================
    # Buttons
    # ==================================================

    def open_http(self):
        webbrowser.open("http://127.0.0.1:8080/")

    def open_vlc_clicked(self):

        possible = [
            r"C:\Program Files\VideoLAN\VLC\vlc.exe",
            r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
        ]

        for exe in possible:
            if Path(exe).exists():
                subprocess.Popen([exe])
                return
            
        print("VLC not found.")
