-- Migration 021: Add signal_class semantic provenance to signals_v2.
-- Issue #155, docs/superpowers/plans/2026-05-18-multisource-intelligence-hardening.md,
-- docs/roadmap/2026-05-19-topic-and-signal-class-attack.md.
--
-- Design principle:
--   signal_class is provenance, NOT NLP-derived. Used to prevent social commentary,
--   wire syndication, and state media from being counted as independent
--   corroboration in cluster/heat scoring (#149, #165).
--
-- Allowed classes (constraint enforces):
--   reporting        — default editorial reporting from any media source family
--   wire             — wire/news-agency syndication (Reuters/AP/AFP)
--   state_media      — sources where is_state_media=true (RT, Sputnik, Global Times, IRNA, etc.)
--   humanitarian     — NGO/humanitarian feeds (ReliefWeb OCHA, IFRC, etc.)
--   social_commentary— social platforms (Reddit, etc.), NOT independent corroboration
--   public_attention — reserved for trends/wikipedia-derived attention rows (future)
--   unknown          — fallback when none of the above apply

ALTER TABLE signals_v2
    ADD COLUMN IF NOT EXISTS signal_class VARCHAR(30) NOT NULL DEFAULT 'reporting';

ALTER TABLE signals_v2
    DROP CONSTRAINT IF EXISTS signals_v2_signal_class_valid;

ALTER TABLE signals_v2
    ADD CONSTRAINT signals_v2_signal_class_valid
    CHECK (signal_class IN (
        'reporting',
        'wire',
        'state_media',
        'humanitarian',
        'social_commentary',
        'public_attention',
        'unknown'
    ));

CREATE INDEX IF NOT EXISTS idx_signals_class_time
    ON signals_v2 (signal_class, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_signals_class_country_time
    ON signals_v2 (signal_class, country_code, timestamp DESC);

-- Backfill: 5 deterministic rules from existing provenance.
-- Order matters: most specific rule wins. Reddit -> social_commentary BEFORE
-- generic source_family='social' (current Reddit signals already have
-- source_family='social' AND attribution_method='reddit_public').
UPDATE signals_v2
SET signal_class = CASE
    WHEN attribution_method = 'reddit_public'
        OR source_family = 'social'                              THEN 'social_commentary'
    WHEN attribution_method = 'reliefweb_ocha'
        OR source_family = 'ngo'                                 THEN 'humanitarian'
    WHEN is_state_media = TRUE
        OR source_family = 'state'                               THEN 'state_media'
    WHEN source_family = 'wire'                                  THEN 'wire'
    WHEN source_family IN ('gdelt','rss','api','independent')    THEN 'reporting'
    ELSE 'unknown'
END
WHERE signal_class = 'reporting'
  AND (
        attribution_method IN ('reddit_public','reliefweb_ocha')
     OR source_family IN ('social','ngo','state','wire','independent','rss','api')
     OR is_state_media = TRUE
  );

-- Sanity counters expected after backfill (informative, not enforced):
--   reporting >> social_commentary, humanitarian, state_media, wire
--   social_commentary ~ count(reddit signals)
--   humanitarian ~ count(reliefweb signals)
