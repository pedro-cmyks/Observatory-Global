from pathlib import Path

from app.services.investigation_graph import ReadinessItem
from app.services.daily_publication import verified_subjects_from_receipts
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
