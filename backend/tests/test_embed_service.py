"""Internal embed service + remote provider chain (#223, Phase 1.5b).

The api box has no torch; nlp_worker hosts the model and serves /embed over
private 6PN. The provider chain in research_semantic must fall back:
local torch → EMBED_SERVICE_URL → None (visible lane gap).
"""
from __future__ import annotations

import importlib.util
import json

import pytest

import app.main_v2  # noqa: F401 — settle import order for app.* modules
from app.services import research_semantic


def _torch_available() -> bool:
    return bool(importlib.util.find_spec("torch")
                and importlib.util.find_spec("transformers"))


def test_remote_provider_skipped_without_url(monkeypatch):
    monkeypatch.delenv("EMBED_SERVICE_URL", raising=False)
    assert research_semantic._embed_remote(["query: x"]) is None


def test_chain_returns_none_when_everything_unavailable(monkeypatch):
    monkeypatch.setenv("RESEARCH_SEMANTIC_DISABLED", "1")  # kills local
    monkeypatch.delenv("EMBED_SERVICE_URL", raising=False)  # kills remote
    assert research_semantic.embed_texts(["query: x"]) is None


def test_remote_provider_parses_service_response(monkeypatch):
    monkeypatch.setenv("EMBED_SERVICE_URL", "http://embed.internal:8090")

    class FakeResponse:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return json.dumps({"vectors": [[0.1, 0.2]], "dim": 2}).encode()

    captured = {}

    def fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data)
        return FakeResponse()

    import urllib.request
    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    vectors = research_semantic._embed_remote(["query: crisis hídrica"])
    assert vectors == [[0.1, 0.2]]
    assert captured["url"] == "http://embed.internal:8090/embed"
    assert captured["body"]["texts"] == ["query: crisis hídrica"]


def test_remote_provider_degrades_on_error(monkeypatch):
    monkeypatch.setenv("EMBED_SERVICE_URL", "http://embed.internal:8090")
    import urllib.request

    def boom(req, timeout=None):
        raise OSError("connection refused")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    assert research_semantic._embed_remote(["query: x"]) is None


def test_service_thread_skipped_when_disabled(monkeypatch):
    monkeypatch.setenv("EMBED_SERVICE_ENABLED", "false")
    from enrichment.embed_service import start_embed_service_thread
    assert start_embed_service_thread() is None


# `integration` (conftest: skipped unless --run-integration) is load-bearing:
# _build_app() loads the real e5 model, and `import transformers` alone costs
# ~142s here (packages_distributions() at import time reads every distribution's
# RECORD — 0.5s CPU, the rest blocked on I/O). The torch PRESENCE check below is
# necessary but not sufficient; once torch landed in `.venv` this test stopped
# skipping and started stalling `pytest tests/` at 21%.
@pytest.mark.integration
@pytest.mark.skipif(not _torch_available(),
                    reason="torch/transformers not in this venv")
def test_embed_endpoint_roundtrip():
    from fastapi.testclient import TestClient
    from enrichment.embed_service import _build_app

    client = TestClient(_build_app())
    health = client.get("/healthz").json()
    assert health["ok"] is True

    res = client.post("/embed", json={"texts": ["query: sequía en Irán"]})
    assert res.status_code == 200
    payload = res.json()
    assert payload["dim"] == 768
    assert len(payload["vectors"]) == 1
    # vectors are L2-normalized by the shared pooling path
    norm = sum(x * x for x in payload["vectors"][0]) ** 0.5
    assert abs(norm - 1.0) < 0.01
