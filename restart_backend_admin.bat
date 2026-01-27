@echo off
:: This script restarts WeOrder Backend with admin privileges
:: Right-click and "Run as Administrator" to use

echo Stopping WeOrder Backend...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq WeOrder*" 2>nul
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :9203 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul

echo Waiting 3 seconds...
timeout /t 3 /nobreak >nul

echo Starting WeOrder Backend...
cd /d %~dp0
start "WeOrder Backend" .venv\Scripts\python.exe -m uvicorn main:app --port 9203 --host 0.0.0.0

echo Done! Backend is starting...
pause
