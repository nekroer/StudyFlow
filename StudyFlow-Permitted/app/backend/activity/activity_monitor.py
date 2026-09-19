"""Windows foreground-activity observer.

This module observes the foreground window and exposes normalized activity
records. It intentionally does not classify activity, block applications,
intervene, or make policy decisions.
"""

from dataclasses import dataclass
from datetime import datetime
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


@dataclass(frozen=True)
class ActivityRecord:
    """Normalized snapshot of the current Windows foreground activity."""

    timestamp: datetime
    window_handle: int
    process_id: int
    process_name: str
    window_title: str
    executable_path: str


class ActivityMonitor(QObject):
    """Polls the Windows foreground window and emits activity changes."""

    activity_changed = Signal(object)
    error_occurred = Signal(str)

    def __init__(self, interval_ms: int = 500, parent=None):
        super().__init__(parent)

        self.interval_ms = max(100, int(interval_ms))
        self._current_activity = None

        self.timer = QTimer(self)
        self.timer.setInterval(self.interval_ms)
        self.timer.timeout.connect(self.poll)

    def start(self):
        """Start observing foreground activity."""
        if not self.timer.isActive():
            self.timer.start()
            self.poll()

    def stop(self):
        """Stop observing foreground activity."""
        if self.timer.isActive():
            self.timer.stop()

    def is_running(self) -> bool:
        """Return whether the observation timer is active."""
        return self.timer.isActive()

    def current_activity(self):
        """Return the most recently observed ActivityRecord, if any."""
        return self._current_activity

    def poll(self):
        """Capture the current foreground activity and emit only on change."""
        try:
            record = self._capture_foreground_activity()
        except Exception as exc:
            self.error_occurred.emit(str(exc))
            return

        if not self._same_activity(record, self._current_activity):
            self._current_activity = record
            self.activity_changed.emit(record)

    @staticmethod
    def _same_activity(first, second) -> bool:
        if first is None or second is None:
            return first is second

        return (
            first.window_handle == second.window_handle
            and first.process_id == second.process_id
            and first.process_name == second.process_name
            and first.window_title == second.window_title
            and first.executable_path == second.executable_path
        )

    def _capture_foreground_activity(self):
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None

        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))

        window_title = self._window_title(hwnd)
        executable_path = self._executable_path(process_id.value)
        process_name = self._process_name(executable_path)

        return ActivityRecord(
            timestamp=datetime.now(),
            window_handle=int(hwnd),
            process_id=int(process_id.value),
            process_name=process_name,
            window_title=window_title,
            executable_path=executable_path,
        )

    @staticmethod
    def _window_title(hwnd: int) -> str:
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0:
            return ""

        buffer = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buffer, length + 1)
        return buffer.value

    @staticmethod
    def _executable_path(process_id: int) -> str:
        if not process_id:
            return ""

        handle = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION,
            False,
            process_id,
        )
        if not handle:
            return ""

        try:
            size = wintypes.DWORD(32768)
            buffer = ctypes.create_unicode_buffer(size.value)

            if kernel32.QueryFullProcessImageNameW(
                handle,
                0,
                buffer,
                ctypes.byref(size),
            ):
                return buffer.value
            return ""
        finally:
            kernel32.CloseHandle(handle)

    @staticmethod
    def _process_name(executable_path: str) -> str:
        if not executable_path:
            return ""
        return executable_path.rsplit("\\", 1)[-1]
