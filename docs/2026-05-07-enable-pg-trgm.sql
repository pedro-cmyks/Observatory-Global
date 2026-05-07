-- Atlas search fuzzy matching support.
-- Run in the Supabase SQL editor if pg_trgm is not already enabled.
-- The application handles a missing extension gracefully, but fuzzy suggestions
-- need the similarity() function from pg_trgm.

CREATE EXTENSION IF NOT EXISTS pg_trgm;
