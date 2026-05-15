# GridCheck Session Context – vor jeder neuen KI-Session ausfuehren
# Aufruf:  .\session-context.ps1 | Set-Clipboard
# Dann den Inhalt in den Cursor-Chat einfuegen.

Write-Output "===== SESSION-START GRIDCHECK ====="
Write-Output "Stand: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
Write-Output ""
Write-Output "REGELN (verbindlich):"
Write-Output "1. Lies alles unten BEVOR du antwortest."
Write-Output "2. Antworten als PowerShell Here-Strings, copy-paste-fertig."
Write-Output "3. Keine Halluzinationen, keine erfundenen Pfade/APIs."
Write-Output "4. Bei Unsicherheit: fragen, nicht raten."
Write-Output "5. Keine Diskussion bereits in DECISIONS.md beschlossener Punkte."
Write-Output "6. Pflichtcheck aus 06-arbeitsweise-gridcheck.mdc Abschnitt 4."
Write-Output ""

Write-Output "===== CURSOR RULES (.mdc) ====="
Get-ChildItem .cursor\rules\*.mdc -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Output "`n----- $($_.Name) -----"
    Get-Content $_.FullName
}

Write-Output "`n===== PROJECT_STATE.md ====="
Get-Content .\PROJECT_STATE.md -ErrorAction SilentlyContinue

Write-Output "`n===== DECISIONS.md ====="
Get-Content .\DECISIONS.md -ErrorAction SilentlyContinue

Write-Output "`n===== ROADMAP.md ====="
Get-Content .\ROADMAP.md -ErrorAction SilentlyContinue

Write-Output "`n===== BACKLOG.md ====="
Get-Content .\BACKLOG.md -ErrorAction SilentlyContinue

Write-Output "`n===== BACKEND-DATEIEN ====="
Get-ChildItem backend -Recurse -Filter *.py -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty FullName

Write-Output "`n===== FRONTEND-DATEIEN ====="
Get-ChildItem frontend -Recurse -Include *.ts,*.tsx,*.json -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty FullName

Write-Output "`n===== GIT LOG (letzte 10) ====="
git log --oneline -10 2>$null

Write-Output "`n===== ENDE SESSION-CONTEXT ====="
