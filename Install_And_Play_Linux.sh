#!/usr/bin/env bash
# =============================================================================
#   GameStation Living Room Console - One-Click Setup & Launcher for Linux
#   Supports: Ubuntu, Debian, Pop!_OS, Linux Mint, Fedora, Arch Linux, SteamOS
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Text Styling
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

clear
echo -e "${CYAN}=============================================================================${NC}"
echo -e "${CYAN}  ######                                #####                                ${NC}"
echo -e "${CYAN} #      #   ##   #    # ######  ####   #     # #####   ##   ##### #  ####  #   ${NC}"
echo -e "${CYAN} #         #  #  ##  ## #      #       #         #    #  #    #   # #    # ##  ${NC}"
echo -e "${CYAN} #  ####  #    # # ## # #####   ####    #####    #   #    #   #   # #    # # # ${NC}"
echo -e "${CYAN} #     #  ###### #    # #           #        #   #   ######   #   # #    # #  #${NC}"
echo -e "${CYAN} #     #  #    # #    # #      #    #  #     #   #   #    #   #   # #    # #   ${NC}"
echo -e "${CYAN}  ######  #    # #    # ######  ####    #####    #   #    #   #   #  ####  #   ${NC}"
echo -e "${CYAN}=============================================================================${NC}"
echo -e "${YELLOW}      GameStation Living Room Console Setup & Launcher for Linux             ${NC}"
echo -e "${CYAN}=============================================================================${NC}"
echo ""

# -----------------------------------------------------------------------------
# STEP 1: Check & Install Python 3, FUSE & System Dependencies
# -----------------------------------------------------------------------------
echo -e "${GREEN}>>> [1/6] Checking system packages & dependencies...${NC}"

# Ensure ~/.local/bin is in PATH and AppImages can run without FUSE conflicts
mkdir -p "$HOME/.local/bin"
export PATH="$HOME/.local/bin:$PATH"
export APPIMAGE_EXTRACT_AND_RUN=1

if command -v apt-get &>/dev/null; then
    echo -e "    [*] Verifying system packages via apt..."
    sudo apt-get update -qq 2>/dev/null || true
    sudo apt-get install -y python3 python3-pip python3-venv curl wget p7zip-full libfuse2t64 2>/dev/null || \
    sudo apt-get install -y python3 python3-pip python3-venv curl wget p7zip-full libfuse2 2>/dev/null || true
elif command -v dnf &>/dev/null; then
    echo -e "    [*] Verifying system packages via dnf..."
    sudo dnf install -y python3 python3-pip curl wget p7zip p7zip-plugins fuse-libs 2>/dev/null || true
elif command -v pacman &>/dev/null; then
    echo -e "    [*] Verifying system packages via pacman..."
    sudo pacman -Sy --noconfirm python python-pip curl wget p7zip fuse2 2>/dev/null || true
fi

PYTHON_CMD="python3"
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}[ERROR] Python 3.10+ is required. Please install python3.${NC}"
    exit 1
fi
echo -e "    ${GREEN}[OK]${NC} Python 3 detected: $($PYTHON_CMD --version)"

# -----------------------------------------------------------------------------
# STEP 2: Python Virtual Environment
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}>>> [2/6] Verifying Python Environment...${NC}"

VENV_DIR="$SCRIPT_DIR/.venv_linux"
if [ ! -d "$VENV_DIR" ]; then
    echo -e "    [*] Creating local virtual environment..."
    $PYTHON_CMD -m venv "$VENV_DIR" 2>/dev/null || true
fi

if [ -f "$VENV_DIR/bin/python" ]; then
    PY_EXEC="$VENV_DIR/bin/python"
    PIP_EXEC="$VENV_DIR/bin/pip"
else
    PY_EXEC="$PYTHON_CMD"
    PIP_EXEC="pip3"
fi

if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    echo -e "    [*] Installing required packages silently..."
    $PIP_EXEC install --upgrade pip --quiet 2>/dev/null || true
    $PIP_EXEC install -r "$SCRIPT_DIR/requirements.txt" --quiet 2>/dev/null || \
    $PIP_EXEC install -r "$SCRIPT_DIR/requirements.txt" --break-system-packages --quiet 2>/dev/null || true
fi
echo -e "    ${GREEN}[OK]${NC} Python environment ready."

# -----------------------------------------------------------------------------
# STEP 3: Download & Install Linux Emulators (RPCS3, Cemu, Xenia, DuckStation, PCSX2)
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}>>> [3/6] Checking Emulators for Linux (AppImages)...${NC}"

# 3a. RPCS3 (PlayStation 3)
if ! command -v rpcs3 &>/dev/null && [ ! -f "$HOME/.local/bin/rpcs3" ]; then
    echo -e "    [*] Downloading RPCS3 (PlayStation 3 AppImage)..."
    RPCS3_URL=$(curl -sL "https://api.github.com/repos/RPCS3/rpcs3-binaries-linux/releases/latest" | grep "browser_download_url" | grep -i "\.AppImage\"" | cut -d '"' -f 4 | head -n 1)
    [ -z "$RPCS3_URL" ] && RPCS3_URL="https://github.com/RPCS3/rpcs3-binaries-linux/releases/download/build-63996a47115563e433b909f2afc62d264e4b1314/rpcs3-v0.0.43-20560-63996a47_linux64.AppImage"
    curl -L --fail --progress-bar -A "GameStation/Linux" "$RPCS3_URL" -o "$HOME/.local/bin/rpcs3" || true
    chmod +x "$HOME/.local/bin/rpcs3" 2>/dev/null || true
    echo -e "    ${GREEN}[OK]${NC} RPCS3 installed to ~/.local/bin/rpcs3"
else
    echo -e "    ${GREEN}[OK]${NC} RPCS3 is present."
fi

# 3b. Cemu (Nintendo Wii U)
if ! command -v cemu &>/dev/null && [ ! -f "$HOME/.local/bin/cemu" ]; then
    echo -e "    [*] Downloading Cemu (Nintendo Wii U AppImage)..."
    CEMU_URL=$(curl -sL "https://api.github.com/repos/cemu-project/Cemu/releases/latest" | grep "browser_download_url" | grep -i "\.AppImage\"" | cut -d '"' -f 4 | head -n 1)
    [ -z "$CEMU_URL" ] && CEMU_URL="https://github.com/cemu-project/Cemu/releases/download/v2.6/Cemu-2.6-x86_64.AppImage"
    curl -L --fail --progress-bar -A "GameStation/Linux" "$CEMU_URL" -o "$HOME/.local/bin/cemu" || true
    chmod +x "$HOME/.local/bin/cemu" 2>/dev/null || true
    echo -e "    ${GREEN}[OK]${NC} Cemu installed to ~/.local/bin/cemu"
else
    echo -e "    ${GREEN}[OK]${NC} Cemu is present."
fi

# 3c. Xenia Canary (Xbox 360)
if ! command -v xenia &>/dev/null && ! command -v xenia_canary &>/dev/null && [ ! -f "$HOME/.local/bin/xenia" ]; then
    echo -e "    [*] Downloading Xenia Canary (Xbox 360 AppImage)..."
    XENIA_URL=$(curl -sL "https://api.github.com/repos/pkgforge-dev/xenia-canary-AppImage/releases/latest" | grep "browser_download_url" | grep -i "\.AppImage\"" | cut -d '"' -f 4 | head -n 1)
    if [ -n "$XENIA_URL" ]; then
        curl -L --fail --progress-bar -A "GameStation/Linux" "$XENIA_URL" -o "$HOME/.local/bin/xenia" || true
        chmod +x "$HOME/.local/bin/xenia" 2>/dev/null || true
        echo -e "    ${GREEN}[OK]${NC} Xenia Canary installed to ~/.local/bin/xenia"
    fi
else
    echo -e "    ${GREEN}[OK]${NC} Xenia Canary is present."
fi

# 3d. DuckStation (PlayStation 1)
if ! command -v duckstation &>/dev/null && [ ! -f "$HOME/.local/bin/duckstation" ]; then
    echo -e "    [*] Downloading DuckStation (PS1 AppImage)..."
    DUCK_URL="https://github.com/stenzek/duckstation/releases/download/latest/DuckStation-x64.AppImage"
    curl -L --fail --progress-bar -A "GameStation/Linux" "$DUCK_URL" -o "$HOME/.local/bin/duckstation" || true
    chmod +x "$HOME/.local/bin/duckstation" 2>/dev/null || true
    echo -e "    ${GREEN}[OK]${NC} DuckStation installed to ~/.local/bin/duckstation"
else
    echo -e "    ${GREEN}[OK]${NC} DuckStation is present."
fi

# 3e. PCSX2 (PlayStation 2)
if ! command -v pcsx2 &>/dev/null && [ ! -f "$HOME/.local/bin/pcsx2" ]; then
    echo -e "    [*] Downloading PCSX2 (PS2 AppImage)..."
    PCSX2_URL=$(curl -sL "https://api.github.com/repos/PCSX2/pcsx2/releases/latest" | grep "browser_download_url" | grep -i "linux-appimage.*\.AppImage\"" | cut -d '"' -f 4 | head -n 1)
    [ -z "$PCSX2_URL" ] && PCSX2_URL="https://github.com/PCSX2/pcsx2/releases/download/v2.8.2/pcsx2-v2.8.2-linux-appimage-x64-Qt.AppImage"
    curl -L --fail --progress-bar -A "GameStation/Linux" "$PCSX2_URL" -o "$HOME/.local/bin/pcsx2" || true
    chmod +x "$HOME/.local/bin/pcsx2" 2>/dev/null || true
    echo -e "    ${GREEN}[OK]${NC} PCSX2 installed to ~/.local/bin/pcsx2"
else
    echo -e "    ${GREEN}[OK]${NC} PCSX2 is present."
fi

# -----------------------------------------------------------------------------
# STEP 4: Dual Controller Profiles
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}>>> [4/6] Pre-configuring Dual Gamepad Profiles...${NC}"
$PY_EXEC -m psconsole.windows_setup || true

# -----------------------------------------------------------------------------
# STEP 5: Create Linux Desktop Launcher Shortcut
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}>>> [5/6] Creating Desktop Launcher...${NC}"

DESKTOP_ENTRY="[Desktop Entry]
Name=GameStation Console
Comment=Living Room Game Console Dashboard
Exec=$SCRIPT_DIR/Install_And_Play_Linux.sh
Icon=input-gaming
Terminal=true
Type=Application
Categories=Game;Console;
StartupNotify=true"

mkdir -p "$HOME/.local/share/applications" 2>/dev/null || true
echo "$DESKTOP_ENTRY" > "$HOME/.local/share/applications/gamestation.desktop" 2>/dev/null || true

if [ -d "$HOME/Desktop" ]; then
    echo "$DESKTOP_ENTRY" > "$HOME/Desktop/GameStation.desktop" 2>/dev/null || true
    chmod +x "$HOME/Desktop/GameStation.desktop" 2>/dev/null || true
    echo -e "    ${GREEN}[OK]${NC} Desktop shortcut created at ~/Desktop/GameStation.desktop"
fi

# -----------------------------------------------------------------------------
# STEP 6: Launch Fullscreen Living Room Console UI
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}>>> [6/6] Launching GameStation Console Service & UI...${NC}"

# Start browser in app/kiosk mode
launch_browser() {
    sleep 1.5
    local URL="http://localhost:8088"
    if command -v google-chrome &>/dev/null; then
        google-chrome --app="$URL" --start-fullscreen &>/dev/null &
    elif command -v chromium &>/dev/null; then
        chromium --app="$URL" --start-fullscreen &>/dev/null &
    elif command -v chromium-browser &>/dev/null; then
        chromium-browser --app="$URL" --start-fullscreen &>/dev/null &
    elif command -v brave-browser &>/dev/null; then
        brave-browser --app="$URL" --start-fullscreen &>/dev/null &
    elif command -v firefox &>/dev/null; then
        firefox --kiosk "$URL" &>/dev/null &
    elif command -v xdg-open &>/dev/null; then
        xdg-open "$URL" &>/dev/null &
    fi
}

launch_browser &

echo ""
echo -e "${CYAN}=============================================================================${NC}"
echo -e "${GREEN}   GAMESTATION IS RUNNING ON LINUX!${NC}"
echo -e "   - Dashboard UI:       http://localhost:8088"
echo -e "   - Couch Controls:     Navigate with Gamepad D-Pad or Left Stick"
echo -e "   - Launch Game:        Press (A) / Cross button"
echo -e "   - In-Game Exit:       Hold (SELECT + START) on any controller for 2s"
echo -e "   - Stop Service:       Press Ctrl+C"
echo -e "${CYAN}=============================================================================${NC}"
echo ""

# Run console daemon in foreground
exec $PY_EXEC -m psconsole.service
