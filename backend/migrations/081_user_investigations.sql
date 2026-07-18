-- 081_user_investigations.sql
-- Accounts v1 (2026-07-18 plan): server-side store for a SIGNED-IN user's
-- Workbench investigations. Local-first: anonymous users never write here
-- (preserves the W0-D5 decision — the server only ever sees anonymous
-- telemetry for them). One row per investigation, whole Investigation JSON
-- as payload, last-write-wins by updated_at. Access is DIRECT from the
-- frontend via supabase-js + RLS — the Fly API is not in this path.
--
-- Reversible: DROP TABLE user_investigations;

CREATE TABLE IF NOT EXISTS user_investigations (
    user_id          UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    investigation_id TEXT        NOT NULL,
    payload          JSONB       NOT NULL,
    updated_at       TIMESTAMPTZ NOT NULL,   -- the Investigation's own updatedAt (LWW key)
    deleted          BOOLEAN     NOT NULL DEFAULT FALSE,  -- tombstone, never hard-delete
    synced_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, investigation_id)
);

ALTER TABLE user_investigations ENABLE ROW LEVEL SECURITY;

-- Owner-only, all verbs. auth.uid() comes from the Supabase JWT.
CREATE POLICY user_investigations_select ON user_investigations
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY user_investigations_insert ON user_investigations
    FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY user_investigations_update ON user_investigations
    FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

GRANT SELECT, INSERT, UPDATE ON user_investigations TO authenticated;
-- (no DELETE grant: tombstones only; no anon grant: signed-in only)
