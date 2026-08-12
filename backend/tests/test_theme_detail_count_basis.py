"""Council R4 N19 (the N8 residual): the detail stamped LIFETIME under a window.

A thread row read `88 · 24h · gated`; one click deeper the detail header read
`3,659 signals · Last 24h`. Measured on prod (2026-08-11, dt-11810 "US Bombards
Iran Over Ormuz Attack" — the council's own witness):

  * the ROW number is `recent_n_signals` = SUM(ec.n_signals) at the topic's
    LATEST snapshot                                              -> 88
  * the DETAIL `total` is `agg_n_signals`, a lifetime aggregate   -> 3,659

Both were stamped "24h", and NEITHER was a 24h count: every cluster at the
latest snapshot carries `snapshot_window_h = 168` (3,080/3,080 measured), so
the row's window word was false too.

A truly window-scoped total was measured and REJECTED as unaffordable:
`topic_members ⋈ signals_v2 ON s.timestamp` exceeded 120s, and the
`assigned_at`-only variant ran 19.4s cold on dt-3433 against a 15s
statement_timeout — and `topic_members` is a *projection* for dynamic topics
(dt-11810: 125 rows vs 3,659 lifetime), so its windowed count would have been a
THIRD number contradicting both.

Contract under test — serve both bases, each labeled truthfully, and let the
detail carry THE ROW'S OWN number so the two surfaces agree by construction:
  * `total`            unchanged — the lifetime gate-kept aggregate.
  * `countBasis`       'lifetime' — names what `total` is, so no caller has to
                       infer it from the window.
  * `currentTotal`     the row's `recent_n_signals`.
  * `countWindowHours` the MEASURED window those members were clustered over
                       (`snapshot_window_h`), never a hardcoded 24.
Absence stays honest: a caller whose SELECT omits the columns serves None, not
a fabricated 0 (a 0 would read as "nothing in the window", a measured claim).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import app.main_v2  # noqa: F401 — resolve the app↔router import cycle first
from app.routers import themes


def _topic_row(
    *,
    lifetime: int = 3659,
    recent: int | None = 88,
    window_h: int | None = 168,
    topic_id: int = 11810,
    include_window_cols: bool = True,
) -> dict:
    """The witness row as prod serves it (dt-11810)."""
    row = {
        "id": topic_id,
        "label": "US Bombards Iran Over Ormuz Attack",
        "category": "armed-conflict-escalation",
        "agg_n_signals": lifetime,
        "mean_cohesion": 0.88,
        "noise_rate": 0.07,
        "last_seen": datetime(2026, 8, 11, 3, 5, tzinfo=timezone.utc),
        "first_seen": datetime(2026, 8, 4, tzinfo=timezone.utc),
        "temporal_signature": None,
        "signature_meta": None,
        "label_status": None,
        "label_proposed": None,
    }
    if include_window_cols:
        row["recent_n_signals"] = recent
        row["count_window_hours"] = window_h
    return row


class _EmptyConn:
    """Every receipt lane empty — this suite is about the COUNT contract only.

    The empty-sample early return and the populated path must both carry the
    basis fields, so the harness deliberately exercises the early return.
    """

    async def execute(self, *args, **kwargs):
        return None

    async def fetchrow(self, *args, **kwargs):
        return None

    async def fetchval(self, *args, **kwargs):
        return None

    async def fetch(self, query, *args, **kwargs):
        return []


def _detail(topic_row, *, sample_ids=None, hours=24):
    return asyncio.run(
        themes._dynamic_topic_detail(
            _EmptyConn(),
            topic_row=topic_row,
            sample_ids=list(sample_ids or []),
            top_country_codes=["IR", "US"],
            hours=hours,
            country_code=None,
        )
    )


class TestLifetimeTotalIsNamedNotWindowStamped:
    def test_total_still_serves_the_lifetime_aggregate(self):
        """`total` is unchanged — existing consumers keep their number."""
        payload = _detail(_topic_row())
        assert payload["total"] == 3659
        assert payload["rawTotal"] == 3659
        assert payload["gated"] == 3659

    def test_count_basis_names_total_as_lifetime(self):
        """The header must not have to infer the basis from the window."""
        payload = _detail(_topic_row())
        assert payload["countBasis"] == "lifetime"


class TestDetailCarriesTheRowsOwnNumber:
    def test_current_total_is_the_rows_recent_n(self):
        """Row and detail agree by construction, not by coincidence."""
        payload = _detail(_topic_row(recent=88))
        assert payload["currentTotal"] == 88

    def test_count_window_hours_is_measured_not_assumed(self):
        """168 = the real clustering window; 24 was always a hardcoded lie."""
        payload = _detail(_topic_row(window_h=168))
        assert payload["countWindowHours"] == 168

    def test_witness_reconciles_row_and_detail(self):
        """The council's exact case: 88 on the row, 3,659 lifetime beneath."""
        payload = _detail(_topic_row(lifetime=3659, recent=88, window_h=168))
        assert payload["currentTotal"] == 88, "must match the row's 88"
        assert payload["total"] == 3659, "lifetime stays available"
        assert payload["countBasis"] == "lifetime"
        assert payload["countWindowHours"] == 168


class TestAbsenceIsHonestNeverFabricated:
    def test_missing_columns_serve_none_not_zero(self):
        """A 0 would read as a measured 'nothing in the window'."""
        payload = _detail(_topic_row(include_window_cols=False))
        assert payload["currentTotal"] is None
        assert payload["countWindowHours"] is None
        assert payload["total"] == 3659, "lifetime lane is independent"

    def test_null_columns_serve_none_not_zero(self):
        """COALESCE(...,0) upstream must not turn absence into a claim."""
        payload = _detail(_topic_row(recent=None, window_h=None))
        assert payload["currentTotal"] is None
        assert payload["countWindowHours"] is None

    def test_basis_fields_survive_the_populated_path(self):
        """Not just the empty-sample early return — the full path too."""
        payload = _detail(_topic_row(), sample_ids=[1, 2, 3])
        assert payload["countBasis"] == "lifetime"
        assert payload["currentTotal"] == 88
        assert payload["countWindowHours"] == 168


class TestThreadRowCarriesItsTrueWindow:
    """The row's other half: its `24h` chip was hardcoded in the frontend.

    Dynamic rows count over the snapshot window (measured 168h), NOT over the
    requested hours, so the row must serve the window its number belongs to.
    Atlas rows genuinely are hours-filtered and keep serving no override — the
    frontend falls back to the requested window for them.
    """

    def test_dynamic_row_serves_the_measured_window(self):
        from app.services.thread_intelligence import assemble_dynamic_thread

        row = _topic_row()
        row["identity_key"] = "u2-iran-ormuz"
        row["top_country_codes"] = ["IR", "US"]
        row["changed_10h"] = 12
        thread = assemble_dynamic_thread(row, [])
        assert thread["count_window_hours"] == 168
        assert thread["signal_count"] == 88, "row number unchanged"

    def test_dynamic_row_without_the_column_serves_absence(self):
        """Never a fabricated 24 — the frontend decides the fallback."""
        from app.services.thread_intelligence import assemble_dynamic_thread

        row = _topic_row(include_window_cols=False)
        row["identity_key"] = "u2-iran-ormuz"
        row["top_country_codes"] = ["IR", "US"]
        thread = assemble_dynamic_thread(row, [])
        assert thread["count_window_hours"] is None
