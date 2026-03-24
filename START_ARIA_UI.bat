@echo off
setlocal

echo ============================================================
echo  ARIA-OS UI Launcher
echo ============================================================

REM --- Python server ---
echo [1/2] Starting FastAPI server on http://localhost:8000 ...
start "ARIA Server" cmd /k "python -m uvicorn aria_server:app --host 0.0.0.0 --port 8000 --reload"

REM --- Node UI ---
echo [2/2] Starting Vite dev server on http://localhost:5173 ...
cd aria-ui

IF NOT EXIST node_modules (
    echo Installing Node dependencies...
    npm install --legacy-peer-deps
)

start "ARIA UI" cmd /k "npm run dev"

echo.
echo UI: http://localhost:5173
echo API: http://localhost:8000/docs
echo.
echo Close the two terminal windows to stop.
endlocal
