@echo off
set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%.."
set "PROJECT_ROOT=%CD%"
popd

echo Starting PlayStation Console Service in background...
cd /d "%PROJECT_ROOT%"
wscript.exe "%PROJECT_ROOT%\scripts\run_service.vbs"
echo Service started.
