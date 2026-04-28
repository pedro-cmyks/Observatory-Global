#!/bin/bash
set -e

OUTPUT="docs/DATA_SNAPSHOT.md"
DB_CONTAINER=$(docker ps -qf "name=postgres" | head -1)
DB_NAME="observatory"
DB_USER="postgres"

if [ -z "$DB_CONTAINER" ]; then
    echo "ERROR: Postgres container not running"
    exit 1
fi

run_sql() {
    docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -t -c "$1" 2>/dev/null
}

cat > $OUTPUT << 'HEADER'
# Observatory Global - Data Snapshot

Generated: $(date)

## Database Evidence

HEADER

echo "### Tables in Database" >> $OUTPUT
echo '```' >> $OUTPUT
run_sql "\dt" >> $OUTPUT
echo '```' >> $OUTPUT

echo -e "\n### Signals Table Schema" >> $OUTPUT
echo '```' >> $OUTPUT
run_sql "\d signals" >> $OUTPUT 2>/dev/null || run_sql "\d signals_v2" >> $OUTPUT 2>/dev/null || echo "(signals table not found)" >> $OUTPUT
echo '```' >> $OUTPUT

echo -e "\n### Row Counts" >> $OUTPUT
echo '```' >> $OUTPUT
run_sql "SELECT 'signals' as table_name, COUNT(*) as row_count FROM signals;" >> $OUTPUT
echo '```' >> $OUTPUT

echo -e "\n### Timestamp Ranges" >> $OUTPUT
echo '```' >> $OUTPUT
run_sql "SELECT MIN(ingested_at) as earliest, MAX(ingested_at) as latest, COUNT(*) as total FROM signals;" >> $OUTPUT
echo '```' >> $OUTPUT

echo -e "\n### Top 20 Countries (Last 24h)" >> $OUTPUT
echo '```' >> $OUTPUT
run_sql "SELECT unnest(country_codes) as country, COUNT(*) as cnt FROM signals WHERE ingested_at > NOW() - INTERVAL '24 hours' GROUP BY 1 ORDER BY 2 DESC LIMIT 20;" >> $OUTPUT 2>/dev/null || echo "(country_codes column may not exist)" >> $OUTPUT
echo '```' >> $OUTPUT

echo -e "\n### Sample Rows (10 most recent)" >> $OUTPUT
echo '```' >> $OUTPUT
run_sql "SELECT id, source_domain, LEFT(title, 50) as title_preview, ingested_at FROM signals ORDER BY ingested_at DESC LIMIT 10;" >> $OUTPUT 2>/dev/null || echo "(adjust columns based on actual schema)" >> $OUTPUT
echo '```' >> $OUTPUT

echo ""
echo "Created $OUTPUT"
