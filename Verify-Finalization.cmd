@echo off
setlocal
powershell -ExecutionPolicy Bypass -File "%~dp0Verify-Finalization.ps1" %*
exit /b %ERRORLEVEL%
