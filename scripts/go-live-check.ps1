# GridCheck Go-Live Check (Frontend + Backend URLs)
# Beispiel:
#   .\scripts\go-live-check.ps1 -FrontendUrl "https://gridcheck-xxx.vercel.app" -BackendUrl "https://xxx.up.railway.app"

param(
    [Parameter(Mandatory = $true)]
    [string]$FrontendUrl,
    [Parameter(Mandatory = $true)]
    [string]$BackendUrl
)

$ErrorActionPreference = "Continue"
$frontend = $FrontendUrl.TrimEnd("/")
$backend = $BackendUrl.TrimEnd("/")

function Test-Url {
    param([string]$Label, [string]$Url, [int[]]$OkStatuses = @(200))
    try {
        $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 20 -Method GET
        $ok = $OkStatuses -contains $r.StatusCode
        if ($ok) {
            Write-Host "[OK] $Label ($($r.StatusCode))" -ForegroundColor Green
        } else {
            Write-Host "[FAIL] $Label HTTP $($r.StatusCode)" -ForegroundColor Red
        }
        return $ok
    } catch {
        Write-Host "[FAIL] $Label – $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

function Test-RegisterProbe {
    param([string]$Url)
    try {
        $body = '{"email":"probe@example.com","password":"short","role":"projektierer"}'
        $r = Invoke-WebRequest -Uri $Url -Method POST -Body $body -ContentType "application/json" -UseBasicParsing -TimeoutSec 25
        Write-Host "[FAIL] Register-Probe erwartet 400/422, bekam $($r.StatusCode)" -ForegroundColor Red
        return $false
    } catch {
        $code = $null
        if ($_.Exception.Response) {
            $code = [int]$_.Exception.Response.StatusCode
        }
        if ($code -in 400, 422) {
            Write-Host "[OK] Register-Probe (HTTP $code – Route erreichbar)" -ForegroundColor Green
            return $true
        }
        Write-Host "[FAIL] Register-Probe HTTP $code – $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

Write-Host "=== GridCheck Go-Live Check ===" -ForegroundColor Cyan
Write-Host "Backend:  $backend"
Write-Host "Frontend: $frontend"
Write-Host ""

$all = $true
$all = (Test-Url "Backend /health" "$backend/health") -and $all
$all = (Test-Url "Frontend Proxy /api/backend/health" "$frontend/api/backend/health") -and $all
$all = (Test-RegisterProbe "$frontend/api/auth/register") -and $all

if ($all) {
    Write-Host ""
    Write-Host "Alle Checks bestanden. Register: $frontend/register" -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Checks fehlgeschlagen. Siehe docs/GO_LIVE_OHNE_DNS.md" -ForegroundColor Yellow
exit 1
