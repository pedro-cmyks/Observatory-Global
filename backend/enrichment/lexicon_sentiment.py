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
    # Negative
    "war": -2.5, "attack": -2.5, "killed": -3, "dead": -2.5, "wounded": -2,
    "crisis": -2, "violence": -2.5, "protest": -1.5, "riot": -2.5, "tension": -1.5,
    "sanction": -2, "embargo": -2, "threat": -2, "fail": -1.5, "collapse": -2.5,
    "corruption": -2, "scandal": -2, "fraud": -2, "fear": -1.5, "panic": -2,
    "famine": -3, "drought": -2, "disaster": -2.5, "deadly": -3, "fatal": -3,
    "strike": -1.5, "denounce": -2, "condemn": -2, "abuse": -2.5, "violate": -2,
    # Positive
    "peace": 2.5, "agreement": 2, "deal": 1.5, "treaty": 2, "ceasefire": 2.5,
    "aid": 1.5, "recovery": 2, "growth": 2, "victory": 2, "win": 1.5,
    "release": 1, "cooperation": 2, "support": 1.5, "rescue": 2, "reform": 1.5,
    "free": 1.5, "save": 2, "improve": 1.5, "success": 2, "elect": 1,
    "stabilize": 2, "celebrate": 2, "innovation": 1.5, "boost": 1.5, "praise": 2,
}

LEXICON_ES: dict[str, float] = {
    "guerra": -2.5, "ataque": -2.5, "muertos": -3, "muerto": -2.5, "heridos": -2,
    "crisis": -2, "violencia": -2.5, "protesta": -1.5, "tensión": -1.5, "tension": -1.5,
    "sanción": -2, "sancion": -2, "amenaza": -2, "fracaso": -1.5, "colapso": -2.5,
    "corrupción": -2, "corrupcion": -2, "escándalo": -2, "fraude": -2, "miedo": -1.5,
    "hambruna": -3, "sequía": -2, "sequia": -2, "desastre": -2.5, "mortal": -3,
    "huelga": -1.5, "condena": -2, "denuncia": -2, "abuso": -2.5, "violar": -2,
    "paz": 2.5, "acuerdo": 2, "tratado": 2, "tregua": 2.5, "alto el fuego": 2.5,
    "ayuda": 1.5, "recuperación": 2, "recuperacion": 2, "crecimiento": 2, "victoria": 2,
    "liberar": 1, "cooperación": 2, "cooperacion": 2, "apoyo": 1.5, "rescate": 2,
    "reforma": 1.5, "libre": 1.5, "salvar": 2, "mejorar": 1.5, "éxito": 2, "exito": 2,
    "estabilizar": 2, "celebrar": 2, "innovación": 1.5, "innovacion": 1.5, "elogio": 2,
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
    "paz": 2.5, "acordo": 2, "tratado": 2, "trégua": 2.5, "tregua": 2.5,
    "ajuda": 1.5, "recuperação": 2, "recuperacao": 2, "crescimento": 2, "vitória": 2,
    "libertar": 1, "cooperação": 2, "cooperacao": 2, "apoio": 1.5, "resgate": 2,
    "reforma": 1.5, "livre": 1.5, "salvar": 2, "melhorar": 1.5, "sucesso": 2,
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

LEXICONS: dict[str, dict[str, float]] = {
    "en": LEXICON_EN,
    "es": LEXICON_ES,
    "fr": LEXICON_FR,
    "pt": LEXICON_PT,
    "ar": LEXICON_AR,
}

# Script-based detection fallback when source_lang is unknown.
ARABIC_RE = re.compile(r"[؀-ۿ]")
LATIN_RE = re.compile(r"[A-Za-z]")
TOKEN_RE = re.compile(r"\w+", re.UNICODE)

CONFIDENCE_CEILING = 0.5
MIN_TOKENS = 3


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
    if ARABIC_RE.search(text):
        return "ar"
    if LATIN_RE.search(text):
        return "en"
    return None


def _score(text: str, lexicon: dict[str, float]) -> tuple[float, float, int]:
    """Compute (signed_score, confidence, token_count) for a single headline."""
    tokens = [t.lower() for t in TOKEN_RE.findall(text)]
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
