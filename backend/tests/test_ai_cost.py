"""Pure-helper tests for the AI cost ledger (app/services/ai_cost.py)."""
from __future__ import annotations

import importlib

import pytest

import app.services.ai_cost as ai_cost


def test_price_usd_deepseek():
    # 1M in @ $0.27 + 1M out @ $1.10 = $1.37
    assert ai_cost.price_usd("deepseek-chat", 1_000_000, 1_000_000) == pytest.approx(1.37)


def test_price_usd_embedding_input_only():
    # embeddings have no output price; 500k in @ $0.02/1M = $0.01
    assert ai_cost.price_usd("text-embedding-3-small", 500_000, 0) == pytest.approx(0.01)
    # output tokens on an embedding model contribute nothing
    assert ai_cost.price_usd("text-embedding-3-small", 0, 9_999) == 0.0


def test_price_usd_zero():
    assert ai_cost.price_usd("deepseek-chat", 0, 0) == 0.0


def test_resolve_price_longest_prefix():
    # dated Anthropic id resolves to the haiku family price
    p = ai_cost.resolve_price("claude-haiku-4-5-20251001")
    assert p == ai_cost.PRICES["claude-haiku-4-5"]


def test_resolve_price_unknown_is_free():
    p = ai_cost.resolve_price("some-unpriced-model-x")
    assert p == {"in": 0.0, "out": 0.0}


def test_build_event_computes_usd_and_ints():
    ev = ai_cost.build_event("brief", "deepseek", "deepseek-chat", 1000, 500, "sess-1")
    assert ev["surface"] == "brief"
    assert ev["provider"] == "deepseek"
    assert ev["input_tokens"] == 1000
    assert ev["output_tokens"] == 500
    assert ev["session_id"] == "sess-1"
    # 1000*0.27/1e6 + 500*1.10/1e6
    assert ev["usd"] == pytest.approx((1000 * 0.27 + 500 * 1.10) / 1_000_000)


def test_build_event_none_tokens_default_zero():
    ev = ai_cost.build_event("translate", "deepseek", "deepseek-chat", None, None)
    assert ev["input_tokens"] == 0
    assert ev["output_tokens"] == 0
    assert ev["usd"] == 0.0


def test_env_price_override(monkeypatch):
    monkeypatch.setenv("ATLAS_AI_PRICES", '{"deepseek-chat": {"in": 1.0, "out": 2.0}}')
    reloaded = importlib.reload(ai_cost)
    try:
        assert reloaded.price_usd("deepseek-chat", 1_000_000, 1_000_000) == pytest.approx(3.0)
        # untouched models keep defaults
        assert reloaded.PRICES["text-embedding-3-small"]["in"] == 0.02
    finally:
        monkeypatch.delenv("ATLAS_AI_PRICES", raising=False)
        importlib.reload(ai_cost)


def test_bad_env_price_falls_back(monkeypatch):
    monkeypatch.setenv("ATLAS_AI_PRICES", "not-json{{")
    reloaded = importlib.reload(ai_cost)
    try:
        assert reloaded.PRICES["deepseek-chat"]["in"] == 0.27
    finally:
        monkeypatch.delenv("ATLAS_AI_PRICES", raising=False)
        importlib.reload(ai_cost)


def test_log_ai_cost_no_loop_returns_event():
    # No running event loop → returns the event dict without raising or persisting.
    ev = ai_cost.log_ai_cost("brief", "deepseek", "deepseek-chat", 100, 50)
    assert ev["usd"] > 0
    assert ev["surface"] == "brief"
