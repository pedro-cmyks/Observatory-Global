-- Migration 052: signals_v2.snippet — persist source-provided body text
--
-- Several ingestion sources (Reddit selftext, NewsAPI/RSS/NewsData/Mediastack
-- description, ReliefWeb body) already extract text beyond the headline but it
-- was never persisted. This column captures up to ~500 chars so the reading
-- panels (threads, theme detail) can show real sentences, not only counts.
-- GDELT brings no body text, so GDELT signals leave this NULL. Additive,
-- nullable, no backfill.

ALTER TABLE signals_v2 ADD COLUMN IF NOT EXISTS snippet TEXT;
