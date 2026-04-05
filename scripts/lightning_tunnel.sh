#!/bin/bash
# Lightning AI SSH tunnel manager for Gemma 4 on remote GPU.
# Automatically reconnects when the tunnel drops or session ID changes.
#
# Usage:
#   ./scripts/lightning_tunnel.sh              # connect with last known session
#   ./scripts/lightning_tunnel.sh SESSION_ID   # connect with specific session
#   ./scripts/lightning_tunnel.sh check        # just check if tunnel is alive
#   ./scripts/lightning_tunnel.sh kill         # kill existing tunnel

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SESSION_FILE="$REPO_ROOT/.lightning_session"
KEY="$HOME/.ssh/lightning_rsa"
LOCAL_PORT=11435
REMOTE_PORT=11434

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

check_tunnel() {
    curl -s --connect-timeout 3 "http://localhost:$LOCAL_PORT/api/tags" > /dev/null 2>&1
    return $?
}

kill_tunnel() {
    # Kill any existing SSH tunnels to lightning
    ps aux 2>/dev/null | grep "ssh.*$LOCAL_PORT.*lightning" | grep -v grep | awk '{print $2}' | xargs kill 2>/dev/null
    # Windows compatible
    tasklist 2>/dev/null | grep -q ssh && taskkill //F //IM ssh.exe 2>/dev/null
    echo -e "${RED}Tunnel killed${NC}"
}

get_session() {
    if [ -n "$1" ] && [ "$1" != "check" ] && [ "$1" != "kill" ]; then
        echo "$1"
        return
    fi
    if [ -f "$SESSION_FILE" ]; then
        cat "$SESSION_FILE"
        return
    fi
    echo ""
}

connect() {
    local SESSION="$1"
    if [ -z "$SESSION" ]; then
        echo -e "${RED}No session ID. Usage: $0 SESSION_ID${NC}"
        echo "Get it from Lightning AI Studio SSH command."
        exit 1
    fi

    # Save session for next time
    echo "$SESSION" > "$SESSION_FILE"

    # Kill existing tunnel
    kill_tunnel 2>/dev/null

    echo "Connecting to Lightning AI (session: $SESSION)..."
    ssh -i "$KEY" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o ConnectTimeout=15 \
        -N -f \
        -L "$LOCAL_PORT:localhost:$REMOTE_PORT" \
        "s_${SESSION}@ssh.lightning.ai" 2>/dev/null

    if check_tunnel; then
        echo -e "${GREEN}Tunnel active: localhost:$LOCAL_PORT -> Gemma 4 on T4${NC}"
        # Show available models
        MODELS=$(curl -s "http://localhost:$LOCAL_PORT/api/tags" 2>/dev/null | python -c "import sys,json; print(', '.join(m['name'] for m in json.load(sys.stdin).get('models',[])))" 2>/dev/null)
        echo -e "${GREEN}Models: $MODELS${NC}"
        return 0
    else
        echo -e "${RED}Tunnel created but Ollama not responding.${NC}"
        echo "The Studio may still be starting. Wait and try again."
        return 1
    fi
}

# Main
case "${1:-}" in
    check)
        if check_tunnel; then
            MODELS=$(curl -s "http://localhost:$LOCAL_PORT/api/tags" 2>/dev/null | python -c "import sys,json; print(', '.join(m['name'] for m in json.load(sys.stdin).get('models',[])))" 2>/dev/null)
            echo -e "${GREEN}Tunnel alive. Models: $MODELS${NC}"
            exit 0
        else
            echo -e "${RED}Tunnel dead.${NC}"
            exit 1
        fi
        ;;
    kill)
        kill_tunnel
        exit 0
        ;;
    *)
        # Check if tunnel already works
        if check_tunnel; then
            echo -e "${GREEN}Tunnel already active.${NC}"
            exit 0
        fi
        # Connect
        SESSION=$(get_session "$1")
        connect "$SESSION"
        ;;
esac
