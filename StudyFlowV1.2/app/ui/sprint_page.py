import json
from pathlib import Path
from datetime import datetime, date

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QMessageBox, QComboBox, QFrame, 
    QScrollArea, QDialog, QListWidget, QTextEdit, QDateEdit, QCheckBox
)
from PySide6.QtCore import Qt, Signal, QMimeData, QTimer, QDate
from PySide6.QtGui import QDrag, QPixmap
from app.backend.sprints.sprints import SprintManager, CATEGORIES

from app.backend.paths import (
    TASKS_DONE_FILE,
    JOURNAL_DIR,
    SPRINTS_DONE_FILE,
)

CATEGORY_COLORS = {
    "URGENT": {
        "bg": "rgba(231, 76, 60, 0.04)",
        "header_bg": "rgba(231, 76, 60, 0.15)",
        "text": "#ff8080",
        "border": "#E74C3C"
    },
    "DEADLINES": {
        "bg": "rgba(241, 196, 15, 0.04)",
        "header_bg": "rgba(241, 196, 15, 0.15)",
        "text": "#ffd166",
        "border": "#F1C40F"
    },
    "ADMIN": {
        "bg": "rgba(52, 152, 219, 0.04)",
        "header_bg": "rgba(52, 152, 219, 0.15)",
        "text": "#79c0ff",
        "border": "#3498DB"
    },
    "CREATIVE": {
        "bg": "rgba(155, 89, 182, 0.04)",
        "header_bg": "rgba(155, 89, 182, 0.15)",
        "text": "#d2a8ff",
        "border": "#9B59B6"
    }
}


class ConfirmActionDialog(QDialog):
    """Generic confirmation dialog with a mandatory 3-second countdown before action can be confirmed."""
    def __init__(self, title: str, message_text: str = "", action_button_text: str = "Confirm", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.message_text = message_text
        self.action_btn_text = action_button_text
        self.countdown_seconds = 3
        self.setFixedSize(380, 200)
        self.setStyleSheet("background-color: #18181c; color: white;")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        self.text_content = QLabel(self.message_text)
        self.text_content.setWordWrap(True)
        self.text_content.setStyleSheet("font-size: 13px; color: #d0d0d6; line-height: 1.4;")
        layout.addWidget(self.text_content)

        self.info_label = QLabel("⚠️ Please review before proceeding.")
        self.info_label.setStyleSheet("font-size: 11px; color: #f39c12; font-weight: bold;")
        layout.addWidget(self.info_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b36; color: #ccc; border: 1px solid #444; 
                padding: 6px 14px; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background-color: #383844; color: white; }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton(f"{self.action_btn_text} (3s)")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60; color: white; border-radius: 6px; 
                padding: 6px 16px; font-weight: bold;
            }
            QPushButton:disabled {
                background-color: #2c3e50; color: #7f8c8d; border: 1px solid #34495e;
            }
            QPushButton:hover:enabled { background-color: #219653; }
        """)
        self.confirm_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)

        # 3-second countdown timer
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update_countdown)
        self.timer.start()

    def set_message(self, text: str):
        self.message_text = text
        self.text_content.setText(text)

    def update_countdown(self):
        self.countdown_seconds -= 1
        if self.countdown_seconds > 0:
            self.confirm_btn.setText(f"{self.action_btn_text} ({self.countdown_seconds}s)")
        else:
            self.confirm_btn.setText(self.action_btn_text)
            self.confirm_btn.setEnabled(True)
            self.timer.stop()


def log_sprint_completion(sprint):
    title = getattr(sprint, "title", "Untitled Task")
    category = getattr(sprint, "category", "GENERAL")
    logged_minutes = getattr(sprint, "logged_minutes", 0)
    sessions = getattr(sprint, "sessions", [])
    session_count = len(sessions) if isinstance(sessions, list) else 0

    end_time = datetime.now()
    timestamp_str = f"[{end_time.strftime('%Y-%m-%d %I:%M %p')}]"

    summary_block = (
        f"{timestamp_str} Task Completed: {title} ({category})\n"
        f"  • Total Time Focused: {logged_minutes} mins\n"
        f"  • Sessions Logged: {session_count}\n"
        f"{'-' * 60}\n"
    )

    try:
        TASKS_DONE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TASKS_DONE_FILE, "a", encoding="utf-8") as f:
            f.write(summary_block)

        JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
        today_journal_filename = end_time.strftime("%d-%m-%Y.md")
        today_journal_path = JOURNAL_DIR / today_journal_filename

        with open(today_journal_path, "a", encoding="utf-8") as f:
            f.write(summary_block)
    except Exception as e:
        print(f"Error persisting sprint text log: {e}")

    return summary_block


def show_completion_dialog(parent_widget, summary_block: str):
    dialog = QDialog(parent_widget)
    dialog.setWindowTitle("Task Completed & Archived")
    dialog.setMinimumSize(420, 260)
    dialog.setStyleSheet("background-color: #18181c; color: white;")

    dlg_layout = QVBoxLayout(dialog)
    dlg_layout.setContentsMargins(20, 20, 20, 20)

    header = QLabel("🎉 Task Completed & Archived Successfully!")
    header.setStyleSheet("color: #27AE60; font-size: 15px; font-weight: bold; margin-bottom: 5px;")
    dlg_layout.addWidget(header)

    preview = QTextEdit()
    preview.setReadOnly(True)
    preview.setPlainText(summary_block)
    preview.setStyleSheet("background-color: #121216; color: #d0d0d8; font-size: 12px; border: 1px solid #2d2d38; border-radius: 6px; padding: 8px;")
    dlg_layout.addWidget(preview)

    close_btn = QPushButton("Done")
    close_btn.setStyleSheet("""
        QPushButton {
            background-color: #0096D6; color: white; font-weight: bold; 
            padding: 8px 20px; border-radius: 6px;
        }
        QPushButton:hover { background-color: #007bb5; }
    """)
    close_btn.clicked.connect(dialog.accept)
    dlg_layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    dialog.exec()


class CompletedSprintsDialog(QDialog):
    def __init__(self, parent_page, parent=None):
        super().__init__(parent)
        self.parent_page = parent_page
        self.setWindowTitle("Completed Sprints History")
        self.setMinimumSize(560, 440)
        self.setStyleSheet("background-color: #18181c; color: white;")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header = QLabel("📜 Completed Sprints History")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #27AE60;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        sub_header = QLabel(f"Source Archive: {SPRINTS_DONE_FILE}")
        sub_header.setStyleSheet("font-size: 11px; color: #8c8c9a; margin-bottom: 2px;")
        sub_header.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(sub_header)

        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget {
                background-color: #121216; 
                border: 1px solid #2d2d38; 
                border-radius: 8px;
                padding: 6px;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #222228;
                color: #e0e0e6;
            }
        """)
        layout.addWidget(self.list_widget)
        self.load_history()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b36; color: white; font-weight: bold; 
                padding: 8px 18px; border-radius: 6px; border: 1px solid #444;
            }
            QPushButton:hover { background-color: #383844; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def load_history(self):
        self.list_widget.clear()
        if not SPRINTS_DONE_FILE.exists():
            self.list_widget.addItem("No completed sprints recorded yet.")
            return

        try:
            with open(SPRINTS_DONE_FILE, "r", encoding="utf-8") as f:
                records = json.load(f)

            if not records:
                self.list_widget.addItem("No completed sprints recorded yet.")
                return

            for item in reversed(records):
                title = item.get("title", "Untitled Task")
                category = item.get("category", "GENERAL")
                minutes = item.get("logged_minutes", 0)
                sessions = len(item.get("sessions", []))
                due = item.get("due_date", "No due date")

                entry_text = f"✓ {title}  [{category}]\n   • Focused Time: {minutes} mins ({sessions} sessions) | Due: {due}"
                self.list_widget.addItem(entry_text)
        except Exception as e:
            self.list_widget.addItem(f"Error loading completed sprints archive: {e}")


class EditTaskDialog(QDialog):
    def __init__(self, sprint, parent_page, parent=None):
        super().__init__(parent)
        self.sprint = sprint
        self.parent_page = parent_page
        self.setWindowTitle("Edit Task")
        self.setFixedSize(380, 380)
        self.setStyleSheet("background-color: #18181c; color: white;")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        layout.addWidget(QLabel("<b>Task Title:</b>"))
        self.title_input = QLineEdit(self.sprint.title)
        self.title_input.setStyleSheet("padding: 8px; background: #121216; border: 1px solid #333; border-radius: 6px; color: white;")
        layout.addWidget(self.title_input)

        layout.addWidget(QLabel("<b>Category:</b>"))
        self.category_dropdown = QComboBox()
        self.category_dropdown.addItems(CATEGORIES)
        idx = self.category_dropdown.findText(getattr(self.sprint, "category", CATEGORIES[0]))
        if idx >= 0:
            self.category_dropdown.setCurrentIndex(idx)
        self.category_dropdown.setStyleSheet("padding: 8px; background: #121216; border: 1px solid #333; border-radius: 6px; color: white;")
        layout.addWidget(self.category_dropdown)

        self.due_checkbox = QCheckBox("Set Due Date")
        self.due_checkbox.setStyleSheet("color: white; font-weight: bold; margin-top: 5px;")
        layout.addWidget(self.due_checkbox)

        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setStyleSheet("padding: 8px; background: #121216; border: 1px solid #333; border-radius: 6px; color: white;")
        
        current_due = getattr(self.sprint, "due_date", None)
        if current_due:
            self.due_checkbox.setChecked(True)
            try:
                d_obj = datetime.strptime(current_due, "%d-%m-%Y").date()
                self.date_edit.setDate(QDate(d_obj.year, d_obj.month, d_obj.day))
            except Exception:
                self.date_edit.setDate(QDate.currentDate())
        else:
            self.due_checkbox.setChecked(False)
            self.date_edit.setDate(QDate.currentDate())
            self.date_edit.setEnabled(False)

        self.due_checkbox.toggled.connect(self.date_edit.setEnabled)
        layout.addWidget(self.date_edit)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("padding: 7px 14px; background: #2b2b36; color: white; border-radius: 6px; border: 1px solid #444;")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("padding: 7px 16px; background: #0096D6; color: white; font-weight: bold; border-radius: 6px;")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _save(self):
        new_title = self.title_input.text().strip()
        new_cat = self.category_dropdown.currentText()
        new_due = self.date_edit.date().toString("dd-MM-YYYY") if self.due_checkbox.isChecked() else None

        if not new_title:
            QMessageBox.warning(self, "Warning", "Title cannot be empty.")
            return

        self.sprint.title = new_title
        self.sprint.category = new_cat
        self.sprint.due_date = new_due
        
        if hasattr(self.parent_page.sprint_manager, "save_sprints"):
            self.parent_page.sprint_manager.save_sprints()

        self.parent_page.refresh_board()
        self.accept()


class TaskDetailDialog(QDialog):
    work_on_task_requested = Signal(str, str)

    def __init__(self, sprint, parent_page, parent=None):
        super().__init__(parent)
        self.sprint = sprint
        self.parent_page = parent_page
        self.setWindowTitle(f"Task: {sprint.title}")
        self.resize(460, 420)
        self.setStyleSheet("background-color: #18181c; color: #eee;")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        self.title_label = QLabel(self.sprint.title)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        self.title_label.setWordWrap(True)
        header_layout.addWidget(self.title_label, stretch=3)

        edit_btn = QPushButton("✏ Edit")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b36; color: #79c0ff; border: 1px solid #388bfd;
                border-radius: 6px; padding: 5px 10px; font-size: 12px; font-weight: bold;
            }
            QPushButton:hover { background-color: #388bfd; color: white; }
        """)
        edit_btn.clicked.connect(self._open_edit)
        header_layout.addWidget(edit_btn, stretch=1)
        layout.addLayout(header_layout)

        due_date = getattr(self.sprint, "due_date", None) or "None"
        meta_info = QLabel(f"<b>Due Date:</b> {due_date}  |  <b>Total Time Focused:</b> {getattr(self.sprint, 'logged_minutes', 0)} mins")
        meta_info.setStyleSheet("color: #a0a0ab; font-size: 12px;")
        layout.addWidget(meta_info)

        layout.addWidget(QLabel("<b>Work Log History:</b>"))
        
        log_list = QListWidget()
        log_list.setStyleSheet("background-color: #121216; border: 1px solid #2d2d38; border-radius: 6px; padding: 4px;")
        
        sessions = getattr(self.sprint, "sessions", [])
        if not sessions:
            log_list.addItem("No focus sessions logged yet.")
        else:
            for s in reversed(sessions):
                time_str = s.get('timestamp', '').split('T')[0]
                log_list.addItem(f"• {time_str}: Focused for {s.get('duration_minutes', 0)} minutes")
        layout.addWidget(log_list)

        btn_layout = QHBoxLayout()
        work_btn = QPushButton("⏱ Focus on Task")
        work_btn.setStyleSheet("background-color: #0096D6; color: white; font-weight: bold; padding: 9px; border-radius: 6px;")
        work_btn.clicked.connect(self._start_work)
        btn_layout.addWidget(work_btn)

        done_btn = QPushButton("✓ Complete")
        done_btn.setStyleSheet("background-color: #27AE60; color: white; font-weight: bold; padding: 9px; border-radius: 6px;")
        done_btn.clicked.connect(self._toggle_done)
        btn_layout.addWidget(done_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("background-color: #2b2b36; color: white; padding: 9px; border-radius: 6px; border: 1px solid #444;")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _open_edit(self):
        edit_dlg = EditTaskDialog(self.sprint, self.parent_page, self)
        if edit_dlg.exec() == QDialog.Accepted:
            self.title_label.setText(self.sprint.title)

    def _start_work(self):
        self.work_on_task_requested.emit(self.sprint.id, self.sprint.title)
        self.accept()

    def _toggle_done(self):
        self.parent_page._complete_sprint_safely(self.sprint)
        self.accept()


class DragCard(QFrame):
    def __init__(self, sprint, parent_page):
        super().__init__()
        self.sprint = sprint
        self.parent_page = parent_page
        self.setCursor(Qt.PointingHandCursor)
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #18181c;
                border: 1px solid #282832;
                border-radius: 8px;
                padding: 10px;
            }
            QFrame:hover {
                background-color: #202026;
                border: 1px solid #0096D6;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title_label = QLabel(self.sprint.title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #f0f0f5;")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)

        due_date_str = getattr(self.sprint, "due_date", None)
        if due_date_str:
            try:
                due_date_obj = datetime.strptime(due_date_str, "%d-%m-%Y").date()
                delta_days = (due_date_obj - date.today()).days

                if delta_days < 0:
                    badge_text = f"⚠ {due_date_str} ({abs(delta_days)}d overdue)"
                    badge_style = "background-color: #3b2222; color: #ff8080; border: 1px solid #552b2b;"
                elif delta_days == 0:
                    badge_text = f"📅 Due Today"
                    badge_style = "background-color: #3b3522; color: #ffd166; border: 1px solid #55482b;"
                else:
                    badge_text = f"📅 {due_date_str} ({delta_days}d left)"
                    badge_style = "background-color: #22222c; color: #a0c4ff; border: 1px solid #333342;"

                badge_layout = QHBoxLayout()
                badge_layout.setContentsMargins(0, 0, 0, 0)
                due_label = QLabel(badge_text)
                due_label.setStyleSheet(f"{badge_style} font-size: 10px; padding: 2px 6px; border-radius: 4px;")
                badge_layout.addWidget(due_label)
                badge_layout.addStretch()
                layout.addLayout(badge_layout)
            except Exception:
                pass

        meta_layout = QHBoxLayout()
        meta_layout.setContentsMargins(0, 0, 0, 0)
        dur_label = QLabel(f"⏱ {getattr(self.sprint, 'logged_minutes', 0)}m focused")
        dur_label.setStyleSheet("color: #8c8c9a; font-size: 11px;")
        meta_layout.addWidget(dur_label)
        meta_layout.addStretch()

        done_btn = QPushButton("✓")
        done_btn.setToolTip("Complete Sprint")
        done_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60; color: white; 
                border: none; border-radius: 4px; padding: 3px 7px; font-weight: bold;
            }
            QPushButton:hover { background-color: #1E8449; }
        """)
        done_btn.clicked.connect(self._toggle_done)
        meta_layout.addWidget(done_btn)

        del_btn = QPushButton("✕")
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: #382222; color: #ff4d4f; 
                border: 1px solid #592b2b; border-radius: 4px; padding: 3px 7px;
            }
            QPushButton:hover { background-color: #4d2b2b; }
        """)
        del_btn.clicked.connect(lambda _, sid=self.sprint.id: self.parent_page._delete_card(sid))
        meta_layout.addWidget(del_btn)

        layout.addLayout(meta_layout)

    def _toggle_done(self):
        self.parent_page._complete_sprint_safely(self.sprint)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            dialog = TaskDetailDialog(self.sprint, self.parent_page, self)
            dialog.work_on_task_requested.connect(self.parent_page.start_study_session_requested.emit)
            dialog.exec_()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            mime_data.setText(self.sprint.id)
            drag.setMimeData(mime_data)
            pixmap = QPixmap(self.size())
            self.render(pixmap)
            drag.setPixmap(pixmap)
            drag.setHotSpot(event.position().toPoint())
            drag.exec_(Qt.MoveAction)


class DropColumn(QFrame):
    def __init__(self, category: str, parent_page):
        super().__init__()
        self.category = category.upper()
        self.parent_page = parent_page
        self.setAcceptDrops(True)
        self.empty_label = None

        color_info = CATEGORY_COLORS.get(self.category, {
            "bg": "rgba(25, 25, 30, 0.5)", 
            "header_bg": "#22222c", 
            "text": "#ffffff", 
            "border": "#333342"
        })

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color_info['bg']};
                border: 1px solid {color_info['border']};
                border-radius: 12px;
            }}
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(10)

        self.header = QLabel(f"{self.category}")
        self.header.setStyleSheet(f"""
            QLabel {{
                background-color: {color_info['header_bg']};
                color: {color_info['text']};
                border: 1px solid {color_info['border']};
                font-weight: bold;
                font-size: 13px;
                padding: 8px;
                border-radius: 8px;
            }}
        """)
        self.header.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")

        task_container = QWidget()
        task_container.setStyleSheet("background: transparent; border: none;")
        self.task_layout = QVBoxLayout(task_container)
        self.task_layout.setContentsMargins(0, 0, 0, 0)
        self.task_layout.setSpacing(10)
        self.task_layout.addStretch()

        scroll.setWidget(task_container)
        self.main_layout.addWidget(scroll)

    def set_empty_state(self, is_empty: bool):
        if self.empty_label:
            try:
                self.empty_label.deleteLater()
            except RuntimeError:
                pass
            self.empty_label = None

        if is_empty:
            messages = {
                "URGENT": "No burning priorities right now ✨",
                "DEADLINES": "No upcoming deadlines tracked",
                "ADMIN": "All routine maintenance clear",
                "CREATIVE": "Drop creative tasks here"
            }
            msg = messages.get(self.category, f"No {self.category.lower()} tasks")
            self.empty_label = QLabel(msg)
            self.empty_label.setStyleSheet("color: #727282; font-style: italic; font-size: 11px; margin-top: 25px;")
            self.empty_label.setAlignment(Qt.AlignCenter)
            
            insert_idx = max(0, self.task_layout.count() - 1)
            self.task_layout.insertWidget(insert_idx, self.empty_label)
            self.empty_label.show()

    def update_header_count(self, count: int):
        self.header.setText(f"{self.category}  ({count})")

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        sprint_id = event.mimeData().text()
        self.parent_page._move_sprint_category(sprint_id, self.category)
        event.acceptProposedAction()


class SprintPage(QWidget):
    back_requested = Signal()
    start_study_session_requested = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.sprint_manager = SprintManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        header_layout = QHBoxLayout()
        self.back_btn = QPushButton("← Dashboard")
        self.back_btn.setStyleSheet("background-color: transparent; border: 1px solid #444; padding: 6px 12px; border-radius: 6px; color: #ccc; font-weight: bold;")
        self.back_btn.clicked.connect(self.back_requested.emit)
        header_layout.addWidget(self.back_btn)
        header_layout.addSpacing(15)

        header = QLabel("Focus Sprints Board")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: white;")
        header_layout.addWidget(header)
        header_layout.addStretch()

        self.btn_view_done = QPushButton("📜 Completed Sprints")
        self.btn_view_done.setStyleSheet("background-color: #22222c; color: #27AE60; font-size: 13px; font-weight: bold; border: 1px solid #27AE60; border-radius: 6px; padding: 6px 14px;")
        self.btn_view_done.clicked.connect(lambda: CompletedSprintsDialog(self, self).exec())
        header_layout.addWidget(self.btn_view_done)

        layout.addLayout(header_layout)

        # Input Bar
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: #18181c; border: 1px solid #282832; border-radius: 8px; padding: 10px;")
        input_layout = QHBoxLayout(input_frame)
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Enter a new task title...")
        self.title_input.setStyleSheet("padding: 8px; border: 1px solid #333; border-radius: 6px; background: #121216; color: white;")
        input_layout.addWidget(self.title_input, stretch=3)

        self.category_dropdown = QComboBox()
        self.category_dropdown.addItems(CATEGORIES)
        self.category_dropdown.setStyleSheet("padding: 8px; border: 1px solid #333; border-radius: 6px; background: #121216; color: white;")
        input_layout.addWidget(self.category_dropdown, stretch=1)

        self.due_checkbox = QCheckBox("Due Date")
        self.due_checkbox.setStyleSheet("color: white; font-weight: bold;")
        input_layout.addWidget(self.due_checkbox)

        self.date_input = QDateEdit()
        self.date_input.setCalendarPopup(True)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setEnabled(False)
        self.date_input.setStyleSheet("padding: 8px; border: 1px solid #333; border-radius: 6px; background: #121216; color: white;")
        self.due_checkbox.toggled.connect(self.date_input.setEnabled)
        input_layout.addWidget(self.date_input, stretch=1)

        self.add_btn = QPushButton("+ Add Task")
        self.add_btn.setStyleSheet("background-color: #0096D6; color: white; font-weight: bold; padding: 8px 16px; border-radius: 6px;")
        self.add_btn.clicked.connect(self.add_sprint)
        input_layout.addWidget(self.add_btn)

        layout.addWidget(input_frame)

        self.board_layout = QHBoxLayout()
        self.board_layout.setSpacing(15)

        self.columns = {}
        for cat in CATEGORIES:
            col = DropColumn(category=cat, parent_page=self)
            self.columns[cat] = col
            self.board_layout.addWidget(col)

        layout.addLayout(self.board_layout)
        self.refresh_board()

    def _complete_sprint_safely(self, sprint):
        dialog = ConfirmActionDialog(
            title="Confirm Task Completion",
            message_text=f"Are you sure you want to mark '{sprint.title}' as completed?\nThis will move it to the permanent archive.",
            action_button_text="Confirm Completion",
            parent=self
        )
        
        if dialog.exec() == QDialog.Accepted:
            self.sprint_manager.mark_completed(sprint.id)
            self.refresh_board()
            summary = log_sprint_completion(sprint)
            show_completion_dialog(self, summary)

    def refresh_board(self):
        col_counts = {cat: 0 for cat in CATEGORIES}

        # Clear existing cards from all columns
        for cat, col in self.columns.items():
            layout = col.task_layout
            while layout.count() > 1:
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        sprints = self.sprint_manager.load_sprints()
        for sprint in sprints:
            if not sprint.completed and sprint.category in self.columns:
                card = DragCard(sprint=sprint, parent_page=self)
                layout = self.columns[sprint.category].task_layout
                layout.insertWidget(layout.count() - 1, card)
                col_counts[sprint.category] += 1

        for cat, count in col_counts.items():
            self.columns[cat].set_empty_state(count == 0)
            self.columns[cat].update_header_count(count)

    def add_sprint(self):
        title = self.title_input.text().strip()
        category = self.category_dropdown.currentText()
        due_date = self.date_input.date().toString("dd-MM-YYYY") if self.due_checkbox.isChecked() else None

        if not title:
            QMessageBox.warning(self, "Validation Error", "Task title cannot be empty.")
            return

        self.sprint_manager.add_sprint(title=title, category=category, due_date=due_date)

        self.title_input.clear()
        self.due_checkbox.setChecked(False)
        self.date_input.setDate(QDate.currentDate())
        self.refresh_board()

    def _move_sprint_category(self, sprint_id: str, new_category: str):
        for sprint in getattr(self.sprint_manager, "sprints", []):
            if sprint.id == sprint_id:
                sprint.category = new_category
                self.sprint_manager.save_sprints()
                break
        self.refresh_board()

    def _delete_card(self, sprint_id: str):
        target_sprint = None
        for s in getattr(self.sprint_manager, "sprints", []):
            if s.id == sprint_id:
                target_sprint = s
                break
        
        task_name = target_sprint.title if target_sprint else "this task"

        dialog = ConfirmActionDialog(
            title="Confirm Task Deletion",
            message_text=f"Are you sure you want to permanently delete '{task_name}'?\nThis action cannot be undone.",
            action_button_text="Confirm Deletion",
            parent=self
        )

        if dialog.exec() == QDialog.Accepted:
            self.sprint_manager.delete_sprint(sprint_id)
            self.refresh_board()