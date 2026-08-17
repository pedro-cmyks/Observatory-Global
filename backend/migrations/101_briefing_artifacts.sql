-- 101_briefing_artifacts.sql
--
-- The daily briefing, PRECOMPUTED. Profiled 2026-08-17
-- (docs/research/perf/2026-08-17-briefing-profile.md, ?profile=1, prod, 3x):
--
--   * The Redis cache had been DEAD for an unknown stretch — every write
--     failed on `Object of type Decimal is not JSON serializable` and a bare
--     `except: pass` ate the failure, so EVERY reader paid the full 16-22s
--     serialized recompute (repaired: jsonable_encoder on write + logged
--     failures, commits 1366e40d / 8b8078d4; cache-hit now 0.67-0.85s).
--   * The FILL still costs 15-18s: ~19 sections run 100% serially on one
--     connection (top_atlas_topics alone ~5.8s), and a real reader eats it
--     on every 900s TTL expiry.
--   * The fill is a LOTTERY: `theme_country` + `top_sources` carry a 1.5s
--     budget and degrade on EVERY fill; one fill under contention froze FOUR
--     degraded sections into the cached payload for the next 15 minutes. The
--     request that pays the fill freezes ITS failures for every reader after.
--
-- So the build leaves the request path, exactly like mig 091
-- (universe_field_artifacts, 84s build -> 2.8s read) and 098
-- (country_edition_artifacts):
--
--     backend/scripts/build_briefing_artifact.py --execute   (M1, 30-min cron)
--         -> briefing_artifacts           (one compact JSONB row per window)
--             -> GET /api/v2/briefing: Redis hit -> fresh artifact (<=75 min,
--                2.5 build cycles) -> live assembly (unchanged fallback)
--
-- A build with no reader waiting takes full section budgets (8s instead of
-- 1.5s), RETRIES a degraded run and publishes the run with fewer degraded
-- sections — killing the fill-lottery at the root. ?profile=1 never reads the
-- artifact: it stays the measuring instrument of the live path.
--
-- Keyed on window_hours (the endpoint's only shape parameter). One row per
-- window; the builder upserts. The payload is stored ALREADY jsonable-encoded
-- (Decimal->float, datetime->isoformat) — the exact bytes FastAPI would serve
-- fresh, so artifact-serve == live-serve parity holds by construction.
--
-- Server-only table: written by the M1 builder, read by the API over asyncpg
-- with the service role. Shipped with the deny-all posture anyway (the 082
-- lesson: Supabase DEFAULT PRIVILEGES grant ALL on new tables to
-- anon+authenticated, silently voiding the intended posture — new tables
-- carry the revokes, house rule). RLS enabled with no policies = deny-all for
-- client roles; the service role is unaffected.
--
-- Additive + reversible; with the table absent or empty the handler finds no
-- artifact and behaves exactly as today (Redis -> live assembly).
--
-- Rollback:
--   DROP TABLE IF EXISTS briefing_artifacts;

CREATE TABLE IF NOT EXISTS briefing_artifacts (
    window_hours      INTEGER     PRIMARY KEY,
    payload           JSONB       NOT NULL,
    generated_at      TIMESTAMPTZ NOT NULL,
    -- How long the build's sections actually took (sum of section timings,
    -- ms), so "is this still off the request path?" stays answerable from
    -- data rather than memory.
    build_ms          REAL,
    -- The degraded sections of the PUBLISHED run (after the retry picked the
    -- cleaner of the two). Empty array = a complete edition. Kept denormalized
    -- so "does the artifact still degrade at 8s budgets?" is a cheap scan.
    degraded_segments TEXT[],
    -- Who wrote this row (script@host) — auditable from data, not memory.
    builder           TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (window_hours >= 1 AND window_hours <= 8760)
);

CREATE INDEX IF NOT EXISTS idx_briefing_artifacts_generated
    ON briefing_artifacts (generated_at DESC);

ALTER TABLE briefing_artifacts ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON briefing_artifacts FROM anon;
REVOKE ALL ON briefing_artifacts FROM authenticated;

COMMENT ON TABLE briefing_artifacts IS
    'Precomputed /api/v2/briefing payloads, one row per window; built on the M1 30-min cron with full section budgets + retry so the reader never pays the 15-18s serial fill nor inherits its degraded sections (perf profile 2026-08-17).';
