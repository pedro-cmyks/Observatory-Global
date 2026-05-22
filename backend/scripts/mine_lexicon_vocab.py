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
import html
import json
import logging
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

import asyncpg

try:
    # langdetect is non-deterministic by default; seed for reproducible mining.
    from langdetect import DetectorFactory, detect_langs
    from langdetect.lang_detect_exception import LangDetectException

    DetectorFactory.seed = 0
    _LANGDETECT_AVAILABLE = True
except ImportError:  # pragma: no cover — keeps miner usable in stripped envs
    detect_langs = None  # type: ignore[assignment]
    LangDetectException = Exception  # type: ignore[assignment]
    _LANGDETECT_AVAILABLE = False

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


def _clean_headline(text: str | None) -> str:
    """Decode HTML entities so accented letters survive tokenisation.

    Many upstream feeds emit numeric character references like `&#xE4;` or
    `&#auml;` instead of UTF-8. The runtime tokenizer then fractures those
    into garbage tokens (`verk` + `xe4` + `ndet`). Decoding entities once
    before tokenisation fixes both miner and runtime scoring.
    """
    if not text:
        return ""
    return html.unescape(text)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(_clean_headline(text))]


def _detect_lang_from_headline(headline: str, min_confidence: float) -> str | None:
    """Run langdetect on a headline; return supported ISO code or None.

    Used when the stored `source_lang` is multilingual placeholder ('xx', 'und')
    or empty. The XLM transformer pipeline stamps 'xx' on every row it scores,
    so 82% of the transformer-tagged corpus is invisible to the miner unless we
    recover language at mining time.
    """
    if not _LANGDETECT_AVAILABLE or not headline:
        return None
    cleaned = _clean_headline(headline)
    if not cleaned:
        return None
    try:
        guesses = detect_langs(cleaned)  # type: ignore[misc]
    except LangDetectException:
        return None
    if not guesses:
        return None
    top = guesses[0]
    if getattr(top, "prob", 0.0) < min_confidence:
        return None
    code = getattr(top, "lang", "").lower()
    if code in SUPPORTED_LANGS:
        return code
    return None


def _normalize_lang(
    raw: str | None,
    headline: str | None = None,
    *,
    detect_fallback: bool = True,
    min_detect_confidence: float = 0.85,
) -> str | None:
    """Project source_lang onto the supported set; None for languages we cannot tokenise.

    When `detect_fallback=True` and source_lang is empty or a multilingual
    placeholder ('xx', 'und'), run langdetect on the headline. Detected codes
    are projected onto SUPPORTED_LANGS; anything else returns None.
    """
    if raw:
        lang = raw.lower()
        if lang in SUPPORTED_LANGS:
            return lang
        if lang in {"xx", "und"} and detect_fallback and headline:
            return _detect_lang_from_headline(headline, min_detect_confidence)
        return None
    if detect_fallback and headline:
        return _detect_lang_from_headline(headline, min_detect_confidence)
    return None


async def _mine(
    conn: asyncpg.Connection,
    min_freq: int,
    max_freq: int,
    min_abs_mean: float,
    output_dir: Path,
    dry_run: bool,
    *,
    detect_fallback: bool = True,
    min_detect_confidence: float = 0.85,
    merge_existing: bool = True,
) -> dict[str, dict[str, int]]:
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
    recovered_via_detect: dict[str, int] = defaultdict(int)
    raw_lang_counts: dict[str, int] = defaultdict(int)

    async with conn.transaction():
        async for row in conn.cursor(PRIORITY_SELECT_SQL):
            stored_raw = (row["source_lang"] or "").lower() or "(null)"
            raw_lang_counts[stored_raw] += 1
            lang = _normalize_lang(
                row["source_lang"],
                row["headline"],
                detect_fallback=detect_fallback,
                min_detect_confidence=min_detect_confidence,
            )
            if lang is None:
                total_skipped_lang += 1
                continue
            if stored_raw in {"xx", "und", "(null)"} and lang in SUPPORTED_LANGS:
                recovered_via_detect[lang] += 1
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

    logger.info(
        "Scanned %d transformer-tagged rows (skipped %d for lang)",
        total_rows,
        total_skipped_lang,
    )
    if detect_fallback and _LANGDETECT_AVAILABLE:
        rec_summary = ", ".join(
            f"{lang}={n}" for lang, n in sorted(recovered_via_detect.items(), key=lambda kv: -kv[1])
        )
        logger.info("Langdetect recovery from xx/und/null: %s", rec_summary or "(none)")
    elif detect_fallback and not _LANGDETECT_AVAILABLE:
        logger.warning("langdetect not installed — install it to recover xx/und rows")
    top_raw = sorted(raw_lang_counts.items(), key=lambda kv: -kv[1])[:8]
    logger.info(
        "Raw source_lang distribution: %s",
        ", ".join(f"{lang}={n}" for lang, n in top_raw),
    )

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
    kept_per_lang: dict[str, dict[str, int]] = {}
    for lang in SUPPORTED_LANGS:
        new_snapshot = per_lang.get(lang, {})
        path = output_dir / f"{lang}.mined.json"

        existing: dict[str, float] = {}
        if merge_existing and path.exists():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(existing, dict):
                    logger.warning("%s.mined.json is not a dict; ignoring", lang)
                    existing = {}
            except Exception as exc:
                logger.warning("Could not load existing %s.mined.json: %s", lang, exc)
                existing = {}

        if merge_existing:
            replaced = sum(1 for tok in new_snapshot if tok in existing)
            added = sum(1 for tok in new_snapshot if tok not in existing)
            merged: dict[str, float] = {**existing, **new_snapshot}
        else:
            replaced = added = 0
            merged = new_snapshot

        stats = per_lang_stats[lang]
        logger.info(
            "%s: considered=%d kept_new=%d merged_total=%d (added=%d replaced=%d kept_old=%d) examples=%s",
            lang,
            stats["considered"],
            stats["kept"],
            len(merged),
            added,
            replaced,
            max(0, len(existing) - replaced),
            ", ".join(
                f"{k}({v:+.2f})"
                for k, v in sorted(new_snapshot.items(), key=lambda kv: abs(kv[1]), reverse=True)[:6]
            ),
        )
        kept_per_lang[lang] = {
            "new_terms": len(new_snapshot),
            "merged_total": len(merged),
            "added": added,
            "replaced": replaced,
        }
        if dry_run:
            continue
        if merge_existing and path.exists() and existing:
            backup_path = path.with_suffix(".json.bak")
            backup_path.write_text(
                json.dumps(existing, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
        # Stable on-disk format: sorted keys + final newline.
        path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return kept_per_lang


async def _cli(
    min_freq: int,
    max_freq: int,
    min_abs_mean: float,
    dry_run: bool,
    detect_fallback: bool,
    min_detect_confidence: float,
    merge_existing: bool,
) -> None:
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL or SUPABASE_DB_URL env var required")
    conn = await asyncpg.connect(db_url)
    try:
        result = await _mine(
            conn,
            min_freq,
            max_freq,
            min_abs_mean,
            OUTPUT_DIR,
            dry_run,
            detect_fallback=detect_fallback,
            min_detect_confidence=min_detect_confidence,
            merge_existing=merge_existing,
        )
    finally:
        await conn.close()
    summary = ", ".join(
        f"{lang}={info['merged_total']}(+{info['added']})"
        for lang, info in sorted(result.items())
    )
    logger.info(
        "Mine complete (dry_run=%s merge=%s) — %s",
        dry_run, merge_existing, summary,
    )


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
    parser.add_argument("--no-langdetect", action="store_true",
                        help="Disable langdetect fallback (treat xx/und rows as skipped).")
    parser.add_argument("--min-detect-confidence", type=float, default=0.85,
                        help="Minimum langdetect top-guess probability to accept (default 0.85).")
    parser.add_argument("--replace", action="store_true",
                        help="Replace existing snapshots instead of merging (default merges and "
                             "backs up the prior file as <lang>.mined.json.bak).")
    return parser.parse_args()


def main():
    args = _parse_args()
    try:
        asyncio.run(
            _cli(
                args.min_freq,
                args.max_freq,
                args.min_abs_mean,
                args.dry_run,
                detect_fallback=not args.no_langdetect,
                min_detect_confidence=args.min_detect_confidence,
                merge_existing=not args.replace,
            )
        )
    except RuntimeError as exc:
        logger.error(str(exc))
        sys.exit(1)


if __name__ == "__main__":
    main()
