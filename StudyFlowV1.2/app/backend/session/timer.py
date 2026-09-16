from PySide6.QtCore import QObject, QTimer, Signal


class SessionTimer(QObject):

    tick = Signal(int)
    finished = Signal()

    def __init__(self):
        super().__init__()

        self.seconds = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self._update)

    def start(self, minutes):

        self.seconds = minutes * 60

        self.tick.emit(self.seconds)

        self.timer.start(1000)

    def pause(self):
        self.timer.stop()

    def resume(self):
        self.timer.start(1000)

    def stop(self):
        self.timer.stop()

    def _update(self):

        self.seconds -= 1

        self.tick.emit(self.seconds)

        if self.seconds <= 0:

            self.timer.stop()

            self.finished.emit()
