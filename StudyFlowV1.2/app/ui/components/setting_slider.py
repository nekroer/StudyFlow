from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QSlider
)

from PySide6.QtCore import Qt


class SettingSlider(QWidget):

    def __init__(
        self,
        title,
        minimum,
        maximum,
        value,
        suffix="%"
    ):

        super().__init__()

        self.suffix = suffix

        layout = QVBoxLayout(self)

        title_row = QHBoxLayout()

        self.title = QLabel(title)

        self.value = QLabel()

        title_row.addWidget(self.title)

        title_row.addStretch()

        title_row.addWidget(self.value)

        layout.addLayout(title_row)

        self.slider = QSlider(Qt.Horizontal)

        self.slider.setRange(minimum, maximum)

        self.slider.setValue(value)

        self.slider.valueChanged.connect(self.update_label)

        layout.addWidget(self.slider)

        self.update_label(value)

    def update_label(self, value):

        if self.suffix == "sec":

            self.value.setText(f"{value/100:.2f} sec")

        else:

            self.value.setText(f"{value}{self.suffix}")