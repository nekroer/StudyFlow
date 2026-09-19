from datetime import datetime
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame


class TransitionDialog(QDialog):
    """Transition Mode preparation dialog with intentional cancellation (Escape disabled) and timestamped payload."""
    def __init__(self, countdown_seconds: int = 120, on_data_changed=None, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint | Qt.WindowType.CustomizeWindowHint)
        self.setStyleSheet("background-color: #121216; color: white;")
        
        self.time_remaining = countdown_seconds
        self.on_data_changed = on_data_changed
        self.collected_data = {
            "goal": "",
            "thought": "",
            "distraction": "",
            "created_at": datetime.now().isoformat()
        }
        
        self.init_ui()
        
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def keyPressEvent(self, event):
        # Explicitly disable Escape key to prevent accidental/reflexive cancellation
        if event.key() == Qt.Key_Escape:
            event.ignore()
            return
        super().keyPressEvent(event)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(80, 50, 80, 50)
        layout.setSpacing(15)

        title = QLabel("Transition Mode")
        title.setStyleSheet("font-size: 26px; font-weight: bold; color: #0096D6;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.timer_label = QLabel()
        self.timer_label.setStyleSheet("font-size: 36px; font-weight: bold; color: #ffd166; margin-bottom: 10px;")
        self.timer_label.setAlignment(Qt.AlignCenter)
        self._update_timer_display()
        layout.addWidget(self.timer_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #282832; max-height: 1px;")
        layout.addWidget(sep)

        layout.addWidget(QLabel("<b>Today's Goal</b>"))
        self.goal_input = QLineEdit()
        self.goal_input.setPlaceholderText("What specific outcome are you targeting?")
        self.goal_input.setStyleSheet("background: #18181c; border: 1px solid #333; border-radius: 6px; padding: 10px; color: white; font-size: 14px;")
        self.goal_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.goal_input)

        layout.addWidget(QLabel("<b>Current Thought</b>"))
        self.thought_input = QLineEdit()
        self.thought_input.setPlaceholderText("What's on your mind right now?")
        self.thought_input.setStyleSheet("background: #18181c; border: 1px solid #333; border-radius: 6px; padding: 10px; color: white; font-size: 14px;")
        self.thought_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.thought_input)

        layout.addWidget(QLabel("<b>Biggest Distraction</b>"))
        self.distraction_input = QLineEdit()
        self.distraction_input.setPlaceholderText("Park any active distractions here to clear your head...")
        self.distraction_input.setStyleSheet("background: #18181c; border: 1px solid #333; border-radius: 6px; padding: 10px; color: white; font-size: 14px;")
        self.distraction_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.distraction_input)

        layout.addStretch()

        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.cancel_btn = QPushButton("Cancel Transition")
        self.cancel_btn.setStyleSheet("background-color: #2b2b36; color: #aaa; border: 1px solid #444; padding: 8px 16px; border-radius: 6px;")
        self.cancel_btn.clicked.connect(self.on_cancel)
        bottom_layout.addWidget(self.cancel_btn)
        layout.addLayout(bottom_layout)

    def _on_text_changed(self):
        self.collected_data["goal"] = self.goal_input.text()
        self.collected_data["thought"] = self.thought_input.text()
        self.collected_data["distraction"] = self.distraction_input.text()
        if self.on_data_changed:
            self.on_data_changed(self.collected_data)

    def _update_timer_display(self):
        mins = self.time_remaining // 60
        secs = self.time_remaining % 60
        self.timer_label.setText(f"Session starts in  {mins:02d}:{secs:02d}")

    def _tick(self):
        self.time_remaining -= 1
        if self.time_remaining > 0:
            self._update_timer_display()
        else:
            self.timer.stop()
            self.timer_label.setText("Transition Complete. Let's begin.")
            self.timer_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #4cd137; margin-bottom: 10px;")
            QTimer.singleShot(1000, self.accept)

    def on_cancel(self):
        self.timer.stop()
        self.reject()

    def result_data(self) -> dict:
        return self.collected_data