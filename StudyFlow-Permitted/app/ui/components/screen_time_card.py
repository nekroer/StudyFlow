from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class ScreenTimeCard(QFrame):
    """Small reusable display card for Activity Monitor metrics."""

    def __init__(self, title: str, value: str = "--", subtitle: str = "", parent=None):
        super().__init__(parent)

        self.setObjectName("screenTimeCard")
        self.setStyleSheet(
            """
            QFrame#screenTimeCard {
                background-color: #18181c;
                border: 1px solid #2d2d38;
                border-radius: 10px;
            }
            QLabel {
                border: none;
            }
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(5)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "color: #8f8f9d; font-size: 11px; font-weight: bold;"
        )
        layout.addWidget(self.title_label)

        self.value_label = QLabel(value)
        self.value_label.setStyleSheet(
            "color: #ffffff; font-size: 25px; font-weight: bold;"
        )
        layout.addWidget(self.value_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setStyleSheet(
            "color: #a0a0b0; font-size: 11px;"
        )
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

    def set_value(self, value: str):
        self.value_label.setText(value)

    def set_subtitle(self, subtitle: str):
        self.subtitle_label.setText(subtitle)
