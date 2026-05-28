# GridCheck – Beispieldaten seeden und PDF-Reports erzeugen
# Ausfuehren: .\scripts\seed-example-data.ps1
# Optional: .\scripts\seed-example-data.ps1 -SkipDb

param(
    [switch]$SkipDb,
    [string]$OutputDir = "reports"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "=== GridCheck Beispieldaten + PDF ===" -ForegroundColor Cyan

if (Get-Command docker -ErrorAction SilentlyContinue) {
    $pg = docker ps --filter "name=gridcheck-postgres" --format "{{.Names}}" 2>$null
    if (-not $pg) {
        Write-Host "Starte Postgres (docker compose)..." -ForegroundColor Gray
        docker compose up -d postgres
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Postgres konnte nicht gestartet werden." -ForegroundColor Red
            exit 1
        }
    }
}

$backendEnv = Join-Path $Root "backend\.env"
if (-not (Test-Path $backendEnv)) {
    Copy-Item (Join-Path $Root "backend\.env.example") $backendEnv
    Write-Host "backend\.env aus .env.example erstellt – JWT_SECRET setzen!" -ForegroundColor Yellow
}

$python = Join-Path $Root "backend\.venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    Write-Host "backend\.venv fehlt. Einmalig: cd backend; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt" -ForegroundColor Red
    exit 1
}

Write-Host "Alembic Migrationen..." -ForegroundColor Gray
Push-Location (Join-Path $Root "backend")
& $python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Pop-Location
    exit $LASTEXITCODE
}
Pop-Location

$argsList = @("backend\scripts\seed_example_and_export_pdf.py", "--output-dir", $OutputDir)
if ($SkipDb) {
    $argsList += "--skip-db"
}

& $python @argsList
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$primary = Join-Path $Root "$OutputDir\example-gridcheck-report.pdf"
Write-Host ""
Write-Host "Fertig." -ForegroundColor Green
Write-Host "  PDF:     $primary" -ForegroundColor Green
Write-Host "  Login:   demo.seed@gridcheck.example / DemoSeed2026!" -ForegroundColor Green
Write-Host "  App:     http://localhost:3000 (Backend :8000)" -ForegroundColor Green
Write-Host ""
Write-Host "PDF oeffnen:  Start-Process '$primary'" -ForegroundColor Gray
