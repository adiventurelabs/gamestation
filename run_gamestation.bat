@echo off
title GameStation Console Launcher
color 0B
echo =======================================================================
echo               Starting GameStation Console for Windows 11
echo =======================================================================
echo Checking Python installation...

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ from https://python.org and check "Add Python to PATH".
    pause
    exit /b 1
)

echo.
echo [1/3] Verifying dependencies...
pip install -r requirements.txt >nul 2>&1

echo [2/3] Running system and emulator verification...
python windows_setup_and_verify.py

echo.
echo [3/3] Launching GameStation Console Service & Dashboard...
echo Dashboard URL: http://localhost:8088
start "" http://localhost:8088

python -m psconsole.service
pause
