"""
ReliefWeb RSS Ingestion Service — Wave 2

Fetches OCHA/ReliefWeb country-specific RSS feeds for the top humanitarian
crisis zones. ReliefWeb's geographic tagging is OCHA-curated and highly
reliable (geo_confidence=0.92), making these signals significantly more
precise than GDELT's keyword-based geo extraction.

API note: ReliefWeb v2 API requires an approved appname. We use their
public RSS feeds instead — no auth required, equivalent content.

Runs every 4 GDELT cycles (~60 min) via ingest_loop.py.
"""
import asyncio
import asyncpg
import aiohttp
import feedparser
import logging
import os
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse
from typing import Optional

from app.config.source_blocklist import is_blocked
from app.services.signal_text import clean_snippet

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable",
)

# ── Crisis country feeds ───────────────────────────────────────────────────────
# Maps ISO3 path slug → ISO2 country code
# Covers all countries rated "Crisis" or "Emergency" in IPC/OCHA classifications
# as of 2026-05. URL: https://reliefweb.int/country/{iso3}/rss.xml
_CRISIS_FEEDS: dict[str, str] = {
    # Conflict zones with active hostilities
    "pse": "GZ",  # occupied Palestinian territory (Gaza + West Bank)
    "yem": "YE",  # Yemen — Houthi conflict, humanitarian crisis
    "sdn": "SD",  # Sudan — RSF/SAF war, Darfur collapse
    "ssd": "SS",  # South Sudan — inter-communal violence
    "mmr": "MM",  # Myanmar — military junta crackdown
    "som": "SO",  # Somalia — Al-Shabaab + drought
    "lby": "LY",  # Libya — ongoing factional conflict
    "afg": "AF",  # Afghanistan — Taliban humanitarian collapse
    "caf": "CF",  # Central African Republic — armed groups
    "cod": "CD",  # DR Congo — M23, eastern conflict
    "mli": "ML",  # Mali — Sahel instability
    "bfa": "BF",  # Burkina Faso — jihadist insurgency
    # Acute humanitarian crises (food/displacement)
    "hti": "HT",  # Haiti — gang control, state collapse
    "eth": "ET",  # Ethiopia — Tigray aftermath, Amhara
    "syr": "SY",  # Syria — ongoing displacement
    # Active geopolitical flashpoints
    "ukr": "UA",  # Ukraine — war with Russia
    "irq": "IQ",  # Iraq — PMF/instability
    "lbn": "LB",  # Lebanon — post-war reconstruction
    "pak": "PK",  # Pakistan — displacement, floods
}

# Additional thematic feeds (no country-specific ISO2 — use keyword extraction fallback)
_THEMATIC_FEEDS: list[tuple[str, str]] = [
    ("reliefweb_disasters", "https://reliefweb.int/updates/rss.xml?legacy-river=disasters"),
]

# ReliefWeb redirects /country/{iso3}/rss.xml → /updates/rss.xml?legacy-river=country/{iso3}
# Use direct URL to avoid bot-detection trigger on the redirect chain.
_RW_BASE = "https://reliefweb.int/updates/rss.xml?legacy-river=country/{iso3}"

# Browser-like headers — ReliefWeb blocks minimal UA strings as bots
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
}


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def parse_entry_time(entry) -> datetime:
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except (TypeError, ValueError):
                pass
    return datetime.now(timezone.utc)


# ── Feed fetcher ──────────────────────────────────────────────────────────────

async def fetch_reliefweb_feed(
    session: aiohttp.ClientSession,
    feed_name: str,
    url: str,
    country_code: Optional[str],
    since: datetime,
) -> list[dict]:
    """Fetch one ReliefWeb RSS feed and return normalized signal dicts."""
    signals = []
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=30),
            allow_redirects=True,
            headers=_HEADERS,
        ) as resp:
            if resp.status != 200:
                logger.warning("[RW] %s returned HTTP %d", feed_name, resp.status)
                return signals
            content = await resp.text()

        feed = feedparser.parse(content)
        if feed.bozo and not feed.entries:
            logger.warning("[RW] parse error %s: %s", feed_name, feed.bozo_exception)
            return signals

        for entry in feed.entries:
            pub_time = parse_entry_time(entry)
            if pub_time <= since:
                continue

            article_url = entry.get("link", "")
            if not article_url or is_blocked(article_url):
                continue

            title = (entry.get("title") or "")[:500]
            raw_summary = entry.get("summary") or entry.get("description") or ""
            snippet = strip_html(raw_summary)[:500]

            # Country code: use feed's country if known (high confidence),
            # else try to extract from title/snippet via description tags
            resolved_country = country_code
            if not resolved_country:
                # Thematic feeds: extract country from description HTML tags
                # ReliefWeb embeds <div class="tag country">Country: X</div>
                m = re.search(r'Country:\s*([^<\n]+)', raw_summary)
                if m:
                    resolved_country = _COUNTRY_NAME_TO_ISO2.get(m.group(1).strip().lower())

            if not resolved_country:
                continue  # Skip if we can't resolve a country

            domain = urlparse(article_url).netloc.lower().removeprefix("www.")

            signals.append({
                "timestamp": pub_time,
                "country_code": resolved_country,
                "latitude": None,
                "longitude": None,
                "sentiment": 0.0,        # NLP pipeline Wave 4 will enrich
                "source_url": article_url,
                "source_name": domain,
                "headline": title or None,
                "themes": [],
                "persons": [],
                "is_crisis": True,       # All ReliefWeb content is humanitarian/crisis
                "crisis_score": 0.5,     # Conservative default; NLP will refine
                "crisis_themes": ["HUMANITARIAN"],
                "severity": "medium",
                "event_type": "humanitarian",
                # Provenance — OCHA-curated geographic tagging is highly reliable
                "source_family": "ngo",
                "source_lang": "en",
                "geo_confidence": 0.92,
                "attribution_method": "reliefweb_rss",
                "is_state_media": False,
                # Semantic class (migration 021) — all ReliefWeb is humanitarian
                "signal_class": "humanitarian",
                "snippet": clean_snippet(snippet),
            })

    except aiohttp.ClientError as e:
        logger.warning("[RW] network error %s: %s", feed_name, e)
    except Exception as e:
        logger.error("[RW] unexpected error %s: %s", feed_name, e)

    return signals


# ── Country name → ISO2 for thematic feed extraction ─────────────────────────
_COUNTRY_NAME_TO_ISO2: dict[str, str] = {
    "afghanistan": "AF",
    "burkina faso": "BF",
    "central african republic": "CF",
    "democratic republic of the congo": "CD",
    "dr congo": "CD",
    "ethiopia": "ET",
    "haiti": "HT",
    "iraq": "IQ",
    "lebanon": "LB",
    "libya": "LY",
    "mali": "ML",
    "myanmar": "MM",
    "occupied palestinian territory": "GZ",
    "opt": "GZ",
    "pakistan": "PK",
    "somalia": "SO",
    "south sudan": "SS",
    "sudan": "SD",
    "syria": "SY",
    "ukraine": "UA",
    "yemen": "YE",
}


# ── DB writer ─────────────────────────────────────────────────────────────────

async def insert_reliefweb_signals(pool: asyncpg.Pool, signals: list[dict]) -> int:
    if not signals:
        return 0
    upserted = 0
    async with pool.acquire() as conn:
        for s in signals:
            try:
                result = await conn.execute(
                    """
                    INSERT INTO signals_v2 (
                        timestamp, country_code, latitude, longitude, sentiment,
                        source_url, source_name, headline, themes, persons,
                        is_crisis, crisis_score, crisis_themes, severity, event_type,
                        source_family, source_lang, geo_confidence, attribution_method, is_state_media,
                        signal_class, snippet
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                            $16,$17,$18,$19,$20,$21,$22)
                    ON CONFLICT (source_url) WHERE source_url IS NOT NULL DO UPDATE SET
                        country_code = EXCLUDED.country_code,
                        source_name = EXCLUDED.source_name,
                        is_crisis = TRUE,
                        crisis_score = GREATEST(
                            COALESCE(signals_v2.crisis_score, 0),
                            EXCLUDED.crisis_score
                        ),
                        crisis_themes = EXCLUDED.crisis_themes,
                        severity = EXCLUDED.severity,
                        event_type = EXCLUDED.event_type,
                        source_family = EXCLUDED.source_family,
                        source_lang = COALESCE(signals_v2.source_lang, EXCLUDED.source_lang),
                        geo_confidence = GREATEST(
                            COALESCE(signals_v2.geo_confidence, 0),
                            EXCLUDED.geo_confidence
                        ),
                        attribution_method = EXCLUDED.attribution_method,
                        is_state_media = FALSE,
                        signal_class = EXCLUDED.signal_class
                    """,
                    s["timestamp"], s["country_code"], s["latitude"], s["longitude"],
                    s["sentiment"], s["source_url"], s["source_name"], s["headline"],
                    s["themes"], s["persons"],
                    s["is_crisis"], s["crisis_score"], s["crisis_themes"],
                    s["severity"], s["event_type"],
                    s["source_family"], s["source_lang"], s["geo_confidence"],
                    s["attribution_method"], s["is_state_media"],
                    s.get("signal_class", "humanitarian"),
                    s.get("snippet"),
                )
                if result in {"INSERT 0 1", "UPDATE 1"}:
                    upserted += 1
            except Exception as e:
                logger.warning("[RW] insert error: %s: %s", type(e).__name__, str(e)[:120])
    return upserted


# ── Main entry point ──────────────────────────────────────────────────────────

# ── Official ReliefWeb API (#180, 2026-07-06) ──────────────────────────────
# RSS-from-Fly gets an empty HTTP 202 (WAF/CDN edge). The JSON API is the
# structured path (ISO3 country, no HTML scraping). MEASURED 2026-07-06:
# v1 is DECOMMISSIONED (410) and v2 now REQUIRES AN APPROVED APPNAME (403,
# registration at apidoc.reliefweb.int/parameters#appname) — an institutional
# gate, same class as #46 ACLED, not a code fix. This path is v2-ready; set
# ATLAS_RELIEFWEB_APPNAME once approved to activate it. Until then the lane
# serves 0 (honest) — better than the RSS 202 that pretended to work.
_RW_API = "https://api.reliefweb.int/v2/reports"
from app.core.iso3_map import ISO3_TO_ISO2 as _ISO3_TO_ISO2


async def fetch_reliefweb_api(
    session: aiohttp.ClientSession, since: datetime, limit: int = 200,
) -> list[dict]:
    """Fetch recent reports via the official API. ISO3 → ISO2 via the country
    field's `iso3`; degrades to [] on any error (honest gap, never raises)."""
    signals: list[dict] = []
    appname = os.environ.get("ATLAS_RELIEFWEB_APPNAME")
    if not appname:
        logger.info("[RW] API path idle — no approved appname "
                    "(set ATLAS_RELIEFWEB_APPNAME after registration)")
        return signals
    payload = {
        "filter": {"field": "date.created",
                   "value": {"from": since.strftime("%Y-%m-%dT%H:%M:%S+00:00")}},
        "fields": {"include": ["title", "url", "date.created",
                               "primary_country.iso3", "primary_country.name",
                               "source.shortname", "body-html"]},
        "sort": ["date.created:desc"],
        "limit": limit,
    }
    try:
        async with session.post(
            _RW_API, json=payload, headers=_HEADERS,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            if resp.status != 200:
                logger.warning("[RW] API returned HTTP %d", resp.status)
                return signals
            data = await resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("[RW] API fetch failed: %s", exc)
        return signals

    for item in data.get("data", []):
        f = item.get("fields", {})
        pc = f.get("primary_country") or {}
        iso3 = (pc.get("iso3") or "").upper()
        iso2 = _ISO3_TO_ISO2.get(iso3)
        if not iso2:
            continue
        url = f.get("url") or ""
        if not url or is_blocked(url):
            continue
        created = f.get("date", {}).get("created")
        try:
            pub = datetime.fromisoformat(created.replace("Z", "+00:00")) \
                if created else datetime.now(timezone.utc)
        except (ValueError, AttributeError):
            pub = datetime.now(timezone.utc)
        if pub <= since:
            continue
        title = (f.get("title") or "")[:500]
        snippet = strip_html(f.get("body-html") or "")[:500]
        signals.append({
            "timestamp": pub, "country_code": iso2,
            "latitude": None, "longitude": None, "sentiment": 0.0,
            "source_url": url,
            "source_name": urlparse(url).netloc.lower().removeprefix("www."),
            "headline": title or None, "themes": [], "persons": [],
            "is_crisis": True, "crisis_score": 0.5,
            "crisis_themes": ["HUMANITARIAN"], "severity": "medium",
            "event_type": "humanitarian", "source_family": "ngo",
            "source_lang": "en", "geo_confidence": 0.92,
            "attribution_method": "reliefweb_api", "is_state_media": False,
            "signal_class": "humanitarian", "snippet": clean_snippet(snippet),
        })
    return signals


async def run_reliefweb_ingestion() -> None:
    """Fetch ReliefWeb reports and insert new signals. Called by ingest_loop.py.

    Primary path = the official JSON API (#180). The legacy RSS feeds stay as
    an env-gated fallback (ATLAS_RELIEFWEB_RSS_FALLBACK=on) in case the API
    ever regresses; default is API-only."""
    since = datetime.now(timezone.utc) - timedelta(hours=4)  # wider window — reports are slower

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    try:
        async with aiohttp.ClientSession() as session:
            api_signals = await fetch_reliefweb_api(session, since)
            n = await insert_reliefweb_signals(pool, api_signals) if api_signals else 0
            logger.info("[RW] API: %d fetched → %d upserted", len(api_signals), n)
            if os.environ.get("ATLAS_RELIEFWEB_RSS_FALLBACK", "").lower() in {"1", "true", "on"}:
                await _run_rss_fallback(session, pool, since)
    finally:
        await pool.close()


async def _run_rss_fallback(session, pool, since) -> None:
    """Legacy RSS path (kept for regression insurance; off by default)."""
    for iso3, iso2 in _CRISIS_FEEDS.items():
        signals = await fetch_reliefweb_feed(
            session, f"reliefweb_{iso3}", _RW_BASE.format(iso3=iso3), iso2, since)
        if signals:
            await insert_reliefweb_signals(pool, signals)
    for feed_name, feed_url in _THEMATIC_FEEDS:
        signals = await fetch_reliefweb_feed(session, feed_name, feed_url, None, since)
        if signals:
            await insert_reliefweb_signals(pool, signals)


if __name__ == "__main__":
    asyncio.run(run_reliefweb_ingestion())
