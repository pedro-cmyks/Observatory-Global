# REDESIGN PROPOSAL — Bloomberg-Style Terminal for Observatory Global

> **Generated**: 2026-03-13  
> **Philosophy**: Every pixel earns its place. Show what IS happening, not what happened.

---

## Design Principles

1. **Dense, not cluttered** — Multiple simultaneous data streams in divided panels, each a different lens on the same reality
2. **Time-contextual** — Every metric shows when it emerged, how fast it's moving, what it looked like before
3. **Cross-linked** — Clicking in one panel filters all others. Panels are not islands, they're coordinated views
4. **No empty space** — The current full-screen map wastes 70% of viewport. A terminal uses every row
5. **Assume intent** — No onboarding, no empty states. If there's no data, show why

---

## Proposed Panel Layout

### Primary Layout — Desktop (≥1440px)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  OBSERVATORY GLOBAL    [Search...]    [24H] [1W] [1M]    [CRISIS] [⚙]  │
├─────────────────────────────────┬────────────────────────────────────────┤
│                                 │                                        │
│                                 │   2. SIGNAL STREAM                     │
│                                 │   ┌─────────────────────────────────┐  │
│   1. GLOBAL RADAR               │   │ ▸ 09:31 US ECON_TRADE +2.1    │  │
│   (Map — 55% width)             │   │ ▸ 09:31 UK TAX_POLICY -3.4    │  │
│                                 │   │ ▸ 09:30 CN DIPLOMACY  +0.8    │  │
│   Country nodes + flow arcs     │   │ ▸ 09:30 DE ECON_TRADE -1.2    │  │
│   Click = lock all panels       │   │ ▸ 09:29 JP CYBER_ATTACK -5.1  │  │
│                                 │   │   ... scrolling ...             │  │
│                                 │   └─────────────────────────────────┘  │
│                                 │                                        │
│                                 │   VELOCITY: 23 sig/min ▲ (+14%)       │
├─────────────────────────────────┼──────────────────┬─────────────────────┤
│                                 │                  │                     │
│   3. NARRATIVE THREADS          │ 4. CORRELATION   │ 5. ANOMALY ALERT   │
│                                 │    MATRIX        │                     │
│   Topic lifecycle timeline      │                  │ ▸ CRITICAL: NG ×3.2│
│   ─────●────●─────●───────→     │  US UK DE FR CN  │ ▸ ELEVATED: EG ×2.1│
│         ↑    ↑     ↑            │  ██ ▓▓ ▒▒ ░░ ░░  │ ▸ NOTABLE:  PK ×1.5│
│        DE   FR    CN            │  ▓▓ ██ ▓▓ ▒▒ ░░  │                     │
│                                 │  ▒▒ ▓▓ ██ ▓▓ ░░  │ 6. SOURCE INTEGRITY│
│   Propagation + velocity        │  ░░ ▒▒ ▓▓ ██ ▒▒  │    Diversity: 73/100│
│                                 │  ░░ ░░ ░░ ▒▒ ██  │    Quality:  81/100 │
│                                 │                  │    Volume:   1.2× ▶ │
└─────────────────────────────────┴──────────────────┴─────────────────────┘
```

### Panel Sizing

| Panel | Width | Height | Content |
|-------|-------|--------|---------|
| **Global Radar** | 55% | 60% of viewport | Map (shrunk from 100%) |
| **Signal Stream** | 45% | 60% of viewport | Live signal feed |
| **Narrative Threads** | 40% | 40% of viewport | Timeline visualization |
| **Correlation Matrix** | 30% | 40% of viewport | Heatmap grid |
| **Anomaly Alert** | 30% | 20% of viewport | Alert list |
| **Source Integrity** | 30% | 20% of viewport | Trust metrics |

### Responsive Breakpoints

| Screen | Behavior |
|--------|----------|
| ≥1440px | Full 6-panel layout as above |
| 1024–1439px | 2-column: Radar (full top) + tabbed bottom panels (Stream/Threads/Matrix/Alerts) |
| <1024px | Single column: Radar + stacked accordion panels |

---

## Panel Specifications

### Panel 1: GLOBAL RADAR (Existing → Enhanced)

**Data source**: Existing `/api/v2/nodes` + `/api/v2/flows`

**Changes from current**:
- Shrink from 100% viewport to 55% left panel
- Node color shift from pure sentiment → **narrative intensity** (signal count delta vs baseline). Red = spiking. Blue = quiet. Green = positive shift
- **Country locking**: Click a country → all other panels filter to that country. Header shows locked country badge
- Add pulsing ring for anomaly countries (use existing anomaly data from `/api/v2/anomalies`)
- Flow arc tooltips show shared themes (data already returned, currently hidden)

**New endpoints needed**: None. Existing data covers this.

---

### Panel 2: SIGNAL STREAM (New)

**What it shows**: Live-scrolling feed of incoming GDELT signals. Each row:
```
[timestamp] [country_flag] [theme_label] [sentiment_bar] [source_name]
```

**Data source**: **New endpoint needed** — `/api/v2/signals/stream`

```python
# Proposed endpoint
@app.get("/api/v2/signals/stream")
async def get_signal_stream(
    country: str = None,     # Filter by locked country
    theme: str = None,       # Filter by theme
    limit: int = 50,         # Number of recent signals
    since: str = None        # ISO timestamp for polling
):
    """Returns latest signals ordered by timestamp DESC.
    Frontend polls every 15-30 seconds."""
```

**Velocity metric**: Count of signals per minute in the current window. Compare to previous window for ▲/▼.

**Can be partially built from existing**: `/api/v2/signals` already returns raw signals with filters. Needs "since" parameter for incremental polling and a velocity calculation.

---

### Panel 3: NARRATIVE THREADS (New)

**What it shows**: A topic's lifecycle as a horizontal timeline. When it emerged, which countries picked it up (as dots on the timeline), current velocity (accelerating/fading).

**Data source**: `/api/v2/trends` endpoint (PARTIALLY EXISTING — currently uses wrong table names though)

**New endpoint needed** — `/api/v2/theme/{code}/propagation`

```python
# Proposed endpoint
@app.get("/api/v2/theme/{theme_code}/propagation")
async def get_theme_propagation(
    theme_code: str,
    hours: int = 168
):
    """Theme propagation: first appearance per country, ordered by time.
    Shows how a narrative spread geographically."""
    # Query: GROUP BY country_code, date_trunc('hour', timestamp)
    # Return: [{country, first_seen, signal_count, peak_hour}]
```

**Frontend**: D3.js or Recharts-based timeline. Horizontal axis = time. Dots = countries that picked up the theme. Dot size = signal volume. Color = sentiment.

**Can be partially built from existing**: `/api/v2/theme/{code}` already returns per-country breakdown and timeline. Needs first-seen timestamps per country to show propagation order.

---

### Panel 4: CORRELATION MATRIX (Partially Existing)

**What it shows**: Heatmap grid of theme co-occurrence between countries. Which countries are talking about the same things?

**Data source**: Existing `/api/v2/flows` already computes Jaccard similarity between country theme vectors. The correlation matrix is simply the **full similarity matrix** instead of just the top 100 flows.

**New endpoint needed** — `/api/v2/correlation`

```python
# Proposed endpoint  
@app.get("/api/v2/correlation")
async def get_correlation_matrix(
    range: str = "24h",
    top_n: int = 15          # Top N countries by activity
):
    """Returns NxN correlation matrix of theme similarity between top countries."""
    # Reuse Jaccard similarity logic from flows endpoint
    # Return: {countries: [...], matrix: [[similarity, ...], ...]}
```

**Frontend**: Canvas-based heatmap (similar to D3 heatmap). Cell color intensity = Jaccard similarity. Click a cell → show shared themes between those two countries.

---

### Panel 5: ANOMALY ALERT (Existing → Extracted)

**Data source**: Existing `/api/v2/anomalies` (already consumed by `CrisisDashboard`)

**Changes**:
- Extract from Crisis Mode into a permanent dedicated panel (always visible, not behind toggle)
- Add: **topic anomalies** (not just country-level volume spikes). New query: which themes appeared in countries where they never appeared before?
- Add: **source anomalies** — sudden appearance of a topic from an unusual source pool

**New endpoint needed** — `/api/v2/anomalies/themes`

```python
# Proposed endpoint
@app.get("/api/v2/anomalies/themes")
async def get_theme_anomalies(hours: int = 24, limit: int = 10):
    """Detect themes appearing in unusual countries or with unusual velocity."""
    # Compare current theme-country pairs against 7-day baseline
    # Flag: "CYBER_ATTACK in BR — first appearance in 30 days"
```

---

### Panel 6: SOURCE INTEGRITY VIEW (Existing → Surfaced)

**Data source**: Existing `/api/indicators/country/{code}` — fully implemented backend, fully built frontend component (`CountryBrief.tsx` + `IndicatorTooltip.tsx`)

**Changes**:
- **Surface the already-built UI** from the orphaned `CountryBrief` component
- Show for the currently locked/selected country
- Add global aggregate: overall source diversity score across all active countries
- Show source concentration: "82% of signals from top 3 sources" as a warning metric

**New endpoint needed**: None for basic version. Already built.

---

## Panel Cross-Linking (The Bloomberg Behavior)

The key differentiator: **panels are coordinated views, not isolated widgets**.

| User Action | Effect |
|-------------|--------|
| Click country on **Radar** | Stream filters to that country. Threads shows that country's top theme. Correlation highlights row/column. Anomaly highlights that country. Source Integrity shows that country's metrics |
| Click theme in **Stream** | Radar highlights countries with that theme. Threads shows that theme's lifecycle. Correlation dims non-relevant countries |
| Click cell in **Correlation** | Radar highlights both countries. Stream filters to shared themes. Threads shows the strongest shared theme |
| Click anomaly in **Alert** | Radar zooms to that country/theme. Stream filters. Everything locks |

**Implementation**: Global filter context (extend existing `FocusContext`) with `{country, theme, timeRange}`. All panels subscribe and filter accordingly.

---

## Mapping: Existing Data vs New Endpoints

| Panel | Existing Endpoints | New Endpoints Needed |
|-------|-------------------|---------------------|
| Global Radar | `/api/v2/nodes`, `/api/v2/flows`, `/api/v2/anomalies` | None |
| Signal Stream | `/api/v2/signals` (partial) | `/api/v2/signals/stream` (add `since` param + velocity) |
| Narrative Threads | `/api/v2/theme/{code}` (partial), `/api/v2/trends` (broken) | `/api/v2/theme/{code}/propagation`, fix `/api/v2/trends` |
| Correlation Matrix | `/api/v2/flows` (has the math) | `/api/v2/correlation` (reshape flows data as NxN matrix) |
| Anomaly Alert | `/api/v2/anomalies` | `/api/v2/anomalies/themes` (theme-level anomalies) |
| Source Integrity | `/api/indicators/country/{code}` | None (already built) |

**Summary**: 3 genuinely new endpoints + 1 fix + 1 parameter addition. Most of the backend data already exists.

---

## Implementation Priority

### Phase 1: Foundation (Highest Value, Lowest Risk)
> *Get the panel layout working with existing data*

1. **CSS Grid shell** — Replace the full-screen map with a 6-panel responsive grid
2. **Shrink Global Radar** into Panel 1 (55% width, existing DeckGL code)
3. **Surface Source Integrity** — Literally rescue `CountryBrief.tsx` from the dead and place it in Panel 6
4. **Extract Anomaly Alert** — Move `CrisisDashboard` content into permanently visible Panel 5
5. **Global filter context** — Extend `FocusContext` to support country+theme locking across all panels

**Backend work**: Zero. All data already exists.

### Phase 2: Signal Stream (Highest Impact New Feature)

1. Add `since` parameter to `/api/v2/signals` endpoint
2. Add velocity calculation (signals/min in current vs previous window)
3. Build `SignalStream.tsx` component with auto-scrolling, country/theme filtering
4. Wire to global filter context

**Backend work**: Minimal — add 2 params to existing endpoint + 1 small query.

### Phase 3: Narrative Threads + Correlation Matrix

1. Fix `/api/v2/trends` endpoint (correct table references)
2. Build `/api/v2/theme/{code}/propagation` endpoint
3. Build `/api/v2/correlation` endpoint (reshape existing Jaccard logic)
4. Build `NarrativeThreads.tsx` with Recharts timeline
5. Build `CorrelationMatrix.tsx` with canvas heatmap

**Backend work**: 2 new endpoints + 1 fix.

### Phase 4: Advanced Anomalies

1. Build `/api/v2/anomalies/themes` endpoint (theme-level anomalies)
2. Add source anomaly detection
3. Enhance Anomaly Alert panel with theme + source anomalies

**Backend work**: 1 new endpoint with statistical analysis.

---

## New Data Fields Needed from GDELT

| Field | Source | Purpose | Available? |
|-------|--------|---------|-----------|
| **Article title / headline** | GKG field not currently extracted | Show in Signal Stream | Available in GDELT Translingual Export. Would need a second file per ingestion cycle |
| **GCAM sentiment dimensions** | GKG V2GCAM (field 17) | Richer sentiment than single tone number | Available but large. Currently ignored in `parse_gkg_row` |
| **Source country** (where published) | GKG V2SOURCECOLLECTIONIDENTIFIER | Distinguish "where it happened" from "who reported it" | Available but not extracted |
| **Image/video count** | GKG V2ALLNAMES or media mentions | Rich signal about story prominence | Available but not critical |

> [!IMPORTANT]
> None of these are **required** for the redesign. The current data fields (themes, persons, sentiment, source_name, source_url, country_code) are sufficient for all 6 panels. The fields above are enhancement opportunities for Phase 4+.

---

## Technical Constraints & Considerations

1. **No router needed yet** — Keep SPA architecture. Panel layout is CSS Grid, not page routing
2. **DeckGL viewport resize** — MapLibre/DeckGL needs explicit resize when container shrinks from 100% to 55%. Use `useEffect` with `ResizeObserver`
3. **Performance budget** — Signal Stream polling every 15-30s adds ~2 req/min. Correlation matrix query on top-15 countries is O(n²) comparisons = 105 pairs. Fast enough
4. **Mobile experience** — Not a priority (Bloomberg terminals aren't mobile). But the responsive breakpoints ensure it doesn't break entirely
5. **No WebSocket needed** — GDELT updates every 15 min. Polling every 15-30s is fine. WebSocket overhead not justified
6. **Schema cleanup prerequisite** — Before Phase 3, fix `schema_v2.sql` to include all tables that actually exist in the DB (crisis columns, baseline stats, daily rollup)

---

## Questions for Human Review

1. **CountryBrief component** — The orphaned `CountryBrief.tsx` has trust indicators built in. Was it intentionally excluded, or did it fall through a merge? Should we resurrect it as-is or redesign it for the Source Integrity panel?

2. **Ingestion frequency** — Currently fetching only the single latest GKG file per cycle. For Signal Stream velocity to be meaningful, should we also fetch the GDELT Translingual Export (which has titles)? This would roughly double ingestion bandwidth.

3. **Schema source of truth** — Several DB tables exist in production but not in `schema_v2.sql`. Should I create a migration script that reconciles the running DB with the schema file, or generate a new authoritative schema from the live DB?

4. **Crisis Mode** — The current crisis toggle hides/shows a separate dashboard. In the redesign, Anomaly Alert is always visible. Should Crisis Mode instead apply a visual overlay (red tint + severity sorting) across all panels, or should it be removed as a concept?

5. **Flow direction** — The current flow arcs are non-directional (Jaccard similarity). For Narrative Threads, do you want us to derive **temporal direction** (which country mentioned the theme first = origin) even though GDELT doesn't explicitly encode information flow?
