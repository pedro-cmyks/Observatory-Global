from __future__ import annotations

import asyncio
import inspect

from app.services import thread_intelligence
from app.services.thread_intelligence import (
    THREAD_EVIDENCE_SQL,
    THREADS_SQL,
    _attach_atlas_evidence,
    _serialize_evidence,
    assemble_dynamic_thread,
    assemble_thread,
    build_thread_id,
    build_thread_label,
    confidence_band,
    evidence_role,
    fetch_threads,
    parse_thread_id,
)


def test_confidence_band_high():
    assert (
        confidence_band(
            evidence_count=80,
            source_count=12,
            geo_count=5,
            assignment_confidence=0.82,
        )
        == "high"
    )


def test_confidence_band_thin():
    assert (
        confidence_band(
            evidence_count=6,
            source_count=2,
            geo_count=1,
            assignment_confidence=0.7,
        )
        == "thin"
    )


def test_confidence_band_degraded():
    assert (
        confidence_band(
            evidence_count=100,
            source_count=1,
            geo_count=1,
            assignment_confidence=0.4,
        )
        == "degraded"
    )


def test_build_thread_id_is_stable():
    assert (
        build_thread_id("fuel-subsidy-unrest", ["NG", "PE"])
        == "fuel-subsidy-unrest--ng-pe"
    )


def test_parse_thread_id_returns_anchor_and_country_codes():
    assert parse_thread_id("fuel-subsidy-unrest--ng-pe") == (
        "fuel-subsidy-unrest",
        ["NG", "PE"],
    )


def test_build_thread_label_uses_topic_and_geography():
    label = build_thread_label(
        anchor_label="Fuel subsidy unrest",
        top_countries=["Nigeria", "Peru"],
    )
    assert label == "Fuel subsidy unrest in Nigeria and Peru"


def test_assemble_thread_contract():
    row = {
        "topic_slug": "fuel-subsidy-unrest",
        "topic_label": "Fuel subsidy unrest",
        "parent_domain": "economy-livelihoods",
        "signal_count": 120,
        "source_count": 18,
        "country_count": 3,
        "avg_confidence": 0.81,
        "first_seen": None,
        "changed_10h": 47,
        "sentiment_swing_10h": -0.24,
        "top_countries": ["NG", "PE"],
        "top_country_names": ["Nigeria", "Peru"],
        "top_sources": ["reuters.com", "elcomercio.pe"],
        "top_entities": ["Bola Tinubu", "Dina Boluarte"],
        "hourly_timeline": [{"hour": "2026-05-24T10:00:00Z", "count": 12}],
        "related_topics": [{"topic": "labor-strike-disruption", "score": 0.21}],
    }
    thread = assemble_thread(row)
    assert thread["thread_id"] == "fuel-subsidy-unrest--ng-pe"
    assert thread["anchor_topics"] == ["fuel-subsidy-unrest"]
    assert thread["parent_domain"] == "economy-livelihoods"
    assert thread["confidence"] == "high"
    assert thread["avg_confidence"] == 0.81
    # 47 / 120 = 0.392 → surging (>= 5% delta)
    assert thread["trend"] == "surging"
    assert thread["top_entities"] == ["Bola Tinubu", "Dina Boluarte"]
    assert thread["hourly_timeline"][0]["count"] == 12
    # #214: why_now must read as a NET delta vs the prior 10h, never as a
    # gross count that invites comparison against the window signal_count.
    assert (
        thread["why_now"]
        == "Up 47 vs the prior 10h (net new coverage), concentrated in Nigeria and Peru."
    )
    # #214: reader-safe movement chip is self-describing ("vs prior 10h").
    assert thread["movement_label"] == "+47 vs prior 10h"
    assert thread["related_threads"][0]["topic"] == "labor-strike-disruption"
    assert "narrative_note" in thread
    assert thread["narrative_note"] is not None
    assert thread["narrative_note"]["source"] == "extractive-v1"


def test_assemble_thread_parses_jsonb_strings_from_asyncpg():
    row = {
        "topic_slug": "mining-royalty-risk",
        "topic_label": "Mining royalty risk",
        "signal_count": 80,
        "source_count": 12,
        "country_count": 3,
        "avg_confidence": 0.78,
        "changed_10h": 8,
        "top_countries": ["CN", "US"],
        "top_country_names": ["China", "United States"],
        "top_sources": ["reuters.com"],
        "top_entities": [],
        "hourly_timeline": '[{"hour":"2026-05-24T10:00:00Z","count":12}]',
        "related_topics": '[{"topic":"currency-debt-stress","co_signals":2}]',
    }

    thread = assemble_thread(row)

    assert thread["hourly_timeline"] == [
        {"hour": "2026-05-24T10:00:00Z", "count": 12}
    ]
    assert thread["related_threads"] == [
        {"topic": "currency-debt-stress", "co_signals": 2}
    ]


def test_assemble_thread_exposes_quality_metadata_and_raw_entity_guardrails():
    row = {
        "topic_slug": "transport-corridor-disruption",
        "topic_label": "Transport corridor disruption",
        "parent_domain": "infrastructure",
        "signal_count": 25,
        "source_count": 4,
        "country_count": 2,
        "avg_confidence": 0.67,
        "first_seen": None,
        "changed_10h": 5,
        "sentiment_swing_10h": 0.08,
        "lex_count": 6,
        "theme_count": 19,
        "top_countries": ["US", "RB"],
        "top_country_names": ["United States", "RB"],
        "top_sources": ["zazoom.it", "reuters.com"],
        "top_entities": ["Pacific Ocean", "El Niño"],
        "hourly_timeline": [],
        "related_topics": [],
    }

    thread = assemble_thread(row)

    assert thread["top_people"] == []
    assert thread["top_entities"] == ["Pacific Ocean", "El Niño"]
    assert thread["quality"] == {
        "lex_pct": 0.24,
        "method_mix": {"lex": 6, "theme": 19},
        "source_flags": {"aggregator_dominant": True},
        "geo_flags": {"unresolved_country_code": True},
        "entity_flags": {"raw_entity_field_untyped": True},
    }


def test_assemble_thread_quality_metadata_handles_zero_counts_and_clean_rows():
    row = {
        "topic_slug": "heat-health-risk",
        "topic_label": "Heat and public health risk",
        "signal_count": 0,
        "source_count": 0,
        "country_count": 0,
        "avg_confidence": None,
        "changed_10h": 0,
        "lex_count": None,
        "theme_count": None,
        "top_countries": [],
        "top_country_names": [],
        "top_sources": ["reuters.com"],
        "top_entities": [],
    }

    thread = assemble_thread(row)

    assert thread["quality"]["lex_pct"] == 0
    assert thread["quality"]["method_mix"] == {"lex": 0, "theme": 0}
    assert thread["quality"]["source_flags"] == {"aggregator_dominant": False}
    assert thread["quality"]["geo_flags"] == {"unresolved_country_code": False}
    assert thread["quality"]["entity_flags"] == {"raw_entity_field_untyped": False}


def test_assemble_dynamic_thread_does_not_duplicate_country_codes_as_names():
    row = {
        "id": 17,
        "identity_key": "dyn-17",
        "label": "Infrastructure and Public Services",
        "agg_n_signals": 350,
        "changed_10h": 25,
        "noise_rate": 0.1938,
        "mean_cohesion": 0.94,
        "first_seen": None,
        "top_country_codes": ["ID", "BR", "CA"],
    }

    thread = assemble_dynamic_thread(row, [])

    assert thread["top_countries"] == ["ID", "BR", "CA"]
    assert thread["top_country_names"] == []
    assert "IDID" not in "".join(
        f"{code}{name}" for code, name in zip(
            thread["top_countries"], thread["top_country_names"], strict=False
        )
    )


def test_trend_label_classifies_volume_delta():
    from app.services.thread_intelligence import _trend_label
    assert _trend_label(0, 100) == "stable"
    assert _trend_label(10, 100) == "surging"  # 10% jump
    assert _trend_label(-20, 100) == "fading"
    assert _trend_label(2, 1000) == "stable"  # 0.2% noise
    assert _trend_label(100, 0) == "stable"  # divide-by-zero guard


def test_why_now_reads_as_net_change_not_gross_count():
    """#214: changed_10h is a NET delta vs the prior 10h, not a count of new
    signals. The copy must not say "N more signals" (which a reader compares
    against the window signal_count and reads as a contradiction)."""
    from app.services.thread_intelligence import _why_now

    up = _why_now(47, ["NG", "PE"])
    assert up == "Up 47 vs the prior 10h (net new coverage), concentrated in Nigeria and Peru."
    # It must NOT use the old absolute phrasing.
    assert "more signals" not in up

    down = _why_now(-12, ["FR"])
    assert down == "Down 12 vs the prior 10h (coverage cooling), concentrated in France."
    assert "fewer signals" not in down

    flat = _why_now(0, [])
    assert flat == "Signal volume is steady vs the prior 10h, concentrated in multiple regions."


def test_why_now_honest_when_delta_exceeds_window_total():
    """#214 core case: a thread served over a <20h window can have a 10h delta
    (+53) that exceeds its window signal_count (28). The why_now line must
    stay reconcilable — it frames +53 as movement vs the PRIOR 10h, never as
    "53 more signals" than the 28 the thread contains."""
    from app.services.thread_intelligence import _why_now

    line = _why_now(53, ["FR"])
    assert "vs the prior 10h" in line
    assert "more signals" not in line
    # The number is presented as movement, not as an absolute pool size.
    assert line.startswith("Up 53 vs the prior 10h")


def test_movement_label_is_self_describing():
    """#214: the short chip must carry "vs prior 10h" so it never reads as a
    gross count compared against signal_count."""
    from app.services.thread_intelligence import _movement_label

    assert _movement_label(53) == "+53 vs prior 10h"
    assert _movement_label(-12) == "-12 vs prior 10h"
    assert _movement_label(0) == "flat vs prior 10h"
    # Emergent path uses a snapshot period instead of a strict 10h window.
    assert _movement_label(8, period="prior snapshot") == "+8 vs prior snapshot"


def test_threads_sql_exposes_enriched_fields():
    """M3a additions: parent_domain, first_seen, top_entities, hourly_timeline
    must be SELECTed so the frontend NarrativeThreads card has parity with
    the legacy /api/v2/narratives shape."""
    assert "parent_domain" in THREADS_SQL
    assert "first_seen" in THREADS_SQL
    assert "top_entities" in THREADS_SQL
    assert "hourly_timeline" in THREADS_SQL
    assert "entity_lists" in THREADS_SQL
    assert "timeline_base" in THREADS_SQL
    # Performance: PK guarantees uniqueness within (topic, model_version)
    # group, so COUNT(*) replaces COUNT(DISTINCT signal_id) in topic_agg.
    # related_counts intentionally keeps DISTINCT because it joins back to
    # signal_topic_assignments and may see the same signal twice.
    assert "COUNT(*)::int AS signal_count" in THREADS_SQL


def test_threads_sql_exposes_method_counts_for_quality_metadata():
    assert "sta.evidence" in THREADS_SQL
    assert "evidence->>'lex_count'" in THREADS_SQL
    assert "evidence->>'theme_hits'" in THREADS_SQL
    assert "ta.lex_count" in THREADS_SQL
    assert "ta.theme_count" in THREADS_SQL


def test_threads_sql_downranks_thin_threads_before_velocity_sort():
    """Thin topics should remain available but not lead Narrative Threads just
    because their 10h delta is high."""
    assert "ta.signal_count >= 50" in THREADS_SQL
    assert "(ta.lex_count::float / NULLIF(ta.signal_count, 0)) >= 0.30" in THREADS_SQL
    assert "ta.changed_10h DESC" in THREADS_SQL


def test_threads_sql_uses_assignments_and_atlas_topics():
    assert "signal_topic_assignments" in THREADS_SQL
    assert "atlas_topics" in THREADS_SQL
    assert "model_version = 'theme-hint-lex-v2'" in THREADS_SQL
    assert "assigned_at >= NOW() - ($1::int * INTERVAL '1 hour')" in THREADS_SQL
    assert "LIMIT $2" in THREADS_SQL


def test_evidence_sql_deduplicates_syndicated_headlines():
    assert "DISTINCT ON (LOWER(s.headline))" in THREAD_EVIDENCE_SQL
    assert "COUNT(*) OVER (PARTITION BY LOWER(s.headline))" in THREAD_EVIDENCE_SQL
    assert "syndication_count" in THREAD_EVIDENCE_SQL
    assert "ORDER BY confidence DESC, timestamp DESC" in THREAD_EVIDENCE_SQL


def test_evidence_role_classifies_by_syndication_count():
    assert evidence_role(1) == "representative"
    assert evidence_role(2) == "repeated"
    assert evidence_role(4) == "repeated"
    assert evidence_role(5) == "syndicated"
    assert evidence_role(25) == "syndicated"


def test_fetch_threads_accepts_external_connection():
    """Milestone 2: briefing reuses its open connection by passing conn=...
    Without this, every briefing request would acquire a second pool
    connection just for the threads section."""
    sig = inspect.signature(fetch_threads)
    assert "conn" in sig.parameters
    assert sig.parameters["conn"].default is None


def test_fetch_threads_uses_supplied_connection_without_pool():
    """When conn is supplied, fetch_threads must NOT touch db.pool."""

    class FakeConn:
        def __init__(self) -> None:
            self.fetch_calls: list[tuple] = []

        async def fetch(self, query, *args, **kwargs):
            self.fetch_calls.append((query, args, kwargs))
            return []

    fake = FakeConn()
    original_pool = getattr(thread_intelligence.db, "pool", None)
    thread_intelligence.db.pool = None  # prove no pool access
    try:
        result = asyncio.run(
            fetch_threads(hours=12, limit=5, conn=fake)
        )
    finally:
        thread_intelligence.db.pool = original_pool

    assert result == []
    assert len(fake.fetch_calls) == 1
    args = fake.fetch_calls[0][1]
    assert args[0] == 12  # hours
    assert args[1] == 5  # limit


def test_serialize_evidence_includes_syndication_metadata():
    row = {
        "id": 42,
        "headline": "Russia launches strikes on Kyiv",
        "source_name": "reuters.com",
        "source_url": "https://reuters.com/x",
        "country_code": "UA",
        "country_name": "Ukraine",
        "timestamp": None,
        "nlp_sentiment": -0.6,
        "confidence": 0.95,
        "syndication_count": 25,
    }
    serialized = _serialize_evidence(row)
    assert serialized["syndication_count"] == 25
    assert serialized["evidence_role"] == "syndicated"
    assert serialized["country_code"] == "UA"


# --- atlas-fill evidence enrichment (briefing LIST path regression) ---------


def _evidence_row(headline: str) -> dict:
    return {
        "id": 1,
        "headline": headline,
        "snippet": None,
        "source_name": "reuters.com",
        "source_url": "https://reuters.com/x",
        "country_code": "UA",
        "country_name": "Ukraine",
        "timestamp": None,
        "nlp_sentiment": -0.5,
        "confidence": 0.9,
        "syndication_count": 3,
    }


class _RecordingConn:
    """Returns a fixed evidence batch and records every fetch() it sees."""

    def __init__(self, rows):
        self._rows = rows
        self.calls: list[tuple] = []

    async def fetch(self, query, *args, **kwargs):
        self.calls.append((query, args, kwargs))
        return self._rows


def test_attach_atlas_evidence_enriches_evidenceless_atlas_thread():
    """Regression: after unified ranking an atlas-fill thread can lead the
    briefing but carries no list-level evidence. The LIST path must backfill
    it from THREAD_EVIDENCE_SQL so the lead shows headlines."""
    thread = {
        "thread_id": "heat-public-health--gb-fr",
        "anchor_topics": ["heat-public-health"],
        "top_countries": ["GB", "FR"],
        "evidence_samples": [],
    }
    conn = _RecordingConn([_evidence_row("Heatwave grips Britain")])

    asyncio.run(_attach_atlas_evidence(conn, [thread], hours=24))

    assert len(thread["evidence_samples"]) == 1
    assert thread["evidence_samples"][0]["headline"] == "Heatwave grips Britain"
    # Bounded: exactly one query, using THREAD_EVIDENCE_SQL with the thread's
    # slug + countries + a per-thread cap, guarded by a timeout.
    assert len(conn.calls) == 1
    query, args, kwargs = conn.calls[0]
    assert query == THREAD_EVIDENCE_SQL
    assert args[0] == 24  # hours
    assert args[1] == "heat-public-health"  # topic_slug from anchor_topics[0]
    assert args[2] == ["GB", "FR"]  # country codes
    assert isinstance(args[3], int) and args[3] > 0  # per-thread cap
    assert kwargs.get("timeout")  # never an unbounded query


def test_attach_atlas_evidence_skips_dynamic_and_already_enriched_threads():
    """Dynamic/emergent threads already carry evidence from their assembly
    paths; threads that already have samples must not be re-queried."""
    dynamic = {
        "thread_id": "dynamic-topic-7",
        "anchor_topics": ["whatever"],
        "evidence_samples": [],
    }
    emergent = {
        "thread_id": "emergent-cluster-3",
        "anchor_topics": ["cluster-3"],
        "evidence_samples": [],
    }
    already = {
        "thread_id": "atlas-x--us",
        "anchor_topics": ["atlas-x"],
        "evidence_samples": [{"headline": "kept"}],
    }
    conn = _RecordingConn([_evidence_row("should not appear")])

    asyncio.run(_attach_atlas_evidence(conn, [dynamic, emergent, already], hours=24))

    # No thread was queried.
    assert conn.calls == []
    assert dynamic["evidence_samples"] == []
    assert emergent["evidence_samples"] == []
    assert already["evidence_samples"] == [{"headline": "kept"}]


def test_attach_atlas_evidence_degrades_to_empty_on_query_failure():
    """A failed evidence query must never raise — the thread degrades to
    evidence_samples=[] and the briefing still ships."""

    class _BoomConn:
        async def fetch(self, *args, **kwargs):
            raise RuntimeError("statement timeout")

    thread = {
        "thread_id": "atlas-y--us",
        "anchor_topics": ["atlas-y"],
        "top_countries": ["US"],
        "evidence_samples": [],
    }

    # Must not raise.
    asyncio.run(_attach_atlas_evidence(_BoomConn(), [thread], hours=24))
    assert thread["evidence_samples"] == []


def test_attach_atlas_evidence_is_bounded_to_top_n():
    """N+1 guard: only the first enrich_top_n atlas threads get a query."""
    threads = [
        {
            "thread_id": f"atlas-{i}--us",
            "anchor_topics": [f"atlas-{i}"],
            "top_countries": ["US"],
            "evidence_samples": [],
        }
        for i in range(15)
    ]
    conn = _RecordingConn([_evidence_row("h")])

    asyncio.run(
        _attach_atlas_evidence(conn, threads, hours=24, enrich_top_n=3)
    )

    assert len(conn.calls) == 3
    # First three enriched, rest left as empty lists.
    assert all(threads[i]["evidence_samples"] for i in range(3))
    assert all(threads[i]["evidence_samples"] == [] for i in range(3, 15))


def test_fetch_threads_exposes_attach_evidence_flag_defaulting_off():
    """The detail path (limit=1) attaches its own richer evidence; only the
    briefing opts in. Default must stay off to avoid changing other callers."""
    sig = inspect.signature(fetch_threads)
    assert "attach_evidence" in sig.parameters
    assert sig.parameters["attach_evidence"].default is False


# --- cross-language event de-duplication (serve-time, conservative) ----------

from app.services.thread_intelligence import (  # noqa: E402
    dedupe_same_event_threads,
    same_event,
)


def _thread(thread_id, label, codes, signal_count, changed_10h=0, **extra):
    base = {
        "thread_id": thread_id,
        "label": label,
        "top_countries": list(codes),
        "top_country_names": list(codes),
        "signal_count": signal_count,
        "changed_10h": changed_10h,
        "top_entities": [],
        "top_sources": [],
        "evidence_samples": [],
    }
    base.update(extra)
    return base


def test_same_event_merges_language_split_pair():
    """The reported bug: one earthquake, two language-split identities with
    different labels but the same country and a shared distinctive token."""
    en = _thread("dynamic-topic-1", "Venezuela Earthquakes", ["VE"], 80, 30)
    ru = _thread("dynamic-topic-2", "Venezuela Earthquake Disaster", ["VE"], 40, 10)
    assert same_event(en, ru) is True


def test_same_event_does_not_merge_distinct_same_country_stories():
    """Two genuinely different Venezuela stories share the country but NOT a
    distinctive event token — they must stay separate."""
    quake = _thread("dynamic-topic-1", "Venezuela Earthquakes", ["VE"], 80)
    election = _thread("dynamic-topic-3", "Venezuela Election Dispute", ["VE"], 60)
    assert same_event(quake, election) is False


def test_same_event_does_not_merge_same_topic_different_country():
    """Same subject word, different country = different real-world events."""
    ve_quake = _thread("dynamic-topic-1", "Venezuela Earthquakes", ["VE"], 80)
    tr_quake = _thread("dynamic-topic-4", "Turkey Earthquakes", ["TR"], 50)
    assert same_event(ve_quake, tr_quake) is False


def test_same_event_country_name_alone_is_insufficient():
    """A bare country-name overlap (no distinctive token) never merges."""
    a = _thread("a", "Venezuela News", ["VE"], 10)
    b = _thread("b", "Venezuela Update", ["VE"], 10)
    assert same_event(a, b) is False


def test_same_event_requires_a_primary_country():
    """Threads with no top country are undecidable and never merge."""
    a = _thread("a", "Earthquake Disaster", [], 10)
    b = _thread("b", "Earthquake Relief", [], 10)
    assert same_event(a, b) is False


def test_dedupe_collapses_pair_keeps_higher_ranked_and_sums_volume():
    """Ranked input order: the first (higher-ranked) thread survives and absorbs
    the later duplicate; disjoint language slices sum to the union volume."""
    en = _thread("dynamic-topic-1", "Venezuela Earthquakes", ["VE"], 80, 30)
    ru = _thread(
        "dynamic-topic-2",
        "Venezuela Earthquake Disaster",
        ["VE"],
        40,
        10,
        top_entities=["Nicolás Maduro"],
        evidence_samples=[{"headline": "Много жертв"}],
    )
    out = dedupe_same_event_threads([en, ru])

    assert len(out) == 1
    survivor = out[0]
    assert survivor["thread_id"] == "dynamic-topic-1"  # higher-ranked kept
    assert survivor["signal_count"] == 120  # 80 + 40 (disjoint coverage)
    assert survivor["changed_10h"] == 40  # 30 + 10
    assert survivor["merged_thread_ids"] == ["dynamic-topic-2"]  # not silent
    assert "Nicolás Maduro" in survivor["top_entities"]
    assert {"headline": "Много жертв"} in survivor["evidence_samples"]


def test_dedupe_leaves_distinct_threads_untouched():
    """The exact same-country pair that must NOT fuse survives as two rows, in
    the original (ranked) order."""
    quake = _thread("dynamic-topic-1", "Venezuela Earthquakes", ["VE"], 80)
    quake_ru = _thread("dynamic-topic-2", "Venezuela Earthquake Disaster", ["VE"], 40)
    election = _thread("dynamic-topic-3", "Venezuela Election Dispute", ["VE"], 60)

    out = dedupe_same_event_threads([quake, election, quake_ru])

    assert len(out) == 2  # the two quakes collapse; election stays
    labels = [t["label"] for t in out]
    assert "Venezuela Election Dispute" in labels
    assert out[0]["signal_count"] == 120  # quake survivor summed
    assert out[0]["label"] == "Venezuela Earthquakes"


def test_dedupe_is_order_stable_and_pure_on_no_duplicates():
    """No duplicates → identical list, order preserved, no mutation of inputs."""
    a = _thread("a", "Ukraine War Updates", ["UA", "RU"], 200)
    b = _thread("b", "Sudan Famine Crisis", ["SD"], 90)
    out = dedupe_same_event_threads([a, b])
    assert [t["thread_id"] for t in out] == ["a", "b"]
    assert a["signal_count"] == 200 and b["signal_count"] == 90
