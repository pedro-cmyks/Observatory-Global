"""L1 country edition — on-demand, live (unsealed).

Composes country-scoped narrative threads + a country-scoped coverage-gaps
band + cache-first article enrichment for the Brief's country door. Read-only;
never writes engine substrate. Mirrors the daily_publication enrichment pattern
but NEVER blocks — this is a live serving endpoint, so it warm-reads the article
cache, enqueues the misses fire-and-forget, and returns immediately; the client
polls for the progressive fill.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from app import db
from app.services.coverage_gaps import COUNTRY_GAPS_SQL, country_gap_floor
from app.services.subject_geography import (
    label_geography_conflict,
    label_subject_country,
    normalize_subject_country,
)
from app.services.thread_intelligence import fetch_threads
from app.services.thread_ranking import rank_threads

logger = logging.getLogger(__name__)

CONTRACT = "country-edition-v0"
ENRICHMENT_CONTRACT = "country-edition-enrichment-v0"
SLOT_GUARD_CONTRACT = "country-edition-slot-guard-v0"

_MAX_THREADS = 24
_RECEIPTS_PER_THREAD = 4
_MAX_RECEIPT_URLS = 48


# ── slot guard (council R4 N17, 2026-08-11) ───────────────────────────────────
# Colombia's edition led with "Japan Earthquake Traps Shoppers" — court
# ENTAILED, subject-geo VERIFIED ['CO'], 95 signals — while every receipt under
# it read "terremoto 7,4 sacude Colombia". The slotter selects threads by the
# COVERAGE country of their signals and never reads the label, so a thread
# whose own receipts contradict its label text can take the #1 slot on the one
# door where that lie is loudest.
#
# The guard is a SLOT decision, not a verdict: an excluded thread is untouched
# everywhere else (global /threads, its own detail, every other edition) — it
# simply is not slotted into THIS country's sections. The exclusion is counted
# and NAMED in the payload (`slot_guard`), never silent.
#
# Precision-first, deliberately narrower than "label country != cc": a label
# naming a foreign country is only excluded when the label ALSO contradicts
# its OWN receipts (`label_geography_conflict` — the same detector the court's
# geography conjunct rides, so the two can never drift apart). A genuine
# Venezuela story carried by Colombian press names Venezuela in its receipts
# too; that is an editorial question, not a defect, and emptying the door of
# real foreign coverage would be the worse error.
#
# KNOWN RESIDUAL, counted not hidden (measured 2026-08-11). The court widens
# its absence pool to 40 receipts before vetoing, because an actor-country
# label ("Ukraine Strikes Wildberries Warehouses" over Russian receipts) reads
# as contradicted on a short window and is honest on a long one. This door has
# only the receipts already in its payload, and it must not grow queries — the
# country edition is the surface that 503s db_busy on cold open (council R4
# N26), so a per-row widening fetch would trade one defect for a worse one.
# So the actor-vs-target class can cost ONE row on ONE door here: measured at
# ~half of the 4.4% of single-country labels that conflict at all, it is named
# in `slot_guard.exclusions` where a reader (or an audit) can see exactly what
# was withheld and why, and `ATLAS_COUNTRY_EDITION_SLOT_GUARD=off` reverts it.
# Follow-up: widen this pool once the door has a warm/cached build.
def slot_guard_enabled() -> bool:
    """Kill-switch, read at call time. Default ON — the guard only ever hides
    a row whose label is measurably contradicted by its own receipts.
    `ATLAS_COUNTRY_EDITION_SLOT_GUARD=off` restores the pre-fix behavior."""
    return os.environ.get("ATLAS_COUNTRY_EDITION_SLOT_GUARD", "on").lower() == "on"


def filter_edition_slots(
    threads: list[dict],
    country_code: str,
    *,
    enabled: bool | None = None,
) -> tuple[list[dict], dict]:
    """(threads to slot, slot-guard block). Pure — no I/O.

    Excludes a thread when its label names exactly ONE country, that country
    is not this edition's, AND the thread's own evidence receipts contradict
    the label's geography claim. Every other case is kept.
    """
    on = slot_guard_enabled() if enabled is None else enabled
    cc = normalize_subject_country(country_code)
    kept: list[dict] = []
    exclusions: list[dict] = []
    for thread in threads or []:
        label = str((thread or {}).get("label") or "")
        named = label_subject_country(label) if on else None
        conflict = (
            label_geography_conflict(label, (thread or {}).get("evidence_samples"))
            if named and named != cc else None
        )
        if not conflict:
            kept.append(thread)
            continue
        exclusions.append({
            "thread_id": (thread or {}).get("thread_id"),
            "label": label,
            "label_country": conflict["label_country"],
            "edition_country": cc,
            "dominant_receipt_country": conflict["dominant_country"],
            "reason_code": "label_country_contradicts_edition_slot",
            "reason": (
                f"{conflict['summary']}; not slotted into the {cc} edition "
                "(excluded from this door only — never demoted globally)"
            ),
        })
    return kept, {
        "contract": SLOT_GUARD_CONTRACT,
        "enabled": on,
        "considered": len(threads or []),
        "excluded": len(exclusions),
        "exclusions": exclusions,
        "note": (
            "a thread whose label names a country its own receipts contradict "
            "is not slotted into this country's edition; it stays served "
            "everywhere else"
        ),
    }


def gather_receipt_urls(
    threads: list[dict],
    *,
    per_thread: int = _RECEIPTS_PER_THREAD,
    cap: int = _MAX_RECEIPT_URLS,
) -> list[str]:
    """Distinct http receipt URLs across the ranked threads (capped per thread
    and per edition), preserving order. Same cap discipline as the seal."""
    urls: list[str] = []
    for thread in threads:
        for ev in (thread.get("evidence_samples") or [])[:per_thread]:
            url = str(ev.get("url") or ev.get("source_url") or "")
            if url.startswith("http"):
                urls.append(url)
    return list(dict.fromkeys(urls))[:cap]


def build_article_enrichment(urls: list[str], states: list[dict]) -> dict:
    """Assemble the enrichment block from a warm article_states read. `pending`
    counts URLs still fetching (None/pending/queued) — the client polls those."""
    by_url = {s["url"]: s for s in states}
    ok_count = sum(1 for s in states if s.get("status") == "ok")
    pending_urls = [
        u for u in urls
        if by_url.get(u, {}).get("status") in (None, "pending", "queued")
    ]
    return {
        "contract": ENRICHMENT_CONTRACT,
        "yield": {
            "ok": ok_count,
            "attempted": len(urls),
            "pending": len(pending_urls),
        },
        "pending_urls": pending_urls,
        "articles": {
            s["url"]: {
                "status": s.get("status"),
                "via": s.get("via"),
                "excerpt": s.get("excerpt"),
                "outlet": s.get("outlet"),
                "fetched_at": s.get("fetched_at"),
            }
            for s in states
        },
        "note": (
            "server-fetched page text per receipt; partial yield is normal "
            "(paywalls/bot walls); pending = still fetching, poll for the fill"
        ),
    }


def build_country_edition_payload(
    *,
    country: str,
    country_name: str,
    ranked_threads: list[dict],
    enrichment: dict,
    coverage_gaps: list[dict],
    generated_at: datetime,
    window_hours: int,
    slot_guard: dict | None = None,
) -> dict:
    """The country-edition-v0 envelope. Pure — no I/O."""
    return {
        "contract": CONTRACT,
        "country": country,
        "country_name": country_name,
        "generated_at": generated_at.isoformat(),
        "window_hours": window_hours,
        "threads": ranked_threads,
        "coverage_gaps": coverage_gaps,
        "article_enrichment": enrichment,
        # always present, even when nothing was excluded — an absent block
        # would read as "the guard did not run" (N17's own lesson: a missing
        # check is indistinguishable from a passing one unless it is counted).
        "slot_guard": slot_guard if slot_guard is not None else {
            "contract": SLOT_GUARD_CONTRACT,
            "enabled": slot_guard_enabled(),
            "considered": len(ranked_threads or []),
            "excluded": 0,
            "exclusions": [],
        },
    }


async def fetch_country_edition(country_code: str, *, hours: int = 24) -> dict:
    """Compose the live country edition. Never blocks: warm-reads the article
    cache and enqueues the misses fire-and-forget."""
    cc = country_code.upper()
    generated_at = datetime.now(timezone.utc)

    if db.pool is None:
        return build_country_edition_payload(
            country=cc,
            country_name=cc,
            ranked_threads=[],
            enrichment=build_article_enrichment([], []),
            coverage_gaps=[],
            generated_at=generated_at,
            window_hours=hours,
        )

    gap_min = country_gap_floor()
    country_name = cc
    gap_rows: list = []
    try:
        async with db.pool.acquire() as conn:
            rec = await conn.fetchrow(
                "SELECT name FROM countries_v2 WHERE code = $1", cc
            )
            country_name = rec["name"] if rec else cc
            gap_rows = await conn.fetch(COUNTRY_GAPS_SQL, hours, cc, gap_min)
    except Exception as exc:  # gaps/name are secondary — never blank the door
        logger.warning(
            "country-edition gaps skipped cc=%s: %s: %s",
            cc, type(exc).__name__, str(exc)[:200],
        )

    threads = await fetch_threads(
        hours=hours,
        limit=_MAX_THREADS,
        country_codes=[cc],
        attach_evidence=True,
    )
    # N17 slot guard runs BEFORE enrichment so an excluded row's receipt URLs
    # never spend the edition's bounded fetch budget either.
    ranked, slot_guard = filter_edition_slots(rank_threads(threads), cc)

    urls = gather_receipt_urls(ranked)
    states: list[dict] = []
    if urls:
        try:
            from app.services.article_fetch import article_states, enqueue_fetches
            states = await article_states(urls)
            by_url = {s["url"]: s for s in states}
            # 'queued' is already in flight — don't re-enqueue (it still counts
            # as pending in the yield, hence the asymmetry with pending_urls).
            missing = [
                u for u in urls
                if by_url.get(u, {}).get("status") in (None, "pending")
            ]
            if missing:
                await enqueue_fetches(missing)      # fire-and-forget, NO wait
                # re-read: picks up the newly-inserted pending rows + any
                # concurrent request's fetch that flipped mid-enqueue.
                states = await article_states(urls)
        except Exception as exc:  # enrichment never breaks the edition
            logger.warning(
                "country-edition enrichment skipped: %s: %s",
                type(exc).__name__, str(exc)[:200],
            )

    enrichment = build_article_enrichment(urls, states)
    coverage_gaps = [dict(r) for r in gap_rows]

    logger.info(
        "country-edition cc=%s threads=%d gaps=%d enrich ok=%d/%d pending=%d "
        "slot-guard excluded=%d",
        cc, len(ranked), len(coverage_gaps),
        enrichment["yield"]["ok"], enrichment["yield"]["attempted"],
        enrichment["yield"]["pending"], slot_guard["excluded"],
    )
    for row in slot_guard["exclusions"]:
        logger.info("country-edition slot-guard cc=%s %s: %s",
                    cc, row["thread_id"], row["reason"])
    return build_country_edition_payload(
        country=cc,
        country_name=country_name,
        ranked_threads=ranked,
        enrichment=enrichment,
        coverage_gaps=coverage_gaps,
        generated_at=generated_at,
        window_hours=hours,
        slot_guard=slot_guard,
    )
