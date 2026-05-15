#Requires -Version 5.1
<#
.SYNOPSIS
  Fuehrt die finale Projekt-Verifikation fuer GridCheck in einem einzigen Schritt aus.

.DESCRIPTION
  Der Skriptlauf spiegelt den praktischen Abschluss-Check des aktuellen Repo-Stands:
  1. Backend-Migrationscheck
  2. Backend-Testlauf
  3. Frontend-Lint
  4. Frontend-Production-Build

  Wichtige Annahmen:
  - `backend/alembic/env.py` verwendet `DATABASE_URL` bzw. `backend/.env`
  - PostgreSQL laeuft lokal auf Port 5433 (siehe docker-compose.yml)

  Aufruf aus dem Repo-Root:
    .\Verify-Finalization.ps1
#>

[CmdletBinding()]
param(
  [switch] $SkipBackend,
  [switch] $SkipFrontend
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot.TrimEnd('\')
$backendPython = Join-Path $root "backend\.venv\Scripts\python.exe"

function Write-Step {
  param(
    [string] $Message,
    [ConsoleColor] $Color = [ConsoleColor]::Cyan
  )

  Write-Host ""
  Write-Host "=== $Message ===" -ForegroundColor $Color
}

function Assert-Command {
  param([string] $Name)

  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Benoetigter Befehl wurde nicht gefunden: $Name"
  }
}

function Invoke-Checked {
  param(
    [string] $Label,
    [scriptblock] $Action
  )

  Write-Host "-> $Label" -ForegroundColor Yellow
  & $Action
  if ($LASTEXITCODE -ne 0) {
    throw "$Label fehlgeschlagen (ExitCode $LASTEXITCODE)."
  }
}

Write-Host "GridCheck Final Verification" -ForegroundColor Green
Write-Host "Repo: $root"

Assert-Command python
if (-not $SkipFrontend) {
  Assert-Command npm
}

$defaultPostgresUrl = "postgresql+psycopg2://gridcheck:gridcheck_dev_2026@localhost:5433/gridcheck_test"
$env:TEST_DATABASE_URL = if ($env:TEST_DATABASE_URL) { $env:TEST_DATABASE_URL } else { $defaultPostgresUrl }
$env:DATABASE_URL = if ($env:DATABASE_URL) { $env:DATABASE_URL } else { $env:TEST_DATABASE_URL }

if ($env:DATABASE_URL -notmatch "^postgres(ql)?(\+.+)?://") {
  throw "DATABASE_URL muss auf PostgreSQL zeigen. Aktuell gesetzt: $env:DATABASE_URL"
}

$env:APP_ENV = "test"
$env:JWT_SECRET = "verify-finalization-secret-32-characters-min"
$env:JWT_REFRESH_SECRET = "verify-finalization-refresh-secret-32"
$env:TRUSTED_HOSTS = "localhost,127.0.0.1,testserver"
$env:AUTO_CREATE_SCHEMA = "false"

try {
  if (-not $SkipBackend) {
    Write-Step "Backend"
    Push-Location (Join-Path $root "backend")
    try {
      $pythonCmd = if (Test-Path $backendPython) { $backendPython } else { "python" }
      Write-Host "Backend Python: $pythonCmd" -ForegroundColor DarkGray
      Invoke-Checked "Ensure PostgreSQL verify database exists" {
        & $pythonCmd -c "from tests.postgres_test_utils import get_test_database_url, ensure_postgres_database_exists; ensure_postgres_database_exists(get_test_database_url())"
      }
      Invoke-Checked "Alembic upgrade head" { & $pythonCmd -m alembic upgrade head }
      Invoke-Checked "Pytest critical backend suite" {
        & $pythonCmd -m pytest tests/test_auth_projects_api.py tests/test_stakeholder_reports_vnb_invest.py tests/test_billing_package_access.py
      }
    }
    finally {
      Pop-Location
    }
  }

  if (-not $SkipFrontend) {
    Write-Step "Frontend"
    Push-Location (Join-Path $root "frontend")
    try {
      Invoke-Checked "npm run lint" { npm run lint }
      Invoke-Checked "npm run build" { npm run build }
    }
    finally {
      Pop-Location
    }
  }

  Write-Step "Ergebnis" Green
  Write-Host "Alle aktivierten Verifikationsschritte wurden erfolgreich abgeschlossen." -ForegroundColor Green
  Write-Host "Naechster sinnvoller Schritt: CI-Lauf bzw. PR-Checks beobachten."
}
catch {
  Write-Step "Fehler" Red
  Write-Host $_.Exception.Message -ForegroundColor Red
  exit 1
}
