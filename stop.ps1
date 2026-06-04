# stop.ps1 - Terminate backend (port 3001) and frontend (port 3000) processes

# Stop process on port 3001 (Backend)
$backendPids = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess
if ($backendPids) {
    $backendPids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Write-Host "Stopped backend process(es) on port 3001."
} else {
    Write-Host "No process found on port 3001."
}

# Stop process on port 3000 (Frontend)
$frontendPids = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess
if ($frontendPids) {
    $frontendPids | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Write-Host "Stopped frontend process(es) on port 3000."
} else {
    Write-Host "No process found on port 3000."
}

Write-Host "All services stopped."
