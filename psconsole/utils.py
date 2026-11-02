"""
Core utility functions for PlayStation Console Service.
Handles logging, path expansion, platform checks, and Windows API wrappers.
"""

import os
import sys
import logging
import platform
from logging.handlers import RotatingFileHandler
from typing import Optional, List, Tuple

IS_WINDOWS = sys.platform.startswith("win")


def is_windows() -> bool:
    """Check if the current host platform is Windows."""
    return IS_WINDOWS


def expand_windows_path(path: str) -> str:
    """
    Safely expand Windows environment variables like %LOCALAPPDATA%,
    converting forward/backward slashes appropriately.
    """
    if not path:
        return ""
    expanded = os.path.expandvars(path)
    if not IS_WINDOWS and "%" in expanded:
        # Fallback simulation when running on non-Windows systems (e.g. testing)
        home = os.path.expanduser("~")
        replacements = {
            "%LOCALAPPDATA%": os.path.join(home, ".local", "share"),
            "%APPDATA%": os.path.join(home, ".config"),
            "%USERPROFILE%": home,
            "%PROGRAMFILES%": "/opt/windows_apps",
            "%PROGRAMFILES(X86)%": "/opt/windows_apps_x86",
        }
        for var, sub in replacements.items():
            expanded = expanded.replace(var, sub)

    if not IS_WINDOWS:
        expanded = expanded.replace("\\", "/")

    return os.path.normpath(expanded)


def setup_logger(
    log_dir: Optional[str] = None,
    log_level: str = "INFO",
    filename: str = "psconsole.log",
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
    to_console: bool = False
) -> logging.Logger:
    """
    Configures and returns a rotating logger without cluttering standard output
    unless explicitly requested.
    """
    logger = logging.getLogger("PSConsole")
    logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
    logger.handlers.clear()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    if log_dir:
        resolved_log_dir = expand_windows_path(log_dir)
        try:
            os.makedirs(resolved_log_dir, exist_ok=True)
            log_file = os.path.join(resolved_log_dir, filename)
            file_handler = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            sys.stderr.write(f"Failed to initialize rotating file logger: {e}\n")

    if to_console or not log_dir:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger


# Windows API helpers with safe fallbacks
if IS_WINDOWS:
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    WM_CLOSE = 0x0010
    SW_RESTORE = 9

    def get_foreground_window() -> int:
        """Get HWND of current foreground window."""
        return user32.GetForegroundWindow()

    def set_foreground_window(hwnd: int) -> bool:
        """Bring window to foreground and restore if minimized."""
        if not hwnd:
            return False
        user32.ShowWindow(hwnd, SW_RESTORE)
        return bool(user32.SetForegroundWindow(hwnd))

    def close_process_windows(pid: int, timeout_seconds: float = 3.0) -> bool:
        """
        Sends WM_CLOSE cleanly to all top-level windows of a process,
        allowing emulators to cleanly save states/memory cards.
        """
        import time
        hwnds = []

        WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

        def enum_windows_callback(hwnd, lparam):
            window_pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
            if window_pid.value == pid:
                hwnds.append(hwnd)
            return True

        cb = WNDENUMPROC(enum_windows_callback)
        user32.EnumWindows(cb, 0)

        for hwnd in hwnds:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)

        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            # Check if process is still running
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            h_proc = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h_proc:
                return True
            exit_code = wintypes.DWORD()
            kernel32.GetExitCodeProcess(h_proc, ctypes.byref(exit_code))
            kernel32.CloseHandle(h_proc)
            STILL_ACTIVE = 259
            if exit_code.value != STILL_ACTIVE:
                return True
            time.sleep(0.1)

        return False

else:
    # Safe fallbacks for non-Windows platforms (e.g., during development or testing)
    def get_foreground_window() -> int:
        return 0

    def set_foreground_window(hwnd: int) -> bool:
        return False

    def close_process_windows(pid: int, timeout_seconds: float = 3.0) -> bool:
        return True
