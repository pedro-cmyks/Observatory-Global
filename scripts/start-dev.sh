#!/bin/bash
set -e

echo "=================================================="
echo "  Observatory Global - Development Startup"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

# Check we're using the right frontend
if [ ! -d "frontend-v2" ]; then
    echo -e "${RED}ERROR: frontend-v2 directory not found!${NC}"
    exit 1
fi

echo -e "${YELLOW}Note: Using frontend-v2 (MapLibre/Deck.gl - free stack)${NC}"
echo -e "${YELLOW}      The ./frontend folder is DEPRECATED (Mapbox - paid)${NC}"
echo ""

# Check Docker for Postgres
echo "1. Checking database..."
if ! docker ps 2>/dev/null | grep -q postgres; then
    echo "   Starting Postgres container..."
    docker-compose up -d postgres 2>/dev/null || docker-compose up -d db 2>/dev/null || {
        echo -e "${YELLOW}   Could not start Postgres via docker-compose. Assuming it's already running.${NC}"
    }
    sleep 3
fi
echo -e "${GREEN}   ✓ Database check complete${NC}"

# Start backend
echo ""
echo "2. Starting backend on port 8000..."
cd "$REPO_ROOT/backend"
if [ -d "../.venv" ]; then
    source ../.venv/bin/activate 2>/dev/null || true
elif [ -d "../venv" ]; then
    source ../venv/bin/activate 2>/dev/null || true
fi

# Kill any existing backend on 8000
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null || true

uvicorn app.main_v2:app --reload --port 8000 &
BACKEND_PID=$!
sleep 3

# Verify backend started
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}   ✓ Backend running (PID: $BACKEND_PID)${NC}"
else
    echo -e "${YELLOW}   ⚠ Backend may still be starting...${NC}"
fi

# Start frontend-v2
echo ""
echo "3. Starting frontend-v2 on port 3000..."
cd "$REPO_ROOT/frontend-v2"

# Kill any existing frontend on 3000
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null || true

npm run dev &
FRONTEND_PID=$!
sleep 5

echo -e "${GREEN}   ✓ Frontend running (PID: $FRONTEND_PID)${NC}"

echo ""
echo "=================================================="
echo -e "${GREEN}  Development servers running!${NC}"
echo "=================================================="
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  Health:    http://localhost:8000/health"
echo ""
echo "  Press Ctrl+C to stop all servers"
echo ""

# Wait and cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}
trap cleanup INT TERM

wait
