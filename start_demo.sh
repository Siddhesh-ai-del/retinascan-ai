#!/bin/bash
# RetinaScan AI — Demo launcher
# Ctrl+C (or any signal) shuts down both backend and frontend cleanly.

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"

# --- cleanup on any exit (Ctrl-C, SIGTERM, normal exit) ---------------
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    # Kill backend by process name
    pkill -f "uvicorn src.api.server" 2>/dev/null && echo -e "  Backend stopped"  || true
    # Kill frontend: kill all node processes on port 3000
    fuser -k 3000/tcp >/dev/null 2>&1 && echo -e "  Frontend stopped" || true
    # Clean up any leftover webpack/node dev server children
    pkill -9 -f "node.*webpack" 2>/dev/null || true
    wait 2>/dev/null || true
    echo -e "${GREEN}All services stopped.${NC}"
    exit 0
}
trap cleanup INT TERM HUP EXIT

# --- preflight --------------------------------------------------------
if ! command -v curl &>/dev/null; then
    echo -e "${RED}ERROR: curl is required but not installed.${NC}"
    exit 1
fi

port_up() { curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$1" ; }

echo "=============================================="
echo "  RetinaScan AI - DR Screening Demo Launcher"
echo "=============================================="

if [ ! -d venv ]; then
    echo -e "${RED}ERROR: venv not found in $PROJECT_DIR${NC}"
    echo "Set up the environment first (see README.md)"
    exit 1
fi

# Fix stale shebangs if the venv was moved from another directory
VENV_PYTHON="$PROJECT_DIR/venv/bin/python"
sed -i "1s|^#!.*|#!${VENV_PYTHON}|" "$PROJECT_DIR"/venv/bin/activate "$PROJECT_DIR"/venv/bin/activate.csh 2>/dev/null || true
for script in "$PROJECT_DIR"/venv/bin/*; do
    if head -1 "$script" 2>/dev/null | grep -q '^#!.*python'; then
        sed -i "1s|^#!.*|#!${VENV_PYTHON}|" "$script"
    fi
done

for f in models/onnx/classifier.onnx models/onnx/segmenter.onnx; do
    if [ ! -f "$f" ]; then
        echo -e "${RED}ERROR: missing $f${NC}"
        echo "Train the models and run ONNX export first (see README.md)."
        exit 1
    fi
done

# --- backend ----------------------------------------------------------
if port_up 8000; then
    echo -e "${YELLOW}Backend already running on :8000 — reusing it${NC}"
else
    echo "Starting backend on :8000 ..."
    venv/bin/python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000 \
        </dev/null > "$LOG_DIR/backend.log" 2>&1 &
fi

for i in $(seq 1 30); do
    health=$(curl -s --max-time 2 http://127.0.0.1:8000/api/health || true)
    if echo "$health" | grep -q '"models_loaded":true'; then
        echo -e "${GREEN}[OK] Backend healthy, models loaded${NC}"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}ERROR: backend did not become healthy. Check $LOG_DIR/backend.log${NC}"
        exit 1
    fi
    sleep 1
done

# --- frontend ---------------------------------------------------------
if port_up 3000; then
    echo -e "${YELLOW}Frontend already running on :3000 — reusing it${NC}"
else
    echo "Starting frontend on :3000 ..."
    bash -c "cd '$PROJECT_DIR/frontend' && npm start" \
        </dev/null > "$LOG_DIR/frontend.log" 2>&1 &
fi

for i in $(seq 1 60); do
    if port_up 3000; then
        echo -e "${GREEN}[OK] Frontend up${NC}"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo -e "${RED}ERROR: frontend did not start. Check $LOG_DIR/frontend.log${NC}"
        exit 1
    fi
    sleep 1
done

echo ""
echo -e "${GREEN}=============================================="
echo -e "   DEMO READY"
echo -e "   Open:  http://localhost:3000"
echo -e ""
echo -e "   Demo images: ./demo_images/"
echo -e "     blurry_ungradable.jpg -> IQA rejection"
echo -e "     moderate_npdr.jpg     -> full pipeline"
echo -e ""
echo -e "   Press Ctrl+C to stop all services"
echo -e "==============================================${NC}"

# --- block until interrupted ------------------------------------------
# Keep the script alive until Ctrl-C or SIGTERM fires the cleanup trap.
tail -f /dev/null &
wait
