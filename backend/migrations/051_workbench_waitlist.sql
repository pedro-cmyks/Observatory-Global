-- Migration 051: workbench_waitlist (public MVP early-access gate)
--
-- Captures early-access interest from the gated Workbench preview overlay.
-- Minimal fields: email + optional use_case. referrer is server-derived.
-- RLS locked: only the backend service role reads/writes; emails are never
-- exposed by any public GET (only an aggregate count).

CREATE TABLE IF NOT EXISTS workbench_waitlist (
    id          BIGSERIAL PRIMARY KEY,
    email       TEXT NOT NULL,
    use_case    TEXT NULL,
    referrer    TEXT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT workbench_waitlist_email_unique UNIQUE (email)
);

ALTER TABLE workbench_waitlist ENABLE ROW LEVEL SECURITY;
-- No public policies created on purpose: only the service role bypasses RLS.
