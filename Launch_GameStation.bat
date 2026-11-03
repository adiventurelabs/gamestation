@echo off
setlocal enabledelayedexpansion
title GameStation Console

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
echo                 Living Room Console for Windows 11 / Helios
echo  =============================================================================
echo.

:: 2. Locate Python 3.10+
set "PY_CMD="

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
    goto :FoundPython
)

python --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python"
    goto :FoundPython
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=python3"
    goto :FoundPython
)

:: Search common Windows install paths
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*" "C:\Python3*") do (
    if exist "%%D\python.exe" (
        set "PY_CMD="%%D\python.exe""
        goto :FoundPython
    )
)

:FoundPython
if "%PY_CMD%"=="" (
    color 0C
    echo [ERROR] Python 3 was not found on this system!
    echo.
    echo Please install Python 3.10 or newer on your Acer Helios laptop:
    echo 1. Download from https://www.python.org/downloads/
    echo 2. IMPORTANT: Check the box "Add Python to PATH" during installation.
    echo.
    pause
    popd
    exit /b 1
)

echo [*] Python detected: %PY_CMD%

:: 3. Fast Dependency Check (Only run pip if packages are missing)
echo [*] Checking required dependencies...
%PY_CMD% -c "import urllib3" >nul 2>&1
if errorlevel 1 (
    echo [*] Installing required packages from requirements.txt...
    %PY_CMD% -m pip install -r requirements.txt --quiet --disable-pip-version-check
)

:: 4. Verify Local Emulators, Dual Xbox Controllers & Cache
%PY_CMD% -m psconsole.windows_setup

:: 5. Launch Fullscreen Console App in Browser
echo.
echo [*] Launching GameStation Console UI...

set "BROWSER_LAUNCHED=0"

:: Try Microsoft Edge App Mode (Clean borderless console window)
where msedge >nul 2>&1
if not errorlevel 1 (
    start "" msedge --app=http://localhost:8088 --start-fullscreen --window-position=0,0
    set "BROWSER_LAUNCHED=1"
)

:: Try Chrome App Mode if Edge not found
if "!BROWSER_LAUNCHED!"=="0" (
    where chrome >nul 2>&1
    if not errorlevel 1 (
        start "" chrome --app=http://localhost:8088 --start-fullscreen --window-position=0,0
        set "BROWSER_LAUNCHED=1"
    )
)

:: Fallback to default browser
if "!BROWSER_LAUNCHED!"=="0" (
    start "" "http://localhost:8088"
)

echo.
echo =============================================================================
echo   GameStation is RUNNING!
echo   - Local Dashboard:      http://localhost:8088
echo   - Network Dashboard:    http://0.0.0.0:8088
echo.
echo   Press (SELECT + START) on any Xbox Controller for 2 seconds to exit any game.
echo   Close this window or press Ctrl+C to shut down GameStation.
echo =============================================================================
echo.

:: 6. Run the Console Service Daemon in Foreground
%PY_CMD% -m psconsole.service

:: Clean up temporary network drive mapping on exit
popd
