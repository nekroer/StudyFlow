from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt


class StatusChip(QWidget):

    def __init__(self, title):

        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        self.dot = QLabel("●")
        self.dot.setFixedWidth(18)
        self.dot.setAlignment(Qt.AlignCenter)

        self.title = QLabel(title)

        self.state = QLabel("Offline")

        layout.addWidget(self.dot)
        layout.addWidget(self.title)
        layout.addStretch()
        layout.addWidget(self.state)

        self.set_offline()

    def set_color(self, color):

        self.dot.setStyleSheet(f"""
        QLabel{{
            color:{color};
            font-size:18px;
            font-weight:bold;
        }}
        """)

    def set_online(self):

        self.set_color("#00D26A")

        self.state.setText("Running")

    def set_offline(self):

        self.set_color("#FF4D4F")

        self.state.setText("Offline")

    def set_starting(self):

        self.set_color("#F7B500")

        self.state.setText("Starting")