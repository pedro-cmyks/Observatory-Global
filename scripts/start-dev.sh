#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║       Observatory Global - Development Startup            ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verify correct frontend exists
if [ ! -d "frontend-v2" ]; then
    echo -e "${RED}ERROR: frontend-v2 directory not found!${NC}"
    exit 1
fi

# Create logs directory
mkdir -p logs

# Run preflight checks
echo "Running preflight checks..."
if ! "$SCRIPT_DIR/preflight.sh"; then
    echo -e "${RED}Preflight failed. Fix issues and retry.${NC}"
    exit 1
fi
echo ""

# Store PIDs for cleanup
PIDS_FILE="$REPO_ROOT/.dev-pids"
> "$PIDS_FILE"

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"
    if [ -f "$PIDS_FILE" ]; then
        while read pid; do
            kill $pid 2>/dev/null && echo "  Stopped PID $pid"
        done < "$PIDS_FILE"
        rm "$PIDS_FILE"
    fi
    exit 0
}
trap cleanup INT TERM

# 1. Start Database
echo -e "${CYAN}[1/3] Database${NC}"
if docker ps | grep -q postgres; then
    echo -e "${GREEN}  ✓ Postgres already running${NC}"
else
    echo "  Starting Postgres..."
    docker-compose up -d postgres 2>/dev/null || docker-compose up -d db 2>/dev/null || {
        echo -e "${YELLOW}  ⚠ Could not auto-start Postgres. Please start manually.${NC}"
    }
    sleep 3
fi

# 2. Start Backend
echo -e "${CYAN}[2/3] Backend (port 8000)${NC}"
cd "$REPO_ROOT"

# Activate virtualenv
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d "backend/.venv" ]; then
    source backend/.venv/bin/activate
fi

cd "$REPO_ROOT/backend"
export PYTHONPATH="$REPO_ROOT:$PYTHONPATH"

uvicorn app.main_v2:app --reload --port 8000 --host 0.0.0.0 > "$REPO_ROOT/logs/backend.log" 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID >> "$PIDS_FILE"
sleep 3

# Verify backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Backend running (PID: $BACKEND_PID)${NC}"
else
    echo -e "${YELLOW}  ⚠ Backend starting... check logs/backend.log if issues persist${NC}"
fi

# 3. Start Frontend-v2
echo -e "${CYAN}[3/3] Frontend-v2 (port 3000)${NC}"
cd "$REPO_ROOT/frontend-v2"

# Ensure dependencies installed
if [ ! -d "node_modules" ]; then
    echo "  Installing dependencies..."
    npm install
fi

npm run dev > "$REPO_ROOT/logs/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID >> "$PIDS_FILE"
sleep 4

# Verify frontend
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}  ✓ Frontend-v2 running (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${YELLOW}  ⚠ Frontend starting... check logs/frontend.log if issues persist${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Development servers running!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Frontend:${NC}  http://localhost:3000  (frontend-v2, MapLibre)"
echo -e "  ${CYAN}Backend:${NC}   http://localhost:8000"
echo -e "  ${CYAN}Health:${NC}    http://localhost:8000/health"
echo ""
echo -e "  ${YELLOW}Logs:${NC}      logs/backend.log, logs/frontend.log"
echo -e "  ${YELLOW}Stop:${NC}      Ctrl+C or ./scripts/stop-dev.sh"
echo ""
echo -e "${CYAN}Verification commands:${NC}"
echo "  curl -s http://localhost:8000/health | jq ."
echo "  curl -s http://localhost:3000 | head -20"
echo ""

# Wait for interrupt
wait
