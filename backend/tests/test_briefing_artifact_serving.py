"""Precompute-and-serve for /api/v2/briefing (mig 101, 2026-08-17).

The perf profile (docs/research/perf/2026-08-17-briefing-profile.md) measured
the live fill at 15-18s of serial sections, paid by a real reader on every
TTL expiry, with that reader's degraded sections frozen into the cache for
everyone after (the fill-lottery). The fix is the mig-091/098 house pattern:
builder -> JSONB artifact -> the handler reads it fresh with the live
assembly as fallback.

These tests pin the four things that keep that honest:

  1. ORDER OF TRUTH — Redis hit -> fresh artifact (<=75 min) -> live
     assembly; a fresh artifact is served as-is (served_from="artifact") and
     backfilled into Redis.
  2. STALENESS — an artifact older than the bound falls through to live,
     never serves silently stale.
  3. ?profile=1 NEVER reads the artifact: it stays the measuring instrument
     of the live path (it never even issues the artifact query).
  4. A broken artifact read is LOGGED and falls through — never a 500,
     never a silent `pass` (the L1-blackout except class).

Plus the builder's honest-retry rule: publish the run with FEWER degraded
sections; a tie goes to the second (fresher) run.
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone

import pytest

import app.main_v2  # noqa: F401 — the router imports the app; import it first
from app.routers import briefing as B

UTC = timezone.utc

ARTIFACT_PAYLOAD = {
    "period_hours": 24,
    "generated_at": "2026-08-17T10:00:00+00:00",
    "served_from": "artifact",
    "artifact_generated_at": "2026-08-17T10:00:00+00:00",
    "degraded": False,
    "degraded_segments": [],
    "stats": {"total_signals": 12345, "countries": 180, "sources": 900,
              "avg_sentiment": -0.2, "sentiment_source": "gdelt",
              "nlp_coverage": 0.5},
    "top_threads": [{"thread_id": "dynamic-topic-1", "label": "L"}],
}


class FakeConn:
    """Just enough connection for BOTH paths: the artifact read routes on the
    table name; every schema probe answers False so the live assembly runs its
    minimal shape ([] sections, honest empties) without a database."""

    def __init__(self, artifact_row=None, artifact_raises=False):
        self.artifact_row = artifact_row
        self.artifact_raises = artifact_raises
        self.queries: list[str] = []

    async def execute(self, *_a, **_k):
        return "SET"

    async def fetchval(self, query, *_a, **_k):
        self.queries.append(query)
        return False  # every to_regclass probe: table absent

    async def fetchrow(self, query, *_a, **_k):
        self.queries.append(query)
        if "briefing_artifacts" in query:
            if self.artifact_raises:
                raise RuntimeError("artifact table exploded")
            return self.artifact_row
        return None

    async def fetch(self, query, *_a, **_k):
        self.queries.append(query)
        return []


class FakePool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        conn = self.conn

        class _Ctx:
            async def __aenter__(self):
                return conn

            async def __aexit__(self, *_exc):
                return False

        return _Ctx()


class FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def get(self, key):
        return self.store.get(key)

    async def setex(self, key, _ttl, value):
        self.store[key] = value


def _fresh_row(age_minutes=1):
    gen = datetime.now(UTC) - timedelta(minutes=age_minutes)
    return {"payload": json.dumps(ARTIFACT_PAYLOAD), "generated_at": gen}


def _serve(monkeypatch, conn, *, redis=None, profile=False, hours=24):
    monkeypatch.setattr(B.db, "pool", FakePool(conn), raising=False)
    monkeypatch.setattr(B.app.state, "redis", redis, raising=False)
    return asyncio.run(B.get_briefing(hours=hours, profile=profile))


# ── (i) redis miss + fresh artifact → artifact served + redis backfilled ────

def test_fresh_artifact_is_served_on_redis_miss(monkeypatch):
    redis = FakeRedis()  # empty → miss
    conn = FakeConn(artifact_row=_fresh_row())
    result = _serve(monkeypatch, conn, redis=redis)
    assert result == ARTIFACT_PAYLOAD
    assert result["served_from"] == "artifact"
    # Backfilled so the next 900s of readers ride Redis, not the DB.
    cached = json.loads(redis.store["briefing_data:24"])
    assert cached == ARTIFACT_PAYLOAD


def test_fresh_artifact_serves_even_with_no_redis_configured(monkeypatch):
    conn = FakeConn(artifact_row=_fresh_row())
    result = _serve(monkeypatch, conn, redis=None)
    assert result["served_from"] == "artifact"


# ── (ii) stale artifact → falls through to the live assembly ────────────────

def test_stale_artifact_falls_through_to_live(monkeypatch):
    stale = _fresh_row(age_minutes=B.BRIEFING_ARTIFACT_MAX_AGE_MINUTES + 5)
    conn = FakeConn(artifact_row=stale)
    result = _serve(monkeypatch, conn)
    assert result["served_from"] == "live"
    # The live shape, not the artifact's:
    assert result["period_hours"] == 24
    assert "stats" in result and "top_threads" in result


def test_artifact_within_the_bound_is_still_fresh(monkeypatch):
    nearly = _fresh_row(age_minutes=B.BRIEFING_ARTIFACT_MAX_AGE_MINUTES - 5)
    conn = FakeConn(artifact_row=nearly)
    assert _serve(monkeypatch, conn)["served_from"] == "artifact"


# ── (iii) profile=1 ignores the artifact entirely ───────────────────────────

def test_profile_never_reads_the_artifact(monkeypatch):
    conn = FakeConn(artifact_row=_fresh_row())
    result = _serve(monkeypatch, conn, profile=True)
    assert result["served_from"] == "live"
    assert "meta_profile" in result  # the instrument still measures
    assert not any("briefing_artifacts" in q for q in conn.queries)


# ── (iv) broken artifact read → logged warning + live fallback, never 500 ───

def test_broken_artifact_read_is_logged_and_falls_through(monkeypatch, caplog):
    conn = FakeConn(artifact_raises=True)
    with caplog.at_level(logging.WARNING, logger="app.routers.briefing"):
        result = _serve(monkeypatch, conn)
    assert result["served_from"] == "live"
    assert any(
        "briefing artifact read failed" in rec.message for rec in caplog.records
    ), "a failed artifact read must be SEEN, never a silent pass"


def test_unparseable_artifact_payload_falls_through(monkeypatch, caplog):
    row = {"payload": "{not json", "generated_at": datetime.now(UTC)}
    conn = FakeConn(artifact_row=row)
    with caplog.at_level(logging.WARNING, logger="app.routers.briefing"):
        result = _serve(monkeypatch, conn)
    assert result["served_from"] == "live"
    assert any("unparseable" in rec.message for rec in caplog.records)


# ── parity: an artifact serve carries every top-level key of a live serve ───

def test_artifact_keys_are_a_superset_of_live_keys(monkeypatch):
    """The builder stores a payload produced by the SAME assembly, so the
    live keys are the contract; the artifact adds only its provenance stamp
    (artifact_generated_at) and trims the profiler's meta block."""
    live = _serve(monkeypatch, FakeConn())  # no artifact row → live path
    assert live["served_from"] == "live"
    live_keys = set(live.keys())

    from scripts.build_briefing_artifact import _build_once

    monkeypatch.setattr(B.db, "pool", FakePool(FakeConn()), raising=False)
    run = asyncio.run(_build_once(24))
    built = dict(run["payload"])
    built["served_from"] = "artifact"
    built["artifact_generated_at"] = "2026-08-17T10:00:00+00:00"
    assert live_keys <= set(built.keys()), (
        "artifact payload lost live top-level keys: "
        f"{sorted(live_keys - set(built.keys()))}"
    )
    assert "meta_profile" not in built  # trimmed before storage


# ── (v) builder retry publishes the run with fewer degraded sections ────────

def test_pick_publish_prefers_fewer_degraded_sections():
    from scripts.build_briefing_artifact import pick_publish

    first = {"payload": {"a": 1}, "build_ms": 900.0,
             "degraded_segments": ["theme_country", "top_sources"]}
    second = {"payload": {"a": 2}, "build_ms": 950.0,
              "degraded_segments": ["theme_country"]}
    assert pick_publish(first, second) is second
    assert pick_publish(second, first) is second  # order-independent


def test_pick_publish_tie_goes_to_the_second_fresher_run():
    from scripts.build_briefing_artifact import pick_publish

    first = {"payload": {}, "build_ms": 1.0, "degraded_segments": ["x"]}
    second = {"payload": {}, "build_ms": 2.0, "degraded_segments": ["y"]}
    assert pick_publish(first, second) is second


def test_pick_publish_without_a_retry_publishes_the_only_run():
    from scripts.build_briefing_artifact import pick_publish

    first = {"payload": {}, "build_ms": 1.0, "degraded_segments": []}
    assert pick_publish(first, None) is first


def test_build_once_trims_meta_profile_and_reports_cost(monkeypatch):
    from scripts.build_briefing_artifact import _build_once

    monkeypatch.setattr(B.db, "pool", FakePool(FakeConn()), raising=False)
    monkeypatch.setattr(B.app.state, "redis", None, raising=False)
    run = asyncio.run(_build_once(24))
    assert "meta_profile" not in run["payload"]
    assert isinstance(run["build_ms"], (int, float))
    assert isinstance(run["degraded_segments"], list)


def test_should_publish_the_kiosk_rule():
    """Never replace a good edition with a worse one just because it is newer —
    unless the good one has gone stale (measured motive: the 22:06 cron build
    with 4 degraded overwrote the 21:47 edition that had 2)."""
    from scripts.build_briefing_artifact import should_publish

    # empty kiosk: anything measured beats nothing
    assert should_publish(4, None, None) is True
    # worse than a FRESH stored edition -> withheld
    assert should_publish(4, 2, 30.0) is False
    # equal quality -> fresher wins
    assert should_publish(2, 2, 30.0) is True
    # better -> publish
    assert should_publish(1, 2, 30.0) is True
    # worse, but the stored edition went stale -> freshness wins over quality
    assert should_publish(4, 2, 91.0) is True
    # boundary: exactly at the window the stored edition still outranks
    assert should_publish(4, 2, 90.0) is False
