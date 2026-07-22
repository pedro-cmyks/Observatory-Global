"""Shared narrative intelligence packet builder.

Aggregates a set of signal rows (a thread's or topic's sample signals) into
the descriptive structures the reading panels render: country edges, source
lanes, timeline, graph, related themes.

Pure function over rows — no DB, no metric weighting.
"""
from __future__ import annotations

import html
from typing import Any

from app.core.gdelt_taxonomy import classify_source
from app.services.source_tiers import tier_payload
from app.utils import extract_domain, rank_key_people

# Social platform domains that classify_source returns "independent" for but
# should map to the "social" lane. Checked against SOURCE_FAMILY (2026-06-04):
# reddit, twitter, mastodon etc. are NOT in SOURCE_FAMILY and have no state
# TLD, so classify_source returns "independent" for them.
_SOCIAL_DOMAINS = {
    "reddit.com", "old.reddit.com",
    "twitter.com", "x.com",
    "mastodon.social", "bsky.app",
    "facebook.com", "instagram.com",
    "vk.com", "t.me", "telegram.org",
    "tumblr.com", "weibo.com",
}

_STATE_FAMILIES = {"state"}
# "unknown" counts as media here: the lane is a coarse press/state/social VOICE
# split, and an unmapped domain arriving through news ingest is press by prior —
# the honest "unknown" claim lives on the badge/tier (D4), not in this split
# (excluding it would silently crater who-says-what press counts).
_MEDIA_FAMILIES = {"wire", "independent", "ngo", "unknown"}


def _extract_base_domain(source_name: str) -> str:
    """Return the bare host (e.g. 'reddit.com') from a source name or URL."""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(
            source_name if source_name.startswith("http") else f"http://{source_name}"
        )
        host = parsed.netloc.lower().replace("www.", "").split(":")[0]
        # strip sub-paths that may be baked in (e.g. "reddit.com/r/x")
        return host or source_name.split("/")[0].lower()
    except Exception:
        return source_name.split("/")[0].lower()


def _lane_for(source_name: str) -> str:
    """Map a source name to one of: social | state | media | other.

    Social domains are checked by name before consulting classify_source,
    because classify_source returns "independent" for reddit/twitter etc.
    (they are not in SOURCE_FAMILY and have no state TLD suffix).
    """
    base = _extract_base_domain(source_name)
    if base in _SOCIAL_DOMAINS:
        return "social"
    family = classify_source(source_name)
    if family in _STATE_FAMILIES:
        return "state"
    if family in _MEDIA_FAMILIES:
        return "media"
    return "other"


def _val(row: Any, key: str):
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return None


def build_thread_packet(rows: list, own_topic: str | None = None) -> dict:
    """Aggregate signal rows into a narrative intelligence packet.

    Parameters
    ----------
    rows:
        Sequence of asyncpg Records or plain dicts with keys:
        ``timestamp``, ``country_code``, ``source_name``, ``source_url``,
        ``sentiment``, ``headline``, ``themes``, ``persons``.
    own_topic:
        If provided, this theme code is excluded from ``relatedThemes``
        (it's the thread's own topic, not a co-occurring one).

    Returns
    -------
    dict with keys: graphSignals, countryBreakdown, topSources, topPersons,
    timeline, lanes, relatedThemes, public_attention.
    """
    country_counts: dict[str, list[float]] = {}
    source_counts: dict[str, list[float]] = {}
    timeline_counts: dict = {}
    person_counts: dict[str, int] = {}
    # B3: distinct headlines/outlets per person feed the syndication-resistant
    # ranker so a single-signal name (e.g. "ocean atlantic" in one article)
    # can't pose as a key subject.
    person_headlines: dict[str, set] = {}
    person_outlets: dict[str, set] = {}
    theme_counts: dict[str, int] = {}
    lanes: dict[str, int] = {"media": 0, "social": 0, "state": 0, "other": 0}

    for r in rows:
        sentiment = float(_val(r, "sentiment") or 0)

        cc = _val(r, "country_code")
        if cc:
            country_counts.setdefault(cc, []).append(sentiment)

        sn = _val(r, "source_name")
        if sn:
            source_counts.setdefault(sn, []).append(sentiment)
            lanes[_lane_for(sn)] += 1

        ts = _val(r, "timestamp")
        if ts:
            bucket = ts.replace(minute=0, second=0, microsecond=0)
            timeline_counts.setdefault(bucket, []).append(sentiment)

        # Unescape before the dedup key: an encoded and a plain copy of one
        # wire story would otherwise read as two distinct headlines and
        # fabricate the corroboration that rank_key_people's floor tests for.
        _hl_norm = html.unescape(_val(r, "headline") or "").strip().lower()
        for p in (_val(r, "persons") or []):
            person_counts[p] = person_counts.get(p, 0) + 1
            if _hl_norm:
                person_headlines.setdefault(p, set()).add(_hl_norm)
            if sn:
                person_outlets.setdefault(p, set()).add(sn)

        for t in (_val(r, "themes") or []):
            if own_topic and t == own_topic:
                continue
            theme_counts[t] = theme_counts.get(t, 0) + 1

    country_breakdown = [
        {"code": cc, "count": len(vs), "sentiment": sum(vs) / len(vs)}
        for cc, vs in sorted(
            country_counts.items(), key=lambda x: len(x[1]), reverse=True
        )
    ][:15]

    top_sources = [
        {
            "name": extract_domain(sn),
            "count": len(vs),
            "sentiment": sum(vs) / len(vs),
            "family": classify_source(sn or ""),
            # #217 capability G: credibility tier as a LABEL with provenance
            # (never a filter) — the who-says-what matrix stops presenting
            # a conspiracy amplifier and a met agency as peers.
            "credibility": tier_payload(
                sn, source_family=classify_source(sn or "")),
        }
        for sn, vs in sorted(
            source_counts.items(), key=lambda x: len(x[1]), reverse=True
        )
    ][:20]

    timeline = [
        {"hour": h.isoformat(), "count": len(vs), "sentiment": sum(vs) / len(vs)}
        for h, vs in sorted(timeline_counts.items())
    ]

    # B3: rank by distinct stories/outlets (syndication-resistant) with a
    # corroboration floor, not raw COUNT(*) gated only by _is_valid_person.
    _person_rows = [
        {
            "person": p,
            "signal_count": c,
            "distinct_headlines": len(person_headlines.get(p, set())) or 1,
            "distinct_outlets": len(person_outlets.get(p, set())) or 1,
        }
        for p, c in person_counts.items()
    ]
    top_persons = [
        {"name": r["person"], "count": r["signal_count"]}
        for r in rank_key_people(_person_rows, limit=10)
    ]

    related_themes = [
        {"theme": t, "count": c}
        for t, c in sorted(
            theme_counts.items(), key=lambda x: x[1], reverse=True
        )
    ][:10]

    def _sig(r: Any) -> dict:
        ts = _val(r, "timestamp")
        hl = _val(r, "headline")
        return {
            # id + source_lang let the frontend TranslatableHeadline translate
            # non-English coverage (id = translation cache key, source_lang =
            # original language). _val is null-safe: callers whose rows omit
            # these columns simply get None.
            "id": _val(r, "id"),
            "source_lang": _val(r, "source_lang"),
            "timestamp": ts.isoformat() if ts else None,
            "country": _val(r, "country_code"),
            "source": _val(r, "source_name"),
            "url": _val(r, "source_url"),
            "headline": html.unescape(hl) if hl else hl,
            "sentiment": float(_val(r, "sentiment") or 0),
            "otherThemes": (_val(r, "themes") or [])[:5],
            "persons": (_val(r, "persons") or [])[:5],
        }

    return {
        "graphSignals": [_sig(r) for r in rows],
        "countryBreakdown": country_breakdown,
        "topSources": top_sources,
        "topPersons": top_persons,
        "timeline": timeline,
        "lanes": lanes,
        "relatedThemes": related_themes,
        "public_attention": None,
    }
