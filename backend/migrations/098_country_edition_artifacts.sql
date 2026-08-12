-- 098_country_edition_artifacts.sql
--
-- The country edition, PRECOMPUTED. Council R4 N26 (2026-08-11): a cold
-- GET /api/v2/country-edition?cc=CO returned 503 db_busy 2-of-3 times ON THE
-- DAY COLOMBIA WAS THE STORY — the fast door does not open exactly when the
-- country is in the news. Re-measured the same day from production, cold:
--
--     cc=CO -> HTTP 503 after 110.8s
--     cc=JP -> HTTP 503 after  21.7s
--     cc=US -> HTTP 503 after  19.2s
--
-- Mechanism (measured against prod from the M1): the door's dominant cost is
-- `_DYNAMIC_TOPICS_COUNTRY_SQL`, the scoped-children query with its correlated
-- array subqueries. It carries a 15s asyncpg budget; when the shared Supabase
-- is under the nightly load it blows through it, the TimeoutError becomes
-- DatabaseBusyError, and the handler answers 503. The 120s Redis layer cannot
-- help: nothing ever succeeds, so the cache never fills. Same shape as the
-- universe field before mig 091 — a build that cannot finish inside a request
-- leaves not even a stale payload to serve.
--
-- So the build leaves the request path, exactly like mig 091
-- (universe_field_artifacts) and 075 (atlas_daily_editions):
--
--     backend/scripts/build_country_editions.py --execute   (M1, nightly)
--         -> country_edition_artifacts   (one compact JSONB row per door)
--             -> the handler: one indexed read, always fast
--
-- The handler keeps its live build as the FALLBACK (stale/absent artifact), and
-- keeps the slot guard on both paths — the guard runs at BUILD time for the
-- artifact, so `payload.slot_guard` is stored with the edition and a reader can
-- still see exactly which row was withheld and why. An artifact whose payload
-- carried no slot_guard block would be indistinguishable from a guard that did
-- not run (N17's own lesson), so the builder refuses to store one.
--
-- Keyed on (country_code, window_hours): the endpoint's only two parameters.
-- One row per door; the builder upserts. Countries are chosen by the builder
-- (top-N by 24h volume + any country spiking against its own baseline), not by
-- this schema — a new selection policy needs no migration.
--
-- Server-only table: written by the M1 builder, read by the API over asyncpg
-- with the service role. It carries no user data and is never reached by a
-- Supabase client key, so it takes no RLS policy / 082-style revokes (same
-- class as atlas_daily_editions and universe_field_artifacts).
--
-- Additive + reversible; touches no existing serving path. With the table
-- absent or empty the handler simply finds no artifact and behaves exactly as
-- it does today (live build, 503 under pressure).
--
-- Rollback:
--   DROP TABLE IF EXISTS country_edition_artifacts;

CREATE TABLE IF NOT EXISTS country_edition_artifacts (
    country_code   CHAR(2)     NOT NULL,
    window_hours   INTEGER     NOT NULL,
    generated_at   TIMESTAMPTZ NOT NULL,
    contract       TEXT        NOT NULL,
    thread_count   INTEGER     NOT NULL,
    -- How many rows the N17 slot guard withheld from THIS door at build time.
    -- Denormalized from payload.slot_guard so "did the guard run, and did it
    -- bite?" is answerable with a cheap scan instead of a JSONB traversal.
    slot_guard_excluded INTEGER NOT NULL DEFAULT 0,
    -- Why this country was built: 'volume_rank' | 'volume_anomaly' | 'explicit'.
    -- Kept so the selection policy stays auditable from data, not memory.
    selection_reason TEXT,
    -- How long the build actually took, so the "is this still off the request
    -- path?" question stays answerable from data rather than memory.
    build_seconds  REAL,
    payload        JSONB       NOT NULL,
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (country_code, window_hours),
    CHECK (window_hours >= 1 AND window_hours <= 24),
    CHECK (thread_count >= 0),
    CHECK (slot_guard_excluded >= 0)
);

CREATE INDEX IF NOT EXISTS idx_country_edition_artifacts_generated
    ON country_edition_artifacts (generated_at DESC);

COMMENT ON TABLE country_edition_artifacts IS
    'Precomputed country-edition-v0 payloads, one row per (country, window); built on the M1 nightly so GET /api/v2/country-edition is an indexed read instead of a 503 on the day the country is in the news (council R4 N26).';
