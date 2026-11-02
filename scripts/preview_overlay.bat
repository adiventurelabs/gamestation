@echo off
setlocal EnableDelayedExpansion
title GameStation Console UI Preview

echo ========================================================
echo   GameStation Console UI Overlay Preview Tool
echo ========================================================
echo.
echo Select an overlay to test on screen:
echo.
echo   [1] "Reading Disc..." Toast (Drive Spin-Up Feedback)
echo   [2] PlayStation 1 Game Card (Castlevania: SotN)
echo   [3] PlayStation 2 Game Card (Final Fantasy X)
echo   [4] Unsupported Media Dialog (DVD-Video / Music CD)
echo   [5] Missing BIOS Warning Dialog
echo   [6] Run Full Demo Cycle (Reading -^> Found -^> Launch)
echo   [0] Exit
echo.
set /p choice="Enter choice (0-6): "

set "SCRIPT_DIR=%~dp0"
set "PS_OVERLAY=%SCRIPT_DIR%show_overlay.ps1"

if "%choice%"=="1" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_OVERLAY%" -Type "READING" -Title "Reading Disc in Drive D:..." -Subtitle "Checking PlayStation Table of Contents..." -DurationSeconds 4.0
) else if "%choice%"=="2" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_OVERLAY%" -Type "LAUNCH_PS1" -Title "Castlevania: Symphony of the Night" -Subtitle "Starting DuckStation in fullscreen..." -Serial "SLUS-00067" -DurationSeconds 4.5
) else if "%choice%"=="3" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_OVERLAY%" -Type "LAUNCH_PS2" -Title "Final Fantasy X" -Subtitle "Starting PCSX2 in fullscreen..." -Serial "SLUS-20062" -DurationSeconds 4.5
) else if "%choice%"=="4" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_OVERLAY%" -Type "ERROR" -Title "Unsupported Media" -Message "Inserted DVD-Video movie disc is not a playable PlayStation game. Press (B) to dismiss." -DurationSeconds 5.0
) else if "%choice%"=="5" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_OVERLAY%" -Type "ERROR" -Title "PlayStation BIOS Missing" -Message "Missing PS2 BIOS (scph39001.bin). Please copy your BIOS dump to documents\pcsx2\bios." -DurationSeconds 5.0
) else if "%choice%"=="6" (
    echo Showing Reading Disc toast...
    start /b powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_OVERLAY%" -Type "READING" -Title "Reading Disc in Drive D:..." -Subtitle "Checking Table of Contents..." -DurationSeconds 2.5
    timeout /t 2 /nobreak >nul
    echo Transitioning to Game Launch Card...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_OVERLAY%" -Type "LAUNCH_PS2" -Title "Final Fantasy X" -Subtitle "Starting PCSX2 in fullscreen..." -Serial "SLUS-20062" -DurationSeconds 4.0
) else (
    echo Exiting.
)
