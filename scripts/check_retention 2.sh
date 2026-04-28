#!/bin/bash
# Check retention status WITHOUT deleting anything
# Shows what WOULD be deleted if retention policy were active

DB_CONTAINER=$(docker ps -qf "name=postgres" | head -1)

echo "=== Data Lifecycle Config ==="
docker exec -i $DB_CONTAINER psql -U observatory -d observatory -c \
    "SELECT key, value, description FROM data_lifecycle_config;"

echo ""
echo "=== Data Age Distribution ==="
docker exec -i $DB_CONTAINER psql -U observatory -d observatory << 'SQL'
SELECT 
    CASE 
        WHEN timestamp > NOW() - INTERVAL '7 days' THEN '0-7 days'
        WHEN timestamp > NOW() - INTERVAL '30 days' THEN '7-30 days'
        WHEN timestamp > NOW() - INTERVAL '90 days' THEN '30-90 days'
        ELSE '> 90 days'
    END AS age_bucket,
    COUNT(*) AS signal_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM signals_v2
GROUP BY 1
ORDER BY 1;
SQL

echo ""
echo "=== Aggregate Stats ==="
docker exec -i $DB_CONTAINER psql -U observatory -d observatory << 'SQL'
SELECT 
    'signals_country_hourly' AS table_name, COUNT(*) AS rows FROM signals_country_hourly
UNION ALL
SELECT 'signals_theme_hourly', COUNT(*) FROM signals_theme_hourly
UNION ALL
SELECT 'signals_source_hourly', COUNT(*) FROM signals_source_hourly;
SQL

echo ""
echo "To refresh aggregates: docker exec -i \$DB_CONTAINER psql -U observatory -d observatory -c \"SELECT refresh_aggregates(48);\""
echo "To enable retention: UPDATE data_lifecycle_config SET value = 'true' WHERE key = 'retention_policy_active';"
