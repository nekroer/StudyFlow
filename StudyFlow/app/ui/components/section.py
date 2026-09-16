from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt


class Section(QLabel):

    def __init__(self, text):
        super().__init__(text)

        self.setAlignment(Qt.AlignLeft)

        self.setStyleSheet("""
            QLabel{
                font-size:18px;
                font-weight:bold;
                color:white;
                padding-top:12px;
                padding-bottom:8px;
            }
        """)