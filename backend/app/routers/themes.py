import json
import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from app import db
from app.main_v2 import app
from app.utils import _is_valid_person, _resolve_persons, extract_domain
from app.core.gdelt_taxonomy import classify_source, get_concepts_for_theme
import httpx

router = APIRouter()

@router.get("/api/v2/focus")
async def get_focus_data(
    focus_type: str = Query(..., description="Type: theme, person, country, source"),
    value: str = Query(..., description="Value to focus on"),
    hours: int = Query(24, ge=1, le=8760)
):
    """
    Get filtered data for Focus Mode.
    Returns nodes, related topics, and top sources matching the focus.
    """
    async with db.pool.acquire() as conn:
        # Build WHERE clause based on focus type
        if focus_type == "theme":
            focus_filter = "$1 = ANY(themes)"
            filter_value = value.upper()
        elif focus_type == "person":
            focus_filter = "EXISTS (SELECT 1 FROM unnest(persons) p WHERE LOWER(p) LIKE LOWER($1))"
            filter_value = f"%{value}%"
        elif focus_type == "country":
            focus_filter = "country_code = $1"
            filter_value = value.upper()
        elif focus_type == "source":
            focus_filter = "LOWER(source_name) LIKE LOWER($1)"
            filter_value = f"%{value}%"
        else:
            return {"error": f"Unknown focus type: {focus_type}"}
        
        # 1. Get nodes (countries) with signal counts
        nodes = await conn.fetch(f"""
            SELECT 
                country_code,
                COUNT(*) as signal_count,
                ROUND(AVG(sentiment)::numeric, 2) as avg_sentiment,
                COUNT(DISTINCT source_name) as unique_sources
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
            GROUP BY country_code
            ORDER BY signal_count DESC
        """, filter_value)
        
        # 2. Get related topics (co-occurring themes)
        related = await conn.fetch(f"""
            SELECT 
                unnest(themes) as topic,
                COUNT(*) as count
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
            GROUP BY topic
            ORDER BY count DESC
            LIMIT 15
        """, filter_value)
        
        # Filter out the focus value itself if it's a theme
        related_topics = [
            {"topic": r['topic'], "count": int(r['count'])}
            for r in related
            if r['topic'].upper() != value.upper()
        ][:10]
        
        # 3. Get top sources
        sources = await conn.fetch(f"""
            SELECT 
                source_name,
                COUNT(*) as count,
                ROUND(AVG(sentiment)::numeric, 2) as avg_sentiment
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
              AND source_name IS NOT NULL
            GROUP BY source_name
            ORDER BY count DESC
            LIMIT 10
        """, filter_value)
        
        # 4. Get recent headlines (deduped by title prefix)
        headlines = await conn.fetch(f"""
            SELECT DISTINCT ON (LEFT(source_url, 100))
                source_url,
                source_name,
                headline,
                timestamp
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
              AND source_url IS NOT NULL
            ORDER BY LEFT(source_url, 100), timestamp DESC
            LIMIT 10
        """, filter_value)

        # 5. Get key people mentioned in matching signals
        persons_rows = await conn.fetch(f"""
            SELECT
                p AS person,
                COUNT(*) AS signal_count,
                ROUND(AVG(sentiment)::numeric, 2) AS avg_sentiment,
                COUNT(DISTINCT country_code) AS country_count
            FROM signals_v2, unnest(persons) p
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
              AND {focus_filter}
              AND p <> ''
              AND LENGTH(p) > 3
            GROUP BY p
            ORDER BY signal_count DESC
            LIMIT 12
        """, filter_value)

        is_valid_person = _is_valid_person

        key_people = [
            {
                "person": r['person'],
                "signal_count": int(r['signal_count']),
                "avg_sentiment": float(r['avg_sentiment'] or 0),
                "country_count": int(r['country_count'])
            }
            for r in persons_rows
            if is_valid_person(r['person'])
        ][:8]

        # Calculate totals
        total_signals = sum(int(n['signal_count']) for n in nodes)
        total_countries = len(nodes)

        return {
            "focus": {
                "type": focus_type,
                "value": value,
                "hours": hours
            },
            "summary": {
                "total_signals": total_signals,
                "total_countries": total_countries,
                "generated_at": datetime.now(timezone.utc).isoformat()
            },
            "nodes": [
                {
                    "country_code": r['country_code'],
                    "signal_count": int(r['signal_count']),
                    "avg_sentiment": float(r['avg_sentiment'] or 0),
                    "unique_sources": int(r['unique_sources'])
                }
                for r in nodes
            ],
            "related_topics": related_topics,
            "top_sources": [
                {
                    "source": extract_domain(r['source_name']),
                    "count": int(r['count']),
                    "avg_sentiment": float(r['avg_sentiment'] or 0)
                }
                for r in sources
            ],
            "headlines": [
                {
                    "url": r['source_url'],
                    "source": r['source_name'],
                    "headline": r['headline'],
                    "time": r['timestamp'].isoformat() if r['timestamp'] else None
                }
                for r in headlines
            ],
            "key_people": key_people
        }

@router.get("/api/v2/theme/{theme_code}/drift")
async def get_theme_drift(
    theme_code: str,
    country_code: str = Query(None, description="Filter by country"),
    days: int = Query(14, ge=1, le=90)
):
    """Get daily sentiment and volume trajectory for a theme."""
    try:
        async with db.pool.acquire() as conn:
            where_conditions = [
                "$1 = ANY(themes)",
                f"timestamp > NOW() - INTERVAL '{days} days'"
            ]
            params = [theme_code.upper()]
            
            if country_code:
                where_conditions.append("country_code = $2")
                params.append(country_code.upper())
            
            where_clause = " AND ".join(where_conditions)
            
            drift_data = await conn.fetch(f"""
                SELECT 
                    DATE_TRUNC('day', timestamp) as date,
                    AVG(sentiment) as sentiment,
                    COUNT(*) as volume
                FROM signals_v2
                WHERE {where_clause}
                GROUP BY DATE_TRUNC('day', timestamp)
                ORDER BY date ASC
            """, *params)
            
            return {
                "theme": theme_code.upper(),
                "country": country_code.upper() if country_code else "GLO",
                "days": days,
                "drift": [
                    {
                        "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                        "sentiment": round(row["sentiment"], 3) if row["sentiment"] is not None else 0,
                        "volume": row["volume"]
                    }
                    for row in drift_data
                ]
            }
    except Exception as e:
        logger.error(f"Error fetching theme drift for {theme_code}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/api/v2/theme/{theme_code}")
async def get_theme_details(
    theme_code: str,
    country_code: str = Query(None, description="Filter by country"),
    hours: int = Query(24, ge=1, le=8760)
):
    """Get detailed information about a theme including rich context."""
    from app.core.gdelt_taxonomy import get_concepts_for_theme
    # For long windows, cap signals_v2 scans at 48h; use pre-agg tables for aggregates
    signals_hours = min(hours, 48) if hours > 24 else hours
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 25000")
            # Build WHERE clause based on filters
            where_conditions = [
                "$1 = ANY(themes)",
                f"timestamp > NOW() - INTERVAL '{signals_hours} hours'"
            ]
            params = [theme_code.upper()]
            
            if country_code:
                where_conditions.append("country_code = $2")
                params.append(country_code.upper())
            
            where_clause = " AND ".join(where_conditions)
            
            # Get signals
            signals = await conn.fetch(f"""
                SELECT 
                    timestamp,
                    country_code,
                    source_name,
                    source_url,
                    sentiment,
                    themes,
                    persons
                FROM signals_v2
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT 200
            """, *params)

            # Representative temporal sample for graph views.
            # Keep `signals` as latest coverage; spread graphSignals across hours.
            graph_signals = await conn.fetch(f"""
                WITH ranked AS (
                    SELECT
                        timestamp,
                        country_code,
                        source_name,
                        source_url,
                        sentiment,
                        themes,
                        persons,
                        ROW_NUMBER() OVER (
                            PARTITION BY date_trunc('hour', timestamp)
                            ORDER BY timestamp DESC
                        ) as rn
                    FROM signals_v2
                    WHERE {where_clause}
                )
                SELECT
                    timestamp,
                    country_code,
                    source_name,
                    source_url,
                    sentiment,
                    themes,
                    persons
                FROM ranked
                WHERE rn <= 8
                ORDER BY timestamp ASC
                LIMIT 240
            """, *params)
            
            # Get timeline — use pre-agg for long windows to avoid full scan
            if hours > 24:
                timeline = await conn.fetch("""
                    SELECT hour,
                           SUM(signal_count)::bigint as count,
                           CASE WHEN SUM(signal_count) > 0
                                THEN (SUM(avg_sentiment * signal_count) / SUM(signal_count))::float
                                ELSE 0::float END as avg_sentiment
                    FROM theme_country_hourly_v2
                    WHERE theme = $1 AND hour > NOW() - INTERVAL '%s hours'
                    GROUP BY hour ORDER BY hour
                """ % hours, theme_code.upper())
            else:
                timeline = await conn.fetch(f"""
                    SELECT
                        date_trunc('hour', timestamp) as hour,
                        COUNT(*) as count,
                        AVG(sentiment) as avg_sentiment
                    FROM signals_v2
                    WHERE {where_clause}
                    GROUP BY hour
                    ORDER BY hour
                """, *params)
            
            # Get country breakdown — use pre-agg for long windows
            if hours > 24:
                country_breakdown = await conn.fetch("""
                    SELECT country_code,
                           SUM(signal_count)::bigint as count,
                           CASE WHEN SUM(signal_count) > 0
                                THEN (SUM(avg_sentiment * signal_count) / SUM(signal_count))::float
                                ELSE 0::float END as avg_sentiment
                    FROM theme_country_hourly_v2
                    WHERE theme = $1 AND hour > NOW() - INTERVAL '%s hours'
                    GROUP BY country_code ORDER BY count DESC LIMIT 15
                """ % hours, theme_code.upper())
            else:
                country_breakdown = await conn.fetch(f"""
                    SELECT
                        country_code,
                        COUNT(*) as count,
                        AVG(sentiment) as avg_sentiment
                    FROM signals_v2
                    WHERE $1 = ANY(themes)
                    AND timestamp > NOW() - INTERVAL '{hours} hours'
                    GROUP BY country_code
                    ORDER BY count DESC
                    LIMIT 15
                """, theme_code.upper())
            
            # Get related themes (co-occurrence) — cap to 48h to avoid full scan
            related_themes_data = await conn.fetch(f"""
                SELECT
                    unnest(themes) as related_theme,
                    COUNT(*) as count
                FROM signals_v2
                WHERE $1 = ANY(themes)
                AND timestamp > NOW() - INTERVAL '{signals_hours} hours'
                GROUP BY related_theme
                ORDER BY count DESC
                LIMIT 20
            """, theme_code.upper())
            
            # Filter out current theme from related
            related_themes = [
                {"theme": r['related_theme'], "count": int(r['count'])}
                for r in related_themes_data
                if r['related_theme'].upper() != theme_code.upper()
            ][:10]
            
            # Get top sources
            top_sources = await conn.fetch(f"""
                SELECT 
                    source_name,
                    COUNT(*) as count,
                    AVG(sentiment) as avg_sentiment
                FROM signals_v2
                WHERE {where_clause}
                AND source_name IS NOT NULL
                GROUP BY source_name
                ORDER BY count DESC
                LIMIT 20
            """, *params)

            # Calculate summary stats
            # Get true total from pre-agg (not the LIMIT 200 capped array)
            if hours > 24:
                true_total_row = await conn.fetchrow("""
                    SELECT SUM(signal_count)::bigint as n
                    FROM theme_country_hourly_v2
                    WHERE theme = $1 AND hour > NOW() - INTERVAL '%s hours'
                """ % hours, theme_code.upper())
                true_total = int(true_total_row['n'] or 0) if true_total_row else len(signals)
            else:
                true_total_row = await conn.fetchrow(f"""
                    SELECT COUNT(*)::bigint as n FROM signals_v2 WHERE {where_clause}
                """, *params)
                true_total = int(true_total_row['n'] or 0) if true_total_row else len(signals)
            total = len(signals)
            avg_sentiment = sum(float(s['sentiment'] or 0) for s in signals) / total if total > 0 else 0
            
            # Get unique persons mentioned
            all_persons = []
            for s in signals:
                if s['persons']:
                    all_persons.extend(s['persons'])
            person_counts = {}
            for p in all_persons:
                person_counts[p] = person_counts.get(p, 0) + 1
            top_persons = [
                {"name": p[0], "count": p[1]}
                for p in sorted(person_counts.items(), key=lambda x: x[1], reverse=True)
                if _is_valid_person(p[0])
            ][:10]

            # --- Country Framing: how different countries cover the same theme ---
            framing_rows = await conn.fetch(f"""
                SELECT
                    s.country_code,
                    co.name as country_name,
                    COUNT(*) as signal_count,
                    ROUND(AVG(s.sentiment)::numeric, 2) as avg_sentiment
                FROM signals_v2 s
                LEFT JOIN countries_v2 co ON s.country_code = co.code
                WHERE $1 = ANY(s.themes)
                  AND s.timestamp > NOW() - INTERVAL '{signals_hours} hours'
                  AND s.country_code IS NOT NULL
                GROUP BY s.country_code, co.name
                ORDER BY signal_count DESC
                LIMIT 6
            """, theme_code.upper())

            country_framing = []
            for fr in framing_rows:
                cc = fr['country_code']
                # Get top 3 co-occurring sub-themes for this country
                sub_rows = await conn.fetch(f"""
                    SELECT sub_theme, COUNT(*) as cnt
                    FROM (
                        SELECT unnest(themes) as sub_theme
                        FROM signals_v2
                        WHERE $1 = ANY(themes)
                          AND country_code = $2
                          AND timestamp > NOW() - INTERVAL '{signals_hours} hours'
                    ) t
                    WHERE sub_theme != $1
                    GROUP BY sub_theme
                    ORDER BY cnt DESC
                    LIMIT 3
                """, theme_code.upper(), cc)

                avg_s = float(fr['avg_sentiment'] or 0)
                if avg_s > 0.5:
                    sentiment_label = "positive"
                elif avg_s > -0.5:
                    sentiment_label = "neutral"
                elif avg_s > -2.0:
                    sentiment_label = "negative"
                else:
                    sentiment_label = "very_negative"

                country_framing.append({
                    "country_code": cc,
                    "country_name": fr['country_name'] or cc,
                    "signal_count": int(fr['signal_count']),
                    "avg_sentiment": avg_s,
                    "top_sub_themes": [r['sub_theme'] for r in sub_rows],
                    "sentiment_label": sentiment_label
                })

            return {
                "theme": theme_code,
                "country": country_code,
                "hours": hours,
                "total": true_total,
                "signalSample": total,
                "avgSentiment": round(avg_sentiment, 3),
                "signals": [
                    {
                        "timestamp": r['timestamp'].isoformat(),
                        "country": r['country_code'],
                        "source": r['source_name'],
                        "url": r['source_url'],
                        "sentiment": float(r['sentiment'] or 0),
                        "otherThemes": [t for t in (r['themes'] or []) if t.upper() != theme_code.upper()][:5],
                        "persons": (r['persons'] or [])[:5]
                    }
                    for r in signals
                ],
                "graphSignals": [
                    {
                        "timestamp": r['timestamp'].isoformat(),
                        "country": r['country_code'],
                        "source": r['source_name'],
                        "url": r['source_url'],
                        "sentiment": float(r['sentiment'] or 0),
                        "otherThemes": [t for t in (r['themes'] or []) if t.upper() != theme_code.upper()][:5],
                        "persons": (r['persons'] or [])[:5]
                    }
                    for r in graph_signals
                ],
                "countryBreakdown": [
                    {"code": r['country_code'], "count": int(r['count']), "sentiment": float(r['avg_sentiment'] or 0)}
                    for r in country_breakdown
                ],
                "relatedThemes": related_themes,
                "topSources": [
                    {
                        "name": extract_domain(r['source_name']),
                        "count": int(r['count']),
                        "sentiment": float(r['avg_sentiment'] or 0),
                        "family": classify_source(r['source_name'] or ""),
                    }
                    for r in top_sources
                ],
                "topPersons": top_persons,
                "timeline": [
                    {"hour": t['hour'].isoformat(), "count": int(t['count']), "sentiment": float(t['avg_sentiment'] or 0)}
                    for t in timeline
                ],
                "countryFraming": country_framing,
                "relatedConcepts": get_concepts_for_theme(theme_code)
            }
    except Exception as e:
        print(f"Error in theme endpoint: {e}")
        import traceback
        traceback.print_exc()
        return {
            "theme": theme_code,
            "country": country_code,
            "hours": hours,
            "total": 0,
            "avgSentiment": 0,
            "signals": [],
            "countryBreakdown": [],
            "relatedThemes": [],
            "topSources": [],
            "topPersons": [],
            "timeline": [],
            "countryFraming": [],
            "error": str(e)
        }


def _clean_theme_label(theme_code: str) -> str:
    """Convert theme code like WB_475_DIGITAL_GOVERNMENT to 'Digital Government'."""
    label = theme_code.upper()
    # Strip known prefixes
    prefixes = (
        "WB_", "TAX_", "GDELT_", "CRISISLEX_", "USPEC_", "UN_", 
        "SOC_", "ENV_", "ECON_", "EPU_", "MIL_", "CRIME_", "HEALTH_"
    )
    for prefix in prefixes:
        if label.startswith(prefix):
            # Also strip the numeric segment that follows e.g. WB_475_
            parts = label.split("_", 2)
            label = parts[-1] if len(parts) >= 2 else label
            break
    # Special cleanup for known redundant suffixes
    if label == "CRISISLEXREC":
        label = "CRISIS RECOVERY"
    
    # Remove any remaining leading numeric segment (e.g. "475_DIGITAL" → "DIGITAL")
    parts = label.split("_", 1)
    if parts[0].isdigit() and len(parts) == 2:
        label = parts[1]
    return label.replace("_", " ").title()


@router.get("/api/v2/theme/{theme_code}/insight")
async def get_theme_insight(
    theme_code: str,
    hours: int = Query(24, ge=1, le=8760),
):
    """
    Generate a 2-3 sentence AI meta-summary of HOW a topic is covered across
    global media. Describes observable coverage patterns only — never editorialises
    about the topic itself.

    Results are cached in Redis for 15 minutes (900 seconds).
    Falls back gracefully when ANTHROPIC_API_KEY is not set or the LLM call fails.
    """
    import math

    cache_key = f"insight:{theme_code.upper()}:{hours}"
    generated_at = datetime.now(timezone.utc).isoformat()

    # --- Cache check ---
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached_raw = await app.state.redis.get(cache_key)
            if cached_raw:
                cached_data = json.loads(cached_raw)
                cached_data["cached"] = True
                return cached_data
        except Exception:
            pass  # Redis hiccup — proceed without cache

    # --- Lightweight DB queries ---
    tc = theme_code.upper()
    try:
        async with db.pool.acquire() as conn:
            # Aggregate stats
            stats_row = await conn.fetchrow(
                f"""
                SELECT
                    COUNT(*)                          AS total_signals,
                    COUNT(DISTINCT country_code)      AS country_count,
                    COUNT(DISTINCT source_name)       AS source_count,
                    AVG(sentiment)                    AS global_sentiment
                FROM signals_v2
                WHERE $1 = ANY(themes)
                  AND timestamp > NOW() - INTERVAL '{hours} hours'
                """,
                tc,
            )

            # Top 5 countries by volume
            country_rows = await conn.fetch(
                f"""
                SELECT country_code, COUNT(*) AS cnt, AVG(sentiment) AS avg_sent
                FROM signals_v2
                WHERE $1 = ANY(themes)
                  AND timestamp > NOW() - INTERVAL '{hours} hours'
                GROUP BY country_code
                ORDER BY cnt DESC
                LIMIT 5
                """,
                tc,
            )

            # Volume trend: last 6h vs previous 6h
            trend_row = await conn.fetchrow(
                """
                SELECT
                    SUM(CASE WHEN timestamp > NOW() - INTERVAL '6 hours' THEN 1 ELSE 0 END)          AS recent,
                    SUM(CASE WHEN timestamp BETWEEN NOW() - INTERVAL '12 hours'
                                             AND NOW() - INTERVAL '6 hours'  THEN 1 ELSE 0 END)     AS previous
                FROM signals_v2
                WHERE $1 = ANY(themes)
                  AND timestamp > NOW() - INTERVAL '12 hours'
                """,
                tc,
            )
    except Exception as db_err:
        return {
            "theme": theme_code.upper(),
            "insight": None,
            "error": "db_error",
            "detail": str(db_err),
            "data_points": {},
            "generated_at": generated_at,
        }

    total_signals = int(stats_row["total_signals"] or 0)
    country_count = int(stats_row["country_count"] or 0)
    source_count = int(stats_row["source_count"] or 0)
    global_sentiment = float(stats_row["global_sentiment"] or 0.0)

    data_points = {
        "total_signals": total_signals,
        "country_count": country_count,
        "source_count": source_count,
    }

    # Format top countries string
    top_countries_parts = []
    for r in country_rows:
        cc = r["country_code"] or "??"
        cnt = int(r["cnt"])
        avg_s = float(r["avg_sent"] or 0.0)
        top_countries_parts.append(f"{cc} ({cnt} signals, {avg_s:+.1f} tone)")
    top_countries_formatted = ", ".join(top_countries_parts) if top_countries_parts else "N/A"

    # Trend description
    recent = int(trend_row["recent"] or 0)
    previous = int(trend_row["previous"] or 0)
    if previous == 0:
        trend_description = "accelerating (no data in previous 6h)" if recent > 0 else "no recent activity"
    else:
        ratio = recent / previous
        if ratio >= 1.5:
            trend_description = f"accelerating ({ratio:.1f}x vs previous 6h)"
        elif ratio <= 0.5:
            trend_description = f"declining ({ratio:.1f}x vs previous 6h)"
        else:
            trend_description = "stable"

    # --- LLM call ---
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    insight_provider = os.getenv("INSIGHT_PROVIDER", "anthropic").lower()
    theme_label = _clean_theme_label(theme_code)

    user_prompt = (
        f'Analyze the global media coverage for the topic "{theme_label}" over the last {hours} hours.\n\n'
        f"Data points to weave into your summary:\n"
        f"- Total volume: {total_signals} articles across {country_count} countries.\n"
        f"- Number of distinct sources: {source_count}\n"
        f"- Overall global tone (sentiment): {global_sentiment:+.1f} (where negative is bad/pessimistic, positive is good/optimistic)\n"
        f"- Key countries driving the coverage (with their specific tone): {top_countries_formatted}\n"
        f"- Current momentum: {trend_description}\n\n"
        "Write your 2-3 sentence summary now."
    )

    system_prompt = (
        "You are an intelligence analyst summarizing global media trends.\n"
        "Your goal is to provide a clear, concise, and highly readable summary of how a topic is being covered globally.\n"
        "Rules:\n"
        "1. Never use raw database taxonomy names (e.g., if the topic is 'Crisislex Crisislexrec', translate it naturally to 'crisis events' or 'emergencies').\n"
        "2. Do not write like a robot listing statistics. Weave the data (countries, sentiment, volume) into a fluid, human-readable narrative.\n"
        "3. Highlight interesting contrasts (e.g., if sentiment is negative in Russia but positive in the US, mention the regional split naturally).\n"
        "4. Keep it exactly 2-3 sentences. Be insightful, engaging, and professional.\n"
        "5. Never use em-dashes (—) or en-dashes. Rephrase with commas or separate sentences."
    )

    insight_text: Optional[str] = None

    # Ollama fallback path (optional, environment-controlled)
    if insight_provider == "ollama":
        ollama_host = os.getenv("OLLAMA_HOST")
        if ollama_host:
            try:
                ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        f"{ollama_host.rstrip('/')}/api/chat",
                        json={
                            "model": ollama_model,
                            "stream": False,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                        },
                    )
                    resp.raise_for_status()
                    insight_text = resp.json()["message"]["content"].strip()
            except Exception as ollama_err:
                print(f"[insight] Ollama call failed: {ollama_err}")

    # Anthropic (Claude Haiku) — primary path
    if insight_text is None and anthropic_key:
        try:
            import anthropic

            async_client = anthropic.AsyncAnthropic(api_key=anthropic_key)
            response = await async_client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=256,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            insight_text = next(
                (block.text for block in response.content if block.type == "text"),
                None,
            )
        except Exception as llm_err:
            err_msg = str(llm_err)
            print(f"[insight] Claude Haiku call failed: {err_msg}")
            error_code = "insight_no_credits" if "credit balance" in err_msg.lower() else "insight_unavailable"
            return {
                "theme": theme_code.upper(),
                "insight": None,
                "error": error_code,
                "data_points": data_points,
                "generated_at": generated_at,
            }

    if insight_text is None:
        # API key missing or provider skipped — return graceful fallback
        return {
            "theme": theme_code.upper(),
            "insight": None,
            "error": "insight_unavailable",
            "data_points": data_points,
            "generated_at": generated_at,
        }

    result = {
        "theme": theme_code.upper(),
        "insight": insight_text,
        "data_points": data_points,
        "cached": False,
        "generated_at": generated_at,
    }

    # --- Cache the result ---
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            await app.state.redis.setex(cache_key, 900, json.dumps(result))
        except Exception:
            pass  # Best-effort caching

    return result


@router.get("/api/v2/theme/{theme_code}/spikes")
async def get_theme_spikes(
    theme_code: str,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(3, ge=1, le=10),
):
    """
    Return the top spike moments for a theme in the last N hours.
    Each spike includes the hour, signal count, % delta from prior hour,
    and the single article that contributed most (trigger event).
    Used to annotate NarrativeThreads sparklines.
    """
    import json as _json, traceback

    cache_key = f"spikes:{theme_code}:{hours}:{limit}"
    if hasattr(app.state, "redis") and app.state.redis:
        try:
            cached = await app.state.redis.get(cache_key)
            if cached:
                return _json.loads(cached)
        except Exception:
            pass

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 10000")

            # Hourly counts for this theme
            hourly = await conn.fetch("""
                SELECT
                    date_trunc('hour', timestamp) AS hour,
                    COUNT(*)                       AS count
                FROM signals_v2
                WHERE timestamp > NOW() - ($2 || ' hours')::INTERVAL
                  AND themes IS NOT NULL
                  AND $1 = ANY(themes)
                GROUP BY 1
                ORDER BY 1
            """, theme_code, str(hours))

            if len(hourly) < 2:
                return {"theme_code": theme_code, "spikes": []}

            # Compute delta vs previous hour; rank by absolute delta
            rows_with_delta = []
            for i in range(1, len(hourly)):
                prev = hourly[i - 1]["count"]
                curr = hourly[i]["count"]
                if prev > 0:
                    delta_pct = round((curr - prev) / prev * 100, 1)
                else:
                    delta_pct = 100.0 if curr > 0 else 0.0
                rows_with_delta.append({
                    "hour": hourly[i]["hour"],
                    "count": curr,
                    "prev_count": prev,
                    "delta_pct": delta_pct,
                })

            # Top spikes by absolute delta_pct (only positive — accelerating moments)
            top_spikes = sorted(
                [r for r in rows_with_delta if r["delta_pct"] > 0],
                key=lambda r: r["delta_pct"],
                reverse=True,
            )[:limit]

            # For each spike hour, find the single article with the most mentions
            # as a proxy for the trigger event
            spikes = []
            for spike in top_spikes:
                trigger = await conn.fetchrow("""
                    SELECT source_url AS url, source_name AS source, country_code, sentiment
                    FROM signals_v2
                    WHERE timestamp >= $1
                      AND timestamp < $1 + INTERVAL '1 hour'
                      AND themes IS NOT NULL
                      AND $2 = ANY(themes)
                      AND source_url IS NOT NULL
                    ORDER BY timestamp ASC
                    LIMIT 1
                """, spike["hour"], theme_code)

                spikes.append({
                    "hour": spike["hour"].isoformat(),
                    "count": spike["count"],
                    "prev_count": spike["prev_count"],
                    "delta_pct": spike["delta_pct"],
                    "trigger": {
                        "url": trigger["url"],
                        "source": trigger["source"],
                        "country_code": trigger["country_code"],
                        "sentiment": round(float(trigger["sentiment"] or 0), 3),
                    } if trigger else None,
                })

            result = {
                "theme_code": theme_code,
                "hours": hours,
                "spikes": spikes,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            if hasattr(app.state, "redis") and app.state.redis:
                try:
                    await app.state.redis.setex(cache_key, 300, _json.dumps(result, default=str))
                except Exception:
                    pass

            return result

    except Exception as e:
        traceback.print_exc()
        return {"theme_code": theme_code, "spikes": [], "error": str(e)}
