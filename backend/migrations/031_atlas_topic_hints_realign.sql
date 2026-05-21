-- Migration 031: realign atlas_topics.gdelt_theme_hints with real GDELT codes
-- Applied via Supabase MCP on 2026-05-21.
--
-- Context: audit showed 50% of last-24h signals matched no atlas_topic via
-- the original gdelt_theme_hints, because the hints used short codes like
-- TRANSPORT, ENERGY, SANCTION that don't exist in real GDELT GKG output.
-- GDELT uses prefixed taxonomy (WB_*, TAX_*, CRISISLEX_*, UNGP_*, EPU_*).
--
-- This migration expands theme_hints with the actual codes observed in
-- signals_v2 last 24h. After applying:
--   - theme-level coverage jumps 50.02% -> 84.21%
--   - 4 previously-zero topics (transport, oil-gas, sanctions, trade-export)
--     now match real signals.
--
-- Tradeoff: theme-only matching remains noisy (single GDELT theme is not
-- a discriminative signal). The accompanying classifier
-- (scripts/classify_topics.py, signal_topic_assignments.method=
-- 'theme_lexicon_v1') requires either a lexicon term hit on headline or
-- >=3 theme hint matches to assign a topic, which keeps precision high
-- (~65% in spot checks) at the cost of recall (~2.5% of 24h volume).

UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ARMEDCONFLICT','MILITARY','KILL','WB_2432_FRAGILITY_CONFLICT_AND_VIOLENCE','CRISISLEX_C03_DEAD_WOUNDED'] WHERE slug='armed-conflict-escalation';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['DISASTER_RESPONSE','REFUGEES','CRISISLEX_C03_DEAD_WOUNDED','CRISISLEX_CRISISLEXREC'] WHERE slug='humanitarian-access-conflict';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['CRIME','TAX_TERROR','ARREST','SOC_GENERALCRIME'] WHERE slug='gang-control-urban-security';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ELECTION','GOVERNMENT','PROTEST','EPU_POLICY_POLITICAL','GENERAL_GOVERNMENT'] WHERE slug='election-legitimacy-dispute';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['GOVERNMENT','COURT','LEADER','WB_840_JUSTICE','EPU_POLICY_GOVERNMENT','GENERAL_GOVERNMENT'] WHERE slug='constitutional-institutional-crisis';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['CORRUPTION','INVESTIGATION','COURT','WB_840_JUSTICE'] WHERE slug='corruption-investigation';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ECON_INFLATION','PROTEST','STRIKE','TAX_ECON_PRICE'] WHERE slug='fuel-subsidy-unrest';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ECON_INFLATION','FOOD_SECURITY','HEALTH','TAX_ECON_PRICE','WB_695_POVERTY'] WHERE slug='food-price-stress';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ECON_BANKRUPTCY','ECON_INFLATION','ECON_STOCKMARKET','EPU_ECONOMY_HISTORIC','TAX_ECON_PRICE'] WHERE slug='currency-debt-stress';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ECON_TRADE','TAX_FNCACT','ENV_MINING','WB_507_ENERGY_AND_EXTRACTIVES'] WHERE slug='mining-royalty-risk';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ENERGY','INFRASTRUCTURE','ENV_CLIMATECHANGE','WB_507_ENERGY_AND_EXTRACTIVES'] WHERE slug='energy-grid-instability';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ENERGY','ECON_TRADE','SANCTION','WB_507_ENERGY_AND_EXTRACTIVES','MARITIME'] WHERE slug='oil-gas-supply-risk';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ENV_CLIMATECHANGE','UNGP_DISASTER','WATER_SECURITY','UNGP_FORESTS_RIVERS_OCEANS'] WHERE slug='water-stress-drought';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['UNGP_DISASTER','DISASTER_RESPONSE','ENV_CLIMATECHANGE','MANMADE_DISASTER_IMPLIED','UNGP_FORESTS_RIVERS_OCEANS'] WHERE slug='flood-landslide-disaster';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['HEALTH','ENV_CLIMATECHANGE','UNGP_DISASTER','WB_621_HEALTH_NUTRITION_AND_POPULATION','MEDICAL'] WHERE slug='heat-health-risk';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['HEALTH','MEDICAL','CRISISLEX_C07_SAFETY','WB_621_HEALTH_NUTRITION_AND_POPULATION'] WHERE slug='disease-outbreak';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['MIGRATION','REFUGEES','HUMAN_RIGHTS','EPU_CATS_MIGRATION_FEAR_FEAR'] WHERE slug='migration-border-pressure';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['REFUGEES','HUMAN_RIGHTS','ARMEDCONFLICT','EPU_CATS_MIGRATION_FEAR_FEAR'] WHERE slug='forced-displacement';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['LABOR','STRIKE','PROTEST','WB_2670_JOBS','WB_724_HUMAN_RESOURCES_FOR_PUBLIC_SECTOR'] WHERE slug='labor-strike-disruption';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['PROTEST','EDUCATION','SOC_POINTSOFVIEW','WB_470_EDUCATION'] WHERE slug='student-youth-protest';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['HUMAN_RIGHTS','KILL','PROTEST','SOC_GENERALCRIME'] WHERE slug='gender-violence-rights';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['TRANSPORT','INFRASTRUCTURE','ECON_TRADE','WB_135_TRANSPORT','MARITIME'] WHERE slug='transport-corridor-disruption';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['CYBER_ATTACK','TECHNOLOGY','INFRASTRUCTURE','WB_133_INFORMATION_AND_COMMUNICATION_TECHNOLOGIES'] WHERE slug='cyberattack-infrastructure';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['TECHNOLOGY','MEDIA_CENSORSHIP','HUMAN_RIGHTS','WB_133_INFORMATION_AND_COMMUNICATION_TECHNOLOGIES','WB_678_DIGITAL_GOVERNMENT'] WHERE slug='telecom-internet-shutdown';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['MEDIA_MSM','SOC_POINTSOFVIEW','TAX_FNCACT','MEDIA_SOCIAL','WB_694_BROADCAST_AND_MEDIA'] WHERE slug='disinformation-influence-operation';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['MEDIA_CENSORSHIP','HUMAN_RIGHTS','ARREST','WB_694_BROADCAST_AND_MEDIA'] WHERE slug='press-freedom-crackdown';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['SANCTION','TAX_DIPLOMACY','TREATY','EPU_POLICY_POLITICAL'] WHERE slug='sanctions-diplomatic-pressure';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ECON_TRADE','SANCTION','TAX_DIPLOMACY','ECON_TAXATION'] WHERE slug='trade-export-restriction';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['ECON_INFLATION','SOC_ECONCOSTOFLIVING','PROTEST','TAX_ECON_PRICE','WB_695_POVERTY'] WHERE slug='housing-cost-pressure';
UPDATE atlas_topics SET gdelt_theme_hints = ARRAY['AGRICULTURE','FOOD_SECURITY','ENV_CLIMATECHANGE'] WHERE slug='agriculture-crop-risk';
