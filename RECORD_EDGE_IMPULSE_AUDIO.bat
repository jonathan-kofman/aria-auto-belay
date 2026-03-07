@echo off
REM Record labeled audio for Edge Impulse wake-word training.
REM Double-click to run, or: cd to this folder and run RECORD_EDGE_IMPULSE_AUDIO.bat
cd /d "%~dp0"
title ARIA — Edge Impulse Audio Recorder

echo.
echo ========================================
echo   ARIA Edge Impulse Audio Dataset
echo ========================================
echo.

if exist ".python\python.exe" (
    set PY=\.python\python.exe
) else (
    set PY=python
    echo Using system Python. For same env as dashboard, run setup_local_python first.
    echo.
)

echo Checking dependencies (sounddevice, soundfile, numpy)...
%PY% -c "import sounddevice, soundfile, numpy" 2>nul
if errorlevel 1 (
    echo Installing: sounddevice soundfile numpy
    %PY% -m pip install sounddevice soundfile numpy --quiet --disable-pip-version-check
    if errorlevel 1 (
        echo.
        echo Pip install failed. Try: pip install sounddevice soundfile numpy
        goto :end
    )
    echo.
)

echo Recording will be saved to: %CD%\dataset\
echo   - take, slack, lower, up, watch_me, rest, noise, unknown
echo.
echo Target: 60 clips per class. Press ENTER to record each clip.
echo See docs\edge_impulse_setup.md for full steps.
echo ========================================
echo.

%PY% tools\aria_collect_audio.py

:end
echo.
pause
