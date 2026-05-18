-- Migration 014: Multilingual NLP shadow columns.
-- Enables NLP_MULTILINGUAL_MODE=shadow rollout for issue #162.
-- Production columns nlp_sentiment, nlp_framing, nlp_persons remain unchanged
-- so we can compare multilingual outputs side-by-side for 24h before promotion.

ALTER TABLE signals_v2
    ADD COLUMN IF NOT EXISTS nlp_sentiment_xlm    FLOAT,
    ADD COLUMN IF NOT EXISTS nlp_confidence_xlm   FLOAT,
    ADD COLUMN IF NOT EXISTS nlp_framing_xlm      VARCHAR(30),
    ADD COLUMN IF NOT EXISTS nlp_persons_xlm      JSONB,
    ADD COLUMN IF NOT EXISTS nlp_processed_at_xlm TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS nlp_model_version    VARCHAR(40);

-- Comparison index for shadow-vs-production audit queries.
CREATE INDEX IF NOT EXISTS idx_signals_v2_nlp_xlm_pending
    ON signals_v2 (nlp_processed_at_xlm)
    WHERE nlp_processed_at_xlm IS NULL;
