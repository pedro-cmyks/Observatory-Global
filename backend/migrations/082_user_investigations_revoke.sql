-- 082_user_investigations_revoke.sql
-- Follow-up to 081 (quality review 2026-07-18): Supabase default privileges
-- had granted ALL on the new table to anon+authenticated, silently voiding
-- 081's intended grant posture. Enforce it: anon touches nothing (RLS already
-- yields zero rows, this is defense-in-depth); authenticated keeps only
-- SELECT/INSERT/UPDATE (tombstones, never hard-delete; TRUNCATE is not
-- RLS-guarded so it must not be grantable).
REVOKE ALL ON user_investigations FROM anon;
REVOKE DELETE, TRUNCATE, REFERENCES, TRIGGER ON user_investigations FROM authenticated;
