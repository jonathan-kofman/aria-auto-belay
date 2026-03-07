@echo off
REM ============================================================
REM  ARIA TEST DAY LAUNCHER
REM  Double-click this before every test session.
REM  Runs pre-flight checks, then opens the dashboard.
REM ============================================================
cd /d "%~dp0"
title ARIA Test Day

echo.
echo ============================================================
echo   ARIA TEST DAY LAUNCHER
echo   %DATE% %TIME%
echo ============================================================
echo.

REM ── Find Python ─────────────────────────────────────────────
set PYTHON=
if exist ".python\python.exe" set PYTHON=.python\python.exe
if not defined PYTHON (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    ) do (
        if exist %%P (
            set PYTHON=%%~P
            goto :found_python
        )
    )
)
:found_python
if not defined PYTHON (
    echo ERROR: Python not found.
    echo Run setup_local_python.ps1 first, or install Python 3.11+
    pause
    exit /b 1
)
echo [OK] Python: %PYTHON%

REM ── Check dependencies ──────────────────────────────────────
echo.
echo [1/5] Checking dependencies...
%PYTHON% -c "import streamlit, pandas, numpy, plotly" 2>nul
if errorlevel 1 (
    echo       Installing missing packages...
    %PYTHON% -m pip install streamlit pandas numpy plotly reportlab --quiet
    if errorlevel 1 (
        echo ERROR: Could not install dependencies.
        pause
        exit /b 1
    )
)
echo [OK] Dependencies ready

REM ── Run constants sync check ────────────────────────────────
echo.
echo [2/5] Checking firmware/model sync...
if exist "tools\aria_constants_sync.py" (
    %PYTHON% tools\aria_constants_sync.py --ci --repo-root . 2>nul
    if errorlevel 1 (
        echo.
        echo *** WARNING: Firmware constants may not match Python model ***
        echo     Run: python tools\aria_constants_sync.py --verbose
        echo     to see what changed. Simulation results may not match hardware.
        echo.
        choice /C YN /M "Continue anyway?"
        if errorlevel 2 exit /b 1
    ) else (
        echo [OK] Firmware/model sync OK
    )
) else (
    echo [--] aria_constants_sync.py not found in tools\ - skipping
)

REM ── Run physics smoke tests ──────────────────────────────────
echo.
echo [3/5] Running physics smoke tests...
%PYTHON% -c "
from aria_models import simulate_static_pawl, simulate_drop_test, simulate_false_trip_check, AriaStateMachine, Inputs
df = simulate_static_pawl([1000, 8000])
assert df['min_sf'].min() > 0, 'Static model broken'
df2, s = simulate_drop_test()
assert s['trigger_fired'], 'Drop model: trigger did not fire'
assert s['arrest_distance_mm'] < 813, 'Drop model: arrest distance too high'
r = simulate_false_trip_check(accel_g=0.3)
assert r['passed'], 'False trip check failed'
sm = AriaStateMachine()
out = sm.step(Inputs(tension_N=50.0, time_s=0.1))
assert out.state.name == 'CLIMBING', 'State machine broken'
print('All physics tests passed')
" 2>&1
if errorlevel 1 (
    echo.
    echo *** ERROR: Physics smoke tests failed ***
    echo     The simulation models are broken. Do NOT use simulation
    echo     results until this is fixed.
    pause
    exit /b 1
)
echo [OK] Physics models verified

REM ── Check for serial ports ──────────────────────────────────
echo.
echo [4/5] Scanning for serial ports...
%PYTHON% -c "
try:
    from serial.tools import list_ports
    ports = list(list_ports.comports())
    if ports:
        print('Found ports:')
        for p in ports:
            print(f'  {p.device}  {p.description}')
    else:
        print('No serial ports found - hardware not connected or drivers needed')
except ImportError:
    print('pyserial not installed - install with: pip install pyserial')
" 2>&1
echo [OK] Port scan complete

REM ── Log test day ────────────────────────────────────────────
echo.
echo [5/5] Logging test day...
%PYTHON% -c "
import json, os
from datetime import datetime
log_path = 'test_day_log.json'
log = []
if os.path.exists(log_path):
    try:
        with open(log_path) as f: log = json.load(f)
    except: pass
log.append({'date': datetime.now().isoformat(), 'status': 'started'})
with open(log_path, 'w') as f: json.dump(log, f, indent=2)
print(f'Test day #{len(log)} logged')
" 2>&1
echo [OK] Logged

REM ── Launch dashboard ────────────────────────────────────────
echo.
echo ============================================================
echo   PRE-FLIGHT COMPLETE — Launching dashboard
echo   When you see Local URL, open it in your browser
echo   Usually: http://localhost:8501
echo   Press Ctrl+C in this window to stop
echo ============================================================
echo.

REM Pass query param to open directly to Test Session tab
%PYTHON% -m streamlit run aria_dashboard.py -- --test-day

:end
echo.
pause
