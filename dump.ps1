# GridCheck Project Dump Generator
# Generiert FULL_PROJECT_DUMP.txt mit allen relevanten Dateien

$root = "C:\Users\andre\gridcheck"
$out = "$root\FULL_PROJECT_DUMP.txt"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Header
@"
========================================
GRIDCHECK FULL PROJECT DUMP
Generated: $timestamp
========================================

"@ | Set-Content $out -Encoding UTF8

# Projektstruktur
"=== VERZEICHNISSTRUKTUR ===" | Add-Content $out
Get-ChildItem -Path $root -Recurse -Depth 4 -Exclude node_modules,.next,__pycache__,.git,backups,.venv,venv,dist,.turbo | 
    Where-Object { $_.FullName -notmatch '(node_modules|\.next|__pycache__|\.git\\|backups|\.venv|venv|dist|\.turbo)' } |
    ForEach-Object {
        $indent = "  " * ($_.FullName.Replace($root, "").Split("\").Count - 2)
        "$indent$($_.Name)$(if($_.PSIsContainer){'/'} else {''})"
    } | Add-Content $out

"`n" | Add-Content $out

# Relevante Dateien sammeln
$extensions = @("*.tsx","*.ts","*.py","*.json","*.toml","*.yaml","*.yml","*.md","*.css","*.sql")
$excludeDirs = @("node_modules",".next","__pycache__",".git","backups",".venv","venv","dist",".turbo")

$files = Get-ChildItem -Path $root -Recurse -Include $extensions |
    Where-Object { 
        $path = $_.FullName
        $skip = $false
        foreach($d in $excludeDirs) {
            if($path -match [regex]::Escape($d)) { $skip = $true; break }
        }
        -not $skip -and $_.Length -lt 100KB
    } |
    Sort-Object FullName

# package.json und config zuerst
foreach($file in $files) {
    $rel = $file.FullName.Replace("$root\", "")
    "`n{'='*60}" | Add-Content $out
    "FILE: $rel" | Add-Content $out
    "{'='*60}" | Add-Content $out
    Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue | Add-Content $out
}

# Installed packages
"`n$('='*60)" | Add-Content $out
"INSTALLED NPM PACKAGES (frontend)" | Add-Content $out
"$('='*60)" | Add-Content $out
if(Test-Path "$root\frontend\package.json") {
    Get-Content "$root\frontend\package.json" -Raw | Add-Content $out
}

"`n$('='*60)" | Add-Content $out
"INSTALLED PIP PACKAGES (backend)" | Add-Content $out
"$('='*60)" | Add-Content $out
if(Test-Path "$root\backend\requirements.txt") {
    Get-Content "$root\backend\requirements.txt" -Raw | Add-Content $out
}

$size = [math]::Round((Get-Item $out).Length / 1KB, 1)
Write-Host "Dump generiert: $out ($size KB)" -ForegroundColor Green
Write-Host "Dateien erfasst: $($files.Count)" -ForegroundColor Cyan
