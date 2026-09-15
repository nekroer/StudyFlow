from PySide6.QtWidgets import QFrame
from PySide6.QtWidgets import QVBoxLayout


class Card(QFrame):

    def __init__(self):

        super().__init__()

        self.layout = QVBoxLayout(self)

        self.layout.setSpacing(12)

        self.layout.setContentsMargins(20,20,20,20)

        self.setStyleSheet("""

        QFrame{

            background:#242424;

            border:1px solid #3B3B3B;

            border-radius:12px;

        }

        """)