import json
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from app import db
from app.main_v2 import app
from app.utils import _is_valid_person, extract_domain
from app.core.gdelt_taxonomy import classify_source
import httpx

router = APIRouter()

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
        has_theme_country_hourly = await conn.fetchval(
            "SELECT to_regclass('theme_country_hourly_v2') IS NOT NULL"
        )
        if hours > 24:
            # Use pre-agg tables to avoid full signals_v2 scan
            top_countries = await conn.fetch("""
                SELECT h.country_code, c.name,
                       SUM(h.signal_count)::bigint as total,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN (SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count))::float
                            ELSE 0::float END as sentiment
                FROM country_hourly_v2 h
                JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - INTERVAL '%s hours'
                GROUP BY h.country_code, c.name ORDER BY total DESC LIMIT 10
            """ % hours)
            negative_sentiment = await conn.fetch("""
                SELECT h.country_code, c.name,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN (SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count))::float
                            ELSE 0::float END as sentiment,
                       SUM(h.signal_count)::bigint as total
                FROM country_hourly_v2 h
                JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - INTERVAL '%s hours'
                GROUP BY h.country_code, c.name HAVING SUM(h.signal_count) > 10
                ORDER BY sentiment ASC LIMIT 10
            """ % hours)
            positive_sentiment = await conn.fetch("""
                SELECT h.country_code, c.name,
                       CASE WHEN SUM(h.signal_count) > 0
                            THEN (SUM(h.avg_sentiment * h.signal_count) / SUM(h.signal_count))::float
                            ELSE 0::float END as sentiment,
                       SUM(h.signal_count)::bigint as total
                FROM country_hourly_v2 h
                JOIN countries_v2 c ON h.country_code = c.code
                WHERE h.hour > NOW() - INTERVAL '%s hours'
                GROUP BY h.country_code, c.name HAVING SUM(h.signal_count) > 10
                ORDER BY sentiment DESC LIMIT 10
            """ % hours)
            if has_theme_country_hourly:
                top_themes = await conn.fetch("""
                    SELECT theme, SUM(signal_count)::bigint as count
                    FROM theme_country_hourly_v2
                    WHERE hour > NOW() - INTERVAL '%s hours'
                    GROUP BY theme ORDER BY count DESC LIMIT 10
                """ % hours)
            else:
                top_themes = await conn.fetch("""
                    SELECT theme, SUM(signal_count)::bigint as count
                    FROM signals_theme_hourly
                    WHERE bucket > NOW() - INTERVAL '%s hours'
                    GROUP BY theme ORDER BY count DESC LIMIT 10
                """ % hours)
            top_sources = await conn.fetch("""
                SELECT source_name, SUM(signal_count)::bigint as count
                FROM signals_source_hourly
                WHERE bucket > NOW() - INTERVAL '%s hours' AND source_name IS NOT NULL
                GROUP BY source_name ORDER BY count DESC LIMIT 5
            """ % hours)
            stats = await conn.fetchrow("""
                SELECT SUM(signal_count)::bigint as total_signals,
                       COUNT(DISTINCT country_code) as countries,
                       SUM(unique_sources)::bigint as sources,
                       CASE WHEN SUM(signal_count) > 0
                            THEN SUM(avg_sentiment * signal_count) / SUM(signal_count)
                            ELSE 0 END as avg_sentiment
                FROM country_hourly_v2
                WHERE hour > NOW() - INTERVAL '%s hours'
            """ % hours)
        else:
            top_countries = await conn.fetch("""
                SELECT s.country_code, c.name, COUNT(*) as total, AVG(s.sentiment) as sentiment
                FROM signals_v2 s JOIN countries_v2 c ON s.country_code = c.code
                WHERE s.timestamp > NOW() - INTERVAL '%s hours'
                GROUP BY s.country_code, c.name ORDER BY total DESC LIMIT 10
            """ % hours)
            negative_sentiment = await conn.fetch("""
                SELECT s.country_code, c.name, AVG(s.sentiment) as sentiment, COUNT(*) as total
                FROM signals_v2 s JOIN countries_v2 c ON s.country_code = c.code
                WHERE s.timestamp > NOW() - INTERVAL '%s hours'
                GROUP BY s.country_code, c.name HAVING COUNT(*) > 10
                ORDER BY sentiment ASC LIMIT 10
            """ % hours)
            positive_sentiment = await conn.fetch("""
                SELECT s.country_code, c.name, AVG(s.sentiment) as sentiment, COUNT(*) as total
                FROM signals_v2 s JOIN countries_v2 c ON s.country_code = c.code
                WHERE s.timestamp > NOW() - INTERVAL '%s hours'
                GROUP BY s.country_code, c.name HAVING COUNT(*) > 10
                ORDER BY sentiment DESC LIMIT 10
            """ % hours)
            top_themes = await conn.fetch("""
                SELECT unnest(themes) as theme, COUNT(*) as count
                FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '%s hours'
                GROUP BY theme ORDER BY count DESC LIMIT 10
            """ % hours)
            top_sources = await conn.fetch("""
                SELECT source_name, COUNT(*) as count
                FROM signals_v2
                WHERE timestamp > NOW() - INTERVAL '%s hours' AND source_name IS NOT NULL
                GROUP BY source_name ORDER BY count DESC LIMIT 5
            """ % hours)
            stats = await conn.fetchrow("""
                SELECT COUNT(*) as total_signals, COUNT(DISTINCT country_code) as countries,
                       COUNT(DISTINCT source_name) as sources, AVG(sentiment) as avg_sentiment
                FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '%s hours'
            """ % hours)

        # Theme-country: always use 24h window — fast index lookup, "right now" framing
        top_theme_codes = [r['theme'] for r in top_themes[:6]]
        if top_theme_codes and has_theme_country_hourly:
            theme_country_rows = await conn.fetch("""
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


        result = {
            "period_hours": hours,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": {
                "total_signals": stats['total_signals'] or 0,
                "countries": stats['countries'] or 0,
                "sources": stats['sources'] or 0,
                "avg_sentiment": float(stats['avg_sentiment'] or 0) / 10
            },
            "top_countries": [
                {"code": r['country_code'], "name": r['name'], "signals": r['total'], "sentiment": float(r['sentiment'] or 0) / 10}
                for r in top_countries
            ],
            "negative_sentiment": [
                {"code": r['country_code'], "name": r['name'], "sentiment": float(r['sentiment'] or 0) / 10, "signals": r['total']}
                for r in negative_sentiment
            ],
            "positive_sentiment": [
                {"code": r['country_code'], "name": r['name'], "sentiment": float(r['sentiment'] or 0) / 10, "signals": r['total']}
                for r in positive_sentiment
            ],
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
            await conn.execute("SET statement_timeout = 10000")
            has_theme_country_hourly = await conn.fetchval(
                "SELECT to_regclass('theme_country_hourly_v2') IS NOT NULL"
            )
            stats = await conn.fetchrow(f"""
                SELECT COUNT(*) as total, COUNT(DISTINCT country_code) as countries,
                       AVG(sentiment) as avg_sent
                FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '{hours} hours'
            """)
            if hours > 24 and has_theme_country_hourly:
                top_themes = await conn.fetch(f"""
                    SELECT theme, SUM(signal_count) as cnt
                    FROM theme_country_hourly_v2
                    WHERE hour > NOW() - INTERVAL '{hours} hours'
                    GROUP BY theme ORDER BY cnt DESC LIMIT 5
                """)
            elif hours > 24:
                top_themes = await conn.fetch(f"""
                    SELECT theme, SUM(signal_count) as cnt
                    FROM signals_theme_hourly
                    WHERE bucket > NOW() - INTERVAL '{hours} hours'
                    GROUP BY theme ORDER BY cnt DESC LIMIT 5
                """)
            else:
                top_themes = await conn.fetch(f"""
                    SELECT unnest(themes) as theme, COUNT(*) as cnt
                    FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '{hours} hours'
                    GROUP BY theme ORDER BY cnt DESC LIMIT 5
                """)
            top_countries = await conn.fetch(f"""
                SELECT s.country_code, co.name, COUNT(*) as cnt, AVG(s.sentiment) as avg_s
                FROM signals_v2 s LEFT JOIN countries_v2 co ON s.country_code = co.code
                WHERE s.timestamp > NOW() - INTERVAL '{hours} hours'
                GROUP BY s.country_code, co.name ORDER BY cnt DESC LIMIT 5
            """)
    except Exception as e:
        return {"insight": None, "error": "db_error", "generated_at": generated_at}

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
