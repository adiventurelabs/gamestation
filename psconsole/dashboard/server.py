"""
GameStation Console Dashboard HTTP & REST API Server.
Hosts the local WebGL/HTML5 60fps GameStation console interface,
serves game library data, and bridges browser Gamepad input to emulator launching.
"""

import os
import sys
import json
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import threading
from typing import Optional, Dict, Any

from ..library_scanner import LibraryScanner
from ..disc_identifier import DiscInfo, DiscType


class DashboardAPIHandler(SimpleHTTPRequestHandler):
    """Handles static assets and GameStation Console REST endpoints."""

    # Reference to active PSConsoleService instance
    service_ref = None
    scanner_ref = None

    def __init__(self, *args, **kwargs):
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        super().__init__(*args, directory=static_dir, **kwargs)

    def do_OPTIONS(self):
        """Handles browser pre-flight checks for CORS."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path

        if path == "/api/status":
            self._handle_get_status()
        elif path == "/api/library":
            self._handle_get_library()
        elif path == "/api/ingestion/status":
            self._handle_get_ingestion()
        else:
            # Fallback to static files
            super().do_GET()

    def do_POST(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path

        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
        try:
            payload = json.loads(body)
        except Exception:
            payload = {}

        if path == "/api/launch":
            self._handle_post_launch(payload)
        elif path == "/api/exit":
            self._handle_post_exit()
        elif path == "/api/refresh":
            self._handle_get_library()
        elif path == "/api/ingestion/cancel":
            self._handle_cancel_ingestion()
        elif path == "/api/test/insert_disc":
            self._handle_post_test_disc(payload)
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_get_status(self):
        service = DashboardAPIHandler.service_ref
        disc_info: Optional[DiscInfo] = service.current_disc_info if service else None
        launcher_running = bool(service and service.launcher and service.launcher.is_emulator_running())
        is_playing = (service.state.value == "PLAYING" or launcher_running) if (service and hasattr(service, "state")) else False
        active_target = service.launcher.active_target if (service and service.launcher and isinstance(service.launcher.active_target, str)) else None
        raw_platform = getattr(service.launcher, "active_platform", None) if (service and service.launcher) else None
        active_platform = raw_platform if isinstance(raw_platform, str) else None

        ingestion_state = None
        if service and hasattr(service, "ingestion_pipeline") and service.ingestion_pipeline:
            try:
                res = service.ingestion_pipeline.get_state()
                if isinstance(res, dict):
                    ingestion_state = res
            except Exception:
                pass

        data = {
            "is_playing": is_playing,
            "active_game": active_target,
            "active_platform": active_platform,
            "state": service.state.value if (service and hasattr(service.state, "value")) else "IDLE",
            "disc": {
                "present": bool(disc_info and disc_info.is_playable),
                "type": disc_info.disc_type.value if (disc_info and hasattr(disc_info.disc_type, "value")) else None,
                "title": disc_info.title if disc_info else None,
                "serial": disc_info.serial if disc_info else None,
                "drive_path": disc_info.drive_path if disc_info else None,
                "requires_ingestion": disc_info.requires_ingestion if disc_info else False
            },
            "ingestion": ingestion_state
        }
        self._send_json(data)

    def _handle_get_ingestion(self):
        service = DashboardAPIHandler.service_ref
        res = {"is_active": False, "progress_percent": 0}
        if service and hasattr(service, "ingestion_pipeline") and service.ingestion_pipeline:
            try:
                raw_state = service.ingestion_pipeline.get_state()
                if isinstance(raw_state, dict):
                    res = raw_state
            except Exception:
                pass
        self._send_json(res)

    def _handle_cancel_ingestion(self):
        service = DashboardAPIHandler.service_ref
        if service and hasattr(service, "ingestion_pipeline"):
            service.ingestion_pipeline.cancel()
            self._send_json({"success": True})
        else:
            self._send_json({"success": False, "error": "No service running"})

    def _handle_post_test_disc(self, payload: Dict[str, Any]):
        service = DashboardAPIHandler.service_ref
        if not service:
            self._send_json({"success": False, "error": "Service unavailable"}, status=503)
            return

        action = payload.get("action", "insert")
        disc_gen = payload.get("generation", "PS1").upper()

        if action == "eject":
            service.handle_disc_removed("D:\\")
            self._send_json({"success": True, "action": "ejected"})
            return

        import tempfile
        test_dir = os.path.join(tempfile.gettempdir(), f"psconsole_test_{disc_gen.lower()}")
        os.makedirs(test_dir, exist_ok=True)

        volume_label = "GAME_DISC"
        if disc_gen == "PS1":
            volume_label = "CASTLEVANIA"
            with open(os.path.join(test_dir, "SYSTEM.CNF"), "w", encoding="utf-8") as f:
                f.write("BOOT = cdrom:\\SLUS_000.67;1\r\nTCB = 4\r\nEVENT = 16\r\nSTACK = 801FFF00\r\n")
        elif disc_gen == "PS2":
            volume_label = "SHADOW_COLOSSUS"
            with open(os.path.join(test_dir, "SYSTEM.CNF"), "w", encoding="utf-8") as f:
                f.write("BOOT2 = cdrom0:\\SCUS_971.24;1\r\nVER = 1.00\r\nVMODE = NTSC\r\n")
        elif disc_gen == "PS3":
            volume_label = "DEMONS_SOULS"
            ps3_game = os.path.join(test_dir, "PS3_GAME")
            os.makedirs(ps3_game, exist_ok=True)
            with open(os.path.join(test_dir, "PS3_DISC.SFB"), "wb") as f:
                f.write(b"\x00PS3_DISC_SFB_MOCK")
            with open(os.path.join(ps3_game, "PARAM.SFO"), "wb") as f:
                f.write(b"\x00PSF\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
        elif disc_gen == "XBOX":
            volume_label = "HALO_2"
            with open(os.path.join(test_dir, "default.xbe"), "wb") as f:
                f.write(b"MOCK_ORIGINAL_XBOX_EXECUTABLE" * 20)
        elif disc_gen == "XBOX360":
            volume_label = "GEARS_OF_WAR"
            with open(os.path.join(test_dir, "default.xex"), "wb") as f:
                f.write(b"MOCK_XBOX360_EXECUTABLE" * 20)
            os.makedirs(os.path.join(test_dir, "$SystemUpdate"), exist_ok=True)
        elif disc_gen == "PS4":
            volume_label = "CUSA-00001"
            sce_sys = os.path.join(test_dir, "sce_sys")
            os.makedirs(sce_sys, exist_ok=True)
            with open(os.path.join(test_dir, "eboot.bin"), "wb") as f:
                f.write(b"MOCK_PS4_ELF" * 20)

        service.handle_disc_inserted(test_dir, volume_label)
        self._send_json({"success": True, "action": "inserted", "generation": disc_gen, "label": volume_label})

    def _handle_get_library(self):
        scanner = DashboardAPIHandler.scanner_ref
        games = []
        if scanner:
            scanned = scanner.scan_all()
            games = [g.to_dict() for g in scanned]
        self._send_json({"games": games, "total": len(games)})

    def _handle_post_launch(self, payload: Dict[str, Any]):
        service = DashboardAPIHandler.service_ref
        if not service:
            self._send_json({"success": False, "error": "Service unavailable"}, status=503)
            return

        launch_type = payload.get("type", "disc")
        if launch_type == "disc":
            if service.current_disc_info and service.current_disc_info.is_playable:
                res = service.launcher.launch(service.current_disc_info)
                if res.status.value == "SUCCESS" and hasattr(service, "state"):
                    from ..service import ServiceState
                    service.state = ServiceState.PLAYING
                self._send_json({"success": res.status.value == "SUCCESS", "status": res.status.value, "error": res.error_message})
            else:
                self._send_json({"success": False, "error": "No playable disc in drive"}, status=400)
        else:
            platform = payload.get("platform", "PS1")
            file_path = payload.get("file_path", "")
            title = payload.get("title", "Game")
            res = service.launcher.launch_digital_game(platform, file_path, title)
            if res.status.value == "SUCCESS" and hasattr(service, "state"):
                from ..service import ServiceState
                service.state = ServiceState.PLAYING
            self._send_json({"success": res.status.value == "SUCCESS", "status": res.status.value, "error": res.error_message})

    def _handle_post_exit(self):
        service = DashboardAPIHandler.service_ref
        if service:
            service.handle_controller_exit()
            self._send_json({"success": True})
        else:
            self._send_json({"success": False}, status=503)

    def _send_json(self, data: Any, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Silence routine HTTP request logging to avoid terminal clutter
        pass


class DashboardServer:
    """Manages background HTTP server lifecycle for the PlayStation console shell."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8088, service=None, config=None, logger=None):
        self.host = host
        self.port = port
        self.service = service
        self.config = config or {}
        self.logger = logger
        self.server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

        DashboardAPIHandler.service_ref = service
        DashboardAPIHandler.scanner_ref = LibraryScanner(self.config, logger=logger)

    def start(self):
        try:
            ThreadingHTTPServer.allow_reuse_address = True
            self.server = ThreadingHTTPServer((self.host, self.port), DashboardAPIHandler)
            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="DashboardServer")
            self._thread.start()
            if self.logger:
                self.logger.info(f"GameStation Console Dashboard server running at http://{self.host}:{self.port}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to start dashboard server: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        if self._thread:
            self._thread.join(timeout=1.0)
            self._thread = None
