# PROJECT AUDIT — Observatory Global

> **Generated**: 2026-03-13  
> **Branch**: `v3-intel-layer`  
> **Scope**: Full-stack audit of every active route, endpoint, component, and data path

---

## 1. Frontend Views / Pages

Observatory Global is a **single-page application** (SPA) — no router, no pages. Everything renders inside `App.tsx` through conditional panels.

### 1.1 Active Layout Regions

| Region | Component(s) | Description |
|--------|-------------|-------------|
| **Header bar** | `App.tsx` inline + `SearchBar` + `FocusIndicator` + `CrisisToggle` + `SettingsPanel` | Branding, search, crisis toggle, settings gear, live stats counter |
| **Time controls bar** | `App.tsx` inline | 8 time-range buttons (1h→All Time) + GLOW/FLOW/NODES layer toggles |
| **Main viewport** | `DeckGL` + `Map` (MapLibre) | Full-screen dark-matter basemap with Deck.gl layers |
| **Country sidebar** | `App.tsx` inline `<aside>` | Right panel when a country node is clicked. Shows name, narrative summary, signal count, sentiment, top 5 themes (clickable), source diversity bar, source tags |
| **Theme detail modal** | `ThemeDetail` | Overlay modal for a specific GDELT theme. Timeline chart, country breakdown, related themes, top sources, top persons, raw signal list |
| **Briefing modal** | `Briefing` | Full-screen overlay showing a "morning briefing" with stats, most active countries, sentiment extremes, top themes, top sources |
| **Focus summary panel** | `FocusSummaryPanel` | Right-side panel that appears when focus mode is active. Shows related topics, top sources, recent coverage links |
| **Crisis dashboard** | `CrisisDashboard` | Right-side fixed panel (hidden unless Crisis Mode toggled on). Shows countries with anomalous activity spikes, severity levels, z-scores |
| **Map tooltip** | `MapTooltip` | Hover tooltip on nodes (country name, signal count, sentiment, source count) and flow arcs (countries, strength, shared themes) |
| **Legend** | `Legend` | Bottom-left collapsible panel explaining node sizes, sentiment colors, flow widths |
| **Crisis overlay** | `CrisisOverlay` | Full-screen red tint when Crisis Mode is active |

### 1.2 Deck.gl Map Layers (rendered order)

1. **TerminatorLayer** — Day/night boundary (optional, hidden in Crisis Mode)
2. **ArcLayer** `flows` — Great-circle arcs between countries (theme co-occurrence). Width = log(strength). Colors are theme-aware
3. **ScatterplotLayer** `nodes-glow-outer` — Outer glow halo (alpha=30)
4. **ScatterplotLayer** `nodes-glow-middle` — Middle glow (alpha=60)
5. **ScatterplotLayer** `nodes-glow-inner` — Inner glow (alpha=100)
6. **ScatterplotLayer** `nodes-core` — Solid, pickable country nodes. Color = sentiment. Size = log(signalCount). Clickable

### 1.3 React Context Providers (wrapping order)

```
FocusProvider → FocusDataProvider → CrisisProvider → AppContent
```

| Context | Purpose |
|---------|---------|
| `FocusContext` | Tracks active focus (type/value/label). `setFocus()` / `clearFocus()` |
| `FocusDataContext` | **Single source of truth** for nodes, flows, summary. Fetches `/api/v2/nodes` + `/api/v2/flows` + `/api/v2/focus` in parallel. Manages `timeRange` state |
| `CrisisContext` | Toggles Crisis Mode (persisted to localStorage). Fetches `/api/v2/anomalies` every 5 min when enabled |
| `ThemeContext` | Provides `themeId` for UI theming (color palette) |

### 1.4 Orphaned / Unused Components

| Component | Status |
|-----------|--------|
| `CountryBrief.tsx` + `CountryBrief.css` | **NOT IMPORTED ANYWHERE**. 326-line executive brief with trust indicators, sentiment, themes, top stories. Has its own CSS. Never rendered. |
| `DevBanner.tsx` | Commented out in `App.tsx` (line 555). Not rendered. |
| `IndicatorTooltip.tsx` + `IndicatorTooltip.css` | Only imported by `CountryBrief.tsx` which is itself unused. Dead code. |

---

## 2. Backend API Endpoints

All endpoints are defined in [main_v2.py](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend/app/main_v2.py) (1655 lines, single file).

### 2.1 Complete Endpoint Catalog

| Endpoint | Method | Purpose | Data Source | Frontend Consumer |
|----------|--------|---------|-------------|-------------------|
| `/` | GET | API root, lists available endpoints | — | Dev only |
| `/health` | GET | Health check with DB connectivity + ingestion lag | `signals_v2` | Vite proxy |
| `/api/v2/stats` | GET | System-wide DB stats (total signals, time ranges, ingestion health) | `signals_v2` | **None** (no frontend consumer) |
| `/api/v2/nodes` | GET | Country nodes with signal counts, sentiment, intensity | `country_hourly_v2` / `country_daily_v2` / `signals_v2` (focus mode) | `FocusDataContext` |
| `/api/v2/flows` | GET | Theme co-occurrence flows (Jaccard similarity between country theme vectors) | `signals_v2` + `countries_v2` | `FocusDataContext` |
| `/api/v2/anomalies` | GET | Countries with activity spikes (z-score, multiplier vs 7-day baseline) | `signals_v2` + `country_baseline_stats` | `CrisisContext` |
| `/api/v2/search` | GET | Cross-entity search (themes, countries, sources, persons) | `signals_v2` + `countries_v2` | `SearchBar` |
| `/api/v2/focus` | GET | Filtered data for focus mode (nodes, related topics, top sources, headlines) | `signals_v2` | `FocusDataContext` (when focus active) |
| `/api/v2/theme/{code}` | GET | Theme detail (signals, timeline, country breakdown, related themes, top sources, persons) | `signals_v2` | `ThemeDetail` |
| `/api/v2/signals` | GET | Raw signals with filters | `signals_v2` | `CountryBrief` (which is unused) |
| `/api/v2/country/{code}` | GET | Country detail (themes, sources, persons, sentiment) | `country_hourly_v2` + `signals_v2` | `App.tsx` (sidebar) |
| `/api/v2/briefing` | GET | Morning briefing summary (top countries, sentiment extremes, themes, sources) | `signals_v2` + `countries_v2` | `Briefing` |
| `/api/v2/trends` | GET | Time-series trends (by entity type: global/country/theme/source) | `signals_country_hourly` / `signals_theme_hourly` / `signals_source_hourly` | **None** |
| `/api/v2/compare` | GET | Period comparison (current vs previous window) | `signals_country_hourly` / `signals_theme_hourly` | **None** |
| `/api/v2/heatmap` | GET | **DEPRECATED**. Returns empty. | — | — |
| `/api/v3/crisis/signals` | GET | Crisis-classified signals with filters | `signals_v2` (crisis columns) | **None** |
| `/api/v3/crisis/summary` | GET | Summary stats for crisis signals | `signals_v2` (crisis columns) | **None** |
| `/api/indicators/country/{code}` | GET | Trust indicators (diversity, quality, volume) for a country | `signals_v2` | `CountryBrief` (unused) |
| `/api/indicators/tooltips` | GET | Tooltip text for trust indicator metrics | Indicators module | `CountryBrief` (unused) |
| `/api/indicators/allowlist` | GET | Source quality allowlist (transparency) | Indicators module | **None** |
| `/api/indicators/denylist` | GET | Source quality denylist (transparency) | Indicators module | **None** |

### 2.2 Endpoints with NO Frontend Consumer (Built but Not Shown)

| Endpoint | Data Available | Value |
|----------|---------------|-------|
| `/api/v2/stats` | Total signals, time range, ingestion health, unique countries/sources | System health dashboard |
| `/api/v2/trends` | Time-series by entity (hourly/daily buckets) | Trend charts, sparklines |
| `/api/v2/compare` | Period-over-period delta (signal count + sentiment change %) | Change indicators |
| `/api/v3/crisis/signals` | Crisis-classified signals with severity/event_type | Crisis signal feed |
| `/api/v3/crisis/summary` | By-severity, by-event-type, top-crisis-countries | Crisis overview |
| `/api/indicators/*` | Source diversity/quality scores, normalized volume | Trust metric UI |

---

## 3. Data Pipeline

### 3.1 Ingestion Flow

```
GDELT Project (every 15 min)
  → http://data.gdeltproject.org/gdeltv2/lastupdate.txt
  → Download latest .gkg.csv.zip
  → Parse GKG 2.0 rows (tab-delimited, 27+ fields)
  → Extract: timestamp, country (FIPS→ISO), lat/lon, sentiment, themes, persons, source
  → Crisis classification: is_crisis, crisis_score, severity, event_type
  → INSERT INTO signals_v2 (ON CONFLICT DO NOTHING)
  → UPDATE countries_v2 (new countries only, never overwrite coords)
  → REFRESH MATERIALIZED VIEW CONCURRENTLY country_hourly_v2
```

### 3.2 Ingestion Runtime

| Component | File | Behavior |
|-----------|------|----------|
| Core ingestion | [ingest_v2.py](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend/app/services/ingest_v2.py) | Async function. Downloads, parses, inserts one GKG file per run |
| Shell daemon | [auto_ingest_v2.sh](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/infra/auto_ingest_v2.sh) | Infinite loop: run ingestion → sleep 900s (15 min) |
| Supervisor | [supervisor.py](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/backend/ingestion/supervisor.py) | Process locking (flock), exponential backoff (5 retries), continuous mode |
| Backfill | [simple_backfill.py](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/scripts/simple_backfill.py), [bash_backfill.sh](file:///Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/scripts/bash_backfill.sh) | Historical data fetching |

### 3.3 Data Freshness

- **Cadence**: Every 15 minutes (matching GDELT update frequency)
- **Latency**: Each cycle fetches only the single latest GKG file (~2-5 seconds download + parse)
- **Health check**: `/health` endpoint reports `ingest_lag_minutes` (healthy < 30 min)
- **Materialized view**: Refreshed after each ingestion. No continuous aggregates (despite schema comment mentioning TimescaleDB; it's standard PostgreSQL with `REFRESH MATERIALIZED VIEW CONCURRENTLY`)

---

## 4. Database Schema

### 4.1 Tables and Views

| Object | Type | Purpose |
|--------|------|---------|
| `signals_v2` | Table | Core raw signals (timestamp, country_code, lat/lon, sentiment, source_url, source_name, themes[], persons[], crisis fields) |
| `countries_v2` | Table | Country reference (code, name, lat, lon) |
| `country_hourly_v2` | Materialized View | Hourly country aggregates (signal_count, avg/min/max sentiment, unique_sources). Refreshed on each ingestion |
| `country_daily_v2` | Referenced in code | **Referenced in nodes endpoint but missing from schema_v2.sql**. Used for extended time ranges (1m, 3m, record) |
| `country_baseline_stats` | Referenced in code | **Referenced in anomalies endpoint but missing from schema_v2.sql**. Stores 7-day rolling avg/stddev per country |
| `signals_country_hourly` | Referenced in code | **Referenced in trends/compare endpoints but missing from schema_v2.sql**. May be a TimescaleDB continuous aggregate from v1 |
| `signals_theme_hourly` | Referenced in code | Same — missing from schema_v2.sql, referenced in trends/compare |
| `signals_source_hourly` | Referenced in code | Same — missing from schema_v2.sql, referenced in trends/compare |

### 4.2 Columns in `signals_v2` (actual vs schema)

The schema_v2.sql defines:
```
id, timestamp, country_code, latitude, longitude, sentiment, source_url, source_name, themes[], persons[], created_at
```

But `ingest_v2.py` INSERTs additional crisis fields:
```
is_crisis, crisis_score, crisis_themes[], severity, event_type
```

> [!WARNING]
> **Schema drift**: The `.sql` file does not include crisis columns (`is_crisis`, `crisis_score`, `crisis_themes`, `severity`, `event_type`). These were likely added via manual ALTER TABLE but never updated in the checked-in schema. This can cause fresh deployments to fail.

### 4.3 Indexes

| Index | Columns |
|-------|---------|
| `idx_signals_v2_timestamp` | `timestamp DESC` |
| `idx_signals_v2_country_time` | `country_code, timestamp DESC` |
| `idx_country_hourly_v2_unique` | `hour, country_code` (UNIQUE, for CONCURRENT refresh) |
| `idx_country_hourly_v2_hour` | `hour DESC` |

> [!NOTE]
> Missing indexes: No index on `themes` (GIN would help), no index on `persons`, no index on `source_name`, no index on `is_crisis`. All theme/person queries unnest arrays and do sequential scans. Performance concern at scale.

---

## 5. What the User Currently Sees

When the user opens `http://localhost:3000`:

**Full-screen dark map** (CartoDB Dark Matter basemap) centered on coordinates (0, 20) at zoom 1.5 — showing roughly the entire world with slight bias toward the Northern Hemisphere.

1. **Glowing country dots**: Each country with news activity has a multi-layered glowing dot. Size = log(signal count) with 3 glow layers + 1 core layer. Color = sentiment (green=positive, amber=neutral, red=negative). The US and UK typically dominate visually.

2. **Flow arcs**: Great-circle arcs connecting countries that share theme coverage. Thicker arcs = stronger theme overlap. Limited to top 25 at default zoom.

3. **Top header**: "OBSERVATORY GLOBAL" with globe icon, a search bar, a "Crisis" toggle button (shield icon), a "Briefing" button, and a settings gear. Live stats show "52 countries • 28,435 signals".

4. **Time controls bar**: Below header — 8 buttons (1 Hour through All Time) + 3 layer toggle buttons (GLOW, FLOW, NODES).

5. **Bottom-left Legend**: Explains node sizes and colors.

**Interaction flow**: Hover a node → tooltip. Click a node → right sidebar with country detail (narrative, signal count, sentiment, top 5 themes, source diversity). Click a theme chip → theme detail modal (timeline chart, country breakdown, related themes, sources, persons, signals). Click "Briefing" → full-screen briefing overlay. Toggle "Crisis" → red-tinted UI + anomaly dashboard.

**Overall impression**: Looks like an intelligence monitoring tool. Dark, data-dense header area sits atop a mostly empty map. The map is the sole persistent visualization. All detail is hidden behind clicks and modals. No persistent secondary panels. No live signal stream.

---

## 6. Data That Exists But Is NOT Shown

| Data Available | Endpoint | Missing UI |
|----------------|----------|-----------|
| **System stats** (total signals, 1h/24h/7d counts, ingestion health) | `/api/v2/stats` | No system health widget |
| **Time-series trends** (hourly/daily bucketed data per country/theme/source) | `/api/v2/trends` | No sparklines, no trend charts visible on main view |
| **Period comparison** (signal delta %, sentiment delta between two windows) | `/api/v2/compare` | No change indicators (▲/▼) on countries |
| **Crisis-classified signals** (severity, event_type, crisis_score) | `/api/v3/crisis/signals`, `/api/v3/crisis/summary` | Only anomaly (volume spike) data shown in Crisis Dashboard. No event-type breakdown, no severity filtering, no crisis signal feed |
| **Trust indicators** (source diversity score, source quality score, normalized volume) | `/api/indicators/country/{code}` | Fully implemented backend + frontend component (`CountryBrief`) exists but is **never rendered** |
| **Raw signal list** with filters | `/api/v2/signals` | No signal feed anywhere in main UI |
| **Person entity data** | Stored in `persons[]` array, searchable via `/api/v2/search` | Person search works but clicking a person only sets focus — no person-specific detail view |
| **Source URLs / headlines** | Stored in `source_url`, returned in focus data | Headlines shown in FocusSummaryPanel but only as source names (no titles) |
| **Shared theme detail on flows** | `/api/v2/flows` returns `sharedThemes` and `similarity` | Flow tooltip shows strength but not the specific shared themes |

---

## 7. Broken, Placeholder, or Incomplete Features

### 7.1 Broken or At-Risk

| Issue | Severity | Detail |
|-------|----------|--------|
| **Schema file incomplete** | HIGH | `schema_v2.sql` missing crisis columns, `country_daily_v2`, `country_baseline_stats`, and all hourly aggregate tables referenced by `/api/v2/trends` and `/api/v2/compare`. Fresh deploy from schema will break 5+ endpoints |
| **SQL injection risk in `%` formatting** | MEDIUM | Multiple endpoints use Python `%` string formatting for hours/days values instead of parameterized queries (lines 338, 391, 548, 567, etc.). While the values come from validated `Query()` integers, this is fragile |
| **`country_daily_v2` table** | MEDIUM | Referenced by nodes endpoint for extended ranges (1m, 3m, record) but no creation/refresh logic exists anywhere in the codebase. If the table doesn't exist, these ranges will error |
| **Trends/Compare endpoints silently broken** | MEDIUM | Reference `signals_country_hourly`, `signals_theme_hourly`, `signals_source_hourly` — names that don't match the actual materialized view (`country_hourly_v2`). These are likely leftover v1 references |
| **Source selection handler is a no-op** | LOW | `onSourceSelect={(source) => console.log('Source selected:', source)}` in App.tsx line 371 |

### 7.2 Incomplete Features

| Feature | State | What's Missing |
|---------|-------|---------------|
| **Country Executive Brief** (`CountryBrief.tsx`) | 326 lines of fully built component + CSS | Never imported into App.tsx. Has trust indicators integration but unreachable |
| **Crisis Signal Feed** | Backend endpoints exist (`/api/v3/crisis/signals`, `/api/v3/crisis/summary`) | No frontend component to display crisis signals by severity/type |
| **Trend visualization** | Backend `/api/v2/trends` returns time-bucketed data | No chart/sparkline component. Endpoint may also be broken (wrong table names) |
| **Error tracking** | Health endpoint has `error_count_last_15m: 0` | Hardcoded TODO. No error tracking table implemented |
| **Person detail view** | Search returns persons, focus mode accepts persons | No distinct person detail component — person focus just filters map nodes |
| **Data retention** | Module exists at `data_retention.py` (5.8KB) | Retention config table referenced but not confirmed in use |

### 7.3 Deprecated Code

| Item | Detail |
|------|--------|
| `frontend/` directory | Full v1 frontend (TailwindCSS). Has `DEPRECATED.md`. Still has `node_modules` and build artifacts taking disk space |
| `/api/v2/heatmap` endpoint | Returns empty response with deprecation message |
| `flow_detector.py` (20KB) | Separate flow detection service. Superseded by inline Jaccard calculation in `main_v2.py` |
| `gdelt_placeholder_generator.py` (30KB) | Generates synthetic test data. Not production-relevant |
| Multiple backend service files | `aggregator.py`, `gdelt_ingest.py`, `gdelt_client.py`, `gdelt_downloader.py`, `gdelt_parser.py` — unclear if these are v1 artifacts or still used elsewhere |

---

## 8. Architecture Summary

```
┌─────────────────────────────────────────────────┐
│                  Frontend (SPA)                  │
│  React + TypeScript + Vite (port 3000)           │
│  MapLibre + Deck.gl (ScatterplotLayer, ArcLayer) │
│  4 Context Providers  │  22 Components           │
│  Proxy: /api/* → localhost:8000                  │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│                Backend (FastAPI)                  │
│  Python 3.11 + asyncpg (port 8000)               │
│  Single file: main_v2.py (1655 lines)            │
│  19 endpoints (v2 + v3)                          │
│  Indicators module (3 metric calculators)        │
└────────────────────┬────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              PostgreSQL Database                  │
│  signals_v2 (core table)                         │
│  countries_v2 (reference)                        │
│  country_hourly_v2 (materialized view)           │
│  + several tables created outside schema_v2.sql  │
└─────────────────────────────────────────────────┘
                     ▲
                     │
┌─────────────────────────────────────────────────┐
│            GDELT Ingestion Pipeline              │
│  auto_ingest_v2.sh (every 15 min cron loop)      │
│  → ingest_v2.py → download GKG → parse → insert │
│  → crisis classification → refresh mat. views    │
└─────────────────────────────────────────────────┘
```
