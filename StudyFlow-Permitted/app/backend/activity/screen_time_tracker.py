"""Screen-time recorder built on top of the foreground ActivityMonitor."""

from datetime import datetime
import ctypes
import json
import time
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal

from app.backend.activity.activity_monitor import ActivityMonitor
from app.backend.activity.browser_activity_bridge import BrowserActivityBridge
from app.backend.paths import CACHE_DIR


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD),
    ]


class ScreenTimeTracker(QObject):
    """Aggregates foreground activity into persistent daily screen-time totals."""

    screen_time_updated = Signal(dict)
    error_occurred = Signal(str)

    def __init__(
        self,
        activity_monitor: ActivityMonitor | None = None,
        browser_bridge: BrowserActivityBridge | None = None,
        idle_timeout_sec: int = 60,
        parent=None,
    ):
        super().__init__(parent)

        self.activity_monitor = activity_monitor or ActivityMonitor(parent=self)
        self.browser_bridge = browser_bridge or BrowserActivityBridge(parent=self)
        self.idle_timeout_sec = max(1, int(idle_timeout_sec))

        self.data_file = CACHE_DIR / "screen_time.json"
        self._data = self._load_data()

        self._current_activity = None
        self._last_accounted_at = time.monotonic()
        self._dirty = False
        self._latest_browser_snapshot = {}
        self._last_browser_accounted_at = time.monotonic()

        self.accounting_timer = QTimer(self)
        self.accounting_timer.setInterval(1000)
        self.accounting_timer.timeout.connect(self._account_current_activity)

        self.save_timer = QTimer(self)
        self.save_timer.setInterval(10000)
        self.save_timer.timeout.connect(self._flush_if_dirty)

        self.activity_monitor.activity_changed.connect(self._on_activity_changed)
        self.activity_monitor.error_occurred.connect(self.error_occurred.emit)
        self.browser_bridge.snapshot_received.connect(self._on_browser_snapshot)
        self.browser_bridge.error_occurred.connect(self.error_occurred.emit)

    def start(self):
        """Start foreground observation and screen-time accounting."""
        if not self.activity_monitor.is_running():
            self.activity_monitor.start()
        if not self.browser_bridge.is_running():
            self.browser_bridge.start()

        self._last_accounted_at = time.monotonic()
        if not self.accounting_timer.isActive():
            self.accounting_timer.start()
        if not self.save_timer.isActive():
            self.save_timer.start()

        self._emit_update()

    def stop(self):
        """Stop accounting after persisting the current in-memory totals."""
        self._account_current_activity()
        self._flush_if_dirty()

        self.accounting_timer.stop()
        self.save_timer.stop()
        self.activity_monitor.stop()
        self.browser_bridge.stop()

    def is_running(self) -> bool:
        return self.accounting_timer.isActive()

    def current_activity(self):
        return self._current_activity

    def today_total_seconds(self) -> int:
        today = self._today_key()
        return int(self._data.get("days", {}).get(today, {}).get("total_seconds", 0))

    def today_applications(self) -> list[dict]:
        today = self._today_key()
        applications = (
            self._data.get("days", {})
            .get(today, {})
            .get("applications", {})
        )

        result = []
        for process_name, entry in applications.items():
            result.append(
                {
                    "process_name": process_name,
                    "executable_path": entry.get("executable_path", ""),
                    "seconds": int(entry.get("seconds", 0)),
                }
            )

        result.sort(key=lambda item: item["seconds"], reverse=True)
        return result

    def snapshot(self) -> dict:
        current = self._current_activity
        browser = self._latest_browser_snapshot

        return {
            "date": self._today_key(),
            "total_seconds": self.today_total_seconds(),
            "applications": self.today_applications(),
            "current_activity": (
                {
                    "process_name": current.process_name,
                    "window_title": current.window_title,
                    "process_id": current.process_id,
                    "executable_path": current.executable_path,
                }
                if current
                else None
            ),
            "is_running": self.is_running(),
            "is_idle": self._is_idle(),
            "browser_activity": dict(browser),
            "browser_sites": self.today_browser_sites(),
        }

    def today_browser_sites(self) -> list[dict]:
        today = self._today_key()
        sites = self._data.get("days", {}).get(today, {}).get("browser_sites", {})
        result = []
        for host, entry in sites.items():
            result.append({"host": host, "seconds": int(entry.get("seconds", 0))})
        result.sort(key=lambda item: item["seconds"], reverse=True)
        return result

    def _on_browser_snapshot(self, snapshot: dict):
        self._account_browser_activity()
        self._latest_browser_snapshot = snapshot
        self._last_browser_accounted_at = time.monotonic()
        self._emit_update()

    def _account_browser_activity(self):
        now = time.monotonic()
        elapsed = max(0.0, now - self._last_browser_accounted_at)
        self._last_browser_accounted_at = now

        if not self._latest_browser_snapshot:
            return
        current = self._current_activity
        if current is None or current.process_name.lower() != "chrome.exe" or self._is_idle():
            return

        active_tab = self._latest_browser_snapshot.get("active_tab", {})
        if not active_tab or active_tab.get("discarded"):
            return

        host = self._browser_host(active_tab.get("url", ""))
        seconds = int(elapsed)
        if not host or seconds <= 0:
            return

        today = self._today_key()
        day = self._data.setdefault("days", {}).setdefault(
            today,
            {"total_seconds": 0, "applications": {}},
        )
        sites = day.setdefault("browser_sites", {})
        entry = sites.setdefault(host, {"seconds": 0})
        entry["seconds"] += seconds
        self._dirty = True

    @staticmethod
    def _browser_host(url: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(url or "")
        return parsed.hostname or ""

    def _on_activity_changed(self, activity):
        self._account_current_activity()
        self._current_activity = activity
        self._last_accounted_at = time.monotonic()
        self._emit_update()

    def _account_current_activity(self):
        now = time.monotonic()
        elapsed = max(0.0, now - self._last_accounted_at)
        self._last_accounted_at = now

        if self._current_activity is None:
            return

        if self._is_idle():
            self._emit_update()
            return

        seconds = int(elapsed)
        if seconds <= 0:
            return

        today = self._today_key()
        day = self._data.setdefault("days", {}).setdefault(
            today,
            {"total_seconds": 0, "applications": {}},
        )

        process_name = self._current_activity.process_name or "Unknown"
        app = day["applications"].setdefault(
            process_name,
            {
                "seconds": 0,
                "executable_path": self._current_activity.executable_path,
            },
        )

        app["seconds"] += seconds
        day["total_seconds"] += seconds
        self._dirty = True
        self._emit_update()

    def _is_idle(self) -> bool:
        info = LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(LASTINPUTINFO)

        if not user32.GetLastInputInfo(ctypes.byref(info)):
            return False

        elapsed_ms = int(kernel32.GetTickCount64()) - int(info.dwTime)
        return elapsed_ms >= self.idle_timeout_sec * 1000

    def _emit_update(self):
        self.screen_time_updated.emit(self.snapshot())

    def _flush_if_dirty(self):
        if not self._dirty:
            return
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            self.data_file.write_text(
                json.dumps(self._data, indent=4),
                encoding="utf-8",
            )
            self._dirty = False
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def _load_data(self) -> dict:
        if not self.data_file.exists():
            return {"version": 1, "days": {}}

        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("days", {}), dict):
                return data
        except Exception as exc:
            self.error_occurred.emit(str(exc))

        return {"version": 1, "days": {}}

    @staticmethod
    def _today_key() -> str:
        return datetime.now().strftime("%Y-%m-%d")
