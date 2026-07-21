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
from app.services.thread_intelligence import fetch_threads
from app.services.thread_ranking import rank_threads

logger = logging.getLogger(__name__)

CONTRACT = "country-edition-v0"
ENRICHMENT_CONTRACT = "country-edition-enrichment-v0"

_MAX_THREADS = 24
_RECEIPTS_PER_THREAD = 4
_MAX_RECEIPT_URLS = 48

# Country-scoped coverage gaps = the "Under the Radar" band. Categories getting
# real domestic signal in this country but with ZERO rows clearing the gate —
# the domestic stories not yet surfacing. Mirrors briefing.coverage_gaps but
# joins signals_v2 for the country predicate and uses a lower floor (per-country
# volume is smaller than global). Tunable via ATLAS_COUNTRY_GAP_MIN.
_COUNTRY_GAPS_SQL = """
    SELECT t.slug, t.label,
           COUNT(*)::int AS raw_signals,
           COUNT(*) FILTER (WHERE a.gate_kept)::int AS verified,
           COUNT(*) FILTER (WHERE a.gate_score IS NOT NULL)::int AS scored
    FROM signal_topic_assignments a
    JOIN atlas_topics t ON t.id = a.topic_id
    JOIN signals_v2 s ON s.id = a.signal_id
    WHERE a.assigned_at > NOW() - ($1::int * INTERVAL '1 hour')
      AND s.country_code = $2
    GROUP BY t.slug, t.label
    HAVING COUNT(*) >= $3
       AND COUNT(*) FILTER (WHERE a.gate_kept) = 0
    ORDER BY raw_signals DESC
    LIMIT 6
"""


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

    gap_min = int(os.getenv("ATLAS_COUNTRY_GAP_MIN", "8"))
    async with db.pool.acquire() as conn:
        rec = await conn.fetchrow(
            "SELECT name FROM countries_v2 WHERE code = $1", cc
        )
        country_name = rec["name"] if rec else cc
        gap_rows = await conn.fetch(_COUNTRY_GAPS_SQL, hours, cc, gap_min)

    threads = await fetch_threads(
        hours=hours,
        limit=_MAX_THREADS,
        country_codes=[cc],
        attach_evidence=True,
    )
    ranked = rank_threads(threads)

    urls = gather_receipt_urls(ranked)
    states: list[dict] = []
    if urls:
        try:
            from app.services.article_fetch import article_states, enqueue_fetches
            states = await article_states(urls)
            by_url = {s["url"]: s for s in states}
            missing = [
                u for u in urls
                if by_url.get(u, {}).get("status") in (None, "pending")
            ]
            if missing:
                await enqueue_fetches(missing)      # fire-and-forget, NO wait
                states = await article_states(urls)  # re-read; warm ones may flip
        except Exception as exc:  # enrichment never breaks the edition
            logger.warning(
                "country-edition enrichment skipped: %s: %s",
                type(exc).__name__, str(exc)[:200],
            )

    enrichment = build_article_enrichment(urls, states)
    coverage_gaps = [dict(r) for r in gap_rows]

    logger.info(
        "country-edition cc=%s threads=%d gaps=%d enrich ok=%d/%d pending=%d",
        cc, len(ranked), len(coverage_gaps),
        enrichment["yield"]["ok"], enrichment["yield"]["attempted"],
        enrichment["yield"]["pending"],
    )
    return build_country_edition_payload(
        country=cc,
        country_name=country_name,
        ranked_threads=ranked,
        enrichment=enrichment,
        coverage_gaps=coverage_gaps,
        generated_at=generated_at,
        window_hours=hours,
    )
