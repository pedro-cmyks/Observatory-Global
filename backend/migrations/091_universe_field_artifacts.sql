-- 091_universe_field_artifacts.sql
--
-- The universe field, PRECOMPUTED. Measured 2026-07-27: the request-path build
-- takes 75.5s (2,603 nodes / 6,306 edges / 3.96 MB of JSON) -- longer than the
-- Fly proxy will hold an HTTP request open. Consequences, all measured in
-- production the same day:
--
--   * every cold build was killed by the PROXY (HTTP 000 after ~70s; auditors
--     saw 502 at 32.7s and 61.1s, 0/5 success up to 92.5s),
--   * so the in-process cache could NEVER fill,
--   * and with no stored artifact there was not even a stale payload to serve,
--   * so GET /api/v2/universe sat at 0% availability and the UNIVERSE tab was
--     permanently dark.
--
-- Raising the STATEMENT timeout (20s -> 90s, commit ae877dee) could not fix
-- this: the ceiling was never Postgres, it was the request itself. The fix is
-- structural -- the build leaves the request path. `backend/scripts/
-- build_universe_field.py` computes the payload on the M1 inside the nightly
-- heavy-job mutex and upserts ONE compact row here; the endpoint becomes a
-- pure artifact read that always answers and labels the artifact's age.
--
-- Same shape as the daily edition (075_atlas_daily_editions.sql ->
-- atlas_daily_editions): heavy compute on the M1, one JSONB row, serving reads
-- only that row.
--
-- Keyed on `days` (the timeline window the payload was built for, the
-- endpoint's only query parameter) so a second window can be precomputed later
-- without a schema change. One row per window; the builder upserts.
--
-- Server-only table: written by the M1 builder and read by the API over
-- asyncpg with the service role. It carries no user data and is never reached
-- by a Supabase client key, so it takes no RLS policy / 082-style revokes
-- (same class as atlas_daily_editions).
--
-- Additive + reversible; touches no existing serving path.
--
-- Rollback:
--   DROP TABLE IF EXISTS universe_field_artifacts;

CREATE TABLE IF NOT EXISTS universe_field_artifacts (
    days          INTEGER     PRIMARY KEY,
    generated_at  TIMESTAMPTZ NOT NULL,
    contract      TEXT        NOT NULL,
    node_count    INTEGER     NOT NULL,
    edge_count    INTEGER     NOT NULL,
    -- How long the build actually took. Kept so the "is this still off the
    -- request path?" question stays answerable from data rather than memory.
    build_seconds REAL,
    payload       JSONB       NOT NULL,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (days >= 1),
    CHECK (node_count >= 0),
    CHECK (edge_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_universe_field_artifacts_generated
    ON universe_field_artifacts (generated_at DESC);

COMMENT ON TABLE universe_field_artifacts IS
    'Precomputed universe-v0 field, one row per timeline window; built on the M1 (~75s) so GET /api/v2/universe is a pure artifact read and never builds in-request.';
