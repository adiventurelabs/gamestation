#!/usr/bin/env bash
# =============================================================================
#   GameStation - PlayStation 3 System Firmware (PS3UPDAT.PUP) Installer
# =============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

clear
echo -e "${CYAN}=============================================================================${NC}"
echo -e "${YELLOW}        PlayStation 3 Firmware Installer for RPCS3                           ${NC}"
echo -e "${CYAN}=============================================================================${NC}"
echo ""

# 1. Locate RPCS3 executable
RPCS3_BIN=""
if [ -f "$HOME/.local/bin/rpcs3" ]; then
    RPCS3_BIN="$HOME/.local/bin/rpcs3"
elif [ -f "$HOME/.local/share/gamestation/emulators/rpcs3.AppImage" ]; then
    RPCS3_BIN="$HOME/.local/share/gamestation/emulators/rpcs3.AppImage"
elif [ -f "$SCRIPT_DIR/emulators/linux/rpcs3.AppImage" ]; then
    mkdir -p "$HOME/.local/share/gamestation/emulators"
    RPCS3_BIN="$HOME/.local/share/gamestation/emulators/rpcs3.AppImage"
    cp "$SCRIPT_DIR/emulators/linux/rpcs3.AppImage" "$RPCS3_BIN"
    chmod +x "$RPCS3_BIN"
elif command -v rpcs3 &>/dev/null; then
    RPCS3_BIN="$(command -v rpcs3)"
fi

if [ -z "$RPCS3_BIN" ]; then
    echo -e "${RED}[ERROR] RPCS3 executable not found. Run ./Install_And_Play_Linux.sh first.${NC}"
    exit 1
fi

chmod +x "$RPCS3_BIN" 2>/dev/null || true
echo -e "    ${GREEN}[OK]${NC} Using RPCS3 executable: $RPCS3_BIN"

# 2. Locate or download official Sony PS3UPDAT.PUP
PUP_FILE=""
LOCAL_CACHE="$HOME/.cache/gamestation/firmware/PS3UPDAT.PUP"
mkdir -p "$HOME/.cache/gamestation/firmware"

if [ -f "$SCRIPT_DIR/emulators/firmware/PS3UPDAT.PUP" ]; then
    echo -e "    [*] Found pre-downloaded PS3UPDAT.PUP in emulators/firmware/."
    if [ ! -f "$LOCAL_CACHE" ]; then
        echo -e "    [*] Copying firmware to local user cache ($LOCAL_CACHE)..."
        cp "$SCRIPT_DIR/emulators/firmware/PS3UPDAT.PUP" "$LOCAL_CACHE"
    fi
    PUP_FILE="$LOCAL_CACHE"
elif [ -f "$LOCAL_CACHE" ]; then
    echo -e "    ${GREEN}[OK]${NC} Found PS3UPDAT.PUP in local user cache."
    PUP_FILE="$LOCAL_CACHE"
else
    echo -e "    [*] Downloading official Sony PS3UPDAT.PUP (197MB) from playstation.net..."
    curl -L --progress-bar -f "http://dus01.ps3.update.playstation.net/update/ps3/image/us/2026_0318_a2b60b6ac1d2e49e230144345616927c/PS3UPDAT.PUP" -o "$LOCAL_CACHE"
    PUP_FILE="$LOCAL_CACHE"
fi

# Ensure permissions & environment
export APPIMAGE_EXTRACT_AND_RUN=1
export TMPDIR="$HOME/.cache/gamestation/tmp"
mkdir -p "$TMPDIR"

echo ""
echo -e "${GREEN}>>> Launching RPCS3 to install PlayStation 3 System Software...${NC}"
echo -e "${YELLOW}>>> INSTRUCTIONS:${NC}"
echo -e "${YELLOW}    1. RPCS3 will prompt: 'Do you want to install PlayStation 3 System Software?'${NC}"
echo -e "${YELLOW}    2. Click 'Yes'.${NC}"
echo -e "${YELLOW}    3. Wait 15-30 seconds for firmware compilation to finish (reaches 100%).${NC}"
echo -e "${YELLOW}    4. Click 'OK' and close RPCS3 window.${NC}"
echo ""

# Launch RPCS3 with the firmware PUP
"$RPCS3_BIN" "$PUP_FILE"

echo ""
echo -e "${CYAN}=============================================================================${NC}"
echo -e "${GREEN}   PlayStation 3 Firmware installation complete!${NC}"
echo -e "   All PS3 games (Dragon Ball Z, Naruto, Assassin's Creed) are ready to play."
echo -e "${CYAN}=============================================================================${NC}"
echo ""
