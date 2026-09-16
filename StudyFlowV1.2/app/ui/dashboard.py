from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from PySide6.QtCore import Qt


class DashboardPage(QWidget):

    def __init__(self, window):
        super().__init__()

        self.window = window

        self.setStyleSheet("""
            QWidget{
                background:#202020;
                color:white;
            }

            QLabel{
                color:white;
            }

            QPushButton{
                background:#2c2c2c;
                border:1px solid #3b3b3b;
                border-radius:10px;
                padding:14px;
                font-size:15px;
                text-align:center;
            }

            QPushButton:hover{
                background:#3a3a3a;
            }

            QPushButton:pressed{
                background:#4a4a4a;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(14)

        title = QLabel("StudyFlow Dashboard")
        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet("""
            font-size:30px;
            font-weight:bold;
            margin:15px;
        """)

        layout.addWidget(title)

        buttons = [

            ("🎯 Study Session", self.window.show_session),

            ("🏃 Focus Sprints", self.window.show_sprints),

            ("📺 Setup for Taking Notes from Video Lectures",
             self.window.show_video),

            ("📅 Scheduler", self.window.show_scheduler),

            ("📝 Interstitial Journal", self.window.show_journal),

            ("📊 Statistics", self.window.show_stats),

            ("⚙️ Settings", self.window.show_settings),

        ]

        for text, func in buttons:

            button = QPushButton(text)
            button.setMinimumHeight(58)
            button.clicked.connect(func)

            layout.addWidget(button)

        layout.addStretch()