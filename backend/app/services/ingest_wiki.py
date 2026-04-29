"""
Wikipedia Pageviews Ingestion Service for V2 Schema.
Fetches top-viewed Wikipedia articles per country/language
and inserts into wiki_pageviews_v2 table.

Runs once daily (Wikipedia data has 24h delay).
"""
import asyncio
import asyncpg
import httpx
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable")

# Countries mapped to Wikipedia language editions
COUNTRY_WIKI_MAP = {
    "US": ("en.wikipedia", "en"),
    "GB": ("en.wikipedia", "en"),
    "IN": ("en.wikipedia", "en"),
    "ES": ("es.wikipedia", "es"),
    "CO": ("es.wikipedia", "es"),
    "MX": ("es.wikipedia", "es"),
    "AR": ("es.wikipedia", "es"),
    "BR": ("pt.wikipedia", "pt"),
    "FR": ("fr.wikipedia", "fr"),
    "DE": ("de.wikipedia", "de"),
    "IT": ("it.wikipedia", "it"),
    "JP": ("ja.wikipedia", "ja"),
    "KR": ("ko.wikipedia", "ko"),
    "CN": ("zh.wikipedia", "zh"),
    "RU": ("ru.wikipedia", "ru"),
    "TR": ("tr.wikipedia", "tr"),
    "UA": ("uk.wikipedia", "uk"),
}

# Meta/special pages to filter out
WIKI_SKIP_TITLES = {
    "Main_Page", "Special:Search", "Wikipedia:Main_Page",
    "-", "Página_principal", "メインページ", "Заглавная_страница",
    "Portada", "Hauptseite", "Pagina_principale", "위키백과:대문",
}

BASE_URL = "https://wikimedia.org/api/rest_v1"


async def fetch_wiki_top_articles(project: str, language: str, country_code: str) -> list[dict]:
    """Fetch top-viewed Wikipedia articles for a project."""
    yesterday = datetime.utcnow() - timedelta(days=1)
    date_str = yesterday.strftime("%Y/%m/%d")
    url = f"{BASE_URL}/metrics/pageviews/top/{project}/all-access/{date_str}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, headers={
                "User-Agent": "ObservatoryGlobal/2.0 (atlas@observatory.dev)"
            })
            response.raise_for_status()
            data = response.json()

            articles = data.get("items", [{}])[0].get("articles", [])
            results = []
            rank = 0

            for article in articles:
                title = article.get("article", "")
                views = article.get("views", 0)

                # Skip meta pages and very short titles
                if not title or title in WIKI_SKIP_TITLES:
                    continue
                if title.startswith("Special:") or title.startswith("Wikipedia:"):
                    continue
                if title.startswith("Especial:") or title.startswith("Spezial:"):
                    continue

                rank += 1
                if rank > 25:  # Top 25 per country
                    break

                results.append({
                    "fetch_date": yesterday.date(),
                    "country_code": country_code,
                    "language": language,
                    "article_title": title.replace("_", " "),
                    "views": views,
                    "rank": rank,
                })

            logger.info(f"[Wiki] {country_code} ({project}): fetched {len(results)} top articles")
            return results

    except Exception as e:
        logger.warning(f"[Wiki] {country_code} ({project}) failed: {e}")
        return []


async def insert_wiki_pageviews(pool: asyncpg.Pool, articles: list[dict]) -> int:
    """Insert Wikipedia pageview data into wiki_pageviews_v2 table."""
    if not articles:
        return 0

    inserted = 0
    async with pool.acquire() as conn:
        for a in articles:
            try:
                await conn.execute("""
                    INSERT INTO wiki_pageviews_v2 (fetch_date, country_code, language, article_title, views, rank)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    ON CONFLICT (fetch_date, country_code, article_title) DO UPDATE
                    SET views = EXCLUDED.views, rank = EXCLUDED.rank
                """,
                    a['fetch_date'],
                    a['country_code'],
                    a['language'],
                    a['article_title'],
                    a['views'],
                    a['rank']
                )
                inserted += 1
            except Exception as e:
                logger.debug(f"[Wiki] Insert error: {e}")
                continue

    return inserted


async def run_wiki_ingestion():
    """Main Wikipedia pageviews ingestion function."""
    logger.info(f"[{datetime.now()}] Starting Wikipedia pageviews ingestion...")

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=1)

    try:
        # Deduplicate by project — don't fetch en.wikipedia twice for US and GB
        seen_projects = set()
        all_articles = []

        for country_code, (project, language) in COUNTRY_WIKI_MAP.items():
            if project in seen_projects:
                # Reuse results from first fetch for this project
                # but tag with the new country_code
                existing = [a for a in all_articles if a['language'] == language]
                for a in existing[:25]:
                    dup = dict(a)
                    dup['country_code'] = country_code
                    all_articles.append(dup)
                logger.info(f"[Wiki] {country_code}: reused {project} data ({len(existing)} articles)")
                continue

            seen_projects.add(project)
            articles = await fetch_wiki_top_articles(project, language, country_code)
            all_articles.extend(articles)
            await asyncio.sleep(1)  # Be nice to Wikimedia API

        if all_articles:
            inserted = await insert_wiki_pageviews(pool, all_articles)
            logger.info(f"[Wiki] Inserted {inserted} pageview records")
        else:
            logger.warning("[Wiki] No pageview data fetched")

        # Stats
        async with pool.acquire() as conn:
            count = await conn.fetchval("SELECT COUNT(*) FROM wiki_pageviews_v2")
            logger.info(f"[Wiki] Total records in wiki_pageviews_v2: {count}")

    finally:
        await pool.close()

    logger.info(f"[{datetime.now()}] Wikipedia pageviews ingestion complete!")


if __name__ == "__main__":
    asyncio.run(run_wiki_ingestion())
