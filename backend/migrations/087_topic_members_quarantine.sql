-- M2 black-hole prune (#224 heir) — reversible member quarantine.
-- Below-floor evidence members (per-centroid adaptive floor, the 2026-07-03
-- method) are DEMOTED, never deleted: `quarantined=true` + reason + stamp.
-- Serving evidence readers exclude quarantined rows, so gated counts
-- recompute honestly.
--
-- Why a column and not a role value: the topic_members PK is
-- (signal_id, topic_id, role, engine_version) and `etl_topic_members.py`
-- re-projects with ON CONFLICT DO NOTHING — flipping role would let the next
-- ETL pass silently re-insert the evidence row (prune undone + duplicate),
-- while a flag on the EXISTING row survives re-projection by construction.
-- (`build_unified_topics.py` DELETEs + rebuilds engine_version='unified-v2'
-- nightly, so flags are only durable on the v1-compat lane — the serving
-- default. The prune script scopes accordingly.)
--
-- Additive + reversible.
-- Reversal (data):   UPDATE topic_members SET quarantined=false,
--                    quarantine_reason=NULL, quarantined_at=NULL
--                    WHERE quarantine_reason LIKE 'blackhole-floor-v1%';
-- Rollback (schema): DROP INDEX IF EXISTS idx_topic_members_quarantined;
--                    ALTER TABLE topic_members
--                      DROP COLUMN IF EXISTS quarantined,
--                      DROP COLUMN IF EXISTS quarantine_reason,
--                      DROP COLUMN IF EXISTS quarantined_at;

ALTER TABLE topic_members
    ADD COLUMN IF NOT EXISTS quarantined BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS quarantine_reason TEXT,
    ADD COLUMN IF NOT EXISTS quarantined_at TIMESTAMPTZ;

-- Flagged rows are a small minority; the partial index keeps reversal and
-- audit reporting cheap without touching the hot evidence read path.
CREATE INDEX IF NOT EXISTS idx_topic_members_quarantined
    ON topic_members (topic_id) WHERE quarantined;
