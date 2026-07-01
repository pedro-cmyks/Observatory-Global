-- 059_r3_unification_schema.sql — R3.0 schema foundation (#229, R3 unification)
-- ADDITIVE-ONLY + daytime-safe + reversible. Unblocks R3.1 (category typing),
-- R3.4a (topic_movement), R3.7 (retirement uses existing cols). The riskier hot-PK
-- swap on topic_members (signal_id nullable + PK widen + default-ref trigger) is a
-- SEPARATE later migration (060), landed off-peak WITH R3.4b/R3.5 (events/attention)
-- when non-signal members actually arrive — per spec §4.6. Here we only stage the
-- member-ref COLUMNS (nullable placeholders) + the 'attention' role so the shape is
-- ready without touching the PK.

BEGIN;

-- 1) topic_members: stage the member-ref extension (columns only, PK unchanged) +
--    the 'attention' role + the deferred rhetorical evidence_role column.
ALTER TABLE topic_members
  ADD COLUMN IF NOT EXISTS member_kind   TEXT DEFAULT 'signal',
  ADD COLUMN IF NOT EXISTS member_ref    TEXT,     -- = signal_id::text for signals (backfilled)
  ADD COLUMN IF NOT EXISTS evidence_role TEXT;     -- rhetorical layer (R3.8), classifier deferred

UPDATE topic_members SET member_ref = signal_id::text WHERE member_ref IS NULL;

-- role CHECK: add 'attention' (evidence/discussion/mood/movement/attention)
ALTER TABLE topic_members DROP CONSTRAINT IF EXISTS topic_members_role_check;
ALTER TABLE topic_members ADD CONSTRAINT topic_members_role_check
  CHECK (role IN ('evidence','discussion','mood','movement','attention'));

-- 2) topic_movement (R3.4a): per-topic volume-vs-baseline z-score. A PROPERTY, not
--    members. Recomputed on the 30-min classifier cron. Cheap, pure-SQL.
CREATE TABLE IF NOT EXISTS topic_movement (
  topic_id       TEXT        NOT NULL,
  window_end     TIMESTAMPTZ NOT NULL,
  volume         INTEGER,
  baseline       REAL,
  zscore         REAL,
  multiplier     REAL,
  engine_version TEXT        NOT NULL DEFAULT 'movement-v1',
  computed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (topic_id, window_end, engine_version)
);
CREATE INDEX IF NOT EXISTS idx_topic_movement_topic ON topic_movement (topic_id, window_end DESC);

-- 3) dynamic_topics: the ANCHORED-EMERGENT category attributes (R3.1).
--    category      = emergent super-cluster label/id (open, grows)
--    crisis_class  = a #204 seed-32 class OR 'non_crisis' (the editorial lens; NULL=untyped)
--    category_confidence = typing confidence
ALTER TABLE dynamic_topics
  ADD COLUMN IF NOT EXISTS category            TEXT,
  ADD COLUMN IF NOT EXISTS crisis_class        TEXT,
  ADD COLUMN IF NOT EXISTS category_confidence REAL;
CREATE INDEX IF NOT EXISTS idx_dynamic_topics_category
  ON dynamic_topics (category) WHERE category IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_dynamic_topics_crisis_class
  ON dynamic_topics (crisis_class) WHERE crisis_class IS NOT NULL;

COMMIT;

-- Reversible (down):
--   ALTER TABLE topic_members DROP COLUMN member_kind, DROP COLUMN member_ref, DROP COLUMN evidence_role;
--   ALTER TABLE topic_members DROP CONSTRAINT topic_members_role_check;
--   ALTER TABLE topic_members ADD  CONSTRAINT topic_members_role_check
--       CHECK (role IN ('evidence','discussion','mood','movement'));
--   DROP TABLE topic_movement;
--   ALTER TABLE dynamic_topics DROP COLUMN category, DROP COLUMN crisis_class, DROP COLUMN category_confidence;
