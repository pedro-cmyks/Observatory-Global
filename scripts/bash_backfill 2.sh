#!/bin/bash
# GDELT Backfill via bash + curl + psql
# Usage: ./scripts/bash_backfill.sh 2025-12-30 2026-01-01 [limit]

set -e

FROM_DATE="${1:-2025-12-30}"
TO_DATE="${2:-2026-01-13}"  
LIMIT="${3:-0}"  # 0 = no limit

CHECKPOINT_FILE="checkpoints/bash_backfill.checkpoint"
LOG_FILE="logs/backfill_$(date +%Y%m%d_%H%M).log"
TEMP_DIR="/tmp/gdelt_backfill"
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="observatory"
DB_USER="observatory"
DB_PASS="changeme"

export PGPASSWORD="$DB_PASS"

mkdir -p checkpoints logs "$TEMP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Generate timestamps (every 15 min)
generate_timestamps() {
    local start_ts=$(date -j -f "%Y-%m-%d" "$FROM_DATE" "+%s" 2>/dev/null || date -d "$FROM_DATE" "+%s")
    local end_ts=$(date -j -f "%Y-%m-%d" "$TO_DATE" "+%s" 2>/dev/null || date -d "$TO_DATE" "+%s")
    end_ts=$((end_ts + 86399))  # End of day
    
    local current=$start_ts
    while [ $current -le $end_ts ]; do
        for m in 00 15 30 45; do
            local ts=$(date -j -f "%s" "$current" "+%Y%m%d%H" 2>/dev/null || date -d "@$current" "+%Y%m%d%H")
            echo "${ts}${m}00"
        done
        current=$((current + 3600))
    done
}

# Load checkpoint
load_checkpoint() {
    if [ -f "$CHECKPOINT_FILE" ]; then
        cat "$CHECKPOINT_FILE"
    else
        echo ""
    fi
}

# Save checkpoint
save_checkpoint() {
    echo "$1" > "$CHECKPOINT_FILE"
}

# Process one file
process_file() {
    local ts="$1"
    local url="http://data.gdeltproject.org/gdeltv2/${ts}.gkg.csv.zip"
    local zip_file="$TEMP_DIR/${ts}.zip"
    local csv_file="$TEMP_DIR/${ts}.csv"
    
    # Download
    if ! curl -sS -f -o "$zip_file" "$url" 2>/dev/null; then
        log "  $ts: not found"
        return 0
    fi
    
    # Extract
    if ! unzip -q -o "$zip_file" -d "$TEMP_DIR" 2>/dev/null; then
        log "  $ts: bad zip"
        rm -f "$zip_file"
        return 0
    fi
    
    # Find CSV
    csv_file=$(find "$TEMP_DIR" -name "*.csv" -newer "$zip_file" 2>/dev/null | head -1)
    if [ -z "$csv_file" ] || [ ! -f "$csv_file" ]; then
        csv_file="$TEMP_DIR/${ts}.gkg.csv"
    fi
    
    if [ ! -f "$csv_file" ]; then
        log "  $ts: no csv found"
        rm -f "$zip_file"
        return 0
    fi
    
    # Count lines
    local line_count=$(wc -l < "$csv_file" | tr -d ' ')
    
    # Parse and insert using awk + psql
    # GKG format: field 0=date, 3=source, 4=url, 8=themes, 10=locations, 12=persons, 15=tone
    local inserted=$(awk -F'\t' '
    BEGIN { count=0 }
    {
        # Parse date
        ts = substr($1, 1, 14)
        year = substr(ts, 1, 4)
        month = substr(ts, 5, 2)
        day = substr(ts, 7, 2)
        hour = substr(ts, 9, 2)
        min = substr(ts, 11, 2)
        sec = substr(ts, 13, 2)
        timestamp = year"-"month"-"day" "hour":"min":"sec
        
        source_name = $4
        source_url = $5
        
        # Parse locations for country code and coordinates
        split($11, locs, ";")
        country_code = ""
        lat = ""
        lon = ""
        for (i in locs) {
            split(locs[i], parts, "#")
            if (parts[3] != "" && parts[5] != "" && parts[6] != "") {
                cc = toupper(substr(parts[3], 1, 2))
                # Simple FIPS to ISO mapping for common codes
                if (cc == "US") country_code = "US"
                else if (cc == "UK") country_code = "GB"
                else if (cc == "GM") country_code = "DE"
                else if (cc == "SP") country_code = "ES"
                else if (cc == "CH") country_code = "CN"
                else if (cc == "JA") country_code = "JP"
                else if (cc == "RS") country_code = "RU"
                else country_code = cc
                lat = parts[5]
                lon = parts[6]
                break
            }
        }
        
        if (country_code == "" || lat == "" || lon == "") next
        
        # Parse tone (sentiment)
        split($16, tone, ",")
        sentiment = tone[1] + 0
        
        # Parse themes (first 5)
        split($9, theme_arr, ";")
        themes = "{"
        theme_count = 0
        for (i in theme_arr) {
            if (theme_count >= 5) break
            split(theme_arr[i], t, ",")
            if (length(t[1]) > 2) {
                if (theme_count > 0) themes = themes ","
                gsub(/"/, "\\\"", t[1])
                themes = themes "\"" toupper(t[1]) "\""
                theme_count++
            }
        }
        themes = themes "}"
        
        # Parse persons (first 5)  
        split($13, person_arr, ";")
        persons = "{"
        person_count = 0
        for (i in person_arr) {
            if (person_count >= 5) break
            split(person_arr[i], p, ",")
            if (length(p[1]) > 2) {
                if (person_count > 0) persons = persons ","
                gsub(/"/, "\\\"", p[1])
                persons = persons "\"" tolower(p[1]) "\""
                person_count++
            }
        }
        persons = persons "}"
        
        # Escape quotes in url and source
        gsub(/'\''/, "'\'''\'''\''", source_url)
        gsub(/'\''/, "'\'''\'''\''", source_name)
        
        # Print SQL
        print "INSERT INTO signals_v2 (timestamp, country_code, latitude, longitude, sentiment, source_url, source_name, themes, persons) VALUES ('\''"\
            timestamp"'\'', '\''"\
            country_code"'\'', "\
            lat", "\
            lon", "\
            sentiment", '\''"\
            source_url"'\'', '\''"\
            source_name"'\'', '\''"\
            themes"'\'', '\''"\
            persons"'\'') ON CONFLICT DO NOTHING;"
        count++
    }
    END { print "-- Processed " count " rows" }
    ' "$csv_file" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -q 2>/dev/null | grep -c "INSERT" || echo 0)
    
    log "  $ts: $line_count rows -> $inserted inserted"
    
    # Cleanup
    rm -f "$zip_file" "$csv_file" "$TEMP_DIR"/*.csv 2>/dev/null
    
    return 0
}

# Main
log "Starting GDELT backfill: $FROM_DATE to $TO_DATE"
log "Log file: $LOG_FILE"

LAST_CHECKPOINT=$(load_checkpoint)
FOUND_CHECKPOINT=false
PROCESSED=0
SKIPPED=0

for ts in $(generate_timestamps); do
    # Resume from checkpoint
    if [ -n "$LAST_CHECKPOINT" ] && [ "$FOUND_CHECKPOINT" = "false" ]; then
        if [ "$ts" = "$LAST_CHECKPOINT" ]; then
            FOUND_CHECKPOINT=true
            log "Resuming from checkpoint: $ts"
        else
            SKIPPED=$((SKIPPED + 1))
            continue
        fi
    fi
    
    # Limit check
    if [ "$LIMIT" -gt 0 ] && [ "$PROCESSED" -ge "$LIMIT" ]; then
        log "Reached limit of $LIMIT files"
        break
    fi
    
    process_file "$ts"
    save_checkpoint "$ts"
    PROCESSED=$((PROCESSED + 1))
    
    # Rate limit: 1 request per second
    sleep 1
done

log "Backfill complete. Processed: $PROCESSED, Skipped: $SKIPPED"
log "Checkpoint: $(cat $CHECKPOINT_FILE 2>/dev/null || echo 'none')"
