@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0Start-Local.ps1" %*
exit /b %ERRORLEVEL%
