from PySide6.QtWidgets import (
    QWidget,
    QListWidget,
    QTextEdit,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QMessageBox,
)

from PySide6.QtGui import QTextCursor, QKeySequence, QShortcut
from PySide6.QtCore import Qt
from app.backend.paths import JOURNAL_FILE
from app.backend.journal.journal_manager import (
    load_today,
    save_today,
    list_journals,
    load_journal,
    timestamp,
    save_journal,
    today_name,
)

from app.utils.volume_controller import (
    mute_for_journal,
    restore_volume,
)


class JournalPage(QWidget):
    def __init__(self, window):
        super().__init__()
        self.storage_path = str(JOURNAL_FILE)

        self.window = window
        self.loading = False
        self.unsaved = False

        layout = QHBoxLayout(self)

        # ====================================
        # LEFT PANEL
        # ====================================

        left = QVBoxLayout()

        title = QLabel("Previous Journals")
        title.setAlignment(Qt.AlignCenter)
        left.addWidget(title)

        self.list = QListWidget()
        left.addWidget(self.list)

        layout.addLayout(left, 1)

        # ====================================
        # RIGHT PANEL
        # ====================================

        right = QVBoxLayout()

        heading = QLabel("Today's Journal")
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet("""
            font-size:20px;
            font-weight:bold;
        """)

        right.addWidget(heading)

        self.editor = QTextEdit()
        right.addWidget(self.editor)

        row = QHBoxLayout()

        self.time_button = QPushButton("Insert Timestamp")
        row.addWidget(self.time_button)

        back = QPushButton("← Dashboard")
        back.clicked.connect(self.go_back)
        row.addWidget(back)

        right.addLayout(row)

        layout.addLayout(right, 3)
        
        self.current_journal = today_name()

        # ====================================
        # Load today's journal
        # ====================================

        self.load_today_journal()

        # ====================================
        # Previous journals
        # ====================================

        self.refresh_list()

        # ====================================
        # Signals & Shortcuts
        # ====================================

        self.editor.textChanged.connect(
            self.text_changed
        )

        self.list.itemClicked.connect(
            self.open_old
        )

        self.time_button.clicked.connect(
            self.insert_timestamp
        )

        # Optional Ctrl+S shortcut for manual saving
        self.shortcut_save = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_save.activated.connect(self.manual_save)

    # ====================================

    def load_today_journal(self):
        self.current_journal = today_name()
        self.loading = True

        self.editor.setPlainText(
            load_today()
        )

        self.loading = False
        self.unsaved = False

        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)

    # ====================================

    def refresh_list(self):
        self.list.clear()

        for journal in list_journals():
            self.list.addItem(journal)

    # ====================================

    def text_changed(self):
        if self.loading:
            return

        self.unsaved = True

    # ====================================

    def save_current_journal(self):
        """Saves current text, parses todos, and updates editor content if lines changed to 'imported:'."""
        text_content = self.editor.toPlainText()
        
        if self.current_journal == today_name():
            updated_text = save_today(text_content)
        else:
            updated_text = save_journal(self.current_journal, text_content)

        # Reload text cleanly so updated 'imported:' status shows immediately in the text editor
        self.loading = True
        cursor_pos = self.editor.textCursor().position()
        
        self.editor.setPlainText(updated_text)
        
        cursor = self.editor.textCursor()
        cursor.setPosition(min(cursor_pos, len(updated_text)))
        self.editor.setTextCursor(cursor)
        
        self.loading = False
        self.unsaved = False

    # ====================================

    def manual_save(self):
        self.save_current_journal()

    # ====================================

    def open_old(self, item):
        target_journal = item.text()
        if target_journal == self.current_journal:
            return

        # Save current journal before switching away
        if self.unsaved:
            self.save_current_journal()

        self.current_journal = target_journal
        self.loading = True

        self.editor.setPlainText(
            load_journal(self.current_journal)
        )

        self.loading = False
        self.unsaved = False
        
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)

    # ====================================

    def insert_timestamp(self):
        cursor = self.editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.editor.setTextCursor(cursor)

        cursor.insertText(
            "\n\n"
            + timestamp()
            + "\n"
        )

    # ====================================

    def go_back(self):
        if self.unsaved:
            self.save_current_journal()

        restore_volume()
        self.window.show_dashboard()

    # ====================================

    def showEvent(self, event):
        super().showEvent(event)
        mute_for_journal()

    # ====================================

    def hideEvent(self, event):
        if self.unsaved:
            self.save_current_journal()

        restore_volume()
        super().hideEvent(event)