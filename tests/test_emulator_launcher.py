"""
Tests for EmulatorLauncher command generation, path resolution, and BIOS checks
for PS1, PS2, PS3, and PS4 (physical discs and digital files).
"""

import os
import shutil
import tempfile
import unittest

from psconsole.disc_identifier import DiscInfo, DiscType
from psconsole.emulator_launcher import EmulatorLauncher, LaunchStatus


class TestEmulatorLauncher(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.mock_bios_dir = os.path.join(self.test_dir, "bios")
        os.makedirs(self.mock_bios_dir)

        # Place mock PS1 and PS2 BIOS files
        with open(os.path.join(self.mock_bios_dir, "scph5501.bin"), "wb") as f:
            f.write(b"MOCK_PS1_BIOS")
        with open(os.path.join(self.mock_bios_dir, "scph39001.bin"), "wb") as f:
            f.write(b"MOCK_PS2_BIOS")

        self.mock_config = {
            "emulators": {
                "ps1": {
                    "name": "DuckStation",
                    "executable_candidates": [os.path.join(self.test_dir, "duckstation-qt.exe")],
                    "bios_candidates": [self.mock_bios_dir],
                    "required_bios_patterns": ["scph*.bin"]
                },
                "ps2": {
                    "name": "PCSX2",
                    "executable_candidates": [os.path.join(self.test_dir, "pcsx2-qt.exe")],
                    "bios_candidates": [self.mock_bios_dir],
                    "required_bios_patterns": ["scph*.bin"]
                },
                "ps3": {
                    "name": "RPCS3",
                    "executable_candidates": [os.path.join(self.test_dir, "rpcs3.exe")]
                },
                "ps4": {
                    "name": "shadPS4",
                    "executable_candidates": [os.path.join(self.test_dir, "shadPS4.exe")]
                }
            }
        }
        self.launcher = EmulatorLauncher(self.mock_config)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_build_command_ps1_disc(self):
        disc_info = DiscInfo(
            drive_path="D:\\",
            disc_type=DiscType.PS1,
            serial="SLUS-00067"
        )
        cmd = self.launcher.build_command_disc(disc_info, "C:\\DuckStation\\duckstation-qt.exe")
        self.assertEqual(cmd, [
            "C:\\DuckStation\\duckstation-qt.exe",
            "-batch",
            "-fullscreen",
            "--",
            "D:\\"
        ])

    def test_build_command_ps2_disc(self):
        disc_info = DiscInfo(
            drive_path="E:",
            disc_type=DiscType.PS2,
            serial="SLUS-20062"
        )
        cmd = self.launcher.build_command_disc(disc_info, "C:\\PCSX2\\pcsx2-qt.exe")
        self.assertEqual(cmd, [
            "C:\\PCSX2\\pcsx2-qt.exe",
            "-batch",
            "-fullscreen",
            "-disc",
            "E:\\"
        ])

    def test_build_command_ps3_disc(self):
        disc_info = DiscInfo(
            drive_path="F:\\",
            disc_type=DiscType.PS3,
            serial="BLUS-30444"
        )
        cmd = self.launcher.build_command_disc(disc_info, "C:\\RPCS3\\rpcs3.exe")
        self.assertEqual(cmd, [
            "C:\\RPCS3\\rpcs3.exe",
            "--fullscreen",
            "F:\\"
        ])

    def test_build_command_digital_files(self):
        # PS1 digital CUE
        cmd1 = self.launcher.build_command_file("PS1", "C:\\Games\\Crash.cue", "duckstation.exe")
        self.assertEqual(cmd1, ["duckstation.exe", "-batch", "-fullscreen", "--", "C:\\Games\\Crash.cue"])

        # PS2 digital ISO
        cmd2 = self.launcher.build_command_file("PS2", "C:\\Games\\FFX.iso", "pcsx2.exe")
        self.assertEqual(cmd2, ["pcsx2.exe", "-batch", "-fullscreen", "C:\\Games\\FFX.iso"])

        # PS4 digital eboot / PKG
        cmd4 = self.launcher.build_command_file("PS4", "C:\\Games\\Bloodborne\\eboot.bin", "shadps4.exe")
        self.assertEqual(cmd4, ["shadps4.exe", "-g", "C:\\Games\\Bloodborne\\eboot.bin"])

        # PSP digital ISO / CSO
        cmd_psp = self.launcher.build_command_file("PSP", "C:\\Games\\CrisisCore.iso", "ppsspp.exe")
        self.assertEqual(cmd_psp, ["ppsspp.exe", "-f", "C:\\Games\\CrisisCore.iso"])

        # GameCube / Wii RVZ
        cmd_gc = self.launcher.build_command_file("GAMECUBE", "C:\\Games\\Melee.rvz", "dolphin.exe")
        self.assertEqual(cmd_gc, ["dolphin.exe", "-b", "-e", "C:\\Games\\Melee.rvz"])

        # Dreamcast CHD / CDI
        cmd_dc = self.launcher.build_command_file("DREAMCAST", "C:\\Games\\CrazyTaxi.chd", "redream.exe")
        self.assertEqual(cmd_dc, ["redream.exe", "C:\\Games\\CrazyTaxi.chd"])

        # GBA
        cmd_gba = self.launcher.build_command_file("GBA", "C:\\Games\\Pokemon.gba", "mgba.exe")
        self.assertEqual(cmd_gba, ["mgba.exe", "-f", "C:\\Games\\Pokemon.gba"])

    def test_verify_bios_files_present(self):
        ok_ps1, path_ps1 = self.launcher.verify_bios_files("PS1")
        self.assertTrue(ok_ps1)
        self.assertEqual(path_ps1, self.mock_bios_dir)

        ok_ps2, path_ps2 = self.launcher.verify_bios_files("PS2")
        self.assertTrue(ok_ps2)
        self.assertEqual(path_ps2, self.mock_bios_dir)

        # PS3 and PS4 return True automatically
        ok_ps3, _ = self.launcher.verify_bios_files("PS3")
        self.assertTrue(ok_ps3)
        ok_ps4, _ = self.launcher.verify_bios_files("PS4")
        self.assertTrue(ok_ps4)

    def test_verify_bios_files_missing(self):
        empty_dir = os.path.join(self.test_dir, "empty_bios")
        os.makedirs(empty_dir)
        self.launcher.config["emulators"]["ps1"]["bios_candidates"] = [empty_dir]

        ok, path = self.launcher.verify_bios_files("PS1")
        self.assertFalse(ok)

    def test_launch_missing_executable(self):
        disc_info = DiscInfo(
            drive_path="D:\\",
            disc_type=DiscType.PS1,
            serial="SLUS-00067"
        )
        result = self.launcher.launch(disc_info)
        self.assertEqual(result.status, LaunchStatus.EMULATOR_NOT_FOUND)

    def test_ensure_local_executable_handles_permissions(self):
        """Verifies that non-executable AppImages on Linux/macOS are granted execute bits or cached."""
        dummy_appimage = os.path.join(self.test_dir, "test_emu.AppImage")
        with open(dummy_appimage, "wb") as f:
            f.write(b"#!/bin/sh\necho OK\n")
        # Strip execute permissions
        os.chmod(dummy_appimage, 0o644)

        result_path = self.launcher._ensure_local_executable(dummy_appimage)
        self.assertTrue(os.path.isfile(result_path))
        self.assertTrue(os.access(result_path, os.X_OK))

    def test_cache_executable_locally(self):
        """Verifies that _cache_executable_locally copies binary and sets 0755."""
        source_bin = os.path.join(self.test_dir, "custom_xenia.AppImage")
        with open(source_bin, "wb") as f:
            f.write(b"MOCK_APPIMAGE_BINARY")
        os.chmod(source_bin, 0o600)

        cached_path = self.launcher._cache_executable_locally(source_bin)
        self.assertTrue(os.path.isfile(cached_path))
        self.assertTrue(os.access(cached_path, os.X_OK))
        # Clean up cached test file
        try:
            os.remove(cached_path)
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
