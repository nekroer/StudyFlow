import time
import webbrowser
import subprocess
from pathlib import Path
import psutil
import sys
import os
import requests
from app.backend.youtube.backend_runner import start_backend
from app.backend.paths import YOUTUBE_CONFIG_FILE
import json

with open(YOUTUBE_CONFIG_FILE, "r", encoding="utf-8") as f:
    config = json.load(f)

PASSWORD = config["vlc_password"]
VLC_URL = config["vlc_url"]
CURRENT_VOLUME = config["playing_volume"]
VLC_WEB_URL = config["vlc_web_url"]

# -------------------------------------------------------
# Debug
# -------------------------------------------------------

def debug_info(label):
    print("\n" + "=" * 60)
    print(label)
    print("=" * 60)
    print("sys.executable:", sys.executable)
    print("sys.argv:", sys.argv)
    print("__file__:", __file__)
    print("cwd:", os.getcwd())
    print("sys.frozen:", getattr(sys, "frozen", False))
    print("sys._MEIPASS:", getattr(sys, "_MEIPASS", None))
    print("=" * 60)


# -------------------------------------------------------
# VLC
# -------------------------------------------------------

def is_vlc_running():
    print("[1] Checking whether VLC is running...")

    for process in psutil.process_iter(["name"]):
        try:
            name = process.info["name"]

            if name:
                if "vlc" in name.lower():
                    print("[VLC CHECK] VLC IS RUNNING")
                    return True

        except Exception as e:
            print("[VLC CHECK] Process error:", repr(e))

    print("[VLC CHECK] VLC IS NOT RUNNING")
    return False


def launch_vlc():
    print("\n[2] launch_vlc()")

    if is_vlc_running():
        print("[2] VLC already running")
        return

    possible_locations = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ]

    for location in possible_locations:

        print("[2] Checking:", location)

        if Path(location).exists():
            print("[2] VLC FOUND:", location)

            process = subprocess.Popen([location])

            print("[2] VLC launched")
            print("[2] VLC PID:", process.pid)

            return

    print("[2] VLC NOT FOUND")


def wait_for_vlc_ready(
    timeout_seconds=15,
    check_interval=0.25
):
    print("\n[3] Waiting for VLC HTTP interface...")

    url = VLC_URL

    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:

        if not is_vlc_running():
            print("[3] VLC process not detected")
            time.sleep(check_interval)
            continue

        try:
            response = requests.get(
                url,
                auth=("", PASSWORD),
                timeout=1
            )

            if response.status_code == 200:

                # Make sure the response is actually valid JSON.
                response.json()

                print("[3] VLC HTTP interface READY")
                return True

            print(
                "[3] VLC HTTP responded with:",
                response.status_code
            )

        except requests.RequestException as e:
            print("[3] VLC HTTP not ready:", repr(e))

        except ValueError as e:
            print("[3] VLC returned invalid JSON:", repr(e))

        time.sleep(check_interval)

    print("[3] VLC HTTP interface FAILED TO BECOME READY")
    return False



# -------------------------------------------------------
# HTTP Interface
# -------------------------------------------------------

def open_http():
    print("\n[4] Opening VLC HTTP interface")

    webbrowser.open(VLC_WEB_URL)

# -------------------------------------------------------
# Startup
# -------------------------------------------------------

def start_everything():

    debug_info("STARTING VIDEO SYSTEM")

    print("[START] Calling launch_vlc()")
    launch_vlc()

    print("[START] Waiting for VLC readiness...")

    if not wait_for_vlc_ready():
        print("[START] VLC failed to become ready")
        return False

    print("[START] VLC is ready")

    print("[START] Calling start_backend()")

    try:
        start_backend()
        print("[START] Backend call returned successfully")

    except Exception:
        import traceback
        traceback.print_exc()
        return False

    print("[START] Calling open_http()")
    open_http()

    print("[START] COMPLETE")

    return True


def stop_everything():
    print("[STOP] stop_everything()")



def stop_everything():
    print("[STOP] stop_everything()")