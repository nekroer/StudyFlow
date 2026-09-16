from PySide6.QtCore import QTimer

try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    PYCAW_AVAILABLE = True
except ImportError:
    PYCAW_AVAILABLE = False


class WindowsVolumeManager:
    """Manages Windows master volume detection, smooth fading to arbitrary targets, and restoration."""
    def __init__(self):
        self.original_volume = None
        self.volume_interface = None
        self.fade_timer = QTimer()
        self.fade_timer.timeout.connect(self._fade_step)
        self._init_audio()

    _target_vol = 0.0
    _decrement = 0.0
    _current_step = 0
    _total_steps = 1

    def _init_audio(self):
        if not PYCAW_AVAILABLE:
            return
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.volume_interface = interface.QueryInterface(IAudioEndpointVolume)
        except Exception as e:
            print(f"Volume Manager Init Error: {e}")

    def get_master_volume(self) -> float:
        """Returns current master volume scalar between 0.0 and 1.0."""
        if not self.volume_interface:
            return 1.0
        try:
            return self.volume_interface.GetMasterVolumeLevelScalar()
        except Exception:
            return 1.0

    def save_original_volume(self):
        if self.original_volume is None:
            self.original_volume = self.get_master_volume()

    def set_volume(self, scalar: float):
        if not self.volume_interface:
            return
        try:
            scalar = max(0.0, min(1.0, scalar))
            self.volume_interface.SetMasterVolumeLevelScalar(scalar, None)
        except Exception as e:
            print(f"Error setting volume: {e}")

    def restore_volume(self):
        """Restores volume back to the original level captured prior to fading."""
        if self.original_volume is not None:
            self.set_volume(self.original_volume)
            self.original_volume = None

    def is_fading(self) -> bool:
        return self.fade_timer.isActive()

    def fade_to(self, target: float = 0.0, duration_seconds: int = 180, step_ms: int = 200):
        """Smoothly fades volume to a target scalar over a given duration."""
        self.save_original_volume()
        start_vol = self.get_master_volume()
        self._target_vol = max(0.0, min(1.0, target))
        
        steps = int((duration_seconds * 1000) / step_ms)
        if steps <= 0:
            steps = 1
        
        self._total_steps = steps
        self._current_step = 0
        
        total_diff = start_vol - self._target_vol
        self._decrement = total_diff / steps if steps > 0 else total_diff
        
        self.fade_timer.setInterval(step_ms)
        self.fade_timer.start()

    def _fade_step(self):
        self._current_step += 1
        current_vol = self.get_master_volume()
        
        if self._decrement >= 0:
            new_vol = max(self._target_vol, current_vol - abs(self._decrement))
        else:
            new_vol = min(self._target_vol, current_vol + abs(self._decrement))
            
        self.set_volume(new_vol)
        
        if new_vol == self._target_vol or self._current_step >= self._total_steps:
            self.fade_timer.stop()

    def cancel_fade(self):
        if self.fade_timer.isActive():
            self.fade_timer.stop()