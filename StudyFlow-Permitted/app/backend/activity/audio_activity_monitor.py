"""Windows background-audio session observer.

Reports processes with active Windows audio sessions that are not the current
foreground application. It does not record audio or make intervention
decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal

try:
    from pycaw.pycaw import AudioUtilities
except ImportError:
    AudioUtilities = None


AUDIO_SESSION_ACTIVE = 1


@dataclass(frozen=True)
class AudioActivityRecord:
    timestamp: datetime
    process_name: str
    process_id: int
    is_background: bool = True


class AudioActivityMonitor(QObject):
    """Poll active Windows audio sessions and expose background audio changes."""

    audio_activity_changed = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, interval_ms: int = 1000, parent=None):
        super().__init__(parent)
        self.interval_ms = max(250, int(interval_ms))
        self._current = ()
        self._dependency_error_reported = False

        self.timer = QTimer(self)
        self.timer.setInterval(self.interval_ms)
        self.timer.timeout.connect(self.poll)

    def start(self):
        if not self.timer.isActive():
            self.timer.start()
            self.poll()

    def stop(self):
        if self.timer.isActive():
            self.timer.stop()

    def is_running(self) -> bool:
        return self.timer.isActive()

    def poll(self):
        try:
            records = self._capture_audio_sessions()
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return

        identity = tuple(
            sorted((record.process_id, record.process_name) for record in records)
        )
        if identity != self._current:
            self._current = identity
            self.audio_activity_changed.emit(records)

    def _capture_audio_sessions(self) -> list[AudioActivityRecord]:
        if AudioUtilities is None:
            if not self._dependency_error_reported:
                self._dependency_error_reported = True
                self.error_occurred.emit(
                    "Background audio monitoring requires the pycaw package."
                )
            return []

        foreground_pid = self._foreground_process_id()
        records = []

        for session in AudioUtilities.GetAllSessions():
            try:
                if int(session.State) != AUDIO_SESSION_ACTIVE:
                    continue
            except Exception:
                continue

            try:
                process = session.Process
                if process is None:
                    continue
                process_id = int(process.pid)
                process_name = str(process.name() or "")
            except Exception:
                continue

            if not process_id or not process_name:
                continue
            if process_id == foreground_pid:
                continue

            records.append(
                AudioActivityRecord(
                    timestamp=datetime.now(),
                    process_name=process_name,
                    process_id=process_id,
                    is_background=True,
                )
            )

        return records

    @staticmethod
    def _foreground_process_id() -> int:
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            if not hwnd:
                return 0

            process_id = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(
                hwnd,
                ctypes.byref(process_id),
            )
            return int(process_id.value)
        except Exception:
            return 0
