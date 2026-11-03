"""
Unit tests for GameStation Windows Automated Setup and Controller Configurator.
"""

import unittest
import os
import tempfile
import shutil
from psconsole.windows_setup import (
    configure_xenia_controllers,
    configure_duckstation_controllers,
    configure_pcsx2_controllers,
    configure_rpcs3_controllers,
    verify_system_readiness
)


class TestWindowsSetup(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_configure_xenia_controllers(self):
        """Verifies Xenia TOML configuration generation with XInput and fullscreen."""
        target = os.path.join(self.temp_dir.name, "xenia")
        paths = configure_xenia_controllers(target_dir=target)
        self.assertTrue(len(paths) >= 2)

        canary_cfg = os.path.join(target, "xenia-canary.config.toml")
        self.assertTrue(os.path.isfile(canary_cfg))
        with open(canary_cfg, "r") as f:
            content = f.read()
        self.assertIn('hid = "xinput"', content)
        self.assertIn("fullscreen = true", content)
        self.assertIn("license_mask = 1", content)

    def test_configure_duckstation_controllers(self):
        """Verifies DuckStation INI generation with dual XInput controllers."""
        target = os.path.join(self.temp_dir.name, "duckstation")
        paths = configure_duckstation_controllers(target_dir=target)
        self.assertTrue(len(paths) >= 1)

        ini_file = os.path.join(target, "settings.ini")
        self.assertTrue(os.path.isfile(ini_file))
        with open(ini_file, "r") as f:
            content = f.read()
        self.assertIn("ControllerType = XInput", content)
        self.assertIn("ControllerIndex = 0", content)
        self.assertIn("ControllerIndex = 1", content)
        self.assertIn("StartFullscreen = true", content)

    def test_configure_pcsx2_controllers(self):
        """Verifies PCSX2 INI generation with dual XInput controller auto-bindings."""
        target = os.path.join(self.temp_dir.name, "pcsx2")
        paths = configure_pcsx2_controllers(target_dir=target)
        self.assertTrue(len(paths) >= 1)

        ini_file = os.path.join(target, "inis", "PCSX2.ini")
        self.assertTrue(os.path.isfile(ini_file))
        with open(ini_file, "r") as f:
            content = f.read()
        self.assertIn("EnableXInput = true", content)
        self.assertIn("AutoBindingPath = XInput-0", content)
        self.assertIn("AutoBindingPath = XInput-1", content)
        self.assertIn("StartFullscreen = true", content)

    def test_configure_rpcs3_controllers(self):
        """Verifies RPCS3 input profile generation for dual XInput devices."""
        target = os.path.join(self.temp_dir.name, "rpcs3")
        paths = configure_rpcs3_controllers(target_dir=target)
        self.assertTrue(len(paths) >= 1)

        yml_file = os.path.join(target, "input_configs", "global", "Default.yml")
        self.assertTrue(os.path.isfile(yml_file))
        with open(yml_file, "r") as f:
            content = f.read()
        self.assertIn("Handler: XInput", content)
        self.assertIn('"XInput/0"', content)
        self.assertIn('"XInput/1"', content)

    def test_verify_system_readiness(self):
        """Tests that verify_system_readiness returns valid dictionary report."""
        report = verify_system_readiness()
        self.assertIn("platform", report)
        self.assertIn("python_version", report)
        self.assertIn("emulators_found", report)
        self.assertIsInstance(report["controllers_detected"], int)


if __name__ == "__main__":
    unittest.main()
