"""
Tests for LibraryScanner and Dashboard HTTP REST API.
Verifies digital game discovery, metadata extraction, and dashboard server integration.
"""

import os
import json
import time
import shutil
import tempfile
import urllib.request
import unittest
from unittest.mock import MagicMock

from psconsole.library_scanner import LibraryScanner
from psconsole.dashboard.server import DashboardServer
from psconsole.disc_identifier import DiscInfo, DiscType


class TestLibraryAndDashboard(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.lib_dir = os.path.join(self.test_dir, "library")
        os.makedirs(os.path.join(self.lib_dir, "ps1"), exist_ok=True)
        os.makedirs(os.path.join(self.lib_dir, "ps2"), exist_ok=True)
        os.makedirs(os.path.join(self.lib_dir, "ps3"), exist_ok=True)
        os.makedirs(os.path.join(self.lib_dir, "ps4"), exist_ok=True)

        # Create dummy digital game files
        with open(os.path.join(self.lib_dir, "ps1", "Crash Bandicoot.cue"), "w") as f:
            f.write("FILE \"Crash Bandicoot.bin\" BINARY\n  TRACK 01 MODE2/2352\n")
        with open(os.path.join(self.lib_dir, "ps1", "Crash Bandicoot.bin"), "wb") as f:
            f.write(b"MOCK_PS1_ISO_DATA")

        with open(os.path.join(self.lib_dir, "ps2", "Final Fantasy X.iso"), "wb") as f:
            f.write(b"MOCK_PS2_ISO_DATA")

        with open(os.path.join(self.lib_dir, "ps4", "Bloodborne.pkg"), "wb") as f:
            f.write(b"MOCK_PS4_PKG_DATA")

        self.mock_config = {
            "library": {
                "ps1_dir": os.path.join(self.lib_dir, "ps1"),
                "ps2_dir": os.path.join(self.lib_dir, "ps2"),
                "ps3_dir": os.path.join(self.lib_dir, "ps3"),
                "ps4_dir": os.path.join(self.lib_dir, "ps4")
            }
        }

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_library_scanner_discovers_games(self):
        scanner = LibraryScanner(self.mock_config)
        games = scanner.scan_all()
        platforms_found = {g.platform for g in games}

        self.assertIn("PS1", platforms_found)
        self.assertIn("PS2", platforms_found)
        self.assertIn("PS4", platforms_found)

        # Verify Crash Bandicoot (PS1)
        ps1_games = [g for g in games if g.platform == "PS1"]
        self.assertTrue(any("Crash Bandicoot" in g.title for g in ps1_games))

        # Verify Final Fantasy X (PS2)
        ps2_games = [g for g in games if g.platform == "PS2"]
        self.assertTrue(any("Final Fantasy X" in g.title for g in ps2_games))

    def test_xbox360_and_root_library_scanning(self):
        # Create xbox360 folder with ISO and companion Vimm's Lair.txt
        xbox360_dir = os.path.join(self.lib_dir, "xbox360")
        os.makedirs(xbox360_dir, exist_ok=True)
        fifa_iso = os.path.join(xbox360_dir, "FIFA 18 - Legacy Edition (USA) (En,Fr,Es).iso")
        with open(fifa_iso, "wb") as f:
            f.write(b"MOCK_FIFA_18_ISO_DATA")
        with open(os.path.join(xbox360_dir, "Vimm's Lair.txt"), "w") as f:
            f.write("This Xbox 360 media is verified by Redump.\nFIFA 18 - Legacy Edition (USA) (En,Fr,Es).iso\n")

        # Create loose PS3 folder game in root Library
        ps3_game_dir = os.path.join(self.lib_dir, "Demons_Souls")
        os.makedirs(os.path.join(ps3_game_dir, "PS3_GAME"), exist_ok=True)
        with open(os.path.join(ps3_game_dir, "PS3_DISC.SFB"), "wb") as f:
            f.write(b"SFB_MAGIC")

        cfg = {
            "library": {
                "base_dir": self.lib_dir,
                "xbox360_dir": xbox360_dir
            }
        }
        scanner = LibraryScanner(cfg)
        games = scanner.scan_all()
        titles = {g.title: g for g in games}

        self.assertIn("FIFA 18 - Legacy Edition", titles)
        self.assertEqual(titles["FIFA 18 - Legacy Edition"].platform, "XBOX360")
        self.assertEqual(titles["FIFA 18 - Legacy Edition"].format, "ISO")

        # Loose root folder game should also be detected
        self.assertTrue(any(g.platform == "PS3" and ("Demons Souls" in g.title or "Demon's Souls" in g.title) for g in games))

    def test_dashboard_server_rest_api(self):
        # Create mock service
        mock_service = MagicMock()
        mock_service.state.value = "IDLE"
        mock_service.current_disc_info = DiscInfo(
            drive_path="D:\\",
            disc_type=DiscType.PS2,
            serial="SLUS-20062",
            title="Final Fantasy X"
        )
        mock_service.launcher = MagicMock()
        mock_service.launcher.active_target = None

        server = DashboardServer(
            host="127.0.0.1",
            port=8999,
            service=mock_service,
            config=self.mock_config
        )
        server.start()
        time.sleep(0.1)

        try:
            # 1. Test GET /api/status
            req = urllib.request.Request("http://127.0.0.1:8999/api/status")
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                self.assertEqual(resp.status, 200)
                data = json.loads(resp.read().decode("utf-8"))
                self.assertTrue(data["disc"]["present"])
                self.assertEqual(data["disc"]["type"], "PS2")
                self.assertEqual(data["disc"]["title"], "Final Fantasy X")

            # 2. Test GET /api/library
            req2 = urllib.request.Request("http://127.0.0.1:8999/api/library")
            with urllib.request.urlopen(req2, timeout=2.0) as resp2:
                self.assertEqual(resp2.status, 200)
                lib_data = json.loads(resp2.read().decode("utf-8"))
                self.assertGreater(lib_data["total"], 0)

            # 3. Test POST /api/launch (Disc)
            mock_launch_res = MagicMock()
            mock_launch_res.status.value = "SUCCESS"
            mock_launch_res.error_message = None
            mock_service.launcher.launch.return_value = mock_launch_res

            req3 = urllib.request.Request(
                "http://127.0.0.1:8999/api/launch",
                data=json.dumps({"type": "disc"}).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req3, timeout=2.0) as resp3:
                self.assertEqual(resp3.status, 200)
                launch_data = json.loads(resp3.read().decode("utf-8"))
                self.assertTrue(launch_data["success"])

        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
