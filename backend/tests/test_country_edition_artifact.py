"""Country-edition WARM BUILD (council R4 N26, 2026-08-11).

The country door 503'd db_busy on cold open — measured in production the same
day: CO 110.8s -> 503, JP 21.7s -> 503, US 19.2s -> 503. The fix follows the
mig-091 universe pattern: a nightly M1 build stores the payload, the handler
reads it, and the live build stays as the fallback.

These tests pin the two things that make that honest:

  1. the ORDER OF TRUTH in the handler — fresh artifact -> STALE artifact
     served IMMEDIATELY (labeled, rebuilt behind the reader) -> live build
     only when there is no artifact at all (V6, 2026-08-12: the old middle
     step made the reader wait on the live build exactly when the DB was
     loaded, with a servable artifact sitting right there), and
  2. that the artifact carries `slot_guard` — the N17 guard runs at build
     time, and an artifact without the block is indistinguishable from a
     guard that never ran, so the builder refuses to store one.
"""
import asyncio
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
async def test_handler_serves_a_stale_artifact_without_waiting_on_the_live_build(
    monkeypatch,
):
    """V6 (cold-user probe, 2026-08-12). The stale door used to fall THROUGH to
    the live build, so a loaded DB hung the reader for 20-110s with a servable
    edition sitting right there. The stale artifact now answers immediately —
    labeled — and the rebuild runs behind the reader."""
    geo = _geo(monkeypatch)
    stale = ce.stamp_artifact(
        _payload(excluded=1), generated_at=datetime.now(UTC) - timedelta(hours=48),
        build_seconds=9.0, selection_reason="volume_rank",
    )
    entered = asyncio.Event()
    release = asyncio.Event()

    async def fake_stored(cc, *, hours=24, now=None):
        return stale

    async def hanging_live(cc, hours=24, enqueue=True):
        entered.set()
        await release.wait()          # in front of the reader this is the hang
        return {**_payload(), "live": True}

    stored_rows: list = []

    async def fake_store(payload, **kwargs):
        stored_rows.append(kwargs)

    monkeypatch.setattr("app.services.country_edition.fetch_stored_country_edition", fake_stored)
    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", hanging_live)
    monkeypatch.setattr("app.services.country_edition.store_country_edition_artifact", fake_store)

    out = await asyncio.wait_for(geo.get_country_edition(cc="co", hours=24), timeout=2)

    assert out["artifact"]["stale"] is True
    assert out["artifact"]["degraded"] is True
    assert out["artifact"]["degraded_reason"] == "stale_artifact_background_refresh"
    assert out["artifact"]["refresh_scheduled"] is True
    assert out["slot_guard"]["excluded"] == 1          # the guard still rides

    # the rebuild IS running — behind the response, not in front of it
    await asyncio.wait_for(entered.wait(), timeout=2)
    release.set()
    await asyncio.wait_for(ce.wait_for_country_edition_refresh("CO", hours=24), timeout=2)
    assert [k["country_code"] for k in stored_rows] == ["CO"]


@pytest.mark.asyncio
async def test_handler_serves_the_stale_artifact_instead_of_503(monkeypatch):
    """The N26 defect itself: the live build cannot answer under load. A
    day-old edition, LABELED day-old, beats 'database is busy' — and under the
    V6 order the reader never pays the failing build's latency to find out."""
    geo = _geo(monkeypatch)
    from app.services.thread_intelligence import DatabaseBusyError
    stale = ce.stamp_artifact(
        _payload(), generated_at=datetime.now(UTC) - timedelta(hours=48),
        build_seconds=9.0, selection_reason="volume_rank",
    )
    built = {"n": 0}

    async def fake_stored(cc, *, hours=24, now=None):
        return stale

    async def fake_live(cc, hours=24, enqueue=True):
        built["n"] += 1
        raise DatabaseBusyError("database command timed out")

    monkeypatch.setattr("app.services.country_edition.fetch_stored_country_edition", fake_stored)
    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", fake_live)

    out = await asyncio.wait_for(geo.get_country_edition(cc="co", hours=24), timeout=2)
    assert out["artifact"]["degraded"] is True
    assert out["artifact"]["stale"] is True
    # the reader was served off the artifact; the failing build is the
    # background task's problem, and it dies quietly there
    await asyncio.wait_for(ce.wait_for_country_edition_refresh("CO", hours=24), timeout=2)
    assert built["n"] == 1


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


# ── background refresh (V6) ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_background_refresh_is_single_flight_per_country(monkeypatch):
    """A saturated DB is exactly when readers pile onto the same door. N
    readers must not become N live builds — one refresh per (country, window),
    and a different country is a different lane."""
    release = asyncio.Event()
    runs: list = []

    async def slow_live(cc, hours=24, enqueue=True):
        runs.append(cc)
        await release.wait()
        return _payload(cc)

    async def fake_store(payload, **kwargs):
        return None

    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", slow_live)
    monkeypatch.setattr("app.services.country_edition.store_country_edition_artifact", fake_store)

    assert ce.schedule_country_edition_refresh("co") is True
    assert ce.schedule_country_edition_refresh("CO") is False   # already in flight
    assert ce.schedule_country_edition_refresh("co", hours=6) is True   # other window
    assert ce.schedule_country_edition_refresh("ng") is True    # other country

    release.set()
    for cc, hours in (("CO", 24), ("CO", 6), ("NG", 24)):
        await asyncio.wait_for(ce.wait_for_country_edition_refresh(cc, hours=hours), timeout=2)
    assert sorted(runs) == ["CO", "CO", "NG"]
    # the lane reopens once the task is done
    assert ce.schedule_country_edition_refresh("co") is True
    await asyncio.wait_for(ce.wait_for_country_edition_refresh("CO"), timeout=2)


@pytest.mark.asyncio
async def test_background_refresh_failure_is_logged_not_raised(monkeypatch):
    """The refresh is detached from the request. A failing build there must be
    a logged non-event — never an unhandled task exception, never a door."""
    from app.services.thread_intelligence import DatabaseBusyError

    async def failing_live(cc, hours=24, enqueue=True):
        raise DatabaseBusyError("database command timed out")

    stored = {"n": 0}

    async def fake_store(payload, **kwargs):
        stored["n"] += 1

    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", failing_live)
    monkeypatch.setattr("app.services.country_edition.store_country_edition_artifact", fake_store)

    assert ce.schedule_country_edition_refresh("co") is True
    await asyncio.wait_for(ce.wait_for_country_edition_refresh("CO"), timeout=2)
    assert stored["n"] == 0                       # nothing half-built was stored
    assert ce.schedule_country_edition_refresh("co") is True   # lane reopened
    await asyncio.wait_for(ce.wait_for_country_edition_refresh("CO"), timeout=2)


@pytest.mark.asyncio
async def test_background_refresh_never_enqueues(monkeypatch):
    """Same reason the nightly build stopped: the enqueue's known-domain gate
    MEASURED 2-3.5 min per door under load, and load is when this fires."""
    seen: list = []

    async def fake_live(cc, hours=24, enqueue=True):
        seen.append(enqueue)
        return _payload(cc)

    async def fake_store(payload, **kwargs):
        return None

    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", fake_live)
    monkeypatch.setattr("app.services.country_edition.store_country_edition_artifact", fake_store)

    ce.schedule_country_edition_refresh("co")
    await asyncio.wait_for(ce.wait_for_country_edition_refresh("CO"), timeout=2)
    assert seen == [False]


@pytest.mark.asyncio
async def test_schedule_refresh_never_raises_at_the_reader(monkeypatch):
    """The scheduler is called with the reader's response already composed. A
    bad argument there must be a False, never an exception that takes down the
    one path whose entire job is to not fail."""
    async def fake_live(cc, hours=24, enqueue=True):
        return _payload(cc)

    monkeypatch.setattr("app.services.country_edition.fetch_country_edition", fake_live)
    assert ce.schedule_country_edition_refresh("co", hours=object()) is False  # type: ignore[arg-type]


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
