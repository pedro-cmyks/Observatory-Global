"""
RSS Feed Ingestion Service — Wave 1 + Wave 3 + Wave 4

Ingests curated international RSS feeds (78 feeds across 30+ countries,
11 languages — Wave 5 added native-language zh/ja/ko/ru/fr/pt/de/ar/fa/hi).
Wave 1: maritime/chokepoints, Middle East, Russia independent, humanitarian, Asia, Africa/LatAm.
Wave 3: state media (RT, Sputnik, Global Times, IRNA) + non-English regional (AR/ES/DE).
Wave 4: LATAM depth (CO/AR/PE/VE/CL), MENA depth (SA/IL/TR/EG), Sub-Saharan Africa
         (KE/NG/ZA x8), Southeast Asia (PH/ID/SG/TH/MM x6).

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

from app.services._signal_class import derive_signal_class
from app.services.signal_text import clean_snippet

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
    # ── WAVE 4A: LATAM ────────────────────────────────────────────────────────
    # Colombian daily — covers peace process, narco, regional politics
    "el_tiempo_co": (
        "https://www.eltiempo.com/rss/colombia.xml",
        "independent", "CO", "es", False,
    ),
    "el_tiempo_mundo": (
        "https://www.eltiempo.com/rss/mundo.xml",
        "independent", "CO", "es", False,
    ),
    # Peruvian daily — Andean politics, extractive industries
    "la_republica_pe": (
        "https://larepublica.pe/rss.xml",
        "independent", "PE", "es", False,
    ),
    # Argentine tabloid/broadsheet — major Southern Cone outlet, high volume
    "clarin_ar": (
        "https://www.clarin.com/rss/lo-ultimo/",
        "independent", "AR", "es", False,
    ),
    # Venezuelan independent daily — opposition perspective, regime coverage
    "elnacional_ve": (
        "https://www.elnacional.com/feed/",
        "independent", "VE", "es", False,
    ),
    # Venezuelan investigative — Runrún, civil society, human rights angle
    "runrunes_ve": (
        "https://runrun.es/feed/",
        "independent", "VE", "es", False,
    ),
    # Chilean investigative journalism — CIPER, corruption/accountability
    "ciper_cl": (
        "https://ciperchile.cl/feed/",
        "independent", "CL", "es", False,
    ),
    # ── WAVE 4B: MENA ─────────────────────────────────────────────────────────
    # Arab News — English-language Saudi outlet; covers Gulf, oil, regional
    "arab_news": (
        "https://www.arabnews.com/rss.xml",
        "independent", "SA", "en", False,
    ),
    # Arab News Middle East section — deeper regional coverage
    "arab_news_me": (
        "https://www.arabnews.com/cat/2/rss.xml",
        "independent", "SA", "en", False,
    ),
    # Jerusalem Post — Israel/Middle East from Israeli perspective
    "jpost_mideast": (
        "https://www.jpost.com/rss/rssfeedsmiddleeastnews.aspx",
        "independent", "IL", "en", False,
    ),
    # Daily Sabah — Turkish English-language, covers Ankara, Syria, Caucasus
    "daily_sabah": (
        "https://www.dailysabah.com/rss/world/mid-east",
        "independent", "TR", "en", False,
    ),
    # Egypt Independent — Cairo-based English, regime + civil society coverage
    "egypt_indep": (
        "https://egyptindependent.com/feed/",
        "independent", "EG", "en", False,
    ),
    # ── WAVE 4C: SUB-SAHARAN AFRICA ───────────────────────────────────────────
    # Africanews — pan-continental English wire (France Médias Monde)
    "africanews": (
        "https://www.africanews.com/feed/rss",
        "wire", "FR", "en", False,
    ),
    # The Standard — Kenya second paper; Mombasa/coast angle
    "standard_ke": (
        "https://www.standardmedia.co.ke/rss/headlines.php",
        "independent", "KE", "en", False,
    ),
    # Nation Africa — Nation Media Group flagship, Kenya/East Africa
    "nation_africa": (
        "https://nation.africa/kenya/rss.xml",
        "independent", "KE", "en", False,
    ),
    # Premium Times — Nigeria's top independent digital paper
    "premium_times_ng": (
        "https://www.premiumtimesng.com/feed",
        "independent", "NG", "en", False,
    ),
    # Vanguard — Nigerian broadsheet; covers Niger Delta, politics
    "vanguard_ng": (
        "https://www.vanguardngr.com/feed/",
        "independent", "NG", "en", False,
    ),
    # The Punch — Nigeria's highest-circulation daily
    "punch_ng": (
        "https://punchng.com/feed/",
        "independent", "NG", "en", False,
    ),
    # Daily Maverick — South Africa's leading investigative outlet
    "daily_maverick": (
        "https://www.dailymaverick.co.za/rss/",
        "independent", "ZA", "en", False,
    ),
    # Mail & Guardian — South Africa; long-form, accountability journalism
    "mail_guardian_za": (
        "https://mg.co.za/feed/",
        "independent", "ZA", "en", False,
    ),
    # ── WAVE 4D: SOUTHEAST ASIA ───────────────────────────────────────────────
    # Philstar — Philippine broadsheet, covers ASEAN, South China Sea
    "philstar_ph": (
        "https://www.philstar.com/rss/world",
        "independent", "PH", "en", False,
    ),
    # Antara — Indonesia's state wire in English; Archipelago + ASEAN
    "antaranews_en": (
        "https://en.antaranews.com/rss/news.xml",
        "wire", "ID", "en", False,
    ),
    # Channel NewsAsia — Singapore wire; Southeast Asia business + politics
    "channel_newsasia": (
        "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml",
        "wire", "SG", "en", False,
    ),
    # Bangkok Post — Thailand English daily; Mekong, junta, China relations
    "bangkok_post": (
        "https://www.bangkokpost.com/rss/data/topstories.xml",
        "independent", "TH", "en", False,
    ),
    # The Irrawaddy — Myanmar exile-run, civil war, junta accountability
    "irrawaddy_mm": (
        "https://www.irrawaddy.com/feed/",
        "independent", "MM", "en", False,
    ),
    # Myanmar NOW — independent news, military conflict coverage
    "myanmar_now": (
        "https://myanmar-now.org/en/feed/",
        "independent", "MM", "en", False,
    ),
    # ── WAVE 5: NATIVE-LANGUAGE VOICE (#150/#230) ─────────────────────────────
    # Diversity audit 2026-06-22 measured English = 96.9% of language-known
    # signals and CJK = 0. RSS is uncapped (unlike NewsData's 200/day), so
    # native-language feeds are the real lever to break the monoculture. Every
    # feed below was verified live (HTTP 200 + items) on 2026-06-22.
    #
    # CHINESE (zh) — endogenous Chinese-language voice, not Western-about-China
    "dw_chinese": (
        "https://rss.dw.com/xml/rss-chi-all",
        "wire", "DE", "zh", False,
    ),
    "rfi_chinese": (
        "https://www.rfi.fr/cn/rss",
        "wire", "FR", "zh", False,
    ),
    "bbc_zhongwen": (
        "https://www.bbc.co.uk/zhongwen/simp/index.xml",
        "wire", "GB", "zh", False,
    ),
    "liberty_times_tw": (
        "https://news.ltn.com.tw/rss/all.xml",
        "independent", "TW", "zh", False,
    ),
    # JAPANESE (ja)
    "nhk_ja": (
        "https://www3.nhk.or.jp/rss/news/cat0.xml",
        "wire", "JP", "ja", False,
    ),
    "asahi_ja": (
        "https://www.asahi.com/rss/asahi/newsheadlines.rdf",
        "independent", "JP", "ja", False,
    ),
    "mainichi_ja": (
        "https://mainichi.jp/rss/etc/mainichi-flash.rss",
        "independent", "JP", "ja", False,
    ),
    # KOREAN (ko)
    "yonhap_ko": (
        "https://www.yna.co.kr/rss/news.xml",
        "wire", "KR", "ko", False,
    ),
    "yonhap_intl_ko": (
        "https://www.yna.co.kr/rss/international.xml",
        "wire", "KR", "ko", False,
    ),
    "hani_ko": (
        "https://www.hani.co.kr/rss/",
        "independent", "KR", "ko", False,
    ),
    # RUSSIAN (ru) — Kremlin framing (RT/state) vs independent (Meduza/exile)
    "meduza_ru": (
        "https://meduza.io/rss/all",
        "independent", "LV", "ru", False,
    ),
    "dw_russian": (
        "https://rss.dw.com/xml/rss-ru-all",
        "wire", "DE", "ru", False,
    ),
    "rt_russian": (
        "https://russian.rt.com/rss",
        "state", "RU", "ru", True,
    ),
    "bbc_russian": (
        "https://www.bbc.co.uk/russian/index.xml",
        "wire", "GB", "ru", False,
    ),
    # FRENCH (fr) — Francophone Europe + Africa angle
    "lemonde_fr": (
        "https://www.lemonde.fr/rss/une.xml",
        "independent", "FR", "fr", False,
    ),
    "france24_fr": (
        "https://www.france24.com/fr/rss",
        "wire", "FR", "fr", False,
    ),
    "rfi_fr": (
        "https://www.rfi.fr/fr/rss",
        "wire", "FR", "fr", False,
    ),
    # PORTUGUESE (pt) — Brazil + Lusophone
    "folha_pt": (
        "https://feeds.folha.uol.com.br/mundo/rss091.xml",
        "independent", "BR", "pt", False,
    ),
    "rfi_brasil_pt": (
        "https://www.rfi.fr/br/rss",
        "wire", "FR", "pt", False,
    ),
    # GERMAN (de) — central-European perspective
    "dw_german": (
        "https://rss.dw.com/xml/rss-de-all",
        "wire", "DE", "de", False,
    ),
    "spiegel_de": (
        "https://www.spiegel.de/schlagzeilen/tops/index.rss",
        "independent", "DE", "de", False,
    ),
    "tagesschau_de": (
        "https://www.tagesschau.de/index~rss2.xml",
        "wire", "DE", "de", False,
    ),
    # ARABIC (ar) — extends existing Arabic coverage
    "dw_arabic": (
        "https://rss.dw.com/xml/rss-ar-all",
        "wire", "DE", "ar", False,
    ),
    "bbc_arabic_rss": (
        "https://feeds.bbci.co.uk/arabic/rss.xml",
        "wire", "GB", "ar", False,
    ),
    # PERSIAN (fa) — Iran inside + diaspora
    "bbc_persian": (
        "https://www.bbc.co.uk/persian/index.xml",
        "wire", "GB", "fa", False,
    ),
    "dw_persian": (
        "https://rss.dw.com/xml/rss-per-all",
        "wire", "DE", "fa", False,
    ),
    "irna_fa": (
        "https://www.irna.ir/rss",
        "state", "IR", "fa", True,
    ),
    # HINDI (hi) — South Asia native
    "bbc_hindi": (
        "https://feeds.bbci.co.uk/hindi/rss.xml",
        "wire", "GB", "hi", False,
    ),
    # ── WAVE 6: ISLAMIC WORLD VOICE (#150/#230) ───────────────────────────────
    # Measured 2026-06-22: Muslim-majority countries are covered as SUBJECT but
    # almost never HEARD — Iran 5,932 signals at 1% Persian/Arabic, Turkey 4,060
    # at 0% Turkish, Pakistan 0% Urdu. Western-Arabic (France24/BBC/DW/RT) existed
    # but the pan-Arab voices (Al Jazeera Arabic, Sky News Arabia) and tr/ur/id/bn
    # were entirely absent. All verified live (HTTP 200 + items).
    #
    # ARABIC — pan-Arab voice (not Western-about-Arab)
    "aljazeera_ar": (
        "https://www.aljazeera.net/aljazeerarss/a7c186be-1baa-4bd4-9d80-a84db769f779/73d0e1b4-532f-45ef-b135-bfdff8b8cab9",
        "wire", "QA", "ar", False,
    ),
    "skynews_arabia": (
        "https://www.skynewsarabia.com/rss",
        "wire", "AE", "ar", False,
    ),
    # TURKISH (tr) — Turkey was 4,060 signals at 0% Turkish
    "bbc_turkce": (
        "https://www.bbc.com/turkce/index.xml",
        "wire", "GB", "tr", False,
    ),
    "anadolu_tr": (
        "https://www.aa.com.tr/tr/rss/default?cat=guncel",
        "state", "TR", "tr", True,
    ),
    "cumhuriyet_tr": (
        "https://www.cumhuriyet.com.tr/rss/son_dakika.xml",
        "independent", "TR", "tr", False,
    ),
    # URDU (ur) — Pakistan was 0% Urdu
    "bbc_urdu": (
        "https://www.bbc.com/urdu/index.xml",
        "wire", "GB", "ur", False,
    ),
    # INDONESIAN (id) — largest Muslim-majority country, was 2% Indonesian
    "antara_id": (
        "https://www.antaranews.com/rss/terkini.xml",
        "wire", "ID", "id", False,
    ),
    # BENGALI (bn) — Bangladesh
    "bbc_bengali": (
        "https://www.bbc.com/bengali/index.xml",
        "wire", "GB", "bn", False,
    ),
    "prothomalo_bn": (
        "https://www.prothomalo.com/feed/",
        "independent", "BD", "bn", False,
    ),
    # ── WAVE 7: DOMESTIC SELF-COVERAGE (#160 source-research project) ──────────
    # Self-coverage = a country's OWN press, by outlet ownership not language.
    # Audit 2026-06-22 (14d, attributable origin): these countries had ~0%
    # domestic voice — narrated only from outside. First batch of domestic
    # outlets, all verified live. Goal: every Atlas country speaks for itself.
    # (Remaining 0% gaps needing alternates: CH, BE, GR — current feeds blocked.)
    "ansa_it": (
        "https://www.ansa.it/sito/ansait_rss.xml",
        "wire", "IT", "it", False,
    ),
    "repubblica_it": (
        "https://www.repubblica.it/rss/homepage/rss2.0.xml",
        "independent", "IT", "it", False,
    ),
    "svt_se": (
        "https://www.svt.se/nyheter/rss.xml",
        "wire", "SE", "sv", False,
    ),
    "derstandard_at": (
        "https://www.derstandard.at/rss",
        "independent", "AT", "de", False,
    ),
    "nos_nl": (
        "https://feeds.nos.nl/nosnieuwsalgemeen",
        "wire", "NL", "nl", False,
    ),
    "nrk_no": (
        "https://www.nrk.no/toppsaker.rss",
        "wire", "NO", "no", False,
    ),
    "rte_ie": (
        "https://www.rte.ie/feeds/rss/?index=/news/",
        "wire", "IE", "en", False,
    ),
    "expats_cz": (
        "https://www.expats.cz/feed",
        "independent", "CZ", "en", False,
    ),
    # State media — domestic voice, flagged as state (whose interest).
    "granma_cu": (
        "http://www.granma.cu/feed",
        "state", "CU", "es", True,
    ),
    "sana_sy": (
        "https://sana.sy/en/?feed=rss2",
        "state", "SY", "en", True,
    ),
    # ── WAVE 8: DOMESTIC SELF-COVERAGE, round 2 (#235) ────────────────────────
    # Second sweep of the zero-domestic work-list. All verified live.
    "lenews_ch": (
        "https://lenews.ch/feed/",
        "independent", "CH", "en", False,
    ),
    "vrt_be": (
        "https://www.vrt.be/vrtnws/en.rss.articles.xml",
        "wire", "BE", "en", False,
    ),
    "greekcitytimes_gr": (
        "https://greekcitytimes.com/feed/",
        "independent", "GR", "en", False,
    ),
    "greekreporter_gr": (
        "https://greekreporter.com/feed/",
        "independent", "GR", "en", False,
    ),
    "telex_hu": (
        "https://telex.hu/rss",
        "independent", "HU", "hu", False,
    ),
    "dailynews_hu": (
        "https://dailynewshungary.com/feed/",
        "independent", "HU", "en", False,
    ),
    "actualite_cd": (
        "https://actualite.cd/feed",
        "independent", "CD", "fr", False,
    ),
    "radiookapi_cd": (
        "https://www.radiookapi.net/rss.xml",
        "wire", "CD", "fr", False,
    ),
    "belta_by": (
        "https://www.belta.by/rss",
        "state", "BY", "ru", True,
    ),
    "tvn_pa": (
        "https://www.tvn-2.com/rss/",
        "independent", "PA", "es", False,
    ),
    # ── WAVE 9: DOMESTIC SELF-COVERAGE, round 3 (#235) ────────────────────────
    # New Zealand had coverage but zero domestic feed.
    "rnz_nz": (
        "https://www.rnz.co.nz/rss/national.xml",
        "wire", "NZ", "en", False,
    ),
    "stuff_nz": (
        "https://www.stuff.co.nz/rss",
        "independent", "NZ", "en", False,
    ),
    # ── WAVE 10: DOMESTIC SELF-COVERAGE, round 4 (#235) ───────────────────────
    # More countries with coverage but zero domestic voice. All verified live.
    "dr_dk": (
        "https://www.dr.dk/nyheder/service/feeds/allenyheder",
        "wire", "DK", "da", False,
    ),
    "cphpost_dk": (
        "https://cphpost.dk/feed/",
        "independent", "DK", "en", False,
    ),
    "digi24_ro": (
        "https://www.digi24.ro/rss",
        "independent", "RO", "ro", False,
    ),
    "delfi_lt": (
        "https://www.delfi.lt/rss/feeds/daily.xml",
        "independent", "LT", "lt", False,
    ),
    "fmt_my": (
        "https://www.freemalaysiatoday.com/feed/",
        "independent", "MY", "en", False,
    ),
    "tcn_hr": (
        "https://total-croatia-news.com/feed/",
        "independent", "HR", "en", False,
    ),
    "newsam_am": (
        "https://news.am/eng/rss/",
        "wire", "AM", "en", False,
    ),
    "hespress_ma": (
        "https://en.hespress.com/feed",
        "independent", "MA", "en", False,
    ),
    "iraqinews_iq": (
        "https://www.iraqinews.com/feed/",
        "independent", "IQ", "en", False,
    ),
    "dabanga_sd": (
        "https://www.dabangasudan.org/en/feed",
        "independent", "SD", "en", False,
    ),
    # ── WAVE 11: SOURCE PLURALISM (#235) ──────────────────────────────────────
    # Several domestic outlets per country, not one — variety of editorial line
    # within a country (independent / state / business / left / right) so "the
    # national voice" isn't a single paper. All verified live. Adds new countries
    # Poland and Vietnam, and the first domestic outlet for Mexico.
    # France
    "lefigaro_fr": ("https://www.lefigaro.fr/rss/figaro_actualites.xml", "independent", "FR", "fr", False),
    "liberation_fr": ("https://www.liberation.fr/arc/outboundfeeds/rss/?outputType=xml", "independent", "FR", "fr", False),
    # Germany
    "zeit_de": ("https://newsfeed.zeit.de/index", "independent", "DE", "de", False),
    "faz_de": ("https://www.faz.net/rss/aktuell/", "independent", "DE", "de", False),
    # Italy
    "corriere_it": ("https://xml2.corriereobjects.it/rss/homepage.xml", "independent", "IT", "it", False),
    "lastampa_it": ("https://www.lastampa.it/rss/homepage.xml", "independent", "IT", "it", False),
    # Spain
    "elmundo_es": ("https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml", "independent", "ES", "es", False),
    "lavanguardia_es": ("https://www.lavanguardia.com/rss/home.xml", "independent", "ES", "es", False),
    # India
    "toi_in": ("https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "independent", "IN", "en", False),
    # Brazil
    "g1_br": ("https://g1.globo.com/rss/g1/", "independent", "BR", "pt", False),
    # Russia — state (TASS) + independent business (Kommersant)
    "tass_ru": ("https://tass.com/rss/v2.xml", "state", "RU", "en", True),
    "kommersant_ru": ("https://www.kommersant.ru/RSS/news.xml", "independent", "RU", "ru", False),
    # Argentina
    "lanacion_ar": ("https://www.lanacion.com.ar/arc/outboundfeeds/rss/?outputType=xml", "independent", "AR", "es", False),
    # Poland (new country)
    "notesfrompoland_pl": ("https://notesfrompoland.com/feed/", "independent", "PL", "en", False),
    # Japan
    "japantimes_jp": ("https://www.japantimes.co.jp/feed/", "independent", "JP", "en", False),
    # Mexico (first domestic)
    "lajornada_mx": ("https://www.jornada.com.mx/rss/edicion.xml?v=1", "independent", "MX", "es", False),
    # Pakistan
    "thenews_pk": ("https://www.thenews.com.pk/rss/1/1", "independent", "PK", "en", False),
    # Vietnam (new country)
    "vnexpress_vn": ("https://e.vnexpress.net/rss/news.rss", "independent", "VN", "en", False),
    # Philippines
    "inquirer_ph": ("https://www.inquirer.net/feed/", "independent", "PH", "en", False),
    "rappler_ph": ("https://www.rappler.com/feed/", "independent", "PH", "en", False),
    # Saudi Arabia
    "saudigazette_sa": ("https://saudigazette.com.sa/rssFeed/74", "independent", "SA", "en", False),
    # ── WAVE 12: PLURALISM round 2 + major-country gaps (#235) ─────────────────
    # New countries Canada, Australia, Ukraine, Portugal, Ecuador (were 0); real
    # domestic pluralism for the US/UK (had only niche/world-service feeds) and
    # China (state outlets, flagged). All verified live.
    # United States — mainstream domestic, not just niche/wire
    "npr_us": ("https://feeds.npr.org/1001/rss.xml", "independent", "US", "en", False),
    "thehill_us": ("https://thehill.com/rss/syndicator/19110", "independent", "US", "en", False),
    "abcnews_us": ("https://abcnews.go.com/abcnews/topstories", "wire", "US", "en", False),
    # United Kingdom — actual UK domestic press
    "guardian_gb": ("https://www.theguardian.com/uk/rss", "independent", "GB", "en", False),
    "independent_gb": ("https://www.independent.co.uk/news/uk/rss", "independent", "GB", "en", False),
    "skynews_gb": ("https://feeds.skynews.com/feeds/rss/home.xml", "wire", "GB", "en", False),
    # Canada (new)
    "cbc_ca": ("https://www.cbc.ca/webfeed/rss/rss-topstories", "wire", "CA", "en", False),
    # Australia (new)
    "abc_au": ("https://www.abc.net.au/news/feed/51120/rss.xml", "wire", "AU", "en", False),
    "smh_au": ("https://www.smh.com.au/rss/feed.xml", "independent", "AU", "en", False),
    # Ukraine (new) — Ukrainian-language domestic voice
    "pravda_ua": ("https://www.pravda.com.ua/rss/", "independent", "UA", "uk", False),
    # Portugal (new)
    "observador_pt": ("https://observador.pt/feed/", "independent", "PT", "pt", False),
    # Ecuador (new)
    "elcomercio_ec": ("https://www.elcomercio.com/feed", "independent", "EC", "es", False),
    # China — add to Global Times; state media, flagged
    "chinadaily_cn": ("https://www.chinadaily.com.cn/rss/china_rss.xml", "state", "CN", "en", True),
    "cgtn_cn": ("https://www.cgtn.com/subscribe/rss/section/world.xml", "state", "CN", "en", True),
    # ── WAVE 13: long-tail country coverage (#235) ────────────────────────────
    # 11 more countries with zero domestic voice — Africa, Caucasus/Central Asia,
    # Caribbean, Balkans, Nordics, South Asia. All verified live.
    "myjoy_gh": ("https://www.myjoyonline.com/feed/", "independent", "GH", "en", False),
    "lusaka_zm": ("https://www.lusakatimes.com/feed/", "independent", "ZM", "en", False),
    "astana_kz": ("https://astanatimes.com/feed/", "independent", "KZ", "en", False),
    "civil_ge": ("https://civil.ge/feed", "independent", "GE", "en", False),
    "trend_az": ("https://en.trend.az/rss/", "wire", "AZ", "en", False),
    "gleaner_jm": ("http://jamaica-gleaner.com/feed/rss.xml", "independent", "JM", "en", False),
    "prensalibre_gt": ("https://www.prensalibre.com/feed/", "independent", "GT", "es", False),
    "ktmpost_np": ("https://kathmandupost.com/rss", "independent", "NP", "en", False),
    "novinite_bg": ("https://www.novinite.com/services/news_rdf.php", "independent", "BG", "en", False),
    "yle_fi": ("https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET", "wire", "FI", "fi", False),
    "n1_rs": ("https://n1info.rs/feed/", "independent", "RS", "sr", False),
    # ── WAVE 14: long-tail coverage round 2 (#235) ────────────────────────────
    # 10 more countries with zero domestic voice. All verified live.
    "newzim_zw": ("https://www.newzimbabwe.com/feed/", "independent", "ZW", "en", False),
    "ktpress_rw": ("https://www.ktpress.rw/feed/", "independent", "RW", "en", False),
    "lostiempos_bo": ("https://www.lostiempos.com/rss.xml", "independent", "BO", "es", False),
    "diariolibre_do": ("https://www.diariolibre.com/rss/portada.xml", "independent", "DO", "es", False),
    "roya_jo": ("https://en.royanews.tv/rss", "independent", "JO", "en", False),
    "adaderana_lk": ("http://adaderana.lk/rss.php", "independent", "LK", "en", False),
    "ppp_kh": ("https://www.phnompenhpost.com/rss", "independent", "KH", "en", False),
    "err_ee": ("https://news.err.ee/rss", "wire", "EE", "en", False),
    "icelandreview_is": ("https://www.icelandreview.com/feed/", "independent", "IS", "en", False),
    "gazeta_uz": ("https://www.gazeta.uz/en/rss/", "independent", "UZ", "en", False),
    # ── WAVE 15: long-tail coverage round 3 (#235) — 31 countries, all verified ─
    # Latin America / Caribbean
    "abc_py": ("https://www.abc.com.py/arc/outboundfeeds/rss/?outputType=xml", "independent", "PY", "es", False),
    "elpais_uy": ("https://www.elpais.com.uy/rss/", "independent", "UY", "es", False),
    "montevideo_uy": ("https://www.montevideo.com.uy/anxml.aspx?59", "independent", "UY", "es", False),
    "elsalvador_sv": ("https://www.elsalvador.com/feed/", "independent", "SV", "es", False),
    "proceso_hn": ("https://proceso.hn/feed/", "independent", "HN", "es", False),
    "confidencial_ni": ("https://confidencial.digital/feed/", "independent", "NI", "es", False),
    "nacion_cr": ("https://www.nacion.com/rss/", "independent", "CR", "es", False),
    "delfino_cr": ("https://delfino.cr/feed", "independent", "CR", "es", False),
    "newsday_tt": ("https://newsday.co.tt/feed/", "independent", "TT", "en", False),
    # Africa
    "dailynews_tz": ("https://dailynews.co.tz/feed/", "state", "TZ", "en", True),
    "dakaractu_sn": ("https://www.dakaractu.com/xml/syndication.rss", "independent", "SN", "fr", False),
    "aip_ci": ("https://aip.ci/feed/", "state", "CI", "fr", True),
    "journalducameroun_cm": ("https://www.journalducameroun.com/feed/", "independent", "CM", "fr", False),
    "makaangola_ao": ("https://www.makaangola.org/feed/", "independent", "AO", "pt", False),
    "opais_mz": ("https://www.opais.co.mz/feed/", "independent", "MZ", "pt", False),
    "sundaystandard_bw": ("https://www.sundaystandard.info/feed/", "independent", "BW", "en", False),
    "bamada_ml": ("https://bamada.net/feed", "independent", "ML", "fr", False),
    "goobjoog_so": ("https://goobjoog.com/english/feed/", "independent", "SO", "en", False),
    "fanabc_et": ("https://www.fanabc.com/english/feed/", "state", "ET", "en", True),
    # Asia / Central Asia
    "ikon_mn": ("https://ikon.mn/rss", "independent", "MN", "mn", False),
    "laotiantimes_la": ("https://laotiantimes.com/feed/", "independent", "LA", "en", False),
    "pajhwok_af": ("https://pajhwok.com/feed/", "independent", "AF", "en", False),
    "timesofoman_om": ("https://timesofoman.com/feed", "independent", "OM", "en", False),
    "akipress_kg": ("https://akipress.com/rss/news.rss", "independent", "KG", "en", False),
    "24kg_kg": ("https://24.kg/rss/", "independent", "KG", "ru", False),
    "asiaplus_tj": ("https://asiaplustj.info/en/rss.xml", "independent", "TJ", "en", False),
    # Europe
    "aktuality_sk": ("https://www.aktuality.sk/rss/", "independent", "SK", "sk", False),
    "rtvslo_si": ("https://www.rtvslo.si/feeds/00.xml", "state", "SI", "sl", True),
    "delo_si": ("https://www.delo.si/rss/", "independent", "SI", "sl", False),
    "balkanweb_al": ("https://www.balkanweb.com/feed/", "independent", "AL", "sq", False),
    "mia_mk": ("https://mia.mk/feed/?lang=en", "state", "MK", "en", True),
    "meta_mk": ("https://meta.mk/en/feed/", "independent", "MK", "en", False),
    "cyprusmail_cy": ("https://cyprus-mail.com/feed/", "independent", "CY", "en", False),
    "luxtimes_lu": ("https://www.luxtimes.lu/rss", "independent", "LU", "en", False),
    "wort_lu": ("https://www.wort.lu/rss", "independent", "LU", "de", False),
    "lovinmalta_mt": ("https://lovinmalta.com/feed/", "independent", "MT", "en", False),
    # Pacific
    "fbcnews_fj": ("https://www.fbcnews.com.fj/feed/", "state", "FJ", "en", True),
    "postcourier_pg": ("https://www.postcourier.com.pg/feed/", "independent", "PG", "en", False),
    # ── WAVE 16: last gaps + pluralism (#235) ─────────────────────────────────
    # Uganda + Yemen close the long-tail (only KW/BH remain — state agencies
    # block bots / no RSS, a documented ceiling). Plus extra outlets for thin
    # high-volume countries.
    "independent_ug": ("https://www.independent.co.ug/feed/", "independent", "UG", "en", False),
    "yemenonline_ye": ("https://yemenonline.info/feed/", "independent", "YE", "en", False),
    "hindustantimes_in": ("https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml", "independent", "IN", "en", False),
    "ndtv_in": ("https://feeds.feedburner.com/ndtvnews-top-stories", "independent", "IN", "en", False),
    "dailystar_bd": ("https://www.thedailystar.net/rss.xml", "independent", "BD", "en", False),
    "dailynews_eg": ("https://www.dailynewsegypt.com/feed/", "independent", "EG", "en", False),
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
    # LATAM (Wave 4A)
    (re.compile(r'\bColombia\b|\bColombian\b|\bBogotá\b|\bBogota\b|\bPetro\b|\bFARC\b', re.I), "CO"),
    (re.compile(r'\bPeru\b|\bPeruvian\b|\bLima\b|\bBoluarte\b', re.I), "PE"),
    (re.compile(r'\bArgentina\b|\bArgentine\b|\bBuenos Aires\b|\bMilei\b', re.I), "AR"),
    (re.compile(r'\bChile\b|\bChilean\b|\bSantiago\b|\bBoric\b', re.I), "CL"),
    (re.compile(r'\bMexico\b|\bMexican\b|\bMéxico\b|\bMexico City\b|\bSheinbaum\b|\bCartel\b', re.I), "MX"),
    (re.compile(r'\bEcuador\b|\bEcuadorian\b|\bQuito\b|\bNoboa\b', re.I), "EC"),
    (re.compile(r'\bBolivia\b|\bBolivian\b|\bLa Paz\b|\bArce\b', re.I), "BO"),
    (re.compile(r'\bParaguay\b|\bParaguayan\b|\bAsunción\b', re.I), "PY"),
    (re.compile(r'\bUruguay\b|\bUruguayan\b|\bMontevideo\b', re.I), "UY"),
    (re.compile(r'\bCuba\b|\bCuban\b|\bHavana\b|\bDíaz-Canel\b', re.I), "CU"),
    (re.compile(r'\bNicaragua\b|\bNicaraguan\b|\bManagua\b|\bOrtega\b', re.I), "NI"),
    # MENA (Wave 4B)
    (re.compile(r'\bEgypt\b|\bEgyptian\b|\bCairo\b|\bEl-Sisi\b|\bSisi\b', re.I), "EG"),
    (re.compile(r'\bTurkey\b|\bTurkish\b|\bAnkara\b|\bIstanbul\b|\bErdogan\b|\bErdoğan\b', re.I), "TR"),
    (re.compile(r'\bMorocco\b|\bMoroccan\b|\bRabat\b|\bCasablanca\b', re.I), "MA"),
    (re.compile(r'\bTunisia\b|\bTunisian\b|\bTunis\b|\bSaied\b', re.I), "TN"),
    (re.compile(r'\bJordan\b|\bJordanian\b|\bAmman\b|\bAbdullah\b', re.I), "JO"),
    (re.compile(r'\bUAE\b|\bDubai\b|\bAbu Dhabi\b|\bEmirati\b', re.I), "AE"),
    (re.compile(r'\bQatar\b|\bQatari\b|\bDoha\b', re.I), "QA"),
    (re.compile(r'\bKuwait\b|\bKuwaiti\b', re.I), "KW"),
    # Sub-Saharan Africa (Wave 4C)
    (re.compile(r'\bNigeria\b|\bNigerian\b|\bAbuja\b|\bLagos\b|\bTinubu\b|\bBoko Haram\b', re.I), "NG"),
    (re.compile(r'\bKenya\b|\bKenyan\b|\bNairobi\b|\bRuto\b', re.I), "KE"),
    (re.compile(r'\bSouth Africa\b|\bSouth African\b|\bJohannesburg\b|\bPretoria\b|\bRamaphosa\b|\bANC\b', re.I), "ZA"),
    (re.compile(r'\bGhana\b|\bGhanaian\b|\bAccra\b|\bMahama\b', re.I), "GH"),
    (re.compile(r'\bTanzania\b|\bTanzanian\b|\bDar es Salaam\b|\bDodoma\b', re.I), "TZ"),
    (re.compile(r'\bUganda\b|\bUgandan\b|\bKampala\b|\bMuseveni\b', re.I), "UG"),
    (re.compile(r'\bCameroon\b|\bCameroonian\b|\bYaoundé\b|\bDouala\b', re.I), "CM"),
    (re.compile(r'\bZimbabwe\b|\bZimbabwean\b|\bHarare\b|\bMnangagwa\b', re.I), "ZW"),
    (re.compile(r'\bMozambique\b|\bMozambican\b|\bMaputo\b|\bFrelimo\b', re.I), "MZ"),
    (re.compile(r'\bAngola\b|\bAngolan\b|\bLuanda\b|\bMPLA\b', re.I), "AO"),
    (re.compile(r'\bSenegal\b|\bSenegalese\b|\bDakar\b|\bFaye\b', re.I), "SN"),
    (re.compile(r'\bMali\b|\bMalian\b|\bBamako\b|\bWagner\b', re.I), "ML"),
    (re.compile(r'\bBurkina Faso\b|\bOuagadougou\b|\bTraoré\b', re.I), "BF"),
    (re.compile(r'\bNiger\b|\bNigerien\b|\bNiamey\b|\bTiani\b', re.I), "NE"),
    # Southeast Asia (Wave 4D)
    (re.compile(r'\bPhilippines\b|\bFilipino\b|\bManila\b|\bMarcos\b|\bDuterte\b', re.I), "PH"),
    (re.compile(r'\bIndonesia\b|\bIndonesian\b|\bJakarta\b|\bPrabowo\b', re.I), "ID"),
    (re.compile(r'\bSingapore\b|\bSingaporean\b|\bLee Hsien Loong\b|\bLawrence Wong\b', re.I), "SG"),
    (re.compile(r'\bThailand\b|\bThai\b|\bBangkok\b|\bjunta\b|\bPita\b', re.I), "TH"),
    (re.compile(r'\bVietnam\b|\bVietnamese\b|\bHanoi\b|\bHo Chi Minh\b', re.I), "VN"),
    (re.compile(r'\bMalaysia\b|\bMalaysian\b|\bKuala Lumpur\b|\bAnwar\b', re.I), "MY"),
    (re.compile(r'\bCambodia\b|\bCambodian\b|\bPhnom Penh\b|\bHun Sen\b|\bHun Manet\b', re.I), "KH"),
    (re.compile(r'\bLaos\b|\bLao\b|\bVientiane\b', re.I), "LA"),
    (re.compile(r'\bBangladesh\b|\bBangladeshi\b|\bDhaka\b|\bYunus\b', re.I), "BD"),
    (re.compile(r'\bSri Lanka\b|\bSri Lankan\b|\bColombo\b|\bDissanayake\b', re.I), "LK"),
]

# ── Native-script country patterns (#150 — Problema A) ────────────────────────
# The Latin _COUNTRY_PATTERNS above are \b word-boundary regexes; a headline in
# Arabic/Persian/Urdu/Bengali/CJK/Cyrillic/Devanagari, or in Turkish (Latin but
# distinct spellings — "Suriye" ≠ "Syria"), matches none of them, so the story
# fell back to the *outlet's* home country — mis-geotagging the subject (a
# DW-Arabic story about Syria tagged DE, not SY). This table carries the SUBJECT
# lexicon those presses actually cover: the full Arab world, the majors, and the
# geopolitically hot subjects, in every script the WAVE 5/6 feeds publish.
#
# Boundary regime per script (validated by tests/test_geo_tagging_native.py):
#   • CJK — plain substring (CJK runs words together; no \b boundaries exist).
#   • Cyrillic — distinctive stem prefixes (Росси- matches Россия/России); no \b.
#   • Arabic/Persian/Urdu — _native_arabic(): \b(?:ال)?…\b, so الصين & صين both
#     match but a root never fires inside a longer word (مصر in مصرف "bank",
#     عراق in عراقيل "obstacles", قطر in قطرة "drop").
#   • Bengali/Devanagari/Turkish — _native_word(): \b…\b, catching inflected
#     forms (Bengali চীন→চীনের, Turkish Suriye→Suriye'de).
# Order is priority: a country listed earlier wins when two are named, so the
# high-coverage subjects (Iran, Russia, Turkey, Pakistan) precede their rivals.
# This is the lexical cut of #150; the e5/NLP geo path is the eventual recall
# ceiling for headlines that name a place only obliquely.


def _native_word(*alts: str) -> re.Pattern:
    """Word-boundary matcher for scripts with \\w/\\W boundaries (Turkish/
    Bengali/Devanagari). \\b on both ends catches inflected/case-suffixed forms
    (Bengali চীন→চীনের) while staying precise."""
    return re.compile(r'\b(?:' + '|'.join(alts) + r')\b')


def _native_arabic(*alts: str) -> re.Pattern:
    """Arabic-script (Arabic/Persian/Urdu) country matcher.

    Optional ال ("the") prefix so الصين and صين both match. Optional trailing
    nisba adjective suffix (ي/ی/ية/یة) so the *demonym* form matches too —
    Arabic/Persian headlines name the actor by adjective far more than by the
    country noun (المصري "the Egyptian", الإيراني "the Iranian", چینی
    "Chinese"). The trailing \\b after the optional suffix is what keeps this
    precise: a root never fires inside a longer word — verified against مصرف
    "bank" (≠EG), عراقيل "obstacles" (≠IQ), قطرة "drop" (≠QA), بھروسا "trust"
    (≠RU). The suffix matches the nisba ي but \\b still rejects عراقيل because
    the ل after عراقي has no boundary."""
    return re.compile(r'\b(?:ال)?(?:' + '|'.join(alts) + r')(?:ی|ي|یة|ية)?\b')


def _native_bengali(*alts: str) -> re.Pattern:
    """Bengali matcher — leading \\b only. Bengali takes agglutinative case
    suffixes (চীন→চীনের "of China") so a trailing boundary would miss the
    inflected form; and a word ending in a spacing vowel-sign/matra (রাশিয়া,
    U+09BE) defeats Python's trailing \\b before whitespace anyway (the matra
    and the space are both non-word, so no boundary forms). The roots here are
    long and distinctive, so a free right edge is safe."""
    return re.compile(r'\b(?:' + '|'.join(alts) + r')')


_NATIVE_COUNTRY_PATTERNS: list[tuple[re.Pattern, str]] = [
    # ── Priority subjects (win over their rivals when both are named) ──
    # Iran — before Israel and the USA
    (_native_arabic('ایران', 'إيران', 'ايران', 'تهران'), "IR"),
    (re.compile(r'伊朗|イラン|이란'), "IR"),
    (re.compile(r'Иран'), "IR"),
    (_native_word('İran'), "IR"),                       # Turkish
    (_native_bengali('ইরান'), "IR"),                    # Bengali
    # Russia — before Ukraine
    (re.compile(r'Росси|Москв|Кремл|Путин'), "RU"),
    (re.compile(r'俄罗斯|ロシア|러시아'), "RU"),
    (_native_arabic('روسیه', 'روسيا', 'روس'), "RU"),
    (re.compile(r'रूस'), "RU"),
    (_native_word('Rusya'), "RU"),                      # Turkish
    (_native_bengali('রাশিয়া'), "RU"),                 # Bengali
    # Turkey — before Syria
    (_native_arabic('تركيا', 'ترکیه', 'ترکیە'), "TR"),
    (_native_word('Türkiye', 'Türk', 'Ankara', 'İstanbul', 'Erdoğan'), "TR"),
    # Pakistan — before Afghanistan
    (_native_arabic('باكستان', 'پاکستان'), "PK"),
    (_native_bengali('পাকিস্তান'), "PK"),               # Bengali
    # ── China ──
    (re.compile(r'中国|中國|北京'), "CN"),
    (re.compile(r'중국'), "CN"),
    (_native_arabic('چین', 'صين'), "CN"),               # Persian/Urdu + Arabic
    (_native_bengali('চীন'), "CN"),                     # Bengali
    (_native_word('Çin'), "CN"),                        # Turkish
    # ── Japan ──
    (re.compile(r'日本|東京'), "JP"),
    (re.compile(r'일본'), "JP"),
    (_native_arabic('ژاپن', 'الیابان', 'یابان'), "JP"),
    # ── Koreas ──
    (re.compile(r'한국|서울|대한민국'), "KR"),
    (re.compile(r'韩国|韓国'), "KR"),
    (re.compile(r'북한|조선민주주의'), "KP"),
    (re.compile(r'朝鲜|北朝鮮'), "KP"),
    # ── Taiwan ──
    (re.compile(r'台湾|台灣|臺灣|타이완|대만'), "TW"),
    # ── India ──
    (re.compile(r'भारत|नई दिल्ली'), "IN"),
    (re.compile(r'印度|インド|인도'), "IN"),
    (_native_arabic('هند', 'بھارت', 'انڈیا'), "IN"),    # Persian + Urdu
    (_native_bengali('ভারত'), "IN"),                    # Bengali
    # ── United States ──
    (re.compile(r'美国|美國|アメリカ|미국'), "US"),
    (re.compile(r'США'), "US"),
    (_native_arabic('آمریکا', 'آمریكا', 'أمريكا', 'امریکہ', 'امریکا',
                    'الولايات المتحدة'), "US"),
    (re.compile(r'अमेरिका'), "US"),
    (_native_bengali('যুক্তরাষ্ট্র', 'আমেরিকা'), "US"), # Bengali
    (_native_word('ABD'), "US"),                        # Turkish
    # ── Israel ──
    (re.compile(r'以色列|イスラエル|이스라엘'), "IL"),
    (re.compile(r'Израил'), "IL"),
    (_native_arabic('اسرائیل', 'اسراییل', 'إسرائيل', 'اسرائيل'), "IL"),
    (re.compile(r'इज़राइल|इजरायल'), "IL"),
    (_native_bengali('ইসরায়েল', 'ইসরাইল'), "IL"),      # Bengali
    (_native_word('İsrail'), "IL"),                     # Turkish
    # ── Gaza / Palestine (project code GZ) ──
    (re.compile(r'加沙|ガザ|가자'), "GZ"),
    (re.compile(r'Газа|Газе'), "GZ"),
    (_native_arabic('غزه', 'غزة', 'فلسطین', 'فلسطين'), "GZ"),
    (_native_bengali('গাজা', 'ফিলিস্তিন'), "GZ"),       # Bengali
    (_native_word('Filistin', 'Gazze'), "GZ"),          # Turkish
    # ── Syria ──
    (re.compile(r'叙利亚|シリア|시리아'), "SY"),
    (re.compile(r'Сири'), "SY"),
    (_native_arabic('سوریه', 'سوريه', 'سوريا', 'سورية', 'سوري', 'دمشق'), "SY"),
    (_native_word('Suriye'), "SY"),                     # Turkish
    # ── Germany (DW native-language outlets cover it heavily) ──
    (re.compile(r'德国|德國|ドイツ|독일'), "DE"),
    (re.compile(r'Германи'), "DE"),
    (_native_arabic('آلمان', 'ألمانيا'), "DE"),
    (_native_word('Almanya'), "DE"),                    # Turkish
    # ── Ukraine (after Russia) ──
    (re.compile(r'Украин|Киев|Зеленск'), "UA"),
    (re.compile(r'乌克兰|ウクライナ|우크라이나'), "UA"),
    (_native_arabic('اوکراین', 'أوكرانيا', 'یوکرین'), "UA"),
    (re.compile(r'यूक्रेन'), "UA"),
    (_native_word('Ukrayna'), "UA"),                    # Turkish
    (_native_bengali('ইউক্রেন'), "UA"),                 # Bengali
    # ── Afghanistan (after Pakistan) ──
    (_native_arabic('افغانستان', 'أفغانستان'), "AF"),
    # ── Arab world (subject lexicon of the pan-Arab presses) ──
    (_native_arabic('مصر', 'القاهرة', 'السیسی', 'السيسي'), "EG"),
    (_native_word('Mısır'), "EG"),                      # Turkish
    (_native_arabic('السعودية', 'سعودية', 'سعودي', 'عربستان', 'سعودی عرب', 'سعودی'), "SA"),
    (_native_arabic('عراق'), "IQ"),
    (_native_word('Irak'), "IQ"),                       # Turkish
    (_native_arabic('لبنان'), "LB"),
    (_native_arabic('یمن', 'الحوثیون', 'الحوثيون'), "YE"),
    (_native_arabic('سودان'), "SD"),
    (_native_arabic('ليبيا', 'ليبي'), "LY"),
    (_native_arabic('الأردن', 'الاردن', 'اردن'), "JO"),
    (_native_arabic('قطر'), "QA"),
    (_native_arabic('الإمارات', 'الامارات'), "AE"),
    (_native_arabic('الكويت', 'کویت', 'كويت'), "KW"),
    (_native_arabic('المغرب', 'مغرب'), "MA"),
    (_native_arabic('تونس'), "TN"),
    (_native_arabic('الجزائر', 'جزائر'), "DZ"),
    # ── Other native-script subjects ──
    (_native_word('Yunanistan'), "GR"),                 # Turkish (Greece)
    (_native_bengali('বাংলাদেশ'), "BD"),                # Bengali
    (_native_bengali('মিয়ানমার'), "MM"),               # Bengali (Myanmar)
]


def _scan_country(text: str) -> Optional[str]:
    """First ISO2 whose subject pattern matches ``text``, else None.

    Latin keyword patterns first, then native-script patterns (#150) so
    non-Latin headlines geo-tag to the story subject rather than falling
    back to the outlet's home country.
    """
    if not text:
        return None
    for pattern, iso2 in _COUNTRY_PATTERNS:
        if pattern.search(text):
            return iso2
    for pattern, iso2 in _NATIVE_COUNTRY_PATTERNS:
        if pattern.search(text):
            return iso2
    return None


def extract_country(title: str, snippet: str = "") -> Optional[str]:
    """Return the story's SUBJECT country (ISO2) from the TITLE, or None.

    Only the title is scanned. The title is the story's subject; the snippet
    (RSS summary / provider description) is supporting body where *incidental*
    country mentions live — syndicated "related stories" blocks, photo
    captions, datelines, "elsewhere in the world" footers, boilerplate. The
    old implementation scanned the concatenated ``title + snippet`` and
    returned the FIRST country matched ANYWHERE, so one passing France token
    in a description hijacked the whole signal:

        title  = "Adam Triggs | Pauline Hanson will be her own downfall …"
        snippet= "… Macron and France's parliament clash over the budget in Paris."
        → confidently tagged FR (areanews.com.au, source_origin_country=AU),
          surfacing "concentrated in France" + FRANCE chips on an AU story.

    Tagging the subject off an incidental body mention is worse than not
    tagging at all: every caller already falls back to a more reliable signal
    when this returns None — RSS to the outlet's ``source_country``, NewsData
    to the provider's own country field, all to ``"XX"``. So a silent title
    yields None and the caller picks the honest fallback, instead of asserting
    a country at high confidence off the body. The ``snippet`` parameter is
    kept for call-site compatibility but is intentionally NOT used for subject
    geo-tagging. (Real subject recall from body text is the e5/NLP geo path,
    the clean #150 end state.)
    """
    return _scan_country(title)


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
            # Read raw bytes, not resp.text(): resp.text() assumes utf-8 and
            # throws UnicodeDecodeError on latin-1/iso-8859-1 feeds (folha_pt,
            # antaranews_en). feedparser detects encoding from the XML
            # declaration / HTTP charset itself when handed bytes.
            content = await resp.read()

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
                # The outlet's HOME country (who is speaking), distinct from
                # country_code (the story's subject). Required to tell a country's
                # OWN press (self-coverage) apart from foreign outlets — including
                # foreign broadcasters in local languages (BBC Persian = GB, not
                # Iranian voice). Previously discarded; now persisted.
                "source_origin_country": source_country,
                "geo_confidence": 0.6,     # RSS geo = keyword match, lower confidence than GDELT
                "attribution_method": "rss_feed",
                "is_state_media": is_state_media,
                # Semantic class (migration 021) — derived from provenance
                "signal_class": derive_signal_class(source_family, "rss_feed", is_state_media),
                "snippet": clean_snippet(snippet),
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
                        source_family, source_lang, geo_confidence, attribution_method, is_state_media,
                        signal_class, snippet, source_origin_country
                    )
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,
                            $16,$17,$18,$19,$20,$21,$22,$23)
                    ON CONFLICT (source_url) WHERE source_url IS NOT NULL DO NOTHING
                    """,
                    s["timestamp"], s["country_code"], s["latitude"], s["longitude"],
                    s["sentiment"], s["source_url"], s["source_name"], s["headline"],
                    s["themes"], s["persons"],
                    s["is_crisis"], s["crisis_score"], s["crisis_themes"],
                    s["severity"], s["event_type"],
                    s["source_family"], s["source_lang"], s["geo_confidence"],
                    s["attribution_method"], s["is_state_media"],
                    s.get("signal_class", "reporting"),
                    s.get("snippet"),
                    s.get("source_origin_country"),
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
