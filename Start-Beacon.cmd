@echo off
setlocal

cd /d "%~dp0"

echo Starting Beacon BOT from:
echo %CD%
echo.
echo A browser window will open automatically at http://127.0.0.1:8765
echo Keep this terminal window open while Beacon BOT is running.
echo Press Ctrl+C here to stop the local server.
echo.

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:8765'"
powershell -NoProfile -ExecutionPolicy Bypass -File ".\src\Start-Beacon.ps1"
