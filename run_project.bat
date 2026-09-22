@echo off
title AI Code Review and Risk Analysis System
echo ======================================================================
echo    AI-POWERED INTELLIGENT CODE REVIEW & RISK ANALYSIS SYSTEM
echo    Batch-13 - Department of Computer Science and Engineering
echo ======================================================================
echo.
echo Starting backend server on http://localhost:8000 ...
echo.
cd /d "%~dp0backend"
start "" "http://localhost:8000"
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
pause
