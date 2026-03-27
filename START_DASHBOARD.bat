@echo off
REM Double-click START_DASHBOARD.bat to run the ARIA dashboard.
REM If nothing happens: open Command Prompt, cd to this folder, then type START_DASHBOARD.bat
cd /d "%~dp0"
title ARIA Dashboard
echo.
echo ========================================
echo   ARIA Virtual Test Dashboard Launcher
echo ========================================
echo.

if not exist ".python\python.exe" (
    echo [1/2] Local Python not found. Running one-time setup...
    echo       This will download Python ~25 MB and install streamlit.
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_local_python.ps1"
    if errorlevel 1 (
        echo.
        echo Setup failed. Check the messages above.
        goto :end
    )
    if not exist ".python\python.exe" (
        echo.
        echo Error: Setup did not create .python\python.exe
        goto :end
    )
    echo.
)

.python\python.exe -c "import streamlit" 2>nul
if errorlevel 1 (
    echo [1.5/2] Installing streamlit, pandas, numpy...
    .python\python.exe -m pip install streamlit pandas numpy --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo Pip install failed.
        goto :end
    )
    echo.
)

echo [2/2] Starting Streamlit...
echo.
echo   When you see "Local URL", open that in your browser.
echo   Usually:  http://localhost:8501
echo.
echo   Press Ctrl+C in this window to stop the dashboard.
echo ========================================
echo.

.python\python.exe -m streamlit run aria_dashboard.py

:end
echo.
pause
