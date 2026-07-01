-- 061_crisis_relevance_lens.sql — reframe crisis/non_crisis binary → open category +
-- a crisis-relevance LENS (Pedro, 2026-07-01). Atlas tracks NARRATIVES; a World Cup is
-- a narrative, not a "reject". So `category` is the OPEN category for every story
-- (crisis seed label OR emergent label), and `crisis_relevant` is a FLAG the analyst
-- filters on ("show me the serious/crisis stuff") — not a taxonomy divide that makes
-- non-crisis second-class. Additive + reversible.
BEGIN;

ALTER TABLE dynamic_topics ADD COLUMN IF NOT EXISTS crisis_relevant BOOLEAN;

-- the LENS: did the story match a crisis seed (#204)? (replaces the crisis/non_crisis binary)
UPDATE dynamic_topics
   SET crisis_relevant = (crisis_class IS NOT NULL AND crisis_class <> 'non_crisis')
 WHERE crisis_class IS NOT NULL;

-- category is now the OPEN category for everyone: a crisis story takes its seed label
-- as its category (so the badge is uniform — every categorized story shows its category,
-- crisis or not). Emergent categories (World Cup / Travel …) already sit in `category`.
UPDATE dynamic_topics
   SET category = crisis_class
 WHERE crisis_relevant = true AND (category IS NULL OR category = '');

CREATE INDEX IF NOT EXISTS idx_dynamic_topics_crisis_relevant
  ON dynamic_topics (crisis_relevant) WHERE crisis_relevant = true;

COMMIT;

-- Reversible: ALTER TABLE dynamic_topics DROP COLUMN crisis_relevant;
