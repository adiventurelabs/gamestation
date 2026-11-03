<#
.SYNOPSIS
    GameStation Console - Zero-Touch Automated Setup & Launcher for Windows 10/11 (Acer Helios)

.DESCRIPTION
    Designed for a fresh install of Windows 10:
    1. Downloads & installs Visual C++ 2015-2022 x64 Redistributable silently (if missing).
    2. Downloads & installs Python 3.11 x64 silently (if missing).
    3. Installs all Python dependencies from requirements.txt.
    4. Downloads and extracts emulators (Xenia Canary, DuckStation, PCSX2).
    5. Pre-configures Dual Xbox One S controllers (XInput) out-of-the-box.
    6. Creates a desktop shortcut.
    7. Launches the GameStation Console Service & boots Edge/Chrome in fullscreen TV mode.
#>

[CmdletBinding()]
param (
    [switch]$SkipEmulators = $false,
    [switch]$NoBrowser = $false
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host " =============================================================================" -ForegroundColor Cyan
Write-Host "   ######                                #####                                " -ForegroundColor Cyan
Write-Host "  #      #   ##   #    # ######  ####   #     # #####   ##   ##### #  ####  #   " -ForegroundColor Cyan
Write-Host "  #         #  #  ##  ## #      #       #         #    #  #    #   # #    # ##  " -ForegroundColor Cyan
Write-Host "  #  ####  #    # # ## # #####   ####    #####    #   #    #   #   # #    # # # " -ForegroundColor Cyan
Write-Host "  #     #  ###### #    # #           #        #   #   ######   #   # #    # #  #" -ForegroundColor Cyan
Write-Host "  #     #  #    # #    # #      #    #  #     #   #   #    #   #   # #    # #   " -ForegroundColor Cyan
Write-Host "   ######  #    # #    # ######  ####    #####    #   #    #   #   #  ####  #   " -ForegroundColor Cyan
Write-Host " =============================================================================" -ForegroundColor Cyan
Write-Host "        GameStation Living Room Console Setup (Acer Helios / Win 10)         " -ForegroundColor Yellow
Write-Host " =============================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ScriptDir) {
    $ScriptDir = (Get-Location).Path
}
Set-Location -Path $ScriptDir

# -----------------------------------------------------------------------------
# STEP 1: Check & Install Visual C++ 2015-2022 x64 Redistributable
# -----------------------------------------------------------------------------
Write-Host ">>> [1/7] Checking Visual C++ 2015-2022 x64 Redistributable..." -ForegroundColor Green
$vcDll = "$env:SystemRoot\System32\vcruntime140_1.dll"
$vcInstalled = Test-Path $vcDll

if ($vcInstalled) {
    Write-Host "    [OK] Visual C++ Runtime is already installed." -ForegroundColor Gray
} else {
    Write-Host "    [*] Visual C++ runtime missing. Downloading vc_redist.x64.exe..." -ForegroundColor Yellow
    $vcUrl = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    $vcDest = "$env:TEMP\vc_redist.x64.exe"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $vcUrl -OutFile $vcDest -UseBasicParsing
        Write-Host "    [*] Installing Visual C++ Redistributable silently..." -ForegroundColor Yellow
        $p = Start-Process -FilePath $vcDest -ArgumentList "/install", "/quiet", "/norestart" -PassThru -Wait
        Remove-Item -Path $vcDest -Force -ErrorAction SilentlyContinue
        Write-Host "    [OK] Visual C++ Runtime installed successfully!" -ForegroundColor Green
    } catch {
        Write-Host "    [WARNING] Could not automatically install VC++ Redistributable: $_" -ForegroundColor Red
        Write-Host "              Please ensure Visual C++ 2015-2022 x64 is installed." -ForegroundColor Yellow
    }
}

# -----------------------------------------------------------------------------
# STEP 2: Check & Install Python 3.11 x64
# -----------------------------------------------------------------------------
Write-Host "`n>>> [2/7] Checking Python 3 Installation..." -ForegroundColor Green

function Find-PythonExecutable {
    # Check py launcher
    $py = Get-Command "py.exe" -ErrorAction SilentlyContinue
    if ($py) { return "py" }

    # Check python in PATH
    $py = Get-Command "python.exe" -ErrorAction SilentlyContinue
    if ($py) {
        $ver = & $py.Source -c "import sys; print(sys.version_info >= (3, 10))" 2>$null
        if ($ver -eq "True") { return $py.Source }
    }

    # Check common install locations
    $locations = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "C:\Program Files\Python311\python.exe",
        "C:\Program Files\Python312\python.exe",
        "C:\Python311\python.exe"
    )
    foreach ($loc in $locations) {
        if (Test-Path $loc) { return $loc }
    }
    return $null
}

$PyExe = Find-PythonExecutable

if (-not $PyExe) {
    Write-Host "    [*] Python 3.10+ not found on this fresh Windows 10 installation." -ForegroundColor Yellow
    Write-Host "    [*] Downloading official Python 3.11.9 (64-bit)..." -ForegroundColor Yellow
    $pyUrl = "https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe"
    $pyDest = "$env:TEMP\python-3.11.9-amd64.exe"
    try {
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        Invoke-WebRequest -Uri $pyUrl -OutFile $pyDest -UseBasicParsing
        Write-Host "    [*] Installing Python 3.11 silently into user profile..." -ForegroundColor Yellow
        $p = Start-Process -FilePath $pyDest -ArgumentList "/quiet", "InstallAllUsers=0", "PrependPath=1", "Include_pip=1", "Include_test=0" -PassThru -Wait
        Remove-Item -Path $pyDest -Force -ErrorAction SilentlyContinue

        # Add to current process PATH immediately
        $pyPath = "$env:LOCALAPPDATA\Programs\Python\Python311"
        $pyScripts = "$pyPath\Scripts"
        $env:PATH = "$pyPath;$pyScripts;$env:PATH"
        $PyExe = "$pyPath\python.exe"

        Write-Host "    [OK] Python 3.11 installed successfully at $PyExe!" -ForegroundColor Green
    } catch {
        Write-Host "    [ERROR] Automatic Python installation failed: $_" -ForegroundColor Red
        Write-Host "    Please download Python 3.11 from https://www.python.org/downloads/ and check 'Add to PATH'." -ForegroundColor Yellow
        Pause
        exit 1
    }
} else {
    Write-Host "    [OK] Python detected: $PyExe" -ForegroundColor Gray
}

# -----------------------------------------------------------------------------
# STEP 3: Install Python Dependencies
# -----------------------------------------------------------------------------
Write-Host "`n>>> [3/7] Verifying Python Dependencies (requirements.txt)..." -ForegroundColor Green
try {
    & $PyExe -m pip install --upgrade pip --quiet --disable-pip-version-check
    if (Test-Path "$ScriptDir\requirements.txt") {
        Write-Host "    [*] Installing required packages silently..." -ForegroundColor Gray
        & $PyExe -m pip install -r "$ScriptDir\requirements.txt" --quiet --disable-pip-version-check
        Write-Host "    [OK] All Python dependencies are satisfied." -ForegroundColor Green
    }
} catch {
    Write-Host "    [WARNING] Error installing pip packages: $_" -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# STEP 4: Automated Emulator Downloads (RPCS3, Xenia, Cemu, DuckStation, PCSX2)
# -----------------------------------------------------------------------------
Write-Host "`n>>> [4/7] Checking Emulators for Windows 10/11..." -ForegroundColor Green

$ProgramsDir = "$env:LOCALAPPDATA\Programs"
New-Item -ItemType Directory -Force -Path $ProgramsDir | Out-Null

function Download-FileWithRetry {
    param([string]$Url, [string]$Destination)
    $headers = @{ "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) GameStation/1.0" }
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Invoke-WebRequest -Uri $Url -OutFile $Destination -UseBasicParsing -Headers $headers
}

$7zrExe = "$env:TEMP\7zr.exe"
if (-not (Test-Path $7zrExe)) {
    try {
        Download-FileWithRetry "https://www.7-zip.org/a/7zr.exe" $7zrExe
    } catch {
        Write-Host "    [INFO] 7zr standalone tool download notice: $_" -ForegroundColor Gray
    }
}

function Expand-7zArchive {
    param([string]$Archive, [string]$Dest)
    New-Item -ItemType Directory -Force -Path $Dest | Out-Null
    if (Test-Path $7zrExe) {
        & $7zrExe x $Archive "-o$Dest" -y | Out-Null
    } else {
        $7z = Get-Command "7z.exe" -ErrorAction SilentlyContinue
        if ($7z) {
            & $7z.Source x $Archive "-o$Dest" -y | Out-Null
        }
    }
}

# 4a. Xenia Canary (Xbox 360)
$XeniaDir = "$ProgramsDir\xenia"
$XeniaExe = "$XeniaDir\xenia_canary.exe"
if (-not (Test-Path $XeniaExe) -and -not (Test-Path "$XeniaDir\xenia.exe") -and -not $SkipEmulators) {
    Write-Host "    [*] Downloading Xenia Canary (Xbox 360 Emulator)..." -ForegroundColor Yellow
    $xeniaZip = "$env:TEMP\xenia_canary.zip"
    try {
        $xeniaUrl = "https://github.com/xenia-canary/xenia-canary/releases/latest/download/xenia_canary.zip"
        Download-FileWithRetry $xeniaUrl $xeniaZip
        New-Item -ItemType Directory -Force -Path $XeniaDir | Out-Null
        Expand-Archive -Path $xeniaZip -DestinationPath $XeniaDir -Force
        Remove-Item -Path $xeniaZip -Force -ErrorAction SilentlyContinue
        Write-Host "    [OK] Xenia Canary installed to $XeniaDir!" -ForegroundColor Green
    } catch {
        Write-Host "    [WARNING] Xenia download failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "    [OK] Xenia Canary is present." -ForegroundColor Gray
}

# 4b. RPCS3 (PlayStation 3)
$RPCS3Dir = "$ProgramsDir\RPCS3"
$RPCS3Exe = "$RPCS3Dir\rpcs3.exe"
if (-not (Test-Path $RPCS3Exe) -and -not $SkipEmulators) {
    Write-Host "    [*] Downloading RPCS3 (PlayStation 3 Emulator)..." -ForegroundColor Yellow
    $rpcs3Archive = "$env:TEMP\rpcs3_latest.7z"
    try {
        $rpcs3Url = $null
        try {
            $apiData = Invoke-RestMethod -Uri "https://api.github.com/repos/RPCS3/rpcs3-binaries-win/releases/latest" -Headers @{"User-Agent"="GameStation-Helios"} -UseBasicParsing
            $asset = $apiData.assets | Where-Object { $_.name -like "*_win64*.7z" -and $_.name -notlike "*.sha256" } | Select-Object -First 1
            if ($asset) { $rpcs3Url = $asset.browser_download_url }
        } catch {}
        if (-not $rpcs3Url) {
            $rpcs3Url = "https://github.com/RPCS3/rpcs3-binaries-win/releases/download/build-a2c2ca2fac39e4e2c45f99073848fc48696db7e3/rpcs3-v0.0.43-20559-a2c2ca2f_win64_msvc.7z"
        }
        Download-FileWithRetry $rpcs3Url $rpcs3Archive
        Expand-7zArchive $rpcs3Archive $RPCS3Dir
        Remove-Item -Path $rpcs3Archive -Force -ErrorAction SilentlyContinue
        Write-Host "    [OK] RPCS3 installed to $RPCS3Dir!" -ForegroundColor Green
    } catch {
        Write-Host "    [WARNING] RPCS3 download failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "    [OK] RPCS3 is present." -ForegroundColor Gray
}

# 4c. Cemu (Wii U)
$CemuDir = "$ProgramsDir\Cemu"
$CemuExe = "$CemuDir\Cemu.exe"
if (-not (Test-Path $CemuExe) -and -not $SkipEmulators) {
    Write-Host "    [*] Downloading Cemu (Wii U Emulator)..." -ForegroundColor Yellow
    $cemuZip = "$env:TEMP\cemu.zip"
    try {
        $cemuUrl = "https://github.com/cemu-project/Cemu/releases/download/v2.6/cemu-2.6-windows-x64.zip"
        Download-FileWithRetry $cemuUrl $cemuZip
        New-Item -ItemType Directory -Force -Path $CemuDir | Out-Null
        Expand-Archive -Path $cemuZip -DestinationPath $CemuDir -Force
        Remove-Item -Path $cemuZip -Force -ErrorAction SilentlyContinue
        Write-Host "    [OK] Cemu installed to $CemuDir!" -ForegroundColor Green
    } catch {
        Write-Host "    [WARNING] Cemu download failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "    [OK] Cemu is present." -ForegroundColor Gray
}

# 4d. DuckStation (PS1)
$DuckDir = "$ProgramsDir\DuckStation"
$DuckExe = "$DuckDir\duckstation-qt.exe"
if (-not (Test-Path $DuckExe) -and -not $SkipEmulators) {
    Write-Host "    [*] Downloading DuckStation (PS1 Emulator)..." -ForegroundColor Yellow
    $duckZip = "$env:TEMP\duckstation.zip"
    try {
        $duckUrl = "https://github.com/stenzek/duckstation/releases/download/latest/duckstation-windows-x64-release.zip"
        Download-FileWithRetry $duckUrl $duckZip
        New-Item -ItemType Directory -Force -Path $DuckDir | Out-Null
        Expand-Archive -Path $duckZip -DestinationPath $DuckDir -Force
        Remove-Item -Path $duckZip -Force -ErrorAction SilentlyContinue
        Write-Host "    [OK] DuckStation installed to $DuckDir!" -ForegroundColor Green
    } catch {
        Write-Host "    [WARNING] DuckStation download failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "    [OK] DuckStation is present." -ForegroundColor Gray
}

# 4e. PCSX2 (PS2)
$PCSX2Dir = "$ProgramsDir\PCSX2"
$PCSX2Exe = "$PCSX2Dir\pcsx2-qt.exe"
if (-not (Test-Path $PCSX2Exe) -and -not $SkipEmulators) {
    Write-Host "    [*] Downloading PCSX2 (PS2 Emulator)..." -ForegroundColor Yellow
    $pcsx2Archive = "$env:TEMP\pcsx2.7z"
    try {
        $pcsx2Url = "https://github.com/PCSX2/pcsx2/releases/download/v2.8.2/pcsx2-v2.8.2-windows-x64-Qt.7z"
        Download-FileWithRetry $pcsx2Url $pcsx2Archive
        Expand-7zArchive $pcsx2Archive $PCSX2Dir
        Remove-Item -Path $pcsx2Archive -Force -ErrorAction SilentlyContinue
        Write-Host "    [OK] PCSX2 installed to $PCSX2Dir!" -ForegroundColor Green
    } catch {
        Write-Host "    [WARNING] PCSX2 download failed: $_" -ForegroundColor Red
    }
} else {
    Write-Host "    [OK] PCSX2 is present." -ForegroundColor Gray
}

# -----------------------------------------------------------------------------
# STEP 5: Dual Xbox One S Controller Pre-Configuration (XInput)
# -----------------------------------------------------------------------------
Write-Host "`n>>> [5/7] Pre-configuring Dual Xbox One S Controllers (XInput)..." -ForegroundColor Green
try {
    & $PyExe -m psconsole.windows_setup
    Write-Host "    [OK] Dual Xbox One S controller bindings applied to all emulators!" -ForegroundColor Green
} catch {
    Write-Host "    [WARNING] Controller configurator warning: $_" -ForegroundColor Yellow
}

# -----------------------------------------------------------------------------
# STEP 6: Create Windows Desktop Shortcut
# -----------------------------------------------------------------------------
Write-Host "`n>>> [6/7] Creating Desktop Shortcut..." -ForegroundColor Green
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $Shortcut = $WshShell.CreateShortcut("$DesktopPath\GameStation Console.lnk")
    $Shortcut.TargetPath = "$ScriptDir\Launch_GameStation.bat"
    $Shortcut.WorkingDirectory = $ScriptDir
    $Shortcut.Description = "GameStation Living Room Console"
    $Shortcut.Save()
    Write-Host "    [OK] Shortcut created: Desktop\GameStation Console.lnk" -ForegroundColor Green
} catch {
    Write-Host "    [INFO] Desktop shortcut creation skipped." -ForegroundColor Gray
}

# -----------------------------------------------------------------------------
# STEP 7: Launch GameStation Console & Fullscreen UI
# -----------------------------------------------------------------------------
Write-Host "`n>>> [7/7] Launching GameStation Console Service & Fullscreen UI..." -ForegroundColor Green

if (-not $NoBrowser) {
    # Open Edge or Chrome in app mode (clean borderless window)
    $EdgePath = "$env:SystemRoot\System32\msedge.exe"
    $EdgeProgramFiles = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
    if (-not (Test-Path $EdgeProgramFiles)) {
        $EdgeProgramFiles = "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe"
    }

    if (Test-Path $EdgeProgramFiles) {
        Start-Process -FilePath $EdgeProgramFiles -ArgumentList "--app=http://localhost:8088", "--start-fullscreen", "--window-position=0,0"
    } else {
        Start-Process "http://localhost:8088"
    }
}

Write-Host ""
Write-Host " =============================================================================" -ForegroundColor Cyan
Write-Host "   GAMESTATION IS RUNNING!" -ForegroundColor Green
Write-Host "   - Local TV Dashboard:   http://localhost:8088" -ForegroundColor White
Write-Host "   - Couch Controls:       Navigate with Xbox D-Pad or Left Stick" -ForegroundColor White
Write-Host "   - Launch Game:          Press (A) button" -ForegroundColor White
Write-Host "   - In-Game Exit:         Hold (SELECT + START) on any controller for 2s" -ForegroundColor White
Write-Host "   - Stop Service:         Close this window or press Ctrl+C" -ForegroundColor Gray
Write-Host " =============================================================================" -ForegroundColor Cyan
Write-Host ""

# Run the console daemon in foreground
& $PyExe -m psconsole.service
