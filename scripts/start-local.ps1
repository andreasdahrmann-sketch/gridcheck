# GridCheck – lokale Entwicklung starten (Postgres + Anleitung Backend/Frontend)
# Ausfuehren: .\scripts\start-local.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "=== GridCheck lokal ===" -ForegroundColor Cyan

Set-Location $Root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker fehlt. Postgres manuell auf Port 5433 bereitstellen." -ForegroundColor Yellow
} else {
    Write-Host "Starte Postgres (docker compose)..." -ForegroundColor Gray
    docker compose up -d postgres
    if ($LASTEXITCODE -ne 0) {
        Write-Host "docker compose fehlgeschlagen." -ForegroundColor Red
        exit 1
    }
    Write-Host "Postgres laeuft auf localhost:5433" -ForegroundColor Green
}

$backendEnv = Join-Path $Root "backend\.env"
$backendExample = Join-Path $Root "backend\.env.example"
if (-not (Test-Path $backendEnv)) {
    Copy-Item $backendExample $backendEnv
    Write-Host "backend\.env aus .env.example erstellt – JWT_SECRET und JWT_REFRESH_SECRET setzen!" -ForegroundColor Yellow
}

$frontendEnv = Join-Path $Root "frontend\.env.local"
$frontendExample = Join-Path $Root "frontend\.env.example"
if (-not (Test-Path $frontendEnv)) {
    Copy-Item $frontendExample $frontendEnv
    Write-Host "frontend\.env.local erstellt (BACKEND_URL=http://localhost:8000)" -ForegroundColor Green
}

Write-Host ""
Write-Host "Terminal 1 – Backend:" -ForegroundColor Cyan
Write-Host "  cd $Root\backend"
Write-Host "  .\.venv\Scripts\python.exe -m alembic upgrade head"
Write-Host "  .\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000"
Write-Host ""
Write-Host "Terminal 2 – Frontend (Node 20):" -ForegroundColor Cyan
Write-Host "  cd $Root\frontend"
Write-Host "  nvm use 20"
Write-Host "  npm run dev"
Write-Host ""
Write-Host "Dann: http://localhost:3000/register  |  Diagnose: http://localhost:3000/api-test" -ForegroundColor Green
