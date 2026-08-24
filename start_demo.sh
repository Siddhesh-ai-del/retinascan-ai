#!/bin/bash
set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

port_up() { curl -s -o /dev/null --max-time 2 "http://127.0.0.1:$1" ; }

echo "=============================================="
echo "  RetinaScan AI - DR Screening Demo Launcher"
echo "=============================================="

if [ ! -d venv ]; then
    echo -e "${RED}ERROR: venv not found in $PROJECT_DIR${NC}"
    echo "Set up the environment first (see README.md)"
    exit 1
fi

for f in models/onnx/classifier.onnx models/onnx/segmenter.onnx; do
    if [ ! -f "$f" ]; then
        echo -e "${RED}ERROR: missing $f${NC}"
        echo "Train the models and run ONNX export first (see README.md)."
        exit 1
    fi
done

if port_up 8000; then
    echo -e "${YELLOW}Backend already running on :8000 — reusing it${NC}"
else
    echo "Starting backend on :8000 ..."
    setsid nohup venv/bin/uvicorn src.api.server:app --host 0.0.0.0 --port 8000 \
        </dev/null > /tmp/opencode/backend.log 2>&1 &
    disown
fi

for i in $(seq 1 30); do
    health=$(curl -s --max-time 2 http://127.0.0.1:8000/api/health || true)
    if echo "$health" | grep -q '"models_loaded":true'; then
        echo -e "${GREEN}[OK] Backend healthy, models loaded${NC}"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo -e "${RED}ERROR: backend did not become healthy. Check /tmp/opencode/backend.log${NC}"
        exit 1
    fi
    sleep 1
done

if port_up 3000; then
    echo -e "${YELLOW}Frontend already running on :3000 — reusing it${NC}"
else
    echo "Starting frontend on :3000 ..."
    setsid nohup bash -c "cd '$PROJECT_DIR/frontend' && npm start" \
        </dev/null > /tmp/opencode/frontend.log 2>&1 &
    disown
fi

for i in $(seq 1 60); do
    if port_up 3000; then
        echo -e "${GREEN}[OK] Frontend up${NC}"
        break
    fi
    if [ "$i" -eq 60 ]; then
        echo -e "${RED}ERROR: frontend did not start. Check /tmp/opencode/frontend.log${NC}"
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
echo -e "==============================================${NC}"
