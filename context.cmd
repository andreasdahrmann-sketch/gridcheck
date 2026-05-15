@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Read-ProjectContext.ps1" -Clipboard
echo Kontext in Zwischenablage. In der KI mit Strg+V einfuegen.
