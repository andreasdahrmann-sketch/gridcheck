# Erzeugt Railway-ENV-Vorlage zum Copy-Paste (nicht committen!)
# .\scripts\generate-railway-env.ps1

$jwt = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
$jwt2 = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })

$out = @"
# In Railway -> Backend Service -> Variables einfuegen
APP_ENV=prod
APP_VERSION=v1.0.0
# DATABASE_URL=<von Railway Postgres verlinken>
JWT_SECRET=$jwt
JWT_REFRESH_SECRET=$jwt2
CORS_ORIGINS=https://gridcheck.vercel.app
CORS_ORIGIN_REGEX=^https://[a-z0-9-]+\.vercel\.app$
TRUSTED_HOSTS=*.up.railway.app,*.vercel.app
LOG_LEVEL=INFO
ENABLE_LEGACY_ROUTES=false
"@

$path = Join-Path (Split-Path -Parent $PSScriptRoot) "railway-variables.generated.txt"
Set-Content -Path $path -Value $out -Encoding UTF8
Write-Host "Geschrieben: $path"
Write-Host "DATABASE_URL in Railway manuell verlinken. Datei nicht committen."
