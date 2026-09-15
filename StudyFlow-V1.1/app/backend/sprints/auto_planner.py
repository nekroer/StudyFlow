from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
)


class AutoPlanDialog(QDialog):
    # Emits a list of planned session dicts: [{title, start_time, duration_mins, task_id}, ...]
    plan_generated = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚡ Auto Plan My Day")
        self.setMinimumWidth(400)
        self.setStyleSheet("""
            QDialog { background-color: #1e1e24; color: white; }
            QLabel { color: #e0e0e0; font-size: 13px; }
            QTimeEdit, QSpinBox, QComboBox {
                background-color: #2b2b36; color: white;
                border: 1px solid #3f3f4e; border-radius: 6px; padding: 6px; font-size: 13px;
            }
            QTimeEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #0096D6; }
        """)

        layout = QVBoxLayout(self)

        title_label = QLabel("<b>Brain Sync • Daily Auto-Planner</b>", self)
        title_label.setStyleSheet("font-size: 16px; color: #0096D6; margin-bottom: 8px;")
        layout.addWidget(title_label)

        form = QFormLayout()

        self.time_available = QSpinBox(self)
        self.time_available.setRange(30, 480)
        self.time_available.setSingleStep(15)
        self.time_available.setValue(120)
        self.time_available.setSuffix(" mins")

        self.energy_level = QComboBox(self)
        self.energy_level.addItems(["⚡ High (Ready for deep work)", "🔋 Moderate (Balanced)", "🪫 Low (High friction / Fatigue)"])

        self.break_interval = QComboBox(self)
        self.break_interval.addItems(["25 min Focus / 5 min Break (Pomodoro)", "50 min Focus / 10 min Break (Deep Work)", "15 min Micro-Sprints (Low Resistance)"])

        form.addRow("Available Time:", self.time_available)
        form.addRow("Energy Check-in:", self.energy_level)
        form.addRow("Session Structure:", self.break_interval)

        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Generate Plan")
        buttons.accepted.connect(self.generate_and_emit_plan)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def generate_and_emit_plan(self):
        total_time = self.time_available.value()
        energy_idx = self.energy_level.currentIndex()

        # Adapt session chunk length based on energy level
        if energy_idx == 2:  # Low energy
            chunk_duration = 15
        elif energy_idx == 1:  # Moderate
            chunk_duration = 25
        else:  # High energy
            chunk_duration = 50

        num_chunks = max(1, total_time // (chunk_duration + 5))
        generated_blocks = []

        for i in range(num_chunks):
            generated_blocks.append({
                "title": f"Auto Block #{i + 1}",
                "duration_mins": chunk_duration,
                "type": "Focus"
            })

        self.plan_generated.emit(generated_blocks)
        self.accept()