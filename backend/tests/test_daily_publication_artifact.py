import asyncio
from pathlib import Path

import numpy as np

from app.services.investigation_graph import ReadinessItem
from app.services.daily_publication import (
    choose_current_edition_label,
    classify_evidence_fit_outliers,
    evidence_fit_metrics_from_vectors,
    measure_publication_evidence_fit,
    verified_subjects_from_receipts,
)
from scripts.build_daily_publication import _edition_status


class Package:
    def __init__(self, status: str = "ready"):
        self.readiness = {
            key: ReadinessItem(status=status)
            for key in ("who", "what", "when", "where", "how")
        }


def test_edition_status_requires_fresh_complete_receipted_readiness():
    ready = {
        "package": Package(),
        "completion": {
            "cursor_exhausted": True,
            "data_lag_hours": 2,
            "receipt_fetch_error": None,
        },
    }
    assert _edition_status(ready) == "ready"

    ready["completion"]["data_lag_hours"] = 8
    assert _edition_status(ready) == "degraded"
    ready["completion"]["data_lag_hours"] = 2
    ready["package"].readiness["who"] = ReadinessItem(status="missing")
    assert _edition_status(ready) == "degraded"


def test_daily_artifact_migration_is_compact_json_not_per_story_vectors():
    sql = (Path(__file__).parents[1] / "migrations/075_atlas_daily_editions.sql").read_text()
    assert "atlas_daily_editions" in sql
    assert "package jsonb" in sql
    assert "graph jsonb" in sql
    assert "vector" not in sql.lower()


def test_scoped_snapshot_precomputes_daily_artifact_after_event_bindings():
    root = Path(__file__).parents[2]
    source = (root / "scripts/run-scoped-snapshot.sh").read_text()

    disaster_at = source.index("scripts.bind_disaster_movement --write")
    daily_at = source.index("scripts.build_daily_publication --execute")
    assert daily_at > disaster_at
    assert "ERROR daily publication artifact failed" in source


def test_scoped_snapshot_refreshes_typed_members_before_sealing_daily_artifact():
    root = Path(__file__).parents[2]
    source = (root / "scripts/run-scoped-snapshot.sh").read_text()

    projection_at = source.index("scripts.project_dynamic_topics")
    members_at = source.index("scripts.etl_topic_members")
    movement_at = source.index("scripts.compute_topic_movement")
    daily_at = source.index("scripts.build_daily_publication --execute")

    assert projection_at < members_at < movement_at < daily_at
    assert "ERROR topic_members ETL failed" in source


def test_batch_builder_does_not_depend_on_http_framework():
    root = Path(__file__).parents[1]
    source = (root / "scripts/build_daily_publication.py").read_text()
    service = (root / "app/services/daily_publication.py").read_text()

    assert "app.services.daily_publication" in source
    assert "app.routers" not in source
    assert "from fastapi" not in source
    assert "import fastapi" not in source
    assert "app.routers" not in service
    assert "from fastapi" not in service
    assert "import fastapi" not in service


def test_offline_receipt_coverage_reconciles_all_candidate_batches():
    root = Path(__file__).parents[1]
    service = (root / "app/services/daily_publication.py").read_text()

    assert "apply_sample_coverage" in service
    assert "if len(selection.selected_ids) >= 12" not in service
    assert '"receipt_scan_exhausted"' in service


def test_daily_verified_subjects_require_two_receipts_and_two_sources():
    receipts = [
        {"id": 1, "source_name": "Reuters", "persons": ["Donald Trump", "Iran"]},
        {"id": 2, "source_name": "Reuters", "persons": ["Donald Trump", "Ali Khamenei"]},
        {"id": 3, "source_name": "AP", "persons": ["donald trump", "Ali Khamenei"]},
        {"id": 4, "source_name": "AP", "persons": ["Single Mention"]},
    ]

    verified = verified_subjects_from_receipts(receipts)

    assert verified == ["donald trump", "ali khamenei"]
    assert "iran" not in verified
    assert "single mention" not in verified


def test_daily_verified_subjects_do_not_treat_syndication_as_corroboration():
    receipts = [
        {"id": 1, "source_name": "Reuters", "persons": ["Donald Trump"]},
        {"id": 2, "source_name": "Reuters", "persons": ["Donald Trump"]},
    ]

    assert verified_subjects_from_receipts(receipts) == []


def test_daily_edition_label_uses_current_cluster_not_stale_thread_identity():
    rows = [
        {
            "id": 1,
            "source_name": "Outlet A",
            "edition_cluster_id": 7001,
            "edition_cluster_label": "Mass Food Poisoning in Turkey",
            "edition_cluster_n_signals": 11,
        },
        {
            "id": 2,
            "source_name": "Outlet B",
            "edition_cluster_id": 7001,
            "edition_cluster_label": "Mass Food Poisoning in Turkey",
            "edition_cluster_n_signals": 11,
        },
    ]

    label, receipt = choose_current_edition_label(
        "Drunk Driver Hits Family in Kaliningrad", rows,
    )

    assert label == "Mass Food Poisoning in Turkey"
    assert receipt == {
        "method": "current_snapshot_cluster_receipt_support",
        "identity_label": "Drunk Driver Hits Family in Kaliningrad",
        "edition_label": "Mass Food Poisoning in Turkey",
        "cluster_id": 7001,
        "receipt_support": 2,
        "source_support": 2,
        "cluster_signal_count": 11,
    }


def test_daily_edition_label_falls_back_honestly_without_current_cluster():
    label, receipt = choose_current_edition_label("Stable Identity", [])

    assert label == "Stable Identity"
    assert receipt["method"] == "identity_label_fallback_no_current_cluster"
    assert receipt["edition_label"] == "Stable Identity"


def test_publication_fit_gate_rejects_only_bivariate_complete_universe_outliers():
    metrics = {
        f"topic-{i}": {
            "pair_median": 0.40 + i * 0.005,
            "label_median": 0.35 + i * 0.004,
        }
        for i in range(40)
    }
    metrics["mixed"] = {"pair_median": 0.10, "label_median": 0.08}
    metrics["broad-but-labeled"] = {"pair_median": 0.11, "label_median": 0.70}

    accepted, ledger, method = classify_evidence_fit_outliers(metrics)

    assert "mixed" not in accepted
    assert "broad-but-labeled" in accepted
    assert ledger["mixed"]["status"] == "downranked"
    assert ledger["mixed"]["reason_codes"] == [
        "publication_evidence_fit_bivariate_low_tail"
    ]
    assert ledger["broad-but-labeled"]["status"] == "eligible"
    assert method["universe_count"] == len(metrics)
    assert method["tail_quantile"] == 0.10
    assert method["semantic_ceiling"] is False
    assert method["omission_ledger"] == "complete"


def test_publication_fit_gate_abstains_when_universe_is_too_small():
    accepted, ledger, method = classify_evidence_fit_outliers({
        "one": {"pair_median": 0.01, "label_median": 0.01},
    })

    assert accepted == {"one"}
    assert ledger["one"]["reason_codes"] == [
        "publication_evidence_fit_abstained_thin_universe"
    ]
    assert method["status"] == "abstained"


def test_publication_fit_vector_metrics_separate_label_support_and_coherence():
    metrics = evidence_fit_metrics_from_vectors(
        np.array([1.0, 0.0]),
        np.array([[1.0, 0.0], [0.8, 0.2], [0.9, 0.1]]),
    )

    assert metrics["label_median"] > 0.95
    assert metrics["pair_median"] > 0.95


def test_publication_fit_measurement_keeps_compound_story_as_explicit_abstention():
    labels = {"compound": "Regional conflict"}
    rows = {
        "compound": [
            {"headline": "One", "edition_cluster_id": 1},
            {"headline": "Two", "edition_cluster_id": 2},
        ]
    }

    accepted, ledger, method = asyncio.run(measure_publication_evidence_fit(
        labels, rows, embed_texts=lambda _texts: np.empty((0, 2)),
    ))

    assert accepted == {"compound"}
    assert ledger["compound"]["reason_codes"] == [
        "publication_evidence_fit_abstained_compound_story"
    ]
    assert method["reason"] == "no_measurable_single_cluster_stories"


def test_daily_graph_quality_carries_only_corroborated_subjects():
    root = Path(__file__).parents[1]
    service = (root / "app/services/daily_publication.py").read_text()

    assert "verified_subjects = verified_subjects_from_receipts(" in service
    assert '"verified_subjects": verified_subjects' in service
    assert '"subject_status": "verified" if verified_subjects' in service


def test_daily_receipts_come_from_current_typed_evidence_not_cluster_samples():
    root = Path(__file__).parents[1]
    service = (root / "app/services/daily_publication.py").read_text()

    assert "_DAILY_EVIDENCE_SQL" in service
    assert "tm.role = 'evidence'" in service
    assert "tm.engine_version = 'v1-compat'" in service
    assert "s.timestamp >= $3::timestamptz - ($2::int * INTERVAL '1 hour')" in service
    assert "s.timestamp <= $3::timestamptz" in service
    assert "ec.sample_signal_ids" not in service
    assert "edition_cluster_label" in service
    assert "choose_current_edition_label" in service
