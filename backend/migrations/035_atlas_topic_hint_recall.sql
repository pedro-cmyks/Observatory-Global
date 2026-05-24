-- Migration 035: extend gdelt_theme_hints for 4 topics with GDELT codes that
-- appear frequently in signals_v2 but were not in any atlas_topic. Targets the
-- recall gap exposed by the 2026-05-23 audit: only 10.7% of 24h-eligible
-- signals were classified by v2 — 87% of unclassified signals had themes the
-- classifier just wasn't looking for.
--
-- Sampling methodology (all confirmed >=75% precision on 24h headlines):
--
--   hint                                volume/24h    precision check
--   TERROR                              3,899         4/4 real conflict
--                                                     (Nigeria troops kill
--                                                     12 terrorists,
--                                                     Lebanon strike,
--                                                     Pulwama mastermind,
--                                                     White House attack)
--   WB_2473_DIPLOMACY_AND_NEGOTIATIONS  982           4/4 real diplomacy
--                                                     (Pakistan-Iran talks,
--                                                     Macron-Trump-Gulf,
--                                                     Israel-Hamas, Trump-
--                                                     Iran deal)
--   EVACUATION                          574           3/4 real evac (CA
--                                                     fire 40k people,
--                                                     Sweden 40k, NSW Navy)
--   WB_2663_EBOLA                       967          10/10 Ebola outbreak
--   TAX_DISEASE_EBOLA                   715           same Ebola cluster
--   TAX_DISEASE_DISEASE                 2,001         general disease (paired
--                                                     with disease lex)
--
-- Also for disease-outbreak: drop MEDICAL — same broad-hint problem that mig
-- 034 fixed for heat-health-risk (MEDICAL matches any medical headline).
--
-- Candidates REJECTED for poor precision in sample:
--   CRISISLEX_T02_INJURED (12,091)              — accidents + animal attacks
--                                                  mixed with conflict.
--   WB_2462_POLITICAL_VIOLENCE_AND_WAR (1,012)  — 50% precision.
--   WB_2495_DETENTION_PRISON          (1,041)  — broad detention noise.
--   CRISISLEX_C06_WATER_SANITATION   (673)     — Bursa butchery, NSW storage.
--   SCANDAL                          (970)     — meta-news + Shell humor.
--   WB_2507_HUMAN_RIGHTS_ABUSES      (538)     — novel rankings + random.
--
-- After applying, re-backfill the 4 affected topics so the new hints take
-- effect immediately (the 30-min cron would catch up but a backfill aligns
-- the test bed).

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY[
        'ARMEDCONFLICT','MILITARY','KILL',
        'WB_2432_FRAGILITY_CONFLICT_AND_VIOLENCE','CRISISLEX_C03_DEAD_WOUNDED',
        'TERROR'
    ]
WHERE slug='armed-conflict-escalation';

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY[
        'SANCTION','TAX_DIPLOMACY','TREATY','EPU_POLICY_POLITICAL',
        'WB_2473_DIPLOMACY_AND_NEGOTIATIONS'
    ]
WHERE slug='sanctions-diplomatic-pressure';

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY[
        'REFUGEES','HUMAN_RIGHTS','ARMEDCONFLICT','EPU_CATS_MIGRATION_FEAR_FEAR',
        'EVACUATION'
    ]
WHERE slug='forced-displacement';

-- disease-outbreak: drop MEDICAL (matches any medical headline), keep HEALTH,
-- WB_621, CRISISLEX_C07_SAFETY (paired with disease lex they discriminate
-- well enough), add the Ebola-specific codes that the live Uganda outbreak
-- is currently triggering on a daily basis.
UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY[
        'HEALTH','CRISISLEX_C07_SAFETY','WB_621_HEALTH_NUTRITION_AND_POPULATION',
        'WB_2663_EBOLA','TAX_DISEASE_EBOLA','TAX_DISEASE_DISEASE'
    ]
WHERE slug='disease-outbreak';
