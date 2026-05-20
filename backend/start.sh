#!/bin/bash
set -e

# Ingest loop watchdog — restarts the loop if it exits for any reason.
# Runs in a subshell so the restart logic doesn't affect the main API process.
ingest_watchdog() {
    echo "[watchdog] Waiting 30s before first ingestion cycle..."
    sleep 30
    while true; do
        echo "[watchdog] Starting ingestion loop ($(date -u +%Y-%m-%dT%H:%M:%SZ))"
        python -m app.services.ingest_loop || true
        echo "[watchdog] Ingestion loop exited — restarting in 60s..."
        sleep 60
    done
}

echo "Starting ingestion watchdog..."
ingest_watchdog &
WATCHDOG_PID=$!
echo "Watchdog PID: $WATCHDOG_PID"

echo "Starting API..."
exec uvicorn app.main_v2:app --host 0.0.0.0 --port 8000 --workers 1
