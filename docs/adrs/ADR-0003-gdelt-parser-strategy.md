# ADR-0003: GDELT GKG Parser Implementation Strategy

## Status
**Accepted**

## Date
2025-01-18

## Context

Observatory Global requires real-time news narrative intelligence from GDELT's Global Knowledge Graph (GKG) data. The current implementation uses placeholder data. We need to implement a production-ready parser that can:

1. Download and parse GDELT GKG v2.1 files (15-minute intervals)
2. Handle large files efficiently (50-150 MB uncompressed per file)
3. Extract critical fields: V2Themes, V2Locations, V2Tone, V2Counts
4. Gracefully handle edge cases and malformed data
5. Support multiple concurrent country queries

### Data Analysis Findings

Analysis of sample GKG file `20251119031500.gkg.csv` revealed:

**File Characteristics:**
- Format: Tab-delimited CSV (27 columns), no header row
- Encoding: ASCII/UTF-8
- Compressed size: ~5 MB per 15-minute window
- Uncompressed size: ~15-50 MB per 15-minute window
- Rows per file: 1,000-30,000 articles
- Maximum line length: ~12,000 characters

**Field Population Rates (from sample):**
- V2Themes (Col 8): 88% populated
- V2Locations (Col 10): 81% populated
- V2Tone (Col 16): 100% populated (7 comma-separated values)
- V2Counts (Col 6): ~15% populated (sparse)

**Edge Cases Identified:**
- Empty theme/location fields common in short articles
- V2Counts often empty (use V2EnhancedThemes for topic counts instead)
- Some rows contain very long lines (12,000+ chars) due to GCAM data
- International characters in location names and persons

## Decision

### 1. Parser Approach: Streaming with Batched Processing

**Choice**: Streaming line-by-line parser with batched database writes

**Rationale**:
- Files can exceed 100 MB; loading entire file into memory is risky
- Streaming allows processing while downloading (future optimization)
- Batch writes (1000 rows) balance performance vs. memory
- Generator pattern enables lazy evaluation

```python
def parse_gkg_streaming(filepath: str) -> Iterator[GKGRecord]:
    with open(filepath, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            try:
                yield parse_gkg_row(line, line_num)
            except ParseError as e:
                logger.warning(f"Malformed row {line_num}: {e}")
                continue  # Skip bad rows, don't fail
```

### 2. Memory Management Strategy

**Choice**: Process in chunks of 1,000 records with explicit garbage collection

**Implementation**:
```python
CHUNK_SIZE = 1000

def process_gkg_file(filepath: str, country_filter: Optional[str] = None):
    chunk = []
    for record in parse_gkg_streaming(filepath):
        if country_filter and not record_matches_country(record, country_filter):
            continue
        chunk.append(record)
        if len(chunk) >= CHUNK_SIZE:
            yield chunk
            chunk = []
            gc.collect()  # Explicit cleanup
    if chunk:
        yield chunk
```

**Memory Budget**:
- Maximum 1,000 records in memory at once
- Each record ~5 KB average = ~5 MB per chunk
- Peak memory: ~50 MB (including parsing overhead)

### 3. Error Handling for Malformed Rows

**Choice**: Skip-and-log strategy with structured warnings

**Error Categories**:
| Error Type | Action | Log Level |
|------------|--------|-----------|
| Wrong column count (!=27) | Skip row | WARNING |
| Unparseable V2DATE | Skip row | WARNING |
| Empty critical field (themes) | Include with flag | DEBUG |
| Invalid numeric (tone) | Use default 0.0 | DEBUG |
| Invalid location format | Skip location only | DEBUG |

**Structured Logging**:
```python
{
    "timestamp": "2025-01-18T10:30:00Z",
    "level": "WARNING",
    "source": "gdelt_parser",
    "file": "20251118153000.gkg.csv",
    "line_number": 4523,
    "error_type": "COLUMN_COUNT_MISMATCH",
    "expected": 27,
    "actual": 25,
    "action": "skipped"
}
```

**Failure Threshold**: If >10% of rows fail parsing, emit ERROR alert and use cached data.

### 4. Retry and Backoff Strategy

**Choice**: Exponential backoff with circuit breaker

**Download Retry Configuration**:
```python
RETRY_CONFIG = {
    "max_attempts": 3,
    "initial_delay_seconds": 5,
    "max_delay_seconds": 60,
    "exponential_base": 2,
    "jitter_factor": 0.1
}
```

**Retry Flow**:
1. Attempt download
2. On failure: wait 5s, retry
3. On failure: wait 10s, retry
4. On failure: wait 20s (capped at 60s), retry
5. After 3 failures: mark source unhealthy, use cached data

**Circuit Breaker**:
- Opens after 5 consecutive failures
- Half-open test after 5 minutes
- Closes after 2 successful requests

```python
class GDELTCircuitBreaker:
    failure_threshold = 5
    recovery_timeout = 300  # 5 minutes
    success_threshold = 2
```

### 5. Caching Strategy

**Choice**: Two-tier caching (file + parsed)

**Tier 1 - File Cache**:
- Location: `/tmp/gdelt_cache/` or configurable path
- Retention: Last 3 files (45 minutes of data)
- Format: Original compressed zip files
- Purpose: Quick reprocessing without re-download

**Tier 2 - Parsed Cache (Redis)**:
- Key pattern: `gdelt:signals:{country}:{timestamp}`
- TTL: 24 hours (sliding window)
- Format: JSON-serialized GDELTSignal objects
- Purpose: Fast API responses

**Cache Invalidation**:
- New file available (check lastupdate.txt)
- Country filter changes
- Manual cache clear endpoint

### 6. File Cleanup Policy

**Choice**: Automatic cleanup with retention limits

**Configuration**:
```python
FILE_CLEANUP = {
    "max_files": 10,           # Keep last 10 files (~2.5 hours)
    "max_age_hours": 6,        # Delete files older than 6 hours
    "min_free_space_gb": 1,    # Emergency cleanup if disk low
    "cleanup_interval_minutes": 15
}
```

**Cleanup Process**:
1. Run after each successful download
2. Delete files exceeding max_files or max_age
3. On disk space emergency, delete oldest files until threshold met
4. Log all deletions for audit

### 7. Column Mapping (GKG v2.1)

Based on actual data analysis, the correct column mapping is:

| Index | Field Name | Type | Format |
|-------|------------|------|--------|
| 0 | GKGRECORDID | String | `YYYYMMDDHHMMSS-N` |
| 1 | V2DATE | Timestamp | `YYYYMMDDHHMMSS` |
| 2 | V2SourceCollectionIdentifier | Integer | 1=web, 2=broadcast |
| 3 | V2SourceCommonName | String | Domain name |
| 4 | V2DocumentIdentifier | String | Full URL |
| 5 | V2Counts | Complex | Theme counts with geo |
| 6 | V2EnhancedCounts | Complex | Extended counts |
| 7 | V2Themes | List | Semicolon-separated |
| 8 | V2EnhancedThemes | Complex | Theme,CharOffset pairs |
| 9 | V2Locations | Complex | Simplified locations |
| 10 | V2EnhancedLocations | Complex | Full location data |
| 11 | V2Persons | List | Semicolon-separated |
| 12 | V2EnhancedPersons | Complex | Person,CharOffset pairs |
| 13 | V2Organizations | List | Semicolon-separated |
| 14 | V2EnhancedOrganizations | Complex | Org,CharOffset pairs |
| 15 | V2Tone | CSV | 7 comma-separated values |
| 16 | V2EnhancedDates | Complex | Date mentions |
| 17 | V2GCAM | Complex | 2300+ metrics |
| 18 | V2SharingImage | URL | Article thumbnail |
| 19-26 | Additional fields | Various | See GDELT docs |

## Alternatives Considered

### Alternative 1: Full In-Memory Loading
**Rejected**: Risk of OOM for large files (100+ MB)

### Alternative 2: Database-First Streaming
Write each row directly to database as parsed.
**Rejected**: Too many small writes, poor performance

### Alternative 3: Apache Spark Processing
Use distributed processing for GKG files.
**Rejected**: Overkill for single-file processing, adds infrastructure complexity

### Alternative 4: GDELT DOC API
Use GDELT's document-level API instead of raw files.
**Rejected**: Limited filtering, higher latency, less control

## Consequences

### Positive
- Memory-efficient processing of large files
- Graceful degradation on errors
- Fast recovery with cached data
- Auditable processing with structured logs
- Testable with deterministic snapshot data

### Negative
- Complexity of streaming parser vs. simple CSV read
- Requires Redis for parsed cache tier
- Circuit breaker may cause stale data during outages
- 15-minute latency inherent to GDELT publishing cadence

### Risks
- GDELT schema changes (rare but possible)
- Network issues during download window
- Disk space exhaustion if cleanup fails

### Mitigations
- Schema version check in parser
- Health check endpoint for GDELT connectivity
- Disk space monitoring with alerts

## Implementation Notes

### File Structure
```
backend/app/services/
  gdelt_parser.py      # Core parsing logic
  gdelt_downloader.py  # File fetch and cache
  gdelt_client.py      # High-level API (existing)
```

### Configuration (settings.py)
```python
# GDELT Configuration
GDELT_BASE = "http://data.gdeltproject.org/gdeltv2/"
GDELT_CACHE_DIR = "/tmp/gdelt_cache"
GDELT_CACHE_TTL_HOURS = 24
GDELT_RETRY_MAX_ATTEMPTS = 3
GDELT_CIRCUIT_BREAKER_THRESHOLD = 5
GDELT_CHUNK_SIZE = 1000
```

### Performance Targets
- Parse 30,000 rows in < 60 seconds
- API response time < 2 seconds (cache hit)
- API response time < 10 seconds (cache miss)
- Memory usage < 100 MB during processing

## References

- [GDELT 2.0 GKG Codebook](https://blog.gdeltproject.org/gdelt-2-0-our-global-world-in-realtime/)
- [docs/GDELT_SCHEMA_ANALYSIS.md](../GDELT_SCHEMA_ANALYSIS.md)
- Sample data: `data/gdelt_samples/20251119031500.gkg.csv`
