import sys
import ctypes
from pathlib import Path

# ============================================
# Force Windows to use ONE application identity
# ============================================

ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
    "StudyFlow.StudyFlow.1.0"
)

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from app.ui.window import MainWindow


def main():

    # ============================================
    # Application Identity (used by QStandardPaths)
    # ============================================

    QCoreApplication.setOrganizationName("StudyFlow")
    QCoreApplication.setOrganizationDomain("studyflow.app")
    QCoreApplication.setApplicationName("StudyFlow")

    app = QApplication(sys.argv)

    icon_path = (
        Path(__file__).parent
        / "app"
        / "assets"
        / "icons"
        / "logo.ico"
    )

    icon = QIcon(str(icon_path))

    app.setWindowIcon(icon)

    window = MainWindow()

    window.setWindowIcon(icon)

    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()