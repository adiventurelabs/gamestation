"""
Emulator Launcher for DuckStation (PS1), PCSX2 (PS2), RPCS3 (PS3), and shadPS4 (PS4).
Resolves emulator executables and BIOS files, builds verified command-line
arguments for physical disc playback and digital game libraries, manages subprocess
execution, and restores foreground launcher focus upon game exit.
"""

import os
import sys
import glob
import shutil
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
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.active_process: Optional[subprocess.Popen] = None
        self.active_target: Optional[str] = None
        self.active_platform: Optional[str] = None
        self.is_simulated: bool = False
        self.saved_launcher_hwnd: int = 0

    def _is_network_or_noexec_path(self, path: str) -> bool:
        """Determines if a path is on a network mount (CIFS/NFS/etc.) or has noexec on Linux."""
        if is_windows():
            return False

        if os.path.isfile(path) and not os.access(path, os.X_OK):
            return True

        if os.path.exists("/proc/mounts"):
            try:
                target_path = os.path.realpath(path)
                matching_mount = ""
                matching_opts: List[str] = []
                matching_fstype = ""

                with open("/proc/mounts", "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        parts = line.strip().split()
                        if len(parts) >= 4:
                            mount_point = parts[1]
                            fstype = parts[2].lower()
                            opts = parts[3].split(",")
                            if target_path.startswith(mount_point) and len(mount_point) > len(matching_mount):
                                matching_mount = mount_point
                                matching_opts = opts
                                matching_fstype = fstype

                if "noexec" in matching_opts:
                    return True

                network_fs = {"cifs", "smbfs", "nfs", "nfs4", "fuse.sshfs", "sshfs", "vboxsf", "vmhgfs", "afpfs"}
                if matching_fstype in network_fs:
                    return True
            except Exception:
                pass

        return False

    def _cache_executable_locally(self, src_path: str) -> str:
        """Copies an emulator binary to local user storage (~/.local/share/gamestation/emulators/)
        and marks it executable to bypass network share and noexec restrictions."""
        if is_windows() or not os.path.isfile(src_path) or src_path.lower().endswith(".exe"):
            return src_path

        local_dir = os.path.expanduser("~/.local/share/gamestation/emulators")
        try:
            os.makedirs(local_dir, exist_ok=True)
            dest_path = os.path.join(local_dir, os.path.basename(src_path))

            # Fast reuse if cached copy exists with matching file size
            if os.path.isfile(dest_path):
                try:
                    if os.path.getsize(dest_path) == os.path.getsize(src_path):
                        os.chmod(dest_path, 0o755)
                        if os.access(dest_path, os.X_OK):
                            return dest_path
                except Exception:
                    pass

            if self.logger:
                self.logger.info(f"Caching emulator binary locally: {src_path} -> {dest_path}")
            shutil.copy2(src_path, dest_path)
            os.chmod(dest_path, 0o755)
            return dest_path
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Could not cache emulator locally ({src_path} -> {local_dir}): {e}")
            return src_path

    def _ensure_local_executable(self, target: str) -> str:
        """Validates that a binary is executable on Linux/macOS.
        If the file lacks +x permissions or is hosted on a network mount or noexec
        filesystem, safely caches it to ~/.local/share/gamestation/emulators/
        and grants execution permissions."""
        if is_windows() or not os.path.isfile(target):
            return target

        if target.lower().endswith(".exe"):
            return target

        # Attempt chmod +x in place
        try:
            current_mode = os.stat(target).st_mode
            if not (current_mode & 0o111):
                os.chmod(target, current_mode | 0o755)
        except Exception:
            pass

        # If it's already executable on a local non-noexec filesystem, use directly
        if os.access(target, os.X_OK) and not self._is_network_or_noexec_path(target):
            return target

        return self._cache_executable_locally(target)

    def find_emulator_executable(self, platform_name: str) -> Optional[str]:
        """Resolves existing emulator executable path for PS1, PS2, PS3, PS4, Xbox 360, Wii U, etc."""
        key = platform_name.lower()
        emu_cfg = self.config.get("emulators", {}).get(key, {})
        candidates = emu_cfg.get("executable_candidates", [])

        # On non-Windows OS, first check if user already has a local executable in ~/.local/bin or ~/.local/share/gamestation/emulators
        if not is_windows():
            local_fast_checks = [
                os.path.expanduser(f"~/.local/bin/{key}"),
                os.path.expanduser(f"~/.local/bin/{key}_canary"),
                os.path.expanduser(f"~/.local/share/gamestation/emulators/{key}.AppImage"),
                os.path.expanduser(f"~/.local/share/gamestation/emulators/{key}_canary.AppImage"),
            ]
            for lpath in local_fast_checks:
                if os.path.isfile(lpath) and os.access(lpath, os.X_OK):
                    return lpath

            for candidate in candidates:
                resolved = expand_windows_path(candidate)
                if not os.path.isabs(resolved):
                    resolved = os.path.join(self.project_root, resolved)
                if not resolved.lower().endswith(".exe") and os.path.isfile(resolved):
                    return self._ensure_local_executable(resolved)

        # Standard candidate check
        for candidate in candidates:
            resolved = expand_windows_path(candidate)
            if not os.path.isabs(resolved):
                resolved = os.path.join(self.project_root, resolved)
            if os.path.isfile(resolved):
                if not is_windows() and not resolved.lower().endswith(".exe"):
                    return self._ensure_local_executable(resolved)
                return resolved

        # Extended candidate names for Windows and Linux
        binary_map = {
            "ps1": ["duckstation-qt.exe", "duckstation-qt", "duckstation", "DuckStation", "DuckStation-x64.AppImage", "duckstation.AppImage"],
            "ps2": ["pcsx2-qt.exe", "pcsx2.exe", "pcsx2-qt", "pcsx2", "PCSX2", "pcsx2.AppImage", "PCSX2.AppImage"],
            "ps3": ["rpcs3.exe", "rpcs3", "RPCS3", "rpcs3.AppImage", "RPCS3.AppImage"],
            "ps4": ["shadPS4.exe", "shadps4", "fpPS4.exe"],
            "xbox": ["xemu.exe", "xemu", "xemu.AppImage"],
            "xbox360": ["xenia.exe", "xenia_canary.exe", "xenia", "xenia_canary", "xenia.AppImage", "xenia_canary.AppImage", "Xenia_Canary.AppImage"],
            "wiiu": ["Cemu.exe", "cemu.exe", "cemu", "Cemu", "Cemu.AppImage", "cemu.AppImage"],
            "psp": ["PPSSPPWindows64.exe", "PPSSPP", "ppsspp"],
            "gamecube": ["Dolphin.exe", "dolphin-emu"],
            "wii": ["Dolphin.exe", "dolphin-emu"],
            "dreamcast": ["redream.exe", "redream", "flycast"],
            "n64": ["simple64-gui.exe", "simple64", "mupen64plus"],
            "snes": ["snes9x-x64.exe", "snes9x"]
        }

        search_dirs = [
            os.path.expanduser("~/.local/bin"),
            os.path.expanduser("~/Applications"),
            os.path.expanduser("~/bin"),
            "/usr/local/bin",
            "/usr/bin"
        ]
        for p in os.environ.get("PATH", "").split(os.pathsep):
            if p and p not in search_dirs:
                search_dirs.append(p)

        names = binary_map.get(key, [key])
        for sdir in search_dirs:
            if not os.path.isdir(sdir):
                continue
            for name in names:
                target = os.path.join(sdir, name)
                if os.path.isfile(target) and (os.access(target, os.X_OK) or is_windows()):
                    return target
            # Also check for wildcards like rpcs3*.AppImage, cemu*.AppImage, etc.
            try:
                for file_name in os.listdir(sdir):
                    f_lower = file_name.lower()
                    if f_lower.endswith(".appimage") and key in f_lower:
                        full_p = os.path.join(sdir, file_name)
                        if os.path.isfile(full_p) and os.access(full_p, os.X_OK):
                            return full_p
            except Exception:
                pass

        # Flatpak fallback on Linux
        if not is_windows():
            flatpak_map = {
                "ps1": "org.duckstation.DuckStation",
                "ps2": "net.pcsx2.PCSX2",
                "ps3": "net.rpcs3.RPCS3",
                "wiiu": "info.cemu.Cemu",
                "gamecube": "org.DolphinEmu.dolphin-emu",
                "wii": "org.DolphinEmu.dolphin-emu",
                "psp": "org.ppsspp.PPSSPP"
            }
            flatpak_app = flatpak_map.get(key)
            if flatpak_app and self._which("flatpak"):
                try:
                    chk = subprocess.run(["flatpak", "info", flatpak_app], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    if chk.returncode == 0:
                        return f"flatpak:{flatpak_app}"
                except Exception:
                    pass

        return None

    def verify_bios_files(self, platform_name: str) -> Tuple[bool, str]:
        """
        Verifies whether suitable BIOS/firmware files are present.
        Returns (is_found, bios_directory_checked).
        """
        key = platform_name.lower()
        if key in ("ps3", "ps4", "xbox", "xbox360", "psp", "gamecube", "wii", "dreamcast", "n64", "snes", "gba"):
            # These systems manage firmware/HLE runtime internally
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
            cmd.extend(["--no-gui", "--fullscreen", drive_root])
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
        if executable_path.startswith("flatpak:"):
            flatpak_app = executable_path.split(":", 1)[1]
            cmd = ["flatpak", "run", flatpak_app]
        else:
            cmd = [executable_path]

        if key == "ps1":
            cmd.extend(["-batch", "-fullscreen", "--", file_path])
        elif key == "ps2":
            cmd.extend(["-batch", "-fullscreen", file_path])
        elif key == "ps3":
            cmd.extend(["--no-gui", "--fullscreen", file_path])
        elif key == "ps4":
            cmd.extend(["-g", file_path])
        elif key == "xbox":
            cmd.extend(["-full-screen", "-dvd_path", file_path])
        elif key == "xbox360":
            cmd.extend(["--fullscreen", file_path])
        elif key == "psp":
            cmd.extend(["-f", file_path])
        elif key in ("gamecube", "wii"):
            cmd.extend(["-b", "-e", file_path])
        elif key == "wiiu":
            cmd.extend(["-f", "-g", file_path])
        elif key == "dreamcast":
            cmd.append(file_path)
        elif key == "n64":
            cmd.extend(["--fullscreen", file_path])
        elif key == "snes":
            cmd.extend(["-fullscreen", file_path])
        elif key == "gba":
            cmd.extend(["-f", file_path])

        return cmd

    def launch(self, disc_info: DiscInfo) -> LaunchResult:
        """Launches the appropriate emulator for the identified physical disc."""
        platform = disc_info.disc_type.value
        exe_path = self.find_emulator_executable(platform)
        emu_name = self._get_emulator_name(platform)

        if not exe_path:
            if self.config.get("allow_simulation", False):
                return self._start_simulated_session(platform, emu_name, disc_info.title)
            return LaunchResult(
                status=LaunchStatus.EMULATOR_NOT_FOUND,
                emulator_name=emu_name,
                command=[],
                error_message=f"{emu_name} executable not found in configured paths."
            )

        bios_ok, bios_dir = self.verify_bios_files(platform)
        if not bios_ok:
            if self.config.get("allow_simulation", False):
                return self._start_simulated_session(platform, emu_name, disc_info.title)
            return LaunchResult(
                status=LaunchStatus.BIOS_MISSING,
                emulator_name=emu_name,
                command=[],
                error_message=f"Missing BIOS file for {emu_name}. Please place BIOS in: {bios_dir}"
            )

        cmd = self.build_command_disc(disc_info, exe_path)
        return self._spawn_process(cmd, emu_name, target_desc=disc_info.title)

    def launch_digital_game(self, platform: str, file_path: str, title: str = "Digital Game") -> LaunchResult:
        """Launches a digital game from the library, automatically resolving absolute paths and archives."""
        # Resolve to absolute path
        abs_target = file_path
        if not os.path.isabs(abs_target):
            abs_target = os.path.join(self.project_root, abs_target)
        abs_target = os.path.normpath(abs_target)

        # Auto-extract if it's an archive (.7z or .zip)
        if abs_target.lower().endswith((".7z", ".zip")) and os.path.isfile(abs_target):
            extractor_tool = shutil.which("7zz") or shutil.which("7z")
            if extractor_tool:
                target_dir = os.path.join(self.project_root, "Library", platform.lower())
                os.makedirs(target_dir, exist_ok=True)
                if self.logger:
                    self.logger.info(f"Auto-extracting archive {abs_target} into {target_dir} before launch...")
                try:
                    subprocess.run(
                        [extractor_tool, "x", abs_target, f"-o{target_dir}", "-y"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=True
                    )
                    # Point abs_target to extracted game
                    for item in os.listdir(target_dir):
                        if item.lower().endswith((".iso", ".xex", ".pkg", ".cue", ".chd", ".rvz", ".wua", ".dec.iso")):
                            abs_target = os.path.join(target_dir, item)
                            break
                except Exception as e:
                    if self.logger:
                        self.logger.warning(f"Archive auto-extract failed: {e}")

        # Resolve PS3 folder game to EBOOT.BIN if needed
        if platform.upper() == "PS3" and os.path.isdir(abs_target):
            eboot_candidate = os.path.join(abs_target, "PS3_GAME", "USRDIR", "EBOOT.BIN")
            if os.path.isfile(eboot_candidate):
                abs_target = eboot_candidate
            else:
                for root, _, files in os.walk(abs_target):
                    if "EBOOT.BIN" in files:
                        abs_target = os.path.join(root, "EBOOT.BIN")
                        break

        if not os.path.exists(abs_target) and not self.config.get("allow_simulation", False):
            return LaunchResult(
                status=LaunchStatus.FILE_NOT_FOUND,
                emulator_name=platform,
                command=[],
                error_message=f"Game file not found at: {abs_target}"
            )

        exe_path = self.find_emulator_executable(platform)
        emu_name = self._get_emulator_name(platform)

        if not exe_path:
            if self.config.get("allow_simulation", False):
                return self._start_simulated_session(platform, emu_name, title)
            return LaunchResult(
                status=LaunchStatus.EMULATOR_NOT_FOUND,
                emulator_name=emu_name,
                command=[],
                error_message=f"{emu_name} executable not found on system. Please install {emu_name} or run Install_And_Play_Helios.bat"
            )

        cmd = self.build_command_file(platform, abs_target, exe_path)
        return self._spawn_process(cmd, emu_name, target_desc=title)

    def _start_simulated_session(self, platform: str, emu_name: str, target_desc: str) -> LaunchResult:
        if self.is_emulator_running():
            return LaunchResult(
                status=LaunchStatus.ALREADY_RUNNING,
                emulator_name=emu_name,
                command=[],
                error_message="Another game is already running."
            )
        self.is_simulated = True
        self.active_target = target_desc
        self.active_platform = platform.upper()
        if self.logger:
            self.logger.info(f"[Simulation Session] Started active gameplay for '{target_desc}' ({platform})")
        return LaunchResult(
            status=LaunchStatus.SUCCESS,
            emulator_name=emu_name,
            command=[f"simulated_{emu_name.lower()}"]
        )

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
            emu_dir = self.project_root if (cmd and cmd[0] == "flatpak") else (os.path.dirname(cmd[0]) if (cmd and os.path.isabs(cmd[0])) else self.project_root)

            env = os.environ.copy()
            env["APPIMAGE_EXTRACT_AND_RUN"] = "1"
            if not is_windows():
                local_tmp = os.path.expanduser("~/.cache/gamestation/tmp")
                os.makedirs(local_tmp, exist_ok=True)
                env["TMPDIR"] = local_tmp

            proc = subprocess.Popen(
                cmd,
                cwd=emu_dir,
                env=env,
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
        except PermissionError as pe:
            if not is_windows() and cmd and cmd[0] != "flatpak":
                if self.logger:
                    self.logger.warning(f"Permission denied launching {cmd[0]}: {pe}. Auto-recovering to local storage...")
                cached = self._cache_executable_locally(cmd[0])
                if cached and cached != cmd[0]:
                    try:
                        cmd[0] = cached
                        emu_dir = os.path.dirname(cached)
                        proc = subprocess.Popen(
                            cmd,
                            cwd=emu_dir,
                            env=env,
                            creationflags=creation_flags,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        self.active_process = proc
                        self.active_target = target_desc
                        if self.logger:
                            self.logger.info(f"Successfully launched {emu_name} via cached local executable: {cached}")
                        return LaunchResult(
                            status=LaunchStatus.SUCCESS,
                            emulator_name=emu_name,
                            command=cmd,
                            process=proc
                        )
                    except Exception as retry_err:
                        pe = retry_err
            if self.logger:
                self.logger.error(f"Failed to launch {emu_name}: {pe}")
            return LaunchResult(
                status=LaunchStatus.LAUNCH_FAILED,
                emulator_name=emu_name,
                command=cmd,
                error_message=str(pe)
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
        if self.is_simulated and self.active_target:
            return True
        if not self.active_process:
            return False
        ret = self.active_process.poll()
        if ret is not None:
            self.active_process = None
            self.active_target = None
            self.active_platform = None
            return False
        return True

    def stop_active_emulator(self) -> bool:
        """Gracefully closes active emulator via WM_CLOSE, flushes saves, and restores focus."""
        if self.is_simulated:
            self.is_simulated = False
            self.active_target = None
            self.active_platform = None
            if self.logger:
                self.logger.info("Simulated gameplay session closed.")
            return True

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
