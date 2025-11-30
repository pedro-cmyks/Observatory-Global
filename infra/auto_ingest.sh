#!/bin/bash
cd /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/infra

while true; do
    echo "$(date): Running ingestion..."
    docker-compose exec -T api python -m app.services.gdelt_ingest < /dev/null
    
    echo "$(date): Running aggregation..."
    docker-compose exec -T api python -m app.services.aggregator < /dev/null
    
    echo "$(date): Done. Sleeping 15 minutes..."
    sleep 900
done
