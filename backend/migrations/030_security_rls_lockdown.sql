-- Migration 030: security lockdown
-- Applied via Supabase MCP on 2026-05-21.
--
-- Context: Supabase advisor flagged CRITICAL exposure — 45 public tables
-- had RLS disabled, meaning the anon/authenticated roles could read or
-- write every row via PostgREST.
--
-- Backend connects as `postgres` superuser via DATABASE_URL, which bypasses
-- RLS unconditionally. Frontend does NOT use the Supabase JS client. So
-- enabling RLS without policies effectively locks the anon role out of the
-- public schema while leaving the application unaffected.
--
-- Verification after apply:
--   - /health returns db_ok=true
--   - /api/v2/briefing?hours=24 returns heat_countries=10, top_themes=10
--   - pg_tables.rowsecurity = true for all 45 public tables
--   - get_advisors(security) drops from 1 CRITICAL + 2 ERROR + many WARN
--     to INFO-level (RLS Enabled No Policy) + 1 WARN (pg_trgm in public).

-- 1. Enable RLS on all 45 public tables (lockdown, no policies needed).
ALTER TABLE public.acled_conflicts_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.atlas_topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.countries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.countries_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.country_baseline_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.country_daily_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.data_lifecycle_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.flows ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.gdelt_signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.historical_archive_coverage ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.historical_evidence_samples ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.historical_processing_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.historical_topic_country_daily ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.hotspots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingest_file_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.ingest_watermark ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nlp_corrections ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nlp_progress ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.nlp_sample_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signal_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signal_themes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signal_topic_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signals_country_hourly ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signals_source_hourly ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signals_theme_hourly ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.signals_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stance_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.theme_aggregations_1h ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.theme_country_hourly_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.theme_daily_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.theme_hourly_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_learning_examples ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_snapshots_2025_w03 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_snapshots_2025_w04 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_snapshots_2025_w05 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_snapshots_2025_w06 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_snapshots_2025_w07 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topic_snapshots_default ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trending_themes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trends_archive ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trends_v2 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.wiki_pageviews_v2 ENABLE ROW LEVEL SECURITY;

-- 2. Revoke anon/authenticated access to materialized views that PostgREST
--    auto-exposes (RLS doesn't apply to matviews).
REVOKE SELECT ON public.mv_recent_hotspots FROM anon, authenticated;
REVOKE SELECT ON public.low_volume_countries FROM anon, authenticated;
REVOKE SELECT ON public.country_heat_v2 FROM anon, authenticated;
REVOKE SELECT ON public.mv_active_flows FROM anon, authenticated;
REVOKE SELECT ON public.country_hourly_v2 FROM anon, authenticated;

-- 3. Convert SECURITY DEFINER views to security_invoker so they enforce
--    the caller's permissions instead of the creator's.
ALTER VIEW public.v_table_sizes SET (security_invoker = true);
ALTER VIEW public.v_row_counts SET (security_invoker = true);

-- 4. Lock function search_path to prevent search_path-injection attacks.
ALTER FUNCTION public.populate_gdelt_derived_fields() SET search_path = public, pg_temp;
ALTER FUNCTION public.update_theme_aggregations() SET search_path = public, pg_temp;
ALTER FUNCTION public.refresh_country_hourly() SET search_path = public, pg_temp;
ALTER FUNCTION public.refresh_country_baseline() SET search_path = public, pg_temp;
ALTER FUNCTION public.refresh_aggregates() SET search_path = public, pg_temp;
ALTER FUNCTION public.geographic_precision(smallint) SET search_path = public, pg_temp;
ALTER FUNCTION public.bucket_1h(timestamp with time zone) SET search_path = public, pg_temp;
ALTER FUNCTION public.sentiment_label(numeric) SET search_path = public, pg_temp;
ALTER FUNCTION public.update_topic_last_seen() SET search_path = public, pg_temp;
ALTER FUNCTION public.detect_stance_change() SET search_path = public, pg_temp;
ALTER FUNCTION public.bucket_15min(timestamp with time zone) SET search_path = public, pg_temp;
