-- 058_topic_umbrella.sql — R2 umbrella hierarchy (#229)
-- Umbrella topics group same-EVENT cross-country children (centroid-of-centroids,
-- Pedro's embedding-of-embeddings). An umbrella IS a dynamic_topics row (one topic
-- model, on-thesis) with is_umbrella=true; its children point up via parent_id.
--   * global serving  = top level (parent_id IS NULL) — collapses cross-country dups
--   * drill / country = the children (per-country/regional sub-threads)
-- Reversible: set parent_id=NULL + is_umbrella=false to flatten back to R1.
-- Never deletes: umbrella-ing only re-parents rows (retention/resurrection intact).

ALTER TABLE dynamic_topics
  ADD COLUMN IF NOT EXISTS parent_id BIGINT REFERENCES dynamic_topics(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS is_umbrella BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_dynamic_topics_parent
  ON dynamic_topics(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_dynamic_topics_umbrella
  ON dynamic_topics(is_umbrella) WHERE is_umbrella = true;
