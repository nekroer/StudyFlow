from PySide6.QtWidgets import (
    QMainWindow,
    QStackedWidget
)

from app.ui.dashboard import DashboardPage
from app.ui.video_page import VideoPage
from app.ui.scheduler_page import SchedulerPage
from app.ui.journal_page import JournalPage
from app.ui.stats_page import StatsPage
from app.ui.settings_page import SettingsPage


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("StudyFlow")
        self.resize(1250, 780)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.dashboard = DashboardPage(self)
        self.video = VideoPage(self)
        self.scheduler = SchedulerPage(self)
        self.journal = JournalPage(self)
        self.stats = StatsPage(self)
        self.settings = SettingsPage(self)

        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.video)
        self.stack.addWidget(self.scheduler)
        self.stack.addWidget(self.journal)
        self.stack.addWidget(self.stats)
        self.stack.addWidget(self.settings)

    def show_dashboard(self):
        self.stack.setCurrentWidget(self.dashboard)

    def show_video(self):
        self.stack.setCurrentWidget(self.video)

    def show_scheduler(self):
        self.stack.setCurrentWidget(self.scheduler)

    def show_journal(self):
        self.stack.setCurrentWidget(self.journal)

    def show_stats(self):
        self.stack.setCurrentWidget(self.stats)

    def show_settings(self):
        self.stack.setCurrentWidget(self.settings)
