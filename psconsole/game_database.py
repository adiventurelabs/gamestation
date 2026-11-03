"""
PlayStation game database and serial resolver.
Maps game serials (e.g., SLUS-20062) to human-readable game titles for
controller-friendly UI notifications.
"""

import os
import re
import json
from typing import Optional, Dict

# Embedded database of major PS1 and PS2 titles across NTSC-U, PAL, and NTSC-J
KNOWN_TITLES: Dict[str, str] = {
    # --- Xbox 360 Classics ---
    "454109F8": "FIFA 18 - Legacy Edition",
    "454109EB": "FIFA 18 - Legacy Edition",
    "5451085D": "WWE SmackDown vs. Raw 2011",
    "5451085C": "WWE SmackDown vs. Raw 2011",
    "454109B6": "FIFA 14",
    "4D5307D5": "Gears of War",
    "4D53085B": "Halo 3",

    # --- PlayStation 1 Classics ---
    "SLUS-00067": "Castlevania: Symphony of the Night",
    "SLUS-00402": "Metal Gear Solid (Disc 1)",
    "SLUS-00424": "Metal Gear Solid (Disc 2)",
    "SLUS-00043": "Final Fantasy VII (Disc 1)",
    "SLUS-00044": "Final Fantasy VII (Disc 2)",
    "SLUS-00045": "Final Fantasy VII (Disc 3)",
    "SLUS-00892": "Final Fantasy VIII (Disc 1)",
    "SLUS-00908": "Final Fantasy VIII (Disc 2)",
    "SLUS-00909": "Final Fantasy VIII (Disc 3)",
    "SLUS-00910": "Final Fantasy VIII (Disc 4)",
    "SLUS-01251": "Final Fantasy IX (Disc 1)",
    "SLUS-01295": "Final Fantasy IX (Disc 2)",
    "SLUS-01296": "Final Fantasy IX (Disc 3)",
    "SLUS-01297": "Final Fantasy IX (Disc 4)",
    "SCUS-94163": "Gran Turismo",
    "SCUS-94455": "Gran Turismo 2 (Arcade Disc)",
    "SCUS-94488": "Gran Turismo 2 (Simulation Disc)",
    "SCUS-94900": "Crash Bandicoot",
    "SCUS-94154": "Crash Bandicoot 2: Cortex Strikes Back",
    "SCUS-94244": "Crash Bandicoot: Warped",
    "SCUS-94263": "Spyro the Dragon",
    "SCUS-94425": "Spyro 2: Ripto's Rage!",
    "SCUS-94467": "Spyro: Year of the Dragon",
    "SLUS-00566": "Resident Evil: Director's Cut",
    "SLUS-00747": "Resident Evil 2 (Leon Disc)",
    "SLUS-00756": "Resident Evil 2 (Claire Disc)",
    "SLUS-00923": "Resident Evil 3: Nemesis",
    "SLUS-00707": "Silent Hill",
    "SLUS-00588": "Parasite Eve (Disc 1)",
    "SLUS-00639": "Parasite Eve (Disc 2)",
    "SLUS-01042": "Chrono Cross (Disc 1)",
    "SLUS-01080": "Chrono Cross (Disc 2)",
    "SLUS-00005": "Tekken",
    "SLUS-00213": "Tekken 2",
    "SLUS-00402": "Tekken 3",
    "SLUS-00845": "Tony Hawk's Pro Skater",
    "SLUS-01066": "Tony Hawk's Pro Skater 2",
    "SLUS-00001": "Ridge Racer",
    "SLUS-00339": "Tomb Raider",
    "SLUS-00437": "Tomb Raider II",
    "SLUS-00742": "Tomb Raider III",
    "SCUS-94426": "Ape Escape",
    "SCUS-94482": "MediEvil II",
    "SCUS-94227": "MediEvil",
    "SLUS-00106": "WipEout",
    "SLUS-00570": "Xenogears (Disc 1)",
    "SLUS-00664": "Xenogears (Disc 2)",
    "SLUS-00880": "Driver",
    "SLUS-01161": "Driver 2 (Disc 1)",
    "SLUS-01318": "Driver 2 (Disc 2)",

    # --- PlayStation 2 Classics ---
    "SLUS-20062": "Final Fantasy X",
    "SLUS-20672": "Final Fantasy X-2",
    "SLUS-20963": "Final Fantasy XII",
    "SLUS-20144": "Metal Gear Solid 2: Sons of Liberty",
    "SLUS-20949": "Metal Gear Solid 3: Snake Eater",
    "SLUS-21359": "Metal Gear Solid 3: Subsistence (Disc 1)",
    "SLUS-20228": "Grand Theft Auto III",
    "SLUS-20552": "Grand Theft Auto: Vice City",
    "SLUS-20946": "Grand Theft Auto: San Andreas",
    "SCUS-97102": "Gran Turismo 3: A-Spec",
    "SCUS-97328": "Gran Turismo 4",
    "SCUS-97399": "God of War",
    "SCUS-97481": "God of War II (Disc 1)",
    "SCUS-97124": "Shadow of the Colossus",
    "SCUS-97113": "Ico",
    "SLUS-20370": "Kingdom Hearts",
    "SLUS-21005": "Kingdom Hearts II",
    "SLUS-20216": "Silent Hill 2",
    "SLUS-20622": "Silent Hill 3",
    "SLUS-20873": "Silent Hill 4: The Room",
    "SLUS-21134": "Resident Evil 4",
    "SLUS-20071": "Tekken Tag Tournament",
    "SLUS-20328": "Tekken 4",
    "SLUS-21063": "Tekken 5",
    "SLUS-20002": "SSX",
    "SLUS-20297": "SSX Tricky",
    "SLUS-20772": "SSX 3",
    "SCUS-97129": "Jak and Daxter: The Precursor Legacy",
    "SCUS-97213": "Jak II",
    "SCUS-97330": "Jak 3",
    "SCUS-97199": "Ratchet & Clank",
    "SCUS-97268": "Ratchet & Clank: Going Commando",
    "SCUS-97353": "Ratchet & Clank: Up Your Arsenal",
    "SCUS-97217": "Sly Cooper and the Thievius Raccoonus",
    "SCUS-97316": "Sly 2: Band of Thieves",
    "SCUS-97464": "Sly 3: Honor Among Thieves",
    "SLUS-20485": "Dragon Ball Z: Budokai",
    "SLUS-20790": "Dragon Ball Z: Budokai 2",
    "SLUS-20998": "Dragon Ball Z: Budokai 3",
    "SLUS-21441": "Dragon Ball Z: Budokai Tenkaichi 2",
    "SLUS-21670": "Dragon Ball Z: Budokai Tenkaichi 3",
    "SLUS-20072": "Dead or Alive 2",
    "SLUS-20173": "Twisted Metal: Black",
    "SLUS-20643": "Need for Speed: Underground",
    "SLUS-21065": "Need for Speed: Underground 2",
    "SLUS-21251": "Need for Speed: Most Wanted",
    "SLUS-20286": "Devil May Cry",
    "SLUS-20484": "Devil May Cry 2 (Dante Disc)",
    "SLUS-20627": "Devil May Cry 2 (Lucia Disc)",
    "SLUS-21113": "Devil May Cry 3: Dante's Awakening",
    "SLUS-21361": "Devil May Cry 3: Special Edition",
    "SLUS-20312": "Burnout",
    "SLUS-20489": "Burnout 2: Point of Impact",
    "SLUS-21050": "Burnout 3: Takedown",
    "SLUS-21250": "Burnout Revenge",
    "SLUS-20486": "Star Wars: Battlefront",
    "SLUS-21240": "Star Wars: Battlefront II",
    "SLUS-20898": "Katamari Damacy",
    "SLUS-21230": "We Love Katamari",
    "SLUS-21049": "Okami",
    "SLUS-20827": "Shin Megami Tensei: Nocturne",
    "SLUS-21569": "Shin Megami Tensei: Persona 3",
    "SLUS-21621": "Shin Megami Tensei: Persona 3 FES",
    "SLUS-21782": "Shin Megami Tensei: Persona 4",
    "SLUS-20014": "Armored Core 2",
    "SLUS-20565": "Zone of the Enders: The 2nd Runner",

    # --- PAL Favorites ---
    "SCES-00001": "Ridge Racer (PAL)",
    "SCES-01437": "Crash Bandicoot (PAL)",
    "SCES-50000": "Tekken Tag Tournament (PAL)",
    "SCES-50490": "Gran Turismo 3: A-Spec (PAL)",
    "SLES-50361": "Final Fantasy X (PAL)",
    "SLES-51156": "Grand Theft Auto: Vice City (PAL)",
    "SLES-52541": "Grand Theft Auto: San Andreas (PAL)",
    "SCES-51719": "God of War (PAL)",
    "SCES-54206": "God of War II (PAL)",

    # --- Sports & Wrestling Classics ---
    "SLUS-20782": "WWE SmackDown! Here Comes the Pain",
    "SLES-51824": "WWE SmackDown! Here Comes the Pain (PAL)",
    "SLUS-20412": "WWE SmackDown! Shut Your Mouth",
    "SLUS-21060": "WWE SmackDown! vs. RAW",
    "SLUS-21269": "WWE SmackDown! vs. RAW 2006",
    "SLUS-01046": "WWF SmackDown! 2: Know Your Role",
    "SLUS-00927": "WWF SmackDown!",
    "SLES-54245": "FIFA 07",
    "SLUS-21474": "FIFA 07",
    "SLES-55668": "FIFA 14",
    "SLUS-21956": "FIFA 14",
    "SLUS-00569": "FIFA 98: Road to World Cup",
    "SLES-00917": "FIFA 98: Road to World Cup (PAL)",
    "SLUS-00746": "FIFA 99",

    # --- Homebrew & Open Source Classics ---
    "240P-PS1": "240p Test Suite (PS1)",
    "240PTESTSUITEPS1-EMU": "240p Test Suite (PS1)",
    "FREEDVDBOOT-PS2-SLIM": "FreeDVDBoot Homebrew (PS2 Slim)",
    "NET-YAROZE-COLLECTION": "Net Yaroze Collection",
    "HERMES": "Hermes (PS2)"
}


def normalize_serial(raw_serial: str) -> str:
    """
    Normalizes disc serial strings from SYSTEM.CNF or executable names.
    Examples:
      'cdrom0:\\SLUS_200.62;1' -> 'SLUS-20062'
      'SLUS_200.62'           -> 'SLUS-20062'
      'slus-20062'            -> 'SLUS-20062'
      'SCES_000.01;1'         -> 'SCES-00001'
    """
    if not raw_serial:
        return ""

    # Strip cdrom prefixes, directory paths, and ;1 version suffixes
    clean = re.sub(r"^cdrom\d*:[\\/]*", "", raw_serial, flags=re.IGNORECASE)
    clean = re.sub(r";\d+$", "", clean)
    clean = os.path.basename(clean).upper()

    # Search for embedded Sony 4-letter prefix + digits format anywhere in string
    match_search = re.search(r"([A-Z]{4})[_\-](\d{5})", clean)
    if match_search:
        prefix, digits = match_search.groups()
        return f"{prefix}-{digits}"

    match_search2 = re.search(r"([A-Z]{4})[_\-]?(\d{3})[.]?(\d{2})", clean)
    if match_search2:
        prefix, part1, part2 = match_search2.groups()
        return f"{prefix}-{part1}{part2}"

    # Match standard Sony 4-letter prefix + digits format
    match = re.match(r"^([A-Z]{4})[_\-]?(\d{3})[.]?(\d{2})$", clean)
    if match:
        prefix, part1, part2 = match.groups()
        return f"{prefix}-{part1}{part2}"

    match2 = re.match(r"^([A-Z]{4})[_\-](\d{5})$", clean)
    if match2:
        prefix, digits = match2.groups()
        return f"{prefix}-{digits}"

    return clean.replace("_", "-")


class GameDatabase:
    """Provides fast title resolution and clean display names for PlayStation discs."""

    def __init__(self, custom_db_path: Optional[str] = None):
        self.db: Dict[str, str] = dict(KNOWN_TITLES)
        if custom_db_path and os.path.isfile(custom_db_path):
            try:
                with open(custom_db_path, "r", encoding="utf-8") as f:
                    extra = json.load(f)
                    for k, v in extra.items():
                        self.db[normalize_serial(k)] = str(v)
            except Exception:
                pass

    def get_title(self, serial: str) -> Optional[str]:
        """Lookup game title by serial string."""
        norm = normalize_serial(serial)
        return self.db.get(norm)

    def format_display_title(self, serial: Optional[str], disc_type: str, volume_label: Optional[str] = None) -> str:
        """
        Formats a friendly, console-grade display title.
        Returns the official title if found, or a clean fallback.
        """
        if serial:
            norm = normalize_serial(serial)
            title = self.db.get(norm)
            if title:
                return title

        if volume_label and volume_label.strip() and volume_label.upper() not in ("PLAYSTATION", "CDROM", "DVD_ROM", ""):
            clean_label = volume_label.replace("_", " ").title()
            return f"{clean_label} ({disc_type})"

        if serial:
            return f"{disc_type} Game ({normalize_serial(serial)})"

        return f"{disc_type} Game Disc"
