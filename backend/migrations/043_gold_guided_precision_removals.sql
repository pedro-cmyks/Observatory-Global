-- Migration 043 — gold-guided precision removals.
-- Source: docs/research/atlas-paper/phase-1-validation/reports/migration-042/post-042-reclassify.json
-- Method: inspected the 25 incorrect reviewed-gold rows, identified lexicon
-- terms that matched ONLY false positives and zero confirmed true positives
-- in the gold sample. Each removal below is verified non-destructive to the
-- correct cases in the N=61 reviewed gold.
--
-- Removals (term -> reason):
--   constitutional-institutional-crisis / 'state of emergency'
--       FP on "California chemical tank cracked causing state of emergency"
--       (industrial disaster, not constitutional). No correct gold case
--       depends on this term; correct cases use impeachment/impeach/ousted/
--       supreme court.
--   cyberattack-infrastructure / 'data breach'
--       FP on "Krispy Kreme data breach lawsuit settlement" (legal/settlement,
--       not an infrastructure attack). Correct cases use hackers/cyberattack.
--   cyberattack-infrastructure / 'critical infrastructure'
--       FP on "Africa's AI ambitions face critical infrastructure questions"
--       (policy/investment, not an attack). Correct cases use hackers/cyberattack.
--
-- NOT removed despite FP appearance (would cost true positives or recall):
--   currency-debt-stress / 'peso'  -> supports 1 correct case as well.
--   currency-debt-stress / 'lira'  -> substring noise ("aliran") is a
--       word-boundary matching defect, not a term-quality defect; keep the
--       term and fix matching separately.
--   armed-conflict-escalation / 'armed conflict','rebels' -> core terms;
--       the FPs are scope mismatches (real conflict mentioned as context),
--       not term noise. Fixing requires the multi-layer scope classifier.
--   constitutional / 'impeachment','impeach' -> core terms; FP was an
--       endorsement headline (scope mismatch), not term noise.

BEGIN;

UPDATE atlas_topics
SET lexicon_terms = array_remove(lexicon_terms, 'state of emergency')
WHERE slug = 'constitutional-institutional-crisis';

UPDATE atlas_topics
SET lexicon_terms = array_remove(lexicon_terms, 'data breach')
WHERE slug = 'cyberattack-infrastructure';

UPDATE atlas_topics
SET lexicon_terms = array_remove(lexicon_terms, 'critical infrastructure')
WHERE slug = 'cyberattack-infrastructure';

COMMIT;
