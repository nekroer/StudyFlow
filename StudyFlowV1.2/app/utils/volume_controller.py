from ctypes import POINTER, cast

from comtypes import CLSCTX_ALL
from pycaw.pycaw import (
    AudioUtilities,
    IAudioEndpointVolume,
)


_saved_volume = None


def _endpoint():
    devices = AudioUtilities.GetSpeakers()

    interface = devices.Activate(
        IAudioEndpointVolume._iid_,
        CLSCTX_ALL,
        None,
    )

    return cast(
        interface,
        POINTER(IAudioEndpointVolume),
    )


def mute_for_journal():
    global _saved_volume

    volume = _endpoint()

    _saved_volume = volume.GetMasterVolumeLevelScalar()

    volume.SetMasterVolumeLevelScalar(
        0,
        None,
    )


def restore_volume():
    global _saved_volume

    if _saved_volume is None:
        return

    volume = _endpoint()

    volume.SetMasterVolumeLevelScalar(
        _saved_volume,
        None,
    )
