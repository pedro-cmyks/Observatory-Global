-- Migration 072: event-internal FACET on dynamic_topics children (constellation
-- assembly, 2026-07-06 — docs/specs/2026-07-06-connection-layer-constellation-assembly.md).
--
-- An umbrella (is_umbrella=true) collapses ~30 near-duplicate/facet fragments of
-- ONE big story (Venezuela earthquake) under a single parent_id. But the children
-- are not all duplicates — they are typed SUB-FACETS of the event: death-toll,
-- rescues, foreign-victims (by nationality), international-aid, government-response
-- / risk-management, aftermath. `facet` names that event-internal role so L3 can
-- offer the analyst the assembled constellation BY FACET instead of 30 noisy rows.
--
-- NULL for umbrellas and for un-parented standalone topics. Distinct from `category`
-- (the R3 crisis-class lens, e.g. "Earthquake or volcanic disaster") — facet is the
-- narrative angle WITHIN one event, category is the cross-event class.
--
-- Written by backend/scripts/assemble_constellation.py (lexical typer over the
-- child label; reversible: UPDATE dynamic_topics SET facet=NULL).

ALTER TABLE dynamic_topics
  ADD COLUMN IF NOT EXISTS facet TEXT;

CREATE INDEX IF NOT EXISTS idx_dynamic_topics_facet
  ON dynamic_topics(parent_id, facet) WHERE facet IS NOT NULL;
