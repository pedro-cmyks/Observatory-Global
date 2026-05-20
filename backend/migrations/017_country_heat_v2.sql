-- Migration 017: country_heat_v2 materialised view for Atlas composite heat.
-- Issue #165, docs/methodology/atlas-heat.md.
--
-- Strategy:
--   - One row per (country_code, hours_window).
--   - Components normalised to [0, 1] in the view itself.
--   - Composite formula computed in the view so the API never recomputes.
--   - Refresh schedule: every 5 minutes by the aggregator job.
--
-- v1 ships with hours_window=24 only. Future revisions add 6, 72, 168.

CREATE MATERIALIZED VIEW IF NOT EXISTS country_heat_v2 AS
WITH
window_params AS (
    SELECT 24::INT AS hours_window
),
country_window AS (
    SELECT
        s.country_code,
        COUNT(*)::BIGINT AS volume_now,
        AVG(NULLIF(s.geo_confidence, 0)) AS geo_confidence_mean,
        COUNT(DISTINCT s.source_family) AS family_count
    FROM signals_v2 s, window_params w
    WHERE s.timestamp > NOW() - (w.hours_window || ' hours')::INTERVAL
      AND s.country_code IS NOT NULL
    GROUP BY s.country_code
),
country_baseline AS (
    SELECT
        country_code,
        AVG(daily_n)::DOUBLE PRECISION AS volume_baseline_daily,
        NULLIF(STDDEV_POP(daily_n), 0)::DOUBLE PRECISION AS volume_sigma_daily
    FROM (
        SELECT country_code, date_trunc('day', timestamp) AS day, COUNT(*)::BIGINT AS daily_n
        FROM signals_v2
        WHERE timestamp BETWEEN NOW() - INTERVAL '14 days' AND NOW() - INTERVAL '1 day'
          AND country_code IS NOT NULL
        GROUP BY 1, 2
    ) d
    GROUP BY country_code
),
global_themes AS (
    SELECT
        LOWER(COALESCE(t.theme, '__none__')) AS theme_key,
        COUNT(*)::BIGINT AS global_count
    FROM signals_v2 s
    LEFT JOIN LATERAL UNNEST(COALESCE(s.themes, ARRAY[]::TEXT[])) AS t(theme) ON TRUE
    , window_params w
    WHERE s.timestamp > NOW() - (w.hours_window || ' hours')::INTERVAL
    GROUP BY 1
),
global_total AS (
    SELECT SUM(global_count)::BIGINT AS total FROM global_themes
),
country_themes AS (
    SELECT
        s.country_code,
        LOWER(COALESCE(t.theme, '__none__')) AS theme_key,
        COUNT(*)::BIGINT AS country_count
    FROM signals_v2 s
    LEFT JOIN LATERAL UNNEST(COALESCE(s.themes, ARRAY[]::TEXT[])) AS t(theme) ON TRUE
    , window_params w
    WHERE s.timestamp > NOW() - (w.hours_window || ' hours')::INTERVAL
      AND s.country_code IS NOT NULL
    GROUP BY 1, 2
),
country_theme_totals AS (
    SELECT country_code, SUM(country_count)::BIGINT AS country_total
    FROM country_themes
    GROUP BY country_code
),
surprise AS (
    SELECT
        ct.country_code,
        SUM(
            (ct.country_count::DOUBLE PRECISION / GREATEST(ctt.country_total, 1))
            * LN(
                GREATEST(
                    (ct.country_count::DOUBLE PRECISION / GREATEST(ctt.country_total, 1))
                    / NULLIF(gt.global_count::DOUBLE PRECISION / NULLIF(g.total, 0), 0),
                    1e-9
                )
            )
        ) AS kl
    FROM country_themes ct
    JOIN country_theme_totals ctt USING (country_code)
    JOIN global_themes gt USING (theme_key)
    CROSS JOIN global_total g
    GROUP BY ct.country_code
),
country_families AS (
    SELECT
        s.country_code,
        s.source_family,
        COUNT(*)::BIGINT AS n
    FROM signals_v2 s, window_params w
    WHERE s.timestamp > NOW() - (w.hours_window || ' hours')::INTERVAL
      AND s.country_code IS NOT NULL
      AND s.source_family IS NOT NULL
    GROUP BY 1, 2
),
country_family_totals AS (
    SELECT country_code, SUM(n)::BIGINT AS total FROM country_families GROUP BY 1
),
diversity AS (
    SELECT
        cf.country_code,
        - SUM(
            (cf.n::DOUBLE PRECISION / GREATEST(cft.total, 1))
            * LN(NULLIF(cf.n::DOUBLE PRECISION / GREATEST(cft.total, 1), 0))
        ) AS shannon_h,
        LN(NULLIF(COUNT(*), 0)) AS h_max
    FROM country_families cf
    JOIN country_family_totals cft USING (country_code)
    GROUP BY cf.country_code
),
voice AS (
    SELECT
        s.country_code,
        SUM(CASE WHEN s.source_origin_country = s.country_code THEN 1 ELSE 0 END)::DOUBLE PRECISION
            / NULLIF(SUM(CASE WHEN s.source_origin_country IS NOT NULL THEN 1 ELSE 0 END), 0)
            AS local_voice_ratio_raw,
        SUM(CASE WHEN s.source_origin_country IS NOT NULL THEN 1 ELSE 0 END)::BIGINT AS known_origin_n
    FROM signals_v2 s, window_params w
    WHERE s.timestamp > NOW() - (w.hours_window || ' hours')::INTERVAL
      AND s.country_code IS NOT NULL
    GROUP BY s.country_code
),
country_frames AS (
    SELECT
        s.country_code,
        s.nlp_framing,
        COUNT(*)::BIGINT AS n
    FROM signals_v2 s, window_params w
    WHERE s.timestamp > NOW() - (w.hours_window || ' hours')::INTERVAL
      AND s.country_code IS NOT NULL
      AND s.nlp_framing IS NOT NULL
    GROUP BY 1, 2
),
country_frame_totals AS (
    SELECT country_code, SUM(n)::BIGINT AS total FROM country_frames GROUP BY 1
),
polyphony AS (
    SELECT
        cf.country_code,
        - SUM(
            (cf.n::DOUBLE PRECISION / GREATEST(cft.total, 1))
            * LN(NULLIF(cf.n::DOUBLE PRECISION / GREATEST(cft.total, 1), 0))
        ) AS frame_h,
        cft.total AS framed_n
    FROM country_frames cf
    JOIN country_frame_totals cft USING (country_code)
    GROUP BY cf.country_code, cft.total
),
duplication AS (
    SELECT
        s.country_code,
        1 - (COUNT(DISTINCT LOWER(s.headline))::DOUBLE PRECISION / NULLIF(COUNT(*), 0)) AS dup_ratio
    FROM signals_v2 s, window_params w
    WHERE s.timestamp > NOW() - (w.hours_window || ' hours')::INTERVAL
      AND s.country_code IS NOT NULL
      AND s.headline IS NOT NULL
    GROUP BY s.country_code
)
SELECT
    cw.country_code,
    (SELECT hours_window FROM window_params) AS hours_window,
    cw.volume_now,
    cb.volume_baseline_daily,
    cb.volume_sigma_daily,
    -- z_velocity_norm via sigmoid scaled to ~0.95 at 3σ
    COALESCE(
        1.0 / (1.0 + EXP(
            - ((cw.volume_now::DOUBLE PRECISION / ((SELECT hours_window FROM window_params)::DOUBLE PRECISION / 24)
                - cb.volume_baseline_daily) / NULLIF(cb.volume_sigma_daily, 0)) / 3.0
        )),
        0.5
    ) AS z_velocity_norm,
    COALESCE(LEAST(GREATEST(s.kl, 0) / 2.0, 1.0), 0.0) AS surprise_kl_norm,
    COALESCE(
        CASE WHEN d.h_max > 0 THEN d.shannon_h / d.h_max ELSE 0 END,
        0.0
    ) AS source_diversity_norm,
    COALESCE(
        CASE WHEN v.known_origin_n >= 50 THEN v.local_voice_ratio_raw ELSE 0.5 END,
        0.5
    ) AS local_voice_ratio,
    COALESCE(
        CASE WHEN p.framed_n >= 25 THEN p.frame_h / LN(6) ELSE 0.5 END,
        0.5
    ) AS polyphony_norm,
    COALESCE(cw.geo_confidence_mean, 0.5) AS geo_confidence_mean,
    COALESCE(LEAST(GREATEST(dup.dup_ratio, 0), 1.0), 0.0) AS duplication_index_norm,
    -- Composite
    (
          0.25 * COALESCE(
              1.0 / (1.0 + EXP(
                  - ((cw.volume_now::DOUBLE PRECISION / ((SELECT hours_window FROM window_params)::DOUBLE PRECISION / 24)
                      - cb.volume_baseline_daily) / NULLIF(cb.volume_sigma_daily, 0)) / 3.0
              )),
              0.5
          )
        + 0.20 * COALESCE(LEAST(GREATEST(s.kl, 0) / 2.0, 1.0), 0.0)
        + 0.15 * COALESCE(CASE WHEN d.h_max > 0 THEN d.shannon_h / d.h_max ELSE 0 END, 0.0)
        + 0.15 * COALESCE(CASE WHEN v.known_origin_n >= 50 THEN v.local_voice_ratio_raw ELSE 0.5 END, 0.5)
        + 0.10 * COALESCE(CASE WHEN p.framed_n >= 25 THEN p.frame_h / LN(6) ELSE 0.5 END, 0.5)
        + 0.10 * COALESCE(cw.geo_confidence_mean, 0.5)
        - 0.05 * COALESCE(LEAST(GREATEST(dup.dup_ratio, 0), 1.0), 0.0)
    ) AS atlas_heat,
    NOW() AS refreshed_at
FROM country_window cw
LEFT JOIN country_baseline cb USING (country_code)
LEFT JOIN surprise s          USING (country_code)
LEFT JOIN diversity d         USING (country_code)
LEFT JOIN voice v             USING (country_code)
LEFT JOIN polyphony p         USING (country_code)
LEFT JOIN duplication dup     USING (country_code);

CREATE UNIQUE INDEX IF NOT EXISTS idx_country_heat_v2_pk
    ON country_heat_v2 (country_code, hours_window);

CREATE INDEX IF NOT EXISTS idx_country_heat_v2_heat
    ON country_heat_v2 (atlas_heat DESC);
