"""
PlayStation Disc Identifier.
Inspects physical optical disc filesystem contents, parses SYSTEM.CNF for PS1/PS2,
and PARAM.SFO for PS3/PS4, distinguishing PlayStation generations reliably.
"""

import os
import re
import struct
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List

from .game_database import GameDatabase, normalize_serial


class DiscType(Enum):
    PS1 = "PS1"
    PS2 = "PS2"
    PS3 = "PS3"
    PS4 = "PS4"
    XBOX = "XBOX"
    XBOX360 = "XBOX360"
    UNSUPPORTED_MEDIA = "UNSUPPORTED"
    UNREADABLE = "UNREADABLE"
    EMPTY = "EMPTY"


@dataclass
class DiscInfo:
    drive_path: str
    disc_type: DiscType
    serial: Optional[str] = None
    title: str = "Unknown Disc"
    executable: Optional[str] = None
    system_cnf: Dict[str, str] = field(default_factory=dict)
    sfo_params: Dict[str, str] = field(default_factory=dict)
    volume_label: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def is_playable(self) -> bool:
        return self.disc_type in (
            DiscType.PS1, DiscType.PS2, DiscType.PS3,
            DiscType.PS4, DiscType.XBOX, DiscType.XBOX360
        )

    @property
    def requires_ingestion(self) -> bool:
        return self.disc_type in (DiscType.XBOX, DiscType.XBOX360, DiscType.PS4)


class DiscIdentifier:
    """Analyzes mounted disc volumes to identify PlayStation generations and games."""

    def __init__(self, db: Optional[GameDatabase] = None):
        self.db = db or GameDatabase()

    def parse_system_cnf(self, content: str) -> Dict[str, str]:
        """
        Parses the key-value configuration pairs in a PlayStation SYSTEM.CNF file.
        Handles variations in spacing, casing, and line terminators.
        """
        config: Dict[str, str] = {}
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith(";"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                config[key.strip().upper()] = val.strip()
        return config

    def parse_param_sfo(self, data: bytes) -> Dict[str, str]:
        """
        Parses Sony PARAM.SFO metadata container used in PS3, PS4, and PSP media.
        Extracts TITLE, TITLE_ID, and CATEGORY.
        """
        params: Dict[str, str] = {}
        if len(data) < 20 or data[:4] != b"\x00PSF":
            return params

        try:
            key_table_start, data_table_start, num_entries = struct.unpack("<III", data[8:20])
            entry_offset = 20

            for _ in range(num_entries):
                if entry_offset + 16 > len(data):
                    break
                key_off, fmt, dlen, max_len, data_off = struct.unpack("<HHIII", data[entry_offset:entry_offset + 16])
                entry_offset += 16

                # Read null-terminated key from key table
                k_start = key_table_start + key_off
                k_end = data.find(b"\x00", k_start)
                if k_end == -1:
                    continue
                key = data[k_start:k_end].decode("latin-1", errors="ignore")

                # Read data
                d_start = data_table_start + data_off
                d_bytes = data[d_start:d_start + dlen]

                if fmt in (0x0204, 0x0004):  # String format (utf-8 / latin-1)
                    val = d_bytes.split(b"\x00")[0].decode("utf-8", errors="replace").strip()
                elif fmt == 0x0404:  # Integer
                    val = str(struct.unpack("<I", d_bytes)[0]) if len(d_bytes) >= 4 else ""
                else:
                    val = d_bytes.decode("latin-1", errors="replace").strip()

                params[key] = val
        except Exception:
            pass

        return params

    def find_file_case_insensitive(self, root_dir: str, target_filename: str) -> Optional[str]:
        """Finds a file in root directory regardless of casing or ISO9660 ;1 version tags."""
        try:
            if not os.path.exists(root_dir):
                return None
            target_clean = target_filename.upper().split(";")[0]
            for entry in os.listdir(root_dir):
                entry_clean = entry.upper().split(";")[0]
                if entry_clean == target_clean:
                    return os.path.join(root_dir, entry)
        except (PermissionError, OSError):
            return None
        return None

    def find_directory_case_insensitive(self, root_dir: str, target_dirname: str) -> bool:
        """Checks if a subdirectory exists with case insensitivity."""
        try:
            if not os.path.exists(root_dir):
                return False
            target_upper = target_dirname.upper()
            for entry in os.listdir(root_dir):
                if entry.upper() == target_upper and os.path.isdir(os.path.join(root_dir, entry)):
                    return True
        except (PermissionError, OSError):
            return False
        return False

    def identify_disc(self, drive_path: str, volume_label: Optional[str] = None) -> DiscInfo:
        """
        Inspects the mounted optical drive volume.
        Determines whether the disc is PS1, PS2, PS3, PS4, unsupported media, or unreadable.
        """
        drive_path = os.path.abspath(drive_path)

        if not os.path.exists(drive_path):
            return DiscInfo(
                drive_path=drive_path,
                disc_type=DiscType.EMPTY,
                error_message="Drive path does not exist or tray is open"
            )

        try:
            entries = os.listdir(drive_path)
        except PermissionError as e:
            return DiscInfo(
                drive_path=drive_path,
                disc_type=DiscType.UNREADABLE,
                error_message=f"Access denied reading optical drive: {e}"
            )
        except OSError as e:
            return DiscInfo(
                drive_path=drive_path,
                disc_type=DiscType.UNREADABLE,
                error_message=f"I/O error reading optical drive: {e}"
            )

        if not entries:
            return DiscInfo(
                drive_path=drive_path,
                disc_type=DiscType.UNSUPPORTED_MEDIA,
                title="Audio CD / Blank Disc",
                volume_label=volume_label,
                error_message="Audio CD or empty data track detected. Not a PlayStation game."
            )

        # 1. PlayStation 3 Check (PS3_DISC.SFB and PS3_GAME directory)
        ps3_sfb = self.find_file_case_insensitive(drive_path, "PS3_DISC.SFB")
        ps3_game_dir = os.path.join(drive_path, "PS3_GAME")
        if ps3_sfb or os.path.isdir(ps3_game_dir):
            title = "PlayStation 3 Game"
            serial = None
            sfo_data = {}

            sfo_path = os.path.join(ps3_game_dir, "PARAM.SFO")
            if os.path.isfile(sfo_path):
                try:
                    with open(sfo_path, "rb") as f:
                        sfo_data = self.parse_param_sfo(f.read())
                    title = sfo_data.get("TITLE") or title
                    serial = sfo_data.get("TITLE_ID")
                except Exception:
                    pass

            norm_serial = normalize_serial(serial) if serial else None
            return DiscInfo(
                drive_path=drive_path,
                disc_type=DiscType.PS3,
                serial=norm_serial,
                title=title,
                sfo_params=sfo_data,
                volume_label=volume_label
            )

        # 2. PlayStation 4 Check (sce_sys/param.sfo, CUSA volume labels, or eboot.bin)
        ps4_sce = os.path.join(drive_path, "sce_sys")
        ps4_eboot = self.find_file_case_insensitive(drive_path, "eboot.bin")
        clean_vol = (volume_label or "").upper()
        if os.path.isdir(ps4_sce) or ps4_eboot or ("CUSA" in clean_vol) or ("PS4" in clean_vol):
            title = "PlayStation 4 Title"
            serial = None
            sfo_data = {}
            sfo_path = os.path.join(ps4_sce, "param.sfo")
            if os.path.isfile(sfo_path):
                try:
                    with open(sfo_path, "rb") as f:
                        sfo_data = self.parse_param_sfo(f.read())
                    title = sfo_data.get("TITLE") or title
                    serial = sfo_data.get("TITLE_ID")
                except Exception:
                    pass

            if not serial and "CUSA" in clean_vol:
                match = re.search(r"CUSA[-_]?\d{5}", clean_vol)
                if match:
                    serial = match.group(0).replace("_", "-")

            return DiscInfo(
                drive_path=drive_path,
                disc_type=DiscType.PS4,
                serial=normalize_serial(serial) if serial else None,
                title=title if title != "PlayStation 4 Title" else (volume_label or "PlayStation 4 Game"),
                sfo_params=sfo_data,
                volume_label=volume_label
            )

        # 3. Xbox 360 Check (default.xex, $SystemUpdate, or XBOX360 volume label)
        has_default_xex = bool(self.find_file_case_insensitive(drive_path, "default.xex"))
        has_sys_update = self.find_directory_case_insensitive(drive_path, "$SystemUpdate")
        if has_default_xex or has_sys_update or ("XBOX360" in clean_vol) or ("XBOX 360" in clean_vol):
            title = f"Xbox 360 Game: {volume_label}" if volume_label else "Xbox 360 Game"
            return DiscInfo(
                drive_path=drive_path,
                disc_type=DiscType.XBOX360,
                title=title,
                executable="default.xex" if has_default_xex else None,
                volume_label=volume_label
            )

        # 4. Xbox (Original) Check (default.xbe or XBOX volume label)
        has_default_xbe = bool(self.find_file_case_insensitive(drive_path, "default.xbe"))
        if has_default_xbe or ("XBOX" in clean_vol and "360" not in clean_vol):
            title = f"Xbox Game: {volume_label}" if volume_label else "Xbox Game"
            return DiscInfo(
                drive_path=drive_path,
                disc_type=DiscType.XBOX,
                title=title,
                executable="default.xbe" if has_default_xbe else None,
                volume_label=volume_label
            )

        # 5. PlayStation 1 & 2 Check via SYSTEM.CNF
        system_cnf_path = self.find_file_case_insensitive(drive_path, "SYSTEM.CNF")
        if system_cnf_path and os.path.isfile(system_cnf_path):
            try:
                with open(system_cnf_path, "r", encoding="latin-1", errors="replace") as f:
                    raw_content = f.read()
                cnf = self.parse_system_cnf(raw_content)

                # PS2 uses BOOT2 = cdrom0:\...
                if "BOOT2" in cnf:
                    boot_target = cnf["BOOT2"]
                    serial = normalize_serial(boot_target)
                    title = self.db.format_display_title(serial, "PlayStation 2", volume_label)
                    return DiscInfo(
                        drive_path=drive_path,
                        disc_type=DiscType.PS2,
                        serial=serial,
                        title=title,
                        executable=boot_target,
                        system_cnf=cnf,
                        volume_label=volume_label
                    )

                # PS1 uses BOOT = cdrom:\...
                if "BOOT" in cnf:
                    boot_target = cnf["BOOT"]
                    serial = normalize_serial(boot_target)
                    title = self.db.format_display_title(serial, "PlayStation", volume_label)
                    return DiscInfo(
                        drive_path=drive_path,
                        disc_type=DiscType.PS1,
                        serial=serial,
                        title=title,
                        executable=boot_target,
                        system_cnf=cnf,
                        volume_label=volume_label
                    )

            except Exception as e:
                return DiscInfo(
                    drive_path=drive_path,
                    disc_type=DiscType.UNREADABLE,
                    volume_label=volume_label,
                    error_message=f"Failed to parse SYSTEM.CNF: {e}"
                )

        # 4. Early PS1 discs without SYSTEM.CNF often have PSX.EXE
        psx_exe = self.find_file_case_insensitive(drive_path, "PSX.EXE")
        if psx_exe:
            serial = self._scan_for_serial_file(entries)
            title = self.db.format_display_title(serial, "PlayStation", volume_label)
            return DiscInfo(
                drive_path=drive_path,
                disc_type=DiscType.PS1,
                serial=serial,
                title=title,
                executable="PSX.EXE",
                volume_label=volume_label
            )

        # 5. Non-game media checks (DVD-Video, PC disc, Audio)
        if self.find_directory_case_insensitive(drive_path, "VIDEO_TS"):
            return DiscInfo(
                drive_path=drive_path,
                disc_type=DiscType.UNSUPPORTED_MEDIA,
                title="DVD-Video Movie",
                volume_label=volume_label,
                error_message="DVD-Video movie disc inserted. Not a playable PlayStation game."
            )

        # Fallback root Sony serial scan
        serial = self._scan_for_serial_file(entries)
        if serial:
            is_ps2_serial = any(p in serial for p in ("20", "21", "50", "51", "52", "53", "54", "97"))
            disc_type = DiscType.PS2 if is_ps2_serial else DiscType.PS1
            gen_name = "PlayStation 2" if disc_type == DiscType.PS2 else "PlayStation"
            title = self.db.format_display_title(serial, gen_name, volume_label)
            return DiscInfo(
                drive_path=drive_path,
                disc_type=disc_type,
                serial=serial,
                title=title,
                volume_label=volume_label
            )

        # 7. Unknown / Unsupported Media
        return DiscInfo(
            drive_path=drive_path,
            disc_type=DiscType.UNSUPPORTED_MEDIA,
            title="Unsupported Disc",
            volume_label=volume_label,
            error_message="Inserted disc is not recognized as a supported PlayStation or Xbox console game disc."
        )

    def _scan_for_serial_file(self, file_entries: List[str]) -> Optional[str]:
        """Scans file list in root for standard Sony executable naming (e.g. SLUS_200.62)."""
        pattern = re.compile(r"^(S[CL][UEP][SAM])_(\d{3})\.(\d{2})(?:;\d+)?$", re.IGNORECASE)
        for entry in file_entries:
            match = pattern.match(entry)
            if match:
                prefix, num1, num2 = match.groups()
                return f"{prefix.upper()}-{num1}{num2}"
        return None
