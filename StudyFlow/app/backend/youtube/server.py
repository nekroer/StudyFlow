from flask import Flask
from flask_cors import CORS
import requests
import threading
import time
import json
from pathlib import Path

# -------------------------------------------------------
# Config
# -------------------------------------------------------

config_path = Path(__file__).parent / "config.json"


def get_config():
    with open(config_path, "r") as f:
        return json.load(f)


config = get_config()

PASSWORD = config["vlc_password"]
VLC_URL = config["vlc_url"]

CURRENT_VOLUME = config["low_volume"]

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

    cfg = get_config()

    print("Pause received")

    set_volume(cfg["high_volume"])

    return "OK"


@app.route("/play", methods=["POST"])
def play():

    cfg = get_config()

    print("Play received")

    set_volume(cfg["low_volume"])

    return "OK"


# -------------------------------------------------------
# Main
# -------------------------------------------------------

if __name__ == "__main__":

    print("=" * 40)
    print("StudyFlow Backend Started")
    print("=" * 40)

    cfg = get_config()

    print(f"Lecture Volume : {cfg['low_volume']}")
    print(f"Music Volume   : {cfg['high_volume']}")
    print(f"Fade Time      : {cfg['fade_time']} s")
    print(f"Fade Steps     : {cfg['fade_steps']}")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )