@echo off
setlocal enabledelayedexpansion
title GameStation Living Room Console Setup (Acer Helios)

:: 1. Handle UNC Network Share paths (pushd maps a temporary drive letter automatically)
pushd "%~dp0"

cls
color 0A
echo  =============================================================================
echo    ######                                #####                                
echo   #      #   ##   #    # ######  ####   #     # #####   ##   ##### #  ####  #    # 
echo   #         #  #  ##  ## #      #       #         #    #  #    #   # #    # ##   # 
echo   #  ####  #    # # ## # #####   ####    #####    #   #    #   #   # #    # # #  # 
echo   #     #  ###### #    # #           #        #   #   ######   #   # #    # #  # # 
echo   #     #  #    # #    # #      #    #  #     #   #   #    #   #   # #    # #   ## 
echo    ######  #    # #    # ######  ####    #####    #   #    #   #   #  ####  #    # 
echo  =============================================================================
echo       Zero-Touch Installer ^& Launcher for Windows 10 (Acer Helios)
echo  =============================================================================
echo.
echo [*] Initializing automated setup for fresh Windows 10...
echo [*] Mapping network workspace and launching installer...
echo.

:: 2. Execute PowerShell setup with bypass policy
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup_Helios_Windows10.ps1"

if errorlevel 1 (
    color 0C
    echo.
    echo [ERROR] Setup encountered an issue. See details above.
    pause
)

:: 3. Clean up network drive mapping
popd
