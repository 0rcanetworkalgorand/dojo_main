# =============================================================================
# 0rca Swarm Dojo — One-Command Local Setup Script
# =============================================================================
# This script bootstraps the entire local development stack:
#   1. Installs backend dependencies (npm install)
#   2. Generates Prisma client and runs database migrations
#   3. Installs frontend dependencies (npm install)
#   4. Starts the backend (Express on port 3001) as a background process
#   5. Starts the frontend (Next.js on port 3000) as a background process
#   6. Polls both services for readiness (30-second timeout each)
#   7. Prints a success summary with service URLs
#
# Usage: .\setup.ps1
# Stop:  .\stop.ps1
# =============================================================================

$ErrorActionPreference = 'Stop'

$RepoRoot = $PSScriptRoot
$BackendDir = Join-Path $RepoRoot "dojo-backend"
$FrontendDir = Join-Path $RepoRoot "dojo-frontend"

# -----------------------------------------------------------------------------
# Step 1: Install backend npm dependencies
# -----------------------------------------------------------------------------
Write-Host "`n[1/7] Installing backend dependencies..." -ForegroundColor Cyan
try {
    Push-Location $BackendDir
    npm install 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "npm install failed in dojo-backend/"
    }
} catch {
    Write-Host "ERROR: npm install failed in dojo-backend/ — $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

# -----------------------------------------------------------------------------
# Step 2: Generate Prisma client and run database migrations
# -----------------------------------------------------------------------------
Write-Host "`n[2/7] Running Prisma generate and migrate..." -ForegroundColor Cyan
try {
    Push-Location $BackendDir
    npx prisma generate 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "prisma generate failed"
    }
    npx prisma migrate dev 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "prisma migrate dev failed"
    }
} catch {
    Write-Host "ERROR: Database setup failed in dojo-backend/ — $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

# -----------------------------------------------------------------------------
# Step 3: Install frontend npm dependencies
# -----------------------------------------------------------------------------
Write-Host "`n[3/7] Installing frontend dependencies..." -ForegroundColor Cyan
try {
    Push-Location $FrontendDir
    npm install 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        throw "npm install failed in dojo-frontend/"
    }
} catch {
    Write-Host "ERROR: npm install failed in dojo-frontend/ — $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    Pop-Location
}

# -----------------------------------------------------------------------------
# Step 4: Start backend as background process (port 3001)
# -----------------------------------------------------------------------------
Write-Host "`n[4/7] Starting backend on port 3001..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory $BackendDir

# -----------------------------------------------------------------------------
# Step 5: Start frontend as background process (port 3000)
# -----------------------------------------------------------------------------
Write-Host "`n[5/7] Starting frontend on port 3000..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath "npm" -ArgumentList "run","dev" -WorkingDirectory $FrontendDir

# -----------------------------------------------------------------------------
# Step 6: Poll backend (http://localhost:3001) with 30-second timeout
# -----------------------------------------------------------------------------
Write-Host "`n[6/7] Waiting for backend to be ready..." -ForegroundColor Cyan
$backendUrl = "http://localhost:3001"
$maxAttempts = 15
$attempt = 0
$backendReady = $false

while ($attempt -lt $maxAttempts) {
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri $backendUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            $backendReady = $true
            break
        }
    } catch {
        # Service not ready yet
    }
    Start-Sleep -Seconds 2
}

if (-not $backendReady) {
    Write-Host "ERROR: Backend failed to start within 30 seconds ($backendUrl)" -ForegroundColor Red
    exit 1
}
Write-Host "  Backend is ready!" -ForegroundColor Green

# -----------------------------------------------------------------------------
# Step 7: Poll frontend (http://localhost:3000) with 30-second timeout
# -----------------------------------------------------------------------------
Write-Host "`n[7/7] Waiting for frontend to be ready..." -ForegroundColor Cyan
$frontendUrl = "http://localhost:3000"
$attempt = 0
$frontendReady = $false

while ($attempt -lt $maxAttempts) {
    $attempt++
    try {
        $response = Invoke-WebRequest -Uri $frontendUrl -UseBasicParsing -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
            $frontendReady = $true
            break
        }
    } catch {
        # Service not ready yet
    }
    Start-Sleep -Seconds 2
}

if (-not $frontendReady) {
    Write-Host "ERROR: Frontend failed to start within 30 seconds ($frontendUrl)" -ForegroundColor Red
    exit 1
}
Write-Host "  Frontend is ready!" -ForegroundColor Green

# -----------------------------------------------------------------------------
# Success Summary
# -----------------------------------------------------------------------------
Write-Host "`n=============================================" -ForegroundColor Green
Write-Host " 0rca Swarm Dojo — All services running!" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Green
Write-Host "  Backend:  $backendUrl" -ForegroundColor White
Write-Host "  Frontend: $frontendUrl" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "  To stop all services: .\stop.ps1" -ForegroundColor Yellow
Write-Host "=============================================`n" -ForegroundColor Green
