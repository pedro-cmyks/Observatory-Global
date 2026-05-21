-- Migration 032: compact historical source aggregates for long-window briefing.
--
-- Context: /api/v2/briefing?hours>24 already serves top themes from
-- historical_topic_country_daily, but top_sources still grouped raw signals_v2
-- and could degrade under Supabase IO pressure. This table stores only the
-- product-ready daily publisher aggregate needed by the briefing.

CREATE TABLE IF NOT EXISTS public.historical_source_daily (
    day                 DATE NOT NULL,
    source_domain       TEXT NOT NULL,
    source_family       TEXT NOT NULL,
    signal_class        TEXT NOT NULL,
    signal_count        BIGINT NOT NULL CHECK (signal_count >= 0),
    avg_sentiment       DOUBLE PRECISION,
    sentiment_coverage  DOUBLE PRECISION NOT NULL DEFAULT 0
        CHECK (sentiment_coverage >= 0 AND sentiment_coverage <= 1),
    model_version       TEXT NOT NULL,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (day, source_domain, source_family, signal_class, model_version)
);

CREATE INDEX IF NOT EXISTS idx_hist_source_daily_lookup
    ON public.historical_source_daily (day DESC, signal_count DESC);

CREATE INDEX IF NOT EXISTS idx_hist_source_daily_model_day
    ON public.historical_source_daily (model_version, day DESC, source_domain)
    INCLUDE (signal_count);

CREATE INDEX IF NOT EXISTS idx_hist_source_daily_domain
    ON public.historical_source_daily (source_domain, day DESC);

ALTER TABLE public.historical_source_daily ENABLE ROW LEVEL SECURITY;
