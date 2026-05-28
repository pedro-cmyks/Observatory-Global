-- Migration 044 — gold-guided theme-hint removals.
-- Source: post-043 reclassify analysis over N=61 reviewed gold.
-- Method: for each theme-only false positive (incorrect gold row with no
-- lexicon match), measured which gdelt_theme_hints intersected the signal
-- themes. Removed only theme hints that produced false positives AND
-- supported zero true positives in the gold sample.
--
-- Removals (theme -> FP/TP in gold -> reason):
--   agriculture-crop-risk / 'ENV_CLIMATECHANGE'  (2 FP / 0 TP)
--       Matched generic climate stories ("El Nino climate phenomenon",
--       "restoring mangroves coastal livelihoods") that are environmental
--       but not crop-risk. Crop risk keeps AGRICULTURE + FOOD_SECURITY +
--       lexicon coverage.
--   cyberattack-infrastructure / 'CYBER_ATTACK'  (4 FP / 0 TP)
--       GDELT's CYBER_ATTACK theme tagged scam/fraud/legal/AI-policy
--       headlines (online investment scams, data-breach lawsuit, NEET
--       paper leak, 5G fraud) — none were infrastructure attacks. The
--       confirmed cyberattacks in gold all matched via lexicon
--       ('hackers', 'cyberattack'), not this theme. Precision-first
--       removal: may cost recall on future lexicon-less cyberattacks, an
--       accepted tradeoff per the project precision-over-recall rule.
--
-- NOT removed (each supports true positives in gold):
--   agriculture / FOOD_SECURITY, AGRICULTURE
--   armed-conflict / ARMEDCONFLICT, MILITARY, KILL, TERROR, WB_2432
--   corruption / CORRUPTION, WB_840_JUSTICE
--   currency / ECON_INFLATION, EPU_ECONOMY_HISTORIC
--   cyberattack / WB_133 (supports 1 TP; kept despite 3 FP)

BEGIN;

UPDATE atlas_topics
SET gdelt_theme_hints = array_remove(gdelt_theme_hints, 'ENV_CLIMATECHANGE')
WHERE slug = 'agriculture-crop-risk';

UPDATE atlas_topics
SET gdelt_theme_hints = array_remove(gdelt_theme_hints, 'CYBER_ATTACK')
WHERE slug = 'cyberattack-infrastructure';

COMMIT;
