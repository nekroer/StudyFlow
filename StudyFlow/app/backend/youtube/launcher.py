import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import psutil


BASE_DIR = Path(__file__).parent
SERVER_FILE = BASE_DIR / "server.py"

_server_process = None


def is_vlc_running():
    for process in psutil.process_iter(["name"]):
        try:
            if process.info["name"] and "vlc" in process.info["name"].lower():
                return True
        except Exception:
            pass
    return False


def launch_vlc():
    if is_vlc_running():
        return

    possible_locations = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ]

    for location in possible_locations:
        if Path(location).exists():
            subprocess.Popen([location])
            return


def start_server():

    global _server_process

    if _server_process is not None:
        return

    _server_process = subprocess.Popen(
        [sys.executable, "-u", str(SERVER_FILE)],
        cwd=BASE_DIR,
        creationflags=subprocess.CREATE_NEW_CONSOLE
    )


def stop_server():

    global _server_process

    if _server_process is None:
        return

    _server_process.terminate()
    _server_process = None


def open_http():

    webbrowser.open("http://127.0.0.1:8080")


def start_everything():

    launch_vlc()

    time.sleep(2)

    start_server()

    time.sleep(2)

    open_http()


def stop_everything():

    stop_server()
