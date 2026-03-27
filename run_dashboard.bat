@echo off
REM ARIA dashboard — uses local Python in .python\ (no system Python needed)
cd /d "%~dp0"
title ARIA Dashboard

if not exist ".python\python.exe" (
    echo Local Python not found. Running one-time setup...
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_local_python.ps1"
    if errorlevel 1 (
        echo Setup failed.
        pause
        exit /b 1
    )
    if not exist ".python\python.exe" (
        echo Setup did not create .python\python.exe
        pause
        exit /b 1
    )
)

echo Starting ARIA dashboard... Open http://localhost:8501 in your browser.
.python\python.exe -m streamlit run aria_dashboard.py
pause
