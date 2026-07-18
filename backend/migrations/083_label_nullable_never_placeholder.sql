-- 083: labels may be NULL; placeholder strings must never persist (Lane A).
--
-- "(label failed)" (a DeepSeek-error sentinel from emergent_poc._label_one)
-- was persisted verbatim into emergent_clusters.label and, via the
-- mode-label in project_dynamic_topics, into dynamic_topics.label — then
-- served on the front page. The NOT NULL constraints forced writers to
-- invent placeholder strings on labeler failure.
--
-- New rule (scripts/label_hygiene.py): on labeler failure persist NULL or
-- keep the previous label. The serving guard
-- (thread_intelligence.clean_thread_label) renders a receipt-derived
-- fallback for NULL/placeholder labels, so a NULL label is always
-- displayable.
--
-- Reversible: re-add NOT NULL only after backfilling
--   UPDATE dynamic_topics SET label = 'dynamic topic ' || id WHERE label IS NULL;
--   UPDATE emergent_clusters SET label = '(no label)' WHERE label IS NULL;

ALTER TABLE dynamic_topics ALTER COLUMN label DROP NOT NULL;
ALTER TABLE emergent_clusters ALTER COLUMN label DROP NOT NULL;
