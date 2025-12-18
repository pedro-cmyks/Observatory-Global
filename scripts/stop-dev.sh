#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
PIDS_FILE="$REPO_ROOT/.dev-pids"

echo "Stopping Observatory Global development services..."

# Kill from PID file
if [ -f "$PIDS_FILE" ]; then
    while read pid; do
        if kill -0 $pid 2>/dev/null; then
            kill $pid && echo "  Stopped PID $pid"
        fi
    done < "$PIDS_FILE"
    rm "$PIDS_FILE"
fi

# Also kill by port as backup
for port in 3000 8000; do
    pid=$(lsof -t -i:$port 2>/dev/null)
    if [ -n "$pid" ]; then
        kill $pid 2>/dev/null && echo "  Stopped process on port $port (PID $pid)"
    fi
done

echo "Done."
