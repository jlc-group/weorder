@echo off
title WeOrder Backend - Auto Restart
cd /d %~dp0
set APP_PORT=9203

:start
echo [%date% %time%] Starting WeOrder Backend on port %APP_PORT%...
.venv\Scripts\python.exe -m uvicorn main:app --port %APP_PORT% --host 0.0.0.0

echo.
echo [%date% %time%] Backend stopped with exit code %ERRORLEVEL%
echo Restarting in 5 seconds... Press Ctrl+C twice to stop.
timeout /t 5 /nobreak
goto start
