#Requires -Version 5.1
<#
.SYNOPSIS
  Startet die lokale GridCheck-Entwicklungsumgebung auf Windows.

.DESCRIPTION
  Der Skriptlauf hilft beim lokalen MVP-Start:
  1. Docker-Dienste (Postgres, Redis) starten
  2. `backend/.env` aus `.env.example` anlegen, falls noch nicht vorhanden
  3. Backend-Venv anlegen und Dependencies installieren
  4. `alembic upgrade head` gegen die aktive DATABASE_URL ausfuehren
  5. Hinweise fuer Backend- und Frontend-Start ausgeben

  Der Skriptlauf startet absichtlich keine langlaufenden Dev-Server automatisch,
  damit Sie Backend und Frontend kontrolliert in eigenen Terminals starten koennen.
#>

[CmdletBinding()]
param(
  [switch] $SkipDocker,
  [switch] $SkipInstall
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot.TrimEnd('\')
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"
$backendEnv = Join-Path $backend ".env"
$backendEnvExample = Join-Path $backend ".env.example"
$venvPython = Join-Path $backend ".venv\Scripts\python.exe"
$activateScript = Join-Path $backend ".venv\Scripts\activate"

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

Write-Host "GridCheck Local Startup Helper" -ForegroundColor Green
Write-Host "Repo: $root"

Assert-Command python
Assert-Command npm
if (-not $SkipDocker) {
  Assert-Command docker
}

if (-not $SkipDocker) {
  Write-Step "Docker"
  Push-Location $root
  try {
    Invoke-Checked "docker compose up -d postgres redis" {
      docker compose up -d postgres redis
    }
  }
  finally {
    Pop-Location
  }
}

Write-Step "Backend Vorbereitung"
if (-not (Test-Path $backendEnv)) {
  Copy-Item $backendEnvExample $backendEnv
  Write-Host "backend/.env wurde aus .env.example erzeugt." -ForegroundColor Green
} else {
  Write-Host "backend/.env existiert bereits." -ForegroundColor DarkGray
}

Push-Location $backend
try {
  if (-not (Test-Path $venvPython)) {
    Invoke-Checked "Python venv erstellen" { python -m venv .venv }
  } else {
    Write-Host "-> Vorhandene Backend-Venv wird verwendet" -ForegroundColor Yellow
  }

  if (-not $SkipInstall) {
    Invoke-Checked "Backend Dependencies installieren" {
      & $venvPython -m pip install -r requirements.txt
    }
  }

  if (-not $env:DATABASE_URL) {
    Write-Host "Hinweis: DATABASE_URL ist in der Shell nicht gesetzt. Alembic nutzt backend/.env." -ForegroundColor DarkGray
  }

  Invoke-Checked "Alembic upgrade head" {
    & $venvPython -m alembic upgrade head
  }
}
finally {
  Pop-Location
}

Write-Step "Naechste Schritte" Green
Write-Host "Backend starten:" -ForegroundColor Green
Write-Host "  cd `"$backend`""
Write-Host "  .\.venv\Scripts\activate"
Write-Host "  uvicorn main:app --reload"
Write-Host ""
Write-Host "Frontend starten:" -ForegroundColor Green
Write-Host "  cd `"$frontend`""
Write-Host "  npm install"
Write-Host "  npm run dev"
Write-Host ""
Write-Host "Frontend: http://localhost:3000"
Write-Host "Backend:  http://localhost:8000"
