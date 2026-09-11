"""The casualty guard, wired into all three translate lanes.

The unit behaviour lives in test_casualty_guard.py; this file pins the
CONTRACT: when the guard fires the reader gets the original text and an
honest `translation_unverified`, the flipped translation is never persisted
in signal_translations, never written to the Redis text cache, and — the part
that matters most for the witness, which is already sitting in prod's cache —
never served FROM cache either.

Fixture style mirrors test_translate_batch.py (module-level TestClient over
app.main_v2, FakeConn that enforces asyncpg's one-operation-at-a-time rule).
"""
from __future__ import annotations

import asyncio
import json

import pytest
from fastapi.testclient import TestClient

from app import db as db_mod
from app.main_v2 import app
from app.routers import translate as translate_mod

client = TestClient(app, raise_server_exceptions=False)

GET_URL = "/api/v2/translate"
BATCH_URL = "/api/v2/translate/batch"
TEXT_URL = "/api/v2/translate/text"

# The witness (2026-08-13 scorecard claim 2), verbatim.
WITNESS_RO = "Bilanţul cutremurului din Columbia urcă la 224 de morţi şi peste 600 de răniţi"
WITNESS_FLIPPED = "Colombia earthquake toll rises to 224 dead and over 600 dead"
WITNESS_FAITHFUL = "Colombia earthquake toll rises to 224 dead and over 600 injured"


class FakeConn:
    def __init__(self, signals=None, cached=None):
        self.signals = signals or {}
        self.cached = cached or {}
        self.busy = False
        self.writes: list[tuple] = []
        self.fetch_calls = 0

    async def _hold(self):
        if self.busy:
            raise RuntimeError("another operation is in progress")
        self.busy = True
        try:
            await asyncio.sleep(0)
        finally:
            self.busy = False

    async def fetch(self, query, *args):
        await self._hold()
        self.fetch_calls += 1
        q = " ".join(query.split()).lower()
        if "signal_translations" in q:
            ids, lang = args[0], args[1]
            return [
                {
                    "signal_id": sid,
                    "translated": self.cached[(sid, lang)][0],
                    "model": self.cached[(sid, lang)][1],
                    "source_lang": self.cached[(sid, lang)][2],
                    "headline": self.signals.get(sid, (None, None))[0],
                }
                for sid in ids
                if (sid, lang) in self.cached
            ]
        ids = args[0]
        return [
            {"id": sid, "headline": self.signals[sid][0], "source_lang": self.signals[sid][1]}
            for sid in ids
            if sid in self.signals
        ]

    async def fetchrow(self, query, *args):
        q = " ".join(query.split()).lower()
        if "signal_translations" in q and "any(" not in q:
            # single-row cache read: (signal_id, target_lang)
            sid, lang = args[0], args[1]
            await self._hold()
            self.fetch_calls += 1
            if (sid, lang) not in self.cached:
                return None
            row = self.cached[(sid, lang)]
            return {
                "translated": row[0],
                "model": row[1],
                "source_lang": row[2],
                "headline": self.signals.get(sid, (None, None))[0],
            }
        if "signals_v2" in q and "any(" not in q:
            sid = args[0]
            await self._hold()
            self.fetch_calls += 1
            if sid not in self.signals:
                return None
            return {"id": sid, "headline": self.signals[sid][0], "source_lang": self.signals[sid][1]}
        rows = await self.fetch(query, *args)
        return rows[0] if rows else None

    async def execute(self, query, *args):
        await self._hold()
        self.writes.append(args)

    async def executemany(self, query, args_list):
        await self._hold()
        self.writes.extend(args_list)


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        pool = self

        class _Ctx:
            async def __aenter__(self):
                return pool.conn

            async def __aexit__(self, *a):
                return False

        return _Ctx()


class FakeRedis:
    def __init__(self, store: dict[str, str] | None = None):
        self.store = store or {}
        self.setex_calls: list[tuple[str, int, str]] = []

    async def get(self, key: str):
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str):
        self.setex_calls.append((key, ttl, value))
        self.store[key] = value


@pytest.fixture
def wire(monkeypatch):
    def _wire(signals, cached=None, translator=None, api_key="k"):
        conn = FakeConn(signals, cached)
        monkeypatch.setattr(db_mod, "pool", FakePool(conn))
        monkeypatch.setenv("DEEPSEEK_API_KEY", api_key)
        calls: list[str] = []

        async def _fake(client_, headline, target_lang, key):
            calls.append(headline)
            await asyncio.sleep(0)
            return translator(headline) if translator else f"EN::{headline}"

        monkeypatch.setattr(translate_mod, "_deepseek_translate", _fake)
        return conn, calls

    return _wire


@pytest.fixture(autouse=True)
def _no_ledger_writes(monkeypatch, tmp_path):
    """Fires are ledgered; in tests they go to a temp file, not the repo."""
    monkeypatch.setenv("ATLAS_TRANSLATION_GUARD_LOG", str(tmp_path / "fires.jsonl"))


# --------------------------------------------------------------------------
# GET /api/v2/translate
# --------------------------------------------------------------------------

def test_get_refuses_to_serve_a_flipped_casualty_figure(wire):
    conn, calls = wire({7: (WITNESS_RO, "ro")}, translator=lambda h: WITNESS_FLIPPED)

    r = client.get(GET_URL, params={"signal_id": 7, "to": "en"})

    assert r.status_code == 200
    body = r.json()
    assert body["translated"] is None, "the flipped translation must never be served"
    assert body["error"] == "translation_unverified"
    assert body["guard"]["reason"] == "category_flip"
    assert "600" in body["guard"]["message"]
    # The reader keeps the source text.
    assert body["original"] == WITNESS_RO
    # …and nothing was written to the cache, so it cannot leak later.
    assert conn.writes == []


def test_get_serves_and_caches_a_faithful_translation(wire):
    conn, calls = wire({7: (WITNESS_RO, "ro")}, translator=lambda h: WITNESS_FAITHFUL)

    body = client.get(GET_URL, params={"signal_id": 7, "to": "en"}).json()

    assert body["translated"] == WITNESS_FAITHFUL
    assert "error" not in body and "guard" not in body
    assert len(conn.writes) == 1


def test_get_refuses_a_poisoned_row_already_in_the_cache(wire):
    """The witness is already cached in prod; guarding only fresh calls would
    keep serving it forever."""
    conn, calls = wire(
        {7: (WITNESS_RO, "ro")},
        cached={(7, "en"): (WITNESS_FLIPPED, "deepseek-chat", "ro")},
    )

    body = client.get(GET_URL, params={"signal_id": 7, "to": "en"}).json()

    assert body["translated"] is None
    assert body["error"] == "translation_unverified"
    assert calls == []  # no provider call needed to refuse


def test_get_identity_short_circuit_is_not_guarded(wire):
    # Same language in and out: there is no translation to verify.
    conn, calls = wire({7: ("224 dead and over 600 injured", "en")})

    body = client.get(GET_URL, params={"signal_id": 7, "to": "en"}).json()

    assert body["model"] == "identity"
    assert body["translated"] == "224 dead and over 600 injured"


# --------------------------------------------------------------------------
# POST /api/v2/translate/batch
# --------------------------------------------------------------------------

def test_batch_refuses_the_flipped_row_and_serves_its_neighbours(wire):
    signals = {
        1: (WITNESS_RO, "ro"),
        2: ("Trei morţi într-un accident", "ro"),
        3: ("Doi răniţi la Galaţi", "ro"),
    }

    def _translate(headline):
        if headline == WITNESS_RO:
            return WITNESS_FLIPPED
        if headline.startswith("Trei"):
            return "Three dead in a crash"
        return "Two injured in Galati"

    conn, calls = wire(signals, translator=_translate)

    r = client.post(BATCH_URL, json={"signal_ids": [1, 2, 3], "to": "en"})

    rows = {t["signal_id"]: t for t in r.json()["translations"]}
    assert rows[1]["translated"] is None
    assert rows[1]["error"] == "translation_unverified"
    assert rows[1]["guard"]["reason"] == "category_flip"
    assert rows[2]["translated"] == "Three dead in a crash"
    assert rows[3]["translated"] == "Two injured in Galati"
    # Only the two clean rows are persisted.
    assert len(conn.writes) == 2
    assert all(w[0] in (2, 3) for w in conn.writes)


def test_batch_refuses_a_poisoned_cache_hit(wire):
    conn, calls = wire(
        {1: (WITNESS_RO, "ro")},
        cached={(1, "en"): (WITNESS_FLIPPED, "deepseek-chat", "ro")},
    )

    rows = client.post(BATCH_URL, json={"signal_ids": [1], "to": "en"}).json()["translations"]

    assert rows[0]["translated"] is None
    assert rows[0]["error"] == "translation_unverified"
    assert calls == []


def test_batch_still_reads_the_cache_set_based(wire):
    """Guarding cache hits must not cost a query per row: the cache read is
    two SET-BASED selects (translations, then their headlines by PK) — never
    one per row, and never the joined form that made prod's planner walk
    signals_v2's index for 60s (2026-09-11)."""
    signals = {i: (f"Titular {i}", "es") for i in range(1, 21)}
    cached = {(i, "en"): (f"Headline {i}", "deepseek-chat", "es") for i in range(1, 21)}
    conn, calls = wire(signals, cached)

    r = client.post(BATCH_URL, json={"signal_ids": list(signals), "to": "en"})

    assert r.status_code == 200
    assert calls == []
    assert conn.fetch_calls == 2


# --------------------------------------------------------------------------
# POST /api/v2/translate/text
# --------------------------------------------------------------------------

def test_text_lane_refuses_a_flip_and_returns_the_original(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(translate_mod, "_redis", lambda: fake)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")

    async def _fake(client_, text, lang, key):
        return WITNESS_FLIPPED

    monkeypatch.setattr(translate_mod, "_deepseek_translate", _fake)

    body = client.post(TEXT_URL, json={"text": WITNESS_RO, "target_lang": "en"}).json()

    assert body["translated"] == WITNESS_RO, "the reader gets the source, not the flip"
    assert body["degraded"] is True
    assert body["error"] == "translation_unverified"
    assert body["guard"]["reason"] == "category_flip"
    assert fake.setex_calls == [], "a refused translation must not be cached for 7 days"


def test_text_lane_refuses_a_poisoned_cache_entry(monkeypatch):
    key = translate_mod._text_cache_key(WITNESS_RO, "en")
    fake = FakeRedis({key: json.dumps({"translated": WITNESS_FLIPPED, "same": False})})
    monkeypatch.setattr(translate_mod, "_redis", lambda: fake)

    def _boom(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("no provider call needed to refuse a cached flip")

    monkeypatch.setattr(translate_mod, "_deepseek_translate", _boom)

    body = client.post(TEXT_URL, json={"text": WITNESS_RO, "target_lang": "en"}).json()

    assert body["translated"] == WITNESS_RO
    assert body["error"] == "translation_unverified"


def test_text_lane_passes_a_faithful_translation_through(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(translate_mod, "_redis", lambda: fake)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "k")

    async def _fake(client_, text, lang, key):
        return WITNESS_FAITHFUL

    monkeypatch.setattr(translate_mod, "_deepseek_translate", _fake)

    body = client.post(TEXT_URL, json={"text": WITNESS_RO, "target_lang": "en"}).json()

    assert body["translated"] == WITNESS_FAITHFUL
    assert "error" not in body
    assert len(fake.setex_calls) == 1


# --------------------------------------------------------------------------
# Failure posture
# --------------------------------------------------------------------------

def test_a_broken_guard_refuses_rather_than_serving_unverified_numbers(wire, monkeypatch):
    """Fail CLOSED. If our own verifier crashes we do not know whether the
    number is real, and 'we could not verify' is the honest answer — the
    frontend already renders it. (The lane still never 500s.)"""
    conn, calls = wire({7: (WITNESS_RO, "ro")}, translator=lambda h: WITNESS_FAITHFUL)

    def _explode(*a, **k):
        raise RuntimeError("guard bug")

    monkeypatch.setattr(translate_mod.casualty_guard, "check_translation", _explode)

    body = client.get(GET_URL, params={"signal_id": 7, "to": "en"}).json()

    assert body["translated"] is None
    assert body["error"] == "translation_unverified"
    assert body["guard"]["reason"] == "guard_error"


def test_every_fire_lands_in_the_ledger(wire, tmp_path, monkeypatch):
    path = tmp_path / "nested" / "fires.jsonl"
    monkeypatch.setenv("ATLAS_TRANSLATION_GUARD_LOG", str(path))
    conn, calls = wire({7: (WITNESS_RO, "ro")}, translator=lambda h: WITNESS_FLIPPED)

    client.get(GET_URL, params={"signal_id": 7, "to": "en"})

    lines = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 1
    entry = lines[0]
    assert entry["reason"] == "category_flip"
    assert entry["signal_id"] == 7
    assert entry["lane"] == "signal"
    assert entry["original"] == WITNESS_RO
    assert entry["translated"] == WITNESS_FLIPPED
    assert entry["at"]
