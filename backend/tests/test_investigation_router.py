from fastapi.testclient import TestClient
from pathlib import Path
import asyncio
from datetime import date, datetime, timezone
import json

from app.main_v2 import app
from app import db
from app.routers.investigation import (
    DOSSIER_RELATION_PROVIDER_WINDOW,
    _fetch_dossier_relation_payload,
    fetch_stored_daily_publication,
)


client = TestClient(app, raise_server_exceptions=False)


def test_resolve_node_endpoint_freezes_country_snapshot():
    response = client.post("/api/v2/investigation/resolve-node", json={
        "node_type": "country",
        "subtype": "country",
        "ref_id": "IR",
        "label": "Iran",
        "observation_window": {
            "range_start": "2026-07-11T00:00:00Z",
            "range_end": "2026-07-12T00:00:00Z",
            "mode": "live",
        },
        "snapshot": {"thread_count": 13, "voice_languages": ["fa", "en"]},
    })

    assert response.status_code == 200
    body = response.json()
    assert body["contract"] == "atlas-investigation-v2"
    assert body["node"]["node_type"] == "country"
    assert body["node"]["snapshot"]["thread_count"] == 13
    assert body["node"]["resolution_status"] == "metadata_only"
    assert body["completion"] == {
        "requested": 1,
        "resolved": 0,
        "partial": 0,
        "metadata_only": 1,
        "unavailable": 0,
    }


def test_resolve_node_rejects_unknown_node_type():
    response = client.post("/api/v2/investigation/resolve-node", json={
        "node_type": "mystery",
        "subtype": "thing",
        "ref_id": "1",
        "label": "Mystery",
        "observation_window": {
            "range_start": "2026-07-11T00:00:00Z",
            "range_end": "2026-07-12T00:00:00Z",
        },
    })

    assert response.status_code == 422


def test_resolve_nodes_batches_operationally_without_semantic_top_n():
    nodes = [
        {
            "node_type": "country",
            "subtype": "country",
            "ref_id": f"X{i}",
            "label": f"Country context {i}",
            "observation_window": {
                "range_start": "2026-07-11T00:00:00Z",
                "range_end": "2026-07-12T00:00:00Z",
                "mode": "live",
            },
            "snapshot": {"ordinal": i},
        }
        for i in range(70)
    ]

    response = client.post("/api/v2/investigation/resolve-nodes", json={"nodes": nodes})

    assert response.status_code == 200
    body = response.json()
    assert len(body["nodes"]) == 70
    assert body["nodes"][-1]["snapshot"]["ordinal"] == 69
    assert body["completion"] == {
        "requested": 70,
        "processed": 70,
        "resolved": 0,
        "partial": 0,
        "metadata_only": 70,
        "unavailable": 0,
        "cursor_exhausted": True,
        "truncated": False,
    }


def test_signal_adapter_queries_only_deployed_signals_v2_columns():
    source = (
        Path(__file__).parents[1] / "app/routers/investigation.py"
    ).read_text(encoding="utf-8")

    assert "organizations" not in source
    assert "locations" not in source
    assert "persons" in source
    assert "themes" in source


def test_graph_and_publication_package_routes_are_registered():
    graph = client.post("/api/v2/investigation/graph", json={
        "nodes": [],
        "enabled_engines": ["exact"],
    })
    assert graph.status_code == 200
    assert graph.json()["contract"] == "atlas-investigation-graph-v1"

    package = client.post("/api/v2/investigation/publication-package", json={
        "title": "Empty but honest",
        "authorship": "analyst",
        "generated_at": "2026-07-12T00:00:00Z",
        "graph": graph.json(),
    })
    assert package.status_code == 200
    assert package.json()["contract"] == "atlas-publication-package-v1"
    assert package.json()["receipts"] == []


def test_daily_publication_route_reads_precomputed_artifact(monkeypatch):
    async def fake_daily():
        return {
            "contract": "atlas-daily-publication-v1",
            "package": {"contract": "atlas-publication-package-v1"},
            "selection": {"completion": {"candidate_count": 3, "truncated": False}},
            "completion": {"cursor_exhausted": True, "stored": True, "truncated": False},
        }

    monkeypatch.setattr("app.routers.investigation.fetch_stored_daily_publication", fake_daily)
    response = client.get("/api/v2/investigation/daily-publication?hours=24")

    assert response.status_code == 200
    body = response.json()
    assert body["contract"] == "atlas-daily-publication-v1"
    assert body["selection"]["completion"]["candidate_count"] == 3
    assert body["completion"]["cursor_exhausted"] is True
    assert body["completion"]["stored"] is True


def test_graph_route_reuses_existing_dossier_connection_provider(monkeypatch):
    calls = []

    async def fake_connections(req):
        calls.append(req.model_dump())
        return {
            "contract": "dossier-connections-v1",
            "nodes": [
                {"id": "dynamic-topic-1", "base_id": "dynamic-topic-1", "label": "One"},
                {"id": "dynamic-topic-2", "base_id": "dynamic-topic-2", "label": "Two"},
            ],
            "edges": [],
            "neighbors": [],
            "distributions": {"roles": {"press": 12, "public": 2}},
            "unresolved": [],
        }

    monkeypatch.setattr("app.routers.investigation.dossier_connections", fake_connections)
    window = {
        "range_start": "2026-07-11T00:00:00Z",
        "range_end": "2026-07-12T00:00:00Z",
        "mode": "live",
    }
    resolved = []
    for ref, label in (("dynamic-topic-1", "One"), ("dynamic-topic-2", "Two")):
        response = client.post("/api/v2/investigation/resolve-node", json={
            "node_type": "story", "subtype": "archive_story", "ref_id": ref,
            "label": label, "observation_window": window,
        })
        assert response.status_code == 200
        resolved.append(response.json()["node"])

    response = client.post("/api/v2/investigation/graph", json={"nodes": resolved})
    assert response.status_code == 200
    body = response.json()
    assert calls[0]["topic_ids"] == ["dynamic-topic-1", "dynamic-topic-2"]
    assert body["completion"]["engines"]["dossier_connections"] == "complete"
    assert body["relation_context"]["dossier_connections"]["distributions"]["roles"]["public"] == 2


def test_relation_provider_window_never_silently_takes_first_n():
    topic_ids = [
        f"dynamic-topic-{i}" for i in range(DOSSIER_RELATION_PROVIDER_WINDOW + 1)
    ]

    payload = asyncio.run(_fetch_dossier_relation_payload(
        topic_ids, days=30, timeout_s=1,
    ))

    assert payload["reason"] == "provider_operational_window_exceeded"
    assert payload["unresolved"] == topic_ids
    assert payload["meta"] == {
        "requested_topics": len(topic_ids),
        "provider_window": DOSSIER_RELATION_PROVIDER_WINDOW,
        "truncated": False,
        "omission_policy": "none_processed_by_this_engine",
    }


def test_stored_daily_reader_is_one_compact_row_and_parses_json(monkeypatch):
    now = datetime(2026, 7, 13, tzinfo=timezone.utc)
    row = {
        "edition_date": date(2026, 7, 12),
        "edition_start": now,
        "edition_end": now,
        "generated_at": now,
        "contract": "atlas-daily-publication-v1",
        "status": "degraded",
        "package": json.dumps({"receipts": [{"n": 1}]}),
        "graph": json.dumps({"edges": []}),
        "selection": json.dumps({"selected_ids": ["dynamic-topic-1"]}),
        "completion": json.dumps({"cursor_exhausted": True}),
        "updated_at": now,
    }

    class Conn:
        def __init__(self):
            self.queries = []

        async def fetchrow(self, query, *, timeout):
            self.queries.append((query, timeout))
            return row

    class Acquire:
        async def __aenter__(self):
            return conn

        async def __aexit__(self, *args):
            return False

    class Pool:
        def acquire(self):
            return Acquire()

    conn = Conn()
    monkeypatch.setattr(db, "pool", Pool(), raising=False)
    payload = asyncio.run(fetch_stored_daily_publication())

    assert payload["completion"]["stored"] is True
    assert payload["package"]["receipts"][0]["n"] == 1
    assert len(conn.queries) == 1
    assert "atlas_daily_editions" in conn.queries[0][0]
    assert "dynamic_topics" not in conn.queries[0][0]
