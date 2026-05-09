"""
RSS Feed Ingestion Service — Wave 1

Ingests curated international RSS feeds targeting coverage gaps found in
the 2026-05-08 investigation: maritime/chokepoints, Middle East, Russia
independent, humanitarian, Asia, Africa/LatAm.

Each feed is tagged with source provenance (migration 008 fields).
Country extraction uses title/snippet keyword matching as a lightweight
fallback when GDELT geographic NLP isn't available.

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
from typing import Optional
from urllib.parse import urlparse

from app.config.source_blocklist import is_blocked

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable",
)

# ── Curated feed registry ─────────────────────────────────────────────────────
# Format: name → (url, source_family, source_country, source_lang, is_state_media)
# source_country = ISO2 of the outlet's home country (not the story's country)
CURATED_FEEDS: dict[str, tuple[str, str, str, str, bool]] = {
    # MARITIME / CHOKEPOINTS — fills Hormuz/shipping blind spot
    "gcaptain": (
        "https://gcaptain.com/feed/",
        "independent", "US", "en", False,
    ),
    "splash247": (
        "https://splash247.com/feed/",
        "independent", "GB", "en", False,
    ),
    # MIDDLE EAST / IRAN
    "aljazeera_en": (
        "https://www.aljazeera.com/xml/rss/all.xml",
        "wire", "QA", "en", False,
    ),
    "middle_east_eye": (
        "https://www.middleeasteye.net/rss",
        "independent", "GB", "en", False,
    ),
    "al_monitor": (
        "https://www.al-monitor.com/rss.xml",
        "independent", "US", "en", False,
    ),
    # RUSSIA — independent perspective
    "meduza_en": (
        "https://meduza.io/rss/en/all",
        "independent", "LV", "en", False,
    ),
    "rferl": (
        "https://www.rferl.org/api/zrqrjmter",
        "wire", "US", "en", False,
    ),
    # ASIA
    "scmp": (
        "https://www.scmp.com/rss/91/feed",
        "independent", "HK", "en", False,
    ),
    "dawn_pk": (
        "https://www.dawn.com/feeds/home",
        "independent", "PK", "en", False,
    ),
    "the_hindu": (
        "https://www.thehindu.com/feeder/default.rss",
        "independent", "IN", "en", False,
    ),
    # HUMANITARIAN — fills Gaza/Somalia/Yemen blind spot
    "un_news": (
        "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
        "ngo", "UN", "en", False,
    ),
    "msf_news": (
        "https://www.msf.org/news/rss.xml",
        "ngo", "CH", "en", False,
    ),
    # AFRICA / LATAM
    "africa_report": (
        "https://www.theafricareport.com/feed/",
        "independent", "FR", "en", False,
    ),
    "allafrica": (
        "https://allafrica.com/tools/headlines/rdf.xml",
        "wire", "ZA", "en", False,
    ),
    # ── WAVE 3: STATE MEDIA (is_state_media=True) ─────────────────────────────
    # Russian state media — essential for tracking Kremlin narrative framing
    "rt_en": (
        "https://www.rt.com/rss/news/",
        "state", "RU", "en", True,
    ),
    "rt_arabic": (
        "https://arabic.rt.com/rss/",
        "state", "RU", "ar", True,
    ),
    "sputnik_en": (
        "https://sputnikglobe.com/export/rss2/archive/index.xml",
        "state", "RU", "en", True,
    ),
    # Chinese state media — covers Belt & Road, Taiwan framing, trade wars
    # (CGTN world RSS stale since Apr 2026; Xinhua RSS abandoned since 2018)
    "global_times": (
        "https://www.globaltimes.cn/rss/outbrain.xml",
        "state", "CN", "en", True,
    ),
    # Iranian state media — covers Gulf, regional conflicts, nuclear program
    "irna_en": (
        "https://en.irna.ir/rss",
        "state", "IR", "en", True,
    ),
    # ── WAVE 3: NON-ENGLISH REGIONAL INDEPENDENTS ─────────────────────────────
    # Arabic-language coverage — Middle East from Arab perspective
    "france24_ar": (
        "https://www.france24.com/ar/rss",
        "wire", "FR", "ar", False,
    ),
    "bbc_arabic": (
        "https://www.bbc.co.uk/arabic/index.xml",
        "wire", "GB", "ar", False,
    ),
    # Spanish-language — Latin America coverage + Iberian perspective
    "france24_es": (
        "https://www.france24.com/es/rss",
        "wire", "FR", "es", False,
    ),
    "elpais_es": (
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "independent", "ES", "es", False,
    ),
    # German public broadcaster — European geopolitical angle
    "dw_en": (
        "https://rss.dw.com/xml/rss-en-all",
        "wire", "DE", "en", False,
    ),
}

# ── Lightweight country extractor ─────────────────────────────────────────────
# Maps country names/demonyms → ISO 3166-1 alpha-2.
# Covers the countries most likely to appear in the feeds above.
_COUNTRY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r'\biran\b|\bIranian\b|\bTehran\b|\bIRGC\b|\bKhamenei\b|\bAraghchi\b', re.I), "IR"),
    (re.compile(r'\bUkraine\b|\bUkrainian\b|\bKyiv\b|\bZelenskyy\b|\bZelenskiy\b', re.I), "UA"),
    (re.compile(r'\bRussia\b|\bRussian\b|\bMoscow\b|\bKremlin\b|\bPutin\b|\bRossiya\b', re.I), "RU"),
    (re.compile(r'\bGaza\b|\bPalestine\b|\bPalestinian\b|\bHamas\b|\bRafah\b|\bWest Bank\b', re.I), "GZ"),
    (re.compile(r'\bIsrael\b|\bIsraeli\b|\bTel Aviv\b|\bNetanyahu\b|\bIDF\b', re.I), "IL"),
    (re.compile(r'\bMyanmar\b|\bBurma\b|\bRangoon\b|\bNaypyidaw\b|\bTatmadaw\b|\bMilitary junta\b', re.I), "MM"),
    (re.compile(r'\bSomalia\b|\bSomali\b|\bMogadishu\b|\bAl-Shabaab\b', re.I), "SO"),
    (re.compile(r'\bYemen\b|\bYemeni\b|\bSanaa\b|\bHouthi\b|\bAden\b', re.I), "YE"),
    (re.compile(r'\bSudan\b|\bSudanese\b|\bKhartoum\b|\bDarfur\b|\bRSF\b', re.I), "SD"),
    (re.compile(r'\bAfghanistan\b|\bAfghan\b|\bKabul\b|\bTaliban\b', re.I), "AF"),
    (re.compile(r'\bPakistan\b|\bPakistani\b|\bIslamabad\b|\bKarachi\b|\bSharif\b', re.I), "PK"),
    (re.compile(r'\bIndia\b|\bIndian\b|\bNew Delhi\b|\bMumbai\b|\bModi\b', re.I), "IN"),
    (re.compile(r'\bChina\b|\bChinese\b|\bBeijing\b|\bShanghai\b|\bXi Jinping\b', re.I), "CN"),
    (re.compile(r'\bNorth Korea\b|\bNorth Korean\b|\bPyongyang\b|\bKim Jong\b', re.I), "KP"),
    (re.compile(r'\bSyria\b|\bSyrian\b|\bDamascus\b|\bAssad\b', re.I), "SY"),
    (re.compile(r'\bLebanon\b|\bLebanese\b|\bBeirut\b|\bHezbollah\b', re.I), "LB"),
    (re.compile(r'\bSaudi Arabia\b|\bSaudi\b|\bRiyadh\b|\bMBS\b', re.I), "SA"),
    (re.compile(r'\bIraq\b|\bIraqi\b|\bBaghdad\b|\bBasra\b', re.I), "IQ"),
    (re.compile(r'\bLibya\b|\bLibyan\b|\bTripoli\b|\bBenghazi\b', re.I), "LY"),
    (re.compile(r'\bEthiopia\b|\bEthiopian\b|\bAddis Ababa\b|\bTigray\b', re.I), "ET"),
    (re.compile(r'\bDR Congo\b|\bDRC\b|\bCongo\b|\bKinshasa\b|\bM23\b', re.I), "CD"),
    (re.compile(r'\bHaiti\b|\bHaitian\b|\bPort-au-Prince\b', re.I), "HT"),
    (re.compile(r'\bVenezuela\b|\bVenezuelan\b|\bCaracas\b|\bMaduro\b', re.I), "VE"),
    (re.compile(r'\bBrazil\b|\bBrazilian\b|\bBrasilia\b|\bLula\b|\bSão Paulo\b', re.I), "BR"),
    (re.compile(r'\bUnited States\b|\bAmerican\b|\bWashington\b|\bTrump\b|\bPentagon\b', re.I), "US"),
    (re.compile(r'\bUnited Kingdom\b|\bBritish\b|\bLondon\b|\bStarmer\b|\bDowning Street\b', re.I), "GB"),
    (re.compile(r'\bFrance\b|\bFrench\b|\bParis\b|\bMacron\b|\bElysée\b', re.I), "FR"),
    (re.compile(r'\bGermany\b|\bGerman\b|\bBerlin\b|\bBundestag\b', re.I), "DE"),
    (re.compile(r'\bStrait of Hormuz\b|\bHormuz\b|\bPersian Gulf\b|\bGulf of Oman\b', re.I), "IR"),
    (re.compile(r'\bRed Sea\b|\bGulf of Aden\b|\bBab el-Mandeb\b', re.I), "YE"),
    (re.compile(r'\bTaiwan\b|\bTaipei\b|\bTaiwanese\b', re.I), "TW"),
]


def extract_country(title: str, snippet: str) -> Optional[str]:
    """Return first ISO2 match found in title+snippet, or None."""
    text = f"{title} {snippet}"
    for pattern, iso2 in _COUNTRY_PATTERNS:
        if pattern.search(text):
            return iso2
    return None


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

async def fetch_feed(
    session: aiohttp.ClientSession,
    feed_name: str,
    url: str,
    source_family: str,
    source_country: str,
    source_lang: str,
    is_state_media: bool,
    since: datetime,
) -> list[dict]:
    """Fetch one RSS feed and return normalized signal dicts."""
    signals = []
    try:
        async with session.get(
            url,
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "Observatory-Global/1.0 RSS-Ingestor"},
        ) as resp:
            if resp.status != 200:
                logger.warning("[RSS] %s returned HTTP %d", feed_name, resp.status)
                return signals
            content = await resp.text()

        feed = feedparser.parse(content)
        if feed.bozo and not feed.entries:
            logger.warning("[RSS] parse error %s: %s", feed_name, feed.bozo_exception)
            return signals

        for entry in feed.entries:
            pub_time = parse_entry_time(entry)
            if pub_time <= since:
                continue

            url_str = entry.get("link", "")
            if not url_str or is_blocked(url_str):
                continue

            title = (entry.get("title") or "")[:500]
            snippet = strip_html(entry.get("summary") or entry.get("description") or "")[:500]

            country_code = extract_country(title, snippet) or source_country

            domain = urlparse(url_str).netloc.lower().removeprefix("www.")

            signals.append({
                "timestamp": pub_time,
                "country_code": country_code,
                "latitude": None,
                "longitude": None,
                "sentiment": 0.0,          # no tone available from RSS; NLP pipeline (Wave 4) fills this
                "source_url": url_str,
                "source_name": domain,
                "headline": title or None,
                "themes": [],              # theme extraction left to NLP pipeline
                "persons": [],
                "is_crisis": False,
                "crisis_score": 0.0,
                "crisis_themes": [],
                "severity": "low",
                "event_type": "other",
                # Provenance (migration 008)
                "source_family": source_family,
                "source_lang": source_lang,
                "geo_confidence": 0.6,     # RSS geo = keyword match, lower confidence than GDELT
                "attribution_method": "rss_feed",
                "is_state_media": is_state_media,
            })

    except aiohttp.ClientError as e:
        logger.warning("[RSS] network error %s: %s", feed_name, e)
    except Exception as e:
        logger.error("[RSS] unexpected error %s: %s", feed_name, e)

    return signals


# ── DB writer ─────────────────────────────────────────────────────────────────

async def insert_rss_signals(pool: asyncpg.Pool, signals: list[dict]) -> int:
    if not signals:
        return 0
    inserted = 0
    async with pool.acquire() as conn:
        for s in signals:
            try:
                result = await conn.execute(
                    """
                    INSERT INTO signals_v2 (
                        timestamp, country_code, latitude, longitude, sentiment,
                        source_url, source_name, headline, themes, persons,
                        is_crisis, crisis_score, crisis_themes, severity, event_type,
                        source_family, source_lang, geo_confidence, attribution_method, is_state_media
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                            $16,$17,$18,$19,$20)
                    ON CONFLICT (source_url) WHERE source_url IS NOT NULL DO NOTHING
                    """,
                    s["timestamp"], s["country_code"], s["latitude"], s["longitude"],
                    s["sentiment"], s["source_url"], s["source_name"], s["headline"],
                    s["themes"], s["persons"],
                    s["is_crisis"], s["crisis_score"], s["crisis_themes"],
                    s["severity"], s["event_type"],
                    s["source_family"], s["source_lang"], s["geo_confidence"],
                    s["attribution_method"], s["is_state_media"],
                )
                if result == "INSERT 0 1":
                    inserted += 1
            except Exception as e:
                logger.warning("[RSS] insert error: %s: %s", type(e).__name__, str(e)[:120])
    return inserted


# ── Main entry point ──────────────────────────────────────────────────────────

async def run_rss_ingestion() -> None:
    """Fetch all curated RSS feeds and insert new signals. Called by ingest_loop.py."""
    since = datetime.now(timezone.utc) - timedelta(hours=2)  # overlap window

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=2)
    total_inserted = 0
    total_fetched = 0

    try:
        async with aiohttp.ClientSession() as session:
            for feed_name, (url, source_family, source_country, source_lang, is_state) in CURATED_FEEDS.items():
                signals = await fetch_feed(
                    session, feed_name, url,
                    source_family, source_country, source_lang, is_state,
                    since,
                )
                total_fetched += len(signals)
                if signals:
                    n = await insert_rss_signals(pool, signals)
                    total_inserted += n
                    logger.info("[RSS] %s: %d fetched → %d inserted", feed_name, len(signals), n)

    finally:
        await pool.close()

    logger.info("[RSS] ingestion complete — %d fetched, %d new signals inserted", total_fetched, total_inserted)


if __name__ == "__main__":
    asyncio.run(run_rss_ingestion())
