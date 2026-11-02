<#
.SYNOPSIS
    Real-time PowerShell diagnostic tool to observe disc insertion and removal events.
#>

Write-Host "Monitoring optical drive events (Press Ctrl+C to stop)..." -ForegroundColor Cyan
$query = "SELECT * FROM __InstanceModificationEvent WITHIN 1 WHERE TargetInstance ISA 'Win32_LogicalDisk' AND TargetInstance.DriveType = 5"

$watcher = New-Object System.Management.ManagementEventWatcher($query)
while ($true) {
    $e = $watcher.WaitForNextEvent()
    $target = $e.TargetInstance
    $drive = $target.DeviceID
    $vol = $target.VolumeName
    $size = $target.Size

    if ($size -and [int64]$size -gt 0) {
        Write-Host "[INSERTION] Disc mounted on $drive (Label: $vol, Size: $([math]::Round($size/1MB)) MB)" -ForegroundColor Green
    } else {
        Write-Host "[REMOVAL] Disc removed or tray opened on $drive" -ForegroundColor Yellow
    }
}
