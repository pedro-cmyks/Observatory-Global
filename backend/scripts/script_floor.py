"""Script-aware headline length floor (2026-07-30, threading-floor diagnosis).

`length(headline) >= 20` is Latin-calibrated. CJK scripts (Chinese/Japanese/
Korean) pack far more information per character — 20 CJK characters is
routinely a FULL headline, and 10-19 is a normal complete one (see the real
examples in `docs/research/recall-229/2026-07-30-cjk-length-floor-measurement.md`,
e.g. "日本30年來8次震度7劇震 熊本占3次", 19 chars, a complete sentence). A flat
20-char floor throttles the CJK funnel at its mouth for no precision reason —
it is measuring the wrong unit for these scripts.

The fix is NARROW by construction: it only lowers the bar for headlines that
are THEMSELVES majority CJK by character count. Latin/ASCII junk placeholders
("Content 23748045", digit-string scrapes) stay at the 20-char floor exactly
as before — they are not CJK-dominant, so `effective_headline_floor` never
touches them. This is deliberate: the diagnosis found the pre-existing
"short headline" bucket is mostly non-CJK junk, and the fix must not let any
of that back in.

See docs/research/recall-229/2026-07-29-threading-floor-diagnosis.md §1
("Side finding (JP)") and §6.3, and the follow-up measurement doc above.

Wired at the R1 scoped-snapshot pull (`run_scoped_snapshot.py`): the
country-eligibility count (`_COUNTRIES`) and the per-country clustering fetch
(`_FETCH_PAGE`) — see that module for the SQL wiring and the
`ATLAS_CJK_LEN_FLOOR` gate (default OFF, byte-identical to the flat floor).
"""
from __future__ import annotations

import os
import re

# Latin-calibrated default (unchanged behaviour when the gate is off).
LATIN_FLOOR = 20
# CJK-dominant floor. Chosen from measurement, not vibes: over JP/KR/TW/CN
# subject-country signals (168h, 2026-07-30), only a handful of CJK-dominant
# headlines fall below 10 chars, and the ones sampled at 10-19 are complete
# real headlines, not fragments.
CJK_FLOOR = 10
# Fraction of characters that must fall in a CJK unicode block for a
# headline to be judged "CJK-dominant". >0.5 (strict majority) — a headline
# that is mostly Latin with an occasional CJK proper noun still uses the
# Latin floor.
CJK_DOMINANCE_THRESHOLD = 0.5

# Hiragana (U+3040-U+309F) + Katakana (U+30A0-U+30FF, contiguous with
# Hiragana) + CJK Unified Ideographs Extension A (U+3400-U+4DBF) + CJK
# Unified Ideographs (U+4E00-U+9FFF) + Hangul Syllables (U+AC00-U+D7A3).
# Covers Japanese (kana + kanji), Chinese (Han), and Korean (Hangul, and
# Han where used). The SAME four ranges are mirrored in `_CJK_SQL_CLASS`
# below for the SQL CASE expression — keep them in lockstep.
_CJK_CHAR_RE = re.compile("[぀-ヿ㐀-䶿一-鿿가-힣]")


def cjk_ratio(headline: str | None) -> float:
    """Fraction of `headline`'s characters that fall in a CJK unicode block.

    0.0 for None/empty/whitespace-only (denominator guard) rather than
    raising. Ratio is over the FULL character count (spaces, digits and
    punctuation included) — matching how the SQL mirror computes it, since
    that is what was measured against prod.
    """
    if not headline:
        return 0.0
    total = len(headline)
    if total == 0:
        return 0.0
    cjk = len(_CJK_CHAR_RE.findall(headline))
    return cjk / total


def is_cjk_dominant(headline: str | None, threshold: float = CJK_DOMINANCE_THRESHOLD) -> bool:
    """True when `headline` is majority CJK-script by character count."""
    return cjk_ratio(headline) > threshold


def effective_headline_floor(headline: str | None) -> int:
    """The length floor `headline` should be judged against.

    CJK-dominant text uses CJK_FLOOR (10); everything else — including
    Latin-script headlines AND non-CJK junk/placeholder text that happens to
    be short — keeps the existing LATIN_FLOOR (20). A None/empty headline
    always fails either floor (both are > 0), matching the pre-existing
    `headline IS NOT NULL` guard at every call site this is wired into.
    """
    return CJK_FLOOR if is_cjk_dominant(headline) else LATIN_FLOOR


def cjk_len_floor_enabled() -> bool:
    """ATLAS_CJK_LEN_FLOOR — reversible gate, default OFF.

    Off (default): every call site keeps emitting the flat, byte-identical
    `length(<col>) >= 20` predicate — zero behaviour change.
    On: call sites switch to the script-aware CASE expression below.
    """
    return os.environ.get("ATLAS_CJK_LEN_FLOOR", "").strip().lower() in {
        "1", "true", "on", "yes",
    }


# SQL mirror of the four unicode ranges above, for a bracket-expression
# regex inside a raw SQL WHERE clause. MUST stay in lockstep with
# `_CJK_CHAR_RE` — same four blocks, same order. Verified directly against
# Postgres (bracket expressions accept literal UTF-8 range endpoints; no
# `\uXXXX` escape needed) in the measurement doc referenced above.
_CJK_SQL_CLASS = "぀-ヿ㐀-䶿一-鿿가-힣"


def headline_floor_sql(column: str) -> str:
    """`length(<column>) >= <script-aware floor>` as a raw SQL boolean expr.

    `column` must be a trusted SQL identifier/reference (e.g. ``"s.headline"``)
    — it is interpolated directly into the returned SQL text, never bound as
    a parameter, so it must never carry user input.

    The CASE mirrors `effective_headline_floor` exactly: CJK ratio computed
    over the full character count (`length`), same 0.5 cut, same two floors.
    `NULLIF(length(<column>), 0)` guards the empty-string divide (headline
    NULL is already excluded by the caller's own `IS NOT NULL` guard).
    """
    cjk_chars = f"length(regexp_replace({column}, '[^{_CJK_SQL_CLASS}]', '', 'g'))"
    return (
        f"length({column}) >= CASE WHEN {cjk_chars}::float / NULLIF(length({column}), 0) "
        f"> {CJK_DOMINANCE_THRESHOLD} THEN {CJK_FLOOR} ELSE {LATIN_FLOOR} END"
    )


def headline_length_predicate(column: str) -> str:
    """The WHERE-clause predicate a length-floor call site should use.

    Behind `ATLAS_CJK_LEN_FLOOR` (default off): returns the flat,
    byte-identical ``length(<column>) >= 20``. On: returns the script-aware
    CASE expression from `headline_floor_sql`. Callers keep their own
    ``<column> IS NOT NULL`` guard unchanged — this function only ever
    returns the length comparison.
    """
    if cjk_len_floor_enabled():
        return headline_floor_sql(column)
    return f"length({column}) >= {LATIN_FLOOR}"
