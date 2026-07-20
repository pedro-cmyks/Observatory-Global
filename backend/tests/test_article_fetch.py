"""Workbench article enrichment F1 — gates, status machine, prompt injection.

Spec: docs/specs/2026-07-20-workbench-article-enrichment.md. These freeze the
abuse posture (SSRF + known-domain, fail-closed) and the honest status machine
(partial yield is a normal state, never dressed as success).
"""
from __future__ import annotations

import time

import pytest

from app.services import article_fetch as af
from app.services.publication_synthesis import (
    SynthEvidenceItem, SynthPin, SynthesizeRequest, _synth_user,
)

# pytest.ini wins over pyproject's asyncio_mode=auto → mark explicitly.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def known(monkeypatch):
    """Prime the in-process domain cache (no DB in unit tests)."""
    af._known_domains_cache.update(
        at=time.monotonic(), domains=frozenset({"example.com", "eltiempo.com"}))
    yield
    af._known_domains_cache.update(at=0.0, domains=None)


# ── gate_url ─────────────────────────────────────────────────────────────────

async def test_gate_rejects_non_http_schemes(known):
    for url in ("ftp://example.com/x", "file:///etc/passwd", "gopher://example.com"):
        allowed, reason = await af.gate_url(url)
        assert not allowed and reason == "scheme"


async def test_gate_rejects_unknown_domain(known):
    allowed, reason = await af.gate_url("https://evil.internal/x")
    assert not allowed and reason == "domain_not_known"


async def test_gate_fails_closed_without_domain_set(monkeypatch):
    af._known_domains_cache.update(at=0.0, domains=None)
    monkeypatch.setattr(af, "_pool", lambda: None)
    allowed, reason = await af.gate_url("https://example.com/story")
    assert not allowed and reason == "domain_set_unavailable"


async def test_gate_rejects_private_host(known, monkeypatch):
    async def fake_public(host):
        return False
    monkeypatch.setattr(af, "_host_public", fake_public)
    allowed, reason = await af.gate_url("https://example.com/story")
    assert not allowed and reason == "host_not_public"


async def test_gate_accepts_known_public(known, monkeypatch):
    async def fake_public(host):
        return True
    monkeypatch.setattr(af, "_host_public", fake_public)
    allowed, reason = await af.gate_url("https://www.example.com/story?id=1")
    assert allowed and reason == "ok"


def test_domain_known_matches_subdomains():
    domains = frozenset({"cnn.com"})
    assert af._domain_known("edition.cnn.com", domains)
    assert af._domain_known("www.cnn.com", domains)
    assert not af._domain_known("cnn.com.evil.io", domains)
    assert not af._domain_known("notcnn.com", domains)


# ── SSRF address check ───────────────────────────────────────────────────────

async def test_host_public_rejects_private_and_loopback(monkeypatch):
    async def fake_getaddrinfo(host, port):
        ip = {"lo": "127.0.0.1", "lan": "10.1.2.3", "link": "169.254.1.1",
              "pub": "93.184.216.34"}[host]
        return [(2, 1, 6, "", (ip, 0))]
    import asyncio
    monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", fake_getaddrinfo, raising=False)
    assert not await af._host_public("lo")
    assert not await af._host_public("lan")
    assert not await af._host_public("link")
    assert await af._host_public("pub")


# ── status machine ───────────────────────────────────────────────────────────

def _ok_doc(words=200):
    return {"title": "T", "text": " ".join(["palabra"] * words), "lang": "es"}

def test_classify_ok():
    assert af.classify_fetch(200, _ok_doc()) == ("ok", None)

def test_classify_thin_extract_is_paywall():
    status, err = af.classify_fetch(200, _ok_doc(words=30))
    assert status == "paywall" and err.startswith("thin_extract")

def test_classify_no_text_is_paywall():
    assert af.classify_fetch(200, None) == ("paywall", "no_extractable_text")

def test_classify_auth_walls_are_robots():
    assert af.classify_fetch(403, None)[0] == "robots"
    assert af.classify_fetch(401, None)[0] == "robots"

def test_classify_402_is_paywall():
    assert af.classify_fetch(402, None)[0] == "paywall"

def test_classify_dead_and_server_errors():
    assert af.classify_fetch(404, None) == ("error", "http_404")
    assert af.classify_fetch(500, None) == ("error", "http_500")

def test_classify_non_html_unsupported():
    assert af.classify_fetch(200, {"unsupported": True}) == ("unsupported", "non_html_content")


def test_excerpt_caps_at_60_words():
    text = " ".join(str(i) for i in range(200))
    ex = af._excerpt(text)
    assert ex.endswith("…") and len(ex.split()) == 60
    assert af._excerpt("corto texto") == "corto texto"


# ── synthesize prompt injection ──────────────────────────────────────────────

def _req():
    return SynthesizeRequest(pins=[SynthPin(
        label="Story A",
        evidence_items=[SynthEvidenceItem(headline="H1", source="outlet",
                                          url="https://example.com/a")],
    )])

def test_synth_user_appends_full_text_under_same_citation_number():
    user = _synth_user(_req(), {"https://example.com/a": {
        "text": "Cuerpo real del artículo con detalle.", "fetched_at": "2026-07-20T10:00:00Z"}})
    assert 'full text of [1] (fetched 2026-07-20): "Cuerpo real' in user
    # no new receipt numbers were minted
    assert "[2]" not in user

def test_synth_user_without_texts_unchanged():
    user = _synth_user(_req())
    assert "full text of" not in user and "[1] H1" in user
