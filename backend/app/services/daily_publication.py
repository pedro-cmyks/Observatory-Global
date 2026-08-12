"""Offline construction of the sealed Atlas daily PublicationPackage.

This module is intentionally independent of FastAPI. The M1 batch runtime
builds the expensive graph/package once; the HTTP router only reads the compact
stored artifact.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import html
import logging
import os
import re
import time
import unicodedata
from typing import Any

import httpx
import numpy as np

from app import db
from app.services.daily_edition import (
    apply_sample_coverage,
    fetch_daily_candidates,
    order_spine_by_publishability,
    select_daily_edition,
)
from app.services.investigation_graph import (
    GraphRequest,
    PublicationPackageRequest,
    assemble_investigation_graph,
    build_publication_package,
)
from app.services.brief_sections import fetch_gap, fetch_rising
from app.services.investigation_nodes import ResolveNodeInput, resolve_investigation_node
from app.services.subjects import classify_subject
from app.services.source_tiers import classify_source_tier
from app.services.subject_geography import (
    decode_headline,
    infer_receipt_subject_geography,
    measure_subject_geography_coherence,
)
from app.services.publication_synthesis import (
    SynthesizeRequest,
    synthesize_publication_article,
)
from app.core.iso_country_names import ISO_COUNTRY_NAMES
from app.services.country_codes import fips_to_iso

logger = logging.getLogger(__name__)


def evidence_fit_metrics_from_vectors(
    label_vector: np.ndarray,
    receipt_vectors: np.ndarray,
) -> dict[str, float]:
    """Return label support and internal coherence in one embedding space."""
    label = np.asarray(label_vector, dtype=np.float32).reshape(-1)
    receipts = np.asarray(receipt_vectors, dtype=np.float32)
    label /= max(float(np.linalg.norm(label)), 1e-12)
    receipts /= np.maximum(np.linalg.norm(receipts, axis=1, keepdims=True), 1e-12)
    label_scores = receipts @ label
    if len(receipts) > 1:
        pairwise = receipts @ receipts.T
        pair_scores = pairwise[np.triu_indices(len(receipts), 1)]
    else:
        pair_scores = np.asarray([1.0], dtype=np.float32)
    return {
        "pair_median": round(float(np.median(pair_scores)), 6),
        "pair_p10": round(float(np.quantile(pair_scores, 0.10)), 6),
        "label_median": round(float(np.median(label_scores)), 6),
        "label_p25": round(float(np.quantile(label_scores, 0.25)), 6),
    }


def _openai_embed_publication_texts(texts: list[str]) -> np.ndarray:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    vectors: list[list[float]] = []
    with httpx.Client(timeout=90.0) as client:
        for offset in range(0, len(texts), 512):
            response = client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "text-embedding-3-small",
                    "input": texts[offset:offset + 512],
                },
            )
            response.raise_for_status()
            rows = sorted(response.json()["data"], key=lambda row: row["index"])
            vectors.extend(row["embedding"] for row in rows)
    return np.asarray(vectors, dtype=np.float32)


async def measure_publication_evidence_fit(
    labels_by_topic: dict[str, str],
    evidence_rows_by_topic: dict[str, list[dict[str, Any]]],
    *,
    embed_texts=None,
) -> tuple[set[str], dict[str, dict[str, Any]], dict[str, Any]]:
    """Measure every single-cluster story and return a complete quality ledger.

    Multi-cluster umbrellas abstain because one child label cannot honestly
    judge a compound story. They remain eligible with an explicit reason.
    """
    all_topic_ids = set(evidence_rows_by_topic)
    measurable: dict[str, tuple[str, list[str]]] = {}
    ledger: dict[str, dict[str, Any]] = {}
    for topic_id, rows in evidence_rows_by_topic.items():
        cluster_ids = {
            int(row["edition_cluster_id"])
            for row in rows if row.get("edition_cluster_id") is not None
        }
        headlines = [
            html.unescape(str(row.get("headline") or "")).strip()
            for row in rows if str(row.get("headline") or "").strip()
        ]
        if len(cluster_ids) != 1:
            ledger[topic_id] = {
                "status": "eligible",
                "cluster_count": len(cluster_ids),
                "receipt_count": len(headlines),
                "reason_codes": ["publication_evidence_fit_abstained_compound_story"],
            }
            continue
        if len(headlines) < 2:
            ledger[topic_id] = {
                "status": "eligible",
                "cluster_count": len(cluster_ids),
                "receipt_count": len(headlines),
                "reason_codes": ["publication_evidence_fit_abstained_thin_receipts"],
            }
            continue
        measurable[topic_id] = (labels_by_topic[topic_id], headlines)

    texts: list[str] = []
    slices: dict[str, tuple[int, int]] = {}
    for topic_id, (label, headlines) in measurable.items():
        start = len(texts)
        texts.extend([html.unescape(label), *headlines])
        slices[topic_id] = (start, len(headlines))
    if not texts:
        return all_topic_ids, ledger, {
            "engine": "openai-text-embedding-3-small",
            "status": "abstained",
            "reason": "no_measurable_single_cluster_stories",
            "universe_count": 0,
            "semantic_ceiling": False,
            "omission_ledger": "complete",
        }

    provider = embed_texts or _openai_embed_publication_texts
    try:
        vectors = await asyncio.to_thread(provider, texts)
    except Exception as exc:
        for topic_id in all_topic_ids:
            ledger.setdefault(topic_id, {
                "status": "eligible",
                "reason_codes": ["publication_evidence_fit_provider_unavailable"],
            })
        return all_topic_ids, ledger, {
            "engine": "openai-text-embedding-3-small",
            "status": "degraded",
            "reason": f"provider_unavailable:{type(exc).__name__}",
            "universe_count": len(measurable),
            "semantic_ceiling": False,
            "omission_ledger": "complete",
        }

    metrics_by_topic: dict[str, dict[str, float]] = {}
    for topic_id, (start, n_receipts) in slices.items():
        metrics_by_topic[topic_id] = {
            **evidence_fit_metrics_from_vectors(
                vectors[start], vectors[start + 1:start + 1 + n_receipts],
            ),
            "receipt_count": n_receipts,
        }
    accepted, measured_ledger, method = classify_evidence_fit_outliers(metrics_by_topic)
    ledger.update(measured_ledger)
    accepted.update(all_topic_ids - set(measurable))
    return accepted, ledger, method


def classify_evidence_fit_outliers(
    metrics_by_topic: dict[str, dict[str, float]],
    *,
    tail_quantile: float = 0.10,
    minimum_universe: int = 20,
) -> tuple[set[str], dict[str, dict[str, Any]], dict[str, Any]]:
    """Detect severe label/evidence mixtures without judging subject matter.

    Both axes must sit in the complete universe's low tail: internal receipt
    coherence and current-label support. This protects broad but correctly
    labeled stories from a single-axis penalty. It is a publication-quality
    downrank only; every row remains in the returned omission ledger.
    """
    topic_ids = set(metrics_by_topic)
    base_method = {
        "engine": "openai-text-embedding-3-small",
        "rule": "bivariate_complete_universe_low_tail",
        "tail_quantile": tail_quantile,
        "minimum_universe": minimum_universe,
        "universe_count": len(metrics_by_topic),
        "semantic_ceiling": False,
        "omission_ledger": "complete",
    }
    if len(metrics_by_topic) < minimum_universe:
        ledger = {
            topic_id: {
                **metrics,
                "status": "eligible",
                "reason_codes": ["publication_evidence_fit_abstained_thin_universe"],
            }
            for topic_id, metrics in metrics_by_topic.items()
        }
        return topic_ids, ledger, {**base_method, "status": "abstained"}

    pair_threshold = float(np.quantile(
        [row["pair_median"] for row in metrics_by_topic.values()], tail_quantile,
    ))
    label_threshold = float(np.quantile(
        [row["label_median"] for row in metrics_by_topic.values()], tail_quantile,
    ))
    accepted: set[str] = set()
    ledger: dict[str, dict[str, Any]] = {}
    for topic_id, metrics in metrics_by_topic.items():
        rejected = (
            metrics["pair_median"] <= pair_threshold
            and metrics["label_median"] <= label_threshold
        )
        if not rejected:
            accepted.add(topic_id)
        ledger[topic_id] = {
            **metrics,
            "status": "downranked" if rejected else "eligible",
            "reason_codes": (
                ["publication_evidence_fit_bivariate_low_tail"] if rejected else []
            ),
        }
    return accepted, ledger, {
        **base_method,
        "status": "measured",
        "pair_median_threshold": round(pair_threshold, 6),
        "label_median_threshold": round(label_threshold, 6),
        "downranked_count": len(metrics_by_topic) - len(accepted),
    }


def choose_current_edition_label(
    identity_label: str,
    evidence_rows: list[dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    """Choose the label supported by the sealed window's current clusters.

    ``dynamic_topics.label`` is a persistent identity label. It is intentionally
    stable across snapshots, so it can lag the event currently represented by a
    living thread. A daily newspaper needs the current event label instead. For
    non-umbrella threads there is one current cluster; for umbrellas we choose
    the child cluster supported by the most receipts, then distinct sources,
    then cluster size. Every current receipt participates and the decision is
    returned as an explicit method receipt.
    """
    support: dict[tuple[int, str], dict[str, Any]] = {}
    for position, row in enumerate(evidence_rows):
        label = str(row.get("edition_cluster_label") or "").strip()
        raw_cluster_id = row.get("edition_cluster_id")
        if not label or raw_cluster_id is None:
            continue
        cluster_id = int(raw_cluster_id)
        key = (cluster_id, label)
        item = support.setdefault(key, {
            "receipts": set(),
            "sources": set(),
            "cluster_signal_count": int(row.get("edition_cluster_n_signals") or 0),
        })
        item["receipts"].add(row.get("id") or f"row:{position}")
        source = str(row.get("source_name") or "").strip().lower()
        if source:
            item["sources"].add(source)
        item["cluster_signal_count"] = max(
            item["cluster_signal_count"],
            int(row.get("edition_cluster_n_signals") or 0),
        )

    if not support:
        return identity_label, {
            "method": "identity_label_fallback_no_current_cluster",
            "identity_label": identity_label,
            "edition_label": identity_label,
            "cluster_id": None,
            "receipt_support": 0,
            "source_support": 0,
            "cluster_signal_count": 0,
        }

    (cluster_id, edition_label), winner = sorted(
        support.items(),
        key=lambda item: (
            -len(item[1]["receipts"]),
            -len(item[1]["sources"]),
            -item[1]["cluster_signal_count"],
            item[0][1].casefold(),
            item[0][0],
        ),
    )[0]
    return edition_label, {
        "method": "current_snapshot_cluster_receipt_support",
        "identity_label": identity_label,
        "edition_label": edition_label,
        "cluster_id": cluster_id,
        "receipt_support": len(winner["receipts"]),
        "source_support": len(winner["sources"]),
        "cluster_signal_count": winner["cluster_signal_count"],
    }


def verified_subjects_from_receipts(receipts: list[dict[str, Any]]) -> list[str]:
    """Return people corroborated by distinct receipts and distinct outlets.

    The untyped ``signals_v2.persons`` lane is discovery evidence, not truth by
    itself. A name completes the publication package's ``who`` dimension only
    after it appears in at least two frozen receipts from at least two outlets
    and passes the shared subject typer. Ordering is first-observed and stable.
    """
    evidence: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    def normalized(value: Any) -> str:
        value = unicodedata.normalize("NFKD", decode_headline(value).casefold())
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return " ".join(re.findall(r"[^\W_]+", value, flags=re.UNICODE))

    for position, row in enumerate(receipts):
        receipt_id = row.get("id") or row.get("source_url") or f"row:{position}"
        outlet = str(row.get("source_name") or "").strip().lower()
        if not outlet:
            continue
        headline = normalized(row.get("headline"))
        for raw_name in row.get("persons") or []:
            name = str(raw_name or "").strip().lower()
            if not name or classify_subject(name) != "person":
                continue
            normalized_name = normalized(name)
            tokens = normalized_name.split()
            if not tokens:
                continue
            full_mention = f" {normalized_name} " in f" {headline} "
            surname_mention = (
                len(tokens) >= 2
                and len(tokens[-1]) >= 4
                and f" {tokens[-1]} " in f" {headline} "
            )
            if not full_mention and not surname_mention:
                continue
            if name not in evidence:
                evidence[name] = {"receipts": set(), "outlets": set()}
                order.append(name)
            evidence[name]["receipts"].add(receipt_id)
            evidence[name]["outlets"].add(outlet)
    return [
        name for name in order
        if len(evidence[name]["receipts"]) >= 2
        and len(evidence[name]["outlets"]) >= 2
    ]


_DAILY_EVIDENCE_SQL = """
WITH requested AS (
    SELECT unnest($1::bigint[]) AS requested_id
), underlying AS (
    SELECT requested.requested_id, child.id AS topic_id
    FROM requested
    JOIN dynamic_topics root ON root.id = requested.requested_id
    JOIN dynamic_topics child ON (
        (NOT root.is_umbrella AND child.id = root.id)
        OR (root.is_umbrella AND child.parent_id = root.id)
    )
), current_cluster AS (
    SELECT DISTINCT ON (underlying.requested_id, underlying.topic_id)
           underlying.requested_id, underlying.topic_id,
           ec.id AS edition_cluster_id,
           ec.label AS edition_cluster_label,
           ec.n_signals AS edition_cluster_n_signals
    FROM underlying
    JOIN dynamic_topic_members dtm ON dtm.dynamic_topic_id = underlying.topic_id
    JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
    ORDER BY underlying.requested_id, underlying.topic_id,
             dtm.snapshot_at DESC, ec.n_signals DESC, ec.id DESC
), current_evidence AS (
    SELECT DISTINCT ON (underlying.requested_id, s.id)
           underlying.requested_id, s.id, s.headline, s.source_name,
           s.source_url, s.source_lang, s.source_origin_country,
           s.country_code, s.timestamp, s.persons, s.is_state_media,
           s.source_family,
           underlying.edition_cluster_id,
           underlying.edition_cluster_label,
           underlying.edition_cluster_n_signals
    FROM current_cluster underlying
    JOIN topic_members tm
      ON tm.topic_id = ('dynamic-topic-' || underlying.topic_id::text)
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.role = 'evidence'
      AND tm.engine_version = 'v1-compat'
      AND tm.quarantined IS NOT TRUE
      AND s.timestamp >= $3::timestamptz - ($2::int * INTERVAL '1 hour')
      AND s.timestamp <= $3::timestamptz
    ORDER BY underlying.requested_id, s.id, tm.assigned_at DESC
)
SELECT ('dynamic-topic-' || requested_id::text) AS topic_id,
       id, headline, source_name, source_url, source_lang,
       source_origin_country, country_code, timestamp, persons,
       is_state_media, source_family,
       edition_cluster_id, edition_cluster_label, edition_cluster_n_signals
FROM current_evidence
ORDER BY requested_id, timestamp DESC, id DESC
"""


def build_lead_synthesis_payload(
    label: str,
    receipts: list[dict[str, Any]],
    *,
    gaps: list[str],
    low_coherence: bool = False,
) -> dict[str, Any]:
    """SynthesizeRequest payload for the daily lead story — the front-page cited
    article. The deduped frozen receipts become the authoritative numbered
    citation table. A single coherent lead story is one publishable mini-article;
    the twelve unrelated top stories are never fused into one piece (that would be
    the grab-bag the coherence guard rejects).
    """
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in receipts:
        headline = decode_headline(row.get("headline"))
        key = headline.lower()
        if not headline or key in seen:
            continue
        seen.add(key)
        items.append({
            "headline": headline,
            "source": row.get("source_name") or row.get("source"),
            "date": (str(row.get("timestamp") or row.get("date") or "")[:10] or None),
            "url": row.get("source_url") or row.get("url"),
            # Carried into the numbered citation table so a state-media source
            # is flagged in the front-page citations, never presented as neutral
            # (council R3 P0).
            "is_state_media": bool(row.get("is_state_media")),
        })
    return {
        "title": label,
        "pins": [{
            "label": label,
            "type": "story",
            "evidence": [item["headline"] for item in items],
            "evidence_items": items,
            "low_coherence": bool(low_coherence),
        }],
        "gaps": list(gaps or []),
    }


def _as_utc(t: datetime | None) -> datetime | None:
    if t is None:
        return None
    return t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)


def resolve_edition_end(
    max_last_seen: datetime | None,
    max_signal_ts: datetime | None,
    now: datetime,
) -> datetime:
    """Anchor the edition's data-window end on the freshest ACTUAL data, capped
    at ``now``.

    Historically this was ``MAX(last_seen)`` over active top-level topics — but
    ``last_seen`` equals the *snapshot_at* of the last clustering pass, so on a
    slow (mindful) pipeline the seal runs hours after that timestamp. The window
    ``[edition_end - 24h, edition_end]`` then misses the FRESH evidence assigned
    since, receipt-eligibility drains to 0 (empty degraded edition), and
    ``data_lag`` trips the >6h degrade even though ingestion is healthy. Using
    the freshest ingested signal instead keeps the window over fresh evidence and
    makes ``data_lag`` the REAL ingestion lag (small when healthy, honestly large
    only when ingestion genuinely stalls).
    """
    cands = [t for t in (_as_utc(max_last_seen), _as_utc(max_signal_ts)) if t is not None]
    if not cands:
        return now
    return min(now, max(cands))


async def fetch_daily_publication(
    *,
    hours: int = 24,
    serving_budget: bool = False,
) -> dict[str, Any]:
    """Build a complete sealed edition outside the serving request path."""
    if db.pool is None:
        return {
            "contract": "atlas-daily-publication-v1",
            "hours": hours,
            "package": None,
            "selection": None,
            "completion": {
                "cursor_exhausted": False,
                "truncated": False,
                "reason": "no_db",
            },
        }

    generated_at = datetime.now(timezone.utc)
    async with db.pool.acquire() as conn:
        max_last_seen = await conn.fetchval(
            """
            SELECT MAX(last_seen)
            FROM dynamic_topics
            WHERE state = 'active' AND parent_id IS NULL
            """,
            timeout=5,
        )
        # Freshest ACTUAL ingested data (bounded to the recent partition so the
        # MAX rides the timestamp index, never a full scan). Anchors the edition
        # window on real data, not the stale clustering snapshot_at.
        max_signal_ts = await conn.fetchval(
            "SELECT MAX(timestamp) FROM signals_v2 WHERE timestamp > NOW() - INTERVAL '2 days'",
            timeout=5,
        )
        edition_end = resolve_edition_end(max_last_seen, max_signal_ts, generated_at)
        candidates, traversal = await fetch_daily_candidates(
            conn, hours=hours, edition_end=edition_end,
        )
        preliminary = select_daily_edition(candidates, display_slots=len(candidates))
        ranked_ids = [row.thread_id for row in preliminary.ledger]
        by_topic: dict[str, list[dict[str, Any]]] = {}
        sources_by_topic: dict[str, set[str]] = {}
        origins_by_topic: dict[str, set[str]] = {}
        languages_by_topic: dict[str, set[str]] = {}
        countries_by_topic: dict[str, set[str]] = {}
        subject_receipts_by_topic: dict[str, list[dict[str, Any]]] = {}
        label_receipts_by_topic: dict[str, list[dict[str, Any]]] = {}
        evidence_counts: dict[str, int] = {}
        receipt_checked_ids: set[str] = set()
        receipt_batches = 0
        receipt_fetch_error: str | None = None
        receipt_evidence_query_ms = 0.0
        selection = select_daily_edition(
            candidates,
            display_slots=12,
            receipt_eligible_ids=set(),
            receipt_checked_ids=set(),
        )
        for offset in range(0, len(ranked_ids), 32):
            chunk = ranked_ids[offset:offset + 32]
            numeric_ids = [
                int(thread_id.removeprefix("dynamic-topic-"))
                for thread_id in chunk
                if thread_id.removeprefix("dynamic-topic-").isdigit()
            ]
            sample_started = time.monotonic()
            try:
                signal_rows = await conn.fetch(
                    _DAILY_EVIDENCE_SQL, numeric_ids, hours, edition_end,
                    timeout=12 if serving_budget else 60,
                )
                receipt_evidence_query_ms += (time.monotonic() - sample_started) * 1000
            except TimeoutError:
                receipt_fetch_error = "current_evidence_provider_timeout"
                break
            receipt_batches += 1
            receipt_checked_ids.update(chunk)
            for raw in signal_rows:
                row = dict(raw)
                topic_id = str(row.pop("topic_id"))
                # Credibility provenance on every receipt (source_tiers #217).
                # State-controlled outlets (RT/Sputnik/IRNA/etc, is_state_media
                # at ingest) MUST NOT ride into a citation as neutral — council
                # R3 P0. Authoritative: the ingest flag wins even if a name list
                # would miss the outlet; tier fills the previously-null receipt
                # tier so `_receipt_rows` and the citation table carry it.
                row["is_state_media"] = bool(row.get("is_state_media"))
                row["credibility_tier"] = classify_source_tier(
                    row.get("source_name"),
                    is_state_media=row["is_state_media"],
                    source_family=row.get("source_family"),
                ).label
                # R4 N18: the GDELT lane carries no ingest flag, so SANA sealed
                # `tier:"mainstream", is_state_media:false` while the article
                # prose said "Syrian state media". The classifier now carries
                # the domain list; the boolean must AGREE with the tier it
                # rides next to — one payload, one truth. Upgrade-only (a
                # true ingest flag is never un-set).
                if row["credibility_tier"] == "state":
                    row["is_state_media"] = True
                evidence_counts[topic_id] = evidence_counts.get(topic_id, 0) + 1
                source = row.get("source_name")
                if source:
                    sources_by_topic.setdefault(topic_id, set()).add(str(source))
                origin = row.get("source_origin_country")
                if origin:
                    origins_by_topic.setdefault(topic_id, set()).add(str(origin).upper())
                lang = row.get("source_lang")
                if lang:
                    languages_by_topic.setdefault(topic_id, set()).add(str(lang).lower())
                country = row.get("country_code")
                if country:
                    countries_by_topic.setdefault(topic_id, set()).add(str(country).upper())
                if row.get("persons"):
                    subject_receipts_by_topic.setdefault(topic_id, []).append(dict(row))
                label_receipts_by_topic.setdefault(topic_id, []).append(dict(row))
                if len(by_topic.setdefault(topic_id, [])) < 6:
                    by_topic[topic_id].append(dict(row))

        # LO QUE SUBE + EL VACÍO (T3.2) — the SAME functions the live briefing
        # calls, on the SAME connection, inside the sealed window. Template
        # prose over measured fields: no provider, no network, so G-SELLO holds
        # (the seal gains no new dependency it could die on). Rising reuses the
        # receipts already in hand for edition stories and only queries for the
        # ones outside the edition. EL VACÍO's ledger write is stamped 'seal'.
        section_timeout = 12.0 if serving_budget else 30.0
        rising_section = await fetch_rising(
            conn, hours=hours, window_end=edition_end,
            receipts_by_thread=by_topic, timeout=section_timeout,
        )
        gap_section = await fetch_gap(
            conn, window_end=edition_end, computed_by="seal",
            timeout=section_timeout,
        )

    label_decisions: dict[str, tuple[str, dict[str, Any]]] = {
        candidate.thread_id: choose_current_edition_label(
            candidate.label,
            label_receipts_by_topic.get(candidate.thread_id, []),
        )
        for candidate in candidates
    }
    current_labeled_candidates = [
        candidate.model_copy(update={
            "label": label_decisions[candidate.thread_id][0],
        })
        for candidate in candidates
    ]
    fit_accepted_ids, fit_ledger, fit_method = await measure_publication_evidence_fit(
        {
            thread_id: decision[0]
            for thread_id, decision in label_decisions.items()
            if thread_id in label_receipts_by_topic
        },
        label_receipts_by_topic,
    )
    # The seal's receipt-less guard: selection SKIPS anything outside this set
    # (daily_edition.select_daily_edition), so a story with no resolved receipt
    # can never enter the edition — the "116 SIGNALS · 0 sources" state the
    # 2026-08-12 cold-user probe hit is structurally impossible here, and was
    # served by the LIVE fallback path instead (thread_intelligence.py, fixed
    # there). Verified against the 2026-08-11 artifact: 12/12 sealed story
    # nodes carried >= 4 receipts. Frozen by
    # tests/test_thread_source_count_starvation.py and test_daily_edition.py.
    receipt_eligible_ids = set(by_topic) & fit_accepted_ids
    enriched_candidates = apply_sample_coverage(
        current_labeled_candidates,
        sources_by_topic=sources_by_topic,
        origins_by_topic=origins_by_topic,
        languages_by_topic=languages_by_topic,
        countries_by_topic=countries_by_topic,
    )
    selection = select_daily_edition(
        enriched_candidates,
        display_slots=12,
        receipt_eligible_ids=receipt_eligible_ids,
        receipt_checked_ids=receipt_checked_ids,
        quality_ledger_by_id=fit_ledger,
    )

    selected_by_id = {
        candidate.thread_id: candidate
        for candidate in enriched_candidates
        if candidate.thread_id in selection.selected_ids
    }
    # Spine layout: lead with the most publishable stories (subject-geography
    # verified, not a grab-bag umbrella) and demote incoherent umbrellas.
    # Selection membership is unchanged; every selected story stays in the spine
    # and the ledger — this reorders visual priority only, reason-coded.
    publishability_by_id = {
        thread_id: {
            "subject_verified": infer_receipt_subject_geography(
                by_topic.get(thread_id, [])
            ).get("status") == "verified",
            "grab_bag": bool(measure_subject_geography_coherence(
                by_topic.get(thread_id, [])
            ).get("grab_bag")),
        }
        for thread_id in selection.selected_ids
    }
    spine_order = order_spine_by_publishability(selection.selected_ids, publishability_by_id)
    spine_reason_by_id = dict(spine_order)
    ordered_ids = [thread_id for thread_id, _ in spine_order]
    lead_id = ordered_ids[0] if ordered_ids else None

    nodes = []
    window_start = edition_end - timedelta(hours=hours)
    for thread_id in ordered_ids:
        candidate = selected_by_id[thread_id]
        receipts = by_topic.get(thread_id, [])
        top_countries = list(dict.fromkeys(
            (
                code if code in ISO_COUNTRY_NAMES else fips_to_iso(code)
            )
            for row in receipts
            if (code := str(row.get("country_code") or "").upper())
        ))
        top_sources = sorted(sources_by_topic.get(thread_id, set()))
        top_entities = list(dict.fromkeys(
            str(person)
            for row in subject_receipts_by_topic.get(thread_id, [])
            for person in (row.get("persons") or [])
            if person
        ))
        verified_subjects = verified_subjects_from_receipts(
            subject_receipts_by_topic.get(thread_id, [])
        )
        subject_geography = infer_receipt_subject_geography(receipts)
        edition_label, label_receipt = label_decisions[thread_id]
        live = {
            "thread_id": thread_id,
            "label": edition_label,
            "category": candidate.category,
            "signal_count": candidate.current_signals,
            "source_count": len(top_sources),
            "top_countries": top_countries,
            "top_sources": top_sources,
            "top_entities": top_entities,
            "evidence_samples": receipts,
            "movement": {
                "velocity": candidate.kalman_velocity,
                "surprise": candidate.kalman_surprise,
                "uncertainty": candidate.kalman_uncertainty,
                "observations": candidate.kalman_observations,
                "prediction_claim": False,
            },
        }

        async def _frozen_thread_fetcher(*, thread_id: str, hours: int, _live=live):
            return _live

        nodes.append(await resolve_investigation_node(
            ResolveNodeInput(
                node_type="story",
                subtype="thread",
                ref_id=thread_id,
                label=edition_label,
                observation_window={
                    "range_start": window_start,
                    "range_end": edition_end,
                    "mode": "live",
                },
                snapshot={
                    "edition_role": (
                        "lead" if thread_id == lead_id else "supporting"
                    ),
                    "spine_layout_reason": spine_reason_by_id.get(thread_id),
                    "selection": next(
                        row.model_dump(mode="json") for row in selection.ledger
                        if row.thread_id == thread_id
                    ),
                    "evidence_sampling": {
                        "method": "current_window_topic_members_evidence_role",
                        "available_receipts": evidence_counts.get(thread_id, 0),
                        "display_receipt_sample": 6,
                        "semantic_ceiling": False,
                    },
                    "label_receipt": label_receipt,
                },
                quality={
                    "coherence": candidate.coherence,
                    "noise_rate": candidate.noise_rate,
                    "publication_evidence_fit": fit_ledger.get(thread_id),
                    "verified_subjects": verified_subjects,
                    "subject_status": "verified" if verified_subjects else (
                        "unverified" if top_entities else "not_available"
                    ),
                    "verified_subject_countries": subject_geography[
                        "verified_subject_countries"
                    ],
                    "subject_country_status": subject_geography["status"],
                    "subject_geography": subject_geography,
                },
            ),
            thread_fetcher=_frozen_thread_fetcher,
        ))

    # dossier-connections-v1 is currently relative to wall-clock NOW. Importing
    # it would mix temporal contracts with this explicit sealed window.
    dossier_payload = {
        "contract": "dossier-connections-v1",
        "nodes": [],
        "edges": [],
        "neighbors": [],
        "distributions": None,
        "unresolved": selection.selected_ids,
        "reason": "explicit_edition_window_not_supported",
    } if selection.selected_ids else None
    graph = assemble_investigation_graph(
        GraphRequest(
            nodes=nodes,
            enabled_engines=["exact", "context"],
            relation_payloads={
                "dossier_connections": dossier_payload,
            } if dossier_payload is not None else {},
        ),
        measured_at=generated_at,
    )
    data_lag_hours = round(
        max(0.0, (generated_at - edition_end).total_seconds() / 3600), 3,
    )
    input_gaps: list[str] = []
    if data_lag_hours > 6:
        input_gaps.append("edition_cutoff_stale_over_6h")
    if receipt_fetch_error:
        input_gaps.append(receipt_fetch_error)
    if fit_method.get("status") != "measured":
        input_gaps.append("publication_evidence_fit_not_measured")
    if not selection.selected_ids:
        input_gaps.append("no_current_window_receipt_eligible_stories")
    package = build_publication_package(PublicationPackageRequest(
        title=f"Atlas Daily Investigation — {edition_end.date().isoformat()}",
        authorship="system",
        graph=graph,
        generated_at=generated_at,
        selection_ledger={
            "selection": selection.model_dump(mode="json"),
            "candidate_traversal": traversal,
            "receipt_checked_count": len(receipt_checked_ids),
            "receipt_eligible_count": len(receipt_eligible_ids),
            "publication_evidence_fit": fit_method,
        },
        input_gaps=input_gaps,
    ))
    package.rising = rising_section
    package.gap = gap_section
    # ── Workbench-enrichment bridge (spec 2026-07-20 — Pedro: all three
    # sections). Fetch the edition's receipt pages server-side BEFORE the lead
    # synthesis so (a) the front-page article quotes bodies, not just headlines
    # (synthesize_publication_article already reads pinned_articles), and
    # (b) every section's receipts carry a frozen excerpt. Best-effort by
    # contract: any failure and the edition seals exactly as before. Never runs
    # under serving_budget (request path stays fast).
    if not serving_budget:
        try:
            from app.services.article_fetch import article_states, enqueue_fetches
            urls: list[str] = []
            for tid in list(by_topic):
                for row in by_topic[tid][:4]:          # cap per story
                    u = str(row.get("source_url") or row.get("url") or "")
                    if u.startswith("http"):
                        urls.append(u)
            urls = list(dict.fromkeys(urls))[:48]      # cap per edition
            if urls:
                # CACHE-FIRST (2026-07-21): the enrichment fetch (48 urls @ conc 3,
                # paywalls/timeouts) OUTLASTS any seal-time wait — measured 07-20:
                # the seal closed 16:38, the fetch finished 18:01, so the excerpts
                # missed the edition entirely (silent absence, no exception). So:
                # READ the warm pinned_articles cache FIRST (excerpts accumulate
                # continuously across nightlies), build the block from whatever is
                # already fetched, and ENQUEUE only the not-yet-fetched ones so
                # they are ready for the NEXT seal. A brief opportunistic top-up
                # grabs any that land fast; the seal never blocks on the slow tail.
                states = await article_states(urls)
                by_url = {s["url"]: s for s in states}
                missing = [u for u in urls
                           if by_url.get(u, {}).get("status") in (None, "pending")]
                if missing:
                    await enqueue_fetches(missing)
                    for _ in range(3):                 # ≤15s opportunistic top-up
                        await asyncio.sleep(5)
                        states = await article_states(urls)
                        by_url = {s["url"]: s for s in states}
                        if all(by_url.get(u, {}).get("status") not in (None, "pending")
                               for u in urls):
                            break
                ok_count = sum(1 for s in states if s.get("status") == "ok")
                pending_count = sum(1 for s in states
                                    if s.get("status") in (None, "pending"))
                package.article_enrichment = {
                    "contract": "edition-article-enrichment-v0",
                    "yield": {"ok": ok_count, "attempted": len(urls),
                              "pending": pending_count},
                    "note": ("server-fetched page text per receipt; partial yield "
                             "is normal (paywalls/bot walls); pending = still "
                             "fetching, will be ready for the next seal"),
                    "articles": {
                        s["url"]: {
                            "status": s.get("status"), "via": s.get("via"),
                            "excerpt": s.get("excerpt"), "outlet": s.get("outlet"),
                            "fetched_at": s.get("fetched_at"),
                        }
                        for s in states
                    },
                }
                # Observability: the yield is now ALWAYS logged (07-20 lesson — a
                # silent absence hid the seal/fetch timing bug for a full day).
                logger.info(
                    "daily-publication enrichment: yield ok=%d/%d pending=%d",
                    ok_count, len(urls), pending_count)
            else:
                logger.info("daily-publication enrichment: no receipt urls to fetch")
        except Exception as exc:
            # Enrichment must never block the seal — degrade to headlines-only.
            # (logger, not print: the 07-01 matview lesson — bare prints die silent.)
            logger.warning("daily-publication enrichment skipped: %s: %s",
                           type(exc).__name__, str(exc)[:200])
    # Front-page cited article: synthesize the lead story into a publishable
    # mini-article (lede → cited body → what we don't know), citations resolved
    # server-side against the frozen receipt table. A single coherent lead is one
    # article; the unrelated top stories are never fused. Degrades openly if the
    # provider is unavailable.
    if lead_id is not None and by_topic.get(lead_id):
        lead_label = label_decisions[lead_id][0]
        lead_grab = bool(publishability_by_id.get(lead_id, {}).get("grab_bag"))
        lead_payload = build_lead_synthesis_payload(
            lead_label, by_topic[lead_id], gaps=list(package.gaps), low_coherence=lead_grab,
        )
        try:
            article = await synthesize_publication_article(SynthesizeRequest(**lead_payload))
        except Exception:
            article = None
        if article and (article.get("lede") or article.get("body") or article.get("synthesis")):
            package.article = {**article, "story_id": lead_id, "story_label": lead_label}
            package.prose_status = "generated"
        else:
            package.prose_status = "unavailable"
        # COVERAGE CHECK (spec 2026-07-20): cross-read the LEAD story's fetched
        # bodies — do the outlets corroborate or diverge on the numbers/actors?
        # Findings carry both verbatim quotes, labeled possible. Lead-only by
        # design (cross-story comparison is noise); best-effort like the rest.
        if not serving_budget:
            try:
                from app.services.article_read import cross_read
                lead_urls = [
                    str(r.get("source_url") or r.get("url") or "")
                    for r in by_topic[lead_id]
                ]
                lead_urls = [u for u in dict.fromkeys(lead_urls) if u.startswith("http")][:8]
                if len(lead_urls) >= 2:
                    cc = await cross_read(lead_urls)
                    if cc.get("articles_with_claims", 0) >= 2 or cc.get("findings"):
                        package.coverage_check = {
                            **{k: cc.get(k) for k in (
                                "contract", "findings", "articles_read",
                                "articles_with_claims", "independent_corroborations",
                                "shared_source_findings", "model", "note",
                            )},
                            "story_id": lead_id,
                        }
            except Exception as exc:
                logger.warning("daily-publication coverage check skipped: %s: %s",
                               type(exc).__name__, str(exc)[:200])
    return {
        "contract": "atlas-daily-publication-v1",
        "hours": hours,
        "package": package,
        "selection": selection,
        "graph": graph,
        "completion": {
            **traversal,
            "generated_at": generated_at.isoformat(),
            "data_lag_hours": data_lag_hours,
            "resolved_selected_nodes": graph.completion.resolved_nodes,
            "requested_selected_nodes": graph.completion.requested_nodes,
            "receipt_batches": receipt_batches,
            "receipt_checked_count": len(receipt_checked_ids),
            "receipt_eligible_count": len(receipt_eligible_ids),
            "receipt_downranked_by_fit": len(set(by_topic) - receipt_eligible_ids),
            "publication_evidence_fit": fit_method,
            "receipt_scan_exhausted": len(receipt_checked_ids) >= len(ranked_ids),
            "receipt_fetch_error": receipt_fetch_error,
            "receipt_evidence_query_ms": round(receipt_evidence_query_ms, 2),
            "truncated": False,
        },
    }
