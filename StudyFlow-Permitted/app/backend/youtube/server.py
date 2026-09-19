from flask import Flask
from flask_cors import CORS
import requests
import threading
import time
print("Loaded server:", __file__)
print("Imported time module:", time)
import json
from pathlib import Path
print("=" * 60)
print(__file__)
print("=" * 60)
from app.backend.paths import YOUTUBE_CONFIG_FILE

last_pause_time = 0

# -------------------------------------------------------
# Config
# -------------------------------------------------------

config_path = YOUTUBE_CONFIG_FILE


def get_config():
    with open(config_path, "r") as f:
        return json.load(f)


config = get_config()

PASSWORD = config["vlc_password"]
VLC_URL = config["vlc_url"]

CURRENT_VOLUME = config["playing_volume"]

fade_thread = None
fade_stop = threading.Event()

app = Flask(__name__)
CORS(app)

# -------------------------------------------------------
# VLC
# -------------------------------------------------------

def send_volume(percent):

    # Convert UI percentage (0-200%)
    # to VLC volume (0-512)

    vlc_volume = int(percent * 256 / 100)

    try:

        print(f"{percent}% -> VLC {vlc_volume}")

        requests.get(
            VLC_URL,
            params={
                "command": "volume",
                "val": vlc_volume
            },
            auth=("", PASSWORD),
            timeout=2
        )

    except Exception as e:
        print("VLC Error:", e)

# -------------------------------------------------------
# Fade Engine
# -------------------------------------------------------

def fade_volume(target):

    global CURRENT_VOLUME

    cfg = get_config()

    fade_time = cfg["fade_time"]
    fade_steps = cfg["fade_steps"]

    delay = fade_time / fade_steps

    start = CURRENT_VOLUME

    fade_stop.clear()

    for i in range(1, fade_steps + 1):

        if fade_stop.is_set():
            print("Fade cancelled")
            return

        volume = int(
            start +
            (target - start) * i / fade_steps
        )

        send_volume(volume)

        CURRENT_VOLUME = volume

        time.sleep(delay)

    CURRENT_VOLUME = target


def set_volume(target):

    global fade_thread

    if fade_thread and fade_thread.is_alive():

        fade_stop.set()

        fade_thread.join()

    fade_thread = threading.Thread(
        target=fade_volume,
        args=(target,),
        daemon=True
    )

    fade_thread.start()


# -------------------------------------------------------
# Routes
# -------------------------------------------------------

@app.route("/")
def home():
    return "StudyFlow Running"


@app.route("/pause", methods=["POST"])
def pause():
    try:
        global last_pause_time

        print("Pause endpoint reached")

        last_pause_time = time.time()

        cfg = get_config()

        print("Config:", cfg)

        threading.Timer(
            cfg["ignore_pause_ms"] / 1000,
            process_pause
        ).start()

        print("Timer started")

        return "OK"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return str(e), 500

def process_pause():

    global last_pause_time

    cfg = get_config()

    if time.time() - last_pause_time >= cfg["ignore_pause_ms"] / 1000:
        print("Pause received")
        set_volume(cfg["paused_volume"])


@app.route("/play", methods=["POST"])
def play():

    global last_pause_time

    last_pause_time = 0

    cfg = get_config()

    print("Play received")

    set_volume(cfg["playing_volume"])

    return "OK"


# -------------------------------------------------------
# Main
# -------------------------------------------------------

if __name__ == "__main__":

    print("=" * 40)
    print("StudyFlow Backend Started")
    print("=" * 40)

    cfg = get_config()

    print(f"Lecture Volume : {cfg['playing_volume']}")
    print(f"Music Volume   : {cfg['paused_volume']}")
    print(f"Fade Time      : {cfg['fade_time']} s")
    print(f"Fade Steps     : {cfg['fade_steps']}")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )
