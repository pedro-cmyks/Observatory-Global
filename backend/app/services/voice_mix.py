"""Voice Mix — diversity metric for the corpus (#160/#230).

Single source of truth for the `diversity_score` so the offline audit
(`scripts/voice_mix_audit.py`) and the live endpoint (`routers/voice_mix.py`)
can never drift. Pure functions only — callers supply already-aggregated rows.

diversity_score (0-100) = 100 * mean(english_balance, language_entropy,
cjk_coverage), each computed over the language-KNOWN slice (GDELT 'xx'/null
excluded). See `compute()` for exact definitions.
"""
from __future__ import annotations

import math

CJK_LANGS = ("zh", "ja", "ko")
CJK_TARGET = 0.05  # aspirational CJK share of language-known corpus
# 'xx' is GDELT's no-language marker; the rest are genuinely missing. All are
# "language unknown" and excluded from the known slice so English dominance is
# measured honestly against signals we can actually attribute.
UNKNOWN_LANGS = {"xx", "(null)", "", "un", "und"}


def shannon_norm(counts: list[int]) -> float:
    """Shannon entropy normalized to [0,1] by ln(n) — 0=one language, 1=uniform."""
    total = sum(counts)
    if total <= 0 or len(counts) <= 1:
        return 0.0
    h = -sum((c / total) * math.log(c / total) for c in counts if c > 0)
    return h / math.log(len(counts))


def compute(
    lang_counts: dict[str, int],
    origin_counts: dict[str, int],
    total: int,
    state_media: int,
    distinct_sources: int,
) -> dict:
    """Build the Voice Mix report from pre-aggregated counts.

    lang_counts:   source_lang -> count (raw, includes unknown buckets)
    origin_counts: source_origin_country -> count (raw, includes '(null)')
    """
    known = {k: v for k, v in lang_counts.items()
             if (k or "").lower() not in UNKNOWN_LANGS}
    known_total = sum(known.values())
    unknown_total = total - known_total

    en = known.get("en", 0)
    cjk = {l: known.get(l, 0) for l in CJK_LANGS}
    cjk_total = sum(cjk.values())

    english_share_known = (en / known_total) if known_total else 0.0
    cjk_share = (cjk_total / known_total) if known_total else 0.0
    lang_entropy = shannon_norm(list(known.values()))

    english_balance = 1.0 - english_share_known
    cjk_coverage = min(cjk_share / CJK_TARGET, 1.0) if CJK_TARGET else 0.0
    diversity_score = round(
        100 * (english_balance + lang_entropy + cjk_coverage) / 3, 1
    )

    origin_known = {k: v for k, v in origin_counts.items() if k != "(null)"}
    ok_total = sum(origin_known.values()) or 1
    hhi = sum((v / ok_total) ** 2 for v in origin_known.values())
    top_origins = sorted(origin_known.items(), key=lambda kv: -kv[1])[:10]
    top_langs = sorted(known.items(), key=lambda kv: -kv[1])[:15]

    return {
        "total_signals": total,
        "language_known": known_total,
        "language_unknown": unknown_total,
        "unknown_pct": round(100 * unknown_total / total, 1) if total else 0,
        "english_share_of_known": round(english_share_known, 4),
        "non_english_share_of_known": round(1 - english_share_known, 4),
        "cjk": {**cjk, "total": cjk_total, "share_of_known": round(cjk_share, 4)},
        "language_entropy_norm": round(lang_entropy, 4),
        "distinct_known_languages": len(known),
        "state_media": state_media,
        "state_media_pct": round(100 * state_media / total, 2) if total else 0,
        "distinct_sources": distinct_sources,
        "origin_hhi": round(hhi, 4),
        "top_origin_countries": [{"cc": c, "n": n} for c, n in top_origins],
        "top_languages": [{"lang": l, "n": n} for l, n in top_langs],
        "diversity_score": diversity_score,
        "components": {
            "english_balance": round(english_balance, 4),
            "language_entropy_norm": round(lang_entropy, 4),
            "cjk_coverage": round(cjk_coverage, 4),
        },
    }
