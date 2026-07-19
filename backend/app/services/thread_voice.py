"""Thread-scoped Voice Mix (council wish 18 — who SPEAKS inside a thread).

The country Voice Mix (#235) answers "who covers country CC"; this answers
"who carries THIS story": the language and outlet-origin distribution over a
thread's typed evidence members (`topic_members role='evidence'`), plus the
self-voice relation against the thread's dominant subject country — computed
with the SAME `voice_mix.relation()` the country surface uses (ownership,
not language; single source of truth, they can never drift).

Honesty invariants:
  * counts are over the thread's TYPED members in the window — a projection
    of the engine's member record, not "all coverage of the topic";
  * unattributed origins / unknown languages are reported, never assumed;
  * no members -> available=False with a reason (engine projection may lag);
  * no dominant subject country -> no relation (never a guessed subject).
"""
from __future__ import annotations

import logging
from collections import Counter
from typing import Any

from app.services.voice_mix import UNKNOWN_LANGS, primary_langs, relation

logger = logging.getLogger(__name__)

# The thread's evidence members in the window, with the speaker fields.
_THREAD_VOICE_SQL = """
    SELECT s.source_lang, s.source_origin_country, s.country_code
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = $1
      AND tm.role = 'evidence'
      AND tm.engine_version = $2
      AND tm.assigned_at >= NOW() - ($3::int * INTERVAL '1 hour')
"""


def _norm_lang(raw: Any) -> str | None:
    lang = (str(raw or "")).strip().lower()
    return None if lang in UNKNOWN_LANGS else lang


def aggregate_thread_voice(rows: list[dict]) -> dict:
    """Pure aggregation: member rows -> the thread voice-mix block."""
    if not rows:
        return {
            "available": False,
            "reason": "no typed evidence members recorded for this thread in "
                      "this window (the member projection may lag the engine)",
        }

    total = len(rows)
    lang_counts: Counter[str] = Counter()
    lang_unknown = 0
    origin_counts: Counter[str] = Counter()
    origin_unattributed = 0
    subject_counts: Counter[str] = Counter()

    for r in rows:
        lang = _norm_lang(r.get("source_lang"))
        if lang is None:
            lang_unknown += 1
        else:
            lang_counts[lang] += 1
        origin = (str(r.get("source_origin_country") or "")).strip().upper()
        if origin:
            origin_counts[origin] += 1
        else:
            origin_unattributed += 1
        subject = (str(r.get("country_code") or "")).strip().upper()
        if subject and subject != "XX":
            subject_counts[subject] += 1

    out: dict[str, Any] = {
        "available": True,
        "voices_total": total,
        "basis": "typed evidence members (who published, per outlet metadata)",
        "languages": [
            {"lang": l, "n": n} for l, n in lang_counts.most_common(8)
        ],
        "language_unknown": lang_unknown,
        "origins": [
            {"cc": c, "n": n} for c, n in origin_counts.most_common(8)
        ],
        "origin_unattributed": origin_unattributed,
        "subject_country": None,
    }

    if not subject_counts:
        return out  # mix served; relation never computed against a guess

    subject, subject_n = subject_counts.most_common(1)[0]
    out["subject_country"] = subject
    out["subject_share"] = round(subject_n / total, 4)

    local_langs = primary_langs(subject)
    origin_known = sum(origin_counts.values())
    domestic = origin_counts.get(subject, 0)
    soft_power = sum(
        1
        for r in rows
        if (str(r.get("source_origin_country") or "")).strip().upper()
        not in ("", subject)
        and (_norm_lang(r.get("source_lang")) or "") in local_langs
    )
    foreign_origins = [
        (c, n) for c, n in origin_counts.most_common() if c != subject
    ]
    foreign_langs = [
        (l, n) for l, n in lang_counts.most_common() if l not in local_langs
    ]
    out["relation"] = relation(
        total, origin_known, domestic, soft_power, foreign_origins, foreign_langs
    )
    return out


async def fetch_thread_voice(
    conn: Any, topic_id: str, engine_version: str, hours: int,
) -> dict:
    base = topic_id.strip().split("--", 1)[0]
    try:
        rows = await conn.fetch(_THREAD_VOICE_SQL, base, engine_version, hours)
    except Exception as exc:  # noqa: BLE001 — degraded section, never a 500
        logger.warning("thread voice fetch failed: %s", exc)
        return {
            "available": False,
            "reason": "voice aggregation failed under load — retry shortly",
        }
    return aggregate_thread_voice([dict(r) for r in rows])
