import threading

_started = False
_lock = threading.Lock()


def start_backend():

    global _started

    with _lock:

        if _started:
            return

        from app.backend.youtube.server import app

        thread = threading.Thread(
            target=lambda: app.run(
                host="127.0.0.1",
                port=5000,
                debug=False,
                use_reloader=False,
            ),
            daemon=True,
        )

        thread.start()

        _started = True
