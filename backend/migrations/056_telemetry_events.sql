-- Anonymous product telemetry for time-to-value (master-consolidation T5.1 /
-- founder-review). No PII; session_id is a random client-generated id.
CREATE TABLE IF NOT EXISTS telemetry_events (
    id BIGSERIAL PRIMARY KEY,
    event TEXT NOT NULL,
    session_id TEXT,
    props JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_created ON telemetry_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_events_event ON telemetry_events (event);
ALTER TABLE telemetry_events ENABLE ROW LEVEL SECURITY;
