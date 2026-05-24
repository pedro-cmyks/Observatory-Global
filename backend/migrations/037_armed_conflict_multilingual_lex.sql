-- Migration 037: Path A multilingual lex expansion and precision cleanup
-- for atlas_topic `armed-conflict-escalation`.
--
-- Spec: docs/specs/2026-05-23-ai-assisted-taxonomy.md
-- Tracking: GitHub issue #202 (Path A) — multilingual lex via LLM.
--
-- Context: after migration 036, this was the highest-impact remaining
-- low-lex topic. Live 24h baseline before this migration:
--
--   assignments: 3,338
--   lex-supported: 70
--   high_conf: 22
--   lex_pct: 2.10%
--
-- Methodology:
-- 1. Pulled live 24h topic metrics and current lexicon terms.
-- 2. Sampled lex-supported positives and theme-only assignments.
-- 3. Found a precision issue in the original English terms:
--      - "clashes" matched sports, entertainment, and celebrity production
--        disputes.
--      - "offensive" matched sports lines, offensive comments, and commercial
--        expansions.
--      - "shelling" matched finance headlines such as "shelling out".
-- 4. SQL-counted proposed multilingual candidate terms against 24h
--    signals_v2 headlines.
-- 5. Spot-checked heavy hitters with 5 random headline samples each.
--
-- Accepted examples from samples:
--   EN: airstrike, drone attack, drone strike, missile attack, missile strike,
--       russian strike(s), offensive campaign.
--   ES/PT: bombardeo(s), enfrentamientos, ataque con dron(es),
--          ataque con misiles, ataque de/com drone.
--   DE: drohnenangriff, luftangriff, raketenangriff.
--   FR/TR: low-current-volume but semantically precise future matchers.
--
-- Rejected:
--   - "clashes" — mixed with sports and entertainment.
--   - "offensive" — mixed with sports, content moderation, and marketing.
--   - "shelling" — mixed with "shelling out" financial idiom.
--   - "troops" — military-related but too broad.
--   - "militants" — mixed armed groups with civilian activists.
--   - "misil" — mixed military headlines with vehicle/technology metaphors.
--   - "sicarios" — better owned by gang-control-urban-security.
--   - "battlefield" — mixed current battlefield reporting with historical and
--     metaphorical uses.
--   - "shots fired", "opening fire", "opened fire", "firing at" — mostly one
--     local White House security incident; armed-public-security, not armed
--     conflict escalation.
--   - "ataque armado", "ataques armados" — mostly local crime/public-security
--     incidents; candidate for a future taxonomy split, not this topic.
--
-- Operational follow-up after applying:
--   1. Delete current v2 assignments for armed-conflict-escalation only.
--   2. Re-run backend/scripts/backfill_lexicon_topics.py for 24h.
--   3. Measure lex_pct, high_conf, and spot-check top matched_terms.

UPDATE atlas_topics SET
    lexicon_terms = ARRAY[
        -- Existing precise English terms kept
        'armed conflict',
        'airstrike',
        'militia',
        'rebels',
        -- New precise English terms
        'airstrikes',
        'drone attack',
        'drone attacks',
        'drone strike',
        'drone strikes',
        'missile attack',
        'missile attacks',
        'missile strike',
        'missile strikes',
        'russian strike',
        'russian strikes',
        'enemy shelling',
        'artillery shelling',
        'border clashes',
        'offensive campaign',
        'air raid',
        -- Spanish / Portuguese
        'bombardeo',
        'bombardeos',
        'enfrentamientos',
        'enfrentamiento armado',
        'ataque con dron',
        'ataque con drones',
        'ataque con misiles',
        'ataque de drone',
        'ataque com drone',
        'bombardeio',
        -- French
        'attaque armée',
        'frappe aérienne',
        'frappe aerienne',
        'bombardement',
        'tirs de roquette',
        'drones du hezbollah',
        -- German
        'drohnenangriff',
        'luftangriff',
        'raketenangriff',
        'bewaffneter angriff',
        -- Turkish
        'hava saldırısı',
        'hava saldirisi',
        'füze saldırısı',
        'fuze saldirisi',
        'silahlı saldırı',
        'silahli saldiri',
        'çatışma',
        'catisma'
    ],
    updated_at = NOW()
WHERE slug='armed-conflict-escalation';
