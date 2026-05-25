-- Migration 039: Path C first-pass taxonomy correction for mining/resource risk.
--
-- Path A showed that `mining-royalty-risk` now captures a coherent,
-- high-confidence mining disaster / resource safety cluster. The previous
-- label over-promised royalty/concession risk even when the evidence was a
-- coal mine explosion and safety-accountability coverage.
--
-- Keep the slug stable for API/historical compatibility. Update the
-- human-facing anchor fields first; split royalty/concession into a separate
-- anchor only after benchmark labels show independent volume.

UPDATE atlas_topics
SET
    label = 'Mining and resource safety crisis',
    description = 'Mine accidents, extraction-site safety failures, illegal mining, resource-disaster events, and related regulatory or accountability fallout.',
    updated_at = NOW()
WHERE slug = 'mining-royalty-risk';
