from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QRadioButton, QButtonGroup


class EarlyExitDialog(QDialog):
    """Friction-aware early exit confirmation prompting session context, intent, and reason."""
    def __init__(self, session_title: str, goal: str, thought: str, elapsed_minutes: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Early Exit - Study Session")
        self.setFixedSize(440, 620)
        self.setStyleSheet("""
            QDialog {
                background-color: #18181c;
                color: #ffffff;
            }
            QPushButton {
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
                padding: 10px 16px;
            }
        """)
        self.selected_reason = "Distracted"
        self.result_action = "continue"
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        title = QLabel("⚠️ End Session Early?")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ff8080; margin-bottom: 2px;")
        layout.addWidget(title)

        # Context Frame Card with explicit text colors
        context_frame = QFrame()
        context_frame.setStyleSheet("""
            QFrame {
                background-color: #121216;
                border: 1px solid #282832;
                border-radius: 8px;
                padding: 12px;
            }
            QLabel {
                color: #e0e0e0;
                font-size: 13px;
            }
        """)
        cf_layout = QVBoxLayout(context_frame)
        cf_layout.setSpacing(6)
        
        cf_layout.addWidget(QLabel(f"<b>Session:</b> {session_title or 'Unnamed Session'}"))
        cf_layout.addWidget(QLabel(f"<b>Goal:</b> {goal or 'None specified'}"))
        cf_layout.addWidget(QLabel(f"<b>Current Thought:</b> {thought or 'None specified'}"))
        cf_layout.addWidget(QLabel(f"<b>Focused Time:</b> {elapsed_minutes} minutes"))
        layout.addWidget(context_frame)

        reason_header = QLabel("<b>Reason for stopping:</b>")
        reason_header.setStyleSheet("color: #ffffff; font-size: 14px; margin-top: 4px;")
        layout.addWidget(reason_header)

        # Radio Buttons with visible indicator styling
        self.reasons = ["Emergency", "Distracted", "Too difficult", "Done"]
        self.btn_group = QButtonGroup(self)
        
        for i, reason in enumerate(self.reasons):
            rb = QRadioButton(reason)
            rb.setStyleSheet("""
                QRadioButton {
                    color: #ffffff;
                    font-size: 13px;
                    padding: 9px 12px;
                    background-color: #212128;
                    border: 1px solid #2e2e3a;
                    border-radius: 6px;
                }
                QRadioButton:hover {
                    background-color: #2b2b36;
                    border-color: #0096D6;
                }
                QRadioButton:checked {
                    background-color: #26354a;
                    border-color: #0096D6;
                }
                QRadioButton::indicator {
                    width: 16px;
                    height: 16px;
                    border-radius: 8px;
                    border: 2px solid #666677;
                    background-color: #18181c;
                }
                QRadioButton::indicator:checked {
                    border-color: #0096D6;
                    background-color: #0096D6;
                }
            """)
            if i == 1:
                rb.setChecked(True)
            rb.toggled.connect(lambda checked, r=reason: self._update_reason(r, checked))
            self.btn_group.addButton(rb)
            layout.addWidget(rb)

        layout.addStretch()

        # Action Buttons Layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.continue_btn = QPushButton("Continue Session")
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #2b2b36;
                color: white;
                border: 1px solid #444;
            }
            QPushButton:hover {
                background-color: #3f3f4e;
            }
        """)
        self.continue_btn.clicked.connect(self.on_continue)
        btn_layout.addWidget(self.continue_btn)

        self.end_btn = QPushButton("End Session")
        self.end_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        """)
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
        if self.selected_reason == "Emergency":
            self.result_action = "end"
            
        return {
            "action": self.result_action,
            "reason": self.selected_reason
        }