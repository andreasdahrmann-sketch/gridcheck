# GridCheck: Prueft, ob das Vercel-Frontend einen Railway-Backend-Proxy hat.
# Die echte Railway-URL steht NICHT in Response-Headern - nur in Railway UI + Vercel BACKEND_URL.
#
#   .\scripts\where-is-my-backend.ps1
#   .\scripts\where-is-my-backend.ps1 -FrontendUrl "https://gridcheck.vercel.app"

param(
    [string]$FrontendUrl = "https://gridcheck.vercel.app"
)

$ErrorActionPreference = "Continue"
$frontend = $FrontendUrl.TrimEnd("/")
$healthUrl = "$frontend/api/backend/health"

Write-Host "=== GridCheck: Wo ist mein Backend? ===" -ForegroundColor Cyan
Write-Host "Frontend: $frontend"
Write-Host "Proxy:    $healthUrl"
Write-Host ""

function Show-VercelBackendUrlHint {
    if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
        Write-Host "[Hinweis] Vercel CLI nicht installiert - BACKEND_URL im Dashboard pruefen." -ForegroundColor Yellow
        return
    }
    $frontendDir = Join-Path (Split-Path -Parent $PSScriptRoot) "frontend"
    if (-not (Test-Path (Join-Path $frontendDir ".vercel\project.json"))) {
        Write-Host "[Hinweis] Vercel nicht verlinkt - im Ordner frontend: vercel link --project gridcheck" -ForegroundColor Yellow
        return
    }
    Push-Location $frontendDir
    try {
        $pullFile = ".env.where-is-backend-pull"
        & vercel env pull $pullFile --environment=production --yes 2>$null | Out-Null
        if (Test-Path $pullFile) {
            $line = Get-Content $pullFile | Where-Object { $_ -match '^BACKEND_URL=' } | Select-Object -First 1
            Remove-Item $pullFile -Force -ErrorAction SilentlyContinue
            if ($line -eq 'BACKEND_URL=""' -or $line -eq "BACKEND_URL=''") {
                Write-Host "[WARN] Vercel Production: BACKEND_URL ist LEER - bitte in Settings setzen + Redeploy." -ForegroundColor Red
            } elseif ($line -match '^BACKEND_URL=(.+)$') {
                $val = $Matches[1].Trim('"').Trim("'")
                if ($val) {
                    Write-Host "[OK] Vercel Production BACKEND_URL gesetzt (Origin): $val" -ForegroundColor Green
                } else {
                    Write-Host "[WARN] Vercel Production: BACKEND_URL leer." -ForegroundColor Red
                }
            }
        }
    } finally {
        Pop-Location
    }
}

try {
    $response = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 25 -Method GET
    Write-Host "[OK] Proxy HTTP $($response.StatusCode)" -ForegroundColor Green
    $snippet = $response.Content
    if ($snippet.Length -gt 120) { $snippet = $snippet.Substring(0, 120) + "..." }
    Write-Host "     Body: $snippet"

    $railwayHeaders = $response.Headers.GetEnumerator() | Where-Object {
        $_.Key -like "X-Railway*"
    }
    if ($railwayHeaders) {
        Write-Host ""
        Write-Host "Railway-Hinweise (Hostname steht hier NICHT):" -ForegroundColor DarkGray
        foreach ($h in $railwayHeaders) {
            Write-Host "  $($h.Key): $($h.Value)"
        }
        Write-Host ""
        Write-Host "=> Backend laeuft auf Railway. Die HTTPS-Origin steht in:" -ForegroundColor Cyan
        Write-Host "   1) Railway -> Service backend -> Settings -> Networking -> Public URL"
        Write-Host "   2) Vercel -> gridcheck -> Settings -> Environment Variables -> BACKEND_URL"
    } else {
        Write-Host ""
        Write-Host "[WARN] Keine X-Railway-* Header - Proxy zeigt evtl. nicht auf Railway." -ForegroundColor Yellow
    }
} catch {
    $code = $null
    if ($_.Exception.Response) { $code = [int]$_.Exception.Response.StatusCode }
    Write-Host "[FAIL] Proxy HTTP $code - $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Typisch: BACKEND_URL in Vercel fehlt/leer oder Railway-Service down." -ForegroundColor Yellow
}

Write-Host ""
Show-VercelBackendUrlHint

Write-Host ""
Write-Host "Doku: docs/RAILWAY_URL_PERSIST.md" -ForegroundColor DarkGray
Write-Host "Direkt-Health (RAILWAY-HOST aus Railway Networking einsetzen):" -ForegroundColor DarkGray
Write-Host "  Invoke-WebRequest -Uri https://RAILWAY-HOST/health -UseBasicParsing"
