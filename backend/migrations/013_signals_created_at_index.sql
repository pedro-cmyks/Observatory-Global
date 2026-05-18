-- Index operational insert-time freshness checks used by /health.
-- Source timestamps can be in the future, so health must query created_at instead.
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_signals_v2_created_at
    ON signals_v2 (created_at DESC);
