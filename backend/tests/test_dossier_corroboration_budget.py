"""Corroborate lane under a real investigation (tren B2 V5).

The fresh Frank test measured this lane at 1 success in 4: two runs died as a
silent 502 (31.4s direct-to-Fly > the Vercel rewrite ceiling) and one came back
"lane unavailable". This suite freezes the three properties that turn that into
an honest, survivable lane:

  1. DOC 2.0 calls are SERIALIZED ≥ the documented 1-req/5s interval — across
     the whole request, not per pin. (The throttle already existed; these tests
     make its absence a failing test instead of a silent regression.)
  2. PARTIALS ALWAYS — a pin whose search lane failed reports its own status
     while every other pin still serves. Never all-or-nothing.
  3. The per-pin `search_status` the backend already measures is IN the payload,
     so the render can say "web lane throttled — N of M pins measured".

Plus the job+poll path: with serialization, total time is ~5.75s/query + ~12s
(measured: 3 pins = 46.3s, 4 pins = 57.8s against prod), which is over the
proxy ceiling by construction — so the frontend starts a job and polls.
"""
from __future__ import annotations

import asyncio
import json
import time

import pytest


# ── 1. Serialization: the documented 1-req/5s, honored across the request ────

@pytest.mark.asyncio
async def test_doc20_calls_are_serialized_by_the_documented_interval(monkeypatch):
    """Concurrent callers must not fire concurrent DOC 2.0 requests.

    Timing is stubbed: the interval is shrunk and the network replaced by a
    recorder, so the test asserts SPACING, not wall-clock patience.
    """
    from app.services import external_depth

    fired: list[float] = []

    def fake_get() -> tuple[int, bytes]:
        fired.append(time.monotonic())
        return 200, json.dumps({"articles": []}).encode()

    monkeypatch.setattr(external_depth, "_RATE_INTERVAL_S", 0.05)
    monkeypatch.setattr(external_depth, "_build_getter", lambda url: fake_get)
    monkeypatch.setattr(external_depth, "_cache", {})
    monkeypatch.setattr(external_depth, "_last_fire", 0.0)

    await asyncio.gather(*[
        external_depth.fetch_external_depth_status(
            "label", raw_query=f"query {i}", timespan="14d")
        for i in range(4)
    ])

    assert len(fired) == 4
    gaps = [b - a for a, b in zip(fired, fired[1:])]
    assert all(g >= 0.045 for g in gaps), gaps


@pytest.mark.asyncio
async def test_throttle_is_shared_with_the_claim_lane(monkeypatch):
    """corroboration.doc20_fetch_status claims to share this throttle — if the
    import ever breaks, the rate limit silently disappears. Freeze the wiring."""
    from app.services import corroboration, external_depth

    assert external_depth.throttle is not None
    calls: list[int] = []

    async def fake_throttle() -> None:
        calls.append(1)

    monkeypatch.setattr(external_depth, "throttle", fake_throttle)

    def fake_get() -> tuple[int, bytes]:
        return 200, json.dumps({"articles": []}).encode()

    monkeypatch.setattr(corroboration, "_build_doc20_getter", lambda url: fake_get)
    await corroboration.doc20_fetch_status("kyiv strike", cache=None)
    assert calls, "doc20_fetch_status must go through the shared throttle"


# ── 2. Honest status classification (throttled ≠ down ≠ measured-zero) ───────

@pytest.mark.asyncio
@pytest.mark.parametrize("resp,expected", [
    ((429, b""), "throttled"),
    ((200, b"Please limit requests to one every 5 seconds."), "throttled"),
    ((503, b""), "down"),
    ((200, json.dumps({"articles": []}).encode()), "ok"),
])
async def test_fetch_status_classifies_the_outcome(monkeypatch, resp, expected):
    from app.services import external_depth

    monkeypatch.setattr(external_depth, "_cache", {})
    monkeypatch.setattr(external_depth, "_RATE_INTERVAL_S", 0.0)
    monkeypatch.setattr(external_depth, "_build_getter", lambda url: (lambda: resp))

    out = await external_depth.fetch_external_depth_status(
        "label", raw_query="q", timespan="14d")
    assert out["status"] == expected


@pytest.mark.asyncio
async def test_network_failure_is_down_not_throttled(monkeypatch):
    from app.services import external_depth

    def boom() -> tuple[int, bytes]:
        raise TimeoutError("timed out")

    monkeypatch.setattr(external_depth, "_cache", {})
    monkeypatch.setattr(external_depth, "_RATE_INTERVAL_S", 0.0)
    monkeypatch.setattr(external_depth, "_build_getter", lambda url: boom)
    out = await external_depth.fetch_external_depth_status(
        "label", raw_query="q", timespan="14d")
    assert out["status"] == "down"
    assert out["result"] is None


@pytest.mark.asyncio
async def test_a_failed_window_is_cached_briefly_not_for_half_an_hour(monkeypatch):
    """A transient failure used to be negative-cached for 30 minutes — the
    'lane unavailable' the analyst hit on re-run. Failures cool down for
    seconds; successes still cache long."""
    from app.services import external_depth

    assert external_depth._FAIL_CACHE_TTL <= 120
    assert external_depth._CACHE_TTL >= 600

    fires: list[int] = []

    def boom() -> tuple[int, bytes]:
        fires.append(1)
        raise TimeoutError("timed out")

    cache: dict = {}
    monkeypatch.setattr(external_depth, "_cache", cache)
    monkeypatch.setattr(external_depth, "_RATE_INTERVAL_S", 0.0)
    monkeypatch.setattr(external_depth, "_build_getter", lambda url: boom)

    await external_depth.fetch_external_depth_status("l", raw_query="q", timespan="14d")
    await external_depth.fetch_external_depth_status("l", raw_query="q", timespan="14d")
    assert len(fires) == 1, "second call inside the cooldown must not re-fire"

    key = next(iter(cache))
    cache[key] = (cache[key][0] - external_depth._FAIL_CACHE_TTL - 1, cache[key][1])
    await external_depth.fetch_external_depth_status("l", raw_query="q", timespan="14d")
    assert len(fires) == 2, "after the cooldown the lane must be retried"


# ── 3. Handler: partials always, per-pin search_status, hard budget ──────────

def _pin(pid: str, label: str, evidence: list[str] | None = None) -> dict:
    return {"id": pid, "label": label, "anchor_type": "thread",
            "evidence": evidence if evidence is not None else [f"{label} receipt"]}


def _ok(title: str, domain: str) -> dict:
    return {"status": "ok", "result": {"items": [
        {"title": title, "url": f"https://{domain}/x", "domain": domain}]}}


@pytest.fixture
def no_llm(monkeypatch):
    from app.routers import dossier as dossier_module

    async def fake_generate(_system, _user, **_kwargs):
        return "Measured comparison.", "test-provider", None, None

    monkeypatch.setattr(dossier_module, "generate_insight", fake_generate)
    return dossier_module


@pytest.mark.asyncio
async def test_one_dead_pin_never_kills_the_others(no_llm, monkeypatch):
    """Frank saw all-or-nothing. A pin whose lane is down reports itself and
    the rest still serve their receipts."""
    from app.services import external_depth
    dossier_module = no_llm

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        if raw_query.startswith("dead"):
            return {"status": "down", "result": None}
        return _ok(f"Coverage of {raw_query}", f"{raw_query.split()[0]}.example")

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)

    resp = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(force=True, pins=[
            _pin("dead-pin", "dead lane story"),
            _pin("live-pin", "live lane story"),
        ]))

    by_id = {p["id"]: p for p in resp["pins"]}
    assert by_id["dead-pin"]["search_status"] == "unavailable"
    assert by_id["live-pin"]["search_status"] == "ok"
    assert by_id["live-pin"]["citations"], "the healthy pin still serves receipts"
    assert resp["partial"] is True
    assert resp["pins_measured"] == 1
    assert resp["pins_applicable"] == 2
    assert resp["pins_partial"] == 0


@pytest.mark.asyncio
async def test_throttled_lane_says_throttled_not_merely_unavailable(no_llm, monkeypatch):
    from app.services import external_depth
    dossier_module = no_llm

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        return {"status": "throttled", "result": None}

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)

    resp = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(force=True, pins=[_pin("p1", "some story")]))

    pin = resp["pins"][0]
    assert pin["search_status"] == "throttled"
    assert "throttl" in pin["note"].lower()
    assert pin["status"] == "unverified"       # never claimed as measured
    assert resp["partial"] is True
    assert "throttl" in (resp["meta"]["search_note"] or "").lower()


@pytest.mark.asyncio
async def test_partial_pin_reports_how_many_queries_answered(no_llm, monkeypatch):
    from app.services import external_depth
    dossier_module = no_llm

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        if "receipt" in raw_query:
            return {"status": "down", "result": None}
        return _ok("Independent coverage", "indep.example")

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)

    resp = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(force=True, pins=[
            {"id": "p1", "label": "half measured story", "anchor_type": "thread",
             "evidence": ["half measured story receipt headline"]},
        ]))

    pin = resp["pins"][0]
    assert pin["queries_run"] == 2
    assert pin["queries_answered"] == 1
    assert pin["search_status"] == "partial"
    assert pin["citations"], "the answered query's receipts still serve"
    # A partially-measured pin that returned real coverage IS measured — the
    # run-level count must not read 0 beside an `established` verdict.
    assert resp["pins_measured"] == 1
    assert resp["pins_partial"] == 1
    assert "partially" in (resp["meta"]["search_note"] or "")


@pytest.mark.asyncio
async def test_context_pin_is_not_applicable_never_partial(no_llm, monkeypatch):
    from app.services import external_depth
    dossier_module = no_llm

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        return _ok("Coverage", "indep.example")

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)

    resp = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(force=True, pins=[
            {"id": "ctx", "label": "Iran", "anchor_type": "country", "evidence": []},
            _pin("p1", "measured story"),
        ]))

    by_id = {p["id"]: p for p in resp["pins"]}
    assert by_id["ctx"]["search_status"] == "not_applicable"
    assert resp["partial"] is False
    assert resp["pins_applicable"] == 1


@pytest.mark.asyncio
async def test_hard_budget_cuts_a_hanging_query_and_still_answers(no_llm, monkeypatch):
    """The 502 class: the request must never outlive its budget. A hanging
    query is cancelled, its pin says `timeout`, everything else serves."""
    from app.services import external_depth
    dossier_module = no_llm

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        if raw_query.startswith("slow"):
            await asyncio.sleep(30)
        return _ok("Fast coverage", "fast.example")

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)
    monkeypatch.setattr(dossier_module, "CORROB_SYNC_BUDGET_S", 0.4)

    t0 = time.monotonic()
    resp = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(force=True, pins=[
            _pin("slow-pin", "slow lane story"),
            _pin("fast-pin", "fast lane story"),
        ]))
    elapsed = time.monotonic() - t0

    assert elapsed < 5, f"budget not enforced: {elapsed:.1f}s"
    by_id = {p["id"]: p for p in resp["pins"]}
    assert by_id["slow-pin"]["search_status"] == "timeout"
    assert by_id["fast-pin"]["search_status"] == "ok"
    assert resp["partial"] is True
    assert resp["meta"]["budget_seconds"] == pytest.approx(0.4)


@pytest.mark.asyncio
async def test_partial_payloads_are_not_cached(no_llm, monkeypatch):
    """A degraded run must not be replayed as the answer for 15 minutes."""
    from app.services import external_depth
    dossier_module = no_llm

    calls: list[str] = []

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        calls.append(raw_query)
        return {"status": "throttled", "result": None}

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)
    monkeypatch.setattr(dossier_module, "_CORROB_CACHE", {})

    req = dossier_module.CorroborateRequest(pins=[_pin("p1", "cache probe story")])
    await dossier_module.dossier_corroborate(req)
    n_first = len(calls)
    await dossier_module.dossier_corroborate(req)
    assert len(calls) > n_first, "a partial run must be retried, never cached"


@pytest.mark.asyncio
async def test_full_run_is_cached(no_llm, monkeypatch):
    from app.services import external_depth
    dossier_module = no_llm

    calls: list[str] = []

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        calls.append(raw_query)
        return _ok("Independent coverage", "indep.example")

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)
    monkeypatch.setattr(dossier_module, "_CORROB_CACHE", {})

    req = dossier_module.CorroborateRequest(pins=[_pin("p1", "cache hit story")])
    await dossier_module.dossier_corroborate(req)
    n_first = len(calls)
    await dossier_module.dossier_corroborate(req)
    assert len(calls) == n_first, "a complete run is cached"


# ── 4. Job + poll (the proxy ceiling binds after serialization) ──────────────

@pytest.mark.asyncio
async def test_start_returns_immediately_and_poll_delivers_the_result(no_llm, monkeypatch):
    from app.services import external_depth
    dossier_module = no_llm

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        await asyncio.sleep(0.05)
        return _ok("Independent coverage", "indep.example")

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)
    monkeypatch.setattr(dossier_module, "_CORROB_JOBS", {})
    monkeypatch.setattr(dossier_module, "_CORROB_CACHE", {})

    t0 = time.monotonic()
    started = await dossier_module.dossier_corroborate_start(
        dossier_module.CorroborateRequest(force=True, pins=[
            _pin("p1", "job story one"), _pin("p2", "job story two")]))
    assert time.monotonic() - t0 < 0.5, "start must not wait for the run"
    assert started["status"] == "running"
    job_id = started["job_id"]
    assert started["progress"]["queries_total"] >= 2

    for _ in range(100):
        snap = await dossier_module.dossier_corroborate_status(job_id)
        if snap["status"] == "done":
            break
        await asyncio.sleep(0.05)
    assert snap["status"] == "done"
    assert snap["result"]["contract"] == "dossier-corroboration-v1"
    assert len(snap["result"]["pins"]) == 2
    assert snap["progress"]["queries_done"] == snap["progress"]["queries_total"]


@pytest.mark.asyncio
async def test_start_serves_a_cached_complete_run_without_a_job(no_llm, monkeypatch):
    from app.services import external_depth
    dossier_module = no_llm

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        return _ok("Independent coverage", "indep.example")

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)
    monkeypatch.setattr(dossier_module, "_CORROB_JOBS", {})
    monkeypatch.setattr(dossier_module, "_CORROB_CACHE", {})

    req = dossier_module.CorroborateRequest(pins=[_pin("p1", "warm cache story")])
    await dossier_module.dossier_corroborate(req)
    started = await dossier_module.dossier_corroborate_start(req)
    assert started["status"] == "done"
    assert started["result"]["pins"][0]["id"] == "p1"


@pytest.mark.asyncio
async def test_unknown_job_is_honest_not_a_crash(no_llm, monkeypatch):
    dossier_module = no_llm
    monkeypatch.setattr(dossier_module, "_CORROB_JOBS", {})
    snap = await dossier_module.dossier_corroborate_status("nope")
    assert snap["status"] == "unknown"
    assert snap["result"] is None


@pytest.mark.asyncio
async def test_job_failure_is_reported_not_swallowed(no_llm, monkeypatch):
    from app.services import external_depth
    dossier_module = no_llm

    async def explode(_label, *, raw_query, timespan, **_kw):
        raise RuntimeError("lane exploded")

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", explode)
    monkeypatch.setattr(dossier_module, "_CORROB_JOBS", {})
    monkeypatch.setattr(dossier_module, "_CORROB_CACHE", {})

    started = await dossier_module.dossier_corroborate_start(
        dossier_module.CorroborateRequest(force=True, pins=[_pin("p1", "boom story")]))
    for _ in range(100):
        snap = await dossier_module.dossier_corroborate_status(started["job_id"])
        if snap["status"] in ("done", "error"):
            break
        await asyncio.sleep(0.05)
    # A raising lane is an honest per-pin gap, not a 500 for the whole report.
    assert snap["status"] == "done"
    assert snap["result"]["pins"][0]["search_status"] == "unavailable"


@pytest.mark.asyncio
async def test_a_pin_measured_by_the_supplied_lane_counts_as_measured(no_llm, monkeypatch):
    """Live witness 2026-08-12: a pin came back `established` on 3 voices / 4
    receipts while the run-level line read "0 of 2 evidence pins measured" —
    its DOC 2.0 query was throttled, but the client-supplied lane HAD measured
    it. `search_status` describes the WEB lane (throttled is true of it); the
    measured COUNT must describe the pin, or the banner puts a 0 next to a
    receipt list."""
    from app.services import external_depth
    dossier_module = no_llm

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        return {"status": "throttled", "result": None}

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)

    resp = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(force=True, pins=[
            _pin("supplied-pin", "supplied story"),
            _pin("dark-pin", "dark story"),
        ], supplied_results=[
            {"pin_id": "supplied-pin", "outlet": "dw.com",
             "title": "Independent account one", "url": "https://dw.com/1"},
            {"pin_id": "supplied-pin", "outlet": "naharnet.com",
             "title": "A different independent account", "url": "https://naharnet.com/2"},
            {"pin_id": "supplied-pin", "outlet": "cnn.com",
             "title": "A third distinct account", "url": "https://cnn.com/3"},
        ]))

    by_id = {p["id"]: p for p in resp["pins"]}
    supplied = by_id["supplied-pin"]
    assert supplied["status"] == "established"
    assert supplied["measured"] is True
    assert supplied["search_status"] == "throttled"   # the WEB lane, honestly
    assert by_id["dark-pin"]["measured"] is False
    assert resp["pins_measured"] == 1, "never 0 beside an established verdict"
    assert resp["pins_applicable"] == 2
    assert resp["partial"] is True


@pytest.mark.asyncio
async def test_the_banner_never_refers_to_a_rest_that_does_not_exist(no_llm, monkeypatch):
    """Live witness 2026-08-12: "2 of 2 evidence pins measured … the rest are
    shown unmeasured" — there is no rest. A degraded run that still reached
    every pin says only what is true of it."""
    from app.services import external_depth
    dossier_module = no_llm

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        # Both pins answer their first query; the second one never lands.
        if "receipt" in raw_query:
            return {"status": "down", "result": None}
        return _ok("Independent coverage", f"{raw_query.split()[0]}.example")

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)

    resp = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(force=True, pins=[
            {"id": "p1", "label": "alpha story", "anchor_type": "thread",
             "evidence": ["alpha story receipt headline"]},
            {"id": "p2", "label": "beta story", "anchor_type": "thread",
             "evidence": ["beta story receipt headline"]},
        ]))

    note = resp["meta"]["search_note"]
    assert resp["pins_measured"] == resp["pins_applicable"] == 2
    assert "the rest" not in note, note
    assert "all 2 evidence pins measured" in note, note
    assert "2 of them only partially" in note, note


@pytest.mark.asyncio
async def test_the_banner_agrees_with_itself_grammatically(no_llm, monkeypatch):
    """Live witness: "the 1 not reached are shown". V2 is fixing agrammatical
    splices elsewhere in the dossier; this lane does not add one."""
    from app.services import external_depth
    dossier_module = no_llm

    async def fake_status(_label, *, raw_query, timespan, **_kw):
        if raw_query.startswith("dark"):
            return {"status": "throttled", "result": None}
        return _ok("Independent coverage", "indep.example")

    monkeypatch.setattr(external_depth, "fetch_external_depth_status", fake_status)
    resp = await dossier_module.dossier_corroborate(
        dossier_module.CorroborateRequest(force=True, pins=[
            _pin("p1", "lit story"), _pin("p2", "dark story")]))
    note = resp["meta"]["search_note"]
    assert "the pin not reached is shown unmeasured" in note, note
    assert " 1 not reached are " not in note
