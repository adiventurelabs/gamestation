"""
Emulator Launcher for DuckStation (PS1), PCSX2 (PS2), RPCS3 (PS3), and shadPS4 (PS4).
Resolves emulator executables and BIOS files, builds verified command-line
arguments for physical disc playback and digital game libraries, manages subprocess
execution, and restores foreground launcher focus upon game exit.
"""

import os
import sys
import glob
import subprocess
from enum import Enum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple

from .disc_identifier import DiscType, DiscInfo
from .utils import expand_windows_path, get_foreground_window, set_foreground_window, close_process_windows, is_windows


class LaunchStatus(Enum):
    SUCCESS = "SUCCESS"
    EMULATOR_NOT_FOUND = "EMULATOR_NOT_FOUND"
    BIOS_MISSING = "BIOS_MISSING"
    LAUNCH_FAILED = "LAUNCH_FAILED"
    ALREADY_RUNNING = "ALREADY_RUNNING"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"


@dataclass
class LaunchResult:
    status: LaunchStatus
    emulator_name: str
    command: List[str]
    process: Optional[subprocess.Popen] = None
    error_message: Optional[str] = None


class EmulatorLauncher:
    """Manages emulator detection, launch arguments, and process lifecycle."""

    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger
        self.active_process: Optional[subprocess.Popen] = None
        self.active_target: Optional[str] = None
        self.saved_launcher_hwnd: int = 0

    def find_emulator_executable(self, platform_name: str) -> Optional[str]:
        """Resolves existing emulator executable path for PS1, PS2, PS3, or PS4."""
        key = platform_name.lower()
        emu_cfg = self.config.get("emulators", {}).get(key, {})
        candidates = emu_cfg.get("executable_candidates", [])

        for candidate in candidates:
            resolved = expand_windows_path(candidate)
            if os.path.isfile(resolved):
                return resolved

        # Check PATH if candidate wasn't found directly
        binary_map = {
            "ps1": ["duckstation-qt.exe", "duckstation-qt"],
            "ps2": ["pcsx2-qt.exe", "pcsx2.exe", "pcsx2-qt"],
            "ps3": ["rpcs3.exe", "rpcs3"],
            "ps4": ["shadPS4.exe", "shadps4", "fpPS4.exe"],
            "xbox": ["xemu.exe", "xemu"],
            "xbox360": ["xenia.exe", "xenia_canary.exe", "xenia"]
        }
        for b_name in binary_map.get(key, []):
            found = self._which(b_name)
            if found:
                return found

        return None

    def verify_bios_files(self, platform_name: str) -> Tuple[bool, str]:
        """
        Verifies whether suitable BIOS/firmware files are present.
        Returns (is_found, bios_directory_checked).
        """
        key = platform_name.lower()
        if key in ("ps3", "ps4", "xbox", "xbox360"):
            # PS3, PS4, Xbox, and Xbox360 manage firmware/runtime internally
            return True, "firmware"

        emu_cfg = self.config.get("emulators", {}).get(key, {})
        bios_candidates = emu_cfg.get("bios_candidates", [])
        patterns = emu_cfg.get("required_bios_patterns", ["*.bin", "*.BIN"])

        first_dir = None
        for dir_candidate in bios_candidates:
            resolved_dir = expand_windows_path(dir_candidate)
            if not first_dir:
                first_dir = resolved_dir
            if os.path.isdir(resolved_dir):
                for pattern in patterns:
                    matches = glob.glob(os.path.join(resolved_dir, pattern))
                    if matches:
                        return True, resolved_dir

        return False, first_dir or "bios"

    def build_command_disc(self, disc_info: DiscInfo, executable_path: str) -> List[str]:
        """
        Builds command line arguments for physical optical disc launch.
        """
        drive_path = disc_info.drive_path.rstrip("\\/")
        drive_letter = drive_path if drive_path.endswith(":") else drive_path[:2]
        drive_root = f"{drive_letter}\\"

        key = disc_info.disc_type.value.lower()
        cmd = [executable_path]

        if disc_info.disc_type == DiscType.PS1:
            cmd.extend(["-batch", "-fullscreen", "--", drive_root])
        elif disc_info.disc_type == DiscType.PS2:
            cmd.extend(["-batch", "-fullscreen", "-disc", drive_root])
        elif disc_info.disc_type == DiscType.PS3:
            cmd.extend(["--fullscreen", drive_root])
        elif disc_info.disc_type == DiscType.PS4:
            cmd.extend(["-g", drive_root])
        elif disc_info.disc_type == DiscType.XBOX:
            cmd.extend(["-full-screen", "-dvd_path", drive_root])
        elif disc_info.disc_type == DiscType.XBOX360:
            cmd.extend(["--fullscreen", drive_root])

        return cmd

    def build_command_file(self, platform: str, file_path: str, executable_path: str) -> List[str]:
        """
        Builds command line arguments for digital game launch from file/folder.
        """
        key = platform.lower()
        cmd = [executable_path]

        if key == "ps1":
            cmd.extend(["-batch", "-fullscreen", "--", file_path])
        elif key == "ps2":
            cmd.extend(["-batch", "-fullscreen", file_path])
        elif key == "ps3":
            cmd.extend(["--fullscreen", file_path])
        elif key == "ps4":
            cmd.extend(["-g", file_path])
        elif key == "xbox":
            cmd.extend(["-full-screen", "-dvd_path", file_path])
        elif key == "xbox360":
            cmd.extend(["--fullscreen", file_path])

        return cmd

    def launch(self, disc_info: DiscInfo) -> LaunchResult:
        """Launches the appropriate emulator for the identified physical disc."""
        platform = disc_info.disc_type.value
        exe_path = self.find_emulator_executable(platform)
        emu_name = self._get_emulator_name(platform)

        if not exe_path:
            return LaunchResult(
                status=LaunchStatus.EMULATOR_NOT_FOUND,
                emulator_name=emu_name,
                command=[],
                error_message=f"{emu_name} executable not found in configured paths."
            )

        bios_ok, bios_dir = self.verify_bios_files(platform)
        if not bios_ok:
            return LaunchResult(
                status=LaunchStatus.BIOS_MISSING,
                emulator_name=emu_name,
                command=[],
                error_message=f"Missing BIOS file for {emu_name}. Please place BIOS in: {bios_dir}"
            )

        cmd = self.build_command_disc(disc_info, exe_path)
        return self._spawn_process(cmd, emu_name, target_desc=disc_info.title)

    def launch_digital_game(self, platform: str, file_path: str, title: str = "Digital Game") -> LaunchResult:
        """Launches a digital game from the library."""
        if not os.path.exists(file_path):
            return LaunchResult(
                status=LaunchStatus.FILE_NOT_FOUND,
                emulator_name=platform,
                command=[],
                error_message=f"Game file not found at: {file_path}"
            )

        exe_path = self.find_emulator_executable(platform)
        emu_name = self._get_emulator_name(platform)

        if not exe_path:
            return LaunchResult(
                status=LaunchStatus.EMULATOR_NOT_FOUND,
                emulator_name=emu_name,
                command=[],
                error_message=f"{emu_name} executable not found."
            )

        cmd = self.build_command_file(platform, file_path, exe_path)
        return self._spawn_process(cmd, emu_name, target_desc=title)

    def _spawn_process(self, cmd: List[str], emu_name: str, target_desc: str) -> LaunchResult:
        if self.is_emulator_running():
            return LaunchResult(
                status=LaunchStatus.ALREADY_RUNNING,
                emulator_name=emu_name,
                command=[],
                error_message="Another game is already running."
            )

        self.saved_launcher_hwnd = get_foreground_window()
        if self.logger:
            self.logger.info(f"Launching {emu_name} for '{target_desc}' with command: {' '.join(cmd)}")

        try:
            creation_flags = 0x00000008 if is_windows() else 0  # DETACHED_PROCESS

            proc = subprocess.Popen(
                cmd,
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.active_process = proc
            self.active_target = target_desc

            return LaunchResult(
                status=LaunchStatus.SUCCESS,
                emulator_name=emu_name,
                command=cmd,
                process=proc
            )
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to launch {emu_name}: {e}")
            return LaunchResult(
                status=LaunchStatus.LAUNCH_FAILED,
                emulator_name=emu_name,
                command=cmd,
                error_message=str(e)
            )

    def is_emulator_running(self) -> bool:
        """Checks whether the currently managed emulator process is still active."""
        if not self.active_process:
            return False
        ret = self.active_process.poll()
        if ret is not None:
            self.active_process = None
            self.active_target = None
            return False
        return True

    def stop_active_emulator(self) -> bool:
        """Gracefully closes active emulator via WM_CLOSE, flushes saves, and restores focus."""
        if not self.active_process:
            return True

        pid = self.active_process.pid
        if self.logger:
            self.logger.info(f"Requesting clean exit for emulator PID: {pid}")

        closed_cleanly = close_process_windows(pid, timeout_seconds=4.0)

        if self.active_process.poll() is None:
            if not closed_cleanly:
                try:
                    self.active_process.terminate()
                    self.active_process.wait(timeout=2.0)
                except Exception:
                    try:
                        self.active_process.kill()
                    except Exception:
                        pass

        self.active_process = None
        self.active_target = None
        self.restore_launcher_focus()
        return True

    def restore_launcher_focus(self):
        """Restores focus to the saved launcher window."""
        if self.saved_launcher_hwnd:
            if self.logger:
                self.logger.info(f"Restoring focus to launcher HWND: {self.saved_launcher_hwnd}")
            set_foreground_window(self.saved_launcher_hwnd)

    def _get_emulator_name(self, platform: str) -> str:
        key = platform.lower()
        return self.config.get("emulators", {}).get(key, {}).get("name", platform.upper())

    def _which(self, program: str) -> Optional[str]:
        path = os.environ.get("PATH", "")
        for p in path.split(os.pathsep):
            candidate = os.path.join(p, program)
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None
