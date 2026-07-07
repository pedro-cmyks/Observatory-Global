-- Migration 073: AI cost ledger (2026-07-07).
--
-- We log the LLM PROVIDER on every call but never the token counts or dollars,
-- so per-interaction AI cost is a guess. This table is the measured answer:
-- one fire-and-forget row per real (non-cached) model call, tagged by SURFACE
-- (brief / theme-insight / dossier-synthesis / translate / typing /
-- dossier-embed). `backend/scripts/ai_cost_report.py` rolls it up into
-- cost-per-surface, cost-per-interaction and projected $/active-user/month.
--
-- Written best-effort by app/services/ai_cost.py (log_ai_cost) — a write
-- failure must NEVER block or break the user path, same discipline as
-- telemetry_events (mig 056). M1/local NER + clustering are $0 (not logged);
-- only the paid providers (DeepSeek, Anthropic, OpenAI embeddings) land here.
CREATE TABLE IF NOT EXISTS ai_cost_events (
    id            BIGSERIAL PRIMARY KEY,
    surface       TEXT NOT NULL,           -- product surface that triggered the call
    provider      TEXT NOT NULL,           -- deepseek | anthropic | openai
    model         TEXT NOT NULL,
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    usd           NUMERIC(12, 8) NOT NULL DEFAULT 0,  -- estimated cost at log-time prices
    session_id    TEXT,                    -- optional: join to telemetry_events
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_ai_cost_events_created ON ai_cost_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ai_cost_events_surface ON ai_cost_events (surface);
ALTER TABLE ai_cost_events ENABLE ROW LEVEL SECURITY;
