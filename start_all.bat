@echo off
title Movie Suggestion Automation - Launcher
echo ========================================================
echo   Starting Backend API and Next.js Frontend...
echo ========================================================
start "Backend API (Port 8001)" cmd /k "%~dp0start_backend.bat"
timeout /t 3 /nobreak >nul
start "Frontend UI (Port 3001)" cmd /k "%~dp0start_frontend.bat"
echo Done!
echo Backend:  http://localhost:8001/docs
echo Frontend: http://localhost:3001
