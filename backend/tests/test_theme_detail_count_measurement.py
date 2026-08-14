"""`total` was named 'lifetime'. It is not a lifetime — it is a running SUM.

The N19 pass (d822ae17) correctly stopped the header stamping the requested
window onto `total`, and named the basis `lifetime`. Measured on prod
2026-08-14 against dt-242 ("7.4-Magnitude Earthquake Kills Dozens in
Colombia"), that NAME is itself wrong, and the header inherited the error:

    header:  "Global · 18 signals · last 7d · 323 lifetime"

`total` = `dynamic_topics.agg_n_signals` = 323. The projection accumulates it
(`project_dynamic_topics.py`: `self.agg_n_signals += cluster["n_signals"]` on
every attach, `+= other.agg_n_signals` on every absorb). dt-242's 17 clustering
passes carry, in order:

    43 34 34 34 16 8 13 10 11 11 14 14 14 14 16 19 18   ->   sum = 323

So 323 is the SUM OF PER-PASS CLUSTER SIZES over 17 passes, not a count of
distinct signals. It double-counts by construction: the four 2026-06-25 passes
each clustered a rolling 24h window (43, 34, 34, 34) over largely the SAME
articles, and every one of those articles was counted again in every pass that
still saw it. A reader told "323 lifetime" reads "323 articles"; the true
distinct figure is unknowable from here (7-day hot retention has deleted most
of the rows, and `topic_members` is only a projection for dynamic topics).

`currentTotal` = 18 is the OTHER half: SUM(ec.n_signals) at the LATEST snapshot
only (2026-08-13 03:27), i.e. one clustering pass. The header printed it as
"last 7d". Its clusters were built over a 168h window, but that window ENDED at
the snapshot — it is not a rolling 7-days-to-now, and above all it is one pass,
not a period count.

Contract under test — every number states the basis it was measured on:
  * ``countBasis``    'cumulative_snapshots' — never 'lifetime'.
  * ``snapshotCount`` how many passes were summed, so 323 is interpretable.
  * ``currentBasis``  'latest_snapshot' — names `currentTotal` as one pass.
  * ``snapshotAt``    when that pass ran (already served; now load-bearing).
Absence stays honest throughout: None, never a fabricated 0.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import app.main_v2  # noqa: F401 — resolve the app↔router import cycle first
from app.routers import themes


def _dt242_row(*, cumulative=323, recent=18, window_h=168, snapshots=17, **over):
    """The witness row exactly as prod serves dt-242."""
    row = {
        "id": 242,
        "label": "7.4-Magnitude Earthquake Kills Dozens in Colombia",
        "category": "natural-disaster",
        "agg_n_signals": cumulative,
        "n_snapshots": snapshots,
        "mean_cohesion": 0.97,
        "noise_rate": 0.0,
        "last_seen": datetime(2026, 8, 13, 3, 27, 59, tzinfo=timezone.utc),
        "first_seen": datetime(2026, 6, 25, 5, 0, 6, tzinfo=timezone.utc),
        "temporal_signature": "new",
        "signature_meta": None,
        "label_status": "entailed",
        "label_proposed": None,
        "recent_n_signals": recent,
        "count_window_hours": window_h,
    }
    row.update(over)
    return row


class _EmptyConn:
    async def execute(self, *a, **k):
        return None

    async def fetchrow(self, *a, **k):
        return None

    async def fetchval(self, *a, **k):
        return None

    async def fetch(self, *a, **k):
        return []


def _detail(topic_row, *, sample_ids=None, hours=168):
    return asyncio.run(
        themes._dynamic_topic_detail(
            _EmptyConn(),
            topic_row=topic_row,
            sample_ids=list(sample_ids or []),
            top_country_codes=["CO"],
            hours=hours,
            country_code=None,
        )
    )


class TestTotalIsNamedCumulativeNotLifetime:
    def test_basis_is_cumulative_snapshots(self):
        """'lifetime' claims distinct signals; 323 is a sum of repeats."""
        assert _detail(_dt242_row())["countBasis"] == "cumulative_snapshots"

    def test_basis_is_never_the_word_lifetime(self):
        """Guards the exact regression: the word itself is the false claim."""
        assert _detail(_dt242_row())["countBasis"] != "lifetime"

    def test_total_value_is_unchanged(self):
        """The number is right for what it is — only its NAME was wrong."""
        payload = _detail(_dt242_row())
        assert payload["total"] == 323
        assert payload["rawTotal"] == 323
        assert payload["gated"] == 323

    def test_snapshot_count_makes_the_sum_interpretable(self):
        """323 means nothing without '...across 17 passes' beside it."""
        assert _detail(_dt242_row(snapshots=17))["snapshotCount"] == 17


class TestCurrentTotalIsNamedAsOnePass:
    def test_current_basis_is_latest_snapshot(self):
        """Not a rolling 7d-to-now: one clustering pass."""
        assert _detail(_dt242_row())["currentBasis"] == "latest_snapshot"

    def test_current_total_is_the_latest_pass_number(self):
        payload = _detail(_dt242_row(recent=18))
        assert payload["currentTotal"] == 18

    def test_snapshot_timestamp_anchors_the_pass(self):
        """'18 as of 13 Aug 03:27' is honest; '18 last 7d' is not."""
        assert _detail(_dt242_row())["snapshotAt"].startswith("2026-08-13T03:27")

    def test_window_hours_still_measured_not_assumed(self):
        assert _detail(_dt242_row(window_h=168))["countWindowHours"] == 168


class TestTheWitnessHeaderCanNowBeTruthful:
    def test_every_number_carries_its_basis(self):
        """All four fields the header needs, in one payload."""
        p = _detail(_dt242_row())
        assert (p["total"], p["countBasis"], p["snapshotCount"]) == (
            323, "cumulative_snapshots", 17,
        )
        assert (p["currentTotal"], p["currentBasis"]) == (18, "latest_snapshot")


class TestAbsenceIsHonest:
    def test_missing_snapshot_count_serves_none_not_zero(self):
        """A 0 would read as 'summed across no passes' — a false claim."""
        row = _dt242_row()
        del row["n_snapshots"]
        assert _detail(row)["snapshotCount"] is None

    def test_null_snapshot_count_serves_none(self):
        assert _detail(_dt242_row(n_snapshots=None))["snapshotCount"] is None

    def test_basis_fields_survive_the_populated_receipt_path(self):
        """Not only the empty-sample early return."""
        p = _detail(_dt242_row(), sample_ids=[1, 2, 3])
        assert p["countBasis"] == "cumulative_snapshots"
        assert p["currentBasis"] == "latest_snapshot"
        assert p["snapshotCount"] == 17


class TestSourceCountRidesTheDetailPayload:
    def test_empty_receipts_serve_none_never_a_capped_zero(self):
        """No receipts resolved is degraded, not '0 outlets'."""
        p = _detail(_dt242_row())
        assert p["sourceCount"] is None
        assert p["sourceCountBasis"] == "receipt_sample"
