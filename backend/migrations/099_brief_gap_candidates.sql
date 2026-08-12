-- 099_brief_gap_candidates.sql
--
-- EL VACÍO's daily candidate LEDGER — the instrument that makes its own bar
-- verifiable, because nothing else can.
--
-- M0 (docs/research/brief-daily/2026-08-12-m0-measurement.md §b.1) measured
-- that the attention/self-voice divergence is IRRETRO-MEASURABLE. Two
-- independent, verified causes:
--
--   1. `signals_v2` hot retention is ~7 days and `country_hourly_v2` is a
--      matview over it, so the anomaly side has a one-week memory and
--      `country_daily_v2` is empty;
--   2. the archive lane that would carry the voice side does not compute it —
--      `historical_process_partition.py` sets `bucket["local_voice_ratio"] =
--      None` UNCONDITIONALLY, so `historical_topic_country_daily
--      .local_voice_ratio` is NULL for every row back to 2020-09-15.
--
-- So the bar shipped by T3.2 (multiplier >= 3.0 AND self_voice <= 0.20 AND
-- volume >= 20 AND known_origin_n >= 50) rests on an anomaly side measured over
-- 7 days and a JOINT rate that is bounded, not measured — the measurement's own
-- verdict is "lowest confidence of the three bars". No amount of querying fixes
-- that backwards. Only forward logging does, which is this table.
--
-- Written on EVERY computation of the section (live briefing and nightly seal),
-- for EVERY scored candidate — the near-misses included, with the arm of the
-- bar they failed. Two weeks of these rows answer the question the bar cannot
-- answer today: how often does a real divergence exist, and is 3.0x the right
-- place to stand?
--
-- `self_voice_ratio` is NULLABLE on purpose and NULL is load-bearing. It means
-- "not measurable at this attribution floor" (`known_origin_n < 50`), the same
-- condition `country_heat_v2` collapses into a literal 0.5 that reads like
-- "half local" (migration 017, five of the measurement day's top-ten anomalies
-- carried it). This table never stores that sentinel: unknown is stored as
-- unknown, and `self_voice_status` names which it is.
--
-- One row per (day, country): the section recomputes many times a day (the
-- briefing cache expires every 15 min) and upserts, so the row always reflects
-- the latest computation of that day and the table grows by candidates, not by
-- computations.
--
-- Server-only table: written by the API/seal over asyncpg with the service
-- role, never reached by a Supabase client key, carries no user data — same
-- class as atlas_daily_editions / country_edition_artifacts, so no RLS policy
-- and no 082-style client revokes.
--
-- Additive and reversible; no existing serving path reads it. With the table
-- absent the ledger write fails, is logged, and the section ships unchanged
-- (the write is best-effort by contract — it must never cost the reader a
-- section).
--
-- Rollback:
--   DROP TABLE IF EXISTS brief_gap_candidates;

CREATE TABLE IF NOT EXISTS brief_gap_candidates (
    day               DATE        NOT NULL,
    country_code      CHAR(2)     NOT NULL,
    -- The day's volume against the leave-one-out mean of the country's other
    -- retained days (the shape the production detector uses over the same
    -- matview). Baseline + its day count travel along so a re-derivation never
    -- has to trust a ratio it cannot decompose.
    multiplier        REAL        NOT NULL,
    volume            INTEGER     NOT NULL,
    baseline          REAL,
    baseline_days     INTEGER,
    -- NULL = unknown (known_origin_n < 50). NEVER 0.5-as-fact.
    self_voice_ratio  REAL,
    self_voice_status TEXT        NOT NULL,
    known_origin_n    INTEGER     NOT NULL DEFAULT 0,
    domestic_n        INTEGER     NOT NULL DEFAULT 0,
    -- Whether this candidate was the day's served VACÍO. At most one per day
    -- in practice; not enforced as a constraint because a re-computation
    -- flips it and a partial-day recompute may legitimately change the pick.
    chosen            BOOLEAN     NOT NULL DEFAULT FALSE,
    -- 'live' (briefing request path) or 'seal' (nightly edition build).
    computed_by       TEXT        NOT NULL,
    -- Comma-joined arms of the bar this candidate failed; NULL when it cleared.
    -- The no-silent-filtering rule applied to a ledger: a row that did not make
    -- it says why.
    failed_reasons    TEXT,
    -- Share of the sampled outlets that ran the SAME headline (the repaired
    -- reprint key of T3.1). Measured 2026-08-12 on the witness's own day: 22 of
    -- 24 Timor-Leste outlets carried one Australian wire piece — a surge can be
    -- syndication wearing mastheads. Only computed for the SERVED country (it
    -- costs a receipts query), so NULL means "not measured", never "not
    -- syndicated". Logged because the frozen bar has no syndication arm and the
    -- two-week recalibration should be able to ask whether it needs one.
    top_reprint_share REAL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (day, country_code),
    CHECK (volume >= 0),
    CHECK (known_origin_n >= 0),
    CHECK (domestic_n >= 0),
    CHECK (self_voice_ratio IS NULL
           OR (self_voice_ratio >= 0 AND self_voice_ratio <= 1)),
    CHECK (top_reprint_share IS NULL
           OR (top_reprint_share >= 0 AND top_reprint_share <= 1)),
    CHECK (self_voice_status IN ('measured', 'unknown')),
    -- The sentinel can never enter through this door: an unknown ratio is NULL.
    CHECK ((self_voice_status = 'measured') = (self_voice_ratio IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS idx_brief_gap_candidates_day
    ON brief_gap_candidates (day DESC);

CREATE INDEX IF NOT EXISTS idx_brief_gap_candidates_chosen
    ON brief_gap_candidates (day DESC) WHERE chosen;

COMMENT ON TABLE brief_gap_candidates IS
    'Daily EL VACÍO candidates (attention/self-voice divergence) with the arm of the bar each one failed. The bar is not verifiable retrospectively (7-day hot retention + NULL local_voice_ratio in the archive), so this forward log is the only instrument that can re-derive it. self_voice_ratio NULL = unmeasurable at known_origin_n < 50, never the 0.5 sentinel of country_heat_v2.';
