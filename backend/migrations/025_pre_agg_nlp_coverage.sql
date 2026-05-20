-- Migration 025: NLP coverage columns in pre-aggregates.
-- Issue context: docs/methodology/atlas-data-operating-model-2026-05-19.md,
-- docs/roadmap/2026-05-19-topic-and-signal-class-attack.md.
--
-- Problem:
--   ingest_v2.py populates theme_hourly_v2 and theme_country_hourly_v2 with
--   AVG(sentiment), which reads GDELT V2Tone raw, not the transformer-normalized
--   nlp_sentiment. Briefing, narrative threads, and concept fast-path therefore
--   show raw GDELT tone even when NLP scores exist on signals_v2.
--
-- Design:
--   Add two columns per pre-agg bucket:
--     nlp_signal_count  — count of rows in the bucket with nlp_sentiment NOT NULL
--     avg_nlp_sentiment — average of nlp_sentiment over the same rows (NULL when none)
--
--   The original avg_sentiment column is preserved unchanged for backward
--   compatibility. Downstream readers choose: when nlp_signal_count / signal_count
--   crosses a coverage threshold, render avg_nlp_sentiment; otherwise fall back
--   to the GDELT-derived avg_sentiment with a coverage badge.
--
-- Safety:
--   ADD COLUMN ... DEFAULT 0 in PostgreSQL >= 11 is a metadata-only operation —
--   existing rows expose the virtual default until rewritten on next INSERT
--   ... ON CONFLICT DO UPDATE. No table rewrite, no lock beyond brief catalog
--   update. Run any time, idempotent.
--
-- Out of scope:
--   country_hourly_v2 is a MATERIALIZED VIEW; adding columns requires DROP +
--   recreate and is tracked separately. The two largest pre-agg tables covered
--   here account for the bulk of sentiment surface area.

ALTER TABLE theme_hourly_v2
    ADD COLUMN IF NOT EXISTS nlp_signal_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE theme_hourly_v2
    ADD COLUMN IF NOT EXISTS avg_nlp_sentiment NUMERIC;

ALTER TABLE theme_country_hourly_v2
    ADD COLUMN IF NOT EXISTS nlp_signal_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE theme_country_hourly_v2
    ADD COLUMN IF NOT EXISTS avg_nlp_sentiment NUMERIC;
