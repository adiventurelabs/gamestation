@echo off
setlocal
pushd "%~dp0"

echo =======================================================================
echo          Create GameStation Desktop Shortcut (Windows 11)
echo =======================================================================
echo.

set "TARGET_BAT=%~dp0Launch_GameStation.bat"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\GameStation.lnk"
set "WORKING_DIR=%~dp0"
set "ICON_LOC=%SystemRoot%\System32\shell32.dll,220"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut('%SHORTCUT_PATH%'); " ^
    "$s.TargetPath = '%TARGET_BAT%'; " ^
    "$s.WorkingDirectory = '%WORKING_DIR%'; " ^
    "$s.IconLocation = '%ICON_LOC%'; " ^
    "$s.Description = 'Launch GameStation Console'; " ^
    "$s.Save();"

if exist "%SHORTCUT_PATH%" (
    echo [SUCCESS] GameStation shortcut created on your Desktop!
    echo Location: %SHORTCUT_PATH%
    echo.
    echo You can now launch GameStation directly by double-clicking the icon on your Desktop.
) else (
    echo [NOTICE] Could not create desktop shortcut automatically.
    echo You can right-click Launch_GameStation.bat and select 'Show more options' -^> 'Send to' -^> 'Desktop (create shortcut)'.
)

echo.
pause
popd
