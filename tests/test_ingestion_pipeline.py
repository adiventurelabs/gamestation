"""
Unit and Integration Tests for Unified Offline Ingestion Pipeline.
Tests detection of non-plug-and-play discs (Xbox, Xbox 360, PS4),
background extraction pipeline, progress event streaming, cancellation,
and automated emulator launching on completion.
"""

import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import MagicMock, patch

from psconsole.disc_identifier import DiscIdentifier, DiscType, DiscInfo
from psconsole.ingestion_pipeline import IngestionPipeline, IngestionState
from psconsole.service import PSConsoleService, ServiceState
from psconsole.emulator_launcher import LaunchResult, LaunchStatus


class TestIngestionPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="psconsole_ingest_test_")
        self.mock_config = {
            "library": {
                "ps1_dir": os.path.join(self.temp_dir, "lib_ps1"),
                "ps2_dir": os.path.join(self.temp_dir, "lib_ps2"),
                "ps3_dir": os.path.join(self.temp_dir, "lib_ps3"),
                "ps4_dir": os.path.join(self.temp_dir, "lib_ps4"),
                "xbox_dir": os.path.join(self.temp_dir, "lib_xbox"),
                "xbox360_dir": os.path.join(self.temp_dir, "lib_xbox360")
            },
            "ui": {"toast_duration_seconds": 1.0}
        }
        self.identifier = DiscIdentifier()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_disc_identification_xbox_original(self):
        """Tests identification of original Xbox discs."""
        drive = os.path.join(self.temp_dir, "xbox_drive")
        os.makedirs(drive)
        with open(os.path.join(drive, "default.xbe"), "wb") as f:
            f.write(b"XBOX_EXEC")

        info = self.identifier.identify_disc(drive, volume_label="HALO_CE")
        self.assertEqual(info.disc_type, DiscType.XBOX)
        self.assertTrue(info.is_playable)
        self.assertTrue(info.requires_ingestion)

    def test_disc_identification_xbox_360(self):
        """Tests identification of Xbox 360 discs via default.xex and $SystemUpdate."""
        drive = os.path.join(self.temp_dir, "x360_drive")
        os.makedirs(os.path.join(drive, "$SystemUpdate"))
        with open(os.path.join(drive, "default.xex"), "wb") as f:
            f.write(b"X360_EXEC")

        info = self.identifier.identify_disc(drive, volume_label="HALO_3")
        self.assertEqual(info.disc_type, DiscType.XBOX360)
        self.assertTrue(info.is_playable)
        self.assertTrue(info.requires_ingestion)

    def test_disc_identification_ps4(self):
        """Tests identification of PS4 discs via eboot.bin or volume label."""
        drive = os.path.join(self.temp_dir, "ps4_drive")
        os.makedirs(drive)
        with open(os.path.join(drive, "eboot.bin"), "wb") as f:
            f.write(b"PS4_ELF")

        info = self.identifier.identify_disc(drive, volume_label="CUSA-00001")
        self.assertEqual(info.disc_type, DiscType.PS4)
        self.assertTrue(info.is_playable)
        self.assertTrue(info.requires_ingestion)

    def test_plug_and_play_discs_do_not_require_ingestion(self):
        """Ensures PS1, PS2, and PS3 physical discs bypass ingestion for direct boot."""
        ps1_info = DiscInfo(drive_path="D:\\", disc_type=DiscType.PS1, title="Crash Bandicoot")
        ps2_info = DiscInfo(drive_path="D:\\", disc_type=DiscType.PS2, title="Final Fantasy X")
        ps3_info = DiscInfo(drive_path="D:\\", disc_type=DiscType.PS3, title="Demon's Souls")

        self.assertFalse(ps1_info.requires_ingestion)
        self.assertFalse(ps2_info.requires_ingestion)
        self.assertFalse(ps3_info.requires_ingestion)

    def test_ingestion_pipeline_execution_and_callback(self):
        """Verifies full execution of IngestionPipeline including progress updates and on_complete."""
        pipeline = IngestionPipeline(self.mock_config)

        # Mock source disc folder
        src_drive = os.path.join(self.temp_dir, "mock_disc_src")
        os.makedirs(src_drive)
        with open(os.path.join(src_drive, "default.xex"), "wb") as f:
            f.write(b"MOCK_GAME_DATA_STREAM" * 50)

        disc_info = DiscInfo(
            drive_path=src_drive,
            disc_type=DiscType.XBOX360,
            title="Gears of War",
            serial="X360-12345"
        )

        completed_events = []

        def handle_complete(platform, out_path, title):
            completed_events.append((platform, out_path, title))

        # Start ingestion with 50x speed simulation for instant unit test execution
        started = pipeline.start_ingestion(disc_info, on_complete=handle_complete, simulate_speed_multiplier=50.0)
        self.assertTrue(started)
        self.assertTrue(pipeline.is_ingesting())

        # Wait for completion
        timeout = 5.0
        start = time.time()
        while pipeline.is_ingesting() and (time.time() - start < timeout):
            time.sleep(0.02)

        self.assertFalse(pipeline.is_ingesting())
        self.assertEqual(len(completed_events), 1)

        platform, out_path, title = completed_events[0]
        self.assertEqual(platform, "XBOX360")
        self.assertEqual(title, "Gears of War")
        self.assertTrue(os.path.isfile(out_path))

        state = pipeline.get_state()
        self.assertEqual(state["progress_percent"], 100)
        self.assertIn("complete", state["current_step"].lower())

    def test_ingestion_pipeline_cancellation(self):
        """Tests that a user can cleanly cancel an in-progress disc ingestion."""
        pipeline = IngestionPipeline(self.mock_config)
        disc_info = DiscInfo(drive_path=self.temp_dir, disc_type=DiscType.XBOX, title="Fable")

        completed_events = []
        pipeline.start_ingestion(disc_info, on_complete=lambda p, o, t: completed_events.append(1), simulate_speed_multiplier=0.1)

        self.assertTrue(pipeline.is_ingesting())
        time.sleep(0.05)
        pipeline.cancel()

        time.sleep(0.1)
        self.assertFalse(pipeline.is_ingesting())
        self.assertEqual(len(completed_events), 0)
        self.assertIn("cancelled", pipeline.get_state()["current_step"].lower())

    def test_service_auto_triggers_ingestion_for_xbox(self):
        """Tests PSConsoleService state machine transitions to INGESTING upon disc insertion."""
        with patch("psconsole.service.DiscDetector"), \
             patch("psconsole.service.ControllerMonitor"), \
             patch("psconsole.service.UIOverlay"), \
             patch("psconsole.service.DashboardServer"):

            service = PSConsoleService()
            service.config = self.mock_config
            service.ingestion_pipeline = IngestionPipeline(self.mock_config, logger=service.logger)

            # Mock identification returning Xbox 360
            mock_disc = DiscInfo(
                drive_path=self.temp_dir,
                disc_type=DiscType.XBOX360,
                title="Forza Motorsport 4"
            )
            service.identifier.identify_disc = MagicMock(return_value=mock_disc)
            service.launcher.launch_digital_game = MagicMock(return_value=LaunchResult(
                status=LaunchStatus.SUCCESS,
                emulator_name="Xenia",
                command=["xenia.exe"],
                process=MagicMock(pid=7788)
            ))

            # Trigger disc insertion
            service.handle_disc_inserted(self.temp_dir, "FORZA4")

            self.assertEqual(service.state, ServiceState.INGESTING)
            self.assertTrue(service.ingestion_pipeline.is_ingesting())

            # Wait for fast mock ingestion to finish
            timeout = 3.0
            t0 = time.time()
            while service.ingestion_pipeline.is_ingesting() and (time.time() - t0 < timeout):
                time.sleep(0.02)

            # Give a brief moment for callback dispatch
            time.sleep(0.05)
            self.assertEqual(service.state, ServiceState.PLAYING)
            service.launcher.launch_digital_game.assert_called_once()


if __name__ == "__main__":
    unittest.main()
