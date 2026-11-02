"""
Controller Monitor for Exit Shortcut.
Polls game controllers via XInput in a background thread to detect
deliberate button hold combinations (e.g., Select + Start held for 1.8s)
without interfering with game controls.
"""

import time
import ctypes
import threading
from typing import Callable, Optional, Dict, Any
from .utils import is_windows


# XInput button masks
XINPUT_GAMEPAD_DPAD_UP = 0x0001
XINPUT_GAMEPAD_DPAD_DOWN = 0x0002
XINPUT_GAMEPAD_DPAD_LEFT = 0x0004
XINPUT_GAMEPAD_DPAD_RIGHT = 0x0008
XINPUT_GAMEPAD_START = 0x0010
XINPUT_GAMEPAD_BACK = 0x0020  # Select / Back / View
XINPUT_GAMEPAD_LEFT_THUMB = 0x0040  # L3
XINPUT_GAMEPAD_RIGHT_THUMB = 0x0080  # R3
XINPUT_GAMEPAD_LEFT_SHOULDER = 0x0100
XINPUT_GAMEPAD_RIGHT_SHOULDER = 0x0200
XINPUT_GAMEPAD_A = 0x1000
XINPUT_GAMEPAD_B = 0x2000
XINPUT_GAMEPAD_X = 0x4000
XINPUT_GAMEPAD_Y = 0x8000


if is_windows():
    # Define XInput C structures
    class XINPUT_GAMEPAD(ctypes.Structure):
        _fields_ = [
            ("wButtons", ctypes.c_ushort),
            ("bLeftTrigger", ctypes.c_ubyte),
            ("bRightTrigger", ctypes.c_ubyte),
            ("sThumbLX", ctypes.c_short),
            ("sThumbLY", ctypes.c_short),
            ("sThumbRX", ctypes.c_short),
            ("sThumbRY", ctypes.c_short),
        ]

    class XINPUT_STATE(ctypes.Structure):
        _fields_ = [
            ("dwPacketNumber", ctypes.c_ulong),
            ("Gamepad", XINPUT_GAMEPAD),
        ]

    # Try loading xinput DLLs in priority order
    _xinput_dll = None
    for dll_name in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
        try:
            _xinput_dll = ctypes.windll.LoadLibrary(dll_name)
            break
        except Exception:
            continue

    if _xinput_dll:
        _XInputGetState = _xinput_dll.XInputGetState
        _XInputGetState.argtypes = [ctypes.c_ulong, ctypes.POINTER(XINPUT_STATE)]
        _XInputGetState.restype = ctypes.c_ulong
    else:
        _XInputGetState = None
else:
    _XInputGetState = None


class ControllerMonitor:
    """Monitors XInput controllers for long-press exit shortcuts."""

    def __init__(
        self,
        config: Dict[str, Any],
        on_exit_requested: Optional[Callable[[], None]] = None,
        logger=None
    ):
        ctrl_cfg = config.get("controller", {})
        self.enabled = ctrl_cfg.get("enabled", True)
        self.shortcut = ctrl_cfg.get("shortcut", "SELECT_START").upper()
        self.hold_time_seconds = ctrl_cfg.get("hold_time_seconds", 1.8)
        self.poll_interval = ctrl_cfg.get("poll_interval_seconds", 0.05)
        self.on_exit_requested = on_exit_requested
        self.logger = logger

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._hold_start_times: Dict[int, float] = {}
        self._has_triggered: Dict[int, bool] = {}

    def _get_target_mask(self) -> int:
        """Translates shortcut configuration name to XInput button bitmask."""
        if self.shortcut == "L3_R3":
            return XINPUT_GAMEPAD_LEFT_THUMB | XINPUT_GAMEPAD_RIGHT_THUMB
        # Default: SELECT + START
        return XINPUT_GAMEPAD_BACK | XINPUT_GAMEPAD_START

    def start(self):
        """Starts background controller polling thread."""
        if not self.enabled or self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="ControllerMonitor")
        self._thread.start()
        if self.logger:
            self.logger.info(f"Controller exit monitor started (shortcut: {self.shortcut}, hold: {self.hold_time_seconds}s)")

    def stop(self):
        """Stops background thread."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _poll_loop(self):
        target_mask = self._get_target_mask()

        while self._running:
            if not _XInputGetState:
                time.sleep(1.0)
                continue

            for user_index in range(4):  # Check controllers 0-3
                state = XINPUT_STATE()
                res = _XInputGetState(user_index, ctypes.byref(state))
                if res != 0:  # ERROR_DEVICE_NOT_CONNECTED = 1167
                    self._hold_start_times.pop(user_index, None)
                    self._has_triggered.pop(user_index, None)
                    continue

                buttons = state.Gamepad.wButtons
                is_combo_down = (buttons & target_mask) == target_mask

                now = time.time()
                if is_combo_down:
                    if user_index not in self._hold_start_times:
                        self._hold_start_times[user_index] = now
                    else:
                        elapsed = now - self._hold_start_times[user_index]
                        if elapsed >= self.hold_time_seconds and not self._has_triggered.get(user_index, False):
                            self._has_triggered[user_index] = True
                            if self.logger:
                                self.logger.info(f"Controller {user_index} triggered deliberate exit shortcut!")
                            if self.on_exit_requested:
                                self.on_exit_requested()
                else:
                    self._hold_start_times.pop(user_index, None)
                    self._has_triggered[user_index] = False

            time.sleep(self.poll_interval)
