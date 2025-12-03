#!/bin/bash
SCRIPT_DIR=/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal

while true; do
    echo "$(date): Running v2 ingestion..."
    cd "$SCRIPT_DIR/backend" && python3 -m app.services.ingest_v2
    cd "$SCRIPT_DIR"
    echo "$(date): Done. Sleeping 15 minutes..."
    sleep 900
done
