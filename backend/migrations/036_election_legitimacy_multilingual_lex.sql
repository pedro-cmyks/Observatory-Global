-- Migration 036: pilot of AI taxonomy Path A (multilingual lex expansion)
-- for atlas_topic `election-legitimacy-dispute`.
--
-- Spec: docs/specs/2026-05-23-ai-assisted-taxonomy.md
-- Tracking: GitHub issue #202 (Path A) — multilingual lex via LLM.
--
-- Context: post mig 035+035b, election-legitimacy-dispute had 1502 sigs/24h
-- with only 6.3% lex-supported (most matched via theme-only — POLITICAL
-- + GOVERNMENT type hints). 64% of unclassified atlas signals are in `xx`
-- language; the original 5 English-only lex terms ("election fraud",
-- "contested election", "vote count", "electoral court", "ballot") missed
-- nearly every Spanish/Italian/Portuguese/French/German/Turkish/Greek
-- election headline.
--
-- Methodology (pilot for issue #202):
-- 1. Pulled 25 high-confidence v2 assignments (positives) and 30
--    theme-only assignments (false-positive candidates) via Supabase MCP.
-- 2. Reading those headlines, Claude proposed 39 candidate multilingual
--    substring matchers.
-- 3. Each candidate verified against 24h signals_v2 via LIKE — counted
--    hit volume + sampled 4 random matches per heavy hitter to confirm
--    precision.
-- 4. Rejected:
--      - "scrutin" (FR) — matched "scrutiny", "escrutinável" etc. (~25%
--        precision on sample).
--    Accepted: the other 38.
--
-- Term inventory:
--   Existing (5 EN):  election fraud, contested election, vote count,
--                     electoral court, ballot.
--   New EN (8):       election integrity, vote recount, presidential
--                     primary, election interference, election denial,
--                     polls closed, voter suppression, electoral college.
--   New ES (9):       elecciones, comicios, urnas, papeleta,
--                     fraude electoral, tribunal electoral,
--                     campaña electoral, dimisión presidente,
--                     renuncia presidente.
--   New IT (3):       elezioni, frode elettorale, brogli elettorali.
--   New PT (5):       eleição, eleições, fraude eleitoral,
--                     tribunal eleitoral, urnas eleitorais.
--   New FR (4):       élections, élection, fraude électorale,
--                     bureau de vote.
--   New DE (4):       wahlbetrug, wahlmanipulation, bundestagswahl,
--                     stimmabgabe.
--   New TR (3):       seçim iptal, yerel seçim, cumhurbaşkanlığı seçim.
--   New EL (2):       εκλογές, εκλογικ.
--
-- Total: 5 -> 43 terms.
--
-- Expected impact: heavy hitters by 24h volume — elecciones (157),
-- elezioni (101), presidential primary (68), comicios (12), urnas (9).
-- Should lift this topic's lex_pct from 6.3% toward 30%+ and raise
-- election-legitimacy from #5 in top_atlas_topics into a more accurate
-- slot once the multilingual headlines stop being theme-only.
--
-- After applying: delete election-legitimacy assignments + re-backfill
-- 24h. The 30-min cron handles incremental traffic going forward.
--
-- If this pilot clears the gate (lex_pct >= 30%, no precision regression
-- in spot check), apply Path A methodology to the remaining low-lex_pct
-- topics: armed-conflict-escalation (2.2%), fuel-subsidy-unrest (10.4%),
-- mining-royalty-risk (12.5%), housing-cost-pressure (13.6%),
-- food-price-stress (19.0%).

UPDATE atlas_topics SET
    lexicon_terms = ARRAY[
        -- Existing English
        'election fraud','contested election','vote count','electoral court','ballot',
        -- New English
        'election integrity','vote recount','presidential primary','election interference',
        'election denial','polls closed','voter suppression','electoral college',
        -- Spanish
        'elecciones','comicios','urnas','papeleta','fraude electoral',
        'tribunal electoral','campaña electoral','dimisión presidente','renuncia presidente',
        -- Italian
        'elezioni','frode elettorale','brogli elettorali',
        -- Portuguese
        'eleição','eleições','fraude eleitoral','tribunal eleitoral','urnas eleitorais',
        -- French
        'élections','élection','fraude électorale','bureau de vote',
        -- German
        'wahlbetrug','wahlmanipulation','bundestagswahl','stimmabgabe',
        -- Turkish
        'seçim iptal','yerel seçim','cumhurbaşkanlığı seçim',
        -- Greek
        'εκλογές','εκλογικ'
    ]
WHERE slug='election-legitimacy-dispute';
