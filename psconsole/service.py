"""
PlayStation Console Main Service.
Coordinates disc detection, disc identification, emulator lifecycle,
controller exit monitoring, and TV-safe UI notifications.
"""

import os
import sys
import time
import json
import signal
from enum import Enum
from typing import Optional, Dict, Any

from .utils import setup_logger, expand_windows_path
from .disc_detector import DiscDetector
from .disc_identifier import DiscIdentifier, DiscType, DiscInfo
from .emulator_launcher import EmulatorLauncher, LaunchStatus
from .controller_monitor import ControllerMonitor
from .ui_overlay import UIOverlay
from .dashboard.server import DashboardServer
from .ingestion_pipeline import IngestionPipeline


class ServiceState(Enum):
    IDLE = "IDLE"
    ANALYZING = "ANALYZING"
    INGESTING = "INGESTING"
    LAUNCHING = "LAUNCHING"
    PLAYING = "PLAYING"


class PSConsoleService:
    """Core daemon managing physical PlayStation disc console automation."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "config.json"
        )
        self.config = self._load_config()

        log_cfg = self.config.get("logging", {})
        self.logger = setup_logger(
            log_dir=log_cfg.get("log_dir"),
            log_level=log_cfg.get("level", "INFO"),
            filename=log_cfg.get("filename", "psconsole.log"),
            max_bytes=log_cfg.get("max_bytes", 5 * 1024 * 1024),
            backup_count=log_cfg.get("backup_count", 3),
            to_console=False
        )

        self.state = ServiceState.IDLE
        self.current_disc_info: Optional[DiscInfo] = None
        self._running = False

        # Initialize subsystems
        self.identifier = DiscIdentifier()
        self.launcher = EmulatorLauncher(self.config, logger=self.logger)
        self.overlay = UIOverlay(
            dark_mode=self.config.get("ui", {}).get("dark_mode", True),
            logger=self.logger
        )

        self.detector = DiscDetector(
            config=self.config,
            on_disc_inserted=self.handle_disc_inserted,
            on_disc_removed=self.handle_disc_removed,
            on_disc_arriving=self.handle_disc_arriving,
            logger=self.logger
        )

        self.controller = ControllerMonitor(
            config=self.config,
            on_exit_requested=self.handle_controller_exit,
            logger=self.logger
        )

        # Ingestion Pipeline for offline disc ripping/extraction
        self.ingestion_pipeline = IngestionPipeline(self.config, logger=self.logger)

        # Dashboard Server
        dash_cfg = self.config.get("dashboard", {})
        self.dashboard = DashboardServer(
            host=dash_cfg.get("host", "127.0.0.1"),
            port=dash_cfg.get("port", 8088),
            service=self,
            config=self.config,
            logger=self.logger
        ) if dash_cfg.get("enabled", True) else None

    def _load_config(self) -> Dict[str, Any]:
        """Loads configuration JSON with safe defaults."""
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                sys.stderr.write(f"Failed to parse config file: {e}\n")
        return {}

    def start(self):
        """Starts all background watchers and enters the main service loop."""
        self.logger.info("==========================================")
        self.logger.info("Starting GameStation Console Service v1.0")
        self.logger.info("==========================================")
        self._running = True

        # Signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

        # Start subsystems
        self.detector.start()
        self.controller.start()
        if self.dashboard:
            self.dashboard.start()

        # Handle disc already inserted at startup
        self.detector.check_initial_discs()

        # Main service loop
        while self._running:
            self._update_state()
            time.sleep(0.5)

    def stop(self):
        """Clean shutdown of service and child processes."""
        self.logger.info("Stopping GameStation Console Service...")
        self._running = False

        if self.state == ServiceState.PLAYING:
            self.launcher.stop_active_emulator()

        if hasattr(self, "ingestion_pipeline") and self.ingestion_pipeline.is_ingesting():
            self.ingestion_pipeline.cancel()

        if self.dashboard:
            self.dashboard.stop()

        self.controller.stop()
        self.detector.stop()
        self.logger.info("GameStation Console Service stopped cleanly.")

    def _handle_signal(self, signum, frame):
        self.logger.info(f"Received shutdown signal ({signum}).")
        self.stop()
        sys.exit(0)

    def _update_state(self):
        """Checks if emulator process finished naturally (e.g. via in-game menu)."""
        if self.state == ServiceState.PLAYING:
            if not self.launcher.is_emulator_running():
                self.logger.info("Emulator exited naturally; returning to IDLE state.")
                self.state = ServiceState.IDLE
                self.current_disc_info = None
                self.launcher.restore_launcher_focus()

    def handle_disc_arriving(self, drive_path: str):
        """Triggered immediately when optical media is loaded into the tray before spin-up completes."""
        if self.state == ServiceState.PLAYING and self.launcher.is_emulator_running():
            return
        self.logger.info(f"Optical disc spin-up initiated on {drive_path}. Displaying reading banner...")
        self.overlay.show_reading_toast(drive_path)

    def handle_disc_inserted(self, drive_path: str, volume_label: Optional[str] = None):
        """Triggered when a disc has arrived and is ready for reading."""
        # Do not disrupt an active gaming session!
        if self.state == ServiceState.PLAYING and self.launcher.is_emulator_running():
            self.logger.info(f"Disc inserted in {drive_path} while game is currently running; ignoring event.")
            return

        self.logger.info(f"Processing disc in {drive_path} (volume: {volume_label})...")
        self.state = ServiceState.ANALYZING

        # Identify disc
        disc_info = self.identifier.identify_disc(drive_path, volume_label)
        self.current_disc_info = disc_info
        self.logger.info(f"Disc Identification result: {disc_info.disc_type.value} | Title: {disc_info.title} | Serial: {disc_info.serial}")

        if disc_info.is_playable:
            # Check if disc requires offline toolchain ingestion (PS4, Xbox, Xbox 360)
            if disc_info.requires_ingestion:
                self.logger.info(f"{disc_info.disc_type.value} disc detected requiring offline ingestion: '{disc_info.title}'")
                self.state = ServiceState.INGESTING

                toast_sec = self.config.get("ui", {}).get("toast_duration_seconds", 3.5)
                self.overlay.show_launch_toast(
                    title=f"{disc_info.disc_type.value} Installation Started",
                    subtitle=disc_info.title,
                    serial=disc_info.serial,
                    disc_type=disc_info.disc_type.value,
                    duration_sec=toast_sec
                )

                def _on_ingestion_finished(platform: str, output_path: str, title: str):
                    self.logger.info(f"Ingestion complete for '{title}' -> {output_path}. Initiating emulator boot...")
                    self.state = ServiceState.LAUNCHING
                    res = self.launcher.launch_digital_game(platform, output_path, title)
                    if res.status == LaunchStatus.SUCCESS:
                        self.logger.info(f"Successfully launched ingested {platform} game '{title}'")
                        self.state = ServiceState.PLAYING
                    else:
                        self.logger.error(f"Failed to launch ingested game: {res.error_message}")
                        self.overlay.show_error_screen(
                            title="Launch Failed",
                            message=f"Could not boot ingested game: {res.error_message or 'Unknown error'}",
                            duration_sec=6.0
                        )
                        self.state = ServiceState.IDLE

                self.ingestion_pipeline.start_ingestion(disc_info, on_complete=_on_ingestion_finished)
                return

            # Direct Disc Launch for PS1, PS2, PS3
            toast_sec = self.config.get("ui", {}).get("toast_duration_seconds", 3.5)
            gen_label_map = {
                DiscType.PS1: "PlayStation",
                DiscType.PS2: "PlayStation 2",
                DiscType.PS3: "PlayStation 3",
                DiscType.PS4: "PlayStation 4",
                DiscType.XBOX: "Xbox",
                DiscType.XBOX360: "Xbox 360"
            }
            gen_label = gen_label_map.get(disc_info.disc_type, disc_info.disc_type.value)
            self.overlay.show_launch_toast(
                title=f"{gen_label} Disc Detected",
                subtitle=disc_info.title,
                serial=disc_info.serial,
                disc_type=disc_info.disc_type.value,
                duration_sec=toast_sec
            )

            # Launch emulator
            self.state = ServiceState.LAUNCHING
            res = self.launcher.launch(disc_info)

            if res.status == LaunchStatus.SUCCESS:
                pid_desc = f"(PID: {res.process.pid})" if (res.process and hasattr(res.process, "pid")) else "(Simulated)"
                self.logger.info(f"Successfully launched {res.emulator_name} for '{disc_info.title}' {pid_desc}")
                self.state = ServiceState.PLAYING
            elif res.status == LaunchStatus.BIOS_MISSING:
                self.logger.error(f"Cannot launch: {res.error_message}")
                self.overlay.show_error_screen(
                    title="PlayStation BIOS Required",
                    message=f"Missing BIOS file for {res.emulator_name}. Please place your dumped BIOS in the emulator folder.",
                    duration_sec=7.0
                )
                self.state = ServiceState.IDLE
            elif res.status == LaunchStatus.EMULATOR_NOT_FOUND:
                self.logger.error(f"Cannot launch: {res.error_message}")
                self.overlay.show_error_screen(
                    title="Emulator Not Found",
                    message=f"{res.emulator_name} is not installed in configured candidates. Please install {res.emulator_name}.",
                    duration_sec=7.0
                )
                self.state = ServiceState.IDLE
            else:
                self.logger.error(f"Launch failed: {res.error_message}")
                self.overlay.show_error_screen(
                    title="Launch Failed",
                    message=f"Could not start game: {res.error_message or 'Unknown error'}",
                    duration_sec=6.0
                )
                self.state = ServiceState.IDLE

        elif disc_info.disc_type == DiscType.UNSUPPORTED_MEDIA:
            self.logger.warning(f"Unsupported disc inserted: {disc_info.error_message}")
            self.overlay.show_error_screen(
                title=disc_info.title,
                message=disc_info.error_message or "Inserted disc is not a PlayStation 1 or 2 game.",
                hint="Please eject disc to return to console menu",
                duration_sec=6.0
            )
            self.state = ServiceState.IDLE

        elif disc_info.disc_type == DiscType.UNREADABLE:
            self.logger.warning(f"Unreadable disc: {disc_info.error_message}")
            self.overlay.show_error_screen(
                title="Disc Read Error",
                message="Unable to read optical disc. Check for dust, scratches, or drive connection.",
                duration_sec=6.0
            )
            self.state = ServiceState.IDLE

    def handle_disc_removed(self, drive_path: str):
        """Triggered when optical media is ejected."""
        self.logger.info(f"Disc removed from {drive_path}")
        self.current_disc_info = None
        if self.state == ServiceState.PLAYING:
            self.logger.warning("Active game disc was ejected during gameplay session. Emulator will manage drive I/O; user can exit via controller.")

    def handle_controller_exit(self):
        """Triggered when user holds the deliberate controller exit shortcut or taps exit."""
        self.overlay.close_active_overlay()
        self.logger.info("Deliberate controller exit shortcut triggered. Closing active emulator gracefully...")
        self.launcher.stop_active_emulator()
        self.state = ServiceState.IDLE
        self.current_disc_info = None
        self.logger.info("Session ended; returned to console launcher.")


def main():
    service = PSConsoleService()
    try:
        service.start()
    except KeyboardInterrupt:
        service.stop()


if __name__ == "__main__":
    main()
