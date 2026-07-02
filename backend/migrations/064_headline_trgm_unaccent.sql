-- 064: accent-folded trigram search over headlines (the Mbappé hole, L1).
-- unaccent() per row seq-scans 160K+ rows > interactive timeouts. Immutable
-- wrapper (unaccent is only STABLE) + trigram GIN = fast ILIKE '%…%' matching
-- that sees through diacritics.
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
AS $$ SELECT public.unaccent('public.unaccent', $1) $$;
CREATE INDEX IF NOT EXISTS idx_signals_headline_trgm
  ON signals_v2 USING gin (f_unaccent(lower(headline)) gin_trgm_ops);
