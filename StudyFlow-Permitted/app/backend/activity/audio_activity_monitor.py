"""Best-effort observer for Windows processes that currently own audio sessions.

This module reports candidate background audio processes only. It does not
record audio, inspect microphone input, or make intervention decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QObject, QTimer, Signal


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
        # The Windows Core Audio COM implementation is intentionally isolated
        # behind this method. Until a platform-specific backend is supplied,
        # return no candidates rather than guessing from process activity.
        return []
