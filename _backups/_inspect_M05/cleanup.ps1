$ErrorActionPreference = "Continue"
$log = ".\_backups\cleanup-$(Get-Date -Format yyyyMMdd-HHmmss).log"
New-Item -ItemType Directory -Path .\_backups -Force | Out-Null
Start-Transcript -Path $log -Force | Out-Null

Write-Host "=== 0) Package-Check ===" -ForegroundColor Cyan
if (Test-Path .\package-lock.json) { Write-Host "lock size: $((Get-Item .\package-lock.json).Length) B"; Get-Content .\package-lock.json }
Get-ChildItem -Recurse -Filter package.json -ErrorAction SilentlyContinue | Select-Object FullName

Write-Host "`n=== 1) M1-Backup ===" -ForegroundColor Cyan
$zip = ".\_backups\M1-baseline-$(Get-Date -Format yyyyMMdd-HHmmss).zip"
$src = @('.\engine','.\rules','.\.cursor','.\docs','.\tests') | Where-Object { Test-Path $_ }
Compress-Archive -Path $src -DestinationPath $zip -Force
Write-Host "ZIP: $zip  Size: $((Get-Item $zip).Length) B"

Write-Host "`n=== 2) Legacy-Struktur ===" -ForegroundColor Cyan
'_legacy','_legacy\dumps','_legacy\old-frontend','_legacy\old-backend','_legacy\old-backups' | ForEach-Object {
    New-Item -ItemType Directory -Path ".\$_" -Force | Out-Null
}

Write-Host "`n=== 3) Ordner verschieben ===" -ForegroundColor Cyan
$moves = @{
    'backend'='_legacy\old-backend'; 'frontend'='_legacy\old-frontend'
    'frontend-new'='_legacy\old-frontend'; 'frontend-TRASH'='_legacy\old-frontend'
    'backups'='_legacy\old-backups'; 'backup_20260416_220920'='_legacy\old-backups'
    'backup_rules_20260420_2324'='_legacy\old-backups'; '_archiv'='_legacy'
}
foreach ($s in $moves.Keys) {
    if (Test-Path ".\$s") { Move-Item ".\$s" ".\$($moves[$s])\" -Force; Write-Host "OK  $s -> $($moves[$s])" }
    else { Write-Host "SKIP $s (fehlt)" }
}

Write-Host "`n=== 4) Leere Ordner entfernen ===" -ForegroundColor Cyan
foreach ($d in '.agents','.github','app') {
    if ((Test-Path ".\$d") -and -not (Get-ChildItem ".\$d" -Recurse -File)) {
        Remove-Item ".\$d" -Recurse -Force; Write-Host "DEL $d"
    }
}

Write-Host "`n=== 5) Root-Dumps nach _legacy\dumps\ ===" -ForegroundColor Cyan
$dumps = Get-ChildItem -File | Where-Object {
    $_.Name -match '_dump\.txt$' -or
    $_.Name -in @('BACKEND_DUMP.txt','CODE_DUMP.txt','backup_form.txt','diagnosis.py.txt','test-output.txt','struktur.txt','dump.ps1')
}
$dumps | ForEach-Object { Move-Item $_.FullName .\_legacy\dumps\ -Force; Write-Host "MV $($_.Name)" }

Write-Host "`n=== 6) Test-Files -> tests\ ===" -ForegroundColor Cyan
'test.js','test-evaluate.js','test-validator.js','test-netzdiagnose.js' | ForEach-Object {
    if (Test-Path ".\$_") { Move-Item ".\$_" .\tests\ -Force; Write-Host "MV $_" }
}

Write-Host "`n=== 7) Dokus -> docs\ ===" -ForegroundColor Cyan
'PROJECT_STATUS.md','PROJEKTPLAN.md','ZUSAMMENFASSUNG_v3.md' | ForEach-Object {
    if (Test-Path ".\$_") { Move-Item ".\$_" .\docs\ -Force; Write-Host "MV $_" }
}

Write-Host "`n=== 8) gridcheck.html (erste 10 Zeilen) ===" -ForegroundColor Cyan
if (Test-Path .\gridcheck.html) { Get-Content .\gridcheck.html -TotalCount 10 }

Write-Host "`n=== 9) Finaler Stand ===" -ForegroundColor Cyan
Write-Host "-- Ordner --"; Get-ChildItem -Directory | Select-Object -ExpandProperty Name
Write-Host "-- Root-Dateien --"; Get-ChildItem -File | Select-Object Name, Length | Format-Table -AutoSize

Stop-Transcript | Out-Null
Write-Host "`nLog: $log" -ForegroundColor Green
