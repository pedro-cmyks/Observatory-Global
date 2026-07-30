"""P3 (2026-07-30) — tail-first budget reserve inside run_scoped_snapshot.

The measured defect (docs/research/recall-229/2026-07-29-threading-floor-
diagnosis.md §P3): the 150-min weekday run budget defers 130-154 countries a
night, rotation only decides WHICH big countries run, and the thin tail is
clustered ~3 nights in 7 — so `persist_min=2` is unreachable for BO/ML by
construction. The tail is not expensive (the whole sub-2k population is ~0.7 %
of the pass's Σn²); the clock simply runs out on the head first.

These tests drive the REAL country loop in ``main()`` against a fake
connection and a fake (shifted-but-monotonic) clock, because the behaviour
under test is scheduling, not clustering:

  - flag OFF is byte-identical: n-DESC order, same deferrals, same ledger;
  - flag ON runs the tail FIRST, cheapest-first, and the head keeps its order;
  - the starvation case: the same budget that never reaches the tail today
    reaches ALL of it with the reserve, and the deferral lands on the head;
  - the reserve is a CEILING — a tail lane that overruns its slice hands the
    budget back to the head instead of eating it (gate TF-4);
  - the checkpoint `done` ledger records exactly the countries that ran, under
    both flags. P2 (ATLAS_LIFECYCLE_COUNTRY_CLOCK) reads that ledger to decide
    which topics may age, so a country listed there without running — or
    missing after running — would silently corrupt the lifecycle clock.

NOTE: run_scoped_snapshot imports emergent_poc which imports hdbscan at module
level — these tests run in the M1 mlvenv and skip cleanly in the API .venv.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("hdbscan")
pytest.importorskip("asyncpg")

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

import backend.scripts.run_scoped_snapshot as rss  # noqa: E402
from backend.scripts.snapshot_budget import load_checkpoint  # noqa: E402

# n-DESC exactly as the countries query serves it. Head ≥ 2000, tail < 2000;
# BO/ML/NE are the diagnosis's own starved witnesses (745/571/133).
SIZES = {"US": 40249, "IN": 20355, "GB": 9000, "RU": 4973,
         "CO": 1500, "BO": 745, "ML": 571, "NE": 133}
N_DESC = ["US", "IN", "GB", "RU", "CO", "BO", "ML", "NE"]
RUN_BUDGET_MIN = 150.0          # the real weekday budget
HEAD_COST_S = 3000.0            # 50 min — three head countries fill the night
TAIL_COST_S = 60.0              # the tail is cheap (measured: ~0.7 % of Σn²)


class _FakeConn:
    """Only the countries query reaches it — every other DB call is patched."""

    def __init__(self, rows):
        self._rows = rows
        self._closed = False

    async def execute(self, *_a):
        return "SET"

    async def fetch(self, *_a):
        return self._rows

    def is_closed(self):
        return self._closed

    async def close(self):
        self._closed = True


def _run_pass(monkeypatch, tmp_path: Path, *, costs: dict[str, float],
              extra_argv: list[str], sizes: dict[str, int] = SIZES,
              order: list[str] = N_DESC):
    """Execute one real ``main()`` pass. Returns (processed_ccs, checkpoint)."""
    seen: list[str] = []
    # A SHIFTED but still-monotonic clock: real monotonic + an offset each
    # country adds. asyncio's own timers stay consistent (the shift only ever
    # grows), while the run-budget arithmetic sees a deterministic cost model.
    offset = [0.0]
    real_monotonic = time.monotonic
    monkeypatch.setattr(time, "monotonic", lambda: real_monotonic() + offset[0])

    conn = _FakeConn([{"country_code": cc, "n": sizes[cc]} for cc in order])

    async def fake_connect(*_a, **_kw):
        return conn

    async def fake_country_clusters(_conn, cc, *_a, **_kw):
        seen.append(cc)
        offset[0] += costs.get(cc, 0.0)
        rows = [{"id": 1, "headline": f"{cc} fixture headline for the tail lane"}]
        return ([{"top_signal_idxs": [0]}],
                np.zeros((1, 4), dtype=np.float32), rows)

    async def fake_prior(*_a, **_kw):
        return {}

    async def fake_commit(conn_, *_a, **_kw):
        return conn_

    monkeypatch.setattr(rss.asyncpg, "connect", fake_connect)
    monkeypatch.setattr(rss, "_load_gate", lambda _p: {"_threshold": 0.5})
    monkeypatch.setattr(rss, "_prior_snapshot_clusters", fake_prior)
    monkeypatch.setattr(rss, "_country_clusters", fake_country_clusters)
    monkeypatch.setattr(rss, "_prepare_snapshot_rows",
                        lambda **_kw: [{"row": 1}])
    monkeypatch.setattr(rss, "_commit_country", fake_commit)

    monkeypatch.setenv("DATABASE_URL", "postgres://fixture/atlas")
    for env in ("ATLAS_SNAPSHOT_TAIL_RESERVE", "ATLAS_SNAPSHOT_TAIL_MAX_N",
                "ATLAS_SNAPSHOT_RUN_BUDGET_MIN", "ATLAS_SNAPSHOT_COUNTRY_BUDGET_S",
                "ATLAS_SNAPSHOT_STATE_DIR", "ATLAS_SNAPSHOT_SUBPROC_MIN_N"):
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setattr(sys, "argv", [
        "run_scoped_snapshot", "--skip-label",
        "--run-budget-min", str(RUN_BUDGET_MIN),
        "--country-budget-s", "0", "--subproc-min-n", "0",
        "--state-dir", str(tmp_path),
    ] + extra_argv)

    asyncio.run(rss.main())
    ck = load_checkpoint(tmp_path / "scoped-snapshot-checkpoint.json")
    return seen, ck


def _costs(head=HEAD_COST_S, tail=TAIL_COST_S) -> dict[str, float]:
    return {cc: (head if n >= 2000 else tail) for cc, n in SIZES.items()}


# ------------------------------------------------------------------ flag OFF

def test_flag_off_keeps_the_n_desc_order_and_starves_the_tail(monkeypatch, tmp_path):
    """The frozen defect: three head countries fill the 150-min night and the
    pass never reaches BO/ML/NE. This is today's behaviour, asserted so the
    flag-on cases below are measured against the real baseline."""
    seen, ck = _run_pass(monkeypatch, tmp_path, costs=_costs(), extra_argv=[])
    assert seen == ["US", "IN", "GB"]
    assert set(ck.done) == {"US", "IN", "GB"}
    for witness in ("BO", "ML", "NE"):
        assert witness not in seen and witness not in ck.done


def test_flag_off_is_unchanged_by_the_tail_max_n_knob(monkeypatch, tmp_path):
    """--tail-max-n is inert on its own: only --tail-reserve arms the lane."""
    seen, ck = _run_pass(monkeypatch, tmp_path, costs=_costs(),
                         extra_argv=["--tail-max-n", "2000"])
    assert seen == ["US", "IN", "GB"] and set(ck.done) == {"US", "IN", "GB"}


# ------------------------------------------------------------------- flag ON

def test_tail_first_reaches_every_thin_country_and_defers_the_head(monkeypatch, tmp_path):
    """(a) the tail is clustered EVERY pass; (b) the head keeps its n-DESC
    order, only later; (c) the deferral falls on the head."""
    seen, ck = _run_pass(monkeypatch, tmp_path, costs=_costs(),
                         extra_argv=["--tail-reserve", "0.25"])
    assert seen[:4] == ["NE", "ML", "BO", "CO"]     # tail, thinnest first
    assert seen[4:] == ["US", "IN", "GB"]           # head order UNCHANGED
    assert set(ck.done) == set(seen)
    assert "RU" not in seen                         # deferral landed on the head


def test_tail_first_costs_the_head_one_country_not_the_night(monkeypatch, tmp_path):
    """The trade, stated as an assertion: the head loses exactly the countries
    the tail's (cheap) lane displaces — US/IN/GB still cluster, so TF-4's
    no-regression bar on the biggest countries is structurally intact."""
    base, _ = _run_pass(monkeypatch, tmp_path, costs=_costs(), extra_argv=[])
    tail_first, _ = _run_pass(monkeypatch, tmp_path / "b", costs=_costs(),
                              extra_argv=["--tail-reserve", "0.25"])
    head_before = [c for c in base if SIZES[c] >= 2000]
    head_after = [c for c in tail_first if SIZES[c] >= 2000]
    assert head_after == head_before                # same head countries, same order
    assert len(tail_first) > len(base)              # and four more countries served


def test_tail_slice_is_a_ceiling_and_hands_the_budget_back(monkeypatch, tmp_path):
    """An overrunning tail lane must not eat the head's budget: once the slice
    is spent the REST OF THE TAIL defers (in bulk) and the head starts."""
    costs = _costs(tail=1200.0)                     # 20 min per tail country
    seen, ck = _run_pass(monkeypatch, tmp_path, costs=costs,
                         extra_argv=["--tail-reserve", "0.1"])  # 15-min slice
    assert seen[0] == "NE"                          # thinnest ran
    assert seen[1:] == ["US", "IN", "GB"]           # slice spent → head lane
    for spilled in ("ML", "BO", "CO"):
        assert spilled not in seen and spilled not in ck.done
    assert set(ck.done) == {"NE", "US", "IN", "GB"}


def test_tail_lane_survives_a_run_budget_that_fits_nothing_else(monkeypatch, tmp_path):
    """The point of P3 in one case: a budget too small for even one head
    country still clusters the whole tail."""
    costs = _costs(head=1e6)                        # no head country can fit
    seen, ck = _run_pass(monkeypatch, tmp_path, costs=costs,
                         extra_argv=["--tail-reserve", "0.25"])
    assert seen[:4] == ["NE", "ML", "BO", "CO"]
    assert set(ck.done) >= {"NE", "ML", "BO", "CO"}


def test_unknown_sized_countries_never_enter_the_cheap_lane(monkeypatch, tmp_path):
    """A --countries test slice has no measured sizes, so the lane is off and
    the literal order stands (same gating as checkpointing and rotation)."""
    seen, _ = _run_pass(monkeypatch, tmp_path, costs=_costs(),
                        extra_argv=["--tail-reserve", "0.25",
                                    "--countries", "NE,US,BO"])
    assert seen == ["NE", "US", "BO"]               # literal order, no reorder


# ------------------------------------------------- done-ledger correctness (P2)

def test_done_ledger_records_only_countries_that_actually_ran(monkeypatch, tmp_path):
    """P2 reads this ledger: a country in `done` is one Atlas LOOKED at, and
    its topics may age. Deferrals — head or tail — must never appear."""
    for argv in ([], ["--tail-reserve", "0.25"], ["--tail-reserve", "0.02"]):
        seen, ck = _run_pass(monkeypatch, tmp_path / f"d{len(argv)}",
                             costs=_costs(tail=600.0), extra_argv=argv)
        assert list(ck.done) == seen                # same set AND same order
        assert all(v == "ok" for v in ck.done.values())
        assert set(ck.done).isdisjoint(set(SIZES) - set(seen))
