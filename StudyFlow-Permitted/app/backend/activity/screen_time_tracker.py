"""Screen-time recorder built on top of foreground, browser, and audio activity."""

from datetime import datetime
import ctypes
import json
import time
from ctypes import wintypes

from PySide6.QtCore import QObject, QTimer, Signal

from app.backend.activity.activity_monitor import ActivityMonitor
from app.backend.activity.browser_activity_bridge import BrowserActivityBridge
from app.backend.activity.audio_activity_monitor import AudioActivityMonitor
from app.backend.paths import CACHE_DIR


user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("dwTime", wintypes.DWORD),
    ]


class ScreenTimeTracker(QObject):
    """Aggregates meaningful foreground and background-audio activity."""

    IGNORED_PROCESSES = {
        "applicationframehost.exe",
        "backgroundtaskhost.exe",
        "conhost.exe",
        "ctfmon.exe",
        "dllhost.exe",
        "dwm.exe",
        "explorer.exe",
        "fontdrvhost.exe",
        "lockapp.exe",
        "openwith.exe",
        "runtimebroker.exe",
        "searchhost.exe",
        "sihost.exe",
        "smartscreen.exe",
        "startmenuexperiencehost.exe",
        "svchost.exe",
        "systemsettings.exe",
        "taskhostw.exe",
        "textinputhost.exe",
        "wmiprvse.exe",
        "wudfhost.exe",
    }

    BROWSER_PROCESS = "chrome.exe"
    MAX_BROWSER_GAP_SEC = 15.0

    screen_time_updated = Signal(dict)
    error_occurred = Signal(str)

    def __init__(
        self,
        activity_monitor: ActivityMonitor | None = None,
        browser_bridge: BrowserActivityBridge | None = None,
        audio_monitor: AudioActivityMonitor | None = None,
        idle_timeout_sec: int = 60,
        parent=None,
    ):
        super().__init__(parent)

        self.activity_monitor = activity_monitor or ActivityMonitor(parent=self)
        self.browser_bridge = browser_bridge or BrowserActivityBridge(parent=self)
        self.audio_monitor = audio_monitor or AudioActivityMonitor(parent=self)
        self.idle_timeout_sec = max(1, int(idle_timeout_sec))

        self.data_file = CACHE_DIR / "screen_time.json"
        self._data = self._load_data()

        self._current_activity = None
        self._last_accounted_at = time.monotonic()
        self._dirty = False

        self._latest_browser_snapshot = {}
        self._last_browser_accounted_at = time.monotonic()

        self._latest_audio_activity = []
        self._last_audio_accounted_at = time.monotonic()

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
        self.audio_monitor.audio_activity_changed.connect(
            self._on_audio_activity_changed
        )
        self.audio_monitor.error_occurred.connect(self.error_occurred.emit)

    def start(self):
        """Start foreground, browser, and background-audio observation."""
        if not self.activity_monitor.is_running():
            self.activity_monitor.start()
        if not self.browser_bridge.is_running():
            self.browser_bridge.start()
        if not self.audio_monitor.is_running():
            self.audio_monitor.start()

        now = time.monotonic()
        self._last_accounted_at = now
        self._last_browser_accounted_at = now
        self._last_audio_accounted_at = now

        if not self.accounting_timer.isActive():
            self.accounting_timer.start()
        if not self.save_timer.isActive():
            self.save_timer.start()

        self._emit_update()

    def stop(self):
        """Stop observation after persisting current in-memory totals."""
        self._account_current_activity()
        self._account_browser_activity()
        self._account_background_audio()
        self._flush_if_dirty()

        self.accounting_timer.stop()
        self.save_timer.stop()
        self.activity_monitor.stop()
        self.browser_bridge.stop()
        self.audio_monitor.stop()

    def refresh_now(self):
        """Synchronously account pending activity, persist it, and emit a fresh snapshot."""
        if not self.is_running():
            self._emit_update()
            return

        self._account_current_activity()
        self._account_browser_activity()
        self._account_background_audio()
        self._flush_if_dirty()
        self._emit_update()

    def is_running(self) -> bool:
        return self.accounting_timer.isActive()

    def current_activity(self):
        return self._current_activity

    def today_total_seconds(self) -> int:
        today = self._today_key()
        return int(
            self._data.get("days", {})
            .get(today, {})
            .get("total_seconds", 0)
        )

    def today_applications(self) -> list[dict]:
        today = self._today_key()
        applications = (
            self._data.get("days", {})
            .get(today, {})
            .get("applications", {})
        )

        result = []
        for process_name, entry in applications.items():
            foreground_seconds = int(entry.get("foreground_seconds", entry.get("seconds", 0)))
            background_audio_seconds = int(entry.get("background_audio_seconds", 0))
            result.append(
                {
                    "process_name": process_name,
                    "executable_path": entry.get("executable_path", ""),
                    "foreground_seconds": foreground_seconds,
                    "background_audio_seconds": background_audio_seconds,
                    "total_seconds": foreground_seconds + background_audio_seconds,
                    "seconds": foreground_seconds,
                }
            )

        result.sort(key=lambda item: item["total_seconds"], reverse=True)
        return result

    def snapshot(self) -> dict:
        return {
            "date": self._today_key(),
            "total_seconds": self.today_total_seconds(),
            "applications": self.today_applications(),
            "current_activity": (
                {
                    "process_name": self._current_activity.process_name,
                    "window_title": self._current_activity.window_title,
                    "process_id": self._current_activity.process_id,
                    "executable_path": self._current_activity.executable_path,
                }
                if self._current_activity
                else None
            ),
            "is_running": self.is_running(),
            "is_idle": self._is_idle(),
            "browser_activity": dict(self._latest_browser_snapshot),
            "browser_sites": self.today_browser_sites(),
            "background_audio": self.today_background_audio(),
        }

    def today_browser_sites(self) -> list[dict]:
        today = self._today_key()
        sites = (
            self._data.get("days", {})
            .get(today, {})
            .get("browser_sites", {})
        )

        result = []
        for host, entry in sites.items():
            foreground_seconds = int(entry.get("foreground_seconds", entry.get("seconds", 0)))
            background_audio_seconds = int(entry.get("background_audio_seconds", 0))
            result.append(
                {
                    "host": host,
                    "foreground_seconds": foreground_seconds,
                    "background_audio_seconds": background_audio_seconds,
                    "total_seconds": foreground_seconds + background_audio_seconds,
                    "seconds": foreground_seconds,
                }
            )

        result.sort(key=lambda item: item["total_seconds"], reverse=True)
        return result

    def _on_browser_snapshot(self, snapshot: dict):
        self._account_browser_activity()
        self._latest_browser_snapshot = snapshot
        self._last_browser_accounted_at = time.monotonic()
        self._emit_update()

    def _account_browser_activity(self):
        now = time.monotonic()
        elapsed = max(0.0, now - self._last_browser_accounted_at)
        elapsed = min(elapsed, self.MAX_BROWSER_GAP_SEC)
        self._last_browser_accounted_at = now

        if not self._latest_browser_snapshot:
            return
        if self._is_idle():
            return

        active_activity = self._current_activity
        chrome_foreground = (
            active_activity is not None
            and active_activity.process_name.lower() == self.BROWSER_PROCESS
        )

        active_tab = self._latest_browser_snapshot.get("active_tab") or {}
        audible_tabs = self._latest_browser_snapshot.get("audible_tabs") or []

        foreground_tab_id = active_tab.get("tab_id") if chrome_foreground else None
        seconds = int(elapsed)
        if seconds <= 0:
            return

        today = self._today_key()
        day = self._data.setdefault("days", {}).setdefault(
            today,
            {"total_seconds": 0, "applications": {}},
        )
        sites = day.setdefault("browser_sites", {})

        changed = False

        if chrome_foreground and active_tab and not active_tab.get("discarded"):
            host = self._browser_host(active_tab.get("url", ""))
            if host:
                entry = sites.setdefault(
                    host,
                    {
                        "foreground_seconds": 0,
                        "background_audio_seconds": 0,
                    },
                )
                entry["foreground_seconds"] += seconds
                changed = True

                app = self._application_entry(
                    day,
                    self.BROWSER_PROCESS,
                    active_activity.executable_path if active_activity else "",
                )
                app["foreground_seconds"] += seconds

        for tab in audible_tabs:
            if tab.get("discarded"):
                continue
            tab_id = tab.get("tab_id")
            if foreground_tab_id is not None and tab_id == foreground_tab_id:
                continue

            host = self._browser_host(tab.get("url", ""))
            if not host:
                continue

            entry = sites.setdefault(
                host,
                {
                    "foreground_seconds": 0,
                    "background_audio_seconds": 0,
                },
            )
            entry["background_audio_seconds"] += seconds
            changed = True

            app = self._application_entry(
                day,
                self.BROWSER_PROCESS,
                active_activity.executable_path if active_activity else "",
            )
            app["background_audio_seconds"] += seconds

        if changed:
            self._dirty = True

    @staticmethod
    def _browser_host(url: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(url or "")
        return parsed.hostname or ""

    def today_background_audio(self) -> list[dict]:
        today = self._today_key()
        audio = (
            self._data.get("days", {})
            .get(today, {})
            .get("background_audio", {})
        )

        result = []
        for process_name, entry in audio.items():
            result.append(
                {
                    "process_name": process_name,
                    "process_id": int(entry.get("process_id", 0)),
                    "seconds": int(entry.get("seconds", 0)),
                }
            )

        result.sort(key=lambda item: item["seconds"], reverse=True)
        return result

    def _on_audio_activity_changed(self, records):
        self._account_background_audio()
        self._latest_audio_activity = [
            record for record in records if record.is_background
        ]
        self._last_audio_accounted_at = time.monotonic()
        self._emit_update()

    def _account_background_audio(self):
        now = time.monotonic()
        elapsed = max(0.0, now - self._last_audio_accounted_at)
        self._last_audio_accounted_at = now

        if self._is_idle():
            return

        seconds = int(elapsed)
        if seconds <= 0 or not self._latest_audio_activity:
            return

        today = self._today_key()
        day = self._data.setdefault("days", {}).setdefault(
            today,
            {"total_seconds": 0, "applications": {}},
        )
        audio = day.setdefault("background_audio", {})

        for record in self._latest_audio_activity:
            process_name = record.process_name or "Unknown"

            entry = audio.setdefault(
                process_name,
                {"process_id": int(record.process_id), "seconds": 0},
            )
            entry["seconds"] += seconds

            app = self._application_entry(day, process_name, "")
            app["background_audio_seconds"] += seconds

        self._dirty = True

    def _on_activity_changed(self, activity):
        self._account_current_activity()
        self._current_activity = activity

        now = time.monotonic()
        self._last_accounted_at = now
        self._last_browser_accounted_at = now
        self._last_audio_accounted_at = now
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

        process_name = self._current_activity.process_name or "Unknown"
        if process_name.lower() in self.IGNORED_PROCESSES:
            return

        today = self._today_key()
        day = self._data.setdefault("days", {}).setdefault(
            today,
            {"total_seconds": 0, "applications": {}},
        )

        app = self._application_entry(
            day,
            process_name,
            self._current_activity.executable_path,
        )
        app["foreground_seconds"] += seconds
        day["total_seconds"] += seconds
        self._dirty = True
        self._emit_update()

    @staticmethod
    def _application_entry(day: dict, process_name: str, executable_path: str) -> dict:
        applications = day.setdefault("applications", {})
        entry = applications.setdefault(
            process_name,
            {
                "foreground_seconds": 0,
                "background_audio_seconds": 0,
                "executable_path": executable_path,
            },
        )

        if "foreground_seconds" not in entry:
            entry["foreground_seconds"] = int(entry.get("seconds", 0))
        if "background_audio_seconds" not in entry:
            entry["background_audio_seconds"] = 0
        if not entry.get("executable_path") and executable_path:
            entry["executable_path"] = executable_path

        return entry

    def _is_idle(self) ->bool:
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
            return {"version": 2, "days": {}}

        try:
            data = json.loads(self.data_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("days", {}), dict):
                return data
        except Exception as exc:
            self.error_occurred.emit(str(exc))

        return {"version": 2, "days": {}}

    @staticmethod
    def _today_key() -> str:
        return datetime.now().strftime("%Y-%m-%d")
