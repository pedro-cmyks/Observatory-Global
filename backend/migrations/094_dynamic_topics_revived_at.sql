-- 094: TF-3b revival marker (2026-07-31).
-- TF-2 (docs/research/recall-229/2026-07-30-tickv2-tf1-tf2-verdict.md) measured
-- that direct retired->active revival serves 62.5% mislabeled/blob stock.
-- Under tick-v2b a revival lands `candidate` and gets stamped here; promotion
-- to active additionally requires label_status='entailed' (the label court
-- re-certifies the label against the topic's CURRENT receipts — the revival
-- path NULLs the court columns so an old stamp can never carry over).
-- Reversible: the column is inert while ATLAS_LIFECYCLE_TICK_V2 is off.
ALTER TABLE dynamic_topics
    ADD COLUMN IF NOT EXISTS revived_at timestamptz;

COMMENT ON COLUMN dynamic_topics.revived_at IS
    'TF-3b: last time this topic was revived (deprecated/retired -> candidate) '
    'by the v2 lifecycle clock. A revived candidate promotes only once the '
    'label court re-certifies its label (label_status=entailed). NULL = never '
    'revived under the v2b regime.';
