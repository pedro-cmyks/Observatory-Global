#!/bin/bash
# Data Quality Diagnostic Report for Observatory Global

set -e

REPORT_DIR="evidence/quality_reports"
mkdir -p $REPORT_DIR
REPORT_FILE="$REPORT_DIR/quality_$(date +%Y%m%d_%H%M%S).md"
DB_CONTAINER="observatory-postgres"
DB_NAME="observatory"
DB_USER="observatory"

echo "# Data Quality Report - $(date)" | tee $REPORT_FILE
echo "" | tee -a $REPORT_FILE

run_sql() {
    docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c "$1" 2>/dev/null
}

# Section 1: Volume Summary
echo "## 1. Volume Summary (7 days)" | tee -a $REPORT_FILE
echo '```' | tee -a $REPORT_FILE
run_sql "
SELECT 
    COUNT(*) as total_signals,
    COUNT(DISTINCT source_url) as unique_urls,
    COUNT(DISTINCT source_name) as unique_sources,
    ROUND(100.0 * (COUNT(*) - COUNT(DISTINCT source_url)) / NULLIF(COUNT(*), 0), 1) as url_dupe_pct
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '7 days';
" | tee -a $REPORT_FILE
echo '```' | tee -a $REPORT_FILE

# Section 2: Source Dominance
echo "" | tee -a $REPORT_FILE
echo "## 2. Top 15 Sources" | tee -a $REPORT_FILE
echo '```' | tee -a $REPORT_FILE
run_sql "
SELECT 
    source_name,
    COUNT(*) as signals,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 15;
" | tee -a $REPORT_FILE
echo '```' | tee -a $REPORT_FILE

# Section 3: Theme Quality
echo "" | tee -a $REPORT_FILE
echo "## 3. Top 20 Themes" | tee -a $REPORT_FILE
echo '```' | tee -a $REPORT_FILE
run_sql "
SELECT 
    unnest(themes) as theme,
    COUNT(*) as occurrences
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY 1
ORDER BY 2 DESC
LIMIT 20;
" | tee -a $REPORT_FILE
echo '```' | tee -a $REPORT_FILE

# Section 4: Aggregator Analysis
echo "" | tee -a $REPORT_FILE
echo "## 4. Aggregator Impact" | tee -a $REPORT_FILE
echo '```' | tee -a $REPORT_FILE
run_sql "
SELECT 
    CASE 
        WHEN source_name IN ('yahoo.com', 'msn.com', 'flipboard.com', 'biztoc.com', 'smartnews.com') THEN 'aggregator'
        ELSE 'original'
    END as source_type,
    COUNT(*) as signals,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) as pct
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY 1
ORDER BY 2 DESC;
" | tee -a $REPORT_FILE
echo '```' | tee -a $REPORT_FILE

# Section 5: Data Freshness
echo "" | tee -a $REPORT_FILE
echo "## 5. Data Freshness" | tee -a $REPORT_FILE
echo '```' | tee -a $REPORT_FILE
run_sql "
SELECT 
    MIN(timestamp) as oldest,
    MAX(timestamp) as newest,
    NOW() as current_time,
    ROUND(EXTRACT(EPOCH FROM (NOW() - MAX(timestamp)))/60, 1) as lag_minutes
FROM signals_v2
WHERE timestamp > NOW() - INTERVAL '7 days';
" | tee -a $REPORT_FILE
echo '```' | tee -a $REPORT_FILE

echo ""
echo "Report saved to: $REPORT_FILE"
