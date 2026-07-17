-- 079_nlp_persons_backlog_index.sql
--
-- #184 ops (2026-07-16): the NLP fleet's backlog_pool lane in
-- enrichment/nlp_pipeline.py `_priority_select_sql` (created_at between
-- now()-15d and now()-24h, {target} IS NULL, ORDER BY created_at DESC
-- LIMIT 5000) timed out at the ~120s statement timeout under DataFileRead
-- IO pressure. Commit f8525b16 made the fleet degrade to hot-lane-only, so
-- it survives — but >24h-old rows never drain while pressure persists.
--
-- Measured selectivity over the 15-day window (906,630 rows, 2026-07-16):
--   nlp_persons     IS NULL: 168,786  (18.6%)  <- sparse, and the nulls sit
--                                                 DEEP in the window: the
--                                                 plain created_at DESC scan
--                                                 filtered 620,812 rows to
--                                                 find 5,000 (193.7s measured)
--   nlp_processed_at IS NULL: 737,030 (81.3%)  <- dense; plain index scan
--                                                 finds matches immediately
--   nlp_framing     IS NULL: 860,096  (94.9%)  <- dense; same
--
-- So ONLY the nlp_persons lane needs a partial index; per-column indexes on
-- nlp_processed_at / nlp_framing would be near-full-table copies (bloat on a
-- high-churn table) for no gain — and nlp_processed_at already has two
-- (idx_signals_v2_nlp_unprocessed_recent et al).
--
-- The index is self-limiting in size: when NER populates nlp_persons the new
-- row version leaves the predicate, so the index tracks the live backlog
-- (~170K rows now, shrinking as the backlog drains).
--
-- Measured effect: backlog_pool CTE 193.7s -> ~milliseconds (index-only
-- ordered scan over predicate-matching rows).
--
-- NOTE: applied to production 2026-07-16 via psql with CONCURRENTLY (cannot
-- run inside a transaction block — run the two statements separately, e.g.
-- `psql -c "SET statement_timeout='0'" -c "CREATE INDEX CONCURRENTLY ..."`).
-- The non-CONCURRENT form below is the Supabase-SQL-editor-safe idempotent
-- record; it no-ops when the index already exists.

CREATE INDEX IF NOT EXISTS idx_signals_v2_nlp_persons_pending
    ON signals_v2 (created_at DESC)
    WHERE nlp_persons IS NULL AND headline IS NOT NULL;
