"""
Structured disaster-event ingestion (event-source-evaluation §2).

Natural-hazard events GDELT CAMEO structurally cannot represent — an M7.8 quake,
a Category-4 cyclone, a volcanic eruption have no "actor" and no CAMEO action code.
Two authoritative, real-time, credential-free feeds:

  USGS FDSN  (earthquakes)   — https://earthquake.usgs.gov/fdsnws/event/1/query
                               GeoJSON, no key, per-event mag/lat/lon/depth/time/place.
  GDACS RSS  (multi-hazard)  — https://www.gdacs.org/xml/rss.xml
                               EU JRC, CC-BY, no key. EQ/TC/FL/WF/VO/DR + alert level.

Lands rows in `disaster_events_v2` (mig 062). Idempotent: ON CONFLICT (event_id) DO
UPDATE (feeds re-issue the same event as it develops — magnitude/alert refine).
The country is best-effort (name match against countries_v2 + US-state fallback);
NULL when unmapped — honest, and the geo-temporal binding simply won't fire for it.

Binding to disaster-category topics is a SEPARATE step (compute_event_movement, the
disaster path) — this module only ingests the authoritative event records.

Runs from ingest_loop on a slow cadence (hazards are lower-volume than news).
Kill-switch: DISASTER_INGEST_ENABLED=false.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta

import aiohttp
import asyncpg
import feedparser

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable",
)

DISASTER_INGEST_ENABLED = os.getenv("DISASTER_INGEST_ENABLED", "true").lower() not in (
    "false", "0", "no", "off",
)

USER_AGENT = os.getenv(
    "DISASTER_USER_AGENT",
    "AtlasObservatory/1.0 (non-commercial research; disaster-event ingest)",
)

USGS_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
USGS_MIN_MAG = float(os.getenv("USGS_MIN_MAGNITUDE", "4.5"))
GDACS_RSS = os.getenv("GDACS_RSS_URL", "https://www.gdacs.org/xml/rss.xml")

# GDACS event-type code -> our normalized event_type.
_GDACS_TYPE = {
    "EQ": "earthquake", "TC": "cyclone", "FL": "flood",
    "WF": "wildfire", "VO": "volcano", "DR": "drought",
}

# US state / territory postal codes — USGS labels US quakes "12km N of Ferndale, CA"
# where the comma-tail is a STATE, not a country. Map those to US.
_US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID", "IL",
    "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO", "MT",
    "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC", "PR",
}

# A few country-name aliases the countries_v2 canonical names miss (feeds are terse).
_NAME_ALIASES = {
    "usa": "US", "united states": "US", "u.s.a.": "US", "america": "US",
    "russia": "RU", "south korea": "KR", "north korea": "KP", "iran": "IR",
    "syria": "SY", "tanzania": "TZ", "bolivia": "BO", "venezuela": "VE",
    "uk": "GB", "united kingdom": "GB", "great britain": "GB",
    "turkey": "TR", "türkiye": "TR", "vietnam": "VN", "laos": "LA",
    "moldova": "MD", "the philippines": "PH", "philippines": "PH",
}


async def _country_name_map(conn: asyncpg.Connection) -> dict:
    """lowercased country name -> ISO2, from countries_v2 (+ aliases)."""
    rows = await conn.fetch("SELECT code, name FROM countries_v2 WHERE code IS NOT NULL")
    m = {r["name"].strip().lower(): r["code"] for r in rows if r["name"]}
    m.update(_NAME_ALIASES)
    return m


def _resolve_country(place: str | None, name_map: dict) -> str | None:
    """Best-effort ISO2 from a place string / country name. NULL when unmapped."""
    if not place:
        return None
    tail = place.split(",")[-1].strip()
    if len(tail) == 2 and tail.upper() in _US_STATES:
        return "US"
    key = tail.lower()
    if key in name_map:
        return name_map[key]
    # try the whole string as a country name (GDACS gives a bare country name)
    return name_map.get(place.strip().lower())


async def fetch_usgs(session: aiohttp.ClientSession, hours: int, name_map: dict) -> list[dict]:
    """USGS FDSN GeoJSON — earthquakes >= min magnitude in the last `hours`."""
    start = (datetime.now(timezone.utc) - timedelta(hours=hours)).strftime("%Y-%m-%dT%H:%M:%S")
    params = {
        "format": "geojson", "starttime": start,
        "minmagnitude": str(USGS_MIN_MAG), "orderby": "time", "limit": "2000",
    }
    out: list[dict] = []
    try:
        async with session.get(USGS_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                logger.warning("USGS %s", resp.status)
                return out
            data = await resp.json()
    except Exception as e:  # noqa: BLE001 — a feed hiccup must not abort ingest
        logger.warning("USGS fetch failed: %s", e)
        return out
    for f in data.get("features", []):
        p = f.get("properties") or {}
        g = f.get("geometry") or {}
        coords = g.get("coordinates") or [None, None, None]
        if (p.get("type") or "earthquake") != "earthquake":
            continue  # skip quarry blasts / explosions
        t_ms = p.get("time")
        if not t_ms:
            continue
        sig = p.get("sig") or 0
        out.append({
            "event_id": f.get("id"),
            "source": "usgs",
            "event_type": "earthquake",
            "title": p.get("place"),
            "country_code": _resolve_country(p.get("place"), name_map),
            "latitude": coords[1], "longitude": coords[0],
            "magnitude": p.get("mag"),
            "alert_level": ("Red" if sig >= 600 else "Orange" if sig >= 300 else "Green"),
            "event_time": datetime.fromtimestamp(t_ms / 1000.0, tz=timezone.utc),
            "url": p.get("url"),
            "population_affected": None,
            "raw": {"place": p.get("place"), "mag": p.get("mag"), "sig": sig,
                    "tsunami": p.get("tsunami"), "depth_km": coords[2]},
        })
    return out


def _gdacs_field(entry, *names):
    for n in names:
        v = entry.get(n)
        if v not in (None, ""):
            return v
    return None


async def fetch_gdacs(session: aiohttp.ClientSession, name_map: dict) -> list[dict]:
    """GDACS GeoRSS — floods / cyclones / wildfires / volcanoes / droughts + earthquakes."""
    out: list[dict] = []
    try:
        async with session.get(GDACS_RSS, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status != 200:
                logger.warning("GDACS %s", resp.status)
                return out
            body = await resp.read()
    except Exception as e:  # noqa: BLE001
        logger.warning("GDACS fetch failed: %s", e)
        return out
    feed = feedparser.parse(body)
    for e in feed.entries:
        etype = _gdacs_field(e, "gdacs_eventtype")
        norm = _GDACS_TYPE.get((etype or "").upper())
        if not norm:
            continue
        eid = _gdacs_field(e, "gdacs_eventid", "gdacs_id")
        epi = _gdacs_field(e, "gdacs_episodeid")
        event_id = f"gdacs-{norm}-{eid}" + (f"-{epi}" if epi else "") if eid else e.get("id") or e.get("link")
        if not event_id:
            continue
        # coordinates: geo_lat/geo_long or georss point "lat lon"
        lat = _gdacs_field(e, "geo_lat")
        lon = _gdacs_field(e, "geo_long")
        if lat is None:
            pt = _gdacs_field(e, "georss_point")
            if pt and len(pt.split()) == 2:
                lat, lon = pt.split()
        country = _gdacs_field(e, "gdacs_country")
        sev = _gdacs_field(e, "gdacs_severity")
        try:
            mag = float(getattr(e, "gdacs_severity_value", None) or sev) if sev else None
        except (TypeError, ValueError):
            mag = None
        pub = getattr(e, "published_parsed", None) or getattr(e, "updated_parsed", None)
        event_time = (datetime(*pub[:6], tzinfo=timezone.utc) if pub
                      else datetime.now(timezone.utc))
        try:
            pop = int(getattr(e, "gdacs_population", None) or 0) or None
        except (TypeError, ValueError):
            pop = None
        out.append({
            "event_id": str(event_id),
            "source": "gdacs",
            "event_type": norm,
            "title": e.get("title"),
            "country_code": _resolve_country(country, name_map) if country else None,
            "latitude": float(lat) if lat not in (None, "") else None,
            "longitude": float(lon) if lon not in (None, "") else None,
            "magnitude": mag,
            "alert_level": _gdacs_field(e, "gdacs_alertlevel"),
            "event_time": event_time,
            "url": e.get("link"),
            "population_affected": pop,
            "raw": {"country": country, "severity": sev, "eventtype": etype},
        })
    return out


_UPSERT = """
    INSERT INTO disaster_events_v2
        (event_id, source, event_type, title, country_code, latitude, longitude,
         magnitude, alert_level, event_time, url, population_affected, raw)
    SELECT * FROM unnest(
        $1::text[], $2::text[], $3::text[], $4::text[], $5::text[],
        $6::double precision[], $7::double precision[], $8::double precision[],
        $9::text[], $10::timestamptz[], $11::text[], $12::bigint[], $13::jsonb[])
    ON CONFLICT (event_id) DO UPDATE SET
        magnitude    = COALESCE(EXCLUDED.magnitude, disaster_events_v2.magnitude),
        alert_level  = COALESCE(EXCLUDED.alert_level, disaster_events_v2.alert_level),
        country_code = COALESCE(EXCLUDED.country_code, disaster_events_v2.country_code),
        population_affected = COALESCE(EXCLUDED.population_affected, disaster_events_v2.population_affected),
        title        = COALESCE(EXCLUDED.title, disaster_events_v2.title)
"""


async def _write(conn: asyncpg.Connection, rows: list[dict]) -> int:
    rows = [r for r in rows if r.get("event_id") and r.get("event_time")]
    if not rows:
        return 0
    import json
    await conn.execute(
        _UPSERT,
        [r["event_id"] for r in rows], [r["source"] for r in rows],
        [r["event_type"] for r in rows], [r.get("title") for r in rows],
        [r.get("country_code") for r in rows], [r.get("latitude") for r in rows],
        [r.get("longitude") for r in rows], [r.get("magnitude") for r in rows],
        [r.get("alert_level") for r in rows], [r["event_time"] for r in rows],
        [r.get("url") for r in rows], [r.get("population_affected") for r in rows],
        [json.dumps(r.get("raw") or {}) for r in rows],
    )
    return len(rows)


async def ingest_disasters(hours: int = 24) -> int:
    """One pull of USGS + GDACS into disaster_events_v2. Returns rows upserted."""
    if not DISASTER_INGEST_ENABLED:
        logger.info("disaster ingest disabled")
        return 0
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        name_map = await _country_name_map(conn)
        async with aiohttp.ClientSession(headers={"User-Agent": USER_AGENT}) as session:
            usgs, gdacs = await asyncio.gather(
                fetch_usgs(session, hours, name_map),
                fetch_gdacs(session, name_map),
            )
        n = await _write(conn, usgs + gdacs)
        logger.info("disaster ingest: %d USGS + %d GDACS -> %d upserted",
                    len(usgs), len(gdacs), n)
        return n
    finally:
        await conn.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    n = asyncio.run(ingest_disasters(int(sys.argv[1]) if len(sys.argv) > 1 else 24))
    print(f"upserted {n} disaster events")
