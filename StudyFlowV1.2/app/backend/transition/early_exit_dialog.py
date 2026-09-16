from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QRadioButton, QButtonGroup


class EarlyExitDialog(QDialog):
    """Friction-aware early exit confirmation prompting session context, intent, and reason."""
    def __init__(self, session_title: str, goal: str, thought: str, elapsed_minutes: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Early Exit - Study Session")
        self.setFixedSize(420, 540)
        self.setStyleSheet("background-color: #18181c; color: white;")
        self.selected_reason = "Distracted"
        self.result_action = "continue"
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("⚠️ End Session Early?")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff8080;")
        layout.addWidget(title)

        context_frame = QFrame()
        context_frame.setStyleSheet("background-color: #121216; border: 1px solid #282832; border-radius: 8px; padding: 12px;")
        cf_layout = QVBoxLayout(context_frame)
        cf_layout.setSpacing(6)
        
        cf_layout.addWidget(QLabel(f"<b>Session:</b> {session_title or 'Unnamed Session'}"))
        cf_layout.addWidget(QLabel(f"<b>Goal:</b> {goal or 'None specified'}"))
        cf_layout.addWidget(QLabel(f"<b>Current Thought:</b> {thought or 'None specified'}"))
        cf_layout.addWidget(QLabel(f"<b>Focused Time:</b> {elapsed_minutes} minutes"))
        layout.addWidget(context_frame)

        layout.addWidget(QLabel("<b>Reason for stopping:</b>"))

        self.reasons = ["Emergency", "Distracted", "Too difficult", "Done"]
        self.btn_group = QButtonGroup(self)
        
        for i, reason in enumerate(self.reasons):
            rb = QRadioButton(reason)
            rb.setStyleSheet("color: #d0d0d8; font-size: 13px; padding: 4px;")
            if i == 1:
                rb.setChecked(True)
            rb.toggled.connect(lambda checked, r=reason: self._update_reason(r, checked))
            self.btn_group.addButton(rb)
            layout.addWidget(rb)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        
        self.continue_btn = QPushButton("Continue Session")
        self.continue_btn.setStyleSheet("background-color: #2b2b36; color: white; font-weight: bold; padding: 10px; border-radius: 6px; border: 1px solid #444;")
        self.continue_btn.clicked.connect(self.on_continue)
        btn_layout.addWidget(self.continue_btn)

        self.end_btn = QPushButton("End Session")
        self.end_btn.setStyleSheet("background-color: #E74C3C; color: white; font-weight: bold; padding: 10px; border-radius: 6px;")
        self.end_btn.clicked.connect(self.on_end)
        btn_layout.addWidget(self.end_btn)

        layout.addLayout(btn_layout)

    def _update_reason(self, reason: str, checked: bool):
        if checked:
            self.selected_reason = reason

    def on_continue(self):
        self.result_action = "continue"
        self.accept()

    def on_end(self):
        self.result_action = "end"
        self.accept()

    def get_exit_data(self) -> dict:
        # Emergency bypasses further friction prompts
        if self.selected_reason == "Emergency":
            self.result_action = "end"
            
        return {
            "action": self.result_action,
            "reason": self.selected_reason
        }