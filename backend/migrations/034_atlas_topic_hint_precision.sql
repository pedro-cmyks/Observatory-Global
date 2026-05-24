-- Migration 034: prune polluting GDELT theme hints and expand lexicon terms
-- for 7 atlas_topics whose v2 classifier output was contaminated by overly
-- broad single-theme matches.
--
-- Context: after PR #197 (v2 classifier) ran live, per-topic lex_supported
-- audit showed catastrophic false-positive rates:
--   currency-debt-stress              2338 sigs / 0.0% lex   (TAX_ECON_PRICE
--                                                              + ECON_STOCKMARKET
--                                                              matched every
--                                                              equity / commodity
--                                                              price story)
--   telecom-internet-shutdown         4100 sigs / 1.0% lex   (WB_133 + WB_678
--                                                              matched any IT
--                                                              / e-gov article)
--   heat-health-risk                  3584 sigs / 1.1% lex   (MEDICAL +
--                                                              WB_621_HEALTH
--                                                              matched ANY
--                                                              medical headline)
--   press-freedom-crackdown           1452 sigs / 0.3% lex   (WB_694_BROADCAST
--                                                              + ARREST: any
--                                                              media OR any
--                                                              arrest)
--   student-youth-protest             1060 sigs / 0.3% lex   (EDUCATION +
--                                                              WB_470_EDUCATION:
--                                                              any school news)
--   constitutional-institutional-crisis 5522 sigs / 4.7% lex (EPU_POLICY_GOVT
--                                                              + GENERAL_GOVT
--                                                              + LEADER: any
--                                                              government story)
--   disinformation-influence-operation 1988 sigs / 2.8% lex  (WB_694_BROADCAST
--                                                              + MEDIA_MSM:
--                                                              all media)
--   forced-displacement                239 sigs / 0.0% lex   (good hints but
--                                                              zero lex terms
--                                                              fired — lex
--                                                              phrases too
--                                                              specific)
--
-- Strategy:
--   1. Drop the noisiest hint(s) per topic. Keep narrower, topic-specific hints.
--   2. Expand lexicon_terms with natural-language phrases that real headlines
--      actually use (vs the dense legal/financial phrasing of the original lex).
--
-- After applying, downstream cleanup:
--   - DELETE all v2 assignments for the 8 affected topics (the existing rows
--     are based on the OLD hint sets — many are now stale false positives).
--   - Re-run backfill_lexicon_topics.py over 24h with the new hints/lex.
--   - The 30-min cron handles incremental traffic going forward.
--
-- Tradeoff: signal_count per topic drops sharply (esp. for currency-debt-stress
-- and heat-health-risk) but the surviving assignments are precision-bounded.
-- product-grade ranking now reflects actual narratives, not "any government
-- news" or "any medical headline".

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY['ECON_INFLATION','ECON_BANKRUPTCY','EPU_ECONOMY_HISTORIC'],
    lexicon_terms = ARRAY[
        'currency crisis','debt default','imf bailout','foreign reserves','devaluation',
        'peso','lira','naira','rupiah','ruble','hyperinflation','central bank',
        'exchange rate','sovereign debt','default risk','debt restructuring',
        'currency collapse','imf loan'
    ]
WHERE slug='currency-debt-stress';

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY['ENV_CLIMATECHANGE','UNGP_DISASTER','HEALTH'],
    lexicon_terms = ARRAY[
        'heat wave','extreme heat','heatstroke','public health warning','thermal stress',
        'heatwave','scorching','record temperature','heat dome','heat advisory',
        'heat alert','dehydration','sunstroke','heatwave deaths','sweltering'
    ]
WHERE slug='heat-health-risk';

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY['MEDIA_CENSORSHIP','HUMAN_RIGHTS','TECHNOLOGY'],
    lexicon_terms = ARRAY[
        'internet shutdown','telecom outage','network disruption','censorship','connectivity',
        'blackout','internet blackout','mobile shutdown','sim card','vpn',
        'undersea cable','fiber cut','signal jam','disconnected','dark internet',
        'throttled internet','social media block'
    ]
WHERE slug='telecom-internet-shutdown';

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY['MEDIA_CENSORSHIP','HUMAN_RIGHTS'],
    lexicon_terms = ARRAY[
        'journalist arrested','press freedom','media censorship','newsroom raid','reporter detained',
        'journalist killed','journalist jailed','gag order','media crackdown',
        'reporter killed','newspaper banned','broadcaster shut','rsf report',
        'editor jailed','correspondent detained'
    ]
WHERE slug='press-freedom-crackdown';

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY['PROTEST','SOC_POINTSOFVIEW'],
    lexicon_terms = ARRAY[
        'student protest','campus protest','youth movement','tuition protest',
        'students rally','students march','school strike','university protest',
        'campus occupation','walkout','youth uprising','education protest',
        'tuition hike protest','students clash','student union'
    ]
WHERE slug='student-youth-protest';

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY['SOC_POINTSOFVIEW','TAX_FNCACT','MEDIA_SOCIAL'],
    lexicon_terms = ARRAY[
        'disinformation','propaganda','influence operation','fake news','bot network',
        'deepfake','troll farm','astroturf','election interference','foreign influence',
        'coordinated inauthentic','hoax','conspiracy theory','debunked','fact-check',
        'misinformation','manipulated content'
    ]
WHERE slug='disinformation-influence-operation';

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY['GOVERNMENT','COURT','WB_840_JUSTICE'],
    lexicon_terms = ARRAY[
        'constitutional crisis','supreme court','impeachment','state of emergency','parliament dissolved',
        'coup attempt','martial law','presidential decree','court ruling overturned','ousted',
        'congress dissolved','judicial review','autocratic','dictator',
        'unconstitutional','impeach','suspended constitution','dissolves parliament'
    ]
WHERE slug='constitutional-institutional-crisis';

UPDATE atlas_topics SET
    gdelt_theme_hints = ARRAY['REFUGEES','HUMAN_RIGHTS','ARMEDCONFLICT','EPU_CATS_MIGRATION_FEAR_FEAR'],
    lexicon_terms = ARRAY[
        'internally displaced','forced displacement','evacuated families','displacement camp',
        'displaced','refugees fleeing','evacuated','fled fighting','displacement crisis',
        'migrants stranded','asylum seekers','refugee camp','idp camp',
        'humanitarian corridor','exodus','displaced persons','refugees flee'
    ]
WHERE slug='forced-displacement';
