#!/bin/bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal

while true; do
    echo "$(date): Running v2 ingestion..."
    cd backend && python3 -m app.services.ingest_v2
    echo "$(date): Done. Sleeping 15 minutes..."
    sleep 900
done
