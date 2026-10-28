@echo off
title Movie Shorts Studio - Auto-Pilot Runner
cd /d "%~dp0"

if exist "d:\movie_review\venv\Scripts\python.exe" (
    set "PYTHON_EXE=d:\movie_review\venv\Scripts\python.exe"
) else if exist "backend\venv\Scripts\python.exe" (
    set "PYTHON_EXE=backend\venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

if "%~1"=="" (
    echo ========================================================
    echo   🎬 1-CLICK AUTOPILOT SHORTS GENERATOR
    echo ========================================================
    set /p MOVIE_NAME="Enter Movie Name (e.g. Colony or Inception): "
    "%PYTHON_EXE%" auto_short.py "%MOVIE_NAME%"
) else (
    "%PYTHON_EXE%" auto_short.py %*
)

pause
