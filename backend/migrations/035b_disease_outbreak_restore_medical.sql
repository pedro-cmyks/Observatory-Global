-- Migration 035b: restore MEDICAL hint on disease-outbreak.
--
-- Mig 035 dropped MEDICAL from disease-outbreak by analogy with mig 034's
-- precision fix on heat-health-risk. That was wrong: MEDICAL on
-- heat-health-risk had ~99% noise (any medical headline), but on
-- disease-outbreak MEDICAL was actually pulling Ebola headlines reliably
-- (live Uganda outbreak generates MEDICAL-tagged stories in many
-- languages where the specific WB_2663_EBOLA code is absent).
--
-- Effect of removing MEDICAL: disease-outbreak v2_sigs dropped 5,246 -> 2,413
-- (54%) and lex-supported assignments fell from ~766 to ~319 — meaning
-- ~447 real lex-supported disease stories were no longer being labeled.
--
-- This migration restores MEDICAL alongside the new specific Ebola hints
-- added by mig 035. After applying + re-backfill: disease-outbreak back
-- to 4,719 sigs with 590 high_confidence assignments (vs 142 before
-- mig 035), confirming the new specific Ebola hints + restored MEDICAL
-- compose well.
--
-- Operational lesson: dropping a broad hint requires per-topic precision
-- measurement, not analogy. MEDICAL is noisy for heat-health-risk because
-- "extreme heat" is rare among medical headlines, but specific for
-- disease-outbreak because most MEDICAL-tagged stories during an active
-- outbreak ARE about that outbreak.

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY[
        'HEALTH','MEDICAL','CRISISLEX_C07_SAFETY',
        'WB_621_HEALTH_NUTRITION_AND_POPULATION',
        'WB_2663_EBOLA','TAX_DISEASE_EBOLA','TAX_DISEASE_DISEASE'
    ]
WHERE slug='disease-outbreak';
