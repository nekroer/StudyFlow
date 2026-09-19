"""Local bridge for browser activity reported by the StudyFlow Chrome extension.

The bridge binds only to 127.0.0.1 and accepts short-lived browser snapshots.
It does not expose a public network service, classify content, or block tabs.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Lock, Thread
from time import time

from PySide6.QtCore import QObject, Signal


class BrowserActivityBridge(QObject):
    """Receives extension snapshots through a localhost HTTP endpoint."""

    snapshot_received = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, host: str = "127.0.0.1", port: int = 8765, parent=None):
        super().__init__(parent)
        self.host = host
        self.port = int(port)
        self._lock = Lock()
        self._latest = {}
        self._server = None
        self._thread = None

    def start(self) -> bool:
        if self._server is not None:
            return True

        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                return

            def do_POST(self):
                if self.path != "/v1/browser-activity":
                    self.send_error(404)
                    return

                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if length <= 0 or length > 65536:
                        raise ValueError("Invalid request size")
                    payload = json.loads(self.rfile.read(length).decode("utf-8"))
                    if not isinstance(payload, dict):
                        raise ValueError("Payload must be an object")
                    payload["received_at"] = time()
                    with bridge._lock:
                        bridge._latest = payload
                    bridge.snapshot_received.emit(payload)
                    body = b'{"ok":true}'
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                except Exception as exc:
                    bridge.error_occurred.emit(str(exc))
                    self.send_error(400, str(exc))

        try:
            self._server = ThreadingHTTPServer((self.host, self.port), Handler)
            self._thread = Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            return True
        except Exception as exc:
            self._server = None
            self.error_occurred.emit(str(exc))
            return False

    def stop(self):
        if self._server is None:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None

    def latest_snapshot(self) -> dict:
        with self._lock:
            return dict(self._latest)

    def is_running(self) -> bool:
        return self._server is not None
