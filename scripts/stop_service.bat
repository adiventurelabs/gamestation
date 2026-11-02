@echo off
echo Stopping PlayStation Console Service...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "Get-WmiObject Win32_Process | Where-Object { $_.CommandLine -like '*psconsole.service*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
echo Service stopped.
