# GridCheck — lokale App starten (Postgres + Backend + Hinweise Frontend)
# Ausfuehren: .\scripts\bootstrap-local.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== GridCheck Bootstrap (lokal) ===" -ForegroundColor Cyan

Set-Location $Root
docker compose up -d postgres redis

$backendEnv = Join-Path $Root "backend\.env"
if (-not (Test-Path $backendEnv)) {
    Copy-Item (Join-Path $Root "backend\.env.example") $backendEnv
}

$jwt = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
$jwt2 = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
$envContent = @"
APP_ENV=dev
APP_VERSION=v0.0.0-local
DATABASE_URL=postgresql+psycopg2://gridcheck:gridcheck_dev_2026@localhost:5433/gridcheck
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
LOG_LEVEL=INFO
JWT_SECRET=$jwt
JWT_REFRESH_SECRET=$jwt2
TRUSTED_HOSTS=localhost,127.0.0.1
REDIS_URL=redis://localhost:6379/0
AUTH_ACCESS_COOKIE=gridcheck_access
AUTH_REFRESH_COOKIE=gridcheck_refresh
AUTH_CSRF_COOKIE=gridcheck_csrf
FREE_CHECKS_LIMIT=3
AUTO_CREATE_SCHEMA=false
PROJECT_UPLOAD_DIR=./uploads
SITE_MARKER_UPLOAD_DIR=./uploads/site_markers
"@
Set-Content -Path $backendEnv -Value $envContent -Encoding UTF8
Write-Host "backend\.env geschrieben (JWT generiert)" -ForegroundColor Green

$frontendEnv = Join-Path $Root "frontend\.env.local"
if (-not (Test-Path $frontendEnv)) {
    @"
BACKEND_URL=http://localhost:8000
NEXT_PUBLIC_APP_NAME=GridCheck
NEXT_PUBLIC_API_BASE=/api/backend
"@ | Set-Content -Path $frontendEnv -Encoding UTF8
}

Set-Location (Join-Path $Root "backend")
& .\.venv\Scripts\python.exe -m alembic upgrade head
Write-Host "Alembic: head" -ForegroundColor Green

Write-Host ""
Write-Host "Terminal 1:" -ForegroundColor Cyan
Write-Host "  cd $Root\backend"
Write-Host "  .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000"
Write-Host ""
Write-Host "Terminal 2 (Node 20):" -ForegroundColor Cyan
Write-Host "  cd $Root\frontend"
Write-Host "  nvm use 20"
Write-Host "  npm run dev"
Write-Host ""
Write-Host "App: http://localhost:3000/register" -ForegroundColor Green
