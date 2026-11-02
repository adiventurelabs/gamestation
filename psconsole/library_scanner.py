"""
PlayStation Digital Game Library Scanner.
Discovers and indexes downloaded PS1, PS2, PS3, and PS4 games
from configured local storage directories for display in the console dashboard.
"""

import os
import glob
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional

from .utils import expand_windows_path
from .disc_identifier import DiscIdentifier
from .game_database import GameDatabase, normalize_serial


@dataclass
class LibraryGame:
    id: str
    title: str
    platform: str  # PS1, PS2, PS3, PS4
    file_path: str
    file_size_mb: float
    format: str  # CUE, CHD, ISO, PKG, FOLDER
    serial: Optional[str] = None
    cover_art: Optional[str] = None
    release_year: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LibraryScanner:
    """Scans local directories for downloaded PlayStation game images and packages."""

    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger
        self.db = GameDatabase()
        self.identifier = DiscIdentifier(self.db)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def get_library_directories(self) -> Dict[str, List[str]]:
        """Resolves target library paths for each platform."""
        lib_cfg = self.config.get("library", {})
        default_base = os.path.join(self.project_root, "library")
        demo_base = os.path.join(self.project_root, "demo_games")

        return {
            "PS1": [
                expand_windows_path(lib_cfg.get("ps1_dir", os.path.join(default_base, "ps1"))),
                os.path.join(demo_base, "ps1")
            ],
            "PS2": [
                expand_windows_path(lib_cfg.get("ps2_dir", os.path.join(default_base, "ps2"))),
                os.path.join(demo_base, "ps2")
            ],
            "PS3": [
                expand_windows_path(lib_cfg.get("ps3_dir", os.path.join(default_base, "ps3"))),
                os.path.join(demo_base, "ps3")
            ],
            "PS4": [
                expand_windows_path(lib_cfg.get("ps4_dir", os.path.join(default_base, "ps4"))),
                os.path.join(demo_base, "ps4")
            ]
        }

    def scan_all(self) -> List[LibraryGame]:
        """Scans all configured directories and returns a unified list of games."""
        games: List[LibraryGame] = []
        dirs = self.get_library_directories()

        for platform, path_list in dirs.items():
            for folder in path_list:
                if not os.path.isdir(folder):
                    continue
                games.extend(self._scan_platform_folder(platform, folder))

        return games

    def _scan_platform_folder(self, platform: str, folder: str) -> List[LibraryGame]:
        games = []
        try:
            for item in sorted(os.listdir(folder)):
                full_path = os.path.join(folder, item)

                if os.path.isdir(full_path):
                    # Check for PS3 folder game (PS3_GAME/PARAM.SFO)
                    if platform == "PS3":
                        sfo_path = os.path.join(full_path, "PS3_GAME", "PARAM.SFO")
                        if os.path.isfile(sfo_path):
                            with open(sfo_path, "rb") as f:
                                params = self.identifier.parse_param_sfo(f.read())
                            title = params.get("TITLE", item)
                            serial = params.get("TITLE_ID")
                            size_mb = self._get_folder_size_mb(full_path)
                            game = LibraryGame(
                                id=f"ps3_{item}",
                                title=title,
                                platform="PS3",
                                file_path=full_path,
                                file_size_mb=round(size_mb, 1),
                                format="FOLDER",
                                serial=serial
                            )
                            games.append(game)
                    continue

                ext = os.path.splitext(item)[1].lower()

                # Filter valid extensions by platform
                valid_exts = {
                    "PS1": [".cue", ".chd", ".iso", ".pbp"],
                    "PS2": [".iso", ".chd", ".cso", ".bin"],
                    "PS3": [".iso", ".pkg"],
                    "PS4": [".pkg", ".bin"]
                }.get(platform, [])

                if ext in valid_exts:
                    # Ignore .bin files if a .cue file exists for PS1
                    if platform == "PS1" and ext == ".bin":
                        base_name = os.path.splitext(item)[0]
                        if os.path.isfile(os.path.join(folder, f"{base_name}.cue")):
                            continue

                    size_mb = os.path.getsize(full_path) / (1024 * 1024)
                    clean_name = os.path.splitext(item)[0].replace("_", " ").replace("-", " ").title()

                    # Try serial lookup from filename (e.g. SLUS-20062)
                    serial = normalize_serial(clean_name)
                    title = self.db.get_title(serial) if serial else None
                    if not title:
                        title = clean_name

                    game = LibraryGame(
                        id=f"{platform.lower()}_{clean_name[:20].lower()}",
                        title=title,
                        platform=platform,
                        file_path=full_path,
                        file_size_mb=round(size_mb, 1),
                        format=ext.lstrip(".").upper(),
                        serial=serial
                    )
                    games.append(game)

        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error scanning library folder {folder}: {e}")

        return games

    def _get_folder_size_mb(self, folder: str) -> float:
        total = 0
        for dirpath, _, filenames in os.walk(folder):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total / (1024 * 1024)
