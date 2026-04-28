#!/bin/bash
# Preflight checks for Observatory Global development

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_port() {
    local port=$1
    local service=$2
    local pid_info=$(lsof -nP -iTCP:$port -sTCP:LISTEN 2>/dev/null | tail -n +2)
    
    if [ -n "$pid_info" ]; then
        echo -e "${RED}✗ Port $port ($service) is OCCUPIED${NC}"
        echo "  Process using port:"
        echo "$pid_info" | awk '{print "    PID: "$2"  Command: "$1}'
        echo ""
        echo "  To free this port, run:"
        echo "    kill \$(lsof -t -i:$port)"
        return 1
    else
        echo -e "${GREEN}✓ Port $port ($service) is available${NC}"
        return 0
    fi
}

echo "=== Observatory Global Preflight Checks ==="
echo ""

FAILED=0

check_port 8000 "Backend" || FAILED=1
check_port 3000 "Frontend" || FAILED=1

# Check Docker/Postgres
echo ""
if docker ps 2>/dev/null | grep -q postgres; then
    echo -e "${GREEN}✓ Postgres container is running${NC}"
else
    echo -e "${YELLOW}⚠ Postgres container not detected${NC}"
    echo "  Start with: docker-compose up -d postgres"
fi

# Check we're not in legacy frontend
if [ -f "package.json" ] && grep -q "mapbox" package.json 2>/dev/null; then
    echo -e "${RED}✗ WARNING: You may be in legacy frontend directory${NC}"
    FAILED=1
fi

echo ""
if [ $FAILED -eq 1 ]; then
    echo -e "${RED}Preflight checks FAILED. Resolve issues above before starting.${NC}"
    exit 1
else
    echo -e "${GREEN}All preflight checks passed.${NC}"
    exit 0
fi
