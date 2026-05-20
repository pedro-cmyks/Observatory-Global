"""Mine lexicon vocabulary from transformer-tagged signals (issue #185).

Manual seed lexicons in enrichment/lexicon_sentiment.py plateau at ~12% hit
rate because most news headlines are factual and contain none of the curated
charged terms. This script derives vocabulary from the rows the transformer
worker already scored — every (token, language) pair gets a mean nlp_sentiment
across all headlines that contain it, plus a document frequency for filtering.

The transformer-tagged corpus is the ground truth the lexicon should be
calibrated against. Manual seeds remain authoritative for high-confidence
terms (loaded after the mined snapshot so seeds win on conflict).

Output: one JSON file per language at backend/enrichment/lexicons/<lang>.mined.json
that the existing lexicon scorer loads at startup. Re-run after every N
thousand additional transformer-tagged rows to keep vocab fresh.

CLI:
    python -m scripts.mine_lexicon_vocab --dry-run
    python -m scripts.mine_lexicon_vocab --min-freq 30 --max-freq 10000 --min-abs-mean 0.4
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

import asyncpg

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [mine-vocab] %(levelname)s %(message)s")

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "enrichment" / "lexicons"

# Supported languages — must match LEXICONS keys in enrichment/lexicon_sentiment.py
SUPPORTED_LANGS = {"en", "es", "fr", "pt", "ar", "it", "de"}

# Token boundaries. Unicode \w covers Latin + most Cyrillic/Hangul/CJK with
# letter-class characters. CJK without spaces still needs proper segmentation
# for high quality — for now we treat each contiguous word-character span as a
# token, matching what the lexicon scorer does at runtime.
TOKEN_RE = re.compile(r"\w+", re.UNICODE)

# Per-language stopword lists. Without these, mining picks up high-frequency
# closed-class tokens (articles, prepositions, auxiliaries) whose mean
# nlp_sentiment is non-zero because the per-language corpus is structurally
# biased (Spanish crisis coverage skews negative, etc.) but that carry no
# discriminative signal per headline. Lists are intentionally conservative —
# only the most common function words. Domain-charged terms ("crisis",
# "victoria", etc.) stay miner-eligible.
STOPWORDS_BY_LANG: dict[str, set[str]] = {
    "en": {
        "a", "an", "the", "and", "or", "of", "to", "in", "on", "at", "for", "by",
        "is", "was", "are", "with", "as", "it", "be", "from", "this", "that",
        "has", "have", "had", "but", "not", "no", "so", "if", "than", "then",
        "into", "over", "out", "up", "down", "off", "about", "after", "before",
        "i", "you", "he", "she", "we", "they", "his", "her", "their", "its",
        "will", "would", "can", "could", "should", "may", "might", "must",
    },
    "es": {
        "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
        "en", "y", "o", "u", "a", "con", "por", "para", "que", "se", "su", "sus",
        "lo", "le", "les", "ya", "no", "sí", "si", "es", "son", "fue", "era",
        "ha", "han", "más", "mas", "como", "pero", "porque", "este", "esta",
        "esto", "ese", "esa", "eso", "aquel", "aquella", "aquello", "yo", "tú",
        "él", "ella", "nos", "vos", "ustedes", "ellos", "ellas", "muy", "ser",
        "estar", "tener", "hacer", "ir",
    },
    "fr": {
        "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou", "à",
        "au", "aux", "en", "dans", "pour", "par", "sur", "sous", "avec", "sans",
        "vers", "chez", "ne", "pas", "plus", "moins", "ce", "cette", "ces",
        "qui", "que", "quoi", "dont", "où", "il", "elle", "ils", "elles", "je",
        "tu", "nous", "vous", "se", "son", "sa", "ses", "leur", "leurs", "y",
        "mais", "comme", "si", "très", "tout", "tous", "toute", "toutes",
        "est", "sont", "était", "été", "a", "ont", "avoir", "être",
    },
    "pt": {
        "o", "a", "os", "as", "um", "uma", "uns", "umas", "de", "do", "da",
        "dos", "das", "no", "na", "nos", "nas", "ao", "aos", "à", "às", "e",
        "ou", "em", "por", "para", "com", "sem", "que", "se", "su", "seu",
        "sua", "seus", "suas", "ele", "ela", "eles", "elas", "eu", "tu", "nós",
        "vós", "lhe", "lhes", "me", "te", "nos", "vos", "não", "sim", "é",
        "são", "foi", "era", "tem", "têm", "ter", "ser", "estar",
        "mais", "menos", "como", "mas", "porque",
    },
    "it": {
        "il", "lo", "la", "i", "gli", "le", "un", "uno", "una", "di", "del",
        "dello", "della", "dei", "degli", "delle", "a", "al", "allo", "alla",
        "ai", "agli", "alle", "da", "dal", "dallo", "dalla", "dai", "dagli",
        "dalle", "in", "nel", "nello", "nella", "nei", "negli", "nelle", "con",
        "per", "su", "tra", "fra", "e", "o", "ma", "che", "non", "non",
        "è", "sono", "era", "ha", "hanno", "essere", "avere",
    },
    "de": {
        "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
        "eines", "und", "oder", "in", "im", "an", "am", "auf", "mit", "für",
        "bei", "von", "zu", "zum", "zur", "aus", "nach", "über", "unter", "vor",
        "nicht", "kein", "keine", "ist", "sind", "war", "waren", "hat", "haben",
        "wird", "werden", "wurde", "wurden", "ich", "du", "er", "sie", "es",
        "wir", "ihr", "mein", "dein", "sein", "ihre", "unser", "euer", "als",
        "wenn", "weil", "dass", "ob", "aber", "doch",
    },
    "ar": {
        "في", "من", "إلى", "على", "عن", "مع", "و", "أو", "ال", "أن", "إن",
        "لا", "لم", "لن", "كان", "كانت", "هو", "هي", "هم", "أنا", "أنت",
        "نحن", "هذا", "هذه", "ذلك", "تلك", "الذي", "التي", "ما", "ماذا",
        "كما", "ثم", "أيضا", "لكن", "إذا", "حتى", "بين", "بعد", "قبل",
    },
}

PRIORITY_SELECT_SQL = """
SELECT headline, source_lang, nlp_sentiment
FROM signals_v2
WHERE nlp_method = 'transformer'
  AND nlp_sentiment IS NOT NULL
  AND headline IS NOT NULL
  AND LENGTH(headline) > 10
"""


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text or "")]


def _normalize_lang(raw: str | None) -> str | None:
    """Project source_lang onto the supported set; None for languages we cannot tokenise."""
    if not raw:
        return None
    lang = raw.lower()
    if lang in SUPPORTED_LANGS:
        return lang
    # xlm-shadow rows carry 'xx' as a multilingual placeholder; skip — we cannot
    # attribute token weights without a real language tag.
    if lang in {"xx", "und"}:
        return None
    # Two-letter ISO outside the supported set: skip.
    return None


async def _mine(
    conn: asyncpg.Connection,
    min_freq: int,
    max_freq: int,
    min_abs_mean: float,
    output_dir: Path,
    dry_run: bool,
) -> dict[str, int]:
    """Compute per-(lang, token) mean sentiment and emit JSON snapshots.

    Returns {lang: tokens_kept_count}.
    """
    # Streaming accumulators per (lang, token).
    # Using lists keeps memory bounded by total transformer-tagged rows × avg
    # token count. For the current ~35K transformer rows × ~12 tokens/row that
    # is ~420K entries — easily fits in memory.
    sentiment_sum: dict[tuple[str, str], float] = defaultdict(float)
    doc_freq: dict[tuple[str, str], int] = defaultdict(int)
    total_rows = 0
    total_skipped_lang = 0

    async with conn.transaction():
        async for row in conn.cursor(PRIORITY_SELECT_SQL):
            lang = _normalize_lang(row["source_lang"])
            if lang is None:
                total_skipped_lang += 1
                continue
            total_rows += 1
            stopwords = STOPWORDS_BY_LANG.get(lang, set())
            seen_in_row: set[str] = set()
            for tok in _tokens(row["headline"]):
                if tok in stopwords:
                    continue
                if len(tok) < 2 or tok.isdigit():
                    continue
                if tok in seen_in_row:
                    continue  # count each token at most once per row for doc_freq
                seen_in_row.add(tok)
                key = (lang, tok)
                doc_freq[key] += 1
                sentiment_sum[key] += float(row["nlp_sentiment"])

    logger.info("Scanned %d transformer-tagged rows (skipped %d for lang)", total_rows, total_skipped_lang)

    # Filter + bucket by language.
    per_lang: dict[str, dict[str, float]] = defaultdict(dict)
    per_lang_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"considered": 0, "kept": 0})
    for (lang, tok), freq in doc_freq.items():
        per_lang_stats[lang]["considered"] += 1
        if freq < min_freq or freq > max_freq:
            continue
        mean_sent = sentiment_sum[(lang, tok)] / freq
        if abs(mean_sent) < min_abs_mean:
            continue
        # Round weight to 2 decimals, clamp to [-3, 3] to match seed conventions.
        weight = round(max(-3.0, min(3.0, mean_sent)), 2)
        per_lang[lang][tok] = weight
        per_lang_stats[lang]["kept"] += 1

    output_dir.mkdir(parents=True, exist_ok=True)
    kept_per_lang: dict[str, int] = {}
    for lang in SUPPORTED_LANGS:
        snapshot = per_lang.get(lang, {})
        kept_per_lang[lang] = len(snapshot)
        stats = per_lang_stats[lang]
        logger.info(
            "%s: considered=%d kept=%d  examples=%s",
            lang, stats["considered"], stats["kept"],
            ", ".join(
                f"{k}({v:+.2f})"
                for k, v in sorted(snapshot.items(), key=lambda kv: abs(kv[1]), reverse=True)[:6]
            ),
        )
        if dry_run:
            continue
        path = output_dir / f"{lang}.mined.json"
        # Stable on-disk format: sorted keys + final newline.
        path.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return kept_per_lang


async def _cli(min_freq: int, max_freq: int, min_abs_mean: float, dry_run: bool) -> None:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")
    conn = await asyncpg.connect(db_url)
    try:
        result = await _mine(conn, min_freq, max_freq, min_abs_mean, OUTPUT_DIR, dry_run)
    finally:
        await conn.close()
    summary = ", ".join(f"{lang}={n}" for lang, n in sorted(result.items()))
    logger.info("Mine complete (dry_run=%s) — %s", dry_run, summary)


def _parse_args():
    parser = argparse.ArgumentParser(description="Atlas — corpus-mine lexicon vocabulary (#185)")
    parser.add_argument("--min-freq", type=int, default=30,
                        help="Minimum doc frequency a token must reach to be kept (default 30).")
    parser.add_argument("--max-freq", type=int, default=10000,
                        help="Maximum doc frequency before a token is treated as uninformative (default 10000).")
    parser.add_argument("--min-abs-mean", type=float, default=0.4,
                        help="Minimum |mean_sentiment| required to keep a token (default 0.4).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip writing JSON snapshots; only log per-language counts.")
    return parser.parse_args()


def main():
    args = _parse_args()
    try:
        asyncio.run(_cli(args.min_freq, args.max_freq, args.min_abs_mean, args.dry_run))
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
