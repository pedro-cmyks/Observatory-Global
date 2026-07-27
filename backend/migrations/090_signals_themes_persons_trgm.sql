-- 090: make the /search/thread OR-branches indexable.
--
-- MEASURED 2026-07-22 (prod, 48h window, one keyword per branch):
--   headline  f_unaccent(lower(headline)) LIKE   ->  0.3s  (mig 064 index)
--   source    lower(source_name) LIKE            ->  0.3s  (mig 022 index)
--   themes    lower(array_to_string(themes,' '))  -> >45s  TIMEOUT
--   persons   lower(array_to_string(persons,' ')) -> >45s  TIMEOUT
--
-- The two array_to_string branches have no index, so ANY rare keyword forces a
-- full scan of the window and /search/thread blows its 8s segment timeout and
-- degrades. Dropping the branches is not an option — they carry most of the
-- recall (6h window: themes +794 rows for 'election', +404 for 'flood';
-- persons +703 for 'trump', and the Mbappé case IS a persons hit, 3 -> 7).
--
-- array_to_string() is STABLE, not IMMUTABLE, so it cannot appear in an index
-- expression directly. Same problem unaccent() had, same fix as mig 064: an
-- IMMUTABLE SQL wrapper. Safe for text[] specifically — text output has no
-- locale dependence, which is the only reason the generic version is STABLE.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE OR REPLACE FUNCTION f_arr_text(text[]) RETURNS text
LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
AS $$ SELECT array_to_string($1, ' ') $$;

-- Themes are uppercase ASCII GDELT codes — lower() is enough, no accent fold.
CREATE INDEX IF NOT EXISTS idx_signals_v2_themes_text_trgm
  ON signals_v2 USING gin (lower(f_arr_text(themes)) gin_trgm_ops)
  WHERE themes IS NOT NULL;

-- Persons DO carry accents ('mbappé'), and the LIKE patterns arrive
-- accent-folded from normalize_search_text, so this one folds like headline.
CREATE INDEX IF NOT EXISTS idx_signals_v2_persons_text_trgm
  ON signals_v2 USING gin (f_unaccent(lower(f_arr_text(persons))) gin_trgm_ops)
  WHERE persons IS NOT NULL;

-- Reversal (indexes only, no data): DROP INDEX CONCURRENTLY
--   idx_signals_v2_themes_text_trgm, idx_signals_v2_persons_text_trgm;
