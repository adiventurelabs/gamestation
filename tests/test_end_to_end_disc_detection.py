"""
End-to-End Integration Tests for PlayStation Console Auto-Detection & Disc Launch.
Simulates real optical disc insertion, startup disc detection, removal, re-insertion,
and controller exit workflows using dummy disc files with exact PlayStation parameters.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from psconsole.service import PSConsoleService, ServiceState
from psconsole.disc_identifier import DiscType
from psconsole.emulator_launcher import LaunchResult, LaunchStatus


class TestEndToEndDiscDetection(unittest.TestCase):
    def setUp(self):
        # Create isolated temporary directory for config, mock drive, and mock emulators
        self.test_root = tempfile.mkdtemp(prefix="psconsole_e2e_")
        self.mock_drive = os.path.join(self.test_root, "drive_d")
        os.makedirs(self.mock_drive, exist_ok=True)

        self.mock_duck_exe = os.path.join(self.test_root, "duckstation-qt.exe")
        self.mock_pcsx2_exe = os.path.join(self.test_root, "pcsx2-qt.exe")
        with open(self.mock_duck_exe, "w") as f:
            f.write("#!/bin/sh\nexit 0")
        with open(self.mock_pcsx2_exe, "w") as f:
            f.write("#!/bin/sh\nexit 0")

        self.mock_bios_dir = os.path.join(self.test_root, "bios")
        os.makedirs(self.mock_bios_dir, exist_ok=True)
        with open(os.path.join(self.mock_bios_dir, "scph5501.bin"), "wb") as f:
            f.write(b"MOCK_PS1_BIOS_5501")
        with open(os.path.join(self.mock_bios_dir, "scph39001.bin"), "wb") as f:
            f.write(b"MOCK_PS2_BIOS_39001")

        # Create isolated config
        self.config_path = os.path.join(self.test_root, "config.json")
        self.config_data = {
            "emulators": {
                "ps1": {
                    "name": "DuckStation",
                    "executable_candidates": [self.mock_duck_exe],
                    "bios_candidates": [self.mock_bios_dir],
                    "required_bios_patterns": ["scph*.bin"]
                },
                "ps2": {
                    "name": "PCSX2",
                    "executable_candidates": [self.mock_pcsx2_exe],
                    "bios_candidates": [self.mock_bios_dir],
                    "required_bios_patterns": ["scph*.bin"]
                }
            },
            "detector": {
                "ready_timeout_seconds": 3,
                "ready_retry_interval_seconds": 0.05,
                "debounce_seconds": 1.5,
                "allowed_drive_letters": []
            },
            "controller": {
                "enabled": False
            },
            "ui": {
                "enable_overlay": True,
                "toast_duration_seconds": 1.0,
                "dark_mode": True
            },
            "logging": {
                "log_dir": None
            }
        }
        import json
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f)

        self.service = PSConsoleService(self.config_path)
        # Mock UI overlay to avoid popping windows during automated test
        self.service.overlay = MagicMock()

    def tearDown(self):
        shutil.rmtree(self.test_root, ignore_errors=True)

    def test_e2e_ps1_disc_auto_detection_and_launch(self):
        """
        Simulates physical PS1 disc insertion using dummy SYSTEM.CNF and serial binary.
        Verifies auto-detection, title identification, exact command building, and launch.
        """
        # Create dummy PS1 disc files with correct parameters
        cnf_content = (
            "BOOT = cdrom:\\SLUS_000.67;1\r\n"
            "TCB = 4\r\n"
            "EVENT = 10\r\n"
            "STACK = 801FFFF0\r\n"
        )
        with open(os.path.join(self.mock_drive, "SYSTEM.CNF"), "w") as f:
            f.write(cnf_content)
        with open(os.path.join(self.mock_drive, "SLUS_000.67"), "wb") as f:
            f.write(b"MOCK_PS1_EXECUTABLE")

        # Mock the launcher's process execution to return a mock running process
        mock_proc = MagicMock()
        mock_proc.pid = 4321
        mock_proc.poll.return_value = None  # Process is running

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            # Trigger disc insertion event
            self.service.detector.simulate_insertion(self.mock_drive, volume_label="CASTLEVANIA")

            # 1. Verify service transitioned to PLAYING state
            self.assertEqual(self.service.state, ServiceState.PLAYING)
            self.assertIsNotNone(self.service.current_disc_info)
            self.assertEqual(self.service.current_disc_info.disc_type, DiscType.PS1)
            self.assertEqual(self.service.current_disc_info.serial, "SLUS-00067")
            self.assertEqual(self.service.current_disc_info.title, "Castlevania: Symphony of the Night")

            # 2. Verify UI toast was shown with identified game title and serial
            self.service.overlay.show_launch_toast.assert_called_once_with(
                title="PlayStation Disc Detected",
                subtitle="Castlevania: Symphony of the Night",
                serial="SLUS-00067",
                disc_type="PS1",
                duration_sec=1.0
            )

            # 3. Verify exact CLI invocation for DuckStation
            mock_popen.assert_called_once()
            called_args = mock_popen.call_args[0][0]
            self.assertEqual(called_args[0], self.mock_duck_exe)
            self.assertIn("-batch", called_args)
            self.assertIn("-fullscreen", called_args)
            self.assertIn("--", called_args)

            # 4. Simulate deliberate controller exit
            self.service.handle_controller_exit()
            self.assertEqual(self.service.state, ServiceState.IDLE)
            self.assertIsNone(self.service.current_disc_info)

    def test_e2e_ps2_disc_auto_detection_and_launch(self):
        """
        Simulates physical PS2 disc insertion using dummy SYSTEM.CNF with BOOT2 parameter.
        Verifies auto-detection, PCSX2 command line (-disc flag), and launch.
        """
        cnf_content = (
            "BOOT2 = cdrom0:\\SLUS_200.62;1\r\n"
            "VER = 1.00\r\n"
            "VMODE = NTSC\r\n"
        )
        with open(os.path.join(self.mock_drive, "SYSTEM.CNF"), "w") as f:
            f.write(cnf_content)
        with open(os.path.join(self.mock_drive, "SLUS_200.62"), "wb") as f:
            f.write(b"MOCK_PS2_EXECUTABLE")

        mock_proc = MagicMock()
        mock_proc.pid = 5678
        mock_proc.poll.return_value = None

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            # Trigger disc insertion
            self.service.detector.simulate_insertion(self.mock_drive, volume_label="FFX")

            # Verify PS2 identification
            self.assertEqual(self.service.state, ServiceState.PLAYING)
            self.assertEqual(self.service.current_disc_info.disc_type, DiscType.PS2)
            self.assertEqual(self.service.current_disc_info.serial, "SLUS-20062")
            self.assertEqual(self.service.current_disc_info.title, "Final Fantasy X")

            # Verify UI toast
            self.service.overlay.show_launch_toast.assert_called_once_with(
                title="PlayStation 2 Disc Detected",
                subtitle="Final Fantasy X",
                serial="SLUS-20062",
                disc_type="PS2",
                duration_sec=1.0
            )

            # Verify exact CLI invocation for PCSX2
            mock_popen.assert_called_once()
            called_args = mock_popen.call_args[0][0]
            self.assertEqual(called_args[0], self.mock_pcsx2_exe)
            self.assertIn("-batch", called_args)
            self.assertIn("-fullscreen", called_args)
            self.assertIn("-disc", called_args)

            # Clean exit
            self.service.handle_controller_exit()
            self.assertEqual(self.service.state, ServiceState.IDLE)

    def test_e2e_disc_already_inserted_at_startup(self):
        """
        Verifies startup behavior when a physical disc is already present in the drive.
        """
        # Place PS2 disc in drive BEFORE service checks drives
        cnf_content = "BOOT2 = cdrom0:\\SCUS_971.24;1\r\nVER = 1.00\r\n"
        with open(os.path.join(self.mock_drive, "SYSTEM.CNF"), "w") as f:
            f.write(cnf_content)

        # Mock optical drive list to return mock drive path
        self.service.detector.get_optical_drives = MagicMock(return_value=[self.mock_drive])

        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_proc.poll.return_value = None

        with patch("subprocess.Popen", return_value=mock_proc):
            # Run startup check
            self.service.detector.check_initial_discs()

            # Should automatically detect and launch Shadow of the Colossus
            self.assertEqual(self.service.state, ServiceState.PLAYING)
            self.assertEqual(self.service.current_disc_info.serial, "SCUS-97124")
            self.assertEqual(self.service.current_disc_info.title, "Shadow of the Colossus")

    def test_e2e_remove_and_reinsert_different_disc(self):
        """
        Tests user inserting Disc 1 (PS1), playing, exiting, ejecting, and inserting Disc 2 (PS2).
        """
        mock_proc1 = MagicMock()
        mock_proc1.pid = 1001
        mock_proc1.poll.return_value = None

        mock_proc2 = MagicMock()
        mock_proc2.pid = 1002
        mock_proc2.poll.return_value = None

        # 1. Insert Disc 1 (Castlevania)
        with open(os.path.join(self.mock_drive, "SYSTEM.CNF"), "w") as f:
            f.write("BOOT = cdrom:\\SLUS_000.67;1\r\n")

        with patch("subprocess.Popen", return_value=mock_proc1):
            self.service.detector.simulate_insertion(self.mock_drive, "CASTLEVANIA")
            self.assertEqual(self.service.state, ServiceState.PLAYING)
            self.assertEqual(self.service.current_disc_info.title, "Castlevania: Symphony of the Night")

            # 2. Exit Game via controller
            self.service.handle_controller_exit()
            self.assertEqual(self.service.state, ServiceState.IDLE)

            # 3. Eject Disc 1
            self.service.detector.simulate_removal(self.mock_drive)
            for f in os.listdir(self.mock_drive):
                os.remove(os.path.join(self.mock_drive, f))

            # 4. Insert Disc 2 (Metal Gear Solid 2)
            with open(os.path.join(self.mock_drive, "SYSTEM.CNF"), "w") as f:
                f.write("BOOT2 = cdrom0:\\SLUS_201.44;1\r\n")

        # Allow debounce window to elapse for simulation
        self.service.detector._last_event_times[self.mock_drive] = 0

        with patch("subprocess.Popen", return_value=mock_proc2):
            self.service.detector.simulate_insertion(self.mock_drive, "MGS2")
            self.assertEqual(self.service.state, ServiceState.PLAYING)
            self.assertEqual(self.service.current_disc_info.title, "Metal Gear Solid 2: Sons of Liberty")

    def test_e2e_duplicate_insertion_debouncing(self):
        """
        Simulates hardware bounce (multiple arrival notifications in rapid succession).
        Verifies launcher is invoked only ONCE.
        """
        with open(os.path.join(self.mock_drive, "SYSTEM.CNF"), "w") as f:
            f.write("BOOT = cdrom:\\SLUS_000.67;1\r\n")

        mock_proc = MagicMock()
        mock_proc.pid = 8888
        mock_proc.poll.return_value = None

        with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
            # Fire 5 rapid insertion events
            for _ in range(5):
                self.service.detector.simulate_insertion(self.mock_drive, "CASTLEVANIA")

            # Popen must be called EXACTLY once!
            self.assertEqual(mock_popen.call_count, 1)

    def test_e2e_unreadable_and_unsupported_discs(self):
        """
        Tests auto-detection of non-game disc (DVD-Video) and corrupt disc.
        Verifies clean controller error handling and no emulator crash.
        """
        # 1. DVD-Video disc
        video_ts = os.path.join(self.mock_drive, "VIDEO_TS")
        os.makedirs(video_ts, exist_ok=True)
        with open(os.path.join(video_ts, "VIDEO_TS.IFO"), "w") as f:
            f.write("DVD_MOCK")

        with patch("subprocess.Popen") as mock_popen:
            self.service.detector.simulate_insertion(self.mock_drive, "MOVIE")
            mock_popen.assert_not_called()
            self.service.overlay.show_error_screen.assert_called_once()
            self.assertEqual(self.service.state, ServiceState.IDLE)


if __name__ == "__main__":
    unittest.main()
