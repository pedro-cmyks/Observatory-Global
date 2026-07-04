-- 067: prune junk GDELT theme hints (2026-07-04).
--
-- The theme-hint-lex-v2 assigner qualifies on lex_count>=1 OR theme_hits>=1,
-- so one ultra-generic GDELT theme assigns a signal to a crisis topic. Measured
-- over 48h of hint-only (lex_count=0) assignments, per (topic, hint) gate
-- keep-rate: several hints contribute ~ZERO verified signal while inflating the
-- topic's raw denominator (the election-legitimacy "1 of 1,269" eval case:
-- ELECTION 858 rows / 0.2% kept, GENERAL_GOVERNMENT 679 / 0.3%,
-- EPU_POLICY_POLITICAL 410 / 0.0%, PROTEST 217 / 0.0%).
--
-- PR3-05 (2026-07-01 staleness ledger) already measured theme-hints as NET
-- NOISE and cleared removal (REMOVE-OK; spec §4.1 gate SATISFIED). This is the
-- surgical per-topic application: prune (topic, hint) pairs with keep-rate
-- < 2% at n >= 40; KEEP hints that carry real signal (ARMEDCONFLICT 15.2%,
-- CORRUPTION 77%, housing/gang hints, non-English coverage enters via these).
--
-- Reversible: previous arrays recorded below.
--   election-legitimacy-dispute: {ELECTION,GOVERNMENT,PROTEST,EPU_POLICY_POLITICAL,GENERAL_GOVERNMENT}
--   fuel-subsidy-unrest:         had ECON_INFLATION,PROTEST,STRIKE,TAX_ECON_PRICE (+ any others untouched)
--   currency-debt-stress:        had EPU_ECONOMY_HISTORIC,ECON_INFLATION among hints
--   oil-gas-supply-risk:         had MARITIME,WB_507_ENERGY_AND_EXTRACTIVES among hints
--   flood-landslide-disaster:    had MANMADE_DISASTER_IMPLIED among hints

-- election-legitimacy-dispute: all measured hints are junk -> empty the list
-- (GOVERNMENT was in the list but never intersected; ELECTION/GENERAL_GOVERNMENT/
-- EPU_POLICY_POLITICAL/PROTEST all measured < 0.3% keep). Lexicon carries it.
UPDATE atlas_topics SET gdelt_theme_hints = '{}'
WHERE slug = 'election-legitimacy-dispute';

UPDATE atlas_topics SET gdelt_theme_hints = (
  SELECT COALESCE(array_agg(h), '{}') FROM unnest(gdelt_theme_hints) h
  WHERE h NOT IN ('ECON_INFLATION','PROTEST','STRIKE','TAX_ECON_PRICE')
) WHERE slug = 'fuel-subsidy-unrest';

UPDATE atlas_topics SET gdelt_theme_hints = (
  SELECT COALESCE(array_agg(h), '{}') FROM unnest(gdelt_theme_hints) h
  WHERE h NOT IN ('EPU_ECONOMY_HISTORIC','ECON_INFLATION')
) WHERE slug = 'currency-debt-stress';

UPDATE atlas_topics SET gdelt_theme_hints = (
  SELECT COALESCE(array_agg(h), '{}') FROM unnest(gdelt_theme_hints) h
  WHERE h NOT IN ('MARITIME','WB_507_ENERGY_AND_EXTRACTIVES')
) WHERE slug = 'oil-gas-supply-risk';

UPDATE atlas_topics SET gdelt_theme_hints = (
  SELECT COALESCE(array_agg(h), '{}') FROM unnest(gdelt_theme_hints) h
  WHERE h NOT IN ('MANMADE_DISASTER_IMPLIED')
) WHERE slug = 'flood-landslide-disaster';

-- Immediate denominator cleanup: drop NOT-gate-kept hint-only assignments that
-- would no longer qualify under the pruned hint lists (they are recomputed
-- every 30 min anyway; gate-kept rows are preserved).
DELETE FROM signal_topic_assignments sta
USING atlas_topics t, signals_v2 s
WHERE t.id = sta.topic_id
  AND s.id = sta.signal_id
  AND sta.model_version = 'theme-hint-lex-v2'
  AND COALESCE(sta.gate_kept, false) = false
  AND (sta.evidence->>'lex_count')::int = 0
  AND NOT (s.themes && t.gdelt_theme_hints)
  AND t.slug IN ('election-legitimacy-dispute','fuel-subsidy-unrest',
                 'currency-debt-stress','oil-gas-supply-risk',
                 'flood-landslide-disaster');
