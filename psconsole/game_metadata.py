"""
GameStation Metadata & Cover Art Manager.
Provides rich game metadata (genres, player counts, developers, descriptions,
and release years) and manages local/online cover art resolution with
high-performance disk caching for large libraries (local NVMe and network SMB/NAS).
"""

import os
import re
import json
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any


# Curated high-fidelity metadata for library games
KNOWN_METADATA: Dict[str, Dict[str, Any]] = {
    "call of duty - modern warfare 3": {
        "title": "Call of Duty: Modern Warfare 3",
        "cover_art": "/covers/cod_mw3.png",
        "genre": "First-Person Shooter / Military Action",
        "players": "1-4 Players (Split-Screen Spec Ops & Versus)",
        "developer": "Infinity Ward / Sledgehammer Games",
        "publisher": "Activision",
        "release_year": "2011",
        "rating": "ESRB: Mature (17+)",
        "description": "The world stands on the brink of destruction. Join Captain Price, Soap MacTavish, and Delta Force across New York, London, Paris, and Berlin in the explosive climax to the original Modern Warfare trilogy with legendary split-screen Survival and Spec Ops modes."
    },
    "call of duty: modern warfare 3": {
        "title": "Call of Duty: Modern Warfare 3",
        "cover_art": "/covers/cod_mw3.png",
        "genre": "First-Person Shooter / Military Action",
        "players": "1-4 Players (Split-Screen Spec Ops & Versus)",
        "developer": "Infinity Ward / Sledgehammer Games",
        "publisher": "Activision",
        "release_year": "2011",
        "rating": "ESRB: Mature (17+)",
        "description": "The world stands on the brink of destruction. Join Captain Price, Soap MacTavish, and Delta Force across New York, London, Paris, and Berlin in the explosive climax to the original Modern Warfare trilogy with legendary split-screen Survival and Spec Ops modes."
    },
    "modern warfare 3": {
        "title": "Call of Duty: Modern Warfare 3",
        "cover_art": "/covers/cod_mw3.png",
        "genre": "First-Person Shooter / Military Action",
        "players": "1-4 Players (Split-Screen Spec Ops & Versus)",
        "developer": "Infinity Ward / Sledgehammer Games",
        "publisher": "Activision",
        "release_year": "2011",
        "rating": "ESRB: Mature (17+)",
        "description": "The world stands on the brink of destruction. Join Captain Price, Soap MacTavish, and Delta Force across New York, London, Paris, and Berlin in the explosive climax to the original Modern Warfare trilogy with legendary split-screen Survival and Spec Ops modes."
    },
    "dragon ball z - budokai hd collection": {
        "title": "Dragon Ball Z: Budokai HD Collection",
        "cover_art": "/covers/dbz_budokai_hd.jpg",
        "genre": "Anime / Fighting / 3D Versus",
        "players": "1-2 Players (Local Versus & World Tournament)",
        "developer": "Dimps",
        "publisher": "Bandai Namco Games",
        "release_year": "2012",
        "rating": "ESRB: Teen",
        "description": "Relive the golden era of Dragon Ball Z fighting games. Includes both Dragon Ball Z Budokai and Dragon Ball Z Budokai 3 completely remastered in high definition with 60 FPS combat."
    },
    "dragon ball z: budokai hd collection": {
        "title": "Dragon Ball Z: Budokai HD Collection",
        "cover_art": "/covers/dbz_budokai_hd.jpg",
        "genre": "Anime / Fighting / 3D Versus",
        "players": "1-2 Players (Local Versus & World Tournament)",
        "developer": "Dimps",
        "publisher": "Bandai Namco Games",
        "release_year": "2012",
        "rating": "ESRB: Teen",
        "description": "Relive the golden era of Dragon Ball Z fighting games. Includes both Dragon Ball Z Budokai and Dragon Ball Z Budokai 3 completely remastered in high definition with 60 FPS combat."
    },
    "call of duty - advanced warfare": {
        "title": "Call of Duty: Advanced Warfare",
        "cover_art": "/covers/cod_advanced_warfare.jpg",
        "genre": "First-Person Shooter / Sci-Fi Military",
        "players": "1-2 Players (Split-Screen Co-op & Exo Survival)",
        "developer": "Sledgehammer Games / High Moon Studios",
        "publisher": "Activision",
        "release_year": "2014",
        "rating": "ESRB: Mature (17+)",
        "description": "Enter a future dominated by Private Military Corporations. Power up with advanced exoskeletons for boosted jumps, cloaking, and high-speed split-screen living room combat starring Kevin Spacey."
    },
    "call of duty: advanced warfare": {
        "title": "Call of Duty: Advanced Warfare",
        "cover_art": "/covers/cod_advanced_warfare.jpg",
        "genre": "First-Person Shooter / Sci-Fi Military",
        "players": "1-2 Players (Split-Screen Co-op & Exo Survival)",
        "developer": "Sledgehammer Games / High Moon Studios",
        "publisher": "Activision",
        "release_year": "2014",
        "rating": "ESRB: Mature (17+)",
        "description": "Enter a future dominated by Private Military Corporations. Power up with advanced exoskeletons for boosted jumps, cloaking, and high-speed split-screen living room combat starring Kevin Spacey."
    },
    "wwe 2k17": {
        "title": "WWE 2K17",
        "cover_art": "/covers/wwe_2k17.jpg",
        "genre": "Sports / Pro Wrestling",
        "players": "1-4 Players (Local Versus, Tag Team & Royal Rumble)",
        "developer": "Yuke's / Visual Concepts",
        "publisher": "2K Sports",
        "release_year": "2016",
        "rating": "ESRB: Teen",
        "description": "Welcome to Suplex City, courtesy of cover Superstar Brock Lesnar! Features thousands of new moves, backstage brawling, and massive 1-4 player living room wrestling showdowns."
    },
    "naruto shippuden - ultimate ninja storm 3 full burst": {
        "title": "Naruto Shippuden: Ultimate Ninja Storm 3 Full Burst",
        "cover_art": "/covers/naruto_storm_3.jpg",
        "genre": "Anime / Fighting / 3D Versus",
        "players": "1-2 Players (Local Versus & Tournament)",
        "developer": "CyberConnect2",
        "publisher": "Bandai Namco Games",
        "release_year": "2013",
        "rating": "ESRB: Teen",
        "description": "The Fourth Great Ninja War reaches its epic climax. Relive iconic anime battles against the Akatsuki, Nine-Tails, and the legendary Madara Uchiha in intense living room ninja combat."
    },
    "naruto shippuden: ultimate ninja storm 3 full burst": {
        "title": "Naruto Shippuden: Ultimate Ninja Storm 3 Full Burst",
        "cover_art": "/covers/naruto_storm_3.jpg",
        "genre": "Anime / Fighting / 3D Versus",
        "players": "1-2 Players (Local Versus & Tournament)",
        "developer": "CyberConnect2",
        "publisher": "Bandai Namco Games",
        "release_year": "2013",
        "rating": "ESRB: Teen",
        "description": "The Fourth Great Ninja War reaches its epic climax. Relive iconic anime battles against the Akatsuki, Nine-Tails, and the legendary Madara Uchiha in intense living room ninja combat."
    },
    "super smash bros. for wii u": {
        "title": "Super Smash Bros. for Wii U",
        "cover_art": "/covers/smash_wiiu.jpg",
        "genre": "Platform Fighter / Party",
        "players": "1-8 Players (8-Player Local Smash)",
        "developer": "Bandai Namco Games / Sora Ltd.",
        "publisher": "Nintendo",
        "release_year": "2014",
        "rating": "ESRB: Everyone 10+",
        "description": "Battle across iconic Nintendo worlds with Mario, Link, Pikachu, Sonic, Mega Man, and Pac-Man. Supports legendary 8-player local living room mayhem on Wii U."
    },
    "super smash bros for wii u": {
        "title": "Super Smash Bros. for Wii U",
        "cover_art": "/covers/smash_wiiu.jpg",
        "genre": "Platform Fighter / Party",
        "players": "1-8 Players (8-Player Local Smash)",
        "developer": "Bandai Namco Games / Sora Ltd.",
        "publisher": "Nintendo",
        "release_year": "2014",
        "rating": "ESRB: Everyone 10+",
        "description": "Battle across iconic Nintendo worlds with Mario, Link, Pikachu, Sonic, Mega Man, and Pac-Man. Supports legendary 8-player local living room mayhem on Wii U."
    },
    "far cry 4": {
        "title": "Far Cry 4",
        "cover_art": "/covers/far_cry_4.jpg",
        "genre": "First-Person Shooter / Open World",
        "players": "1-2 Players (Drop-in Co-op)",
        "developer": "Ubisoft Montreal",
        "publisher": "Ubisoft",
        "release_year": "2014",
        "rating": "ESRB: Mature (17+)",
        "description": "Hidden in the towering Himalayas lies Kyrat, a country steeped in tradition and violence. You are Ajay Ghale, traveling to Kyrat to fulfill your mother's dying wish, only to find yourself caught in a civil war to overthrow the despotic regime of Pagan Min."
    },
    "halo 4": {
        "title": "Halo 4",
        "cover_art": "/covers/halo_4.jpg",
        "genre": "First-Person Shooter / Sci-Fi",
        "players": "1-4 Players (Split-Screen Co-op & War Games)",
        "developer": "343 Industries",
        "publisher": "Microsoft Studios",
        "release_year": "2012",
        "rating": "ESRB: Mature (17+)",
        "description": "The Master Chief returns to face his own destiny and an ancient evil that threatens the fate of the entire universe. Shipwrecked on a mysterious Forerunner world with Cortana, battle Promethean knights and unravel ancient galactic secrets."
    },
    "halo 4 (disc 1)": {
        "title": "Halo 4 (Disc 1 - Campaign)",
        "cover_art": "/covers/halo_4.jpg",
        "genre": "First-Person Shooter / Sci-Fi",
        "players": "1-4 Players (Split-Screen Co-op)",
        "developer": "343 Industries",
        "publisher": "Microsoft Studios",
        "release_year": "2012",
        "rating": "ESRB: Mature (17+)",
        "description": "The Master Chief awakens aboard the Forward Unto Dawn to defend Cortana against Covenant remnants and the awakening Didact in the epic single-player and co-op campaign."
    },
    "halo 4 (disc 2)": {
        "title": "Halo 4 (Disc 2 - War Games & Spartan Ops)",
        "cover_art": "/covers/halo_4.jpg",
        "genre": "First-Person Shooter / Multiplayer",
        "players": "1-4 Players (Split-Screen War Games)",
        "developer": "343 Industries",
        "publisher": "Microsoft Studios",
        "release_year": "2012",
        "rating": "ESRB: Mature (17+)",
        "description": "War Games competitive multiplayer and episodic Spartan Ops cooperative missions on the UNSC Infinity combat deck."
    },
    "assassin's creed iv - black flag": {
        "title": "Assassin's Creed IV - Black Flag",
        "cover_art": "/covers/ac4.jpg",
        "genre": "Action-Adventure / Open World",
        "players": "1 Player",
        "developer": "Ubisoft Montreal",
        "publisher": "Ubisoft",
        "release_year": "2013",
        "rating": "ESRB: Mature (17+)",
        "description": "Sail the high seas of the Caribbean as Edward Kenway during the Golden Age of Piracy. Explore over 50 unique tropical locations, plunder ships in naval combat, and duel with hidden blades."
    },
    "assassin's creed iv": {
        "title": "Assassin's Creed IV - Black Flag",
        "cover_art": "/covers/ac4.jpg",
        "genre": "Action-Adventure / Open World",
        "players": "1 Player",
        "developer": "Ubisoft Montreal",
        "publisher": "Ubisoft",
        "release_year": "2013",
        "rating": "ESRB: Mature (17+)",
        "description": "Sail the high seas of the Caribbean as Edward Kenway during the Golden Age of Piracy. Explore over 50 unique tropical locations, plunder ships in naval combat, and duel with hidden blades."
    },
    "blus31159": {
        "title": "Assassin's Creed IV - Black Flag",
        "cover_art": "/covers/ac4.jpg",
        "genre": "Action-Adventure / Open World",
        "players": "1 Player",
        "developer": "Ubisoft Montreal",
        "publisher": "Ubisoft",
        "release_year": "2013",
        "rating": "ESRB: Mature (17+)",
        "description": "Sail the high seas of the Caribbean as Edward Kenway during the Golden Age of Piracy. Explore over 50 unique tropical locations, plunder ships in naval combat, and duel with hidden blades."
    },
    "fifa 18 - legacy edition": {
        "title": "FIFA 18 - Legacy Edition",
        "cover_art": "/covers/fifa_18.jpg",
        "genre": "Sports / Football",
        "players": "1-4 Players (Local Versus & Co-op)",
        "developer": "EA Canada",
        "publisher": "EA Sports",
        "release_year": "2017",
        "rating": "ESRB: Everyone",
        "description": "Experience the world's game on Xbox 360 with authentic kits, clubs, broadcast packaging, and intense 1-4 player couch multiplayer football."
    },
    "wwe smackdown vs. raw 2011": {
        "title": "WWE SmackDown vs. Raw 2011",
        "cover_art": "/covers/wwe_2011.jpg",
        "genre": "Sports / Pro Wrestling",
        "players": "1-4 Players (Local Versus & Royal Rumble)",
        "developer": "Yuke's",
        "publisher": "THQ",
        "release_year": "2010",
        "rating": "ESRB: Teen",
        "description": "WWE SmackDown vs. Raw 2011 empowers players to control their destiny with dynamic Havok physics, WWE Universe mode, and epic 1-4 player living room wrestling."
    },
    "fifa 14": {
        "title": "FIFA 14",
        "cover_art": "/covers/fifa_14.jpg",
        "genre": "Sports / Football",
        "players": "1-4 Players (Local Versus & Co-op)",
        "developer": "EA Canada",
        "publisher": "EA Sports",
        "release_year": "2013",
        "rating": "ESRB: Everyone",
        "description": "Feel the emotion of scoring great goals with Pure Shot ball physics, authentic tactical defending, and legendary couch multiplayer matches."
    },
    "fifa 14 xbox360": {
        "title": "FIFA 14",
        "cover_art": "/covers/fifa_14.jpg",
        "genre": "Sports / Football",
        "players": "1-4 Players (Local Versus & Co-op)",
        "developer": "EA Canada",
        "publisher": "EA Sports",
        "release_year": "2013",
        "rating": "ESRB: Everyone",
        "description": "Feel the emotion of scoring great goals with Pure Shot ball physics, authentic tactical defending, and legendary couch multiplayer matches."
    },
    "xbox 360 game gears of war": {
        "title": "Gears of War",
        "cover_art": "/covers/gears_of_war.jpg",
        "genre": "Shooter / Action",
        "players": "1-2 Players (Split-Screen Co-op)",
        "developer": "Epic Games",
        "publisher": "Microsoft Game Studios",
        "release_year": "2006",
        "rating": "ESRB: Mature (17+)",
        "description": "Marcus Fenix and Delta Squad fight for humanity's survival against the Locust Horde in this genre-defining cinematic cover-based shooter."
    },
    "gears of war": {
        "title": "Gears of War",
        "cover_art": "/covers/gears_of_war.jpg",
        "genre": "Shooter / Action",
        "players": "1-2 Players (Split-Screen Co-op)",
        "developer": "Epic Games",
        "publisher": "Microsoft Game Studios",
        "release_year": "2006",
        "rating": "ESRB: Mature (17+)",
        "description": "Marcus Fenix and Delta Squad fight for humanity's survival against the Locust Horde in this genre-defining cinematic cover-based shooter."
    },
    "xbox game halo 2": {
        "title": "Halo 2",
        "cover_art": "/covers/halo_2.jpg",
        "genre": "First-Person Shooter",
        "players": "1-4 Players (Split-Screen Versus & Co-op)",
        "developer": "Bungie",
        "publisher": "Microsoft Game Studios",
        "release_year": "2004",
        "rating": "ESRB: Mature (17+)",
        "description": "The Master Chief defends Earth against the alien Covenant invasion with dual-wielding, vehicle warfare, and iconic 4-player living room combat."
    },
    "halo 2": {
        "title": "Halo 2",
        "cover_art": "/covers/halo_2.jpg",
        "genre": "First-Person Shooter",
        "players": "1-4 Players (Split-Screen Versus & Co-op)",
        "developer": "Bungie",
        "publisher": "Microsoft Game Studios",
        "release_year": "2004",
        "rating": "ESRB: Mature (17+)",
        "description": "The Master Chief defends Earth against the alien Covenant invasion with dual-wielding, vehicle warfare, and iconic 4-player living room combat."
    },
    "wwf raw": {
        "title": "WWF Raw",
        "cover_art": "/covers/wwf_raw.jpg",
        "genre": "Sports / Pro Wrestling",
        "players": "1-4 Players (Local Versus)",
        "developer": "Anchor Inc.",
        "publisher": "THQ",
        "release_year": "2002",
        "rating": "ESRB: Teen",
        "description": "High-octane Attitude Era wrestling featuring The Rock, Stone Cold Steve Austin, Undertaker, and Triple H in intense 4-player matchups."
    },
    "fifa 07": {
        "title": "FIFA 07",
        "cover_art": "/covers/fifa_07.jpg",
        "genre": "Sports / Football",
        "players": "1-4 Players (Local Versus & Co-op)",
        "developer": "EA Canada",
        "publisher": "EA Sports",
        "release_year": "2006",
        "rating": "ESRB: Everyone",
        "description": "Classic PlayStation 2 football featuring over 510 licensed teams, realistic ball trajectory physics, and fluid passing."
    },
    "wwe smackdown! here comes the pain": {
        "title": "WWE SmackDown! Here Comes the Pain",
        "cover_art": "/covers/wwe_pain.png",
        "genre": "Sports / Pro Wrestling",
        "players": "1-4 Players (Local Versus & Elimination Chamber)",
        "developer": "Yuke's",
        "publisher": "THQ",
        "release_year": "2003",
        "rating": "ESRB: Teen",
        "description": "The undisputed king of arcade wrestling games. Features devastating grapples, backstage brawling, and legendary 4-player multiplayer."
    },
    "demon's souls": {
        "title": "Demon's Souls",
        "cover_art": "/covers/demons_souls.jpg",
        "genre": "Action RPG / Dark Fantasy",
        "players": "1 Player",
        "developer": "FromSoftware",
        "publisher": "Sony Computer Entertainment",
        "release_year": "2009",
        "rating": "ESRB: Mature (17+)",
        "description": "FromSoftware's groundbreaking dark fantasy action RPG. Venture through the kingdom of Boletaria and conquer brutal demonic challenges."
    },
    "bloodborne": {
        "title": "Bloodborne",
        "cover_art": "/covers/bloodborne.jpg",
        "genre": "Action RPG / Gothic Horror",
        "players": "1 Player",
        "developer": "FromSoftware",
        "publisher": "Sony Computer Entertainment",
        "release_year": "2015",
        "rating": "ESRB: Mature (17+)",
        "description": "Hunt your nightmares in the ancient gothic city of Yharnam. Fast-paced visceral combat, transforming trick weapons, and cosmic mysteries."
    },
    "grand theft auto - liberty city stories": {
        "title": "Grand Theft Auto - Liberty City Stories",
        "cover_art": "/covers/gta_lcs.jpg",
        "genre": "Open World / Action",
        "players": "1 Player",
        "developer": "Rockstar Leeds / North",
        "publisher": "Rockstar Games",
        "release_year": "2005",
        "rating": "ESRB: Mature (17+)",
        "description": "Return to Liberty City as Toni Cipriani, rising through the ranks of the Leone crime family in a sprawling open world."
    },
    "super smash bros. melee": {
        "title": "Super Smash Bros. Melee",
        "cover_art": "/covers/smash_melee.png",
        "genre": "Platform Fighter",
        "players": "1-4 Players (Local Versus & Free-For-All)",
        "developer": "HAL Laboratory",
        "publisher": "Nintendo",
        "release_year": "2001",
        "rating": "ESRB: Teen",
        "description": "The definitive competitive platform fighter. 26 iconic Nintendo all-stars battle in fast, high-flying 4-player living room showdowns."
    },
    "crazy taxi": {
        "title": "Crazy Taxi",
        "cover_art": "/covers/crazy_taxi.png",
        "genre": "Arcade Driving",
        "players": "1 Player",
        "developer": "Hitmaker",
        "publisher": "Sega",
        "release_year": "2000",
        "rating": "ESRB: Teen",
        "description": "Hey hey, come on over and have some fun with Crazy Taxi! Weave through traffic, pull crazy stunts, and deliver frantic passengers in record time."
    },
    "hermes (ps2)": {
        "title": "Hermes (PS2)",
        "cover_art": "/covers/hermes.svg",
        "genre": "Arcade Platformer",
        "players": "1-2 Players",
        "developer": "Retroguru",
        "publisher": "Homebrew Community",
        "release_year": "2017",
        "rating": "All Ages",
        "description": "A charming retro arcade platformer following chef Hermes as he chases down delicious culinary ingredients across colorful levels."
    },
    "freedvdboot homebrew (ps2 slim)": {
        "title": "FreeDVDBoot Homebrew (PS2 Slim)",
        "cover_art": "/covers/freedvdboot.svg",
        "genre": "System Utility",
        "players": "System Tool",
        "developer": "CTurt",
        "publisher": "PS2 Scene",
        "release_year": "2020",
        "rating": "All Ages",
        "description": "Innovative optical DVD exploit enabling autonomous homebrew booting on unmodded PlayStation 2 Slim hardware."
    },
    "net yaroze collection": {
        "title": "Net Yaroze Collection",
        "cover_art": "/covers/net_yaroze.svg",
        "genre": "Indie Collection",
        "players": "1-2 Players",
        "developer": "Indie Developers",
        "publisher": "Sony Computer Entertainment",
        "release_year": "1997",
        "rating": "All Ages",
        "description": "Legendary collection of creative homebrew games developed on Sony's black Net Yaroze PlayStation hobbyist platform."
    },
    "240p test suite (ps1)": {
        "title": "240p Test Suite (PS1)",
        "cover_art": "/covers/test_suite_240p.svg",
        "genre": "Video Calibration",
        "players": "Calibration Tool",
        "developer": "Artemio Urbina",
        "publisher": "240p Suite Project",
        "release_year": "2014",
        "rating": "All Ages",
        "description": "Essential CRT and scaler video calibration tool to benchmark display timing, 240p linearity, and audio-video synchronization."
    }
}


class GameMetadataManager:
    """Resolves and caches rich metadata and box art for console games."""

    def __init__(self, project_root: str, logger=None):
        self.project_root = project_root
        self.logger = logger
        self.covers_dir = os.path.join(self.project_root, "psconsole", "dashboard", "static", "covers")
        os.makedirs(self.covers_dir, exist_ok=True)

    def resolve_game_metadata(
        self,
        title: str,
        platform: str,
        file_path: str,
        serial: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enriches a game with cover art, genre, player counts, developer, and synopsis.
        Checks curated database, local folder art, and cached box arts.
        """
        clean_key = re.sub(r"[™®©]", "", title).strip().lower()

        # 1. Check curated dictionary
        meta = KNOWN_METADATA.get(clean_key)
        if not meta:
            # Try normalized key match (ignoring punctuation, spaces, and trademark symbols)
            norm_key = re.sub(r"[^a-z0-9]", "", clean_key)
            for k, v in KNOWN_METADATA.items():
                norm_k = re.sub(r"[^a-z0-9]", "", k)
                if norm_k == norm_key or (len(norm_k) > 6 and (norm_k in norm_key or norm_key in norm_k)):
                    meta = v
                    break

        result: Dict[str, Any] = {
            "cover_art": None,
            "hero_art": None,
            "genre": None,
            "players": None,
            "developer": None,
            "publisher": None,
            "release_year": None,
            "rating": None,
            "description": None
        }

        if meta:
            result.update(meta)

        # 2. Check local alongside box art (e.g., cover.jpg, folder.jpg, {gamename}.jpg)
        local_cover = self._find_local_cover(file_path)
        if local_cover:
            # Copy or link local cover to static/covers if not already there
            cached_name = f"local_{abs(hash(file_path))}.jpg"
            cached_path = os.path.join(self.covers_dir, cached_name)
            if not os.path.exists(cached_path):
                try:
                    with open(local_cover, "rb") as sf, open(cached_path, "wb") as df:
                        df.write(sf.read())
                except Exception:
                    pass
            result["cover_art"] = f"/covers/{cached_name}"

        # 3. If cover_art still missing, check static/covers by filename or serial
        if not result.get("cover_art"):
            result["cover_art"] = self._match_existing_cover(title, serial)

        # 4. Default player count heuristics if missing
        if not result.get("players"):
            up = title.upper()
            if any(w in up for w in ("FIFA", "WWE", "WWF", "SMASH", "BRAWL", "MARIO KART", "HALO", "NBA", "NFL", "TEKKEN")):
                result["players"] = "1-4 Players (Local Multiplayer)"
            else:
                result["players"] = "1 Player"

        if not result.get("description"):
            result["description"] = f"Original {platform} title available in your GameStation library. Ready to play."

        return result

    def _find_local_cover(self, game_file_path: str) -> Optional[str]:
        """Checks for alongside cover art files in the game's directory."""
        if not game_file_path or not os.path.exists(game_file_path):
            return None

        folder = os.path.dirname(game_file_path) if os.path.isfile(game_file_path) else game_file_path
        stem = os.path.splitext(os.path.basename(game_file_path))[0].lower()

        candidates = [
            "cover.jpg", "cover.png", "cover.webp",
            "folder.jpg", "folder.png",
            "front.jpg", "front.png",
            "boxart.jpg", "boxart.png",
            f"{stem}.jpg", f"{stem}.png"
        ]

        for cand in candidates:
            fp = os.path.join(folder, cand)
            if os.path.isfile(fp):
                return fp

        return None

    def _match_existing_cover(self, title: str, serial: Optional[str]) -> Optional[str]:
        """Checks if a matching cover image already exists in the covers directory."""
        clean = re.sub(r"[^a-zA-Z0-9]", "_", title.lower()).strip("_")
        for ext in (".jpg", ".png", ".svg", ".webp"):
            if os.path.isfile(os.path.join(self.covers_dir, f"{clean}{ext}")):
                return f"/covers/{clean}{ext}"

        if serial:
            norm_s = serial.replace("-", "").lower()
            for ext in (".jpg", ".png", ".webp"):
                if os.path.isfile(os.path.join(self.covers_dir, f"{norm_s}{ext}")):
                    return f"/covers/{norm_s}{ext}"

        return None
