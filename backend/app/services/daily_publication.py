"""Offline construction of the sealed Atlas daily PublicationPackage.

This module is intentionally independent of FastAPI. The M1 batch runtime
builds the expensive graph/package once; the HTTP router only reads the compact
stored artifact.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import time
from typing import Any

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


_DAILY_SAMPLE_IDS_SQL = """
SELECT
        ('dynamic-topic-' || dt.id::text) AS topic_id,
        sampled.signal_id
FROM dynamic_topics dt
CROSS JOIN LATERAL (
    SELECT DISTINCT sample.signal_id
    FROM dynamic_topic_members dtm
    JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
    CROSS JOIN LATERAL unnest(
        COALESCE(ec.sample_signal_ids, ARRAY[]::bigint[])
    ) AS sample(signal_id)
    WHERE dtm.dynamic_topic_id = dt.id
      AND dtm.snapshot_at = (
          SELECT MAX(latest.snapshot_at)
          FROM dynamic_topic_members latest
          WHERE latest.dynamic_topic_id = dt.id
      )
    LIMIT 32
) sampled
WHERE dt.id = ANY($1::bigint[])
ORDER BY dt.id, sampled.signal_id
"""

_DAILY_SIGNALS_SQL = """
SELECT id, headline, source_name, source_url, source_lang,
       source_origin_country, country_code, timestamp, persons
FROM signals_v2
WHERE id = ANY($1::bigint[])
  AND timestamp >= $3::timestamptz - ($2::int * INTERVAL '1 hour')
  AND timestamp <= $3::timestamptz
ORDER BY timestamp DESC, id DESC
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
        receipt_checked_ids: set[str] = set()
        receipt_batches = 0
        receipt_fetch_error: str | None = None
        receipt_sample_query_ms = 0.0
        receipt_signal_query_ms = 0.0
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
                sample_rows = await conn.fetch(
                    _DAILY_SAMPLE_IDS_SQL, numeric_ids,
                    timeout=4 if serving_budget else 30,
                )
                receipt_sample_query_ms += (time.monotonic() - sample_started) * 1000
            except TimeoutError:
                receipt_fetch_error = "receipt_sample_provider_timeout"
                break
            topics_by_signal: dict[int, list[str]] = {}
            for raw in sample_rows:
                topics_by_signal.setdefault(int(raw["signal_id"]), []).append(str(raw["topic_id"]))
            signal_started = time.monotonic()
            try:
                signal_rows = await conn.fetch(
                    _DAILY_SIGNALS_SQL,
                    list(topics_by_signal), hours, edition_end,
                    timeout=12 if serving_budget else 60,
                ) if topics_by_signal else []
                receipt_signal_query_ms += (time.monotonic() - signal_started) * 1000
            except TimeoutError:
                receipt_fetch_error = "receipt_signal_provider_timeout"
                break
            receipt_batches += 1
            receipt_checked_ids.update(chunk)
            for raw in signal_rows:
                row = dict(raw)
                for topic_id in topics_by_signal.get(int(row["id"]), []):
                    source = row.get("source_name")
                    if source:
                        sources_by_topic.setdefault(topic_id, set()).add(str(source))
                    origin = row.get("source_origin_country")
                    if origin:
                        origins_by_topic.setdefault(topic_id, set()).add(str(origin).upper())
                    if len(by_topic.setdefault(topic_id, [])) < 6:
                        by_topic[topic_id].append(dict(row))

        enriched_candidates = apply_sample_coverage(
            candidates,
            sources_by_topic=sources_by_topic,
            origins_by_topic=origins_by_topic,
        )
        selection = select_daily_edition(
            enriched_candidates,
            display_slots=12,
            receipt_eligible_ids=set(by_topic),
            receipt_checked_ids=receipt_checked_ids,
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
            str(row.get("country_code")).upper()
            for row in receipts if row.get("country_code")
        ))
        top_sources = list(dict.fromkeys(
            str(row.get("source_name")) for row in receipts if row.get("source_name")
        ))
        top_entities = list(dict.fromkeys(
            str(person)
            for row in receipts
            for person in (row.get("persons") or [])
            if person
        ))
        live = {
            "thread_id": thread_id,
            "label": candidate.label,
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
                label=candidate.label,
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
                        "method": "latest_dynamic_cluster_sample_signal_ids",
                        "available_receipts": len(receipts),
                        "display_receipt_sample": 6,
                        "semantic_ceiling": False,
                    },
                },
                quality={
                    "coherence": candidate.coherence,
                    "noise_rate": candidate.noise_rate,
                    "subject_status": "unverified" if top_entities else "not_available",
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
            "receipt_eligible_count": len(by_topic),
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
            "receipt_eligible_count": len(by_topic),
            "receipt_scan_exhausted": len(receipt_checked_ids) >= len(ranked_ids),
            "receipt_fetch_error": receipt_fetch_error,
            "receipt_sample_query_ms": round(receipt_sample_query_ms, 2),
            "receipt_signal_query_ms": round(receipt_signal_query_ms, 2),
            "truncated": False,
        },
    }
