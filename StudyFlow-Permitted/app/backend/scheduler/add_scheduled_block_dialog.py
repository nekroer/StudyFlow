from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QComboBox, QSpinBox, QPushButton, QDialogButtonBox, QTabWidget, QWidget, QMessageBox
)
from PySide6.QtCore import Qt
import uuid

class AddScheduledBlockDialog(QDialog):
    """Unified dialog allowing users to pick from active sprint tasks or schedule manual events."""
    
    def __init__(self, sprint_tasks: list = None, existing_sessions: list = None, default_category: str = "academics", default_start_mins: int = 360, default_duration_min: int = 60, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plan Session")
        self.setMinimumWidth(420)
        self.setStyleSheet("""
            QDialog {
                background-color: #141417;
                color: #ffffff;
                font-family: 'Segoe UI';
            }
            QLabel {
                color: #a0a0b0;
                font-size: 12px;
            }
            QLineEdit, QComboBox, QSpinBox {
                background-color: #1e1e24;
                border: 1px solid #2d2d38;
                border-radius: 6px;
                padding: 6px 10px;
                color: #ffffff;
                font-size: 13px;
            }
            QTabWidget::pane {
                border: 1px solid #2d2d38;
                background-color: #141417;
                border-radius: 6px;
            }
            QTabBar::tab {
                background-color: #1e1e24;
                color: #a0a0b0;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #4F8EF7;
                color: white;
                font-weight: bold;
            }
        """)

        self.sprint_tasks = sprint_tasks or []
        self.existing_sessions = existing_sessions or []
        self.result_data = None
        self.default_category = default_category
        self.default_start_mins = default_start_mins
        self.default_duration_min = default_duration_min

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        # Tab widget to switch between Sprint Task binding and Manual Event
        self.tabs = QTabWidget()
        
        # Tab 1: Sprint Task Picker
        self.sprint_tab = QWidget()
        self._init_sprint_tab_ui()
        self.tabs.addTab(self.sprint_tab, "Sprint Task")

        # Tab 2: Manual Event Form
        self.manual_tab = QWidget()
        self._init_manual_tab_ui()
        self.tabs.addTab(self.manual_tab, "Manual Event")

        layout.addWidget(self.tabs)

        # Time & Duration Row (Shared across tabs)
        time_layout = QHBoxLayout()
        time_layout.setSpacing(12)

        start_h = self.default_start_mins // 60
        start_m = self.default_start_mins % 60
        
        start_box = QVBoxLayout()
        start_box.setSpacing(6)
        start_box.addWidget(QLabel("Start Time (HH:MM)"))
        self.start_input = QLineEdit(f"{start_h:02d}:{start_m:02d}")
        start_box.addWidget(self.start_input)
        time_layout.addLayout(start_box)

        dur_box = QVBoxLayout()
        dur_box.setSpacing(6)
        dur_box.addWidget(QLabel("Duration (mins)"))
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 60)
        self.duration_spin.setSingleStep(1)
        self.duration_spin.setValue(self.default_duration_min)
        dur_box.addWidget(self.duration_spin)
        time_layout.addLayout(dur_box)

        layout.addLayout(time_layout)

        # Dialog Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        
        for btn in button_box.buttons():
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #272730;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 16px;
                    color: white;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #4F8EF7;
                }
            """)
        
        layout.addWidget(button_box)

    def _init_sprint_tab_ui(self):
        layout = QVBoxLayout(self.sprint_tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Select active task from Sprint Manager:"))
        self.task_combo = QComboBox()
        
        if self.sprint_tasks:
            for task in self.sprint_tasks:
                self.task_combo.addItem(task.get("title", "Untitled Task"), task)
        else:
            self.task_combo.addItem("No active sprint tasks found", None)
            self.task_combo.setEnabled(False)
            
        layout.addWidget(self.task_combo)
        layout.addStretch()

    def _init_manual_tab_ui(self):
        layout = QVBoxLayout(self.manual_tab)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Session Title"))
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("e.g., Deep Work Block")
        layout.addWidget(self.title_input)

        layout.addWidget(QLabel("Category"))
        self.category_combo = QComboBox()
        self.category_combo.addItems([
            "Academics", "Physics", "Math", "Chemistry", 
            "Coding", "Reading", "Admin", "Health", "Buffer"
        ])
        idx = self.category_combo.findText(self.default_category, Qt.MatchFlag.MatchFixedString)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        layout.addWidget(self.category_combo)
        layout.addStretch()

    def _check_overlap(self, new_start_mins: int, new_duration: int) -> bool:
        """Validates if the new block overlaps with any already scheduled session."""
        new_end_mins = new_start_mins + new_duration
        for session in self.existing_sessions:
            start_str = session.get("start_time", "09:00")
            try:
                parts = start_str.split(":")
                exist_start_mins = int(parts[0]) * 60 + int(parts[1])
            except (ValueError, IndexError):
                exist_start_mins = 540

            exist_duration = session.get("planned_duration_min", 60)
            exist_end_mins = exist_start_mins + exist_duration

            # Overlap condition check
            if new_start_mins < exist_end_mins and new_end_mins > exist_start_mins:
                return True
        return False

    def _on_accept(self):
        start_str = self.start_input.text().strip()
        parts = start_str.split(":")
        if len(parts) != 2:
            QMessageBox.warning(self, "Invalid Time", "Please enter time in HH:MM format.")
            return

        try:
            hour = int(parts[0])
            minute = int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Out of range")
            start_mins = hour * 60 + minute
        except ValueError:
            QMessageBox.warning(self, "Invalid Time", "Hours must be 0-23 and minutes must be 0-59.")
            return

        duration = self.duration_spin.value()

        # Check for collision/overlap before accepting
        if self._check_overlap(start_mins, duration):
            QMessageBox.warning(self, "Scheduling Conflict", "This time slot collides or overlaps with an existing session. Please choose a different time or duration.")
            return

        # Check active tab to determine source data
        if self.tabs.currentIndex() == 0 and self.sprint_tasks and self.task_combo.currentData():
            selected_task = self.task_combo.currentData()
            title = selected_task.get("title", "Sprint Session")
            category = selected_task.get("category", "academics").lower()
            task_id = selected_task.get("task_id")
        else:
            title = self.title_input.text().strip() or "Study Session"
            category = self.category_combo.currentText().lower()
            task_id = None

        self.result_data = {
            "quest_id": str(uuid.uuid4()),
            "task_id": task_id,
            "title": title,
            "category": category,
            "start_time": f"{hour:02d}:{minute:02d}",
            "planned_duration_min": duration,
            "objectives": [
                "Review core prerequisite notes",
                "Execute primary problem set / workflow",
                "Verify final output & log progress"
            ]
        }
        self.accept()

    def get_session_data(self) -> dict:
        return self.result_data