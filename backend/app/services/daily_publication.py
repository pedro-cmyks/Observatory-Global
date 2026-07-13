"""Offline construction of the sealed Atlas daily PublicationPackage.

This module is intentionally independent of FastAPI. The M1 batch runtime
builds the expensive graph/package once; the HTTP router only reads the compact
stored artifact.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import html
import os
import re
import time
import unicodedata
from typing import Any

import numpy as np

from app import db
from app.services.daily_edition import (
    apply_sample_coverage,
    fetch_daily_candidates,
    select_daily_edition,
)
from app.services.investigation_graph import (
    GraphRequest,
    PublicationPackageRequest,
    assemble_investigation_graph,
    build_publication_package,
)
from app.services.investigation_nodes import ResolveNodeInput, resolve_investigation_node
from app.services.subjects import classify_subject
from app.services.subject_geography import (
    decode_headline,
    infer_receipt_subject_geography,
)
from app.core.iso_country_names import ISO_COUNTRY_NAMES
from app.services.country_codes import fips_to_iso


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
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    client = OpenAI(api_key=api_key)
    vectors: list[list[float]] = []
    for offset in range(0, len(texts), 512):
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts[offset:offset + 512],
        )
        vectors.extend(item.embedding for item in response.data)
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
           s.country_code, s.timestamp, s.persons,
           underlying.edition_cluster_id,
           underlying.edition_cluster_label,
           underlying.edition_cluster_n_signals
    FROM current_cluster underlying
    JOIN topic_members tm
      ON tm.topic_id = ('dynamic-topic-' || underlying.topic_id::text)
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.role = 'evidence'
      AND tm.engine_version = 'v1-compat'
      AND s.timestamp >= $3::timestamptz - ($2::int * INTERVAL '1 hour')
      AND s.timestamp <= $3::timestamptz
    ORDER BY underlying.requested_id, s.id, tm.assigned_at DESC
)
SELECT ('dynamic-topic-' || requested_id::text) AS topic_id,
       id, headline, source_name, source_url, source_lang,
       source_origin_country, country_code, timestamp, persons,
       edition_cluster_id, edition_cluster_label, edition_cluster_n_signals
FROM current_evidence
ORDER BY requested_id, timestamp DESC, id DESC
"""

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
        edition_end = await conn.fetchval(
            """
            SELECT MAX(last_seen)
            FROM dynamic_topics
            WHERE state = 'active' AND parent_id IS NULL
            """,
            timeout=5,
        )
        edition_end = edition_end or generated_at
        if edition_end.tzinfo is None:
            edition_end = edition_end.replace(tzinfo=timezone.utc)
        candidates, traversal = await fetch_daily_candidates(
            conn, hours=hours, edition_end=edition_end,
        )
        preliminary = select_daily_edition(candidates, display_slots=len(candidates))
        ranked_ids = [row.thread_id for row in preliminary.ledger]
        by_topic: dict[str, list[dict[str, Any]]] = {}
        sources_by_topic: dict[str, set[str]] = {}
        origins_by_topic: dict[str, set[str]] = {}
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
                evidence_counts[topic_id] = evidence_counts.get(topic_id, 0) + 1
                source = row.get("source_name")
                if source:
                    sources_by_topic.setdefault(topic_id, set()).add(str(source))
                origin = row.get("source_origin_country")
                if origin:
                    origins_by_topic.setdefault(topic_id, set()).add(str(origin).upper())
                if row.get("persons"):
                    subject_receipts_by_topic.setdefault(topic_id, []).append(dict(row))
                label_receipts_by_topic.setdefault(topic_id, []).append(dict(row))
                if len(by_topic.setdefault(topic_id, [])) < 6:
                    by_topic[topic_id].append(dict(row))

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
    receipt_eligible_ids = set(by_topic) & fit_accepted_ids
    enriched_candidates = apply_sample_coverage(
        current_labeled_candidates,
        sources_by_topic=sources_by_topic,
        origins_by_topic=origins_by_topic,
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
    nodes = []
    window_start = edition_end - timedelta(hours=hours)
    for thread_id in selection.selected_ids:
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
                        "lead" if thread_id == selection.selected_ids[0] else "supporting"
                    ),
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
