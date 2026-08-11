"""Country-edition WARM BUILD (council R4 N26, 2026-08-11).

The country door 503'd db_busy on cold open — measured in production the same
day: CO 110.8s -> 503, JP 21.7s -> 503, US 19.2s -> 503. The fix follows the
mig-091 universe pattern: a nightly M1 build stores the payload, the handler
reads it, and the live build stays as the fallback.

These tests pin the two things that make that honest:

  1. the ORDER OF TRUTH in the handler (fresh artifact -> live build ->
     STALE artifact rather than a 503), and
  2. that the artifact carries `slot_guard` — the N17 guard runs at build
     time, and an artifact without the block is indistinguishable from a
     guard that never ran, so the builder refuses to store one.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.services import country_edition as ce


UTC = timezone.utc


def _payload(cc="CO", *, threads=1, excluded=0, slot_guard=True):
    payload = {
        "contract": ce.CONTRACT,
        "country": cc,
        "country_name": "Colombia",
        "generated_at": datetime(2026, 8, 11, 3, 0, tzinfo=UTC).isoformat(),
        "window_hours": 24,
        "threads": [{"thread_id": f"t{i}", "label": "L"} for i in range(threads)],
        "coverage_gaps": [],
        "article_enrichment": {"contract": ce.ENRICHMENT_CONTRACT,
                               "yield": {"ok": 0, "attempted": 0, "pending": 0},
                               "pending_urls": [], "articles": {}},
    }
    if slot_guard:
        payload["slot_guard"] = {
            "contract": ce.SLOT_GUARD_CONTRACT,
            "enabled": True,
            "considered": threads + excluded,
            "excluded": excluded,
            "exclusions": [{"thread_id": "dynamic-topic-8597"}] * excluded,
        }
    return payload


# ── country selection ────────────────────────────────────────────────────────

def test_select_build_countries_takes_the_volume_head_in_order():
    vol = [("US", 17895), ("CN", 6682), ("GB", 6490), ("RU", 6037)]
    out = ce.select_build_countries(vol, [], top_n=3)
    assert [c["country_code"] for c in out] == ["US", "CN", "GB"]
    assert {c["selection_reason"] for c in out} == {"volume_rank"}


def test_select_build_countries_adds_countries_spiking_off_the_head():
    # LY: 302 today against a 64.6/day baseline — a real spike with real
    # substrate, and nowhere near the volume head. That is the N26 case: the
    # country in the news whose door nobody warmed.
    vol = [("US", 17895), ("CN", 6682)]
    heat = [{"country_code": "LY", "volume_now": 302, "volume_baseline_daily": 64.6}]
    out = ce.select_build_countries(vol, heat, top_n=2)
    assert [c["country_code"] for c in out] == ["US", "CN", "LY"]
    assert out[-1]["selection_reason"] == "volume_anomaly"


def test_select_build_countries_never_duplicates_a_head_country():
    vol = [("CO", 4160), ("US", 100)]
    heat = [{"country_code": "CO", "volume_now": 4160, "volume_baseline_daily": 900}]
    out = ce.select_build_countries(vol, heat, top_n=2)
    assert [c["country_code"] for c in out] == ["CO", "US"]


def test_select_build_countries_anomaly_needs_both_mass_and_ratio():
    vol = [("US", 100)]
    heat = [
        # ratio 4.0 but 8 signals all day: nothing to build an edition from.
        {"country_code": "AI", "volume_now": 8, "volume_baseline_daily": 2.0},
        # mass but flat against its own baseline: not news, just a big country.
        {"country_code": "SI", "volume_now": 288, "volume_baseline_daily": 275.0},
    ]
    out = ce.select_build_countries(vol, heat, top_n=1)
    assert [c["country_code"] for c in out] == ["US"]


def test_select_build_countries_honours_explicit_countries_first():
    vol = [("US", 100)]
    out = ce.select_build_countries(vol, [], top_n=1, explicit=["jp"])
    assert [c["country_code"] for c in out] == ["JP", "US"]
    assert out[0]["selection_reason"] == "explicit"


def test_select_build_countries_caps_the_total():
    codes = ["US", "CN", "GB", "RU", "IN", "DE", "IT", "TR", "CO", "ES"]
    vol = [(cc, 1000 - i) for i, cc in enumerate(codes)]
    assert len(ce.select_build_countries(vol, [], top_n=10, cap=4)) == 4


def test_select_build_countries_ignores_non_country_codes():
    # 'XX' is the unknown-geography bucket, not a country: it has no door.
    vol = [("XX", 9999), ("US", 10)]
    assert [c["country_code"] for c in ce.select_build_countries(vol, [], top_n=2)] == ["US"]


# ── artifact freshness / stamping ────────────────────────────────────────────

def test_stamp_artifact_marks_a_fresh_build_and_names_its_source():
    now = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
    out = ce.stamp_artifact(
        _payload(), generated_at=now - timedelta(hours=9), build_seconds=12.5,
        selection_reason="volume_rank", now=now,
    )
    art = out["artifact"]
    assert art["contract"] == ce.ARTIFACT_CONTRACT
    assert art["source"] == "precomputed_artifact"
    assert art["age_hours"] == 9.0
    assert art["stale"] is False
    assert art["build_seconds"] == 12.5
    assert art["selection_reason"] == "volume_rank"
    # the edition body is untouched — the artifact block is additive
    assert out["threads"] == _payload()["threads"]
    assert out["slot_guard"]["contract"] == ce.SLOT_GUARD_CONTRACT


def test_stamp_artifact_marks_a_missed_night_stale():
    now = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
    out = ce.stamp_artifact(
        _payload(), generated_at=now - timedelta(hours=30), build_seconds=1.0,
        selection_reason="volume_rank", now=now,
    )
    assert out["artifact"]["stale"] is True
    assert out["artifact"]["max_age_hours"] == ce.ARTIFACT_MAX_AGE_HOURS


def test_stamp_artifact_names_a_window_mismatch_instead_of_hiding_it():
    now = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
    out = ce.stamp_artifact(
        _payload(), generated_at=now, build_seconds=1.0,
        selection_reason="volume_rank", now=now,
        window_requested=6, window_served=24,
    )
    assert out["artifact"]["window_requested"] == 6
    assert out["artifact"]["window_served"] == 24


def test_stamp_artifact_carries_a_degraded_reason_when_serving_a_stale_fallback():
    now = datetime(2026, 8, 11, 12, 0, tzinfo=UTC)
    out = ce.stamp_artifact(
        _payload(), generated_at=now - timedelta(hours=40), build_seconds=1.0,
        selection_reason="volume_rank", now=now,
        degraded_reason="live_build_db_busy",
    )
    assert out["artifact"]["degraded"] is True
    assert out["artifact"]["degraded_reason"] == "live_build_db_busy"


def test_artifact_row_fields_reads_the_guard_off_the_payload():
    fields = ce.artifact_row_fields(_payload(threads=3, excluded=2))
    assert fields == {"contract": ce.CONTRACT, "thread_count": 3,
                      "slot_guard_excluded": 2}


def test_artifact_row_fields_refuses_a_payload_without_a_slot_guard_block():
    # N17's lesson: a missing check is indistinguishable from a passing one.
    with pytest.raises(ValueError, match="slot_guard"):
        ce.artifact_row_fields(_payload(slot_guard=False))


# ── handler order of truth ───────────────────────────────────────────────────

def _geo(monkeypatch):
    import app.main_v2  # noqa: F401  (load first — geo<->main_v2 import cycle)
    import app.routers.geo as geo
    monkeypatch.setattr(geo.app.state, "redis", None, raising=False)
    return geo


@pytest.mark.asyncio
async def test_handler_serves_a_fresh_artifact_without_building(monkeypatch):
    geo = _geo(monkeypatch)
    fresh = ce.stamp_artifact(
        _payload(excluded=1), generated_at=datetime.now(UTC) - timedelta(hours=2),
        build_seconds=9.0, selection_reason="volume_rank",
    )
    built = {"n": 0}

    async def fake_stored(cc, *, hours=24, now=None):
        assert cc == "CO"
        return fresh

    async def fake_live(cc, hours=24):
        built["n"] += 1
        return _payload()

    monkeypatch.setattr("app.services.country_edition.fetch_stored_country_edition", fake_stored)
    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", fake_live)

    out = await geo.get_country_edition(cc="co")
    assert built["n"] == 0                               # never touched the slow path
    assert out["artifact"]["source"] == "precomputed_artifact"
    assert out["slot_guard"]["excluded"] == 1            # the guard rode along


@pytest.mark.asyncio
async def test_handler_builds_live_when_no_artifact_exists(monkeypatch):
    geo = _geo(monkeypatch)

    async def fake_stored(cc, *, hours=24, now=None):
        return None

    async def fake_live(cc, hours=24):
        return {**_payload(), "live": True}

    monkeypatch.setattr("app.services.country_edition.fetch_stored_country_edition", fake_stored)
    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", fake_live)

    out = await geo.get_country_edition(cc="co")
    assert out["live"] is True
    assert "artifact" not in out


@pytest.mark.asyncio
async def test_handler_prefers_a_live_build_over_a_stale_artifact(monkeypatch):
    geo = _geo(monkeypatch)
    stale = ce.stamp_artifact(
        _payload(), generated_at=datetime.now(UTC) - timedelta(hours=48),
        build_seconds=9.0, selection_reason="volume_rank",
    )

    async def fake_stored(cc, *, hours=24, now=None):
        return stale

    async def fake_live(cc, hours=24):
        return {**_payload(), "live": True}

    monkeypatch.setattr("app.services.country_edition.fetch_stored_country_edition", fake_stored)
    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", fake_live)

    out = await geo.get_country_edition(cc="co")
    assert out["live"] is True


@pytest.mark.asyncio
async def test_handler_serves_the_stale_artifact_instead_of_503(monkeypatch):
    """The N26 defect itself: the live build dies under load. A day-old
    edition, LABELED day-old, beats 'database is busy'."""
    geo = _geo(monkeypatch)
    from app.services.thread_intelligence import DatabaseBusyError
    stale = ce.stamp_artifact(
        _payload(), generated_at=datetime.now(UTC) - timedelta(hours=48),
        build_seconds=9.0, selection_reason="volume_rank",
    )

    async def fake_stored(cc, *, hours=24, now=None):
        return stale

    async def fake_live(cc, hours=24):
        raise DatabaseBusyError("database command timed out")

    monkeypatch.setattr("app.services.country_edition.fetch_stored_country_edition", fake_stored)
    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", fake_live)

    out = await geo.get_country_edition(cc="co")
    assert out["artifact"]["degraded"] is True
    assert out["artifact"]["degraded_reason"] == "live_build_db_busy"
    assert out["artifact"]["stale"] is True


@pytest.mark.asyncio
async def test_handler_still_503s_when_there_is_nothing_at_all(monkeypatch):
    geo = _geo(monkeypatch)
    from app.services.thread_intelligence import DatabaseBusyError

    async def fake_stored(cc, *, hours=24, now=None):
        return None

    async def fake_live(cc, hours=24):
        raise DatabaseBusyError("database command timed out")

    monkeypatch.setattr("app.services.country_edition.fetch_stored_country_edition", fake_stored)
    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", fake_live)

    with pytest.raises(DatabaseBusyError):
        await geo.get_country_edition(cc="co")


@pytest.mark.asyncio
async def test_handler_never_lets_the_artifact_read_break_the_door(monkeypatch):
    geo = _geo(monkeypatch)

    async def fake_stored(cc, *, hours=24, now=None):
        raise RuntimeError("artifact table missing")

    async def fake_live(cc, hours=24):
        return {**_payload(), "live": True}

    monkeypatch.setattr("app.services.country_edition.fetch_stored_country_edition", fake_stored)
    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", fake_live)

    out = await geo.get_country_edition(cc="co")
    assert out["live"] is True


# ── the build does not enqueue ───────────────────────────────────────────────

class _Conn:
    async def fetchrow(self, *a, **k):
        return {"name": "Colombia"}

    async def fetch(self, *a, **k):
        return []


class _Acquire:
    async def __aenter__(self):
        return _Conn()

    async def __aexit__(self, *a):
        return False


class _Pool:
    def acquire(self):
        return _Acquire()


async def _one_thread(**kwargs):
    return [{"thread_id": "t1", "label": "L1",
             "evidence_samples": [{"url": "http://a"}]}]


@pytest.mark.asyncio
async def test_build_path_warm_reads_but_never_enqueues(monkeypatch):
    """The enqueue's known-domain gate MEASURED 2-3.5 min per door under load
    — more than the composition it decorates — and the browser enqueues
    `pending_urls` itself. The build reads the cache and stops there."""
    calls = {"enqueue": 0}

    async def fake_states(urls):
        return []

    async def fake_enqueue(urls):
        calls["enqueue"] += 1
        return []

    monkeypatch.setattr(ce.db, "pool", _Pool())
    monkeypatch.setattr(ce, "fetch_threads", _one_thread)
    monkeypatch.setattr(ce, "rank_threads", lambda t: t)
    import app.services.article_fetch as af
    monkeypatch.setattr(af, "article_states", fake_states)
    monkeypatch.setattr(af, "enqueue_fetches", fake_enqueue)

    out = await ce.fetch_country_edition("co", enqueue=False)
    assert calls["enqueue"] == 0
    # the uncached receipt is still NAMED so the client can fetch it
    assert out["article_enrichment"]["pending_urls"] == ["http://a"]

    await ce.fetch_country_edition("co")          # serving default unchanged
    assert calls["enqueue"] == 1


# ── build-path query budget ──────────────────────────────────────────────────

def test_serving_query_timeout_is_unchanged_by_default(monkeypatch):
    from app.services import thread_intelligence as ti
    monkeypatch.delenv("ATLAS_THREADS_QUERY_TIMEOUT_S", raising=False)
    assert ti.query_timeout(15) == 15
    assert ti.query_timeout(8) == 8


def test_build_can_widen_the_query_budget_but_never_narrow_it(monkeypatch):
    from app.services import thread_intelligence as ti
    monkeypatch.setenv("ATLAS_THREADS_QUERY_TIMEOUT_S", "300")
    assert ti.query_timeout(15) == 300
    assert ti.query_timeout(8) == 300
    monkeypatch.setenv("ATLAS_THREADS_QUERY_TIMEOUT_S", "3")
    assert ti.query_timeout(15) == 15          # a smaller override cannot bite
    monkeypatch.setenv("ATLAS_THREADS_QUERY_TIMEOUT_S", "junk")
    assert ti.query_timeout(15) == 15          # garbage is ignored, not fatal
