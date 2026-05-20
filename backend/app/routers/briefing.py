import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from app import db
from app.main_v2 import app
from app.utils import _is_valid_person, extract_domain
from app.core.gdelt_taxonomy import classify_source
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)

BRIEFING_DB_TIMEOUT_SECONDS = float(os.getenv("BRIEFING_DB_TIMEOUT_SECONDS", "8"))

from app.services.sentiment_fusion import (  # noqa: E402 — kept here to group briefing config
    NLP_COVERAGE_THRESHOLD,
    NLP_SENTIMENT_SCALE,
    choose_sentiment,
    serialize_country_row,
)


async def _fetch_section(
    conn,
    degraded_segments: list[str],
    segment: str,
    query: str,
    *args,
    row: bool = False,
):
    try:
        if row:
            return await conn.fetchrow(query, *args, timeout=BRIEFING_DB_TIMEOUT_SECONDS)
        return await conn.fetch(query, *args, timeout=BRIEFING_DB_TIMEOUT_SECONDS)
    except Exception as exc:
        degraded_segments.append(segment)
        logger.warning("briefing section degraded: %s: %s", segment, exc)
        return None if row else []

def _build_theme_country_map(rows) -> list:
    """Group theme_country_hourly rows into [{theme, countries: [{code, name, count}]}]."""
    from collections import defaultdict
    grouped: dict = defaultdict(list)
    for r in rows:
        grouped[r['theme']].append({
            "code": r['country_code'],
            "name": r['country_name'] or r['country_code'],
            "count": int(r['cnt'])
        })
    return [
        {"theme": theme, "countries": countries[:4]}
        for theme, countries in grouped.items()
    ]


def _clean_theme_label(theme_code: str) -> str:
    """Convert theme code like WB_475_DIGITAL_GOVERNMENT to 'Digital Government'."""
    label = (theme_code or "").upper()
    prefixes = (
        "WB_", "TAX_", "GDELT_", "CRISISLEX_", "USPEC_", "UN_",
        "SOC_", "ENV_", "ECON_", "EPU_", "MIL_", "CRIME_", "HEALTH_",
    )
    for prefix in prefixes:
        if label.startswith(prefix):
            parts = label.split("_", 2)
            label = parts[-1] if len(parts) >= 2 else label
            break
    parts = label.split("_", 1)
    if parts[0].isdigit() and len(parts) == 2:
        label = parts[1]
    return label.replace("_", " ").title()


@router.get("/api/v2/briefing")
async def get_briefing(hours: int = Query(24, ge=1, le=8760)):
    """Get morning briefing summary."""
    cache_key = f"briefing_data:{hours}"
    cache_ttl = 900 if hours <= 24 else 1800
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 15000")
        degraded_segments: list[str] = []
        has_theme_country_hourly = await conn.fetchval(
            "SELECT to_regclass('theme_country_hourly_v2') IS NOT NULL"
        )
        # Use pre-agg tables for every window. Sentiment payload selects NLP
        # transformer-normalized values when bucket NLP coverage clears the
        # threshold, otherwise falls back to GDELT V2Tone. chosen_sentiment_raw
        # drives ORDER BY so rankings reflect what we actually serve.
        top_countries = await _fetch_section(conn, degraded_segments, "top_countries", """
            WITH agg AS (
                SELECT h.country_code, c.name,
                       SUM(h.signal_count)         AS sig_total,
                       SUM(h.nlp_signal_count)     AS nlp_total,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count)
                            ELSE NULL END           AS gdelt_avg,
                       CASE WHEN SUM(h.nlp_signal_count) > 0
                            THEN SUM(h.avg_nlp_sentiment * h.nlp_signal_count) / SUM(h.nlp_signal_count)
                            ELSE NULL END           AS nlp_avg
                FROM country_hourly_v2 h
                JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY h.country_code, c.name
            )
            SELECT country_code, name,
                   sig_total::bigint                          AS total,
                   COALESCE(gdelt_avg, 0)::float              AS gdelt_sentiment,
                   nlp_avg::float                             AS nlp_sentiment,
                   (nlp_total::float / NULLIF(sig_total, 0))  AS nlp_coverage
            FROM agg
            ORDER BY total DESC LIMIT 10
        """, hours)
        negative_sentiment = await _fetch_section(conn, degraded_segments, "negative_sentiment", """
            WITH agg AS (
                SELECT h.country_code, c.name,
                       SUM(h.signal_count)         AS sig_total,
                       SUM(h.nlp_signal_count)     AS nlp_total,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count)
                            ELSE NULL END           AS gdelt_avg,
                       CASE WHEN SUM(h.nlp_signal_count) > 0
                            THEN SUM(h.avg_nlp_sentiment * h.nlp_signal_count) / SUM(h.nlp_signal_count)
                            ELSE NULL END           AS nlp_avg
                FROM country_hourly_v2 h
                JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY h.country_code, c.name
                HAVING SUM(h.signal_count) > 10
            )
            SELECT country_code, name,
                   sig_total::bigint                          AS total,
                   COALESCE(gdelt_avg, 0)::float              AS gdelt_sentiment,
                   nlp_avg::float                             AS nlp_sentiment,
                   (nlp_total::float / NULLIF(sig_total, 0))  AS nlp_coverage,
                   CASE
                       WHEN nlp_total::float / NULLIF(sig_total, 0) >= $2::float
                            AND nlp_avg IS NOT NULL
                       THEN nlp_avg * $3::float
                       ELSE COALESCE(gdelt_avg, 0)
                   END                                         AS chosen_sentiment_raw
            FROM agg
            ORDER BY chosen_sentiment_raw ASC LIMIT 10
        """, hours, NLP_COVERAGE_THRESHOLD, NLP_SENTIMENT_SCALE)
        positive_sentiment = await _fetch_section(conn, degraded_segments, "positive_sentiment", """
            WITH agg AS (
                SELECT h.country_code, c.name,
                       SUM(h.signal_count)         AS sig_total,
                       SUM(h.nlp_signal_count)     AS nlp_total,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count)
                            ELSE NULL END           AS gdelt_avg,
                       CASE WHEN SUM(h.nlp_signal_count) > 0
                            THEN SUM(h.avg_nlp_sentiment * h.nlp_signal_count) / SUM(h.nlp_signal_count)
                            ELSE NULL END           AS nlp_avg
                FROM country_hourly_v2 h
                JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY h.country_code, c.name
                HAVING SUM(h.signal_count) > 10
            )
            SELECT country_code, name,
                   sig_total::bigint                          AS total,
                   COALESCE(gdelt_avg, 0)::float              AS gdelt_sentiment,
                   nlp_avg::float                             AS nlp_sentiment,
                   (nlp_total::float / NULLIF(sig_total, 0))  AS nlp_coverage,
                   CASE
                       WHEN nlp_total::float / NULLIF(sig_total, 0) >= $2::float
                            AND nlp_avg IS NOT NULL
                       THEN nlp_avg * $3::float
                       ELSE COALESCE(gdelt_avg, 0)
                   END                                         AS chosen_sentiment_raw
            FROM agg
            ORDER BY chosen_sentiment_raw DESC LIMIT 10
        """, hours, NLP_COVERAGE_THRESHOLD, NLP_SENTIMENT_SCALE)
        # theme_hourly_v2 is the live pre-agg populated by ingest_v2.refresh.
        # The legacy signals_theme_hourly table from migration 006 is no longer
        # written to and returns empty results.
        top_themes = await _fetch_section(conn, degraded_segments, "top_themes", """
            SELECT theme, SUM(signal_count)::bigint as count
            FROM theme_hourly_v2
            WHERE hour > NOW() - ($1::int * INTERVAL '1 hour')
            GROUP BY theme ORDER BY count DESC LIMIT 10
        """, hours)
        # TODO(#TBD): source_hourly_v2 pre-agg does not exist yet — high source_name
        # cardinality (~86K unique/day) makes a (hour, source_name) table heavy.
        # Track separately; meanwhile this section degrades to empty. Briefing
        # already surfaces source counts in stats via country_hourly_v2.unique_sources.
        top_sources = await _fetch_section(conn, degraded_segments, "top_sources", """
            SELECT source_name, SUM(signal_count)::bigint as count
            FROM signals_source_hourly
            WHERE bucket > NOW() - ($1::int * INTERVAL '1 hour') AND source_name IS NOT NULL
            GROUP BY source_name ORDER BY count DESC LIMIT 5
        """, hours)
        stats = await _fetch_section(conn, degraded_segments, "stats", """
            SELECT SUM(signal_count)::bigint                          AS total_signals,
                   COUNT(DISTINCT country_code)                       AS countries,
                   SUM(unique_sources)::bigint                        AS sources,
                   CASE WHEN SUM(signal_count) > 0
                        THEN SUM(avg_sentiment * signal_count) / SUM(signal_count)
                        ELSE 0 END                                    AS gdelt_sentiment,
                   CASE WHEN SUM(nlp_signal_count) > 0
                        THEN SUM(avg_nlp_sentiment * nlp_signal_count) / SUM(nlp_signal_count)
                        ELSE NULL END                                 AS nlp_sentiment,
                   (SUM(nlp_signal_count)::float
                       / NULLIF(SUM(signal_count), 0))                AS nlp_coverage
            FROM country_hourly_v2
            WHERE hour > NOW() - ($1::int * INTERVAL '1 hour')
        """, hours, row=True)

        # Theme-country: always use 24h window — fast index lookup, "right now" framing
        top_theme_codes = [r['theme'] for r in top_themes[:6]]
        if top_theme_codes and has_theme_country_hourly:
            theme_country_rows = await _fetch_section(conn, degraded_segments, "theme_country", """
                SELECT tc.theme, tc.country_code, c.name as country_name,
                       SUM(tc.signal_count)::bigint as cnt
                FROM theme_country_hourly_v2 tc
                LEFT JOIN countries_v2 c ON tc.country_code = c.code
                WHERE tc.theme = ANY($1::text[])
                  AND tc.hour > NOW() - INTERVAL '24 hours'
                GROUP BY tc.theme, tc.country_code, c.name
                ORDER BY tc.theme, cnt DESC
            """, top_theme_codes)
        else:
            theme_country_rows = []

        stats = stats or {
            "total_signals": 0,
            "countries": 0,
            "sources": 0,
            "gdelt_sentiment": 0,
            "nlp_sentiment": None,
            "nlp_coverage": 0,
        }

        global_sentiment, global_source, global_coverage = choose_sentiment(
            stats.get("gdelt_sentiment") if isinstance(stats, dict) else stats["gdelt_sentiment"],
            stats.get("nlp_sentiment") if isinstance(stats, dict) else stats["nlp_sentiment"],
            stats.get("nlp_coverage") if isinstance(stats, dict) else stats["nlp_coverage"],
        )

        result = {
            "period_hours": hours,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "degraded": bool(degraded_segments),
            "degraded_segments": degraded_segments,
            "stats": {
                "total_signals": stats['total_signals'] or 0,
                "countries": stats['countries'] or 0,
                "sources": stats['sources'] or 0,
                "avg_sentiment": global_sentiment,
                "sentiment_source": global_source,
                "nlp_coverage": round(global_coverage, 3),
            },
            "top_countries": [serialize_country_row(r) for r in top_countries],
            "negative_sentiment": [serialize_country_row(r) for r in negative_sentiment],
            "positive_sentiment": [serialize_country_row(r) for r in positive_sentiment],
            "top_themes": [
                {"theme": r['theme'], "count": r['count']}
                for r in top_themes
            ],
            "top_sources": [
                {"source": extract_domain(r['source_name']), "count": r['count']}
                for r in top_sources
            ],
            "theme_country": _build_theme_country_map(theme_country_rows)
        }
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(cache_key, cache_ttl, json.dumps(result))
        except Exception:
            pass
    return result


@router.get("/api/v2/briefing/insight")
async def get_briefing_insight(hours: int = Query(24, ge=1, le=8760)):
    """AI meta-summary of the global news landscape for the current time window."""
    cache_key = f"briefing_insight:{hours}"
    generated_at = datetime.now(timezone.utc).isoformat()

    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached_raw = await app.state.redis.get(cache_key)
            if cached_raw:
                data = json.loads(cached_raw)
                data["cached"] = True
                return data
        except Exception:
            pass

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 15000")
            degraded_segments: list[str] = []
            has_theme_hourly = await conn.fetchval(
                "SELECT to_regclass('theme_hourly_v2') IS NOT NULL"
            )

            # Stats + top_countries come from country_hourly_v2 (same fast path as /briefing).
            stats = await _fetch_section(conn, degraded_segments, "insight_stats", """
                SELECT SUM(signal_count)::bigint AS total,
                       COUNT(DISTINCT country_code) AS countries,
                       CASE WHEN SUM(signal_count) > 0
                            THEN (SUM(avg_sentiment * signal_count) / SUM(signal_count))::float
                            ELSE 0::float END AS avg_sent
                FROM country_hourly_v2
                WHERE hour > NOW() - ($1::int * INTERVAL '1 hour')
            """, hours, row=True)

            top_countries = await _fetch_section(conn, degraded_segments, "insight_top_countries", """
                SELECT h.country_code, c.name,
                       SUM(h.signal_count)::bigint AS cnt,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN (SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count))::float
                            ELSE 0::float END AS avg_s
                FROM country_hourly_v2 h
                LEFT JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - ($1::int * INTERVAL '1 hour')
                GROUP BY h.country_code, c.name
                ORDER BY cnt DESC LIMIT 5
            """, hours)

            # top_themes uses theme_hourly_v2 (post-mig 008 + 025). Falls back to
            # signals_theme_hourly if the v2 pre-agg is unavailable on a given env.
            if has_theme_hourly:
                top_themes = await _fetch_section(conn, degraded_segments, "insight_top_themes", """
                    SELECT theme, SUM(signal_count)::bigint AS cnt
                    FROM theme_hourly_v2
                    WHERE hour > NOW() - ($1::int * INTERVAL '1 hour')
                    GROUP BY theme ORDER BY cnt DESC LIMIT 5
                """, hours)
            else:
                top_themes = await _fetch_section(conn, degraded_segments, "insight_top_themes_fallback", """
                    SELECT theme, SUM(signal_count)::bigint AS cnt
                    FROM signals_theme_hourly
                    WHERE bucket > NOW() - ($1::int * INTERVAL '1 hour')
                    GROUP BY theme ORDER BY cnt DESC LIMIT 5
                """, hours)
    except Exception as exc:
        logger.warning("briefing/insight db failed: %s", exc)
        return {"insight": None, "error": "db_error", "generated_at": generated_at}

    stats = stats or {"total": 0, "countries": 0, "avg_sent": 0}

    total = int(stats["total"] or 0)
    countries = int(stats["countries"] or 0)
    avg_sent = float(stats["avg_sent"] or 0) / 10
    themes_str = ", ".join([_clean_theme_label(r["theme"]) for r in top_themes])
    countries_str = ", ".join([
        f"{r['name'] or r['country_code']} ({int(r['cnt'])} signals, {float(r['avg_s'] or 0) / 10:+.2f})"
        for r in top_countries
    ])

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        return {"insight": None, "error": "insight_unavailable", "generated_at": generated_at}

    user_prompt = (
        f"Summarize the global information landscape over the last {hours} hours.\n"
        f"- Total coverage: {total:,} articles across {countries} countries\n"
        f"- Global sentiment: {avg_sent:+.1f} (negative = concern/crisis, positive = stability/progress)\n"
        f"- Dominant topics: {themes_str}\n"
        f"- Most-covered countries (with their tone): {countries_str}\n\n"
        "Write 2-3 sentences describing what the world's media is focused on right now, "
        "what emotional tenor dominates, and any notable geographic patterns in coverage."
    )
    system_prompt = (
        "You are an intelligence analyst giving a morning media briefing. "
        "Describe what the world's press is covering and how, using the data provided. "
        "Be concise, neutral, and analytical. No markdown, no bullet points — flowing prose only."
    )

    try:
        import anthropic as _anthropic
        client = _anthropic.AsyncAnthropic(api_key=anthropic_key)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        insight_text = next((b.text for b in response.content if b.type == "text"), None)
    except Exception as e:
        err = str(e)
        code = "insight_no_credits" if "credit balance" in err.lower() else "insight_unavailable"
        return {"insight": None, "error": code, "generated_at": generated_at}

    result = {"insight": insight_text, "generated_at": generated_at, "cached": False}
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(cache_key, 1800, json.dumps(result))
        except Exception:
            pass
    return result


# =============================================================================
# TRUST INDICATORS API (v3)
# =============================================================================
