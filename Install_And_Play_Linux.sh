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
# STEP 1: Check & Install Python 3 & Dependencies
# -----------------------------------------------------------------------------
echo -e "${GREEN}>>> [1/5] Checking Python 3 and system requirements...${NC}"

if ! command -v python3 &>/dev/null; then
    echo -e "${YELLOW}[*] Python 3 not found. Installing via system package manager...${NC}"
    if command -v apt-get &>/dev/null; then
        sudo apt-get update && sudo apt-get install -y python3 python3-pip python3-venv
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y python3 python3-pip
    elif command -v pacman &>/dev/null; then
        sudo pacman -Sy --noconfirm python python-pip
    else
        echo -e "${RED}[ERROR] Please install Python 3.10+ manually on your system.${NC}"
        exit 1
    fi
fi

PYTHON_CMD="python3"
echo -e "    ${GREEN}[OK]${NC} Python 3 detected: $($PYTHON_CMD --version)"

# -----------------------------------------------------------------------------
# STEP 2: Python Virtual Environment & Requirements
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}>>> [2/5] Verifying Python Dependencies (requirements.txt)...${NC}"

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
    echo -e "    ${GREEN}[OK]${NC} Dependencies satisfied."
fi

# -----------------------------------------------------------------------------
# STEP 3: Dual Controller & Emulator Setup
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}>>> [3/5] Configuring Controller Profiles & System Readiness...${NC}"
$PY_EXEC -m psconsole.windows_setup || true

# -----------------------------------------------------------------------------
# STEP 4: Create Linux Desktop Launcher Shortcut
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}>>> [4/5] Creating Desktop Launcher...${NC}"

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
# STEP 5: Launch Fullscreen Living Room Console UI
# -----------------------------------------------------------------------------
echo -e "\n${GREEN}>>> [5/5] Launching GameStation Console Service & UI...${NC}"

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
