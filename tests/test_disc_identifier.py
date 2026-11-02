"""
Tests for DiscIdentifier and GameDatabase.
Verifies SYSTEM.CNF parsing (PS1/PS2), PARAM.SFO parsing (PS3/PS4),
serial extraction, and error handling.
"""

import os
import struct
import shutil
import tempfile
import unittest

from psconsole.disc_identifier import DiscIdentifier, DiscType
from psconsole.game_database import GameDatabase, normalize_serial


def create_mock_sfo(title: str, title_id: str) -> bytes:
    """Helper to generate a binary PARAM.SFO structure."""
    magic = b"\x00PSF"
    version = b"\x01\x01\x00\x00"
    key_data = b"TITLE\x00TITLE_ID\x00"
    val_title = title.encode("utf-8") + b"\x00"
    val_id = title_id.encode("utf-8") + b"\x00"

    key_table_start = 20 + 32  # Header (20) + 2 entries (32)
    data_table_start = key_table_start + len(key_data)

    header = struct.pack("<4s4sIII", magic, version, key_table_start, data_table_start, 2)
    entry0 = struct.pack("<HHIII", 0, 0x0204, len(val_title), len(val_title), 0)
    entry1 = struct.pack("<HHIII", 6, 0x0204, len(val_id), len(val_id), len(val_title))

    return header + entry0 + entry1 + key_data + val_title + val_id


class TestDiscIdentifier(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.identifier = DiscIdentifier()

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_normalize_serial(self):
        self.assertEqual(normalize_serial("cdrom0:\\SLUS_200.62;1"), "SLUS-20062")
        self.assertEqual(normalize_serial("cdrom:\\SLUS_000.67;1"), "SLUS-00067")
        self.assertEqual(normalize_serial("SCUS_941.63"), "SCUS-94163")
        self.assertEqual(normalize_serial("sles-50361"), "SLES-50361")
        self.assertEqual(normalize_serial("SCES_000.01;1"), "SCES-00001")
        self.assertEqual(normalize_serial("BLUS-30444"), "BLUS-30444")

    def test_ps1_disc_detection(self):
        cnf_content = (
            "BOOT = cdrom:\\SLUS_000.67;1\r\n"
            "TCB = 4\r\n"
            "EVENT = 10\r\n"
            "STACK = 801FFFF0\r\n"
        )
        cnf_path = os.path.join(self.test_dir, "SYSTEM.CNF")
        with open(cnf_path, "w") as f:
            f.write(cnf_content)

        info = self.identifier.identify_disc(self.test_dir, volume_label="CASTLEVANIA")
        self.assertEqual(info.disc_type, DiscType.PS1)
        self.assertEqual(info.serial, "SLUS-00067")
        self.assertEqual(info.title, "Castlevania: Symphony of the Night")
        self.assertTrue(info.is_playable)

    def test_ps2_disc_detection(self):
        cnf_content = (
            "BOOT2 = cdrom0:\\SLUS_200.62;1\r\n"
            "VER = 1.00\r\n"
            "VMODE = NTSC\r\n"
        )
        cnf_path = os.path.join(self.test_dir, "system.cnf")
        with open(cnf_path, "w") as f:
            f.write(cnf_content)

        info = self.identifier.identify_disc(self.test_dir, volume_label="FINAL_FANTASY_X")
        self.assertEqual(info.disc_type, DiscType.PS2)
        self.assertEqual(info.serial, "SLUS-20062")
        self.assertEqual(info.title, "Final Fantasy X")
        self.assertTrue(info.is_playable)

    def test_ps3_disc_detection(self):
        # Create PS3_DISC.SFB and PS3_GAME/PARAM.SFO
        with open(os.path.join(self.test_dir, "PS3_DISC.SFB"), "wb") as f:
            f.write(b"MOCK_PS3_SFB")

        game_dir = os.path.join(self.test_dir, "PS3_GAME")
        os.makedirs(game_dir)
        sfo_bytes = create_mock_sfo("Demon's Souls", "BLUS-30444")
        with open(os.path.join(game_dir, "PARAM.SFO"), "wb") as f:
            f.write(sfo_bytes)

        info = self.identifier.identify_disc(self.test_dir, volume_label="DEMONS_SOULS")
        self.assertEqual(info.disc_type, DiscType.PS3)
        self.assertEqual(info.title, "Demon's Souls")
        self.assertEqual(info.serial, "BLUS-30444")
        self.assertTrue(info.is_playable)

    def test_ps4_package_detection(self):
        # Create sce_sys/param.sfo
        sce_dir = os.path.join(self.test_dir, "sce_sys")
        os.makedirs(sce_dir)
        sfo_bytes = create_mock_sfo("Bloodborne", "CUSA-00900")
        with open(os.path.join(sce_dir, "param.sfo"), "wb") as f:
            f.write(sfo_bytes)

        info = self.identifier.identify_disc(self.test_dir, volume_label="BLOODBORNE")
        self.assertEqual(info.disc_type, DiscType.PS4)
        self.assertEqual(info.title, "Bloodborne")
        self.assertEqual(info.serial, "CUSA-00900")
        self.assertTrue(info.is_playable)

    def test_dvd_video_detection(self):
        os.makedirs(os.path.join(self.test_dir, "VIDEO_TS"))
        with open(os.path.join(self.test_dir, "VIDEO_TS", "VIDEO_TS.IFO"), "w") as f:
            f.write("mock dvd video")

        info = self.identifier.identify_disc(self.test_dir, volume_label="THE_MATRIX")
        self.assertEqual(info.disc_type, DiscType.UNSUPPORTED_MEDIA)
        self.assertFalse(info.is_playable)
        self.assertIn("DVD-Video", info.title)

    def test_audio_or_empty_disc(self):
        info = self.identifier.identify_disc(self.test_dir)
        self.assertEqual(info.disc_type, DiscType.UNSUPPORTED_MEDIA)
        self.assertFalse(info.is_playable)

    def test_early_ps1_without_system_cnf(self):
        with open(os.path.join(self.test_dir, "PSX.EXE"), "w") as f:
            f.write("executable")
        with open(os.path.join(self.test_dir, "SLUS_000.01"), "w") as f:
            f.write("executable")

        info = self.identifier.identify_disc(self.test_dir, volume_label="RIDGE_RACER")
        self.assertEqual(info.disc_type, DiscType.PS1)
        self.assertEqual(info.serial, "SLUS-00001")
        self.assertEqual(info.title, "Ridge Racer")
        self.assertTrue(info.is_playable)


if __name__ == "__main__":
    unittest.main()
