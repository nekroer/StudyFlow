from PySide6.QtWidgets import QWidget
from PySide6.QtWidgets import QLabel
from PySide6.QtWidgets import QHBoxLayout
from PySide6.QtWidgets import QCheckBox


class ToggleRow(QWidget):

    def __init__(self, text):

        super().__init__()

        layout = QHBoxLayout(self)

        layout.setContentsMargins(0,0,0,0)

        self.label = QLabel(text)

        self.toggle = QCheckBox()

        layout.addWidget(self.label)

        layout.addStretch()

        layout.addWidget(self.toggle)