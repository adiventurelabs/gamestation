# Future PlayStation 3 (RPCS3) Integration Roadmap

While the initial scope focuses exclusively on **PS1 and PS2 physical media**, the system architecture has been designed from the ground up to allow adding **PlayStation 3 physical Blu-ray discs** cleanly.

---

## Technical Differences Between PS1/PS2 and PS3 Discs

| Feature | PS1 (CD-ROM) / PS2 (CD/DVD) | PS3 (BD-ROM) |
| :--- | :--- | :--- |
| **Media Type** | CD-ROM (700 MB) / DVD-ROM (4.7 GB – 8.5 GB) | Dual-Layer Blu-ray Disc (25 GB – 50 GB) |
| **Filesystem** | ISO9660 / UDF 1.02 bridge | UDF 2.50 / 2.60 |
| **Identification File** | `SYSTEM.CNF` | `PS3_DISC.SFB` and `PS3_GAME/PARAM.SFO` |
| **Encryption** | None on standard PC drive | **Hardware Disc Encryption (3K3Y / ODE keys)** |
| **Optical Drive Requirements** | Standard PC DVD/CD drive | **Compatible Blu-ray drive (e.g. LG BP50NB40)** |

---

## Key Requirements to Implement PS3 Physical Playback Later

### 1. Drive Hardware
- An optical drive from the RPCS3 validated list (such as the proposed **LG BP50NB40**) is required. Generic PC Blu-ray drives will fail to read the encrypted game partition sectors.

### 2. Disc Key Decryption (IRD / .dkey)
- Retail PS3 game discs are encrypted. Unlike PS1 and PS2 discs which can be read directly by emulators once mounted, RPCS3 must decrypt sectors on-the-fly.
- RPCS3 requires a matching `.dkey` (Disc Key) or IRD file corresponding to the title ID (e.g., `BCUS-98114` for *The Last of Us*).
- RPCS3 includes an automatic disc key downloader that queries the community IRD database matching your disc's CRC/serial when inserted.

### 3. Disc Identifier Extension
In `psconsole/disc_identifier.py`, add PS3 detection logic:
1. Check for `PS3_DISC.SFB` in root directory.
2. Read `PS3_GAME/PARAM.SFO` (contains `TITLE` and `TITLE_ID` e.g. `BLUS-30444`).
3. Return `DiscType.PS3`.

### 4. Emulator Invocation
In `psconsole/emulator_launcher.py`:
- Executable: `rpcs3.exe`
- Direct disc boot command:
  ```bash
  rpcs3.exe --headless --fullscreen "D:\"
  ```
  *(or pass the drive root path with RPCS3's `--disc` flag once disc key is loaded)*.

### 5. PS3 System Software
- Official Sony PlayStation 3 firmware (`PS3UPDAT.PUP`) downloaded directly from Sony's official PlayStation support website and installed into RPCS3 via `File > Install Firmware`.
