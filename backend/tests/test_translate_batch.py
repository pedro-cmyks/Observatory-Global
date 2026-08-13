"""POST /api/v2/translate/batch — the batch lane, and why it was dead.

Found 2026-08-13 (W3 re-judge, "⇄ Translate all" no-op). The batch endpoint
existed but NOTHING used it, because it 500'd for any request with more than
one id: it acquired ONE asyncpg connection and then handed that same
connection to five concurrent `asyncio.gather` tasks. asyncpg connections are
not safe for concurrent use — the second overlapping query raises
`another operation is in progress`. Measured against prod before the fix:
1 signal_id → 200, 5 signal_ids → 500.

That is the deep cause of the whole defect: with no working batch lane the
frontend fanned out one HTTP request PER RECEIPT (~26 per Brief load) against
a 20-per-5-minutes rate-limit bucket, so the translate lane 429'd wholesale.

The rewrite is set-based instead of concurrent-per-row:
  1. ONE cache SELECT for every id,
  2. ONE metadata SELECT for the misses,
  3. provider calls concurrently (no DB touched),
  4. ONE write pass.
So the connection is only ever used sequentially, and a 32-id batch costs 2
queries instead of 64.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app import db as db_mod
from app.main_v2 import app
from app.routers import translate as translate_mod

client = TestClient(app, raise_server_exceptions=False)

URL = "/api/v2/translate/batch"


class FakeConn:
    """asyncpg-ish connection that ENFORCES the real single-operation rule.

    Any overlapping operation raises, exactly like asyncpg does — so the old
    gather-over-one-connection implementation cannot pass this suite.
    """

    def __init__(self, signals=None, cached=None):
        self.signals = signals or {}
        self.cached = cached or {}
        self.busy = False
        self.writes: list[tuple] = []
        self.fetch_calls = 0

    def _guard(self):
        if self.busy:
            raise RuntimeError("another operation is in progress")

    async def _hold(self):
        self._guard()
        self.busy = True
        try:
            await asyncio.sleep(0)  # yield: a concurrent user would collide here
        finally:
            self.busy = False

    async def fetch(self, query, *args):
        await self._hold()
        self.fetch_calls += 1
        q = " ".join(query.split()).lower()
        if "signal_translations" in q:
            ids, lang = args[0], args[1]
            return [
                {"signal_id": sid, "translated": self.cached[(sid, lang)][0],
                 "model": self.cached[(sid, lang)][1], "source_lang": self.cached[(sid, lang)][2]}
                for sid in ids if (sid, lang) in self.cached
            ]
        ids = args[0]
        return [
            {"id": sid, "headline": self.signals[sid][0], "source_lang": self.signals[sid][1]}
            for sid in ids if sid in self.signals
        ]

    async def fetchrow(self, query, *args):
        rows = await self.fetch(query, *args)
        return rows[0] if rows else None

    async def execute(self, query, *args):
        await self._hold()
        self.writes.append(args)

    async def executemany(self, query, args_list):
        await self._hold()
        self.writes.extend(args_list)


class FakePool:
    """Records acquire/release so a test can prove the connection is not held
    across the provider fan-out (a 32-id batch used to pin one of the pool's
    10 connections for ~15s of DeepSeek latency)."""

    def __init__(self, conn):
        self.conn = conn
        self.timeline: list[str] = []

    def acquire(self):
        pool = self

        class _Ctx:
            async def __aenter__(self):
                pool.timeline.append("acquire")
                return pool.conn

            async def __aexit__(self, *a):
                pool.timeline.append("release")
                return False

        return _Ctx()


@pytest.fixture
def wire(monkeypatch):
    pool_ref: dict = {}

    def _wire(signals, cached=None, translator=None, api_key="k"):
        conn = FakeConn(signals, cached)
        pool = FakePool(conn)
        pool_ref["p"] = pool
        conn.pool = pool
        monkeypatch.setattr(db_mod, "pool", pool)
        monkeypatch.setenv("DEEPSEEK_API_KEY", api_key)
        calls: list[str] = []

        async def _fake(client_, headline, target_lang, key):
            calls.append(headline)
            pool_ref["p"].timeline.append("provider")
            await asyncio.sleep(0)
            if translator is not None:
                return translator(headline)
            return f"EN::{headline}"

        monkeypatch.setattr(translate_mod, "_deepseek_translate", _fake)
        return conn, calls

    return _wire


def test_multi_id_batch_does_not_blow_up_the_connection(wire):
    """The regression: five ids used to raise 'another operation is in progress'."""
    signals = {i: (f"Titular {i}", "es") for i in range(1, 6)}
    conn, calls = wire(signals)

    r = client.post(URL, json={"signal_ids": list(signals), "to": "en"})

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["target_lang"] == "en"
    assert len(body["translations"]) == 5
    assert {t["signal_id"] for t in body["translations"]} == set(signals)
    assert all(t["translated"].startswith("EN::") for t in body["translations"])
    assert sorted(calls) == sorted(f"Titular {i}" for i in range(1, 6))


def test_batch_reads_the_cache_in_one_query_not_one_per_row(wire):
    signals = {i: (f"Titular {i}", "es") for i in range(1, 21)}
    cached = {(i, "en"): (f"cached {i}", "deepseek-chat", "es") for i in range(1, 21)}
    conn, calls = wire(signals, cached)

    r = client.post(URL, json={"signal_ids": list(signals), "to": "en"})

    assert r.status_code == 200
    assert calls == []  # every row served from signal_translations
    # ONE cache SELECT for 20 ids (a second SELECT for misses is not needed
    # when there are none) — the old code did 20 round trips minimum.
    assert conn.fetch_calls == 1
    assert all(t["cached"] for t in r.json()["translations"])


def test_batch_mixes_cache_hits_and_provider_calls(wire):
    signals = {1: ("Uno", "es"), 2: ("Dos", "es"), 3: ("Tres", "es")}
    cached = {(2, "en"): ("Two", "deepseek-chat", "es")}
    conn, calls = wire(signals, cached)

    r = client.post(URL, json={"signal_ids": [1, 2, 3], "to": "en"})

    rows = {t["signal_id"]: t for t in r.json()["translations"]}
    assert rows[2]["translated"] == "Two" and rows[2]["cached"] is True
    assert rows[1]["translated"] == "EN::Uno" and rows[1]["cached"] is False
    assert sorted(calls) == ["Tres", "Uno"]


def test_identity_short_circuit_never_calls_the_provider(wire):
    signals = {1: ("Already English", "en")}
    conn, calls = wire(signals)

    r = client.post(URL, json={"signal_ids": [1], "to": "en"})

    row = r.json()["translations"][0]
    assert row["model"] == "identity"
    assert row["translated"] == "Already English"
    assert calls == []


def test_unknown_signal_is_reported_as_not_found_not_dropped(wire):
    """The client counts a missing row as UNAVAILABLE, so every requested id
    must come back with a verdict of its own."""
    conn, calls = wire({1: ("Uno", "es")})

    r = client.post(URL, json={"signal_ids": [1, 999], "to": "en"})

    rows = {t["signal_id"]: t for t in r.json()["translations"]}
    assert set(rows) == {1, 999}
    assert rows[999]["translated"] is None
    assert rows[999]["error"] == "not_found"


def test_provider_failure_is_labelled_translate_failed(wire):
    conn, calls = wire({1: ("Uno", "es")}, translator=lambda h: None)

    r = client.post(URL, json={"signal_ids": [1], "to": "en"})

    row = r.json()["translations"][0]
    assert row["translated"] is None
    assert row["error"] == "translate_failed"


def test_missing_api_key_is_labelled_no_api_key(wire, monkeypatch):
    conn, calls = wire({1: ("Uno", "es")})
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    r = client.post(URL, json={"signal_ids": [1], "to": "en"})

    row = r.json()["translations"][0]
    assert row["translated"] is None
    assert row["error"] == "no_api_key"
    assert calls == []


def test_duplicate_ids_are_translated_once_and_answered_once(wire):
    conn, calls = wire({1: ("Uno", "es")})

    r = client.post(URL, json={"signal_ids": [1, 1, 1], "to": "en"})

    assert len(r.json()["translations"]) == 1
    assert calls == ["Uno"]


def test_html_entities_are_unescaped_before_translating(wire):
    conn, calls = wire({1: ("Ni&#241;os &amp; padres", "es")})

    r = client.post(URL, json={"signal_ids": [1], "to": "en"})

    assert calls == ["Niños & padres"]
    assert r.json()["translations"][0]["translated"] == "EN::Niños & padres"


def test_batch_size_ceiling_is_enforced_by_the_contract():
    r = client.post(URL, json={"signal_ids": list(range(1, 100)), "to": "en"})
    assert r.status_code == 422


def test_connection_is_released_before_the_provider_fan_out(wire):
    """A pool connection must not be pinned across DeepSeek latency.

    Reproduced live while verifying the W3 fix: a local API holding one
    connection per in-flight batch starved every other endpoint on a
    10-connection pool. Reads, then provider, then a single write pass.
    """
    signals = {i: (f"Titular {i}", "es") for i in range(1, 4)}
    conn, calls = wire(signals)

    r = client.post(URL, json={"signal_ids": list(signals), "to": "en"})
    assert r.status_code == 200

    tl = conn.pool.timeline
    # The invariant, stated directly: no provider call ever happens while a
    # connection is checked out.
    held = False
    for event in tl:
        if event == "acquire":
            assert not held, "connection acquired twice without release"
            held = True
        elif event == "release":
            held = False
        elif event == "provider":
            assert not held, f"provider call ran while holding a pool connection: {tl}"
    assert not held, "connection never released"

    # And the shape is the intended three phases: read, provider, write.
    assert tl[:2] == ["acquire", "release"]
    assert "provider" in tl
    assert tl[-2:] == ["acquire", "release"]


def test_all_cached_batch_never_reacquires_for_a_write(wire):
    signals = {1: ("Uno", "es")}
    cached = {(1, "en"): ("One", "deepseek-chat", "es")}
    conn, calls = wire(signals, cached)

    client.post(URL, json={"signal_ids": [1], "to": "en"})

    assert conn.pool.timeline == ["acquire", "release"]
