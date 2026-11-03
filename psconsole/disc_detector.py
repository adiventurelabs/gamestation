"""
Windows Optical Disc Detector.
Uses Win32 device arrival notifications (WM_DEVICECHANGE) for event-driven,
zero-polling disc detection, with bounded retries for optical drive spin-up.
"""

import os
import sys
import time
import threading
from typing import Callable, Optional, List, Tuple, Dict, Any

from .utils import is_windows


# Win32 Constants
WM_DEVICECHANGE = 0x0219
DBT_DEVICEARRIVAL = 0x8000
DBT_DEVICEREMOVECOMPLETE = 0x8004
DBT_DEVTYP_VOLUME = 0x00000002
DBTF_MEDIA = 0x0001
DRIVE_CDROM = 5


if is_windows():
    import ctypes
    from ctypes import wintypes
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32

    class DEV_BROADCAST_HDR(ctypes.Structure):
        _fields_ = [
            ("dbch_size", wintypes.DWORD),
            ("dbch_devicetype", wintypes.DWORD),
            ("dbch_reserved", wintypes.DWORD),
        ]

    class DEV_BROADCAST_VOLUME(ctypes.Structure):
        _fields_ = [
            ("dbcv_size", wintypes.DWORD),
            ("dbcv_devicetype", wintypes.DWORD),
            ("dbcv_reserved", wintypes.DWORD),
            ("dbcv_unitmask", wintypes.DWORD),
            ("dbcv_flags", wintypes.WORD),
        ]
else:
    kernel32 = None
    user32 = None


class DiscDetector:
    """Detects optical disc insertion and removal events without aggressive polling."""

    def __init__(
        self,
        config: Dict[str, Any],
        on_disc_inserted: Optional[Callable[[str, Optional[str]], None]] = None,
        on_disc_removed: Optional[Callable[[str], None]] = None,
        on_disc_arriving: Optional[Callable[[str], None]] = None,
        logger=None
    ):
        self.config = config
        det_cfg = config.get("detector", {})
        self.ready_timeout = det_cfg.get("ready_timeout_seconds", 15)
        self.retry_interval = det_cfg.get("ready_retry_interval_seconds", 1.0)
        self.debounce_sec = det_cfg.get("debounce_seconds", 3.0)
        self.allowed_drives = det_cfg.get("allowed_drive_letters", [])

        self.on_disc_inserted = on_disc_inserted
        self.on_disc_removed = on_disc_removed
        self.on_disc_arriving = on_disc_arriving
        self.logger = logger

        self._running = False
        self._stop_requested = False
        self._thread: Optional[threading.Thread] = None
        self._hwnd: int = 0
        self._last_event_times: Dict[str, float] = {}

    def get_optical_drives(self) -> List[str]:
        """Returns list of drive roots for all connected CD/DVD/Blu-ray optical drives."""
        drives = []
        if is_windows() and kernel32:
            for letter_code in range(ord('A'), ord('Z') + 1):
                drive_letter = chr(letter_code)
                root = f"{drive_letter}:\\"
                if kernel32.GetDriveTypeW(root) == DRIVE_CDROM:
                    if not self.allowed_drives or drive_letter in self.allowed_drives:
                        drives.append(root)
        return drives

    def wait_until_ready(self, drive_path: str) -> Tuple[bool, Optional[str]]:
        """
        Polls drive with bounded retries while the disc spins up and TOC is read.
        Returns (is_ready, volume_label).
        """
        start = time.time()
        attempt = 1

        while time.time() - start < self.ready_timeout:
            if self._stop_requested:
                return False, None

            # Attempt to read volume info or directory
            try:
                if is_windows() and kernel32:
                    vol_name = ctypes.create_unicode_buffer(261)
                    fs_name = ctypes.create_unicode_buffer(261)
                    serial_num = wintypes.DWORD()
                    max_len = wintypes.DWORD()
                    flags = wintypes.DWORD()

                    res = kernel32.GetVolumeInformationW(
                        drive_path,
                        vol_name, 260,
                        ctypes.byref(serial_num),
                        ctypes.byref(max_len),
                        ctypes.byref(flags),
                        fs_name, 260
                    )
                    if res != 0:
                        # Drive is ready and mounted
                        label = vol_name.value
                        if self.logger:
                            self.logger.info(f"Drive {drive_path} became ready after {attempt} attempts (label: {label})")
                        return True, label

                # Fallback: check filesystem access
                if os.path.exists(drive_path):
                    # Try listing root
                    entries = os.listdir(drive_path)
                    if entries:
                        if self.logger:
                            self.logger.info(f"Drive {drive_path} filesystem readable with {len(entries)} entries")
                        return True, None

            except (PermissionError, OSError):
                pass

            time.sleep(self.retry_interval)
            attempt += 1

        if self.logger:
            self.logger.warning(f"Drive {drive_path} did not become ready within {self.ready_timeout}s timeout")
        return False, None

    def start(self):
        """Starts the event listener thread."""
        if self._running:
            return
        self._running = True
        self._stop_requested = False

        if is_windows():
            self._thread = threading.Thread(target=self._win32_message_loop, daemon=True, name="DiscDetectorThread")
            self._thread.start()
        else:
            if self.logger:
                self.logger.info("DiscDetector running in non-Windows mode (manual/mock event injection available).")

    def stop(self):
        """Stops the event listener and tears down hidden message window."""
        self._running = False
        self._stop_requested = True
        if is_windows() and user32 and self._hwnd:
            WM_QUIT = 0x0012
            user32.PostMessageW(self._hwnd, WM_QUIT, 0, 0)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None

    def check_initial_discs(self):
        """
        Scans optical drives at startup. If a disc is already inserted,
        triggers the insertion callback.
        """
        drives = self.get_optical_drives()
        if self.logger:
            self.logger.info(f"Checking optical drives at startup: {drives}")

        for drive in drives:
            try:
                if os.path.exists(drive):
                    entries = os.listdir(drive)
                    if entries:
                        if self.logger:
                            self.logger.info(f"Detected disc already present at startup in {drive}")
                        ready, label = self.wait_until_ready(drive)
                        if ready and self.on_disc_inserted:
                            self.on_disc_inserted(drive, label)
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Optical drive {drive} not ready at startup: {e}")

    def simulate_insertion(self, drive_path: str, volume_label: Optional[str] = None):
        """Used for testing and mock environments."""
        now = time.time()
        last = self._last_event_times.get(drive_path, 0)
        if now - last < self.debounce_sec:
            if self.logger:
                self.logger.info(f"Debounced duplicate insertion for {drive_path}")
            return
        self._last_event_times[drive_path] = now

        if self.on_disc_arriving:
            self.on_disc_arriving(drive_path)

        ready, label = self.wait_until_ready(drive_path)
        if ready and self.on_disc_inserted:
            self.on_disc_inserted(drive_path, label or volume_label)

    def simulate_removal(self, drive_path: str):
        """Used for testing and mock environments."""
        if self.on_disc_removed:
            self.on_disc_removed(drive_path)

    def _win32_message_loop(self):
        """Runs a message-only hidden Win32 window to capture WM_DEVICECHANGE."""
        try:
            WNDPROCTYPE = ctypes.WINFUNCTYPE(ctypes.c_long, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

            def wndproc(hwnd, msg, wparam, lparam):
                if msg == WM_DEVICECHANGE:
                    self._handle_device_change(wparam, lparam)
                    return 1
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            self._wndproc = WNDPROCTYPE(wndproc)

            HCURSOR = getattr(wintypes, "HCURSOR", getattr(wintypes, "HANDLE", ctypes.c_void_p))
            HBRUSH = getattr(wintypes, "HBRUSH", getattr(wintypes, "HANDLE", ctypes.c_void_p))
            HICON = getattr(wintypes, "HICON", getattr(wintypes, "HANDLE", ctypes.c_void_p))

            class WNDCLASS(ctypes.Structure):
                _fields_ = [
                    ("style", wintypes.UINT),
                    ("lpfnWndProc", WNDPROCTYPE),
                    ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HINSTANCE),
                    ("hIcon", HICON),
                    ("hCursor", HCURSOR),
                    ("hbrBackground", HBRUSH),
                    ("lpszMenuName", wintypes.LPCWSTR),
                    ("lpszClassName", wintypes.LPCWSTR),
                ]

            cls = WNDCLASS()
            cls_name = "PSConsoleDiscWatcher"
            cls.lpszClassName = cls_name
            cls.lpfnWndProc = self._wndproc
            cls.hInstance = kernel32.GetModuleHandleW(None)

            user32.RegisterClassW(ctypes.byref(cls))

            HWND_MESSAGE = -3
            self._hwnd = user32.CreateWindowExW(
                0, cls_name, cls_name, 0, 0, 0, 0, 0,
                HWND_MESSAGE, 0, cls.hInstance, 0
            )

            if not self._hwnd:
                if self.logger:
                    self.logger.warning("Failed to create hidden Win32 message window for disc detection. Drive polling remains active.")
                return

            if self.logger:
                self.logger.info("Win32 device change notification window created successfully.")

            msg = wintypes.MSG()
            while self._running:
                b_ret = user32.GetMessageW(ctypes.byref(msg), self._hwnd, 0, 0)
                if b_ret <= 0:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Win32 disc notification loop encountered error: {e}. Media polling remains active.")

    def _handle_device_change(self, wparam: int, lparam: int):
        """Processes WM_DEVICECHANGE parameters for optical media events."""
        if not lparam:
            return

        hdr = ctypes.cast(lparam, ctypes.POINTER(DEV_BROADCAST_HDR)).contents
        if hdr.dbch_devicetype != DBT_DEVTYP_VOLUME:
            return

        vol = ctypes.cast(lparam, ctypes.POINTER(DEV_BROADCAST_VOLUME)).contents

        # Only process media events (disc tray load/unload), not USB drive plug/unplug
        if not (vol.dbcv_flags & DBTF_MEDIA):
            return

        unitmask = vol.dbcv_unitmask
        # Find which drive letter matched
        drive_letter = None
        for i in range(26):
            if unitmask & (1 << i):
                drive_letter = chr(ord('A') + i)
                break

        if not drive_letter:
            return

        drive_root = f"{drive_letter}:\\"

        # Verify it's an optical drive
        if kernel32.GetDriveTypeW(drive_root) != DRIVE_CDROM:
            return

        if self.allowed_drives and drive_letter not in self.allowed_drives:
            return

        now = time.time()
        last = self._last_event_times.get(drive_root, 0)

        if wparam == DBT_DEVICEARRIVAL:
            if now - last < self.debounce_sec:
                if self.logger:
                    self.logger.info(f"Ignoring duplicate/bounced arrival event on {drive_root}")
                return
            self._last_event_times[drive_root] = now

            if self.logger:
                self.logger.info(f"Optical disc arrival detected on {drive_root}. Waiting for ready state...")

            if self.on_disc_arriving:
                self.on_disc_arriving(drive_root)

            # Run ready wait in a separate thread to avoid blocking the Win32 message pump
            def _async_ready_worker():
                ready, label = self.wait_until_ready(drive_root)
                if ready:
                    if self.on_disc_inserted:
                        self.on_disc_inserted(drive_root, label)
                else:
                    if self.logger:
                        self.logger.warning(f"Disc inserted in {drive_root} but was unreadable or timed out.")

            t = threading.Thread(target=_async_ready_worker, daemon=True, name=f"ReadyWait-{drive_letter}")
            t.start()

        elif wparam == DBT_DEVICEREMOVECOMPLETE:
            self._last_event_times[drive_root] = now
            if self.logger:
                self.logger.info(f"Optical disc removal detected on {drive_root}")
            if self.on_disc_removed:
                self.on_disc_removed(drive_root)
