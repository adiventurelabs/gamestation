# PlayStation BIOS Guide

Both DuckStation and PCSX2 require original system BIOS firmware to emulate the PlayStation hardware correctly and boot physical game discs.

> [!IMPORTANT]
> **Legal Notice:** Do not download proprietary PlayStation BIOS firmware from unofficial or third-party websites. Extract the BIOS directly from the physical PlayStation 1 and PlayStation 2 hardware you already own.

---

## 1. Required BIOS Files

### PlayStation 1 (DuckStation)
DuckStation requires a 512 KB PS1 BIOS file. Recommended dumps:

| Region | BIOS Filename | Console Model |
| :--- | :--- | :--- |
| **NTSC-U (North America)** | `scph5501.bin` (or `scph1001.bin`, `scph7001.bin`) | SCPH-5501 / SCPH-1001 |
| **PAL (Europe / Australia)** | `scph5502.bin` (or `scph7502.bin`) | SCPH-5502 |
| **NTSC-J (Japan)** | `scph5500.bin` (or `scph7000.bin`) | SCPH-5500 |

### PlayStation 2 (PCSX2)
PCSX2 requires a 4 MB PS2 BIOS dump (and optionally companion files):

| File | Description |
| :--- | :--- |
| `scph39001.bin` / `scph70012.bin` | Main PS2 BIOS ROM0 (4 MB) |
| `rom1.bin` | PS2 DVD player firmware (optional, for DVD movies) |
| `rom2.bin` | Chinese font data (optional) |
| `erom.bin` | DVD player extensions (optional) |

---

## 2. How to Legally Dump from Your Consoles

### Dumping PlayStation 1 BIOS
1. **Method A: Via FreePSXBoot Memory Card**
   - Place **FreePSXBoot** on an original PS1 memory card using a Unirom cartridge, DexDrive, or Memcard Pro.
   - Boot the console into the homebrew menu.
   - Run the BIOS dumper utility to write the 512 KB image to the memory card or serial cable.
2. **Method B: Via Backward Compatible PS2 / PS3**
   - If you own a PS2 with FreeMCBoot, you can dump the PS1 BIOS stored inside the PS2's I/O processor (`rom0:PS1SYS` or `ps1bios.bin`).

### Dumping PlayStation 2 BIOS
1. **Prepare a USB Flash Drive:**
   - Format a standard USB flash drive to FAT32.
   - Copy `dumpbios-usb.elf` (part of the official PCSX2 toolset) to the USB drive.
2. **Boot Your Physical PS2:**
   - Insert a **FreeMCBoot (FMCB)** memory card into Slot 1 and your USB drive into a PS2 USB port.
   - Power on the console and select **uLaunchELF** from the PS2 main menu.
3. **Execute the Dumper:**
   - Browse to `mass:/dumpbios-usb.elf` and press `Circle` to launch it.
   - The tool will dump the BIOS ROMs directly onto the USB drive.
   - When finished, plug the USB drive into your PC.

---

## 3. Placement Locations on Windows

Copy the dumped `.bin` files into the standard BIOS directories:

### DuckStation BIOS Directory
- `%USERPROFILE%\Documents\DuckStation\bios\`
- *(Alternative)*: `%LOCALAPPDATA%\DuckStation\bios\`

### PCSX2 BIOS Directory
- `%USERPROFILE%\Documents\PCSX2\bios\`
- *(Alternative)*: `%LOCALAPPDATA%\PCSX2\bios\`

---

## 4. Verification

After placing your files:
1. Open PowerShell and run the setup script:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
   ```
2. The script will confirm that valid BIOS files were located for both systems.
