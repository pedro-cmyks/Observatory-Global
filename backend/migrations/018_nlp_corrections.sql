-- Migration 018: nlp_corrections capture for the analyst feedback loop
-- (issue #166, Phase 5 of docs/superpowers/plans/2026-05-18-creative-solutions-execution.md).
--
-- Each row records a single analyst override of NLP output on a specific signal.
-- The table is intentionally narrow: any analyst session writes one row per
-- field changed. Downstream calibration/training jobs read these as the
-- ground-truth set for tuning thresholds and producing fine-tune datasets.

CREATE TABLE IF NOT EXISTS nlp_corrections (
    id                   BIGSERIAL PRIMARY KEY,
    signal_id            BIGINT NOT NULL,
    analyst_id           TEXT NOT NULL,
    original_sentiment   FLOAT,
    corrected_sentiment  FLOAT,
    original_framing     VARCHAR(30),
    corrected_framing    VARCHAR(30),
    original_persons     JSONB,
    corrected_persons    JSONB,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT nlp_corrections_signal_fk
        FOREIGN KEY (signal_id) REFERENCES signals_v2(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nlp_corrections_signal
    ON nlp_corrections (signal_id);

CREATE INDEX IF NOT EXISTS idx_nlp_corrections_analyst_time
    ON nlp_corrections (analyst_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_nlp_corrections_recent
    ON nlp_corrections (created_at DESC);
