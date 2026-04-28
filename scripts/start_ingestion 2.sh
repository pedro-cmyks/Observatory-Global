#!/bin/bash
# start_ingestion.sh - Single command to start Observatory ingestion
#
# Usage:
#   ./scripts/start_ingestion.sh          # Run continuously (every 15 min)
#   ./scripts/start_ingestion.sh --once   # Run once and exit
#
# The supervisor handles:
#   - Process locking (prevents duplicate runs)
#   - Exponential backoff on failures
#   - Structured logging

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$SCRIPT_DIR"

echo "=== Observatory Global Ingestion ==="
echo "Working directory: $SCRIPT_DIR"
echo "Time: $(date)"
echo ""

# Activate virtual environment if it exists
if [ -d "backend/.venv" ]; then
    echo "Activating virtual environment..."
    source backend/.venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Set PYTHONPATH to include backend
export PYTHONPATH="$SCRIPT_DIR/backend:$PYTHONPATH"

# Run the supervisor
echo "Starting ingestion supervisor..."
python -m ingestion.supervisor "$@"
