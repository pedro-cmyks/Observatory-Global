"""POST /api/v2/translate/text — free-text translation (#204b backend).

Thread/topic LABELS have no signal_id, so the signal-bound
GET /api/v2/translate cache can't serve them. This endpoint translates a
short free text (<=600 chars — sized to clear the 420-char FROM THE SOURCE
excerpt cap) with a Redis cache keyed by
sha1(text + "|" + target_lang) and NEVER 500s: on provider failure it
degrades to the original text with `degraded: true`.

Contract: {translated: str, same: bool, cached: bool[, degraded: bool]}.

Fixture style follows the sibling router tests (module-level TestClient
over app.main_v2, monkeypatching module globals in app.routers.translate).
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main_v2 import app
from app.routers import translate as translate_mod

client = TestClient(app, raise_server_exceptions=False)

URL = "/api/v2/translate/text"


class FakeRedis:
    """Minimal async Redis stand-in recording get/setex traffic."""

    def __init__(self, store: dict[str, str] | None = None):
        self.store = store or {}
        self.get_calls: list[str] = []
        self.setex_calls: list[tuple[str, int, str]] = []

    async def get(self, key: str):
        self.get_calls.append(key)
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.setex_calls.append((key, ttl, value))
        self.store[key] = value


def _boom_deepseek(*args, **kwargs):  # pragma: no cover - guard helper
    raise AssertionError("DeepSeek must not be called on a cache hit")


def test_cache_hit_returns_cached_without_calling_deepseek(monkeypatch):
    text = "Peluncuran Program B50"
    key = translate_mod._text_cache_key(text, "en")
    fake = FakeRedis({key: json.dumps({"translated": "B50 Program Launch", "same": False})})
    monkeypatch.setattr(translate_mod, "_redis", lambda: fake)
    monkeypatch.setattr(translate_mod, "_deepseek_translate", _boom_deepseek)

    r = client.post(URL, json={"text": text, "target_lang": "en"})

    assert r.status_code == 200
    body = r.json()
    assert body["translated"] == "B50 Program Launch"
    assert body["cached"] is True
    assert body["same"] is False
    assert fake.get_calls == [key]


def test_provider_failure_degrades_to_original_text(monkeypatch):
    text = "Peluncuran Program B50"
    fake = FakeRedis()
    monkeypatch.setattr(translate_mod, "_redis", lambda: fake)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    async def _fail(client_, text_, target_lang_, api_key_):
        return None

    monkeypatch.setattr(translate_mod, "_deepseek_translate", _fail)

    r = client.post(URL, json={"text": text, "target_lang": "en"})

    assert r.status_code == 200
    body = r.json()
    assert body["translated"] == text
    assert body["same"] is True
    assert body["degraded"] is True
    # A degraded result must NOT poison the cache.
    assert fake.setex_calls == []


def test_no_api_key_degrades_to_original_text(monkeypatch):
    monkeypatch.setattr(translate_mod, "_redis", lambda: None)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    r = client.post(URL, json={"text": "Bonjour le monde", "target_lang": "en"})

    assert r.status_code == 200
    body = r.json()
    assert body["translated"] == "Bonjour le monde"
    assert body["same"] is True
    assert body["degraded"] is True


def test_same_language_passthrough_sets_same_true(monkeypatch):
    text = "NATO summit opens in Ankara"
    fake = FakeRedis()
    monkeypatch.setattr(translate_mod, "_redis", lambda: fake)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    async def _identity(client_, text_, target_lang_, api_key_):
        return text_

    monkeypatch.setattr(translate_mod, "_deepseek_translate", _identity)

    r = client.post(URL, json={"text": text, "target_lang": "en"})

    assert r.status_code == 200
    body = r.json()
    assert body["translated"] == text
    assert body["same"] is True
    assert body.get("degraded") is not True
    assert body["cached"] is False
    # Successful (even identity) results are cached with the 7-day TTL.
    assert len(fake.setex_calls) == 1
    key, ttl, value = fake.setex_calls[0]
    assert key == translate_mod._text_cache_key(text, "en")
    assert ttl == translate_mod.TEXT_CACHE_TTL_SECONDS == 7 * 24 * 3600
    assert json.loads(value) == {"translated": text, "same": True}


def test_translation_result_html_unescaped(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(translate_mod, "_redis", lambda: fake)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    captured: dict[str, str] = {}

    async def _translator(client_, text_, target_lang_, api_key_):
        captured["input"] = text_
        return "Erdo&#287;an speaks"

    monkeypatch.setattr(translate_mod, "_deepseek_translate", _translator)

    r = client.post(URL, json={"text": "Erdo&#287;an konu&#351;uyor", "target_lang": "en"})

    assert r.status_code == 200
    # Input was unescaped before hitting the provider; output unescaped too.
    assert captured["input"] == "Erdoğan konuşuyor"
    assert r.json()["translated"] == "Erdoğan speaks"
    assert r.json()["same"] is False


def test_422_on_text_over_600_chars():
    r = client.post(URL, json={"text": "x" * 601, "target_lang": "en"})
    assert r.status_code == 422


def test_accepts_full_length_excerpt(monkeypatch):
    # EXCERPT_MAX_CHARS=420 (article_fetch.py): a max-length FROM THE SOURCE
    # excerpt must clear validation — the old 300 bound 422'd every excerpt
    # over it and the client silently kept the original (untranslated quotes).
    fake = FakeRedis()
    monkeypatch.setattr(translate_mod, "_redis", lambda: fake)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    captured: dict[str, str] = {}

    async def _translator(client_, text_, target_lang_, api_key_):
        captured["input"] = text_
        return "translated excerpt"

    monkeypatch.setattr(translate_mod, "_deepseek_translate", _translator)

    r = client.post(URL, json={"text": "и" * 420, "target_lang": "en"})

    assert r.status_code == 200
    assert r.json()["translated"] == "translated excerpt"
    assert len(captured["input"]) == 420


def test_422_on_bad_target_lang():
    r = client.post(URL, json={"text": "hola", "target_lang": "english"})
    assert r.status_code == 422


def test_rate_limit_rule_covers_translate_text():
    from app.rate_limit import _build_rules

    assert any(
        p.match("/api/v2/translate/text") and bucket == "paid"
        for (p, bucket, _pred) in _build_rules()
    )
