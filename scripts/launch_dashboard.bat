@echo off
setlocal
title PlayStation Console Dashboard

echo ========================================================
echo   Launching PlayStation Console Dashboard Shell
echo ========================================================
echo.

set "EDGE_EXE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not exist "%EDGE_EXE%" (
    set "EDGE_EXE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
)

set "TARGET_URL=http://127.0.0.1:8088"

if exist "%EDGE_EXE%" (
    echo Starting Microsoft Edge in PlayStation Kiosk Mode...
    start "" "%EDGE_EXE%" --app="%TARGET_URL%" --kiosk --start-fullscreen --no-first-run
) else (
    echo Starting in default system browser...
    start "" "%TARGET_URL%"
)

echo Dashboard active at %TARGET_URL%
