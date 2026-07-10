-- A0 — the honest 3-way split (roadmap v2 Phase 0.4).
-- Every 24h signal ends in ONE labeled bucket:
--   useful-story / junk-typed / unassigned (→ split: syndication-dup vs junk-headline vs real-unclustered)
-- Run when the engine chain is FRESH (assigned_at within the last few hours) and
-- the DB is quiet (no embed/cluster job running — P1 mutex discipline).
-- Usage: psql "$DATABASE_URL" -f backend/scripts/a0_coverage_split.sql

SET statement_timeout = '300s';

-- 1. Denominators
SELECT 'raw_24h' AS metric, count(*) AS n
FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '24 hours'
UNION ALL
SELECT 'substantive (headline>=20)', count(*)
FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '24 hours'
  AND headline IS NOT NULL AND length(headline) >= 20;

-- 2. Assigned split (useful vs junk threads)
WITH sig AS (
  SELECT id FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '24 hours'
),
a AS (
  SELECT tm.signal_id,
         bool_or(dt.state='active' AND dt.is_junk IS NOT TRUE) AS useful,
         bool_or(dt.is_junk IS TRUE) AS junk
  FROM topic_members tm
  JOIN dynamic_topics dt ON ('dynamic-topic-'||dt.id) = tm.topic_id
  WHERE tm.role='evidence' AND tm.assigned_at > NOW() - INTERVAL '30 hours'
  GROUP BY tm.signal_id
)
SELECT 'in_useful_thread' AS bucket, count(*) FROM a JOIN sig ON sig.id=a.signal_id WHERE useful
UNION ALL
SELECT 'in_junk_thread_only', count(*) FROM a JOIN sig ON sig.id=a.signal_id WHERE junk AND NOT useful;

-- 3. Unassigned split (sampled if the full pass is too heavy):
--   (a) syndication-dup: headline identical to a signal that IS in a useful thread
--   (b) junk-headline: the is_junk_headline heuristic class (approximate here by
--       length/pattern; the python probe gives the precise number)
--   (c) real-unclustered: the remainder = the true recall gap
WITH sig AS (
  SELECT s.id, s.headline FROM signals_v2 s
  WHERE s.timestamp > NOW() - INTERVAL '24 hours'
    AND s.headline IS NOT NULL AND length(s.headline) >= 20
),
assigned AS (
  SELECT DISTINCT tm.signal_id FROM topic_members tm
  WHERE tm.role='evidence' AND tm.assigned_at > NOW() - INTERVAL '30 hours'
),
covered_headlines AS (
  SELECT DISTINCT s2.headline
  FROM topic_members tm
  JOIN dynamic_topics dt ON ('dynamic-topic-'||dt.id) = tm.topic_id
  JOIN signals_v2 s2 ON s2.id = tm.signal_id
  WHERE tm.role='evidence' AND tm.assigned_at > NOW() - INTERVAL '30 hours'
    AND dt.state='active' AND dt.is_junk IS NOT TRUE
),
un AS (
  SELECT sig.id, sig.headline FROM sig
  LEFT JOIN assigned a ON a.signal_id = sig.id
  WHERE a.signal_id IS NULL
)
SELECT 'unassigned_total' AS bucket, count(*) FROM un
UNION ALL
SELECT 'unassigned_but_headline_covered (syndication-dup)', count(*)
FROM un WHERE headline IN (SELECT headline FROM covered_headlines);

-- The remainder (unassigned - dup) splits into junk-headline vs real-unclustered
-- via the python junk heuristic: sample 500 of `un`, run
-- research_semantic.is_junk_headline + the topic_junk category probe, report %.
