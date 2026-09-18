from enum import Enum, auto
import traceback
from datetime import datetime, timedelta
import json
from PySide6.QtCore import QObject, Signal, QTimer
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
from comtypes import CLSCTX_ALL
import math
from app.backend.paths import SCHEDULER_FILE, TRANSITION_CONFIG_FILE
from pathlib import Path

# Use winotify for modern Windows 10/11 Toast Notifications
try:
    from winotify import Notification, audio
    HAS_TOASTER = True
except ImportError:
    HAS_TOASTER = False


class TransitionState(Enum):
    IDLE = auto()
    FADING = auto()
    TRANSITION_DIALOG = auto()


class WindowsVolumeManager(QObject):
    """Manages system master volume using relative step-wise plateaus."""
    
    volume_restored = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.step_timer = QTimer(self)
        self.step_timer.timeout.connect(self._step_volume_plateau)

        self.enforce_timer = QTimer(self)
        self.enforce_timer.setInterval(300)
        self.enforce_timer.timeout.connect(self._enforce_volume)
        self._enforce_target = 0.0
        self._is_enforcing = False

        self._original_volume = 1.0
        self._target_vol = 0.0
        self._current_step_index = 0
        self._plateau_steps = []
        self._is_fading = False

        self._init_audio_interface()

    def _init_audio_interface(self):
        try:
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            self.volume_interface = interface.QueryInterface(IAudioEndpointVolume)
        except Exception:
            self.volume_interface = None

    def get_current_volume(self) -> float:
        if not self.volume_interface:
            return 1.0
        try:
            return self.volume_interface.GetMasterVolumeLevelScalar()
        except Exception:
            return 1.0

    def start_zero_enforcement(self, target_vol: float = 0.0):
        if not self.volume_interface:
            return
        try:
            self._original_volume = self.get_current_volume()
            self._enforce_target = max(0.0, min(1.0, target_vol))
            self.volume_interface.SetMasterVolumeLevelScalar(self._enforce_target, None)
            self._is_enforcing = True
            self.enforce_timer.start()
        except Exception as e:
            print(f"Error starting zero enforcement: {e}")

    def stop_zero_enforcement(self):
        if self.enforce_timer.isActive():
            self.enforce_timer.stop()
        self._is_enforcing = False

    def _enforce_volume(self):
        if not self.volume_interface or not self._is_enforcing:
            self.enforce_timer.stop()
            return
        try:
            current = self.volume_interface.GetMasterVolumeLevelScalar()
            if abs(current - self._enforce_target) > 0.01:
                self.volume_interface.SetMasterVolumeLevelScalar(self._enforce_target, None)
        except Exception:
            pass

    def start_fade(self, duration_sec: int, target_vol: float = 0.0):
        if not self.volume_interface:
            return

        try:
            self._original_volume = self.get_current_volume()
            self._target_vol = max(0.0, min(1.0, target_vol))
            
            relative_percentages = [1.0, 0.75, 0.50, 0.25, 0.10, 0.0]
            scaled_steps = [self._original_volume * p for p in relative_percentages]
            
            filtered_steps = []
            for vol in scaled_steps:
                if not filtered_steps or abs(vol - filtered_steps[-1]) > 0.01:
                    if vol >= self._target_vol:
                        filtered_steps.append(vol)
                        
            if not filtered_steps or filtered_steps[-1] != self._target_vol:
                filtered_steps.append(self._target_vol)
                
            self._plateau_steps = filtered_steps
            self._current_step_index = 0
            self._is_fading = True

            num_intervals = len(self._plateau_steps)
            interval_ms = max(5000, int((duration_sec * 1000) / num_intervals))

            self.step_timer.start(interval_ms)
        except Exception as e:
            print(f"Error starting step-wise volume descent: {e}")

    def _step_volume_plateau(self):
        if not self.volume_interface or not self._is_fading:
            self.step_timer.stop()
            return

        if self._current_step_index < len(self._plateau_steps):
            next_vol = self._plateau_steps[self._current_step_index]
            self._current_step_index += 1
            try:
                self.volume_interface.SetMasterVolumeLevelScalar(next_vol, None)
            except Exception:
                pass
        
        if self._current_step_index >= len(self._plateau_steps):
            self._is_fading = False
            self.step_timer.stop()

    def cancel_fade(self):
        if self.step_timer.isActive():
            self.step_timer.stop()
        self._is_fading = False

    def finish_at_volume(self, target_volume: float):
        self.cancel_fade()
        if not self.volume_interface:
            return
        try:
            clamped_vol = max(0.0, min(1.0, target_volume))
            self.volume_interface.SetMasterVolumeLevelScalar(clamped_vol, None)
        except Exception as e:
            print(f"Error finishing fade at volume {target_volume}: {e}")

    def restore_volume(self):
        self.cancel_fade()
        self.stop_zero_enforcement()
        if not self.volume_interface:
            return
        try:
            self.volume_interface.SetMasterVolumeLevelScalar(self._original_volume, None)
            self.volume_restored.emit()
        except Exception as e:
            print(f"Error restoring volume: {e}")


class AutomatedTransitionMonitor:
    """Watches scheduler.json and handles notifications, volume fading, and dialog popups."""
    def __init__(self, transition_controller):
        self.transition_controller = transition_controller
        self.warned_sessions = set()
        self.vol_warned_sessions = set()
        self.dialog_warned_sessions = set()
        self.faded_sessions = set()
        self.triggered_dialog_sessions = set()

        self.timer = QTimer()
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.check_upcoming_sessions)
        self.timer.start()

    def send_windows_notification(self, title: str, message: str):
        if HAS_TOASTER:
            try:
                toast = Notification(
                    app_id="StudyFlow",
                    title=title,
                    msg=message,
                    duration="short",
                    icon = str(Path(__file__).resolve().parents[2] / "assets" / "icons" / "logo.ico")
                )
                toast.show()
            except Exception as e:
                print(f"Failed to trigger toast notification: {e}")

    def check_upcoming_sessions(self):
        if not SCHEDULER_FILE.exists() or not TRANSITION_CONFIG_FILE.exists():
            return

        try:
            schedule_data = json.loads(SCHEDULER_FILE.read_text(encoding="utf-8"))
            config_data = json.loads(TRANSITION_CONFIG_FILE.read_text(encoding="utf-8"))
            
            fade_start_offset_min = config_data.get("fade_start_offset_min", 7)
            fade_sec = config_data.get("fade_duration_sec", 300)
            countdown_sec = config_data.get("countdown_sec", 120)
            
            fade_lead_time = fade_start_offset_min * 60
            warning_lead_time = 10 * 60  
            vol_warning_lead_time = 7 * 60   
            
            now = datetime.now()
            sessions = schedule_data.get("sessions", [])

            for session in sessions:
                if session.get("completed") is True:
                    continue

                session_id = session.get("quest_id") or session.get("title")
                time_str = session.get("start_time")
                session_title = session.get("title", "Scheduled Session")
                
                if not time_str:
                    continue

                try:
                    today_date = now.date()
                    parsed_time = datetime.strptime(time_str, "%H:%M").time()
                    session_start = datetime.combine(today_date, parsed_time)
                except Exception:
                    continue
                
                warning_trigger_time = session_start - timedelta(seconds=warning_lead_time)
                vol_warning_trigger_time = session_start - timedelta(seconds=vol_warning_lead_time)
                dialog_warning_trigger_time = session_start - timedelta(seconds=160)
                dialog_warning_end_time = session_start - timedelta(seconds=100)
                fade_trigger_time = session_start - timedelta(seconds=fade_lead_time)
                dialog_trigger_time = session_start - timedelta(seconds=countdown_sec)

                # 1. Trigger 10-Minute Warning Notification
                if warning_trigger_time <= now < vol_warning_trigger_time and session_id not in self.warned_sessions:
                    self.warned_sessions.add(session_id)
                    self.send_windows_notification(
                        "Upcoming Session Warning", 
                        f"'{session_title}' starts in 10 minutes. Get ready to transition!"
                    )

                # 2. Trigger T - 7 Min Volume Warning Notification
                if vol_warning_trigger_time <= now < fade_trigger_time and session_id not in self.vol_warned_sessions:
                    self.vol_warned_sessions.add(session_id)
                    self.send_windows_notification(
                        "Volume Reducing Notice", 
                        f"Volume will be reducing from here onwards for '{session_title}'."
                    )

                # 3. Trigger Dialog Warning Notification
                if dialog_warning_trigger_time <= now < dialog_warning_end_time and session_id not in self.dialog_warned_sessions:
                    self.dialog_warned_sessions.add(session_id)
                    self.send_windows_notification(
                        "Transition Approaching", 
                        f"The transition dialog box is about to appear for '{session_title}'."
                    )

                # 4. Trigger Step-Wise Volume Fade at T - offset
                if fade_trigger_time <= now < dialog_trigger_time and session_id not in self.faded_sessions:
                    if self.transition_controller.state == TransitionState.IDLE:
                        if self.transition_controller.start_volume_fade_only(session, fade_sec=fade_sec):
                            self.faded_sessions.add(session_id)

                # 5. Trigger Transition Dialog at T - countdown_sec
                if dialog_trigger_time <= now < session_start and session_id not in self.triggered_dialog_sessions:
                    state = self.transition_controller.state
                    if state == TransitionState.IDLE:
                        if self.transition_controller.start_transition_sequence(session, fade_sec=fade_sec, countdown_sec=countdown_sec):
                            self.triggered_dialog_sessions.add(session_id)
                            break
                    elif state == TransitionState.FADING:
                        if self.transition_controller.trigger_dialog_popup(session):
                            self.triggered_dialog_sessions.add(session_id)
                            break
                    elif state == TransitionState.TRANSITION_DIALOG:
                        pass

        except Exception as e:
            print(f"Error checking automated scheduler triggers: {e}")


class TransitionController(QObject):
    transition_started = Signal(dict)
    show_dialog_requested = Signal(dict)
    transition_cancelled = Signal()
    transition_completed = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = TransitionState.IDLE
        self.session_data = {}
        
        self.volume_manager = WindowsVolumeManager(self)
        self.volume_manager.volume_restored.connect(lambda: print("Volume successfully restored."))

        config = self._load_config()
        self.fade_duration_sec = config.get("fade_duration_sec", 300)
        self.countdown_sec = config.get("countdown_sec", 120)

        self.auto_monitor = AutomatedTransitionMonitor(self)

    def _load_config(self) -> dict:
        if TRANSITION_CONFIG_FILE.exists():
            try:
                data = json.loads(TRANSITION_CONFIG_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except Exception:
                pass
        return {"fade_start_offset_min": 7, "fade_duration_sec": 300, "countdown_sec": 120}

    def start_volume_fade_only(self, session_payload: dict, fade_sec: int = None) -> bool:
        if self.state != TransitionState.IDLE:
            return False
        try:
            config = self._load_config()
            self.fade_duration_sec = fade_sec if fade_sec is not None else config.get("fade_duration_sec", 300)
            
            self.state = TransitionState.FADING
            self.session_data = dict(session_payload)
            self.transition_started.emit(self.session_data)

            self.volume_manager.start_fade(duration_sec=self.fade_duration_sec, target_vol=0.0)
            return True
        except Exception as e:
            traceback.print_exc()
            self.cancel_transition()
            return False

    def trigger_dialog_popup(self, session_payload: dict = None) -> bool:
        if self.state != TransitionState.FADING:
            return False
        try:
            if session_payload:
                self.session_data.update(session_payload)
            
            self.volume_manager.cancel_fade()
            self.volume_manager.finish_at_volume(0.0)
            self.volume_manager.start_zero_enforcement(0.0)

            self.state = TransitionState.TRANSITION_DIALOG
            self.show_dialog_requested.emit(self.session_data)
            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def start_transition_sequence(self, session_payload: dict, fade_sec: int = None, countdown_sec: int = None) -> bool:
        if self.state != TransitionState.IDLE:
            return False

        try:
            config = self._load_config()
            self.fade_duration_sec = fade_sec if fade_sec is not None else config.get("fade_duration_sec", 300)
            self.countdown_sec = countdown_sec if countdown_sec is not None else config.get("countdown_sec", 120)

            self.session_data = dict(session_payload)

            self.volume_manager.cancel_fade()
            self.volume_manager._original_volume = self.volume_manager.get_current_volume()
            self.volume_manager.finish_at_volume(0.0)
            self.volume_manager.start_zero_enforcement(0.0)

            self.state = TransitionState.TRANSITION_DIALOG
            self.transition_started.emit(self.session_data)
            self.show_dialog_requested.emit(self.session_data)
            return True

        except Exception as e:
            traceback.print_exc()
            self.error_occurred.emit(str(e))
            self.cancel_transition()
            return False

    def complete_transition(self, user_inputs: dict):
        if self.state not in (TransitionState.FADING, TransitionState.TRANSITION_DIALOG):
            return

        try:
            self.volume_manager.stop_zero_enforcement()
            self.volume_manager.finish_at_volume(0.15)
            
            # Ensures the original title and session metadata are never overwritten
            merged_data = dict(self.session_data)
            merged_data.update(user_inputs)
            self.session_data = merged_data
            
            self.transition_completed.emit(self.session_data)
            self.state = TransitionState.IDLE
            self.session_data = {}

        except Exception as e:
            traceback.print_exc()
            self.error_occurred.emit(str(e))
            self.cancel_transition()

    def cancel_transition(self):
        self.volume_manager.stop_zero_enforcement()
        self.volume_manager.restore_volume()
        self.state = TransitionState.IDLE
        self.session_data = {}
        self.transition_cancelled.emit()
        
    def reset_to_idle(self):
        """Resets the transition state machine back to IDLE so future sessions can trigger transitions."""
        self.volume_manager.cancel_fade()
        self.volume_manager.stop_zero_enforcement()
        self.state = TransitionState.IDLE
        self.session_data = {}