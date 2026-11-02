@echo off
setlocal EnableDelayedExpansion
title Uninstall PlayStation Console Service

echo =======================================================
echo Uninstalling PlayStation Console Service
echo =======================================================
echo.

set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\PlayStationConsole.lnk"

if exist "%SHORTCUT_PATH%" (
    del /f /q "%SHORTCUT_PATH%"
    echo [OK] Removed startup shortcut: "%SHORTCUT_PATH%"
) else (
    echo [INFO] Startup shortcut was not present.
)

echo Stopping any active background service instances...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*psconsole.service*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

echo.
echo [DONE] PlayStation Console Service has been completely removed from startup and stopped.
echo Your existing launcher and system configurations remain untouched.
echo.
pause
