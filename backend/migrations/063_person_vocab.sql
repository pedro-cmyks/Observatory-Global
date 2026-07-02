-- 063: person vocabulary for typeahead (capture-doc G2).
-- The live person aggregate (unnest over 24h signals_v2) costs ~14s — above
-- any interactive timeout, so search/compare person results were permanently
-- degraded-empty. This tiny table is rebuilt by the M1 matview cron.
CREATE TABLE IF NOT EXISTS person_vocab (
    person        TEXT PRIMARY KEY,
    signal_count  INT NOT NULL,
    refreshed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_person_vocab_count ON person_vocab (signal_count DESC);
