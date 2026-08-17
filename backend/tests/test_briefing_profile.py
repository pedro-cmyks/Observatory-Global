"""Timing instrumentation for the briefing profiler (spec §9, T1).

The dict passed as `timings` collects {section_name: elapsed_ms}. It must
record for BOTH the fetchrow and fetch paths, and record even when the
section degrades (a degraded section that took 14.9s is exactly what we
are hunting).
"""
import asyncio
import pytest

import app.main_v2  # noqa: F401 — the router imports the app; import it first
from app.routers.briefing import _fetch_section


class FakeConn:
    def __init__(self, delay_s=0.0, fail=False):
        self.delay_s = delay_s
        self.fail = fail

    async def _go(self):
        await asyncio.sleep(self.delay_s)
        if self.fail:
            raise RuntimeError("boom")
        return [{"x": 1}]

    async def fetch(self, query, *args, timeout=None):
        return await self._go()

    async def fetchrow(self, query, *args, timeout=None):
        rows = await self._go()
        return rows[0]


@pytest.mark.asyncio
async def test_timings_recorded_for_fetch_path():
    timings, degraded = {}, []
    await _fetch_section(FakeConn(delay_s=0.01), degraded, "top_countries",
                         "SELECT 1", timings=timings)
    assert "top_countries" in timings
    assert timings["top_countries"] >= 10  # ms


@pytest.mark.asyncio
async def test_timings_recorded_even_when_section_degrades():
    timings, degraded = {}, []
    await _fetch_section(FakeConn(delay_s=0.01, fail=True), degraded,
                         "heat_countries", "SELECT 1", timings=timings)
    assert "heat_countries" in timings
    assert "heat_countries" in degraded  # existing degradation contract intact


@pytest.mark.asyncio
async def test_timings_none_is_the_default_and_changes_nothing():
    degraded = []
    rows = await _fetch_section(FakeConn(), degraded, "s", "SELECT 1")
    assert rows == [{"x": 1}]
