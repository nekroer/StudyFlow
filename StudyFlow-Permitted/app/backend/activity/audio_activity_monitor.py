"""Best-effort observer for Windows processes that currently own audio sessions.

This module reports candidate background audio processes only. It does not
record audio, inspect microphone input, or make intervention decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal

try:
    from pycaw.pycaw import AudioUtilities
except ImportError:
    AudioUtilities = None


@dataclass(frozen=True)
class AudioActivityRecord:
    timestamp: datetime
    process_name: str
    process_id: int
    is_background: bool = True


class AudioActivityMonitor(QObject):
    """Optional Windows audio-session observer with a safe no-op fallback."""

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
        self.timer.stop()

    def is_running(self) -> bool:
        return self.timer.isActive()

    def poll(self):
        try:
            records = self._capture_audio_sessions()
            identity = tuple((r.process_id, r.process_name) for r in records)
            if identity != self._current:
                self._current = identity
                self.audio_activity_changed.emit(records)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def _capture_audio_sessions(self) -> list[AudioActivityRecord]:
        if AudioUtilities is None:
            if not self._dependency_error_reported:
                self._dependency_error_reported = True
                self.error_occurred.emit(
                    "Background audio monitoring requires the pycaw package."
                )
            return []

        foreground_pid = 0
        try:
            import ctypes
            foreground = ctypes.windll.user32.GetForegroundWindow()
            if foreground:
                pid = ctypes.c_ulong()
                ctypes.windll.user32.GetWindowThreadProcessId(
                    foreground, ctypes.byref(pid)
                )
                foreground_pid = int(pid.value)
        except Exception:
            foreground_pid = 0

        records = []
        for session in AudioUtilities.GetAllSessions():
            process = session.Process
            if process is None:
                continue

            try:
                state = int(session.State)
            except Exception:
                state = 0
            if state != 1:
                continue

            try:
                process_id = int(process.pid)
                process_name = str(process.name() or "")
            except Exception:
                continue

            if not process_id or not process_name:
                continue

            records.append(
                AudioActivityRecord(
                    timestamp=datetime.now(),
                    process_name=process_name,
                    process_id=process_id,
                    is_background=process_id != foreground_pid,
                )
            )

        return [record for record in records if record.is_background]
