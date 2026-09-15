from PySide6.QtWidgets import QPushButton


class ActionButton(QPushButton):

    def __init__(self, text):

        super().__init__(text)

        self.setMinimumHeight(42)

        self.setStyleSheet("""
            QPushButton{

                background:#2D89EF;
                color:white;

                border:none;

                border-radius:10px;

                font-size:14px;
                font-weight:bold;

                padding:10px;
            }

            QPushButton:hover{

                background:#4798F5;

            }

            QPushButton:pressed{

                background:#1B5FBF;

            }
        """)