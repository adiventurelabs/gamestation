"""
Tests for PSConsoleService state transitions, debouncing, and event handling.
"""

import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from psconsole.service import PSConsoleService, ServiceState
from psconsole.disc_identifier import DiscType, DiscInfo
from psconsole.emulator_launcher import LaunchResult, LaunchStatus


class TestServiceStateMachine(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.test_dir, "config.json")
        with open(self.config_path, "w") as f:
            f.write("""{
                "detector": {"debounce_seconds": 2.0, "ready_timeout_seconds": 5},
                "controller": {"enabled": false},
                "ui": {"enable_overlay": false},
                "logging": {"log_dir": null}
            }""")

        self.service = PSConsoleService(self.config_path)
        # Mock UI overlay to avoid GUI windows during headless testing
        self.service.overlay = MagicMock()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_initial_state(self):
        self.assertEqual(self.service.state, ServiceState.IDLE)
        self.assertIsNone(self.service.current_disc_info)

    def test_ps1_launch_flow(self):
        mock_info = DiscInfo(
            drive_path="D:\\",
            disc_type=DiscType.PS1,
            serial="SLUS-00067",
            title="Castlevania: Symphony of the Night"
        )
        self.service.identifier.identify_disc = MagicMock(return_value=mock_info)

        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_res = LaunchResult(
            status=LaunchStatus.SUCCESS,
            emulator_name="DuckStation",
            command=["duckstation", "D:\\"],
            process=mock_proc
        )
        self.service.launcher.launch = MagicMock(return_value=mock_res)
        self.service.launcher.is_emulator_running = MagicMock(return_value=True)

        self.service.handle_disc_inserted("D:\\", "CASTLEVANIA")

        self.assertEqual(self.service.state, ServiceState.PLAYING)
        self.assertEqual(self.service.current_disc_info.title, "Castlevania: Symphony of the Night")
        self.service.overlay.show_launch_toast.assert_called_once()

    def test_ignore_disc_insertion_while_playing(self):
        # Setup currently playing state
        self.service.state = ServiceState.PLAYING
        self.service.launcher.is_emulator_running = MagicMock(return_value=True)
        self.service.identifier.identify_disc = MagicMock()

        self.service.handle_disc_inserted("E:\\", "ANOTHER_DISC")

        # Must NOT analyze or interrupt playing game
        self.service.identifier.identify_disc.assert_not_called()
        self.assertEqual(self.service.state, ServiceState.PLAYING)

    def test_controller_exit_returns_to_idle(self):
        self.service.state = ServiceState.PLAYING
        self.service.launcher.stop_active_emulator = MagicMock()

        self.service.handle_controller_exit()

        self.service.launcher.stop_active_emulator.assert_called_once()
        self.assertEqual(self.service.state, ServiceState.IDLE)
        self.assertIsNone(self.service.current_disc_info)

    def test_unsupported_disc_handling(self):
        mock_info = DiscInfo(
            drive_path="D:\\",
            disc_type=DiscType.UNSUPPORTED_MEDIA,
            title="DVD-Video Movie",
            error_message="DVD-Video movie inserted."
        )
        self.service.identifier.identify_disc = MagicMock(return_value=mock_info)
        self.service.launcher.launch = MagicMock()

        self.service.handle_disc_inserted("D:\\", "MOVIE")

        self.service.launcher.launch.assert_not_called()
        self.service.overlay.show_error_screen.assert_called_once()
        self.assertEqual(self.service.state, ServiceState.IDLE)

    def test_unreadable_disc_handling(self):
        mock_info = DiscInfo(
            drive_path="D:\\",
            disc_type=DiscType.UNREADABLE,
            title="Disc Read Error",
            error_message="I/O error reading disc."
        )
        self.service.identifier.identify_disc = MagicMock(return_value=mock_info)
        self.service.launcher.launch = MagicMock()

        self.service.handle_disc_inserted("D:\\", "BAD_DISC")

        self.service.launcher.launch.assert_not_called()
        self.service.overlay.show_error_screen.assert_called_once()
        self.assertEqual(self.service.state, ServiceState.IDLE)

    def test_bios_missing_handling(self):
        mock_info = DiscInfo(
            drive_path="D:\\",
            disc_type=DiscType.PS1,
            serial="SLUS-00067",
            title="Castlevania"
        )
        self.service.identifier.identify_disc = MagicMock(return_value=mock_info)
        mock_res = LaunchResult(
            status=LaunchStatus.BIOS_MISSING,
            emulator_name="DuckStation",
            command=[],
            error_message="Missing BIOS"
        )
        self.service.launcher.launch = MagicMock(return_value=mock_res)

        self.service.handle_disc_inserted("D:\\", "CASTLEVANIA")

        self.service.overlay.show_error_screen.assert_called_once()
        self.assertEqual(self.service.state, ServiceState.IDLE)


if __name__ == "__main__":
    unittest.main()
