"""
GDELT Ingestion for V2 Schema
Fetches latest GDELT data and inserts into signals_v2 table
V3: Now includes crisis classification
V3.1: Converts FIPS country codes to ISO 3166-1 alpha-2
V3.2: Fixed CSV field size limit for GDELT GKG large fields
"""
import csv
import sys

# CRITICAL: Increase CSV field size limit for GDELT GKG files
# GDELT V2Themes/V2Persons columns can exceed 200KB
# Must be set BEFORE any csv.reader() calls
csv.field_size_limit(10 * 1024 * 1024)  # 10MB

import asyncio
import aiohttp
import asyncpg
import zipfile
import io
import logging
from datetime import datetime, timezone
from typing import Optional
import os
import re
import html as _html

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config.crisis_themes import (
    is_crisis_theme,
    get_crisis_themes,
    calculate_crisis_score,
    calculate_severity,
    get_event_type
)
from app.config.source_blocklist import is_blocked
from app.services.country_codes import fips_to_iso

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://observatory:changeme@localhost:5432/observatory?sslmode=disable")

# GDELT GKG (Global Knowledge Graph) URL
GDELT_LAST_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate.txt"
GDELT_TRANS_UPDATE_URL = "http://data.gdeltproject.org/gdeltv2/lastupdate-translation.txt"

async def fetch_latest_gdelt_url(update_url: str = GDELT_LAST_UPDATE_URL) -> Optional[str]:
    """Get the URL of the latest GDELT GKG file."""
    async with aiohttp.ClientSession() as session:
        async with session.get(update_url) as resp:
            if resp.status != 200:
                print(f"Failed to fetch GDELT update list: {resp.status}")
                return None
            text = await resp.text()
            for line in text.strip().split('\n'):
                if 'gkg' in line.lower() and line.endswith('.csv.zip'):
                    parts = line.split()
                    if len(parts) >= 3:
                        return parts[2]
    return None

async def download_and_parse_gkg(url: str, source_lang: str = "en") -> list[dict]:
    """Download and parse GDELT GKG file with resilient error handling."""
    signals = []
    skipped = 0

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                logger.error(f"Failed to download {url}: {resp.status}")
                return signals

            data = await resp.read()

    # Unzip and parse
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for filename in zf.namelist():
                if filename.endswith('.csv'):
                    with zf.open(filename) as f:
                        reader = csv.reader(io.TextIOWrapper(f, encoding='utf-8', errors='replace'), delimiter='\t')
                        for line_num, row in enumerate(reader, start=1):
                            try:
                                signal = parse_gkg_row(row, source_lang=source_lang)
                                if signal:
                                    signals.append(signal)
                            except Exception as e:
                                skipped += 1
                                if skipped <= 5:  # Log first 5 errors only
                                    logger.warning(f"Skipped line {line_num} in {filename}: {type(e).__name__}: {str(e)[:100]}")
                                continue  # CRITICAL: Continue, don't crash
    except Exception as e:
        logger.error(f"Failed to process zip file from {url}: {e}")

    if skipped > 0:
        logger.info(f"Processed {url}: {len(signals)} signals, {skipped} skipped")

    return signals

# Known domain → ISO2 source-country mapping (largest news domains by country).
# Used to detect when a signal's country_code differs from the outlet's home country.
_DOMAIN_COUNTRY: dict[str, str] = {
    # United States
    'cnn.com': 'US', 'foxnews.com': 'US', 'msnbc.com': 'US', 'nbcnews.com': 'US',
    'abcnews.go.com': 'US', 'cbsnews.com': 'US', 'npr.org': 'US', 'pbs.org': 'US',
    'apnews.com': 'US', 'bloomberg.com': 'US', 'washingtonpost.com': 'US',
    'nytimes.com': 'US', 'wsj.com': 'US', 'usatoday.com': 'US', 'politico.com': 'US',
    'axios.com': 'US', 'thehill.com': 'US', 'huffpost.com': 'US', 'vox.com': 'US',
    'buzzfeednews.com': 'US', 'vice.com': 'US', 'time.com': 'US', 'newsweek.com': 'US',
    'theatlantic.com': 'US', 'newyorker.com': 'US', 'slate.com': 'US',
    'breitbart.com': 'US', 'thedailybeast.com': 'US', 'dailywire.com': 'US',
    'oann.com': 'US', 'newsmax.com': 'US', 'foxbusiness.com': 'US',
    # United Kingdom
    'bbc.co.uk': 'GB', 'bbc.com': 'GB', 'theguardian.com': 'GB',
    'telegraph.co.uk': 'GB', 'thetimes.co.uk': 'GB', 'independent.co.uk': 'GB',
    'dailymail.co.uk': 'GB', 'mirror.co.uk': 'GB', 'express.co.uk': 'GB',
    'sky.com': 'GB', 'channel4.com': 'GB', 'ft.com': 'GB',
    # France
    'lemonde.fr': 'FR', 'lefigaro.fr': 'FR', 'liberation.fr': 'FR',
    'france24.com': 'FR', 'rfi.fr': 'FR', 'lepoint.fr': 'FR',
    # Germany
    'dw.com': 'DE', 'spiegel.de': 'DE', 'zeit.de': 'DE', 'faz.net': 'DE',
    'sueddeutsche.de': 'DE', 'bild.de': 'DE',
    # Russia
    'rt.com': 'RU', 'sputniknews.com': 'RU', 'tass.com': 'RU',
    'ria.ru': 'RU', 'pravda.ru': 'RU', 'iz.ru': 'RU',
    # China
    'xinhuanet.com': 'CN', 'chinadaily.com.cn': 'CN', 'globaltimes.cn': 'CN',
    'cgtn.com': 'CN', 'people.com.cn': 'CN',
    # Iran
    'irna.ir': 'IR', 'press.tv': 'IR', 'tehrantimes.com': 'IR',
    'farsnews.ir': 'IR', 'tasnimnews.com': 'IR',
    # India
    'thehindu.com': 'IN', 'hindustantimes.com': 'IN', 'ndtv.com': 'IN',
    'timesofindia.indiatimes.com': 'IN', 'indianexpress.com': 'IN',
    # Al Jazeera / Qatar
    'aljazeera.com': 'QA',
    # Australia
    'abc.net.au': 'AU', 'smh.com.au': 'AU', 'theaustralian.com.au': 'AU',
    # Canada
    'cbc.ca': 'CA', 'globalnews.ca': 'CA', 'torontostar.com': 'CA',
    'theglobeandmail.com': 'CA', 'nationalpost.com': 'CA',
    # Reuters / AP (international wires — treat as US-headquartered)
    'reuters.com': 'US',
    # ── Expanded coverage (issue #165 local_voice_ratio activation) ──
    # Latin America
    'elpais.com': 'ES', 'elmundo.es': 'ES', 'abc.es': 'ES', 'lavanguardia.com': 'ES',
    'clarin.com': 'AR', 'lanacion.com.ar': 'AR', 'pagina12.com.ar': 'AR', 'infobae.com': 'AR',
    'folha.uol.com.br': 'BR', 'globo.com': 'BR', 'g1.globo.com': 'BR', 'estadao.com.br': 'BR',
    'eltiempo.com': 'CO', 'semana.com': 'CO', 'elespectador.com': 'CO',
    'eluniversal.com.mx': 'MX', 'jornada.com.mx': 'MX', 'milenio.com': 'MX', 'reforma.com': 'MX',
    'eluniversal.com': 'VE', 'el-nacional.com': 'VE',
    'emol.com': 'CL', 'latercera.com': 'CL', 'biobiochile.cl': 'CL',
    'larepublica.pe': 'PE', 'elcomercio.pe': 'PE',
    'eluniverso.com': 'EC', 'elcomercio.com': 'EC',
    'lostiempos.com': 'BO', 'paginasiete.bo': 'BO',
    'ultimahora.com': 'PY', 'abc.com.py': 'PY',
    'elobservador.com.uy': 'UY', 'elpais.com.uy': 'UY',
    'prensalibre.com': 'GT', 'laprensagrafica.com': 'SV',
    'laprensa.com.ni': 'NI', 'lanacion.com.do': 'DO',
    # Africa
    'allafrica.com': 'ZA',
    'mg.co.za': 'ZA', 'iol.co.za': 'ZA', 'news24.com': 'ZA', 'dailymaverick.co.za': 'ZA',
    'punchng.com': 'NG', 'vanguardngr.com': 'NG', 'premiumtimesng.com': 'NG', 'thecable.ng': 'NG',
    'guardian.ng': 'NG', 'thisdaylive.com': 'NG',
    'nation.africa': 'KE', 'standardmedia.co.ke': 'KE', 'the-star.co.ke': 'KE',
    'monitor.co.ug': 'UG', 'newvision.co.ug': 'UG',
    'theeastafrican.co.ke': 'KE',
    'graphic.com.gh': 'GH', 'myjoyonline.com': 'GH', 'ghanaweb.com': 'GH',
    'lemonde.sn': 'SN', 'seneweb.com': 'SN', 'lequotidien.sn': 'SN',
    'koaci.com': 'CI', 'fratmat.info': 'CI',
    'ennaharonline.com': 'DZ', 'liberte-algerie.com': 'DZ',
    'lemorial.tn': 'TN', 'tap.info.tn': 'TN', 'lapresse.tn': 'TN',
    'middleeastmonitor.com': 'GB', 'almasryalyoum.com': 'EG', 'ahram.org.eg': 'EG', 'egyptindependent.com': 'EG',
    'addisstandard.com': 'ET', 'addisfortune.news': 'ET', 'thereporterethiopia.com': 'ET',
    'newtimes.co.rw': 'RW',
    'thecitizen.co.tz': 'TZ',
    'mwnation.com': 'MW',
    'zambianobserver.com': 'ZM',
    'zimlive.com': 'ZW', 'thezimbabwemail.com': 'ZW',
    'angop.ao': 'AO',
    # MENA
    'arabnews.com': 'SA', 'saudigazette.com.sa': 'SA',
    'thenationalnews.com': 'AE', 'gulfnews.com': 'AE', 'khaleejtimes.com': 'AE',
    'dailystar.com.lb': 'LB', 'lorientlejour.com': 'LB',
    'haaretz.com': 'IL', 'jpost.com': 'IL', 'timesofisrael.com': 'IL', 'ynetnews.com': 'IL',
    'jordantimes.com': 'JO', 'roya.tv': 'JO',
    'hurriyetdailynews.com': 'TR', 'dailysabah.com': 'TR', 'trtworld.com': 'TR',
    'al-monitor.com': 'US',
    # Asia
    'scmp.com': 'HK', 'standnews.com': 'HK',
    'straitstimes.com': 'SG', 'channelnewsasia.com': 'SG', 'todayonline.com': 'SG',
    'bangkokpost.com': 'TH', 'nationthailand.com': 'TH',
    'jakartapost.com': 'ID', 'tempo.co': 'ID', 'kompas.com': 'ID',
    'inquirer.net': 'PH', 'rappler.com': 'PH', 'philstar.com': 'PH', 'abs-cbn.com': 'PH',
    'vnexpress.net': 'VN', 'tuoitrenews.vn': 'VN',
    'mizzima.com': 'MM', 'irrawaddy.com': 'MM', 'frontiermyanmar.net': 'MM',
    'dhakatribune.com': 'BD', 'thedailystar.net': 'BD',
    'thehimalayantimes.com': 'NP', 'kathmandupost.com': 'NP',
    'dawn.com': 'PK', 'tribune.com.pk': 'PK', 'thenews.com.pk': 'PK', 'geo.tv': 'PK',
    'asahi.com': 'JP', 'mainichi.jp': 'JP', 'japantimes.co.jp': 'JP', 'nhk.or.jp': 'JP',
    'koreaherald.com': 'KR', 'koreatimes.co.kr': 'KR', 'hankyoreh.com': 'KR', 'chosun.com': 'KR',
    'kyivindependent.com': 'UA', 'pravda.com.ua': 'UA',
    # Latin Americas (additional)
    'la-prensa.com.ar': 'AR', 'rfi.fr/es': 'FR',
}

def _extract_source_country(url: str | None) -> str | None:
    """Infer the outlet's home country from its domain. Returns ISO2 or None."""
    if not url:
        return None
    try:
        import urllib.parse as _up
        host = _up.urlparse(url).netloc.lower().lstrip('www.')
        # Exact match first
        if host in _DOMAIN_COUNTRY:
            return _DOMAIN_COUNTRY[host]
        # Suffix match (subdomains like 'edition.cnn.com')
        for domain, country in _DOMAIN_COUNTRY.items():
            if host.endswith('.' + domain) or host == domain:
                return country
        # TLD heuristic for ccTLDs not already in map
        tld = host.rsplit('.', 1)[-1]
        _TLD_MAP = {
            'uk': 'GB', 'fr': 'FR', 'de': 'DE', 'ru': 'RU', 'cn': 'CN',
            'ir': 'IR', 'in': 'IN', 'au': 'AU', 'ca': 'CA', 'br': 'BR',
            'mx': 'MX', 'jp': 'JP', 'kr': 'KR', 'eg': 'EG', 'ng': 'NG',
            'za': 'ZA', 'tr': 'TR', 'pk': 'PK', 'il': 'IL', 'ua': 'UA',
            'pl': 'PL', 'ar': 'AR', 've': 'VE', 'co': 'CO', 'cl': 'CL',
            # National ccTLDs (high-precision: a country outlet on its own TLD).
            # Widens #238 override coverage — .pe outlets were resolving to None.
            'pe': 'PE', 'ec': 'EC', 'bo': 'BO', 'py': 'PY', 'uy': 'UY',
            'do': 'DO', 'gt': 'GT', 'cr': 'CR', 'pa': 'PA', 'hn': 'HN',
            'ni': 'NI', 'sv': 'SV', 'cu': 'CU', 'es': 'ES', 'it': 'IT',
            'pt': 'PT', 'nl': 'NL', 'be': 'BE', 'se': 'SE', 'no': 'NO',
            'fi': 'FI', 'dk': 'DK', 'gr': 'GR', 'at': 'AT', 'ch': 'CH',
            'cz': 'CZ', 'sk': 'SK', 'hu': 'HU', 'ro': 'RO', 'bg': 'BG',
            'rs': 'RS', 'hr': 'HR', 'ie': 'IE', 'id': 'ID', 'my': 'MY',
            'th': 'TH', 'ph': 'PH', 'vn': 'VN', 'sa': 'SA', 'ae': 'AE',
            'qa': 'QA', 'lb': 'LB', 'ma': 'MA', 'dz': 'DZ', 'tn': 'TN',
            'ke': 'KE', 'gh': 'GH', 'tw': 'TW',
        }
        return _TLD_MAP.get(tld)
    except Exception:
        return None


# #238 subject-geography core. GDELT's geocoder mis-locates non-English content:
# a stray token in a Spanish/Portuguese article ("Belén"->Bethlehem, a passing
# place name) gets tagged, and the naive "first location with lat/lon" pick then
# stamps a Peruvian farándula story onto the West Bank. Two measured levers:
#  (1) PROMINENCE — pick the most-MENTIONED country across V2ENHANCEDLOCATIONS,
#      not the first one. Each ';' block is one mention; frequency = subject.
#  (2) NON-ENGLISH OUTLET-ORIGIN OVERRIDE — when the translation feed
#      (source_lang != 'en') yields only single-mention scatter (no location
#      mentioned twice = no real subject) and the winner conflicts with the
#      outlet's home country, distrust GDELT geo and fall back to the outlet
#      country with a low geo_confidence flag. Genuine foreign coverage names
#      its subject repeatedly (count >= 2) and is left untouched.
# Reversible: ATLAS_GEO_SUBJECT_GATE=off restores the naive first-pick.
_GEO_SUBJECT_GATE = os.getenv("ATLAS_GEO_SUBJECT_GATE", "on").lower() not in ("0", "off", "false", "no")
_GEO_OVERRIDE_CONFIDENCE = 0.35

# #238 ambiguous-geo demotion. Measured 2026-07-08: 67% of GDELT rows tagged PS
# (Palestine) over 5 days were keyword-negative mistags — Spanish "Belén"
# (a Peru district / a first name), Portuguese "Belém" (a major Brazilian city),
# and US "Bethlehem, PA" all resolve to Bethlehem, West Bank (FIPS WE → ISO PS)
# in GDELT's gazetteer, so a Peruvian farándula or Brazilian city-hall story
# gets stamped onto Palestine. The prominence pick alone doesn't catch it
# (repeated "Belém" tokens give PS count ≥ 2) and the outlet-origin override
# can't fire when the source URL doesn't resolve to a country (65% of the class)
# or when the feed is English.
#
# Lever: when the prominence winner is an AMBIGUOUS-geo country (PS) but the
# article gives NO Palestine corroboration (headline + GDELT themes carry no
# Palestine/Gaza/Israel token) AND the same article geocodes a real non-PS
# subject, reassign to that non-PS subject. A repeated (count ≥ 2) alternative
# is trusted (conf 0.6); a single-mention alternative is only taken when the
# outlet-origin override won't fire (conf 0.4, damped). Genuine Palestine
# coverage names its subject (corroborated → untouched); a PS-only article with
# no alternative is left as-is (can't disambiguate). Reversible:
# ATLAS_GEO_AMBIGUOUS_DEMOTE=off.
_GEO_AMBIGUOUS_DEMOTE = os.getenv("ATLAS_GEO_AMBIGUOUS_DEMOTE", "on").lower() not in ("0", "off", "false", "no")
_GEO_AMBIGUOUS_ISO = {"PS"}  # Bethlehem(WE)/Gaza(GZ) collision with Belén/Belém
_PALESTINE_CORROBORATION = re.compile(
    r"(palestin|gaza|hamas|israel|cisjord|ramallah|rafah|jenin|nablus|hebron|"
    r"khan\s*y|west\s*bank|بيت\s*لحم|فلسط|غزة|حماس|إسرائيل|الضفة)",
    re.IGNORECASE,
)


def _select_primary_country(
    locations: str,
    source_lang: str,
    source_origin_country: str | None,
    corroboration_text: str = "",
) -> Optional[tuple]:
    """Choose (iso_country, lat, lon, geo_confidence, method) from a GKG
    V2ENHANCEDLOCATIONS field. Returns None when no location geocodes.

    Block format: Type#FullName#CountryCode#ADM1#Lat#Long#FeatureID#Offset
    """
    if not locations:
        return None

    # Tally geocoded mentions by ISO country: [count, earliest_offset, (lat,lon)]
    tally: dict[str, list] = {}
    for loc in locations.split(';'):
        parts = loc.split('#')
        if len(parts) < 6:
            continue
        iso = fips_to_iso(parts[2][:2]) if parts[2] else None
        if not iso:
            continue
        try:
            lat = float(parts[4]) if parts[4] else None
        except ValueError:
            lat = None
        try:
            lon = float(parts[5]) if parts[5] else None
        except ValueError:
            lon = None
        try:
            offset = int(parts[7]) if len(parts) > 7 and parts[7] else 10 ** 9
        except ValueError:
            offset = 10 ** 9
        rec = tally.setdefault(iso, [0, 10 ** 9, None])
        rec[0] += 1
        rec[1] = min(rec[1], offset)
        if rec[2] is None and lat is not None and lon is not None:
            rec[2] = (lat, lon)

    if not tally:
        return None

    if not _GEO_SUBJECT_GATE:
        # Legacy behaviour: first geocoded block wins (earliest offset).
        iso = min(tally.items(), key=lambda kv: kv[1][1])[0]
        lat, lon = tally[iso][2] or (None, None)
        return iso.upper(), lat, lon, 0.85, 'gdelt_geo_first'

    # (1) Prominence: most mentions, tie-break earliest mention.
    iso, (count, _off, latlon) = min(
        tally.items(), key=lambda kv: (-kv[1][0], kv[1][1])
    )
    lat, lon = latlon or (None, None)
    max_count = max(rec[0] for rec in tally.values())

    # (1b) Ambiguous-geo demotion (#238, measured 2026-07-08). The prominence
    # winner is Palestine but the article never corroborates it -> the classic
    # "Belén"/"Belém"/"Bethlehem, PA" -> Bethlehem, West Bank false geocode.
    # Reassign to the real non-PS subject in the same article when one exists.
    if (
        _GEO_AMBIGUOUS_DEMOTE
        and iso.upper() in _GEO_AMBIGUOUS_ISO
        and not (corroboration_text and _PALESTINE_CORROBORATION.search(corroboration_text))
    ):
        non_ambiguous = [
            (c, rec) for c, rec in tally.items() if c.upper() not in _GEO_AMBIGUOUS_ISO
        ]
        if non_ambiguous:
            c2, rec2 = min(non_ambiguous, key=lambda kv: (-kv[1][0], kv[1][1]))
            ll2 = rec2[2] or (None, None)
            if rec2[0] >= 2:
                # A repeated real subject lost only on the ambiguous token.
                return c2.upper(), ll2[0], ll2[1], 0.6, 'ambiguous_geo_demote'
            # Single-mention alternative: prefer the outlet override if it will
            # fire below (scatter with a known outlet); otherwise take the
            # alternative at damped confidence rather than trust the mistag.
            outlet_would_fire = (
                source_lang != 'en'
                and source_origin_country
                and max_count == 1
                and source_origin_country.upper() not in _GEO_AMBIGUOUS_ISO
            )
            if not outlet_would_fire:
                return c2.upper(), ll2[0], ll2[1], 0.4, 'ambiguous_geo_demote_weak'

    # (2) Non-English single-mention scatter conflicting with the outlet home
    # country -> trust the outlet, flag low confidence. Only fires when NO
    # location is mentioned more than once (max_count == 1), i.e. there is no
    # dominant subject for GDELT to have gotten right.
    if (
        source_lang != 'en'
        and source_origin_country
        and max_count == 1
        and iso.upper() != source_origin_country.upper()
    ):
        return source_origin_country.upper(), None, None, _GEO_OVERRIDE_CONFIDENCE, 'outlet_origin_override'

    return iso.upper(), lat, lon, 0.85, 'gdelt_geo_prominence'


def parse_gkg_row(row: list, source_lang: str = "en") -> Optional[dict]:
    """Parse a single GKG row into a signal dict."""
    if len(row) < 27:
        return None
    
    # Extract fields (GKG 2.0 format)
    try:
        date_str = row[0]  # YYYYMMDDHHMMSS
        timestamp = datetime.strptime(date_str[:14], "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)
    except:
        timestamp = datetime.now(timezone.utc)
    
    source_url = row[4] if len(row) > 4 else None
    source_name = row[3] if len(row) > 3 else None

    # Drop signals from blocked entertainment/tabloid domains before any further work
    if is_blocked(source_url):
        return None
    
    import re as _re
    import urllib.parse

    headline = None

    # Try V2EXTRASXML (col 26) for real article title first
    extras_xml = row[26] if len(row) > 26 else ''
    if extras_xml:
        m = _re.search(r'<PAGE_TITLE>(.+?)</PAGE_TITLE>', extras_xml)
        if m:
            candidate = m.group(1).strip()
            # Basic validation: at least 4 words, no GDELT doc IDs
            words = candidate.split()
            if len(words) >= 4 and not _re.match(r'^\d{6,}', candidate):
                headline = candidate

    # Fall back to URL slug if no title found
    if not headline and source_url:
        try:
            path = urllib.parse.urlparse(source_url).path
            slug = path.strip('/').split('/')[-1]
            if slug and len(slug) >= 5 and ('-' in slug or '_' in slug):
                slug = slug.replace('.html', '').replace('.htm', '').replace('.php', '')
                headline = slug.replace('-', ' ').replace('_', ' ').title()
        except:
            pass
    
    # Locations (V2ENHANCEDLOCATIONS - field 10). Subject-geography selection
    # (#238): prominence pick + non-English outlet-origin override + ambiguous-
    # geo demotion. Needs the outlet home country and the article text (headline
    # + themes, for Palestine corroboration) up front.
    locations = row[10] if len(row) > 10 else ""
    themes_raw = row[8] if len(row) > 8 else ""
    source_origin_country = _extract_source_country(source_url)
    selected = _select_primary_country(
        locations,
        source_lang,
        source_origin_country,
        # Unescape so HTML-entity-encoded non-Latin headlines (e.g. Arabic
        # &#x641;&#x644;&#x633;... = فلسطين) corroborate too, not just the
        # ASCII GDELT themes.
        corroboration_text=_html.unescape(f"{headline or ''} {themes_raw or ''}"),
    )
    if not selected:
        return None
    country_code, lat, lon, geo_confidence, geo_method = selected
    
    # Themes (V2ENHANCEDTHEMES - field 8; themes_raw computed above)
    themes = []
    if themes_raw:
        for theme in themes_raw.split(';'):
            theme_name = theme.split(',')[0] if ',' in theme else theme
            if theme_name and len(theme_name) > 2:
                themes.append(theme_name.upper())
    themes = list(set(themes))[:10]
    
    # Persons (V2ENHANCEDPERSONS - field 12)
    persons_raw = row[12] if len(row) > 12 else ""
    persons = []
    if persons_raw:
        for person in persons_raw.split(';'):
            person_name = person.split(',')[0] if ',' in person else person
            if person_name and len(person_name) > 2:
                persons.append(person_name.lower())
    persons = list(set(persons))[:10]

    # Organizations (V2ENHANCEDORGANIZATIONS - field 13) — the WHO-orgs half
    # (#251). Same parse shape as persons; companies/agencies/armed-groups.
    orgs_raw = row[13] if len(row) > 13 else ""
    organizations = []
    if orgs_raw:
        for org in orgs_raw.split(';'):
            org_name = org.split(',')[0] if ',' in org else org
            if org_name and len(org_name) > 2:
                organizations.append(org_name.lower())
    organizations = list(set(organizations))[:10]

    # Tone (V2TONE - field 15)
    tone_raw = row[15] if len(row) > 15 else ""
    sentiment = 0.0
    if tone_raw:
        try:
            tone_parts = tone_raw.split(',')
            sentiment = float(tone_parts[0]) if tone_parts else 0.0
        except:
            pass
    
    # Crisis classification
    crisis_themes = get_crisis_themes(themes)
    is_crisis = len(crisis_themes) > 0
    crisis_score = calculate_crisis_score(themes) if is_crisis else 0.0
    severity = calculate_severity(themes) if is_crisis else 'low'
    event_type = get_event_type(themes) if is_crisis else 'other'
    
    attribution = 'gdelt_gkg_translated' if source_lang != 'en' else 'gdelt_gkg'

    return {
        'timestamp': timestamp,
        'country_code': country_code,
        'latitude': lat,
        'longitude': lon,
        'sentiment': sentiment,
        'source_url': source_url,
        'source_name': source_name,
        'headline': headline,
        'themes': themes,
        'persons': persons,
        'organizations': organizations,
        # Crisis classification fields
        'is_crisis': is_crisis,
        'crisis_score': crisis_score,
        'crisis_themes': crisis_themes,
        'severity': severity,
        'event_type': event_type,
        # Source provenance fields (migration 008)
        'source_family': 'gdelt',
        'source_lang': source_lang,
        'geo_confidence': geo_confidence,
        'attribution_method': attribution,
        'is_state_media': False,
        # Geo validation (migration 012)
        'source_origin_country': source_origin_country,
        # Semantic class (migration 021) — GDELT is always editorial reporting
        'signal_class': 'reporting',
    }

async def insert_signals(pool: asyncpg.Pool, signals: list[dict]) -> int:
    """Insert signals into database. Returns count of newly inserted rows."""
    if not signals:
        return 0

    inserted = 0
    skipped_dup = 0
    failed = 0
    async with pool.acquire() as conn:
        for signal in signals:
            try:
                result = await conn.execute("""
                    INSERT INTO signals_v2 (
                        timestamp, country_code, latitude, longitude, sentiment,
                        source_url, source_name, headline, themes, persons,
                        is_crisis, crisis_score, crisis_themes, severity, event_type,
                        source_family, source_lang, geo_confidence, attribution_method, is_state_media,
                        source_origin_country, signal_class, organizations
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
                            $16, $17, $18, $19, $20, $21, $22, $23)
                    ON CONFLICT (source_url) WHERE source_url IS NOT NULL DO NOTHING
                """,
                    signal['timestamp'],
                    signal['country_code'],
                    signal['latitude'],
                    signal['longitude'],
                    signal['sentiment'],
                    signal['source_url'],
                    signal['source_name'],
                    signal['headline'],
                    signal['themes'],
                    signal['persons'],
                    signal['is_crisis'],
                    signal['crisis_score'],
                    signal['crisis_themes'],
                    signal['severity'],
                    signal['event_type'],
                    signal.get('source_family', 'gdelt'),
                    signal.get('source_lang', 'en'),
                    signal.get('geo_confidence', 0.85),
                    signal.get('attribution_method', 'gdelt_gkg'),
                    signal.get('is_state_media', False),
                    signal.get('source_origin_country'),
                    signal.get('signal_class', 'reporting'),
                    signal.get('organizations'),
                )
                # asyncpg returns "INSERT 0 N" — N=0 means conflict (dup)
                if result == "INSERT 0 1":
                    inserted += 1
                else:
                    skipped_dup += 1
            except Exception as e:
                failed += 1
                if failed <= 3:
                    logger.warning("Insert failed: %s: %s", type(e).__name__, str(e)[:120])

    logger.info("insert_signals: %d parsed → %d inserted, %d dup-skipped, %d errors",
                len(signals), inserted, skipped_dup, failed)
    return inserted

async def update_countries(pool: asyncpg.Pool):
    """
    Add new countries from signals, but NEVER overwrite existing coordinates.
    Only looks at the last 2 hours of signals to avoid scanning the full table.
    """
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO countries_v2 (code, name, latitude, longitude)
            SELECT DISTINCT
                country_code,
                country_code,
                NULL::numeric,
                NULL::numeric
            FROM signals_v2
            WHERE country_code IS NOT NULL
              AND timestamp > NOW() - INTERVAL '2 hours'
              AND country_code NOT IN (SELECT code FROM countries_v2)
            ON CONFLICT (code) DO NOTHING
        """)

_last_matview_refresh: Optional[datetime] = None

async def refresh_aggregates(pool: asyncpg.Pool):
    """country_hourly_v2 refresh is OWNED by the M1 cron (refresh-country-hourly.sh,
    session-mode psql) since 2026-07-02. This API-side path is retired: through
    the Supabase TRANSACTION pooler the session SET above never reached the
    backend running the REFRESH, so it ran UNBOUNDED — and collided with the M1
    cron's refresh (two CONCURRENTLY refreshes observed 2026-07-02 18:20 UTC,
    8m+ each, IO-starving /api/v2/signals into intermittent 500s)."""
    return

async def run_ingestion():
    """Main ingestion function."""
    logger.info("GDELT ingestion cycle starting")

    pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=1)

    try:
        # Fetch latest GDELT URL
        url = await fetch_latest_gdelt_url(GDELT_LAST_UPDATE_URL)
        if url:
            logger.info("Downloading English GKG: %s", url.split('/')[-1])
            signals = await download_and_parse_gkg(url)
            logger.info("Parsed %d English signals from GKG", len(signals))
            inserted = await insert_signals(pool, signals)
            logger.info("English GKG: %d new signals inserted", inserted)

        # Fetch Translingual GDELT URL (Arabic, Persian, Russian, Chinese, Spanish, etc.)
        trans_url = await fetch_latest_gdelt_url(GDELT_TRANS_UPDATE_URL)
        if trans_url:
            logger.info("Downloading Translingual GKG: %s", trans_url.split('/')[-1])
            # source_lang='xx' signals translingual origin; per-article lang not in GKG schema
            trans_signals = await download_and_parse_gkg(trans_url, source_lang='xx')
            logger.info("Parsed %d translingual signals from GKG", len(trans_signals))
            inserted_trans = await insert_signals(pool, trans_signals)
            logger.info("Translingual GKG: %d new signals inserted", inserted_trans)
        
        # Update countries (non-fatal if it fails)
        try:
            await update_countries(pool)
            print("Updated countries")
        except Exception as e:
            print(f"update_countries failed (non-fatal): {e}")

        # Refresh aggregates (always run regardless of update_countries outcome)
        try:
            await refresh_aggregates(pool)
            print("Refreshed aggregates")
        except Exception as e:
            # LOUD: a silent matview death starves brief stats / /stats / geo
            # detail / anomaly baselines for hours (2026-07-01 incident).
            logger.error("refresh_aggregates FAILED — country_hourly_v2 going stale: %s", e)

        # Update theme_hourly_v2 pre-aggregation (enables fast narratives for any window).
        # nlp_signal_count + avg_nlp_sentiment let downstream readers pick transformer
        # sentiment when bucket coverage clears the threshold (migration 025).
        # nlp_sentiment_weight_sum + nlp_confidence_sum carry confidence-weighted
        # sums so readers can compute SUM(s*c)/SUM(c) instead of the flat AVG
        # that diluted high-confidence transformer rows with low-confidence
        # lexicon/fast_neutral rows (migration 033).
        try:
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO theme_hourly_v2
                        (hour, theme, signal_count, country_count, source_count, avg_sentiment,
                         nlp_signal_count, avg_nlp_sentiment,
                         nlp_sentiment_weight_sum, nlp_confidence_sum)
                    SELECT
                        date_trunc('hour', timestamp) AS hour,
                        unnest(themes)                AS theme,
                        COUNT(*)                      AS signal_count,
                        COUNT(DISTINCT country_code)  AS country_count,
                        COUNT(DISTINCT source_name)   AS source_count,
                        AVG(sentiment)                AS avg_sentiment,
                        COUNT(*) FILTER (WHERE nlp_sentiment IS NOT NULL) AS nlp_signal_count,
                        AVG(nlp_sentiment) FILTER (WHERE nlp_sentiment IS NOT NULL) AS avg_nlp_sentiment,
                        COALESCE(SUM(nlp_sentiment * nlp_confidence) FILTER (
                            WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0
                        ), 0) AS nlp_sentiment_weight_sum,
                        COALESCE(SUM(nlp_confidence) FILTER (
                            WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0
                        ), 0) AS nlp_confidence_sum
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '2 hours'
                      AND themes IS NOT NULL
                    GROUP BY 1, 2
                    ON CONFLICT (hour, theme) DO UPDATE SET
                        signal_count             = EXCLUDED.signal_count,
                        country_count            = EXCLUDED.country_count,
                        source_count             = EXCLUDED.source_count,
                        avg_sentiment            = EXCLUDED.avg_sentiment,
                        nlp_signal_count         = EXCLUDED.nlp_signal_count,
                        avg_nlp_sentiment        = EXCLUDED.avg_nlp_sentiment,
                        nlp_sentiment_weight_sum = EXCLUDED.nlp_sentiment_weight_sum,
                        nlp_confidence_sum       = EXCLUDED.nlp_confidence_sum
                """)
            print("Updated theme_hourly_v2")
        except Exception as e:
            print(f"theme_hourly_v2 update failed (non-fatal): {e}")

        # Update theme_country_hourly_v2 pre-aggregation (enables fast 168h concept queries).
        # Same NLP coverage + confidence-weighted columns as theme_hourly_v2.
        try:
            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO theme_country_hourly_v2
                        (hour, theme, country_code, signal_count, avg_sentiment,
                         nlp_signal_count, avg_nlp_sentiment,
                         nlp_sentiment_weight_sum, nlp_confidence_sum)
                    SELECT
                        date_trunc('hour', timestamp) AS hour,
                        unnest(themes)                AS theme,
                        country_code,
                        COUNT(*)                      AS signal_count,
                        AVG(sentiment)                AS avg_sentiment,
                        COUNT(*) FILTER (WHERE nlp_sentiment IS NOT NULL) AS nlp_signal_count,
                        AVG(nlp_sentiment) FILTER (WHERE nlp_sentiment IS NOT NULL) AS avg_nlp_sentiment,
                        COALESCE(SUM(nlp_sentiment * nlp_confidence) FILTER (
                            WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0
                        ), 0) AS nlp_sentiment_weight_sum,
                        COALESCE(SUM(nlp_confidence) FILTER (
                            WHERE nlp_sentiment IS NOT NULL AND nlp_confidence > 0
                        ), 0) AS nlp_confidence_sum
                    FROM signals_v2
                    WHERE timestamp > NOW() - INTERVAL '2 hours'
                      AND themes IS NOT NULL
                      AND country_code IS NOT NULL
                    GROUP BY 1, 2, 3
                    ON CONFLICT (hour, theme, country_code) DO UPDATE SET
                        signal_count             = EXCLUDED.signal_count,
                        avg_sentiment            = EXCLUDED.avg_sentiment,
                        nlp_signal_count         = EXCLUDED.nlp_signal_count,
                        avg_nlp_sentiment        = EXCLUDED.avg_nlp_sentiment,
                        nlp_sentiment_weight_sum = EXCLUDED.nlp_sentiment_weight_sum,
                        nlp_confidence_sum       = EXCLUDED.nlp_confidence_sum
                """)
            print("Updated theme_country_hourly_v2")
        except Exception as e:
            print(f"theme_country_hourly_v2 update failed (non-fatal): {e}")

        # Stats
        async with pool.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM signals_v2")
            last_1h = await conn.fetchval(
                "SELECT COUNT(*) FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '1 hour'"
            )
            logger.info("DB totals — total: %d, last 1h: %d", total, last_1h)

    finally:
        await pool.close()

    logger.info("GDELT ingestion cycle complete")

if __name__ == "__main__":
    asyncio.run(run_ingestion())
