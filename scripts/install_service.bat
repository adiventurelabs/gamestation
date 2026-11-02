@echo off
setlocal EnableDelayedExpansion
title Install PlayStation Console Service

echo =======================================================
echo Installing PlayStation Console Service (User Space)
echo =======================================================
echo No administrator privileges required.
echo.

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

set "VBS_LAUNCHER=%PROJECT_ROOT%\scripts\run_service.vbs"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "SHORTCUT_PATH=%STARTUP_FOLDER%\PlayStationConsole.lnk"

if not exist "%VBS_LAUNCHER%" (
    echo [ERROR] Launcher file not found: "%VBS_LAUNCHER%"
    pause
    exit /b 1
)

echo Creating Startup shortcut in:
echo "%STARTUP_FOLDER%"
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut('%SHORTCUT_PATH%'); " ^
    "$s.TargetPath = 'wscript.exe'; " ^
    "$s.Arguments = '\"%VBS_LAUNCHER%\"'; " ^
    "$s.WorkingDirectory = '%PROJECT_ROOT%'; " ^
    "$s.Description = 'PlayStation Disc Console Background Daemon'; " ^
    "$s.Save()"

if exist "%SHORTCUT_PATH%" (
    echo [SUCCESS] Startup shortcut created: "%SHORTCUT_PATH%"
) else (
    echo [ERROR] Failed to create shortcut.
    pause
    exit /b 1
)

echo.
echo Starting background service now...
wscript.exe "%VBS_LAUNCHER%"

echo.
echo [DONE] The service is installed and running in the background.
echo When you insert a PS1 or PS2 disc, it will automatically launch!
echo.
pause
