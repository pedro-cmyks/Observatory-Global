-- 062_disaster_events.sql — structured disaster event feed (event-source-evaluation §2).
-- Natural-hazard events (earthquake / volcano / flood / cyclone / wildfire) that GDELT CAMEO
-- structurally CANNOT represent (no actor, no action code for the Earth moving). Authoritative,
-- real-time, machine-readable: USGS FDSN (earthquakes, no key) + GDACS RSS (multi-hazard, CC-BY).
-- These bind to the disaster-category dynamic_topics (earthquake-volcano / flood-landslide /
-- wildfire-storm) by country + time + type — the movement role, verified=false, never evidence.
-- Additive: a new table; touches nothing served today.

CREATE TABLE IF NOT EXISTS disaster_events_v2 (
    event_id        TEXT PRIMARY KEY,          -- USGS feature id ('us7000...') / GDACS 'EQ1000123'
    source          TEXT NOT NULL,             -- 'usgs' | 'gdacs'
    event_type      TEXT NOT NULL,             -- earthquake | volcano | flood | cyclone | wildfire | drought
    title           TEXT,                      -- human place/description ('10km S of Pangai, Tonga')
    country_code    CHAR(2),                   -- ISO2 subject country (best-effort; NULL if unmapped)
    latitude        DOUBLE PRECISION,
    longitude       DOUBLE PRECISION,
    magnitude       DOUBLE PRECISION,          -- USGS mag; GDACS type-specific severity (may be NULL)
    alert_level     TEXT,                      -- GDACS Green/Orange/Red; USGS derived from sig
    event_time      TIMESTAMPTZ NOT NULL,
    url             TEXT,
    population_affected BIGINT,                -- GDACS only (NULL for USGS)
    raw             JSONB,                     -- full source payload (provenance)
    ingested_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Binding + serving query paths: by country+time (geospatial bind) and by recency.
CREATE INDEX IF NOT EXISTS idx_disaster_events_country_time
    ON disaster_events_v2 (country_code, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_disaster_events_time
    ON disaster_events_v2 (event_time DESC);
CREATE INDEX IF NOT EXISTS idx_disaster_events_type
    ON disaster_events_v2 (event_type, event_time DESC);

COMMENT ON TABLE disaster_events_v2 IS
    'Structured natural-hazard events (USGS earthquakes + GDACS multi-hazard). The gap CAMEO '
    'cannot fill (event-source-evaluation §2). Bind to disaster-category topics via country+time+type '
    'as movement members (verified=false, context not evidence).';
