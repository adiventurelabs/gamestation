"""
PlayStation Console Dashboard HTTP & REST API Server.
Hosts the local WebGL/HTML5 60fps PlayStation console interface,
serves game library data, and bridges browser Gamepad input to emulator launching.
"""

import os
import sys
import json
import urllib.parse
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading
from typing import Optional, Dict, Any

from ..library_scanner import LibraryScanner
from ..disc_identifier import DiscInfo, DiscType


class DashboardAPIHandler(SimpleHTTPRequestHandler):
    """Handles static assets and PlayStation Console REST endpoints."""

    # Reference to active PSConsoleService instance
    service_ref = None
    scanner_ref = None

    def __init__(self, *args, **kwargs):
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        super().__init__(*args, directory=static_dir, **kwargs)

    def do_GET(self):
        url_parts = urllib.parse.urlparse(self.path)
        path = url_parts.path

        if path == "/api/status":
            self._handle_get_status()
        elif path == "/api/library":
            self._handle_get_library()
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
        else:
            self.send_error(404, "Endpoint not found")

    def _handle_get_status(self):
        service = DashboardAPIHandler.service_ref
        disc_info: Optional[DiscInfo] = service.current_disc_info if service else None
        is_playing = (service.state.value == "PLAYING") if service else False
        active_target = service.launcher.active_target if (service and service.launcher) else None

        data = {
            "is_playing": is_playing,
            "active_game": active_target,
            "state": service.state.value if service else "IDLE",
            "disc": {
                "present": bool(disc_info and disc_info.is_playable),
                "type": disc_info.disc_type.value if disc_info else None,
                "title": disc_info.title if disc_info else None,
                "serial": disc_info.serial if disc_info else None,
                "drive_path": disc_info.drive_path if disc_info else None
            }
        }
        self._send_json(data)

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
                self._send_json({"success": res.status.value == "SUCCESS", "status": res.status.value, "error": res.error_message})
            else:
                self._send_json({"success": False, "error": "No playable disc in drive"}, status=400)
        else:
            platform = payload.get("platform", "PS1")
            file_path = payload.get("file_path", "")
            title = payload.get("title", "Game")
            res = service.launcher.launch_digital_game(platform, file_path, title)
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
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Silence routine HTTP request logging to avoid terminal clutter
        pass


class DashboardServer:
    """Manages background HTTP server lifecycle for the PlayStation console shell."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8088, service=None, config=None, logger=None):
        self.host = host
        self.port = port
        self.service = service
        self.config = config or {}
        self.logger = logger
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

        DashboardAPIHandler.service_ref = service
        DashboardAPIHandler.scanner_ref = LibraryScanner(self.config, logger=logger)

    def start(self):
        try:
            self.server = HTTPServer((self.host, self.port), DashboardAPIHandler)
            self._thread = threading.Thread(target=self.server.serve_forever, daemon=True, name="DashboardServer")
            self._thread.start()
            if self.logger:
                self.logger.info(f"PlayStation Console Dashboard server running at http://{self.host}:{self.port}")
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
