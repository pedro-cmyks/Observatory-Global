from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from app import db

router = APIRouter()

@router.get("/api/v2/wiki/top")
async def get_wiki_top_articles(
    country_code: Optional[str] = Query(None, description="ISO 2-letter country code"),
    days: int = Query(1, ge=1, le=7),
    limit: int = Query(15, ge=1, le=50)
):
    """Get top Wikipedia articles by pageviews for a country or globally."""
    try:
        async with db.pool.acquire() as conn:
            if country_code:
                rows = await conn.fetch("""
                    SELECT article_title, views, rank, language, fetch_date
                    FROM wiki_pageviews_v2
                    WHERE country_code = $1
                    AND fetch_date >= CURRENT_DATE - $2::int
                    ORDER BY views DESC
                    LIMIT $3
                """, country_code.upper(), days, limit)
            else:
                # Global aggregate: sum views across all countries
                rows = await conn.fetch("""
                    SELECT article_title, SUM(views) as views, MIN(rank) as rank,
                           COUNT(DISTINCT country_code) as country_count
                    FROM wiki_pageviews_v2
                    WHERE fetch_date >= CURRENT_DATE - $1::int
                    GROUP BY article_title
                    ORDER BY views DESC
                    LIMIT $2
                """, days, limit)

            return {
                "articles": [
                    {
                        "title": r['article_title'],
                        "views": r['views'],
                        "rank": r['rank'],
                        "language": r.get('language'),
                        "country_count": r.get('country_count'),
                    }
                    for r in rows
                ],
                "country_code": country_code,
                "days": days,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
    except Exception as e:
        return {"articles": [], "error": str(e)}


@router.get("/api/v2/wiki/match")
async def get_wiki_theme_match(
    theme: str = Query(..., description="GDELT theme code to check against Wikipedia activity"),
    days: int = Query(1, ge=1, le=7)
):
    """Check if a GDELT theme matches any spiking Wikipedia articles.
    Returns matching articles and view counts — useful for 'wiki activity' badges.
    """
    from app.core.gdelt_taxonomy import get_theme_label

    label = get_theme_label(theme).lower()
    theme_words = [w for w in label.split() if len(w) > 3]

    if not theme_words:
        return {"matches": [], "theme": theme, "has_wiki_activity": False}

    try:
        async with db.pool.acquire() as conn:
            conditions = " OR ".join([f"LOWER(article_title) LIKE '%' || ${i+1} || '%'" for i in range(len(theme_words))])
            query = f"""
                SELECT article_title, SUM(views) as views, COUNT(DISTINCT country_code) as country_count
                FROM wiki_pageviews_v2
                WHERE fetch_date >= CURRENT_DATE - ('{days} days')::INTERVAL
                AND ({conditions})
                GROUP BY article_title
                ORDER BY views DESC
                LIMIT 5
            """
            rows = await conn.fetch(query, *theme_words)

            matches = [
                {
                    "title": r['article_title'],
                    "views": r['views'],
                    "country_count": r['country_count'],
                }
                for r in rows
            ]

            return {
                "matches": matches,
                "theme": theme,
                "theme_label": get_theme_label(theme),
                "has_wiki_activity": len(matches) > 0,
                "total_views": sum(m['views'] for m in matches),
            }
    except Exception as e:
        return {"matches": [], "theme": theme, "has_wiki_activity": False, "error": str(e)}


# =============================================================================
# GDELT EVENTS API
# =============================================================================
