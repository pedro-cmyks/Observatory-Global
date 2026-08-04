"""Gold day-5 GQ-08/GQ-12 serving starvation (2026-08-04).

`GET /api/v2/theme/dynamic-topic-8057` served `total: 41, signalSample: 1,
signals: [1 row]` with NO degraded flag — a surging 41-member thread silently
collapsed to one receipt. Root cause: the detail's ONLY receipt lane is
`dynamic_topic_members ⋈ emergent_clusters.sample_signal_ids ⋈ signals_v2`,
and the persisted sample ids reference signals the 7-day hot retention has
already deleted (dt-8057: 11 distinct sample ids → 1 alive; dt-3805: 39 → 2).
The count lane (`agg_n_signals`) survives retention because it is a persisted
integer; the receipt lane dies because it is a set of foreign references.

Fix under test:
 * `_dynamic_topic_detail` unions the typed `topic_members` evidence
   projection (engine-agnostic, deduped — the relationship-endpoint UNION
   pattern) with the cluster sample ids, and the signals_v2 join decides
   liveness.
 * Starvation is judged on the UNSCOPED live count: when every lane together
   serves fewer live receipts than min(5, total), the payload carries
   `degraded: true, degraded_reason: 'member_sample_starved'` plus a warning —
   the query_thread G5 contract shape. Absence (total=0) stays honest and
   un-degraded; silent thinness is what is banned.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import app.main_v2  # noqa: F401 — resolve the app↔router import cycle first
from app.routers import themes


def _topic_row(total: int = 41, topic_id: int = 8057) -> dict:
    return {
        "id": topic_id,
        "label": "Indonesia Central Bank Governor Resigns",
        "category": "financial-market-movements",
        "agg_n_signals": total,
        "mean_cohesion": 0.91,
        "noise_rate": 0.05,
        "last_seen": datetime(2026, 8, 2, 3, 5, tzinfo=timezone.utc),
        "first_seen": datetime(2026, 7, 28, tzinfo=timezone.utc),
        "temporal_signature": None,
        "signature_meta": None,
        "label_status": None,
        "label_proposed": None,
    }


def _sig(i: int, cc: str = "ID") -> dict:
    return {
        "id": i,
        "source_lang": "en",
        "timestamp": datetime(2026, 8, 3, 12, tzinfo=timezone.utc)
        - timedelta(hours=i),
        "country_code": cc,
        "source_name": f"outlet-{i}.example",
        "source_url": f"https://outlet-{i}.example/story",
        "sentiment": -0.1,
        "headline": f"BI governor resignation coverage item {i}",
        "themes": [],
        "persons": [],
    }


class _Conn:
    """Routes _dynamic_topic_detail's queries by shape.

    * `signal_embeddings` join → the coherence guard lane → empty (guard
      degrades to None).
    * `FROM topic_members` (evidence union lane) → configured signal ids,
      or raises when `tm_error` (the lane must degrade, never 500).
    * `FROM signals_v2` by id-array → only the configured LIVE rows whose ids
      were requested (retention pruning simulated by absence).
    * fetchrow → None (no centroid → semantic lane measured-absent).
    """

    def __init__(self, *, tm_ids=None, live_rows=None, tm_error: bool = False):
        self.tm_ids = list(tm_ids or [])
        self.live_rows = list(live_rows or [])
        self.tm_error = tm_error
        self.queries: list[str] = []

    async def execute(self, *args, **kwargs):
        return None

    async def fetchrow(self, *args, **kwargs):
        return None

    async def fetchval(self, *args, **kwargs):
        return None

    async def fetch(self, query, *args, **kwargs):
        self.queries.append(query)
        if "signal_embeddings" in query:
            return []
        if "FROM topic_members" in query:
            if self.tm_error:
                raise RuntimeError("topic_members unavailable")
            return [{"signal_id": i} for i in self.tm_ids]
        if "FROM signals_v2" in query:
            requested = {int(x) for x in args[0]}
            return [r for r in self.live_rows if int(r["id"]) in requested]
        return []


def _detail(conn, *, topic_row, sample_ids, country_code=None, hours=24):
    return asyncio.run(
        themes._dynamic_topic_detail(
            conn,
            topic_row=topic_row,
            sample_ids=sample_ids,
            top_country_codes=["ID"],
            hours=hours,
            country_code=country_code,
        )
    )


class TestStarvedSampleIsNeverSilent:
    def test_retention_starved_sample_marks_degraded(self):
        # dt-8057 live shape: 11 persisted sample ids, 1 survives retention.
        conn = _Conn(live_rows=[_sig(1)])
        out = _detail(conn, topic_row=_topic_row(41), sample_ids=list(range(1, 12)))
        assert out["total"] == 41
        assert out["signalSample"] == 1
        assert out["degraded"] is True
        assert out["degraded_reason"] == "member_sample_starved"
        assert "member_sample_starved" in out["warnings"]
        # It still serves what it honestly has.
        assert len(out["signals"]) == 1

    def test_empty_sample_on_populated_thread_marks_degraded(self):
        # Every lane empty while the thread advertises 41 members.
        conn = _Conn()
        out = _detail(conn, topic_row=_topic_row(41), sample_ids=[])
        assert out["signalSample"] == 0
        assert out["degraded"] is True
        assert out["degraded_reason"] == "member_sample_starved"
        assert "dynamic_topic_empty_sample" in out["warnings"]
        assert "member_sample_starved" in out["warnings"]

    def test_honest_absence_is_not_degraded(self):
        # total=0 with nothing to serve is a measured absence, not starvation.
        conn = _Conn()
        out = _detail(conn, topic_row=_topic_row(0), sample_ids=[])
        assert out["signalSample"] == 0
        assert out["degraded"] is False
        assert out["degraded_reason"] is None
        assert "member_sample_starved" not in out["warnings"]

    def test_small_topic_fully_served_is_not_degraded(self):
        # min(5, total) floor: a 3-member thread serving all 3 is healthy.
        conn = _Conn(live_rows=[_sig(1), _sig(2), _sig(3)])
        out = _detail(conn, topic_row=_topic_row(3), sample_ids=[1, 2, 3])
        assert out["signalSample"] == 3
        assert out["degraded"] is False
        assert out["degraded_reason"] is None


class TestTopicMembersUnionLane:
    def test_topic_members_evidence_rescues_dead_sample_ids(self):
        # Cluster sample ids all retention-dead; the typed evidence projection
        # still knows 8 live members → the detail serves them, un-degraded.
        live = [_sig(i) for i in range(1, 9)]
        conn = _Conn(tm_ids=list(range(1, 9)), live_rows=live)
        out = _detail(conn, topic_row=_topic_row(41), sample_ids=[900, 901])
        assert out["signalSample"] == 8
        assert out["degraded"] is False
        assert out["degraded_reason"] is None
        assert "member_sample_starved" not in out["warnings"]
        assert "dynamic_topic_member_preview_sample" in out["warnings"]

    def test_union_deduplicates_across_lanes(self):
        # Same signal known to both lanes must serve once.
        live = [_sig(i) for i in range(1, 7)]
        conn = _Conn(tm_ids=[1, 2, 3, 4, 5, 6], live_rows=live)
        out = _detail(conn, topic_row=_topic_row(6), sample_ids=[1, 2, 3])
        assert out["signalSample"] == 6
        served_ids = [s["id"] for s in out["graphSignals"]]
        assert len(served_ids) == len(set(served_ids))

    def test_topic_members_lane_failure_degrades_to_sample_lane(self):
        # topic_members query raising must never 500 the detail; the cluster
        # sample lane still serves and the payload stays honest.
        live = [_sig(i) for i in range(1, 7)]
        conn = _Conn(tm_error=True, live_rows=live)
        out = _detail(conn, topic_row=_topic_row(6), sample_ids=[1, 2, 3, 4, 5, 6])
        assert out["signalSample"] == 6
        assert out["degraded"] is False


class TestCountryScopeIsNotStarvation:
    def test_thin_country_slice_of_healthy_sample_is_honest_scoping(self):
        # 12 live members globally, 2 in PE: the PE slice is honest scoping —
        # starvation is judged on the UNSCOPED live count.
        live = [_sig(i, cc="PE" if i <= 2 else "ID") for i in range(1, 13)]
        conn = _Conn(live_rows=live)
        out = _detail(
            conn,
            topic_row=_topic_row(41),
            sample_ids=list(range(1, 13)),
            country_code="PE",
        )
        assert out["signalSample"] == 2
        assert out["degraded"] is False
        assert out["degraded_reason"] is None
        assert all(s["country"] == "PE" or s.get("country_code") == "PE"
                   for s in out["graphSignals"])

    def test_country_scoped_starved_thread_still_flags(self):
        # 1 live member globally on a 41-member thread stays starved no matter
        # the scope.
        conn = _Conn(live_rows=[_sig(1, cc="PE")])
        out = _detail(
            conn,
            topic_row=_topic_row(41),
            sample_ids=list(range(1, 12)),
            country_code="PE",
        )
        assert out["degraded"] is True
        assert out["degraded_reason"] == "member_sample_starved"
