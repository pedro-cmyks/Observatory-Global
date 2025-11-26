# PROJECT CONTEXT: GLOBAL OBSERVATORY

## What is the Global Observatory

The Global Observatory is a system for visualizing and analyzing global information flows. Its goal is to allow users to understand what narratives are circulating worldwide, how they propagate between geographies, and who is pushing them.

**Current project state:**
- Functional frontend with interactive map (React + Mapbox)
- Three visualization modes: Heatmap, Flows, Nodes
- Basic connection to GDELT that queries and plots coordinates
- NO data persistence (resets every 15 minutes)
- NO real analysis (just a scatter plot of coordinates)
- NO meaningful calculation of flows between countries
- Displayed data may be placeholders

**Current stack:**
- Frontend: React + Mapbox
- Backend: (to be defined/improved)
- Database: PostgreSQL

---

## GOAL OF THIS PHASE

Build the **data infrastructure** required for the Global Observatory to function meaningfully. This involves:

1. Persisting GDELT events in PostgreSQL
2. Intelligent aggregation system by theme/geography/time
3. Real calculation of flows between countries
4. Basic anomaly detection (what's trending vs what's noise)

---

## PROPOSED DATA ARCHITECTURE

### 1. DATABASE SCHEMA

```sql
-- Main table: raw GDELT events
CREATE TABLE gdelt_events (
    id SERIAL PRIMARY KEY,
    gdelt_id VARCHAR(50) UNIQUE,
    event_date TIMESTAMP NOT NULL,
    
    -- Actors
    actor1_name VARCHAR(255),
    actor1_country_code VARCHAR(3),
    actor1_type VARCHAR(50),
    actor2_name VARCHAR(255),
    actor2_country_code VARCHAR(3),
    actor2_type VARCHAR(50),
    
    -- Geography
    action_country_code VARCHAR(3),
    action_lat DECIMAL(10, 6),
    action_lon DECIMAL(10, 6),
    
    -- GDELT categorization
    event_code VARCHAR(10),
    event_root_code VARCHAR(10),
    quad_class INTEGER, -- 1=Verbal Coop, 2=Material Coop, 3=Verbal Conflict, 4=Material Conflict
    goldstein_scale DECIMAL(4, 1), -- -10 to +10, event tone
    
    -- Source
    source_url TEXT,
    source_domain VARCHAR(255),
    
    -- Metadata
    num_mentions INTEGER,
    num_sources INTEGER,
    num_articles INTEGER,
    avg_tone DECIMAL(5, 2),
    
    -- Internal timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Indexes for frequent queries
    INDEX idx_event_date (event_date),
    INDEX idx_action_country (action_country_code),
    INDEX idx_actor1_country (actor1_country_code),
    INDEX idx_actor2_country (actor2_country_code)
);

-- Aggregation table by country and time window
CREATE TABLE country_aggregates (
    id SERIAL PRIMARY KEY,
    country_code VARCHAR(3) NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    window_type VARCHAR(10) NOT NULL, -- '1h', '6h', '12h', '24h'
    
    -- Aggregated metrics
    total_events INTEGER DEFAULT 0,
    total_mentions INTEGER DEFAULT 0,
    total_sources INTEGER DEFAULT 0,
    avg_tone DECIMAL(5, 2),
    
    -- Distribution by event type
    verbal_coop_count INTEGER DEFAULT 0,
    material_coop_count INTEGER DEFAULT 0,
    verbal_conflict_count INTEGER DEFAULT 0,
    material_conflict_count INTEGER DEFAULT 0,
    
    -- For normalization
    intensity_score DECIMAL(5, 2), -- Normalized 0-100
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(country_code, window_start, window_type)
);

-- Flows between countries table
CREATE TABLE country_flows (
    id SERIAL PRIMARY KEY,
    source_country VARCHAR(3) NOT NULL,
    target_country VARCHAR(3) NOT NULL,
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    window_type VARCHAR(10) NOT NULL,
    
    -- Flow metrics
    event_count INTEGER DEFAULT 0, -- Events involving both countries
    mention_count INTEGER DEFAULT 0,
    avg_tone DECIMAL(5, 2), -- Average tone of the relationship
    
    -- Normalized weight for visualization
    flow_weight DECIMAL(5, 2), -- 0-100, for line thickness
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(source_country, target_country, window_start, window_type)
);

-- Trending themes/categories table
CREATE TABLE trending_themes (
    id SERIAL PRIMARY KEY,
    theme_code VARCHAR(20) NOT NULL, -- GDELT event code or derived category
    theme_name VARCHAR(255),
    window_start TIMESTAMP NOT NULL,
    window_end TIMESTAMP NOT NULL,
    window_type VARCHAR(10) NOT NULL,
    
    -- Metrics
    event_count INTEGER DEFAULT 0,
    country_count INTEGER DEFAULT 0, -- How many countries it appears in
    avg_tone DECIMAL(5, 2),
    
    -- For anomaly detection
    baseline_avg DECIMAL(10, 2), -- Historical average
    current_value DECIMAL(10, 2),
    anomaly_score DECIMAL(5, 2), -- How far above/below baseline
    is_trending BOOLEAN DEFAULT FALSE,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(theme_code, window_start, window_type)
);

-- Relevant actors table
CREATE TABLE actors (
    id SERIAL PRIMARY KEY,
    actor_name VARCHAR(255) NOT NULL,
    actor_type VARCHAR(50),
    country_code VARCHAR(3),
    
    -- Accumulated metrics (updated periodically)
    total_mentions INTEGER DEFAULT 0,
    avg_tone DECIMAL(5, 2),
    first_seen TIMESTAMP,
    last_seen TIMESTAMP,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(actor_name, actor_type, country_code)
);

-- Historical baseline table (for anomaly detection)
CREATE TABLE historical_baselines (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR(20) NOT NULL, -- 'country', 'flow', 'theme'
    entity_id VARCHAR(50) NOT NULL, -- country_code, 'US-CO', theme_code
    metric_name VARCHAR(50) NOT NULL, -- 'event_count', 'mention_count', etc.
    
    -- Historical statistics
    avg_value DECIMAL(10, 2),
    std_dev DECIMAL(10, 2),
    min_value DECIMAL(10, 2),
    max_value DECIMAL(10, 2),
    sample_count INTEGER,
    
    -- Calculation period
    calculated_from TIMESTAMP,
    calculated_to TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(entity_type, entity_id, metric_name)
);
```

### 2. DATA INGESTION LOGIC

The system must run a process every 15 minutes (synchronized with GDELT):

```python
# Pseudocode for the ingestion process

def ingest_gdelt_data():
    """
    Main process that runs every 15 minutes
    """
    
    # 1. Fetch latest events from GDELT
    new_events = fetch_gdelt_last_15_minutes()
    
    # 2. Insert raw events (upsert to avoid duplicates)
    insert_raw_events(new_events)
    
    # 3. Recalculate aggregates for all active windows
    recalculate_aggregates()
    
    # 4. Recalculate flows between countries
    recalculate_flows()
    
    # 5. Detect trending themes
    detect_trending_themes()
    
    # 6. Update baselines if needed (every 24h)
    if should_update_baselines():
        update_historical_baselines()
```

### 3. FLOW CALCULATION BETWEEN COUNTRIES

A flow between Country A and Country B is defined as:
- Events where Actor1 is from Country A and Actor2 is from Country B (or vice versa)
- Events where the action occurs in Country A and involves Country B
- Weighted by number of mentions and sources

```python
def calculate_flow(country_a, country_b, window_start, window_end):
    """
    Calculates the flow weight between two countries
    """
    
    query = """
    SELECT 
        COUNT(*) as event_count,
        SUM(num_mentions) as total_mentions,
        AVG(avg_tone) as avg_tone
    FROM gdelt_events
    WHERE event_date BETWEEN %s AND %s
    AND (
        (actor1_country_code = %s AND actor2_country_code = %s)
        OR (actor1_country_code = %s AND actor2_country_code = %s)
        OR (action_country_code = %s AND (actor1_country_code = %s OR actor2_country_code = %s))
        OR (action_country_code = %s AND (actor1_country_code = %s OR actor2_country_code = %s))
    )
    """
    
    # Weight is normalized against the maximum global flow in that window
    # so that line thickness is relative
```

### 4. ANOMALY DETECTION

To surface what's interesting vs noise:

```python
def calculate_anomaly_score(current_value, baseline_avg, baseline_std):
    """
    Calculates how anomalous a value is compared to its baseline
    Uses z-score: (value - mean) / standard_deviation
    """
    if baseline_std == 0:
        return 0
    
    z_score = (current_value - baseline_avg) / baseline_std
    return z_score

def is_trending(z_score, threshold=2.0):
    """
    A theme/country/flow is trending if its z-score exceeds the threshold
    threshold=2.0 means ~2 standard deviations above normal
    """
    return abs(z_score) > threshold
```

### 5. INTENSITY NORMALIZATION

So that small countries don't become invisible:

```python
def calculate_normalized_intensity(country_code, raw_count, window_type):
    """
    Normalizes a country's intensity considering its historical baseline
    """
    
    baseline = get_baseline(country_code, 'event_count')
    
    if baseline.avg_value == 0:
        return 50  # Neutral value if no history
    
    # Ratio compared to its own historical average
    ratio = raw_count / baseline.avg_value
    
    # Convert to 0-100 scale with sigmoid to avoid extremes
    intensity = 100 / (1 + math.exp(-2 * (ratio - 1)))
    
    return intensity
```

---

## REQUIRED API ENDPOINTS

The frontend needs these endpoints:

```
GET /api/heatmap?window=24h
  → Returns: List of countries with centroid coordinates and normalized intensity

GET /api/flows?window=24h&min_weight=10
  → Returns: List of flows between countries with weight for line thickness

GET /api/nodes?window=24h
  → Returns: Aggregation of all flows to/from each country

GET /api/country/{country_code}?window=24h
  → Returns: Country detail (metrics, dominant themes, actors, etc.)

GET /api/trending?window=24h
  → Returns: Themes/countries/flows with high anomaly_score

GET /api/search?q=tesla&window=24h
  → Returns: Events/countries/flows related to the search term
```

---

## IMMEDIATE TASKS

1. **Create the tables in PostgreSQL** according to the proposed schema

2. **Implement the ingestion job** that runs every 15 minutes:
   - Connect to GDELT API
   - Parse and clean data
   - Insert into `gdelt_events`

3. **Implement aggregation jobs** that run after ingestion:
   - Calculate `country_aggregates` for each time window
   - Calculate `country_flows`
   - Detect `trending_themes`

4. **Create the API endpoints** to serve data to the frontend

5. **Modify the frontend** to consume these endpoints instead of making direct GDELT queries

---

## TECHNICAL NOTES

- GDELT updates every 15 minutes; the job must be synchronized
- Flows should be bidirectional (A→B is the same as B→A for visualization)
- Storing history indefinitely can be expensive; consider retention policy (e.g., raw events 30 days, aggregates 1 year)
- Baselines should be recalculated periodically (daily or weekly)
- For text search (future), consider PostgreSQL full-text search or Elasticsearch

---

## QUESTIONS FOR THE DEVELOPER

Before implementing, please confirm:
1. Does the project already have a backend structure (FastAPI, Express, etc.) or does it need to be created?
2. Is there a cron job or scheduler configured for periodic tasks?
3. Is the PostgreSQL connection already configured?
4. What is the exact format of the data that GDELT currently returns?
