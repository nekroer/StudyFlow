from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout
)

from PySide6.QtCore import Qt


class DashboardPage(QWidget):

    def __init__(self, window):
        super().__init__()

        self.window = window

        layout = QVBoxLayout(self)

        title = QLabel("StudyFlow Dashboard")
        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet("""
            font-size:28px;
            font-weight:bold;
            margin:25px;
        """)

        layout.addWidget(title)

        buttons = [

            ("📺 Setup for Taking Notes from Video Lectures", self.window.show_video),

            ("📅 Scheduler", self.window.show_scheduler),

            ("📝 Interstitial Journal", self.window.show_journal),

            ("📊 Statistics", self.window.show_stats),

            ("⚙ Settings", self.window.show_settings)

        ]

        for text, func in buttons:

            b = QPushButton(text)

            b.setMinimumHeight(55)

            b.clicked.connect(func)

            layout.addWidget(b)

        layout.addStretch()
