<#
.SYNOPSIS
    Inspects existing Windows laptop setup for GameStation Console integration.
    Checks optical drives, DuckStation, PCSX2, BIOS files, controllers, and Python.
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " GameStation Console Setup & Inspection Inspector" -ForegroundColor Yellow
Write-Host " Target Hardware: Acer Helios 300 / Windows Gaming Setup" -ForegroundColor Gray
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

$report = [PSCustomObject]@{
    PythonReady = $false
    OpticalDriveFound = $false
    OpticalDrives = @()
    DuckStationFound = $false
    DuckStationExe = ""
    PCSX2Found = $false
    PCSX2Exe = ""
    PS1BiosFound = $false
    PS2BiosFound = $false
    ControllerConnected = $false
}

# 1. Inspect Python
Write-Host "1. Checking Python Environment..." -ForegroundColor White
try {
    $pythonVer = & python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   [PASS] Found: $pythonVer" -ForegroundColor Green
        $report.PythonReady = $true
    } else {
        Write-Host "   [WARN] Python command failed. Ensure Python 3.9+ is in PATH." -ForegroundColor Yellow
    }
} catch {
    Write-Host "   [FAIL] Python is not installed or not in system PATH." -ForegroundColor Red
}

# 2. Inspect Optical Drives
Write-Host "`n2. Inspecting Optical Drives (CD/DVD/Blu-ray)..." -ForegroundColor White
$cdroms = Get-CimInstance Win32_CDROMDrive -ErrorAction SilentlyContinue
if ($cdroms -and $cdroms.Count -gt 0) {
    $report.OpticalDriveFound = $true
    foreach ($cd in $cdroms) {
        $driveLetter = $cd.Drive
        $driveName = $cd.Name
        $status = $cd.Status
        Write-Host "   [PASS] Optical Drive Detected: $driveLetter ($driveName) [Status: $status]" -ForegroundColor Green
        $report.OpticalDrives += "$driveLetter ($driveName)"
    }
} else {
    Write-Host "   [INFO] No internal or USB optical drive currently detected." -ForegroundColor Yellow
    Write-Host "          Acer Helios 300 requires an external USB optical drive." -ForegroundColor Gray
    Write-Host "          Recommended model: LG BP50NB40 External USB Blu-ray/DVD/CD Drive." -ForegroundColor Cyan
}

# 3. Inspect DuckStation
Write-Host "`n3. Inspecting DuckStation (PS1)..." -ForegroundColor White
$duckCandidates = @(
    "$env:LOCALAPPDATA\DuckStation\duckstation-qt-x64-ReleaseLTCG.exe",
    "$env:LOCALAPPDATA\DuckStation\duckstation-qt.exe",
    "$env:ProgramFiles\DuckStation\duckstation-qt.exe",
    "$env:LOCALAPPDATA\Programs\DuckStation\duckstation-qt.exe",
    "$env:USERPROFILE\scoop\apps\duckstation\current\duckstation-qt.exe"
)
foreach ($c in $duckCandidates) {
    if (Test-Path $c) {
        $report.DuckStationFound = $true
        $report.DuckStationExe = $c
        Write-Host "   [PASS] DuckStation Executable: $c" -ForegroundColor Green
        break
    }
}
if (-not $report.DuckStationFound) {
    Write-Host "   [WARN] DuckStation not found in standard candidate locations." -ForegroundColor Yellow
    Write-Host "          If installed elsewhere, specify path in config/config.json." -ForegroundColor Gray
}

# 4. Inspect PCSX2
Write-Host "`n4. Inspecting PCSX2 (PS2)..." -ForegroundColor White
$pcsx2Candidates = @(
    "$env:LOCALAPPDATA\Programs\PCSX2\pcsx2-qt.exe",
    "$env:ProgramFiles\PCSX2\pcsx2-qt.exe",
    "$env:LOCALAPPDATA\PCSX2\pcsx2-qt.exe",
    "${env:ProgramFiles(x86)}\PCSX2\pcsx2-qt.exe",
    "$env:USERPROFILE\scoop\apps\pcsx2\current\pcsx2-qt.exe"
)
foreach ($c in $pcsx2Candidates) {
    if (Test-Path $c) {
        $report.PCSX2Found = $true
        $report.PCSX2Exe = $c
        Write-Host "   [PASS] PCSX2 Executable: $c" -ForegroundColor Green
        break
    }
}
if (-not $report.PCSX2Found) {
    Write-Host "   [WARN] PCSX2 not found in standard candidate locations." -ForegroundColor Yellow
    Write-Host "          If installed elsewhere, specify path in config/config.json." -ForegroundColor Gray
}

# 5. Inspect RPCS3 (PS3) & shadPS4 (PS4)
Write-Host "`n5. Inspecting RPCS3 (PS3) & shadPS4 (PS4)..." -ForegroundColor White
$rpcs3Candidates = @(
    "$env:LOCALAPPDATA\Programs\RPCS3\rpcs3.exe",
    "$env:LOCALAPPDATA\RPCS3\rpcs3.exe",
    "$env:ProgramFiles\RPCS3\rpcs3.exe"
)
$rpcs3Found = $false
foreach ($c in $rpcs3Candidates) {
    if (Test-Path $c) {
        $rpcs3Found = $true
        Write-Host "   [PASS] RPCS3 Executable: $c" -ForegroundColor Green
        break
    }
}
if (-not $rpcs3Found) {
    Write-Host "   [INFO] RPCS3 (PS3) not found. Required only for PS3 games." -ForegroundColor Gray
}

$shadps4Candidates = @(
    "$env:LOCALAPPDATA\Programs\shadPS4\shadPS4.exe",
    "$env:LOCALAPPDATA\shadPS4\shadPS4.exe",
    "$env:ProgramFiles\shadPS4\shadPS4.exe",
    "$env:LOCALAPPDATA\fpPS4\fpPS4.exe"
)
$shadps4Found = $false
foreach ($c in $shadps4Candidates) {
    if (Test-Path $c) {
        $shadps4Found = $true
        Write-Host "   [PASS] shadPS4 Executable: $c" -ForegroundColor Green
        break
    }
}
if (-not $shadps4Found) {
    Write-Host "   [INFO] shadPS4 (PS4) not found. Required only for digital PS4 titles." -ForegroundColor Gray
}

# 6. Inspect BIOS Files
Write-Host "`n6. Inspecting BIOS Files..." -ForegroundColor White
$ps1BiosDirs = @(
    "$env:USERPROFILE\Documents\DuckStation\bios",
    "$env:LOCALAPPDATA\DuckStation\bios",
    "$env:APPDATA\DuckStation\bios"
)
foreach ($d in $ps1BiosDirs) {
    if (Test-Path $d) {
        $files = Get-ChildItem -Path $d -Include "scph*.bin","SCPH*.bin","ps-*.bin" -Recurse -ErrorAction SilentlyContinue
        if ($files -and $files.Count -gt 0) {
            $report.PS1BiosFound = $true
            Write-Host "   [PASS] Found $($files.Count) PS1 BIOS file(s) in: $d" -ForegroundColor Green
            break
        }
    }
}
if (-not $report.PS1BiosFound) {
    Write-Host "   [WARN] No PS1 BIOS files detected in standard DuckStation bios folders." -ForegroundColor Yellow
}

$ps2BiosDirs = @(
    "$env:USERPROFILE\Documents\PCSX2\bios",
    "$env:LOCALAPPDATA\PCSX2\bios",
    "$env:APPDATA\PCSX2\bios"
)
foreach ($d in $ps2BiosDirs) {
    if (Test-Path $d) {
        $files = Get-ChildItem -Path $d -Include "scph*.bin","SCPH*.bin","rom1.bin" -Recurse -ErrorAction SilentlyContinue
        if ($files -and $files.Count -gt 0) {
            $report.PS2BiosFound = $true
            Write-Host "   [PASS] Found $($files.Count) PS2 BIOS file(s) in: $d" -ForegroundColor Green
            break
        }
    }
}
if (-not $report.PS2BiosFound) {
    Write-Host "   [WARN] No PS2 BIOS files detected in standard PCSX2 bios folders." -ForegroundColor Yellow
}

# 6. Inspect Active Console Launcher
Write-Host "`n6. Checking Front-End Launcher..." -ForegroundColor White
$launchers = @("Playnite.FullscreenApp", "Playnite.DesktopApp", "BigBox", "steam", "retroarch", "pegasus-fe", "Kodi")
$runningLauncher = Get-Process -Name $launchers -ErrorAction SilentlyContinue
if ($runningLauncher) {
    Write-Host "   [PASS] Active Front-End Launcher Detected: $($runningLauncher.Name)" -ForegroundColor Green
} else {
    Write-Host "   [INFO] No active launcher currently in foreground. Foreground restoration will attach to whatever window launched the game." -ForegroundColor Gray
}

Write-Host "`n==========================================================" -ForegroundColor Cyan
Write-Host " Inspection Complete" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan
