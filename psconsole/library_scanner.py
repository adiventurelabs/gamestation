"""
GameStation Digital Game Library Scanner.
Discovers and indexes downloaded games across PlayStation, Xbox, Nintendo,
and Sega consoles from configured local storage directories and project library
folders for display in the console dashboard.
"""

import os
import re
import glob
import shutil
import subprocess
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Set

from .utils import expand_windows_path
from .disc_identifier import DiscIdentifier
from .game_database import GameDatabase, normalize_serial


@dataclass
class LibraryGame:
    id: str
    title: str
    platform: str  # PS1, PS2, PS3, PS4, XBOX, XBOX360, PSP, GAMECUBE, WII, DREAMCAST, N64, SNES, GBA
    file_path: str
    file_size_mb: float
    format: str  # CUE, CHD, ISO, PKG, FOLDER, RVZ, CSO, etc.
    serial: Optional[str] = None
    cover_art: Optional[str] = None
    release_year: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LibraryScanner:
    """Scans local directories for downloaded console game images and packages."""

    KNOWN_PLATFORMS = {
        "PS1": "ps1",
        "PS2": "ps2",
        "PS3": "ps3",
        "PS4": "ps4",
        "XBOX": "xbox",
        "XBOX360": "xbox360",
        "PSP": "psp",
        "GAMECUBE": "gamecube",
        "WII": "wii",
        "DREAMCAST": "dreamcast",
        "N64": "n64",
        "SNES": "snes",
        "GBA": "gba"
    }

    def __init__(self, config: Dict[str, Any], logger=None):
        self.config = config
        self.logger = logger
        self.db = GameDatabase()
        self.identifier = DiscIdentifier(self.db)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _get_unique_directories(self, dir_names: List[str]) -> List[str]:
        """Resolves existing directories deduplicated by filesystem inode."""
        unique: List[str] = []
        seen_inodes: Set[int] = set()
        seen_paths: Set[str] = set()

        for d in dir_names:
            if not d:
                continue
            norm = os.path.normpath(d)
            if not os.path.isdir(norm):
                continue
            try:
                ino = os.stat(norm).st_ino
                if ino in seen_inodes:
                    continue
                seen_inodes.add(ino)
            except Exception:
                lower = norm.lower()
                if lower in seen_paths:
                    continue
                seen_paths.add(lower)
            unique.append(norm)

        return unique

    def get_library_directories(self) -> Dict[str, List[str]]:
        """Resolves target library paths for each platform, including project-local Library dirs."""
        lib_cfg = self.config.get("library", {})
        custom_base = lib_cfg.get("base_dir")
        default_bases = self._get_unique_directories([
            custom_base,
            os.path.join(self.project_root, "Library"),
            os.path.join(self.project_root, "library")
        ])
        demo_base = os.path.join(self.project_root, "demo_games")

        result: Dict[str, List[str]] = {}

        for plat_key, plat_folder in self.KNOWN_PLATFORMS.items():
            candidates: List[str] = []

            # 1. User configured path from config.json
            cfg_path = lib_cfg.get(f"{plat_folder}_dir")
            if cfg_path:
                candidates.append(expand_windows_path(cfg_path))

            # 2. Project-local library and Library folders
            for b in default_bases:
                candidates.append(os.path.join(b, plat_folder))

            # 3. Project demo_games folder
            candidates.append(os.path.join(demo_base, plat_folder))

            result[plat_key] = self._get_unique_directories(candidates)

        return result

    def scan_all(self) -> List[LibraryGame]:
        """Scans all configured directories and root Library folders, returning a unified list of games."""
        games: List[LibraryGame] = []
        seen_inodes: Set[int] = set()
        seen_paths: Set[str] = set()

        def is_seen(fp: str) -> bool:
            try:
                if os.path.exists(fp):
                    ino = os.stat(fp).st_ino
                    if ino in seen_inodes:
                        return True
                    seen_inodes.add(ino)
                    return False
            except Exception:
                pass
            low = fp.lower()
            if low in seen_paths:
                return True
            seen_paths.add(low)
            return False

        # 1. Scan platform subdirectories
        dirs = self.get_library_directories()
        for platform, path_list in dirs.items():
            for folder in path_list:
                for g in self._scan_platform_folder(platform, folder):
                    if not is_seen(g.file_path):
                        games.append(g)

        # 2. Scan root Library/ and library/ directories for loose games or unextracted archives
        existing_titles = {g.title.lower() for g in games}
        lib_cfg = self.config.get("library", {})
        custom_base = lib_cfg.get("base_dir")
        root_bases = self._get_unique_directories([
            custom_base,
            os.path.join(self.project_root, "Library"),
            os.path.join(self.project_root, "library")
        ])
        for rb in root_bases:
            for g in self._scan_root_library(rb, existing_titles):
                if not is_seen(g.file_path):
                    games.append(g)

        return games

    def _clean_game_title(self, raw_stem: str) -> str:
        """Cleans regional tags, brackets, parens, and standardizes title capitalization."""
        cleaned = re.sub(r"\[[^\]]*\]|\([^\)]*\)", "", raw_stem).strip()
        cleaned = re.sub(r"_+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -")

        words = cleaned.split()
        fixed = []
        for w in words:
            up = w.upper()
            low = w.lower()
            if up in (
                "WWE", "WWF", "FIFA", "NBA", "NFL", "NHL", "UFC", "MLB", "GTA", "NFS", "DBZ",
                "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII",
                "XIV", "XV", "XVI", "HD"
            ):
                fixed.append(up)
            elif low in ("vs.", "vs", "the", "of", "and", "in", "on", "a", "an") and fixed:
                fixed.append(low)
            elif w == "-":
                fixed.append("-")
            else:
                fixed.append(w.capitalize())

        return " ".join(fixed) if fixed else raw_stem

    def _scan_platform_folder(self, platform: str, folder: str) -> List[LibraryGame]:
        games: List[LibraryGame] = []
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
                            title = params.get("TITLE") or self._clean_game_title(item)
                            serial = params.get("TITLE_ID")
                            size_mb = self._get_folder_size_mb(full_path)
                            game = LibraryGame(
                                id=f"ps3_{item.lower()}",
                                title=title,
                                platform="PS3",
                                file_path=full_path,
                                file_size_mb=round(size_mb, 1),
                                format="FOLDER",
                                serial=serial
                            )
                            games.append(game)
                    elif platform == "PS4":
                        eboot_path = os.path.join(full_path, "eboot.bin")
                        if os.path.isfile(eboot_path):
                            size_mb = self._get_folder_size_mb(full_path)
                            sfo_path = os.path.join(full_path, "sce_sys", "param.sfo")
                            title = None
                            serial = None
                            if os.path.isfile(sfo_path):
                                try:
                                    with open(sfo_path, "rb") as f:
                                        params = self.identifier.parse_param_sfo(f.read())
                                    title = params.get("TITLE")
                                    serial = params.get("TITLE_ID")
                                except Exception:
                                    pass
                            if not title:
                                title = self._clean_game_title(item)
                            games.append(LibraryGame(
                                id=f"ps4_{item.lower()}",
                                title=title,
                                platform="PS4",
                                file_path=eboot_path,
                                file_size_mb=round(size_mb, 1),
                                format="FOLDER",
                                serial=serial
                            ))
                    elif platform == "XBOX":
                        xbe_path = os.path.join(full_path, "default.xbe")
                        if os.path.isfile(xbe_path):
                            size_mb = self._get_folder_size_mb(full_path)
                            title = self._clean_game_title(item)
                            games.append(LibraryGame(
                                id=f"xbox_{item.lower()}",
                                title=title,
                                platform="XBOX",
                                file_path=xbe_path,
                                file_size_mb=round(size_mb, 1),
                                format="FOLDER"
                            ))
                    elif platform == "XBOX360":
                        xex_path = os.path.join(full_path, "default.xex")
                        if os.path.isfile(xex_path):
                            size_mb = self._get_folder_size_mb(full_path)
                            title = self._clean_game_title(item)
                            games.append(LibraryGame(
                                id=f"xbox360_{item.lower()}",
                                title=title,
                                platform="XBOX360",
                                file_path=xex_path,
                                file_size_mb=round(size_mb, 1),
                                format="FOLDER"
                            ))
                    continue

                ext = os.path.splitext(item)[1].lower()

                # Filter valid extensions by platform
                valid_exts = {
                    "PS1": [".cue", ".chd", ".iso", ".pbp", ".bin"],
                    "PS2": [".iso", ".chd", ".cso", ".bin", ".gz"],
                    "PS3": [".iso", ".pkg"],
                    "PS4": [".pkg", ".bin"],
                    "PSP": [".iso", ".cso", ".chd", ".pbp"],
                    "GAMECUBE": [".rvz", ".iso", ".gcm", ".ciso"],
                    "WII": [".rvz", ".wbfs", ".iso", ".ciso"],
                    "DREAMCAST": [".chd", ".cdi", ".gdi"],
                    "N64": [".z64", ".n64", ".v64"],
                    "SNES": [".sfc", ".smc"],
                    "GBA": [".gba"],
                    "XBOX": [".iso", ".xbe"],
                    "XBOX360": [".iso", ".xex"]
                }.get(platform, [])

                if ext in valid_exts:
                    # Ignore .bin files if a .cue file exists for PS1
                    if platform == "PS1" and ext == ".bin":
                        base_name = os.path.splitext(item)[0]
                        if os.path.isfile(os.path.join(folder, f"{base_name}.cue")):
                            continue

                    size_mb = os.path.getsize(full_path) / (1024 * 1024)
                    raw_stem = os.path.splitext(item)[0]

                    # Try serial lookup from raw filename (e.g. SLUS-20782 or [SLES-54245])
                    serial = normalize_serial(raw_stem)
                    title = self.db.get_title(serial) if serial else None
                    if not title:
                        title = self._clean_game_title(raw_stem)
                    clean_id = re.sub(r"[^a-zA-Z0-9_]", "_", title.lower())[:25]

                    game = LibraryGame(
                        id=f"{platform.lower()}_{clean_id}",
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

    def _scan_root_library(self, root_folder: str, existing_titles: Set[str]) -> List[LibraryGame]:
        """Scans root library folder for games placed directly without platform subfolders."""
        games: List[LibraryGame] = []
        known_subfolders = set(self.KNOWN_PLATFORMS.values())

        try:
            for item in sorted(os.listdir(root_folder)):
                full_path = os.path.join(root_folder, item)

                # Skip known platform folders (they are scanned individually)
                if os.path.isdir(full_path):
                    if item.lower() in known_subfolders:
                        continue

                    # Check for folder game placed in root Library
                    plat = self._detect_folder_platform(full_path)
                    if plat:
                        size_mb = self._get_folder_size_mb(full_path)
                        title = self._clean_game_title(item)
                        serial = None

                        if plat == "PS3":
                            sfo_path = os.path.join(full_path, "PS3_GAME", "PARAM.SFO")
                            if os.path.isfile(sfo_path):
                                try:
                                    with open(sfo_path, "rb") as f:
                                        params = self.identifier.parse_param_sfo(f.read())
                                    title = params.get("TITLE") or title
                                    serial = params.get("TITLE_ID")
                                except Exception:
                                    pass
                        clean_id = re.sub(r"[^a-zA-Z0-9_]", "_", title.lower())[:25]
                        games.append(LibraryGame(
                            id=f"{plat.lower()}_{clean_id}",
                            title=title,
                            platform=plat,
                            file_path=full_path,
                            file_size_mb=round(size_mb, 1),
                            format="FOLDER",
                            serial=serial
                        ))
                    continue

                # It is a file in root Library
                ext = os.path.splitext(item)[1].lower()
                raw_stem = os.path.splitext(item)[0]

                # Check for unextracted archive (.7z, .zip)
                if ext in (".7z", ".zip"):
                    clean_name = self._clean_game_title(raw_stem)
                    # If game is already indexed from extracted files, skip the archive
                    if clean_name.lower() in existing_titles:
                        continue

                    plat_hint = self._detect_archive_platform(full_path, item) or "XBOX360"
                    size_mb = os.path.getsize(full_path) / (1024 * 1024)
                    clean_id = re.sub(r"[^a-zA-Z0-9_]", "_", clean_name.lower())[:25]
                    games.append(LibraryGame(
                        id=f"{plat_hint.lower()}_{clean_id}",
                        title=clean_name,
                        platform=plat_hint,
                        file_path=full_path,
                        file_size_mb=round(size_mb, 1),
                        format=ext.lstrip(".").upper()
                    ))
                    existing_titles.add(clean_name.lower())
                    continue

                # Loose game file in root Library
                plat = self._detect_file_platform(full_path, item)
                if plat:
                    size_mb = os.path.getsize(full_path) / (1024 * 1024)
                    serial = normalize_serial(raw_stem)
                    title = self.db.get_title(serial) if serial else None
                    if not title:
                        title = self._clean_game_title(raw_stem)
                    clean_id = re.sub(r"[^a-zA-Z0-9_]", "_", title.lower())[:25]
                    games.append(LibraryGame(
                        id=f"{plat.lower()}_{clean_id}",
                        title=title,
                        platform=plat,
                        file_path=full_path,
                        file_size_mb=round(size_mb, 1),
                        format=ext.lstrip(".").upper(),
                        serial=serial
                    ))

        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error scanning root library {root_folder}: {e}")

        return games

    def _detect_folder_platform(self, folder_path: str) -> Optional[str]:
        """Detects console platform for an extracted game folder."""
        if os.path.isfile(os.path.join(folder_path, "PS3_DISC.SFB")) or os.path.isdir(os.path.join(folder_path, "PS3_GAME")):
            return "PS3"
        if os.path.isfile(os.path.join(folder_path, "default.xex")):
            return "XBOX360"
        if os.path.isfile(os.path.join(folder_path, "default.xbe")):
            return "XBOX"
        if os.path.isdir(os.path.join(folder_path, "sce_sys")) or os.path.isfile(os.path.join(folder_path, "eboot.bin")):
            return "PS4"

        # Check SYSTEM.CNF
        for item in os.listdir(folder_path):
            if item.upper() == "SYSTEM.CNF":
                try:
                    with open(os.path.join(folder_path, item), "r", errors="ignore") as f:
                        txt = f.read()
                    if "BOOT2" in txt:
                        return "PS2"
                    if "BOOT" in txt:
                        return "PS1"
                except Exception:
                    pass

        return None

    def _detect_file_platform(self, file_path: str, filename: str) -> Optional[str]:
        """Infers platform from filename, extension, companion metadata, or disc sectors."""
        ext = os.path.splitext(filename)[1].lower()

        ext_map = {
            ".z64": "N64", ".n64": "N64", ".v64": "N64",
            ".sfc": "SNES", ".smc": "SNES",
            ".gba": "GBA",
            ".rvz": "GAMECUBE", ".gcm": "GAMECUBE",
            ".wbfs": "WII",
            ".cdi": "DREAMCAST", ".gdi": "DREAMCAST",
            ".xex": "XBOX360",
            ".xbe": "XBOX",
            ".cso": "PSP", ".pbp": "PSP"
        }
        if ext in ext_map:
            return ext_map[ext]

        # Check serial pattern in filename
        norm_serial = normalize_serial(filename)
        if norm_serial:
            if any(norm_serial.startswith(p) for p in ("BLES", "BLUS", "BCES", "BCUS")):
                return "PS3"
            if norm_serial.startswith("CUSA"):
                return "PS4"
            if any(norm_serial.startswith(p) for p in ("ULUS", "ULES", "UCUS")):
                return "PSP"
            if any(norm_serial.startswith(p) for p in ("SLUS-2", "SLES-5", "SCES-5", "SLUS-20", "SLUS-21")):
                return "PS2"
            if any(norm_serial.startswith(p) for p in ("SLUS-0", "SLES-0", "SCES-0", "SCUS-9")):
                return "PS1"

        # Check companion text file (e.g., Vimm's Lair.txt or {game}.txt)
        folder = os.path.dirname(file_path)
        stem = os.path.splitext(filename)[0]
        for t_name in ("Vimm's Lair.txt", f"{stem}.txt"):
            tp = os.path.join(folder, t_name)
            if os.path.isfile(tp):
                try:
                    with open(tp, "r", errors="ignore") as f:
                        content = f.read()
                    if "Xbox 360" in content:
                        return "XBOX360"
                    if "PlayStation 3" in content:
                        return "PS3"
                    if "PlayStation 2" in content:
                        return "PS2"
                    if "PlayStation" in content:
                        return "PS1"
                    if "GameCube" in content:
                        return "GAMECUBE"
                    if "Wii" in content:
                        return "WII"
                except Exception:
                    pass

        # Inspect ISO sectors for PlayStation and Xbox
        if ext == ".iso":
            try:
                size_mb = os.path.getsize(file_path) / (1024 * 1024)
                with open(file_path, "rb") as f:
                    f.seek(0x8000)
                    pvd = f.read(2048)
                    if b"PS3_GAME" in pvd or b"PS3_DISC" in pvd:
                        return "PS3"
                    if b"SYSTEM.CNF" in pvd:
                        return "PS2" if size_mb > 700 else "PS1"
                    # Redump Xbox 360 images (XGD2/XGD3 typically > 7GB with standard UDF PVD)
                    if size_mb > 7000 and (b"CD001" in pvd or b"BEA01" in pvd or b"NSR02" in pvd or b"NSR03" in pvd):
                        return "XBOX360"
            except Exception:
                pass

        # Fallback to name inspection
        up_name = filename.upper()
        if "XBOX 360" in up_name or "XBOX360" in up_name:
            return "XBOX360"
        if "PS3" in up_name:
            return "PS3"
        if "PS2" in up_name:
            return "PS2"
        if "PS1" in up_name or "PSX" in up_name:
            return "PS1"
        if "XBOX" in up_name:
            return "XBOX"

        return None

    def _detect_archive_platform(self, archive_path: str, filename: str) -> Optional[str]:
        """Inspects archive contents or metadata to identify target console."""
        # Check archive tool
        tool = shutil.which("7zz") or shutil.which("7z")
        if tool:
            try:
                proc = subprocess.run(
                    [tool, "l", archive_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5
                )
                output = proc.stdout
                if "default.xex" in output:
                    return "XBOX360"
                if "PS3_GAME" in output or "PS3_DISC.SFB" in output:
                    return "PS3"
                if "default.xbe" in output:
                    return "XBOX"
                if "SYSTEM.CNF" in output:
                    return "PS2"
            except Exception:
                pass

        # Fallback to file name detection
        return self._detect_file_platform(archive_path, filename)

    def _auto_extract_archive(self, archive_path: str, platform: str) -> Optional[str]:
        """Extracts game archive to platform library folder if 7z is available."""
        tool = shutil.which("7zz") or shutil.which("7z")
        if not tool:
            return None

        target_dir = os.path.join(self.project_root, "Library", platform.lower())
        os.makedirs(target_dir, exist_ok=True)

        try:
            if self.logger:
                self.logger.info(f"Auto-extracting {archive_path} to {target_dir}...")
            subprocess.run(
                [tool, "x", archive_path, f"-o{target_dir}", "-y"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300
            )
            # Find the primary extracted game file
            for item in os.listdir(target_dir):
                if item.lower().endswith((".iso", ".xex", ".pkg")):
                    return os.path.join(target_dir, item)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Archive auto-extract failed for {archive_path}: {e}")

        return None

    def _get_folder_size_mb(self, folder: str) -> float:
        total = 0
        for dirpath, _, filenames in os.walk(folder):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total += os.path.getsize(fp)
        return total / (1024 * 1024)
