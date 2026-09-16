from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QProgressBar, QListWidget, QListWidgetItem, QPushButton
)

class InspectorPanel(QWidget):
    """Pure display widget driven strictly by selected_quest_id and facade data."""
    objective_toggled = Signal(str, str)  # (quest_id, objective_id)
    session_launched = Signal(str)        # (quest_id)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_quest_id = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(12)

        self.lbl_title = QLabel("Select or Create a Quest", self)
        self.lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ffffff;")
        self.lbl_title.setWordWrap(True)
        layout.addWidget(self.lbl_title)

        self.lbl_meta = QLabel("Click a block on the timeline to inspect.", self)
        self.lbl_meta.setStyleSheet("font-size: 13px; color: #a0a0a0;")
        self.lbl_meta.setWordWrap(True)
        layout.addWidget(self.lbl_meta)

        # Progress Section
        prog_frame = QFrame(self)
        prog_frame.setStyleSheet("background-color: #18181c; border-radius: 8px; padding: 10px;")
        prog_layout = QVBoxLayout(prog_frame)
        
        lbl_prog_title = QLabel("Weighted Objective Progress", self)
        lbl_prog_title.setStyleSheet("font-size: 12px; font-weight: bold; color: #7f7f8f;")
        prog_layout.addWidget(lbl_prog_title)

        self.progress_bar = QProgressBar(self)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: None; background-color: #2b2b36; border-radius: 4px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #0096D6; border-radius: 4px; }
        """)
        self.progress_bar.setValue(0)
        prog_layout.addWidget(self.progress_bar)
        layout.addWidget(prog_frame)

        # Objectives List
        layout.addWidget(QLabel("Objectives Checklist", self))
        self.obj_list = QListWidget(self)
        self.obj_list.setStyleSheet("""
            QListWidget { background-color: #18181c; color: #e0e0e0; border: 1px solid #2b2b36; border-radius: 8px; padding: 4px; }
            QListWidget::item { padding: 8px; border-bottom: 1px solid #22222a; }
            QListWidget::item:hover { background-color: #2b2b36; }
        """)
        self.obj_list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.obj_list)

        # Action Button
        self.btn_start = QPushButton("▶ Start Focus Session", self)
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet("""
            QPushButton { background-color: #0096D6; color: white; font-size: 14px; font-weight: bold; border-radius: 8px; padding: 12px; }
            QPushButton:disabled { background-color: #2b2b36; color: #7f7f8f; }
        """)
        self.btn_start.clicked.connect(lambda: self.current_quest_id and self.session_launched.emit(self.current_quest_id))
        layout.addWidget(self.btn_start)

        layout.addStretch()

    def update_quest_view(self, quest: dict | None, progress_percent: int = 0):
        """Renders inspector state from a fresh quest payload."""
        if not quest:
            self.current_quest_id = None
            self.lbl_title.setText("Select or Create a Quest")
            self.lbl_meta.setText("Click a block on the timeline to inspect.")
            self.progress_bar.setValue(0)
            self.obj_list.clear()
            self.btn_start.setEnabled(False)
            return

        self.current_quest_id = quest.get("quest_id")
        self.lbl_title.setText(quest.get("title", "Untitled Quest"))
        self.lbl_meta.setText(f"Track: {quest.get('track', 'General')} | Start: {quest.get('start_time')}")
        self.progress_bar.setValue(progress_percent)
        self.btn_start.setEnabled(True)

        self.obj_list.clear()
        objectives = quest.get("objectives", [])
        if not objectives:
            item = QListWidgetItem(f"○ Complete session: {quest.get('title')}")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.obj_list.addItem(item)
        else:
            for obj in objectives:
                status_symbol = "✓ " if obj.get("done", False) else "○ "
                weight_str = f" (x{obj.get('weight', 1)})" if obj.get("weight", 1) > 1 else ""
                item = QListWidgetItem(f"{status_symbol}{obj.get('title')}{weight_str}")
                item.setData(Qt.ItemDataRole.UserRole, obj.get("id"))
                self.obj_list.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem):
        obj_id = item.data(Qt.ItemDataRole.UserRole)
        if self.current_quest_id and obj_id:
            self.objective_toggled.emit(self.current_quest_id, obj_id)