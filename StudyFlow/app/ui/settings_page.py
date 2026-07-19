from PySide6.QtWidgets import QWidget,QVBoxLayout,QLabel,QPushButton
from PySide6.QtCore import Qt

class SettingsPage(QWidget):

    def __init__(self,window):
        super().__init__()

        self.window=window

        layout=QVBoxLayout(self)

        title=QLabel("Settings")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:24px;font-weight:bold;")

        layout.addWidget(title)

        layout.addWidget(QLabel("Coming Soon"))

        layout.addStretch()

        back=QPushButton("← Dashboard")
        back.clicked.connect(window.show_dashboard)

        layout.addWidget(back)
