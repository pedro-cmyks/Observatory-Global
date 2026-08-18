"""The sealed edition freezes the Label Court verdict per story.

Panel ciego 2026-08-18 (docs/research/ux-council/2026-08-18-panel-ciego-daily-
reader.md): the "Ceuta Migrant Crisis" card carried no LABEL UNDER REVIEW chip
even though the court had failed that very label — ``daily_publication.py``'s
frozen ``live`` dict carried ZERO court fields, so a sealed card was
structurally chip-blind. The frontend join (``lib/cardWarnings.ts``
``sealedCourtTrust``, f4d22427) already consumes these fields the moment the
sealed payload carries them; rows that carry their own trust columns are used
directly (BriefNewspaper's ``trustRowFor``).

Contract frozen here:

  * sealed story nodes carry ``label_status`` / ``label_proposed`` /
    ``court_withheld`` / ``avg_confidence`` / ``confidence_measured`` under
    ``snapshot.live`` — the SAME names the live top_threads serializer serves
    (``thread_intelligence.assemble_dynamic_thread``), taken from the topic's
    state AT the seal;
  * a verdict is about ONE sentence. When the edition relabels a story
    (``choose_current_edition_label`` picks a different current-cluster label),
    the identity label's verdict is NOT transferred onto the fresh sentence —
    the frozen court fields are honest NULLs, mirroring the frontend's strict
    identity join (same thread AND same normalized label);
  * a topic the court never judged seals NULL, never an invented default;
  * the court-state fetch is best-effort: its failure degrades to NULL court
    fields, never a voided night (the 2026-07-27 seal-death class);
  * editions sealed BEFORE the fields existed keep serving unchanged — the
    stored path is a passthrough and the frontend treats absence as "no chip".
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone

from app import db
from app.services import daily_publication as dp


_NOW = datetime(2026, 8, 18, 6, 0, tzinfo=timezone.utc)
_CHECKED = _NOW - timedelta(hours=4)


# ---------------------------------------------------------------------------
# frozen_court_fields — the pure freeze rule
# ---------------------------------------------------------------------------

def test_failed_verdict_freezes_with_live_serializer_names():
    fields = dp.frozen_court_fields(
        identity_label="Ceuta Migrant Crisis",
        edition_label="Ceuta Migrant Crisis",
        court_state={
            "label_status": "failed",
            "label_proposed": "Migrant arrivals in Ceuta",
            "label_court_model": "deepseek-chat",
            "label_checked_at": _CHECKED,
        },
        noise_rate=0.2,
    )
    assert fields == {
        "label_status": "failed",
        "label_proposed": "Migrant arrivals in Ceuta",
        "court_withheld": False,
        "avg_confidence": 0.8,
        "confidence_measured": True,
        "confidence_source": "noise_rate",
    }


def test_unjudged_topic_seals_honest_null_not_a_default():
    fields = dp.frozen_court_fields(
        identity_label="Unjudged Story",
        edition_label="Unjudged Story",
        court_state={
            "label_status": None,
            "label_proposed": None,
            "label_court_model": None,
            "label_checked_at": None,
        },
        noise_rate=None,
    )
    assert fields["label_status"] is None
    assert fields["label_proposed"] is None
    assert fields["court_withheld"] is False
    assert fields["avg_confidence"] is None
    assert fields["confidence_measured"] is False
    assert fields["confidence_source"] is None


def test_missing_court_row_seals_null_court_but_keeps_thread_confidence():
    # Court-state fetch failed, or the topic vanished between the candidate scan
    # and the court query: court fields are honest NULLs, while confidence — a
    # THREAD property derived from noise_rate, not a court output — still freezes.
    fields = dp.frozen_court_fields(
        identity_label="X", edition_label="X", court_state=None, noise_rate=0.5,
    )
    assert fields["label_status"] is None
    assert fields["label_proposed"] is None
    assert fields["court_withheld"] is False
    assert fields["avg_confidence"] == 0.5
    assert fields["confidence_measured"] is True


def test_withheld_umbrella_matches_the_live_predicate():
    # label_status NULL + label_court_model '…#withheld' + label_checked_at set
    # is the court's "attempted, ungrounded" marker — the sealed lane must agree
    # with thread_intelligence._is_court_withheld, not grow its own predicate.
    fields = dp.frozen_court_fields(
        identity_label="Umbrella Story",
        edition_label="Umbrella Story",
        court_state={
            "label_status": None,
            "label_proposed": None,
            "label_court_model": "deepseek-chat#withheld",
            "label_checked_at": _CHECKED,
        },
        noise_rate=0.1,
    )
    assert fields["court_withheld"] is True
    assert fields["label_status"] is None


def test_edition_relabel_never_transfers_the_verdict():
    # The court judged "Old Identity Label"; the edition serves "Fresh Event
    # Label". Freezing the identity verdict onto the fresh sentence would be a
    # verdict transfer between different claims — exactly what the frontend's
    # strict identity join refuses. NULL is the honest freeze.
    fields = dp.frozen_court_fields(
        identity_label="Old Identity Label",
        edition_label="Fresh Event Label",
        court_state={
            "label_status": "entailed",
            "label_proposed": None,
            "label_court_model": "deepseek-chat",
            "label_checked_at": _CHECKED,
        },
        noise_rate=0.2,
    )
    assert fields["label_status"] is None
    assert fields["label_proposed"] is None
    assert fields["court_withheld"] is False
    # Thread-level confidence is not a sentence claim: it still freezes.
    assert fields["avg_confidence"] == 0.8
    assert fields["confidence_measured"] is True


def test_label_match_mirrors_the_frontend_normalizer():
    # cardWarnings.normalizeWarningLabel: collapse whitespace, trim, lowercase.
    # The freeze must not null out a verdict over cosmetic label differences.
    fields = dp.frozen_court_fields(
        identity_label="  Ceuta   Migrant Crisis ",
        edition_label="ceuta migrant crisis",
        court_state={
            "label_status": "failed",
            "label_proposed": None,
            "label_court_model": "deepseek-chat",
            "label_checked_at": _CHECKED,
        },
        noise_rate=None,
    )
    assert fields["label_status"] == "failed"


def test_avg_confidence_clamps_and_rounds_like_the_live_serializer():
    # thread_intelligence: avg_conf = 1 - noise_rate, clamped [0,1], round(_, 3).
    high = dp.frozen_court_fields(
        identity_label="A", edition_label="A", court_state=None, noise_rate=-0.25,
    )
    assert high["avg_confidence"] == 1.0
    mid = dp.frozen_court_fields(
        identity_label="A", edition_label="A", court_state=None, noise_rate=0.6667,
    )
    assert mid["avg_confidence"] == 0.333


def test_court_state_sql_reads_the_court_columns_from_dynamic_topics():
    sql = dp._COURT_STATE_SQL
    assert "dynamic_topics" in sql
    for column in (
        "label_status",
        "label_proposed",
        "label_court_model",
        "label_checked_at",
    ):
        assert column in sql, f"court freeze query must select {column}"


# ---------------------------------------------------------------------------
# Contract: the sealed payload carries the frozen fields per story node
# ---------------------------------------------------------------------------

def _candidate_row(topic_id: int, label: str, noise_rate: float | None = 0.2) -> dict:
    return {
        "id": topic_id,
        "thread_id": f"dynamic-topic-{topic_id}",
        "label": label,
        "category": "migration-border",
        "crisis_relevant": True,
        "is_roundup": False,
        "is_junk": False,
        "coherence": 0.9,
        "noise_rate": noise_rate,
        "first_seen": _NOW - timedelta(days=2),
        "last_seen": _NOW - timedelta(hours=1),
        "current_signals": 40,
        "prior_signals": 0,
        "source_breadth": 0,
        "source_origins": 0,
        "fallback_changed_10h": None,
        "kalman_velocity": 0.1,
        "kalman_surprise": 0.0,
        "kalman_uncertainty": 0.2,
        "kalman_observations": 5,
    }


def _receipt_row(topic_id: int, receipt_id: int, cluster_label: str) -> dict:
    return {
        "topic_id": f"dynamic-topic-{topic_id}",
        "id": receipt_id,
        "headline": f"Receipt {receipt_id} names the concrete event",
        "source_name": f"outlet{receipt_id}.example",
        "source_url": f"https://outlet{receipt_id}.example/a/{receipt_id}",
        "source_lang": "es",
        "source_origin_country": "ES",
        "country_code": "ES",
        "timestamp": _NOW - timedelta(hours=2),
        "persons": None,
        "is_state_media": False,
        "source_family": "press",
        "edition_cluster_id": topic_id * 10,
        "edition_cluster_label": cluster_label,
        "edition_cluster_n_signals": 30,
    }


_CANDIDATES = [
    _candidate_row(1, "Ceuta Migrant Crisis", noise_rate=0.2),
    _candidate_row(2, "Old Identity Label", noise_rate=0.2),
    _candidate_row(3, "Unjudged Story", noise_rate=None),
]

_RECEIPTS = [
    # Story 1: current cluster carries the SAME sentence the court judged.
    _receipt_row(1, 101, "Ceuta Migrant Crisis"),
    _receipt_row(1, 102, "Ceuta Migrant Crisis"),
    # Story 2: the edition relabels to the current cluster's fresh sentence.
    _receipt_row(2, 201, "Fresh Event Label"),
    _receipt_row(2, 202, "Fresh Event Label"),
    # Story 3: never judged.
    _receipt_row(3, 301, "Unjudged Story"),
    _receipt_row(3, 302, "Unjudged Story"),
]

_COURT_ROWS = [
    {
        "id": 1,
        "label_status": "failed",
        "label_proposed": "Migrant arrivals in Ceuta",
        "label_court_model": "deepseek-chat",
        "label_checked_at": _CHECKED,
    },
    {
        "id": 2,
        "label_status": "entailed",
        "label_proposed": None,
        "label_court_model": "deepseek-chat",
        "label_checked_at": _CHECKED,
    },
    {
        "id": 3,
        "label_status": None,
        "label_proposed": None,
        "label_court_model": None,
        "label_checked_at": None,
    },
]


class _FakeConn:
    """SQL-dispatch fake (the test_dossier_walk/test_edge_diff pattern): each
    ``fetch`` call routes by a distinguishing substring of the statement."""

    def __init__(self, *, court_rows=None, court_error: Exception | None = None):
        self._court_rows = court_rows if court_rows is not None else _COURT_ROWS
        self._court_error = court_error
        self.court_queries = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def fetchval(self, sql, *args, timeout=None):
        if "MAX(last_seen)" in sql:
            return _NOW - timedelta(hours=1)
        if "MAX(timestamp)" in sql:
            return _NOW - timedelta(minutes=30)
        return None

    async def fetchrow(self, sql, *args, timeout=None):
        return None

    async def fetch(self, sql, *args, timeout=None):
        if "AS thread_id" in sql:  # _DAILY_CANDIDATE_BATCH_SQL (cursor batches)
            cursor = args[1]
            return [dict(row) for row in _CANDIDATES if row["id"] > cursor]
        if "current_evidence" in sql:  # _DAILY_EVIDENCE_SQL
            requested = set(args[0])
            return [
                dict(row) for row in _RECEIPTS
                if int(row["topic_id"].removeprefix("dynamic-topic-")) in requested
            ]
        if "label_checked_at" in sql:  # _COURT_STATE_SQL
            self.court_queries += 1
            if self._court_error is not None:
                raise self._court_error
            requested = set(args[0])
            return [dict(row) for row in self._court_rows if row["id"] in requested]
        return []


class _FakePool:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    def acquire(self):
        return self._conn


async def _fit_accepts_everything(labels_by_topic, evidence_rows_by_topic, **kwargs):
    accepted = set(evidence_rows_by_topic)
    ledger = {tid: {"status": "measured", "reason_codes": []} for tid in accepted}
    return accepted, ledger, {"status": "measured"}


async def _no_section(*args, **kwargs):
    return None


async def _no_article(request):
    return None


def _run_seal(monkeypatch, conn: _FakeConn) -> dict:
    monkeypatch.setattr(db, "pool", _FakePool(conn))
    monkeypatch.setattr(dp, "measure_publication_evidence_fit", _fit_accepts_everything)
    monkeypatch.setattr(dp, "fetch_rising", _no_section)
    monkeypatch.setattr(dp, "fetch_gap", _no_section)
    monkeypatch.setattr(dp, "synthesize_publication_article", _no_article)
    return asyncio.run(dp.fetch_daily_publication(hours=24, serving_budget=True))


def _story_live_by_id(out: dict) -> dict[str, dict]:
    return {
        node.live_ref["id"]: node.snapshot["live"]
        for node in out["graph"].nodes
        if node.node_type == "story"
    }


def test_sealed_story_node_freezes_court_fields_in_payload(monkeypatch):
    conn = _FakeConn()
    out = _run_seal(monkeypatch, conn)
    live = _story_live_by_id(out)
    assert set(live) == {"dynamic-topic-1", "dynamic-topic-2", "dynamic-topic-3"}
    assert conn.court_queries == 1

    # The acceptance case: a court-failed story seals its verdict.
    judged = live["dynamic-topic-1"]
    assert judged["label_status"] == "failed"
    assert judged["label_proposed"] == "Migrant arrivals in Ceuta"
    assert judged["court_withheld"] is False
    assert judged["avg_confidence"] == 0.8
    assert judged["confidence_measured"] is True

    # Edition relabel: the identity verdict is NOT transferred to the fresh
    # sentence — honest NULLs (the frontend's strict identity join, sealed-side).
    relabeled = live["dynamic-topic-2"]
    assert relabeled["label"] == "Fresh Event Label"
    assert relabeled["label_status"] is None
    assert relabeled["label_proposed"] is None
    assert relabeled["court_withheld"] is False
    assert relabeled["avg_confidence"] == 0.8

    # Never judged: NULL, not a default; unmeasured confidence says so.
    unjudged = live["dynamic-topic-3"]
    assert unjudged["label_status"] is None
    assert unjudged["label_proposed"] is None
    assert unjudged["court_withheld"] is False
    assert unjudged["avg_confidence"] is None
    assert unjudged["confidence_measured"] is False

    # The freeze is additive: the pre-existing frozen shape survives intact.
    assert judged["movement"]["prediction_claim"] is False
    assert judged["evidence_samples"]
    assert judged["signal_count"] == 40


def test_court_state_fetch_failure_never_aborts_the_seal(monkeypatch):
    # G-SELLO: the 2026-07-27 incident class — one enrichment failure must never
    # void the night. A dead court query seals NULL court fields, keeps the
    # thread-level confidence, and the edition still assembles.
    conn = _FakeConn(court_error=TimeoutError("court state timed out"))
    out = _run_seal(monkeypatch, conn)
    live = _story_live_by_id(out)
    assert set(live) == {"dynamic-topic-1", "dynamic-topic-2", "dynamic-topic-3"}
    judged = live["dynamic-topic-1"]
    assert judged["label_status"] is None
    assert judged["court_withheld"] is False
    assert judged["avg_confidence"] == 0.8  # noise_rate lineage, not the court's
    assert out["package"] is not None


# ---------------------------------------------------------------------------
# Compatibility: editions sealed BEFORE the fields existed keep serving
# ---------------------------------------------------------------------------

class _StoredEditionConn:
    def __init__(self, row: dict):
        self._row = row

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def fetchrow(self, sql, *args, timeout=None):
        return dict(self._row)


def test_already_sealed_editions_without_court_fields_keep_serving(monkeypatch):
    from app.routers.investigation import fetch_stored_daily_publication

    old_node = {
        "node_type": "story",
        "subtype": "thread",
        "label": "Ceuta Migrant Crisis",
        "live_ref": {"kind": "thread", "id": "dynamic-topic-1"},
        "snapshot": {
            "live": {
                "thread_id": "dynamic-topic-1",
                "label": "Ceuta Migrant Crisis",
                "signal_count": 10,
                # No court fields: sealed before this contract existed.
            },
        },
    }
    stored_row = {
        "edition_date": date(2026, 8, 10),
        "edition_start": _NOW - timedelta(days=8, hours=24),
        "edition_end": _NOW - timedelta(days=8),
        "generated_at": _NOW - timedelta(days=8),
        "contract": "atlas-daily-publication-v1",
        "status": "sealed_full",
        "package": {"title": "Atlas Daily Investigation — 2026-08-10"},
        "graph": {"nodes": [old_node], "edges": []},
        "selection": {"selected_ids": ["dynamic-topic-1"]},
        "completion": {"generated_at": (_NOW - timedelta(days=8)).isoformat()},
        "updated_at": _NOW - timedelta(days=8),
    }
    monkeypatch.setattr(db, "pool", _FakePool(_StoredEditionConn(stored_row)))

    served = asyncio.run(fetch_stored_daily_publication())

    assert served["contract"] == "atlas-daily-publication-v1"
    node = served["graph"]["nodes"][0]
    assert node["snapshot"]["live"]["thread_id"] == "dynamic-topic-1"
    # Absence stays absence — the stored path is a passthrough, never a
    # backfill; the frontend renders "no chip" for missing court fields.
    assert "label_status" not in node["snapshot"]["live"]
