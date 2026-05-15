#Requires -Version 5.1
<#
.SYNOPSIS
  Sammelt alle .md / .mdc im Repo (außer Cache- und Build-Ordner) und gibt sie als ein Textband aus.

.EXAMPLE
  .\Read-ProjectContext.ps1

.EXAMPLE
  .\Read-ProjectContext.ps1 -OutFile context.txt

.EXAMPLE
  .\Read-ProjectContext.ps1 -Clipboard
#>
param(
  [string] $OutFile,
  [switch] $Clipboard
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot.TrimEnd('\')

# Pfade, die kein Arbeitskontext sind (würden Umfang sprengen oder sind Artefakte)
$excludePathFragments = @(
  '\node_modules\', '\.git\', '\__pycache__\', '\.pytest_cache\', '\.mypy_cache\', '\.ruff_cache\',
  '\dist\', '\build\', '\.venv\', '\venv\', '\.next\', '\coverage\', '\.turbo\', '\.cache\',
  '\_milestone_backups\', '\rules_backup'
)

function Test-IsExcludedContextFile {
  param([string] $FullPath)
  foreach ($frag in $excludePathFragments) {
    if ($FullPath.Contains($frag)) { return $true }
  }
  return $false
}

# Nur relevante Ordner (kein Repo-weites Rekurs — sonst sehr langsam)
$pathSet = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)

function Add-OneMarkdownTree {
  param(
    [string] $RelativeDir,
    [switch] $Recurse
  )
  $base = if ([string]::IsNullOrEmpty($RelativeDir)) { $root } else { Join-Path $root $RelativeDir }
  if (-not (Test-Path -LiteralPath $base)) { return }
  $enum = if ($Recurse) {
    Get-ChildItem -LiteralPath $base -Recurse -File -ErrorAction SilentlyContinue
  } else {
    Get-ChildItem -LiteralPath $base -File -ErrorAction SilentlyContinue
  }
  foreach ($item in $enum) {
    if ($item.Extension -notin @('.md', '.mdc')) { continue }
    if (Test-IsExcludedContextFile $item.FullName) { continue }
    [void]$pathSet.Add($item.FullName)
  }
}

Write-Host "Sammle .md / .mdc (gezielte Pfade) ..."
Add-OneMarkdownTree -RelativeDir '' -Recurse:$false
foreach ($dir in @('.cursor\rules', '.cursor\skills', 'docs', 'skills', 'backend\compliance')) {
  Add-OneMarkdownTree -RelativeDir $dir -Recurse
}
foreach ($top in @('frontend', 'backend')) {
  Add-OneMarkdownTree -RelativeDir $top -Recurse:$false
}

$files = $pathSet |
  ForEach-Object { Get-Item -LiteralPath $_ } |
  Sort-Object { $_.FullName }

Write-Host "Gefunden: $($files.Count) Dateien. Lese Inhalt..."
$blocks = [System.Collections.Generic.List[string]]::new()
$readErrors = [System.Collections.Generic.List[string]]::new()

foreach ($f in $files) {
  $rel = $f.FullName.Substring($root.Length).TrimStart('\') -replace '\\', '/'
  try {
    $content = [System.IO.File]::ReadAllText($f.FullName, [System.Text.UTF8Encoding]::new($false))
  } catch {
    try {
      $content = Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8
    } catch {
      [void]$readErrors.Add($rel)
      continue
    }
  }
  $sep = "`n=== $rel ===`n"
  [void]$blocks.Add($sep + $content)
}

$header = @"
#
# Gridcheck - Projekt-Kontext (md/mdc in Root, .cursor/rules, .cursor/skills, docs, skills, backend/compliance, optional frontend|backend/*.md)
# Dateien: $($files.Count)
# Root: $root
# Zeit: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
#
"@

$body = ($blocks -join "`n`n")
$footer = ''
if ($readErrors.Count -gt 0) {
  $footer = "`n`n# Nicht lesbar:`n# " + ($readErrors -join "`n# ")
}

$out = $header + $body + $footer

if ($Clipboard) {
  # clip.exe per stdin: schneller als Tempdatei; Set-Clipboard bei grossen Texten unzuverlaessig
  $clip = Join-Path $env:SystemRoot 'System32\clip.exe'
  if (-not (Test-Path -LiteralPath $clip)) {
    $clip = 'clip.exe'
  }
  Write-Host "Kopiere $($out.Length) Zeichen in Zwischenablage (clip.exe)..."
  $out | & $clip
  Write-Host "In Zwischenablage kopiert ($($out.Length) Zeichen)."
}

if ($OutFile) {
  $dest = if ([System.IO.Path]::IsPathRooted($OutFile)) { $OutFile } else { Join-Path $root $OutFile }
  Set-Content -LiteralPath $dest -Value $out -Encoding UTF8
  Write-Host "Geschrieben: $dest"
}

if (-not $OutFile -and -not $Clipboard) {
  Write-Output $out
}
