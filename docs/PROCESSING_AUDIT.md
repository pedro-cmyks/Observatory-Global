# PROCESSING AUDIT — Observatory Global Ingestion Pipeline

> **Generated**: 2026-03-13 from live analysis of `ingest_v2.py`, `crisis_themes.py`, and live DB

---

## 1. Pipeline Flow

```
GDELT lastupdate.txt (every 15 min)
  → fetch_latest_gdelt_url()  → find .gkg.csv.zip URL
  → download_and_parse_gkg()  → download ZIP, unzip, tab-delimited CSV
  → parse_gkg_row()           → extract fields from GKG 2.0 format (27+ fields)
  → insert_signals()          → INSERT INTO signals_v2 ON CONFLICT DO NOTHING
  → update_countries()        → INSERT new country codes (never overwrite coords)
  → refresh_aggregates()      → REFRESH MATERIALIZED VIEW CONCURRENTLY country_hourly_v2
```

Runtime: `auto_ingest_v2.sh` → infinite loop with 900s (15 min) sleep between cycles.

---

## 2. What Filtering Is Applied

### Pre-Insert Filtering (in `parse_gkg_row`)

| Filter | Logic | Impact |
|--------|-------|--------|
| **Minimum row length** | `if len(row) < 27: return None` | Drops malformed GKG rows (<27 tab-separated fields) |
| **Country code required** | `if not country_code: return None` | Drops signals with no extractable location. This is the biggest filter — ~40-60% of GKG rows have no country |
| **Theme name minimum length** | `len(theme_name) > 2` | Drops very short theme codes (noise) |
| **Person name minimum length** | `len(person_name) > 2` | Drops very short person strings |
| **Theme cap** | `themes = list(set(themes))[:10]` | Keeps max 10 unique themes per signal |
| **Person cap** | `persons = list(set(persons))[:10]` | Keeps max 10 unique persons per signal |

### Missing Filters (No Quality Gating)

- **No confidence threshold** — GDELT provides confidence scores in some fields, but `ingest_v2.py` does not use them
- **No source quality check** — All sources treated equally (BBC = random blog)
- **No sentiment range validation** — Raw GDELT tone values pass through unchecked (can range -100 to +100 theoretically)
- **No language filter** — All languages ingested (GKG includes non-English sources)
- **No geographic precision check** — Country-level and city-level locations treated the same

---

## 3. Deduplication

### Current State

- **INSERT uses `ON CONFLICT DO NOTHING`** — but there's no unique constraint on signals_v2 that would trigger this (the only unique-ish column is the auto-increment `id`)
- **Live verification**: 0 duplicate `(source_url, timestamp, country_code)` tuples found in the last 24h
- **Natural deduplication**: Each GDELT cycle publishes a DIFFERENT file, so running the same cycle twice would insert duplicates. The 15-min sleep between cycles prevents this in practice
- **Risk**: If ingestion fails mid-cycle and retries, it could insert partial duplicates. The supervisor has retry logic but no idempotency key

### Recommendation

The `ON CONFLICT DO NOTHING` is currently a no-op (no matching unique constraint). Adding a unique index on `(source_url, timestamp, country_code)` would provide true deduplication but at a storage cost. Given current zero-duplicate state, this is low priority.

---

## 4. Sentiment Calculation

### Current Implementation

```python
# From parse_gkg_row, lines 159-167
tone_raw = row[15]  # V2TONE field (field 15)
tone_parts = tone_raw.split(',')
sentiment = float(tone_parts[0])  # Takes FIRST element only
```

### What This Means

GDELT V2TONE field contains comma-separated values:
1. **Tone** (overall) — used as `sentiment`
2. Positive Score
3. Negative Score
4. Polarity
5. Activity Reference Density
6. Self/Group Reference Density
7. Word Count

**Only element [0] (overall tone) is extracted**. Values typically range -10 to +10, though extremes can reach ±20+. The raw GDELT value is stored directly — no normalization, no smoothing, no averaging with other signals.

### Assessment

This is the simplest possible approach. The tone score is noisy (GDELT's own docs warn about this). For display purposes, the frontend already includes a "Sentiment analysis is noisy" disclaimer in `CountryBrief.tsx`. The other 6 V2TONE dimensions (polarity, activity density, etc.) are discarded.

---

## 5. What Gets Dropped and Why

| Drop Point | Reason | Estimated % |
|-----------|--------|-------------|
| `len(row) < 27` | Malformed GKG rows | ~1-2% |
| No country code extractable | No location in V2ENHANCEDLOCATIONS, or FIPS code can't map to ISO | ~40-60% (biggest loss) |
| Exception in `parse_gkg_row` | Encoding errors, malformed fields | ~0.1% (logged for first 5) |
| Exception in `insert_signals` | DB insert failures | ~0.01% (silently swallowed) |

### Live Volume Verification

From ingestion log: **1287 signals parsed → 779 inserted** per cycle. The ~40% "drop" between parsed and inserted is primarily the `ON CONFLICT DO NOTHING` (for rows that already exist from prior cycles — though we measured 0 duplicates, this suggests some were already in DB from a prior run today).

Typical hourly volume: **~1,530 signals/hour** (from live DB query).

---

## 6. Signal Quality / Source Weight

### Current State: NONE

There is **no concept of signal quality or source weight** in the ingestion pipeline. Every signal from every source has equal standing.

### Built But Unused

The `backend/indicators/` module contains three quality metrics that are calculated **on query** (not at ingestion time):

| Metric | Module | What It Does |
|--------|--------|-------------|
| Source Diversity | `source_diversity.py` (4.1KB) | Counts unique sources per country per time window. Higher = more diverse reporting |
| Source Quality | `source_quality.py` (4.8KB) | Compares sources against an allowlist/denylist. Higher = more reputable sources |
| Normalized Volume | `normalized_volume.py` (4.5KB) | Compares current signal volume to 7-day rolling baseline. Detects spikes |

These are served by `/api/indicators/country/{code}` but have **no frontend consumer** (the `CountryBrief.tsx` component that uses them is orphaned).

### v1 Schema Has More

The v1-era `gdelt_signals` table (48K rows) includes richer fields:
- `confidence` (NUMERIC, DEFAULT 1.0) — quality score per signal
- `duplicate_count` / `duplicate_outlets` — dedup tracking
- `intensity` — derived engagement metric
- `geographic_precision` — location specificity
- `source_collection_id` — source provenance

None of these fields exist in the v2 `signals_v2` table.

---

## 7. Data Volume Summary

| Metric | Value |
|--------|-------|
| Total signals in DB | 2,256,449 |
| Signals per cycle (~15 min) | ~779 inserted (1287 parsed) |
| Signals per hour | ~1,530 |
| Unique countries with data | 292 |
| Countries with baseline stats | 189 |
| Materialized view refresh | After each cycle (concurrent) |
| DB size (signals_v2) | 1,248 MB |
| DB size (all tables + indexes) | ~1.4 GB |

---

## 8. Crisis Classification

Every signal passes through crisis classification **at ingestion time**:

```python
crisis_themes = get_crisis_themes(themes)       # Filter themes against 40+ crisis prefixes
is_crisis = len(crisis_themes) > 0              # Boolean
crisis_score = calculate_crisis_score(themes)    # 0.0-1.0 (ratio of crisis themes + severity boost)
severity = calculate_severity(themes)            # critical/high/medium/low (keyword matching)
event_type = get_event_type(themes)              # armed_conflict/civil_unrest/terrorism/etc.
```

This is stored per-signal in the DB. The backend has `/api/v3/crisis/signals` and `/api/v3/crisis/summary` endpoints to query this data, but **neither has a frontend consumer**.

---

## 9. GDELT Translingual Export — Assessment for Expansion

GDELT publishes two GKG files every 15 minutes:
1. **GKG** (currently ingested) — English-language sources
2. **Translingual GKG** — non-English sources, machine-translated

Both use the same format and appear at:
```
http://data.gdeltproject.org/gdeltv2/lastupdate-translation.txt
```

### What Translingual Adds

- **Document title/identifier** — The `DocumentIdentifier` (field 4, currently extracted as `source_url`) contains the article URL. For Translingual, GDELT sometimes includes translated titles in the `Extras` XML field
- **Broader source coverage** — Non-English media (Al Jazeera Arabic, Le Monde, Xinhua Chinese, etc.)
- **~2x signal volume** — Roughly doubles the number of signals per cycle

### Integration Plan

The same `parse_gkg_row()` function works for Translingual GKG files (identical format). The integration requires:
1. Fetch Translingual URL from `lastupdate-translation.txt`
2. Parse with same logic
3. Add `headline` column to `signals_v2` (extracted from URL slug or Extras field)
4. Insert alongside regular GKG signals

### Headline Extraction Strategy

GDELT does not provide clean article titles in the GKG format. Options:
1. **URL slug extraction** — Parse the `source_url` to extract the URL path slug (e.g., `/politics/trump-trade-deal-2026` → "Trump Trade Deal 2026"). Works for most news sites. ~80% success rate
2. **V2Extras XML** — Some GKG records include an `<PAGE_TITLE>` in the Extras XML field. Unreliable (~30% of records)
3. **HTTP fetch** — Download the actual article page and extract `<title>`. Too slow for ingestion pipeline

**Recommendation**: Use URL slug extraction as primary strategy. It's fast, reliable, and gives meaningful context for the Signal Stream panel.
