-- 086_pinned_articles.sql
-- Workbench article enrichment F1 (spec 2026-07-20-workbench-article-enrichment):
-- server-side cache of fetched+extracted pinned pages, keyed by URL hash and
-- shared across users (one URL = one fetch; no user data in the row). Article
-- text never enters localStorage/accounts-sync — the pin's citation url is the
-- join key. ai_readings ships now (F2 consumer): per-article LLM reading cached
-- by prompt_version so regenerating a dossier never re-pays inference.
--
-- Frozen-evidence discipline: a successful fetch is never silently overwritten
-- (content_hash + fetched_at); 'pending' rows older than 10 min are re-eligible
-- (a deploy can kill the background task — requeue at read time, no queue infra).

CREATE TABLE IF NOT EXISTS pinned_articles (
  url_hash       TEXT PRIMARY KEY,           -- sha1(url)
  url            TEXT NOT NULL,
  status         TEXT NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending','ok','paywall','robots','error','unsupported')),
  http_status    INT,
  via            TEXT NOT NULL DEFAULT 'live' CHECK (via IN ('live','wayback')),
  title          TEXT,
  outlet         TEXT,
  lang           TEXT,
  extracted_text TEXT,
  excerpt        TEXT,                       -- first ~60 words, display/export-safe
  word_count     INT,
  content_hash   TEXT,
  fetch_error    TEXT,
  fetched_at     TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ai_readings (
  url_hash       TEXT NOT NULL,
  prompt_version TEXT NOT NULL,
  model          TEXT NOT NULL,
  reading        JSONB NOT NULL,             -- {claims:[{text,quote,attribution}],actors,numbers,gaps}
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (url_hash, prompt_version)
);

-- Server-only tables (asyncpg via the API; never PostgREST). 082 lesson:
-- Supabase DEFAULT privileges grant ALL to anon+authenticated on new tables —
-- revoke, and enable RLS with no policies as defense-in-depth.
ALTER TABLE pinned_articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE ai_readings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON pinned_articles FROM anon, authenticated;
REVOKE ALL ON ai_readings FROM anon, authenticated;
