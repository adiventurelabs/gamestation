"""
Integration tests using realistic mock PlayStation disc filesystem structures.
"""

import os
import unittest

from psconsole.disc_identifier import DiscIdentifier, DiscType


class TestMockDiscsIntegration(unittest.TestCase):
    def setUp(self):
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.mock_dir = os.path.join(self.base_dir, "mock_discs")
        self.identifier = DiscIdentifier()

    def test_ps1_castlevania_mock_disc(self):
        disc_path = os.path.join(self.mock_dir, "ps1_castlevania")
        info = self.identifier.identify_disc(disc_path, volume_label="CASTLEVANIA")
        self.assertEqual(info.disc_type, DiscType.PS1)
        self.assertEqual(info.serial, "SLUS-00067")
        self.assertEqual(info.title, "Castlevania: Symphony of the Night")
        self.assertTrue(info.is_playable)

    def test_ps2_ffx_mock_disc(self):
        disc_path = os.path.join(self.mock_dir, "ps2_finalfantasyx")
        info = self.identifier.identify_disc(disc_path, volume_label="FFX")
        self.assertEqual(info.disc_type, DiscType.PS2)
        self.assertEqual(info.serial, "SLUS-20062")
        self.assertEqual(info.title, "Final Fantasy X")
        self.assertTrue(info.is_playable)

    def test_ps1_ridge_racer_no_cnf_mock_disc(self):
        disc_path = os.path.join(self.mock_dir, "ps1_ridge_racer_no_cnf")
        info = self.identifier.identify_disc(disc_path, volume_label="RIDGE_RACER")
        self.assertEqual(info.disc_type, DiscType.PS1)
        self.assertEqual(info.serial, "SLUS-00001")
        self.assertEqual(info.title, "Ridge Racer")
        self.assertTrue(info.is_playable)

    def test_dvd_video_mock_disc(self):
        disc_path = os.path.join(self.mock_dir, "dvd_video")
        info = self.identifier.identify_disc(disc_path, volume_label="MOVIE_DISC")
        self.assertEqual(info.disc_type, DiscType.UNSUPPORTED_MEDIA)
        self.assertIn("DVD-Video", info.title)
        self.assertFalse(info.is_playable)

    def test_audio_cd_mock_disc(self):
        disc_path = os.path.join(self.mock_dir, "audio_cd")
        info = self.identifier.identify_disc(disc_path)
        self.assertEqual(info.disc_type, DiscType.UNSUPPORTED_MEDIA)
        self.assertFalse(info.is_playable)


if __name__ == "__main__":
    unittest.main()
