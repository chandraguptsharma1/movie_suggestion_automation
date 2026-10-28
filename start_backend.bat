@echo off
title Movie Suggestion Automation - Backend
cd /d "%~dp0backend"
echo ========================================================
echo   Starting Movie Suggestion Automation Backend API...
echo   URL: http://localhost:8001/docs
echo ========================================================
if exist "d:\movie_review\venv\Scripts\python.exe" (
    d:\movie_review\venv\Scripts\python.exe run.py
) else if exist "venv\Scripts\python.exe" (
    venv\Scripts\python.exe run.py
) else (
    python run.py
)
pause
