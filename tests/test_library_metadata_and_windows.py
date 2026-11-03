"""
Tests for GameStation rich metadata resolution, PS3 .dec.iso format detection,
and Windows emulator command line generation.
"""

import unittest
import os
import json
import tempfile
from psconsole.library_scanner import LibraryScanner
from psconsole.game_metadata import GameMetadataManager, KNOWN_METADATA
from psconsole.emulator_launcher import EmulatorLauncher
from psconsole.utils import expand_windows_path


class TestLibraryMetadataAndWindows(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = {
            "library": {
                "base_dir": self.temp_dir.name
            },
            "allow_simulation": True,
            "emulators": {
                "ps3": {
                    "name": "RPCS3",
                    "executable_candidates": ["%LOCALAPPDATA%\\Programs\\RPCS3\\rpcs3.exe"],
                    "cli_args_file": ["--no-gui", "--fullscreen", "{target}"]
                },
                "xbox360": {
                    "name": "Xenia",
                    "executable_candidates": ["%LOCALAPPDATA%\\Programs\\xenia\\xenia.exe"],
                    "cli_args_file": ["--fullscreen", "{target}"]
                }
            }
        }
        self.scanner = LibraryScanner(self.config)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_clean_title_dec_iso(self):
        """Tests that .dec suffix from Redump/Vimm's Lair PS3 dumps is cleaned cleanly."""
        raw_stem = "Assassin's Creed IV - Black Flag (USA) (En,Fr,Es,Pt).dec"
        cleaned = self.scanner._clean_game_title(raw_stem)
        self.assertEqual(cleaned, "Assassin's Creed IV - Black Flag")

    def test_ac4_metadata_resolution(self):
        """Tests that Assassin's Creed IV resolves official cover art, genre, and synopsis."""
        mgr = GameMetadataManager(self.scanner.project_root)
        meta = mgr.resolve_game_metadata(
            title="Assassin's Creed IV - Black Flag",
            platform="PS3",
            file_path="/fake/path/Library/ps3/Assassin's Creed IV - Black Flag.dec.iso",
            serial="BLUS31159"
        )
        self.assertEqual(meta["cover_art"], "/covers/ac4.jpg")
        self.assertEqual(meta["players"], "1 Player")
        self.assertIn("Ubisoft", meta.get("developer", "") or meta.get("publisher", ""))
        self.assertIn("Caribbean", meta["description"])

    def test_fifa18_and_wwe2011_multiplayer_metadata(self):
        """Tests FIFA 18 and WWE SmackDown vs. Raw 2011 metadata and multiplayer classification."""
        mgr = GameMetadataManager(self.scanner.project_root)

        fifa_meta = mgr.resolve_game_metadata(
            title="FIFA 18 - Legacy Edition",
            platform="XBOX360",
            file_path="/fake/path/fifa18.iso"
        )
        self.assertEqual(fifa_meta["cover_art"], "/covers/fifa_18.jpg")
        self.assertIn("1-4 Players", fifa_meta["players"])

        wwe_meta = mgr.resolve_game_metadata(
            title="WWE SmackDown vs. Raw 2011",
            platform="XBOX360",
            file_path="/fake/path/wwe2011.iso"
        )
        self.assertEqual(wwe_meta["cover_art"], "/covers/wwe_2011.jpg")
        self.assertIn("1-4 Players", wwe_meta["players"])

    def test_ps3_dec_iso_scan_discovery(self):
        """Tests that .dec.iso files placed in Library/ps3/ are indexed with proper format and title."""
        ps3_dir = os.path.join(self.temp_dir.name, "ps3")
        os.makedirs(ps3_dir, exist_ok=True)
        game_path = os.path.join(ps3_dir, "Assassin's Creed IV - Black Flag (USA).dec.iso")
        with open(game_path, "wb") as f:
            f.write(b"MOCK_PS3_DEC_ISO_BYTES")

        scanned = self.scanner.scan_all()
        matching = [g for g in scanned if "Assassin's Creed" in g.title]
        self.assertTrue(len(matching) >= 1)
        game = matching[0]
        self.assertEqual(game.platform, "PS3")
        self.assertEqual(game.format, "ISO")
        self.assertEqual(game.cover_art, "/covers/ac4.jpg")

    def test_windows_emulator_commands(self):
        """Tests command line argument generation for Windows 11 emulators."""
        launcher = EmulatorLauncher(self.config)

        # PS3 command
        cmd_ps3 = launcher.build_command_file("PS3", "C:\\Games\\ac4.dec.iso", "C:\\rpcs3\\rpcs3.exe")
        self.assertEqual(cmd_ps3, ["C:\\rpcs3\\rpcs3.exe", "--no-gui", "--fullscreen", "C:\\Games\\ac4.dec.iso"])

        # Xbox 360 command
        cmd_x360 = launcher.build_command_file("XBOX360", "C:\\Games\\fifa18.iso", "C:\\xenia\\xenia.exe")
        self.assertEqual(cmd_x360, ["C:\\xenia\\xenia.exe", "--fullscreen", "C:\\Games\\fifa18.iso"])

        # PCSX2 (PS2) command
        cmd_ps2 = launcher.build_command_file("PS2", "C:\\Games\\ffx.iso", "C:\\pcsx2\\pcsx2-qt.exe")
        self.assertEqual(cmd_ps2, ["C:\\pcsx2\\pcsx2-qt.exe", "-batch", "-fullscreen", "C:\\Games\\ffx.iso"])

        # DuckStation (PS1) command
        cmd_ps1 = launcher.build_command_file("PS1", "C:\\Games\\sotn.cue", "C:\\duckstation\\duckstation-qt.exe")
        self.assertEqual(cmd_ps1, ["C:\\duckstation\\duckstation-qt.exe", "-batch", "-fullscreen", "--", "C:\\Games\\sotn.cue"])


if __name__ == "__main__":
    unittest.main()
