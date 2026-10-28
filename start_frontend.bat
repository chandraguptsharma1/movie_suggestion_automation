@echo off
title Movie Suggestion Automation - Next.js Frontend
cd /d "%~dp0frontend"
echo ========================================================
echo   Starting Movie Suggestion Automation Frontend (Next.js)...
echo   URL: http://localhost:3001
echo ========================================================
npm.cmd run dev -- -p 3001
pause
