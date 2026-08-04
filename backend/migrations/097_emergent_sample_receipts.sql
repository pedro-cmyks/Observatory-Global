-- 097: retention-proof receipt snapshots (2026-08-04).
-- Root cause (gold day-5 GQ-08/GQ-12, fix e55cb08e made it HONEST, this makes
-- it DURABLE): the 7-day signals_v2 hot retention deletes rows that
-- emergent_clusters.sample_signal_ids still references, so an aged story's
-- receipt lane decays to 1-2 live rows while agg_n_signals (a persisted
-- integer) still advertises the full membership — dt-8057 served 41/1.
--
-- sample_receipts freezes the receipt CONTENT at snapshot-write time, from
-- the in-memory signal data the clustering pass already holds (no extra
-- queries): a jsonb array of
--   {id, h (headline), u (source_url), src (source_name), cc, ts}
-- capped at the same SAMPLE_TOP_K as sample_signal_ids. The id keys let the
-- serving layer prefer LIVE signals_v2 rows while they exist and fall back to
-- the frozen receipt — visibly marked archived — only for ids retention has
-- deleted. NULL = written before this migration (or the backfill found no
-- live rows to freeze); '[]' = processed, nothing recoverable.
-- Reversible: column is additive and inert until writer + serving ship.
ALTER TABLE emergent_clusters
    ADD COLUMN IF NOT EXISTS sample_receipts jsonb;

COMMENT ON COLUMN emergent_clusters.sample_receipts IS
    'Retention-proof frozen receipt snapshots [{id,h,u,src,cc,ts}] captured '
    'at snapshot-write time from in-memory signal data (capped at the sample '
    'size). The id keys allow serving to prefer live signals_v2 rows when '
    'they still exist; entries whose live row retention has deleted serve as '
    'visibly-archived receipts. NULL = pre-097 row with no backfill; [] = '
    'processed, nothing recoverable.';
