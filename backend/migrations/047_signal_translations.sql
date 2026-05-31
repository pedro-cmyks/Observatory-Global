-- Migration 047: signal_translations
--
-- Lazy translation cache for signals_v2 headlines. The brief / threads /
-- theme-detail surfaces preserve the original-language headline and
-- render the translation underneath in a secondary color. Headlines are
-- translated on demand the first time a consumer requests a given
-- (signal_id, target_lang) pair, then cached forever (or until the
-- signal row is pruned by ON DELETE CASCADE).
--
-- Spec: docs/superpowers/specs/2026-05-29-emergent-topic-discovery-design.md
-- (Translation layer section).

CREATE TABLE IF NOT EXISTS signal_translations (
    signal_id    BIGINT      NOT NULL REFERENCES signals_v2(id) ON DELETE CASCADE,
    target_lang  TEXT        NOT NULL,
    translated   TEXT        NOT NULL,
    model        TEXT        NOT NULL,           -- e.g. 'deepseek-chat'
    source_lang  TEXT,                           -- original signal language as known at translate time
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (signal_id, target_lang)
);

CREATE INDEX IF NOT EXISTS idx_signal_translations_lang
    ON signal_translations (target_lang, created_at DESC);

ALTER TABLE signal_translations ENABLE ROW LEVEL SECURITY;
-- No policy: anon/authenticated have no SELECT/INSERT through PostgREST.
-- Backend connects as postgres superuser and bypasses RLS (mirrors mig
-- 030 lockdown convention).
