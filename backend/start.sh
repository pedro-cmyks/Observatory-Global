#!/bin/bash
set -e

echo "Starting ingestion loop..."
python -m app.services.ingest_loop &
INGEST_PID=$!
echo "Ingestion PID: $INGEST_PID"

echo "Starting API..."
exec uvicorn app.main_v2:app --host 0.0.0.0 --port 8000 --workers 1
