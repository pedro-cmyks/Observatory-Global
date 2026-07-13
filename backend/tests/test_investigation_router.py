from fastapi.testclient import TestClient

from app.main_v2 import app


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
