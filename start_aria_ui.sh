#!/usr/bin/env bash
set -e

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

echo "============================================================"
echo " ARIA-OS UI Launcher"
echo "============================================================"

# --- Python server ---
echo "[1/2] Starting FastAPI server on http://localhost:8000 ..."
python -m uvicorn aria_server:app --host 0.0.0.0 --port 8000 --reload &
SERVER_PID=$!

# --- Node UI ---
echo "[2/2] Starting Vite dev server on http://localhost:5173 ..."
cd aria-ui

if [ ! -d node_modules ]; then
    echo "Installing Node dependencies..."
    npm install --legacy-peer-deps
fi

npm run dev &
UI_PID=$!

echo ""
echo "UI:  http://localhost:5173"
echo "API: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $SERVER_PID $UI_PID 2>/dev/null; exit 0" INT TERM
wait
