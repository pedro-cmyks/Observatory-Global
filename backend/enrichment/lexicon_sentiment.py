"""
Multilingual lexicon-grade sentiment scorer (ADR-0004, issue #164).

Cheap signed-token scorer for historical backfill (`>30 days` tail).
Writes nlp_sentiment + nlp_confidence to signals_v2 with nlp_method='lexicon'.

Quality is intentionally lower than the transformer pipeline. Confidence is
capped at 0.5 so consumers can filter on `nlp_method = 'transformer'` when
they need higher recall, or accept `nlp_method IN ('transformer', 'lexicon')`
when they need historical coverage.

Languages in v1: en, es, fr, ar, pt. New languages plug in by adding a
LEXICON entry.

CLI:
    python -m enrichment.lexicon_sentiment --limit 5000 --dry-run
"""
from __future__ import annotations

import argparse
import asyncio
import html
import logging
import os
import re
import time
from typing import Iterable

import asyncpg

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [lexicon] %(levelname)s %(message)s")

# ── Lexicons (seed; expand with curated word lists in a follow-up) ──────────
# Values are signed weights in [-3, +3]. Tokens are lowercased on lookup.

LEXICON_EN: dict[str, float] = {
    # Conflict / violence
    "war": -2.5, "attack": -2.5, "killed": -3, "dead": -2.5, "wounded": -2,
    "crisis": -2, "violence": -2.5, "protest": -1.5, "riot": -2.5, "tension": -1.5,
    "sanction": -2, "embargo": -2, "threat": -2, "fail": -1.5, "collapse": -2.5,
    "corruption": -2, "scandal": -2, "fraud": -2, "fear": -1.5, "panic": -2,
    "famine": -3, "drought": -2, "disaster": -2.5, "deadly": -3, "fatal": -3,
    "strike": -1.5, "denounce": -2, "condemn": -2, "abuse": -2.5, "violate": -2,
    "murder": -3, "bomb": -3, "bombing": -3, "terrorist": -3, "terror": -2.5,
    "destroy": -2.5, "destroyed": -2.5, "devastate": -2.5, "devastating": -2.5,
    "missile": -2, "drone": -1, "shelling": -2.5, "airstrike": -2.5, "assault": -2.5,
    "battle": -2, "clash": -2, "fighting": -2, "invade": -2.5, "invasion": -2.5,
    "occupy": -1.5, "siege": -2.5, "kidnap": -3, "hostage": -2.5, "captured": -1.5,
    "raid": -2, "raids": -2, "explosion": -2.5, "blast": -2.5, "casualties": -2.5,
    # Crime / law
    "arrest": -1.5, "arrested": -1.5, "indict": -2, "indicted": -2, "charged": -1.5,
    "convict": -2, "convicted": -2, "sentence": -1.5, "sentenced": -1.5, "jail": -2,
    "prison": -1.5, "imprisoned": -2, "guilty": -1.5, "crime": -2, "criminal": -2,
    "investigation": -1, "probe": -1, "raid": -1.5, "trafficking": -2.5, "smuggle": -2,
    # Disaster / environment
    "flood": -2, "earthquake": -2.5, "hurricane": -2.5, "storm": -1.5, "wildfire": -2.5,
    "evacuate": -2, "evacuation": -2, "victim": -2, "victims": -2, "tragedy": -2.5,
    "tragic": -2.5, "outbreak": -2, "pandemic": -2, "epidemic": -2, "infected": -1.5,
    # Economic stress
    "recession": -2.5, "inflation": -1.5, "default": -2.5, "bankrupt": -2.5, "crash": -2.5,
    "deficit": -1.5, "downturn": -2, "layoff": -2, "layoffs": -2, "shortage": -1.5,
    "plunge": -2, "tumble": -1.5, "slump": -2, "loss": -1.5, "losses": -1.5,
    # Political
    "dictator": -2, "regime": -1, "oppress": -2, "censor": -2, "censorship": -2,
    "coup": -2.5, "impeach": -2, "ousted": -2, "expelled": -1.5, "banned": -1.5,
    "reject": -1, "rejected": -1, "resign": -1.5, "resigned": -1.5, "scandal": -2,
    # Positive — peace / cooperation
    "peace": 2.5, "agreement": 2, "deal": 1.5, "treaty": 2, "ceasefire": 2.5,
    "aid": 1.5, "recovery": 2, "growth": 2, "victory": 2, "win": 1.5,
    "release": 1, "cooperation": 2, "support": 1.5, "rescue": 2, "reform": 1.5,
    "free": 1.5, "save": 2, "improve": 1.5, "success": 2, "elect": 1,
    "stabilize": 2, "celebrate": 2, "innovation": 1.5, "boost": 1.5, "praise": 2,
    # Positive — diplomatic / economic
    "talks": 1, "negotiation": 1.5, "negotiate": 1.5, "summit": 1, "alliance": 1.5,
    "partnership": 1.5, "investment": 1.5, "expand": 1, "rise": 1, "surge": 1.5,
    "gain": 1, "profit": 1.5, "record": 1, "milestone": 1.5, "breakthrough": 2.5,
    "approve": 1.5, "approved": 1.5, "signed": 1, "sign": 1, "launch": 1,
    "launched": 1, "open": 0.5, "opens": 0.5, "welcome": 1.5, "honor": 1.5,
    # Positive — relief / humanitarian
    "freed": 2, "released": 1.5, "survivor": 1.5, "saved": 2, "donated": 1.5,
    "donation": 1.5, "rebuild": 2, "rebuilt": 2, "restored": 2, "restore": 1.5,
    "vaccinate": 1.5, "cure": 2, "cured": 2, "treatment": 1, "heal": 1.5,
    "champion": 1.5, "award": 1.5, "honored": 1.5,
}

LEXICON_ES: dict[str, float] = {
    "guerra": -2.5, "ataque": -2.5, "muertos": -3, "muerto": -2.5, "heridos": -2,
    "crisis": -2, "violencia": -2.5, "protesta": -1.5, "tensión": -1.5, "tension": -1.5,
    "sanción": -2, "sancion": -2, "amenaza": -2, "fracaso": -1.5, "colapso": -2.5,
    "corrupción": -2, "corrupcion": -2, "escándalo": -2, "fraude": -2, "miedo": -1.5,
    "hambruna": -3, "sequía": -2, "sequia": -2, "desastre": -2.5, "mortal": -3,
    "huelga": -1.5, "condena": -2, "denuncia": -2, "abuso": -2.5, "violar": -2,
    # Conflict / crime expansion
    "asesinato": -3, "asesinado": -3, "asesinar": -3, "bomba": -3, "explosión": -2.5,
    "explosion": -2.5, "terrorista": -3, "terror": -2.5, "destruir": -2.5, "destruido": -2.5,
    "invasión": -2.5, "invasion": -2.5, "invadir": -2.5, "secuestro": -3, "secuestrado": -3,
    "rehén": -2.5, "rehen": -2.5, "ataques": -2.5, "combates": -2, "asedio": -2.5,
    "redada": -1.5, "redadas": -1.5, "víctimas": -2, "victimas": -2, "trágico": -2.5, "tragico": -2.5,
    "tragedia": -2.5, "detenido": -1.5, "detenidos": -1.5, "arrestado": -1.5, "arrestar": -1.5,
    "cárcel": -1.5, "carcel": -1.5, "prisión": -1.5, "prision": -1.5, "culpable": -1.5,
    "crimen": -2, "criminal": -2, "investigación": -1, "investigacion": -1,
    # Disaster / economic
    "inundación": -2, "inundacion": -2, "terremoto": -2.5, "huracán": -2.5, "huracan": -2.5,
    "tormenta": -1.5, "incendio": -2, "evacuar": -2, "evacuación": -2, "evacuacion": -2,
    "brote": -2, "pandemia": -2, "epidemia": -2, "recesión": -2.5, "recesion": -2.5,
    "inflación": -1.5, "inflacion": -1.5, "quiebra": -2.5, "déficit": -1.5, "deficit": -1.5,
    "caída": -2, "caida": -2, "pérdida": -1.5, "perdida": -1.5, "pérdidas": -1.5, "perdidas": -1.5,
    # Political
    "dictador": -2, "régimen": -1, "regimen": -1, "censura": -2, "golpe": -2.5,
    "destituido": -2, "expulsado": -1.5, "prohibido": -1.5, "renunció": -1.5, "renuncio": -1.5,
    "rechazado": -1, "rechazar": -1,
    # Positive expansion
    "paz": 2.5, "acuerdo": 2, "tratado": 2, "tregua": 2.5, "alto el fuego": 2.5,
    "ayuda": 1.5, "recuperación": 2, "recuperacion": 2, "crecimiento": 2, "victoria": 2,
    "liberar": 1, "cooperación": 2, "cooperacion": 2, "apoyo": 1.5, "rescate": 2,
    "reforma": 1.5, "libre": 1.5, "salvar": 2, "mejorar": 1.5, "éxito": 2, "exito": 2,
    "estabilizar": 2, "celebrar": 2, "innovación": 1.5, "innovacion": 1.5, "elogio": 2,
    "negociación": 1.5, "negociacion": 1.5, "diálogo": 1, "dialogo": 1, "cumbre": 1,
    "alianza": 1.5, "asociación": 1.5, "asociacion": 1.5, "inversión": 1.5, "inversion": 1.5,
    "ganancia": 1.5, "récord": 1, "record": 1, "hito": 1.5, "aprobado": 1.5, "aprobar": 1.5,
    "firmado": 1, "firmar": 1, "lanzar": 1, "lanzado": 1, "bienvenida": 1.5,
    "liberado": 2, "salvado": 2, "donación": 1.5, "donacion": 1.5, "reconstruir": 2,
    "restaurado": 2, "vacuna": 1.5, "vacunar": 1.5, "cura": 2, "tratamiento": 1,
    "premio": 1.5, "homenaje": 1.5,
}

LEXICON_FR: dict[str, float] = {
    "guerre": -2.5, "attaque": -2.5, "morts": -3, "mort": -2.5, "blessés": -2, "blesses": -2,
    "crise": -2, "violence": -2.5, "manifestation": -1.5, "tension": -1.5,
    "sanction": -2, "embargo": -2, "menace": -2, "échec": -1.5, "echec": -1.5,
    "corruption": -2, "scandale": -2, "fraude": -2, "peur": -1.5, "panique": -2,
    "famine": -3, "sécheresse": -2, "secheresse": -2, "catastrophe": -2.5, "mortel": -3,
    "grève": -1.5, "greve": -1.5, "dénoncer": -2, "denoncer": -2, "condamner": -2,
    "paix": 2.5, "accord": 2, "traité": 2, "traite": 2, "cessez-le-feu": 2.5,
    "aide": 1.5, "reprise": 2, "croissance": 2, "victoire": 2, "victoire": 2,
    "libérer": 1, "liberer": 1, "coopération": 2, "cooperation": 2, "soutien": 1.5,
    "sauvetage": 2, "réforme": 1.5, "reforme": 1.5, "libre": 1.5, "sauver": 2,
    "succès": 2, "succes": 2, "stabiliser": 2, "célébrer": 2, "celebrer": 2,
}

LEXICON_PT: dict[str, float] = {
    "guerra": -2.5, "ataque": -2.5, "mortos": -3, "morto": -2.5, "feridos": -2,
    "crise": -2, "violência": -2.5, "violencia": -2.5, "protesto": -1.5, "tensão": -1.5,
    "sanção": -2, "sancao": -2, "ameaça": -2, "ameaca": -2, "fracasso": -1.5, "colapso": -2.5,
    "corrupção": -2, "corrupcao": -2, "escândalo": -2, "fraude": -2, "medo": -1.5,
    "fome": -3, "seca": -2, "desastre": -2.5, "mortal": -3,
    "greve": -1.5, "condenar": -2, "denunciar": -2, "abuso": -2.5, "violar": -2,
    "assassinato": -3, "bomba": -3, "explosão": -2.5, "explosao": -2.5, "terrorista": -3,
    "invasão": -2.5, "invasao": -2.5, "sequestro": -3, "refém": -2.5, "refem": -2.5,
    "vítimas": -2, "vitimas": -2, "trágico": -2.5, "tragico": -2.5, "tragédia": -2.5, "tragedia": -2.5,
    "detido": -1.5, "preso": -1.5, "prisão": -1.5, "prisao": -1.5, "culpado": -1.5,
    "inundação": -2, "inundacao": -2, "terremoto": -2.5, "incêndio": -2, "incendio": -2,
    "surto": -2, "pandemia": -2, "recessão": -2.5, "recessao": -2.5, "inflação": -1.5, "inflacao": -1.5,
    "falência": -2.5, "falencia": -2.5, "queda": -2, "perda": -1.5, "perdas": -1.5,
    "golpe": -2.5, "renúncia": -1.5, "renuncia": -1.5, "rejeitado": -1,
    "paz": 2.5, "acordo": 2, "tratado": 2, "trégua": 2.5, "tregua": 2.5,
    "ajuda": 1.5, "recuperação": 2, "recuperacao": 2, "crescimento": 2, "vitória": 2,
    "libertar": 1, "cooperação": 2, "cooperacao": 2, "apoio": 1.5, "resgate": 2,
    "reforma": 1.5, "livre": 1.5, "salvar": 2, "melhorar": 1.5, "sucesso": 2,
    "negociação": 1.5, "negociacao": 1.5, "cúpula": 1, "cupula": 1, "aliança": 1.5, "alianca": 1.5,
    "investimento": 1.5, "lucro": 1.5, "marco": 1, "aprovado": 1.5, "assinado": 1,
    "lançamento": 1, "lancamento": 1, "boas-vindas": 1.5, "libertado": 2,
    "vacina": 1.5, "vacinar": 1.5, "cura": 2, "prêmio": 1.5, "premio": 1.5,
}

LEXICON_IT: dict[str, float] = {
    "guerra": -2.5, "attacco": -2.5, "morti": -3, "morto": -2.5, "feriti": -2,
    "crisi": -2, "violenza": -2.5, "protesta": -1.5, "tensione": -1.5,
    "sanzione": -2, "minaccia": -2, "crollo": -2.5, "corruzione": -2, "scandalo": -2,
    "frode": -2, "paura": -1.5, "carestia": -3, "siccità": -2, "siccita": -2,
    "disastro": -2.5, "mortale": -3, "sciopero": -1.5, "condannare": -2, "abuso": -2.5,
    "omicidio": -3, "bomba": -3, "esplosione": -2.5, "terrorista": -3, "invasione": -2.5,
    "rapimento": -3, "ostaggio": -2.5, "vittime": -2, "tragico": -2.5, "tragedia": -2.5,
    "arrestato": -1.5, "carcere": -1.5, "prigione": -1.5, "colpevole": -1.5,
    "alluvione": -2, "terremoto": -2.5, "uragano": -2.5, "incendio": -2,
    "epidemia": -2, "recessione": -2.5, "inflazione": -1.5, "fallimento": -2.5,
    "perdita": -1.5, "perdite": -1.5, "golpe": -2.5, "dimesso": -1.5,
    "pace": 2.5, "accordo": 2, "trattato": 2, "tregua": 2.5, "cessate il fuoco": 2.5,
    "aiuto": 1.5, "ripresa": 2, "crescita": 2, "vittoria": 2, "vincere": 1.5,
    "liberare": 1, "cooperazione": 2, "sostegno": 1.5, "salvataggio": 2, "riforma": 1.5,
    "libero": 1.5, "salvare": 2, "migliorare": 1.5, "successo": 2, "celebrare": 2,
    "negoziato": 1.5, "vertice": 1, "alleanza": 1.5, "investimento": 1.5,
    "approvato": 1.5, "firmato": 1, "vaccino": 1.5,
}

LEXICON_DE: dict[str, float] = {
    "krieg": -2.5, "angriff": -2.5, "tote": -3, "tot": -2.5, "verletzt": -2,
    "krise": -2, "gewalt": -2.5, "protest": -1.5, "spannung": -1.5,
    "sanktion": -2, "drohung": -2, "scheitern": -1.5, "zusammenbruch": -2.5,
    "korruption": -2, "skandal": -2, "betrug": -2, "angst": -1.5,
    "hungersnot": -3, "dürre": -2, "duerre": -2, "katastrophe": -2.5, "tödlich": -3, "toedlich": -3,
    "streik": -1.5, "verurteilen": -2, "missbrauch": -2.5,
    "mord": -3, "bombe": -3, "explosion": -2.5, "terrorist": -3, "invasion": -2.5,
    "geisel": -2.5, "opfer": -2, "tragisch": -2.5, "tragödie": -2.5, "tragoedie": -2.5,
    "festgenommen": -1.5, "verhaftet": -1.5, "gefängnis": -1.5, "gefaengnis": -1.5,
    "schuldig": -1.5, "flut": -2, "erdbeben": -2.5, "sturm": -1.5, "brand": -2,
    "ausbruch": -2, "pandemie": -2, "rezession": -2.5, "inflation": -1.5, "insolvenz": -2.5,
    "verlust": -1.5, "putsch": -2.5, "rücktritt": -1.5, "ruecktritt": -1.5,
    "frieden": 2.5, "abkommen": 2, "vertrag": 2, "waffenstillstand": 2.5,
    "hilfe": 1.5, "erholung": 2, "wachstum": 2, "sieg": 2, "gewinnen": 1.5,
    "freilassen": 1, "kooperation": 2, "unterstützung": 1.5, "unterstuetzung": 1.5,
    "rettung": 2, "reform": 1.5, "frei": 1.5, "retten": 2, "verbessern": 1.5,
    "erfolg": 2, "feiern": 2, "verhandlung": 1.5, "gipfel": 1, "allianz": 1.5,
    "investition": 1.5, "genehmigt": 1.5, "unterzeichnet": 1, "impfstoff": 1.5,
}

LEXICON_AR: dict[str, float] = {
    # Compact seed; expand later with curated MSA lexicon
    "حرب": -2.5, "هجوم": -2.5, "قتل": -3, "قتلى": -3, "جرحى": -2,
    "أزمة": -2, "عنف": -2.5, "احتجاج": -1.5, "توتر": -1.5,
    "عقوبة": -2, "تهديد": -2, "فشل": -1.5, "انهيار": -2.5,
    "فساد": -2, "فضيحة": -2, "احتيال": -2, "خوف": -1.5,
    "مجاعة": -3, "جفاف": -2, "كارثة": -2.5, "قاتل": -3,
    "إضراب": -1.5, "إدانة": -2, "تنديد": -2, "انتهاك": -2,
    "سلام": 2.5, "اتفاق": 2, "معاهدة": 2, "هدنة": 2.5, "وقف إطلاق النار": 2.5,
    "مساعدة": 1.5, "تعافي": 2, "نمو": 2, "نصر": 2, "فوز": 1.5,
    "إفراج": 1, "تعاون": 2, "دعم": 1.5, "إنقاذ": 2, "إصلاح": 1.5,
    "حر": 1.5, "إنقاذ": 2, "تحسين": 1.5, "نجاح": 2,
}

_SEED_LEXICONS: dict[str, dict[str, float]] = {
    "en": LEXICON_EN,
    "es": LEXICON_ES,
    "fr": LEXICON_FR,
    "pt": LEXICON_PT,
    "ar": LEXICON_AR,
    "it": LEXICON_IT,
    "de": LEXICON_DE,
}


def _load_mined_lexicon(lang: str) -> dict[str, float]:
    """Load mined vocabulary snapshot (issue #185) for a language if present.

    Snapshots are checked into the repo at enrichment/lexicons/<lang>.mined.json
    by backend/scripts/mine_lexicon_vocab.py. Missing files are normal (mining
    has not run yet for that lang) and return an empty dict.
    """
    import json
    import os

    path = os.path.join(os.path.dirname(__file__), "lexicons", f"{lang}.mined.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            logger.warning("Mined lexicon %s is not a dict — ignoring", path)
            return {}
        return {str(k).lower(): float(v) for k, v in data.items()}
    except Exception as exc:
        logger.warning("Failed to load mined lexicon %s: %s", path, exc)
        return {}


def _merge_lexicons(seed: dict[str, float], mined: dict[str, float]) -> dict[str, float]:
    """Compose seed + mined vocab. Seeds always win on conflict so curated
    high-confidence weights are never overridden by automatically derived ones.
    """
    merged: dict[str, float] = dict(mined)
    merged.update(seed)
    return merged


LEXICONS: dict[str, dict[str, float]] = {
    lang: _merge_lexicons(seed, _load_mined_lexicon(lang))
    for lang, seed in _SEED_LEXICONS.items()
}

# Script-based detection fallback when source_lang is unknown.
ARABIC_RE = re.compile(r"[؀-ۿ]")
LATIN_RE = re.compile(r"[A-Za-z]")
TOKEN_RE = re.compile(r"\w+", re.UNICODE)

CONFIDENCE_CEILING = 0.5
MIN_TOKENS = 3


def _clean(text: str) -> str:
    """Decode HTML numeric/named character references before tokenisation.

    Upstream feeds emit `&#xE4;`, `&#auml;`, etc. instead of UTF-8. Without
    decoding, the tokenizer splits `verk&#xE4;ndet` into `verk` + `xe4` +
    `ndet`, which prevents lexicon hits and pushes the row into the
    `fast_neutral` fallback. Mirrors the same step in scripts.mine_lexicon_vocab.
    """
    return html.unescape(text) if text else ""


def _detect_lang(text: str, hint: str | None) -> str | None:
    """Resolve which lexicon to apply.

    The hint from `source_lang` wins when available and supported. Otherwise
    we fall back to script presence — Arabic script picks the AR lexicon,
    Latin script defaults to EN and lets per-language seed words override.
    """
    if hint:
        lang = hint.lower()
        if lang in LEXICONS:
            return lang
    cleaned = _clean(text)
    if ARABIC_RE.search(cleaned):
        return "ar"
    if LATIN_RE.search(cleaned):
        return "en"
    return None


def _score(text: str, lexicon: dict[str, float]) -> tuple[float, float, int]:
    """Compute (signed_score, confidence, token_count) for a single headline."""
    tokens = [t.lower() for t in TOKEN_RE.findall(_clean(text))]
    if len(tokens) < MIN_TOKENS:
        return 0.0, 0.0, len(tokens)
    raw = sum(lexicon.get(tok, 0.0) for tok in tokens)
    score = max(-5.0, min(5.0, raw))
    confidence = min(CONFIDENCE_CEILING, (abs(score) / 5.0) * CONFIDENCE_CEILING)
    return round(score, 3), round(confidence, 3), len(tokens)


def score_headline(text: str, source_lang: str | None = None) -> tuple[float, float, str | None]:
    """Score a single headline. Returns (sentiment, confidence, lang_used)."""
    if not text or not text.strip():
        return 0.0, 0.0, None
    lang = _detect_lang(text, source_lang)
    if lang is None:
        return 0.0, 0.0, None
    sentiment, confidence, _ = _score(text, LEXICONS[lang])
    return sentiment, confidence, lang


# ── Backfill runner ──────────────────────────────────────────────────────────
PRIORITY_SELECT_SQL = """
SELECT id, headline, source_lang
FROM signals_v2
WHERE nlp_processed_at IS NULL
  AND nlp_method IS NULL
  AND headline IS NOT NULL
  AND LENGTH(headline) > 10
  AND created_at > NOW() - INTERVAL '15 days'
ORDER BY timestamp DESC
LIMIT $1
"""

UPDATE_SQL = """
UPDATE signals_v2
SET nlp_sentiment = $1,
    nlp_confidence = $2,
    nlp_method = 'lexicon',
    nlp_processed_at = NOW()
WHERE id = $3
"""


async def _run_backfill(conn: asyncpg.Connection, limit: int, dry_run: bool) -> int:
    rows = await conn.fetch(PRIORITY_SELECT_SQL, limit)
    if not rows:
        logger.info("Lexicon backfill: no eligible rows")
        return 0

    records: list[tuple[float, float, int]] = []
    skipped_no_lang = 0
    skipped_short = 0
    for row in rows:
        sentiment, confidence, lang = score_headline(row["headline"], row["source_lang"])
        if lang is None:
            skipped_no_lang += 1
            continue
        if confidence == 0.0 and sentiment == 0.0:
            # Either too short, or no lexicon hits. Skip silently — the row stays
            # unscored until a future iteration (or transformer worker) picks it up.
            skipped_short += 1
            continue
        records.append((sentiment, confidence, row["id"]))

    if not dry_run and records:
        await conn.executemany(UPDATE_SQL, records)

    logger.info(
        "Lexicon backfill: scored=%d skipped_no_lang=%d skipped_short=%d total_fetched=%d",
        len(records), skipped_no_lang, skipped_short, len(rows),
    )
    return len(records)


async def _cli(limit: int, dry_run: bool) -> None:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")
    conn = await asyncpg.connect(db_url)
    started = time.monotonic()
    try:
        scored = await _run_backfill(conn, limit, dry_run)
    finally:
        await conn.close()
    logger.info("Backfill done: scored=%d duration=%.1fs dry_run=%s", scored, time.monotonic() - started, dry_run)


def _parse_args():
    parser = argparse.ArgumentParser(description="Atlas lexicon-grade sentiment backfill")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main():
    args = _parse_args()
    asyncio.run(_cli(args.limit, args.dry_run))


if __name__ == "__main__":
    main()
