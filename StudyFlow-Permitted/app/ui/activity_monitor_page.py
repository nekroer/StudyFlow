from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QListWidget,
    QListWidgetItem,
)

from app.backend.activity.screen_time_tracker import ScreenTimeTracker
from app.ui.components.screen_time_card import ScreenTimeCard


class ActivityMonitorPage(QWidget):
    """Dashboard for live foreground and background-audio activity."""

    def __init__(self, tracker: ScreenTimeTracker, window=None):
        super().__init__(window)
        self.tracker = tracker
        self.window = window

        self.setStyleSheet("""
            QWidget { background-color: #202020; color: #ffffff; }
            QLabel { color: #ffffff; }
            QPushButton {
                background-color: #1e1e24;
                color: #ffffff;
                border: 1px solid #2d2d38;
                border-radius: 7px;
                padding: 7px 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2b2b33; }
            QListWidget {
                background-color: #18181c;
                color: #e0e0e0;
                border: 1px solid #2d2d38;
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 9px;
                border-bottom: 1px solid #24242c;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Activity Monitor")
        title.setStyleSheet("font-size: 28px; font-weight: bold; font-family: 'Segoe UI';")
        header.addWidget(title)
        header.addStretch()

        back_button = QPushButton("← Dashboard")
        back_button.clicked.connect(self._go_back)
        header.addWidget(back_button)
        layout.addLayout(header)

        subtitle = QLabel(
            "Foreground use and background audio are recorded separately."
        )
        subtitle.setStyleSheet("color: #a0a0b0; font-size: 12px;")
        layout.addWidget(subtitle)

        cards = QHBoxLayout()
        cards.setSpacing(12)
        self.total_card = ScreenTimeCard(
            "SCREEN TIME TODAY", "0m", "Recorded foreground time"
        )
        self.background_card = ScreenTimeCard(
            "BACKGROUND AUDIO", "0m", "Audio playing while not foreground"
        )
        self.status_card = ScreenTimeCard(
            "MONITOR STATUS", "Stopped", "Activity recorder"
        )
        cards.addWidget(self.total_card, 1)
        cards.addWidget(self.background_card, 1)
        cards.addWidget(self.status_card, 1)
        layout.addLayout(cards)

        apps_frame = QFrame()
        apps_frame.setStyleSheet("""
            QFrame {
                background-color: #141417;
                border: 1px solid #2d2d38;
                border-radius: 10px;
            }
        """)
        apps_layout = QVBoxLayout(apps_frame)
        apps_layout.setContentsMargins(16, 16, 16, 16)
        apps_layout.setSpacing(10)

        apps_title = QLabel("Today's Applications & Sites")
        apps_title.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
        apps_layout.addWidget(apps_title)

        self.apps_list = QListWidget()
        apps_layout.addWidget(self.apps_list)
        layout.addWidget(apps_frame, 1)

        footer = QHBoxLayout()
        self.refresh_label = QLabel("")
        self.refresh_label.setStyleSheet("color: #777783; font-size: 10px;")
        footer.addWidget(self.refresh_label)
        footer.addStretch()

        self.refresh_button = QPushButton("↻ Refresh")
        self.refresh_button.clicked.connect(self.refresh)
        footer.addWidget(self.refresh_button)
        layout.addLayout(footer)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1000)
        self.refresh_timer.timeout.connect(lambda: self._render(self.tracker.snapshot()))
        self.refresh_timer.start()

        self.tracker.screen_time_updated.connect(self._on_tracker_update)
        self.tracker.error_occurred.connect(self._on_tracker_error)
        self.refresh()

    def refresh(self):
        self.tracker.refresh_now()

    def _on_tracker_update(self, snapshot: dict):
        self._render(snapshot)

    def _on_tracker_error(self, error: str):
        self.refresh_label.setText(f"Monitor error: {error}")

    def _render(self, snapshot: dict):
        self.total_card.set_value(
            self._format_duration(int(snapshot.get("total_seconds", 0)))
        )

        background_audio = snapshot.get("background_audio", [])
        background_total = sum(
            int(item.get("seconds", 0)) for item in background_audio
        )
        self.background_card.set_value(self._format_duration(background_total))

        running = bool(snapshot.get("is_running"))
        idle = bool(snapshot.get("is_idle"))

        if not running:
            self.status_card.set_value("Stopped")
            self.status_card.set_subtitle("Activity recorder")
        elif idle:
            self.status_card.set_value("Idle")
            self.status_card.set_subtitle("Foreground time is not being counted")
        else:
            self.status_card.set_value("Recording")
            self.status_card.set_subtitle("Foreground and background audio are being tracked")

        self.apps_list.clear()

        for index, app in enumerate(snapshot.get("applications", []), start=1):
            foreground = self._format_duration(int(app.get("foreground_seconds", app.get("seconds", 0))))
            background = self._format_duration(int(app.get("background_audio_seconds", 0)))
            total = self._format_duration(int(app.get("total_seconds", 0)))
            name = app.get("process_name") or "Unknown"
            self.apps_list.addItem(
                QListWidgetItem(
                    f"{index}.  {name}    ·    {total} total    "
                    f"(foreground {foreground}, background audio {background})"
                )
            )

        browser_sites = snapshot.get("browser_sites", [])
        if browser_sites:
            self.apps_list.addItem(QListWidgetItem("Chrome sites"))
            for site in browser_sites[:10]:
                foreground = self._format_duration(
                    int(site.get("foreground_seconds", site.get("seconds", 0)))
                )
                background = self._format_duration(
                    int(site.get("background_audio_seconds", 0))
                )
                total = self._format_duration(int(site.get("total_seconds", 0)))
                host = site.get("host") or "Unknown site"
                self.apps_list.addItem(
                    QListWidgetItem(
                        f"   {host}    ·    {total} total    "
                        f"(foreground {foreground}, background audio {background})"
                    )
                )

        if background_audio:
            self.apps_list.addItem(QListWidgetItem("Background audio sessions"))
            for audio in background_audio[:10]:
                duration = self._format_duration(int(audio.get("seconds", 0)))
                name = audio.get("process_name") or "Unknown audio app"
                self.apps_list.addItem(QListWidgetItem(f"   {name}    ·    {duration}"))

        self.refresh_label.setText("Live data · updated continuously")

    def _go_back(self):
        if self.window and hasattr(self.window, "show_dashboard"):
            self.window.show_dashboard()

    @staticmethod
    def _format_duration(seconds: int) -> str:
        seconds = max(0, int(seconds))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours}h {minutes:02d}m"
        if minutes:
            return f"{minutes}m {secs:02d}s"
        return f"{secs}s"
