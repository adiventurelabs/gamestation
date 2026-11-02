"""
UI Notification Overlay.
Renders sleek, TV-safe, hardware-accelerated PlayStation Console banners and dialogs.
Supports native Windows WPF (PowerShell) for smooth 60fps animations with acrylic styling,
Tkinter fallback, and headless fallback for test suites.
"""

import os
import sys
import subprocess
import threading
from typing import Optional

from .utils import is_windows


class UIOverlay:
    """Manages console-style on-screen notifications, toasts, and error screens."""

    def __init__(self, dark_mode: bool = True, logger=None):
        self.dark_mode = dark_mode
        self.logger = logger
        self._script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._wpf_script = os.path.join(self._script_dir, "scripts", "show_overlay.ps1")

    def show_reading_toast(self, drive_path: str):
        """Displays immediate feedback as soon as disc tray closes and drive begins spin-up."""
        drive_name = drive_path.rstrip("\\/")
        self._dispatch_overlay(
            overlay_type="READING",
            title=f"Reading Disc in Drive {drive_name}...",
            subtitle="Checking PlayStation format and Table of Contents",
            duration_sec=12.0
        )

    def show_launch_toast(
        self,
        title: str,
        subtitle: str,
        serial: Optional[str] = None,
        disc_type: str = "PS1",
        duration_sec: float = 3.5
    ):
        """Displays a clean PlayStation game title card banner."""
        ov_type = "LAUNCH_PS2" if disc_type.upper() in ("PS2", "PLAYSTATION 2") else "LAUNCH_PS1"
        self._dispatch_overlay(
            overlay_type=ov_type,
            title=title,
            subtitle=subtitle,
            serial=serial or "",
            duration_sec=duration_sec
        )

    def show_error_screen(
        self,
        title: str,
        message: str,
        hint: str = "Eject disc or press (B) to continue",
        duration_sec: float = 6.0
    ):
        """Displays a clean controller-friendly error modal."""
        full_msg = f"{message} | {hint}" if hint else message
        self._dispatch_overlay(
            overlay_type="ERROR",
            title=title,
            message=full_msg,
            duration_sec=duration_sec
        )

    def close_active_overlay(self):
        """Dismisses any active overlay immediately."""
        if is_windows() and os.path.isfile(self._wpf_script):
            try:
                subprocess.Popen(
                    [
                        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                        "-File", self._wpf_script, "-Close"
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=0x00000008  # DETACHED_PROCESS
                )
            except Exception:
                pass

    def _dispatch_overlay(
        self,
        overlay_type: str,
        title: str,
        subtitle: str = "",
        serial: str = "",
        message: str = "",
        duration_sec: float = 3.5
    ):
        """Dispatches overlay to native Windows WPF or Tkinter fallback in background thread."""
        if self.logger:
            self.logger.info(f"[UI Overlay] ({overlay_type}) {title} - {subtitle or message}")

        def _worker():
            if is_windows() and os.path.isfile(self._wpf_script):
                # Use native Windows Presentation Framework for hardware-accelerated translucent UI
                cmd = [
                    "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                    "-File", self._wpf_script,
                    "-Type", overlay_type,
                    "-Title", title,
                    "-Subtitle", subtitle,
                    "-Serial", serial,
                    "-Message", message,
                    "-DurationSeconds", str(duration_sec)
                ]
                try:
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                except Exception as e:
                    if self.logger:
                        self.logger.debug(f"PowerShell WPF overlay failed: {e}; falling back to Tkinter.")

            # Cross-platform / fallback Tkinter implementation
            try:
                import tkinter as tk
                root = tk.Tk()
                root.overrideredirect(True)
                root.attributes("-topmost", True)

                bg_color = "#0A0E17"
                accent_color = "#0070D1" if "PS1" in overlay_type or "READING" in overlay_type else (
                    "#E63946" if "ERROR" in overlay_type else "#00A9E0"
                )

                screen_w = root.winfo_screenwidth()
                screen_h = root.winfo_screenheight()
                win_w = min(720, int(screen_w * 0.75))
                win_h = 135
                pos_x = (screen_w - win_w) // 2
                pos_y = screen_h - win_h - 100

                root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
                root.configure(bg=bg_color)

                frame = tk.Frame(root, bg=bg_color, padx=22, pady=16, highlightthickness=2, highlightbackground=accent_color)
                frame.pack(fill=tk.BOTH, expand=True)

                header_text = title if not serial else f"{title} [{serial}]"
                lbl_title = tk.Label(frame, text=header_text, font=("Helvetica", 17, "bold"), bg=bg_color, fg="#FFFFFF", anchor="w")
                lbl_title.pack(fill=tk.X)

                body_text = subtitle or message
                lbl_sub = tk.Label(frame, text=body_text, font=("Helvetica", 13), bg=bg_color, fg="#B0C4DE", anchor="w", pady=4)
                lbl_sub.pack(fill=tk.X)

                root.after(int(duration_sec * 1000), root.destroy)
                root.mainloop()
            except Exception:
                # Silently ignore if no display or Tk is unavailable (e.g. testing)
                pass

        t = threading.Thread(target=_worker, daemon=True, name="OverlayDispatch")
        t.start()
