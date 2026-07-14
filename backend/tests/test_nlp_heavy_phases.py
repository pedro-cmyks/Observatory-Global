"""#184 P1.3 — the heavy NLP pass must be phase-selectable.

On the M1 the fast-lane already keeps nlp_sentiment ~100%, and framing is a
secondary field. Running the heavy pass NER-only drops 2 of 3 heavy model
loads per cycle, which is the throughput lever for actor coverage. The Fly
path (no phases arg) must stay all-three for back-compat.
"""
from __future__ import annotations

import asyncio

from unittest.mock import AsyncMock

import enrichment.nlp_pipeline as pipeline


def _patch_phases(monkeypatch, *, sent=5, ner=7, fram=3):
    fake_conn = AsyncMock()

    async def fake_connect(*_a, **_k):
        return fake_conn

    s = AsyncMock(return_value=sent)
    n = AsyncMock(return_value=ner)
    f = AsyncMock(return_value=fram)
    monkeypatch.setenv("DATABASE_URL", "postgres://fake/db")
    monkeypatch.setattr(pipeline.asyncpg, "connect", fake_connect)
    monkeypatch.setattr(pipeline, "_run_sentiment_phase", s)
    monkeypatch.setattr(pipeline, "_run_ner_phase", n)
    monkeypatch.setattr(pipeline, "_run_framing_phase", f)
    return s, n, f


def test_ner_only_pass_skips_sentiment_and_framing(monkeypatch):
    s, n, f = _patch_phases(monkeypatch)
    counts = asyncio.run(pipeline.run_nlp_enrichment(limit=10, phases=("ner",)))
    n.assert_awaited_once()
    s.assert_not_awaited()
    f.assert_not_awaited()
    assert counts == {"sentiment": 0, "ner": 7, "framing": 0}


def test_default_runs_all_three_phases_for_backcompat(monkeypatch):
    s, n, f = _patch_phases(monkeypatch)
    counts = asyncio.run(pipeline.run_nlp_enrichment(limit=10))
    s.assert_awaited_once()
    n.assert_awaited_once()
    f.assert_awaited_once()
    assert counts == {"sentiment": 5, "ner": 7, "framing": 3}
