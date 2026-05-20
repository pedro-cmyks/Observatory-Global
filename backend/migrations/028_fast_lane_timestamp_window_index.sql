-- Migration 028: align fast-lane index with the product SLA window.
--
-- The hot-window SLA is measured on source/event timestamp, not created_at.
-- Fast-lane enrichment must select the same window or rows with recent source
-- timestamps but older created_at remain provenance-only.

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_fast_lane_pending_timestamp
    ON signals_v2 (timestamp DESC)
    WHERE nlp_method IS NULL;
