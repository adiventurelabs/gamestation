@echo off
setlocal EnableDelayedExpansion
title Uninstall GameStation Console Service

echo =======================================================
echo Uninstalling GameStation Console Service
echo =======================================================
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\GameStation.lnk"
set "LEGACY_SHORTCUT=%STARTUP_FOLDER%\PlayStationConsole.lnk"

if exist "%SHORTCUT_PATH%" (
    del /f /q "%SHORTCUT_PATH%"
    echo [OK] Removed startup shortcut: "%SHORTCUT_PATH%"
)
if exist "%LEGACY_SHORTCUT%" (
    del /f /q "%LEGACY_SHORTCUT%"
    echo [OK] Removed legacy startup shortcut: "%LEGACY_SHORTCUT%"
)

echo Stopping any active background service instances...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*psconsole.service*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo.
echo [DONE] GameStation Console Service has been completely removed from startup and stopped.
echo Your existing launcher and system configurations remain untouched.
echo.
pause
