"""LO QUE SUBE + EL VACÍO — the two measured Brief sections (T3.2).

Bars are FROZEN from the M0 measurement
(`docs/research/brief-daily/2026-08-12-m0-measurement.md`), so these tests are
the pre-registration made executable: every witness the measurement named is a
fixture here.

  (c) LO QUE SUBE   surprise >= 2.5 AND velocity > 0 AND volume >= 20   §c.4
  (b) EL VACÍO      multiplier >= 3.0 AND self_voice <= 0.20 AND
                    volume >= 20 AND known_origin_n >= 50               §b.4

The honesty rule the measurement made blocking (§b.2): `local_voice_ratio =
0.5` is a SENTINEL for `known_origin_n < 50`, not a ratio. A country whose
voice is unattributable is UNKNOWN — never "half local", never a candidate.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.services.brief_sections import (
    fetch_gap,
    fetch_rising,
    measure_reprint_concentration,
    pick_receipts,
    reprint_caveat,
    GAP_BAR,
    GAP_CONTRACT,
    RISING_BAR,
    RISING_CONTRACT,
    build_gap_payload,
    build_rising_payload,
    count_rising_exclusions,
    gap_ledger_rows,
    gap_prose,
    resolve_self_voice,
    rising_why_now,
    select_gap,
    select_rising,
)


# ── fixtures from the measured field ────────────────────────────────────────

def movement_row(topic_id: str, *, surprise: float, velocity: float,
                 volume: int, label: str | None = "A Story",
                 is_junk: bool = False, is_roundup: bool = False,
                 label_status: str | None = "entailed",
                 trend: str = "surging", category: str | None = "conflict"):
    return {
        "thread_id": topic_id,
        "label": label,
        "category": category,
        "is_junk": is_junk,
        "is_roundup": is_roundup,
        "label_status": label_status,
        "surprise": surprise,
        "velocity": velocity,
        "volume": volume,
        "trend": trend,
        "window_end": datetime(2026, 8, 12, 10, 54, tzinfo=timezone.utc),
    }


# The jalapeño witness, measured 2026-08-12: it clears `s>=2.0 & v>0` and
# `trend='surging'` and FAILS `s>=2.5`. M0 §c.4 picked 2.5 partly for this.
JALAPENO = movement_row("dynamic-topic-11877", surprise=2.2995, velocity=0.3956,
                        volume=86, label="Jalapeño Salmonella Outbreak")
# The two topics that actually cleared the bar on the measurement day.
RISING_TODAY = [
    movement_row("dynamic-topic-4257", surprise=3.067, velocity=0.057, volume=256,
                 label="Government Initiatives and Infrastructure"),
    movement_row("dynamic-topic-3839", surprise=2.567, velocity=0.406, volume=53,
                 label="Scaloni Future Doubts"),
]

# East Timor, 2026-08-12 — 11.2x its own baseline, 0 of 53 attributable voices
# domestic. The witness of the whole section.
TIMOR = {
    "country_code": "TL", "volume": 28, "baseline": 2.5, "baseline_days": 6,
    "multiplier": 11.2, "domestic_n": 0, "known_origin_n": 53, "total_n": 60,
}


# ── (c) LO QUE SUBE ─────────────────────────────────────────────────────────

def test_rising_bar_is_the_frozen_m0_bar():
    assert RISING_BAR["surprise_min"] == 2.5
    assert RISING_BAR["velocity_min_exclusive"] == 0.0
    assert RISING_BAR["volume_min"] == 20


def test_rising_selects_by_surprise_descending():
    picked = select_rising(RISING_TODAY[::-1])
    assert [row["thread_id"] for row in picked] == [
        "dynamic-topic-4257", "dynamic-topic-3839",
    ]


def test_rising_excludes_the_jalapeno_witness():
    """G-JALAPEÑO's sibling: the wire/service recall is not the day's rising news."""
    assert select_rising([JALAPENO, *RISING_TODAY]) == select_rising(RISING_TODAY)
    assert all(row["thread_id"] != "dynamic-topic-11877"
               for row in select_rising([JALAPENO, *RISING_TODAY]))


@pytest.mark.parametrize("row", [
    movement_row("dynamic-topic-1", surprise=2.49, velocity=0.5, volume=100),
    movement_row("dynamic-topic-2", surprise=3.0, velocity=0.0, volume=100),
    movement_row("dynamic-topic-3", surprise=3.0, velocity=-0.1, volume=100),
    movement_row("dynamic-topic-4", surprise=3.0, velocity=0.5, volume=19),
])
def test_rising_rejects_everything_below_the_bar(row):
    assert select_rising([row]) == []


def test_rising_drops_unpresentable_stories_but_never_loosens_the_bar():
    """A story with no name has no headline; junk/roundups are not 'rising news'.

    These are PRESENTABILITY filters applied on top of the frozen bar, never
    a relaxation of it — the seal takes the same position on unlabelled
    candidates (daily_edition.DailyCandidate.label is nullable by design).
    """
    unnamed = movement_row("dynamic-topic-5", surprise=4.0, velocity=1.0,
                           volume=99, label=None)
    junk = movement_row("dynamic-topic-6", surprise=4.0, velocity=1.0,
                        volume=99, is_junk=True)
    roundup = movement_row("dynamic-topic-7", surprise=4.0, velocity=1.0,
                           volume=99, is_roundup=True)
    assert select_rising([unnamed, junk, roundup]) == []


def test_rising_refuses_a_topic_the_label_court_ruled_unnameable():
    """Measured 2026-08-12: dt-4257 cleared the bar carrying `too_broad` — the
    court's verdict that no single label describes it — and its receipts were an
    Argentine supermarket launch and a drawing class. A headline over that is a
    false claim, so it is dropped and COUNTED."""
    fusion = movement_row("dynamic-topic-4257", surprise=3.067, velocity=0.057,
                          volume=256, label="Government Initiatives and Infrastructure",
                          label_status="too_broad")
    assert select_rising([fusion]) == []
    assert count_rising_exclusions([fusion]) == {"label_court_too_broad": 1}


def test_rising_marks_a_contested_label_instead_of_hiding_it():
    """`failed`/`partial` are marked, not hidden — the standing project stance
    (the LABEL UNDER REVIEW chip), so the verdict rides in the item."""
    contested = movement_row("dynamic-topic-3839", surprise=2.567, velocity=0.406,
                             volume=53, label="Scaloni Future Doubts",
                             label_status="failed")
    picked = select_rising([contested])
    assert len(picked) == 1
    assert picked[0]["label_status"] == "failed"


def test_rising_exclusions_only_count_stories_that_cleared_the_bar():
    below = movement_row("dynamic-topic-9", surprise=1.0, velocity=0.4,
                         volume=99, is_junk=True)
    assert count_rising_exclusions([below]) == {}


def test_rising_payload_carries_the_exclusion_ledger():
    payload = build_rising_payload([], candidates=1,
                                   excluded={"label_court_too_broad": 1})
    assert payload["excluded_after_bar"] == {"label_court_too_broad": 1}


def test_rising_caps_at_three_items():
    many = [
        movement_row(f"dynamic-topic-{i}", surprise=3.0 + i, velocity=0.4, volume=50)
        for i in range(6)
    ]
    assert len(select_rising(many)) == 3


def test_rising_why_now_is_a_template_over_measured_fields():
    line = rising_why_now(surprise=2.567, velocity=0.406, volume=53)
    assert "2.6σ" in line
    assert "+0.41" in line
    # The Kalman state is log-volume per 6h step, NOT signals per hour: the
    # prose must never invent a per-hour rate it did not measure.
    assert "/h" not in line


def test_rising_payload_is_honest_when_nothing_clears():
    payload = build_rising_payload([], candidates=0)
    assert payload["contract"] == RISING_CONTRACT
    assert payload["items"] == []
    assert payload["status"] == "empty"
    assert payload["reason"] == "no_story_cleared_the_bar"
    assert payload["bar"]["surprise_min"] == 2.5


def test_rising_payload_serves_what_exists_below_the_asked_for_two():
    payload = build_rising_payload(select_rising([RISING_TODAY[1]]), candidates=1)
    assert len(payload["items"]) == 1
    assert payload["status"] == "partial"
    assert payload["reason"] == "fewer_than_two_cleared_the_bar"


def test_rising_payload_carries_receipts_and_the_velocity_basis():
    items = select_rising(RISING_TODAY)
    items[0]["receipts"] = [{"headline": "H", "source": "s.com", "url": "http://s"}]
    payload = build_rising_payload(items, candidates=2)
    assert payload["status"] == "ok"
    assert payload["items"][0]["receipts"][0]["source"] == "s.com"
    assert "6" in payload["bar"]["velocity_basis"]


def test_rising_payload_marks_a_story_whose_receipts_did_not_resolve():
    items = select_rising(RISING_TODAY)
    payload = build_rising_payload(items, candidates=2)
    assert payload["items"][0]["receipts"] == []
    assert payload["items"][0]["receipt_status"] == "unavailable"


# ── the sentinel (the blocking honesty fix of M0 §b.2) ──────────────────────

def test_self_voice_below_the_attribution_floor_is_unknown_not_a_ratio():
    value, status, reason = resolve_self_voice(domestic_n=3, known_origin_n=7)
    assert value is None
    assert status == "unknown"
    assert reason == "known_origin_below_50"


def test_self_voice_never_returns_the_half_local_sentinel():
    """`country_heat_v2.local_voice_ratio` answers 0.5 when it cannot judge.

    Five of the measurement day's top-ten anomalies carried it. This section
    computes the ratio from raw ownership counts precisely so that a country it
    cannot judge comes back `None`, never 0.5-as-fact.
    """
    for known in (0, 1, 25, 49):
        value, status, _ = resolve_self_voice(domestic_n=known // 2, known_origin_n=known)
        assert value is None and status == "unknown"


def test_self_voice_is_measured_at_and_above_the_floor():
    value, status, reason = resolve_self_voice(domestic_n=0, known_origin_n=53)
    assert value == 0.0
    assert status == "measured"
    assert reason is None
    value, status, _ = resolve_self_voice(domestic_n=13, known_origin_n=52)
    assert value == pytest.approx(0.25)
    assert status == "measured"


# ── (b) EL VACÍO ────────────────────────────────────────────────────────────

def test_gap_bar_is_the_frozen_m0_bar_and_declares_low_confidence():
    assert GAP_BAR["multiplier_min"] == 3.0
    assert GAP_BAR["self_voice_max"] == 0.20
    assert GAP_BAR["volume_min"] == 20
    assert GAP_BAR["known_origin_min"] == 50
    assert GAP_BAR["confidence"] == "provisional"
    # The cost guard is published, not hidden — a threshold nobody can see is a
    # silent filter.
    assert GAP_BAR["prefilter_max_daily_volume"] == 3000


def test_gap_picks_the_east_timor_witness():
    chosen, scored = select_gap([TIMOR])
    assert chosen is not None
    assert chosen["country_code"] == "TL"
    assert chosen["self_voice_ratio"] == 0.0
    assert chosen["self_voice_status"] == "measured"
    assert scored[0]["cleared"] is True


def test_gap_ranks_by_multiplier():
    other = {**TIMOR, "country_code": "ZW", "multiplier": 4.0, "volume": 105,
             "domestic_n": 4, "known_origin_n": 105}
    chosen, _ = select_gap([other, TIMOR])
    assert chosen["country_code"] == "TL"


def test_gap_never_chooses_a_country_whose_voice_is_unattributable():
    """The 0.5-sentinel class. Its self_voice is UNKNOWN, so it cannot clear a
    bar that asks for measured silence — and it is logged with its reason."""
    sentinel = {"country_code": "BW", "volume": 21, "baseline": 6.0,
                "baseline_days": 7, "multiplier": 3.5,
                "domestic_n": 6, "known_origin_n": 7, "total_n": 24}
    chosen, scored = select_gap([sentinel])
    assert chosen is None
    row = scored[0]
    assert row["cleared"] is False
    assert row["self_voice_ratio"] is None
    assert row["self_voice_status"] == "unknown"
    assert "known_origin" in row["failed"][0]


@pytest.mark.parametrize("override,expected_fail", [
    ({"multiplier": 2.9}, "multiplier"),
    ({"volume": 19}, "volume"),
    ({"domestic_n": 30}, "self_voice"),
])
def test_gap_rejects_each_arm_of_the_bar(override, expected_fail):
    chosen, scored = select_gap([{**TIMOR, **override}])
    assert chosen is None
    assert any(expected_fail in reason for reason in scored[0]["failed"])


def test_gap_prose_is_a_template_over_the_measured_numbers():
    chosen, _ = select_gap([TIMOR])
    line = gap_prose(chosen)
    assert "Timor-Leste" in line
    assert "11.2" in line          # the multiplier
    assert "28" in line            # the day's volume
    assert "53" in line            # attributable voices
    assert "none" in line.lower()  # 0 domestic, said in words


def test_gap_prose_counts_a_non_zero_domestic_voice_honestly():
    chosen, _ = select_gap([{**TIMOR, "domestic_n": 5}])
    assert "5 of the 53" in gap_prose(chosen)


def test_gap_payload_is_honest_when_no_country_clears():
    payload = build_gap_payload(None, [], day=date(2026, 8, 12), day_complete=True)
    assert payload["contract"] == GAP_CONTRACT
    assert payload["status"] == "empty"
    assert payload["reason"] == "no_country_cleared_the_bar"
    assert payload["country"] is None
    assert payload["confidence"] == "provisional"


def test_gap_payload_carries_the_partial_day_caveat():
    chosen, scored = select_gap([TIMOR])
    payload = build_gap_payload(chosen, scored, day=date(2026, 8, 12),
                                day_complete=False)
    assert payload["day_complete"] is False
    assert payload["measured"]["multiplier"] == 11.2
    assert payload["measured"]["known_origin_n"] == 53
    assert payload["measured"]["self_voice_ratio"] == 0.0
    assert payload["country"]["code"] == "TL"
    assert payload["country"]["name"] == "Timor-Leste"
    assert payload["prose"]


# ── the ledger (the only path to a validated bar — M0 §b.1) ─────────────────

def test_ledger_records_every_candidate_not_only_the_chosen_one():
    sentinel = {"country_code": "BW", "volume": 21, "baseline": 6.0,
                "baseline_days": 7, "multiplier": 3.5,
                "domestic_n": 6, "known_origin_n": 7, "total_n": 24}
    chosen, scored = select_gap([TIMOR, sentinel])
    rows = gap_ledger_rows(scored, chosen, day=date(2026, 8, 12), source="live")
    assert {row[1] for row in rows} == {"TL", "BW"}
    by_cc = {row[1]: row for row in rows}
    assert by_cc["TL"][8] is True     # chosen
    assert by_cc["BW"][8] is False
    assert by_cc["BW"][4] is None     # self_voice_ratio stays NULL, never 0.5
    assert by_cc["TL"][4] == 0.0


def test_ledger_carries_the_reprint_share_only_where_it_was_measured():
    chosen, scored = select_gap([TIMOR])
    chosen["top_reprint_share"] = 0.917
    rows = gap_ledger_rows(scored, chosen, day=date(2026, 8, 12), source="live")
    assert rows[0][13] == 0.917
    # An unmeasured candidate logs NULL — "not measured", never "not syndicated".
    chosen2, scored2 = select_gap([TIMOR])
    assert gap_ledger_rows(scored2, chosen2, day=date(2026, 8, 12),
                           source="live")[0][13] is None


def test_ledger_is_written_even_when_nothing_clears_the_bar():
    """Two weeks of near-misses is exactly what re-derives the bar."""
    near = {**TIMOR, "multiplier": 2.4}
    chosen, scored = select_gap([near])
    rows = gap_ledger_rows(scored, chosen, day=date(2026, 8, 12), source="seal")
    assert len(rows) == 1
    assert rows[0][8] is False
    assert rows[0][9] == "seal"


# ── receipts: K receipts must be K stories ──────────────────────────────────

def _receipt(headline: str, source: str, when_hour: int = 12):
    return {"id": abs(hash((headline, source))) % 10**7, "headline": headline,
            "source_name": source, "source_url": f"http://{source}/x",
            "source_lang": "en", "source_origin_country": "AU",
            "timestamp": datetime(2026, 8, 12, when_hour, tzinfo=timezone.utc)}


# Measured on the first live run of EL VACÍO: the day's three outlet-distinct
# Timor-Leste receipts were ONE Australian wire piece under three mastheads.
WIRE_FAMILY = [
    _receipt("All-women East Timorese delegation welcomed to Canberra",
             "gleninnesexaminer.com.au", 14),
    _receipt("All-women East Timorese delegation welcomed to Canberra",
             "bendigoadvertiser.com.au", 13),
    _receipt("All-women East Timorese delegation welcomed to Canberra",
             "areanews.com.au", 12),
]


def test_receipts_fold_one_wire_piece_under_many_mastheads():
    picked = pick_receipts(WIRE_FAMILY, k=3)
    assert len(picked) == 1
    assert picked[0]["source"] == "gleninnesexaminer.com.au"


def test_receipts_keep_genuinely_different_stories():
    rows = [
        *WIRE_FAMILY,
        _receipt("CNC Now Has a Modern Archive Centre", "thediliweekly.com", 4),
        _receipt("Polisi Segera Tetapkan Tersangka Kasus Dugaan Rudapaksa",
                 "tribunnews.com", 11),
    ]
    picked = pick_receipts(rows, k=3)
    assert len(picked) == 3
    assert {row["source"] for row in picked} == {
        "gleninnesexaminer.com.au", "thediliweekly.com", "tribunnews.com"}


def test_receipts_serialize_the_fields_a_reader_needs():
    picked = pick_receipts(WIRE_FAMILY, k=1)[0]
    assert picked["url"].startswith("http")
    assert picked["origin_country"] == "AU"
    assert picked["timestamp"] == "2026-08-12T14:00:00+00:00"


def test_receipts_drop_rows_with_no_usable_headline():
    assert pick_receipts([_receipt("", "a.com"), _receipt("   ", "b.com")]) == []


def test_reprint_concentration_names_the_wire_family():
    other = _receipt("CNC Now Has a Modern Archive Centre", "thediliweekly.com", 4)
    measured = measure_reprint_concentration([*WIRE_FAMILY, other], scan_limit=60)
    assert measured["outlets_scanned"] == 4
    assert measured["distinct_stories"] == 2
    assert measured["top_story_outlets"] == 3
    assert measured["share_of_scanned_outlets"] == 0.75
    assert measured["scan_truncated"] is False


def test_reprint_concentration_flags_a_truncated_scan_as_a_floor():
    measured = measure_reprint_concentration(WIRE_FAMILY, scan_limit=3)
    assert measured["scan_truncated"] is True
    assert "at least" in reprint_caveat(measured)


def test_reprint_caveat_stays_silent_on_genuinely_plural_coverage():
    plural = [_receipt(f"Story number {i}", f"outlet{i}.com") for i in range(6)]
    measured = measure_reprint_concentration(plural, scan_limit=60)
    assert measured["top_story_outlets"] == 1
    assert reprint_caveat(measured) is None
    assert reprint_caveat(None) is None


def test_gap_payload_discloses_reprint_concentration_but_never_vetoes_on_it():
    """The frozen bar has no syndication arm; this build does not invent one —
    it measures the concentration and says so beside the finding."""
    chosen, scored = select_gap([TIMOR])
    concentration = measure_reprint_concentration(WIRE_FAMILY, scan_limit=60)
    payload = build_gap_payload(chosen, scored, day=date(2026, 8, 12),
                                day_complete=True, concentration=concentration)
    assert payload["status"] == "ok"
    assert payload["measured"]["reprint_concentration"]["top_story_outlets"] == 3
    assert "3 of the 3 outlets" in payload["caveat"]


# ── the DB path (shared by the live briefing and the seal) ──────────────────

class FakeConn:
    """SQL-aware asyncpg stub: answers by which statement was asked."""

    def __init__(self, *, movement=None, evidence=None, fallback=None,
                 volume=None, voice=None, receipts=None, fail=()):
        self.movement = movement or []
        self.evidence = evidence or []
        self.fallback = fallback or []
        self.volume = volume or []
        self.voice = voice or []
        self.receipts = receipts or []
        self.fail = set(fail)
        self.calls: list[str] = []
        self.executemany_calls: list[tuple] = []

    async def fetch(self, sql, *args, **kwargs):
        from app.services import brief_sections as bs
        from app.services.daily_publication import _DAILY_EVIDENCE_SQL
        which = {
            bs.RISING_MOVEMENT_SQL: "movement",
            _DAILY_EVIDENCE_SQL: "evidence",
            bs.RISING_RECEIPTS_FALLBACK_SQL: "fallback",
            bs.GAP_VOLUME_SQL: "volume",
            bs.GAP_VOICE_SQL: "voice",
            bs.GAP_RECEIPTS_SQL: "receipts",
        }[sql]
        self.calls.append(which)
        if which in self.fail:
            raise TimeoutError(which)
        return getattr(self, which)

    async def executemany(self, sql, rows, **kwargs):
        if "ledger" in self.fail:
            raise TimeoutError("ledger")
        self.executemany_calls.append((sql, list(rows)))


NOW = datetime(2026, 8, 12, 15, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_fetch_rising_serves_items_with_edition_receipts():
    conn = FakeConn(
        movement=RISING_TODAY,
        evidence=[
            {"topic_id": "dynamic-topic-4257", "id": 1, "headline": "One",
             "source_name": "a.com", "source_url": "http://a", "source_lang": "en",
             "source_origin_country": "US",
             "timestamp": datetime(2026, 8, 12, 9, tzinfo=timezone.utc)},
            {"topic_id": "dynamic-topic-3839", "id": 2, "headline": "Two",
             "source_name": "b.com", "source_url": "http://b", "source_lang": "es",
             "source_origin_country": "AR",
             "timestamp": datetime(2026, 8, 12, 8, tzinfo=timezone.utc)},
        ],
    )
    payload = await fetch_rising(conn, hours=24, window_end=NOW)
    assert payload["status"] == "ok"
    assert [item["thread_id"] for item in payload["items"]] == [
        "dynamic-topic-4257", "dynamic-topic-3839"]
    assert payload["items"][0]["receipts"][0]["headline"] == "One"
    assert payload["items"][0]["receipt_status"] == "ok"
    assert conn.calls == ["movement", "evidence"]


@pytest.mark.asyncio
async def test_fetch_rising_unions_the_two_membership_regimes_for_receipts():
    """Measured 2026-08-12: BOTH stories that cleared the bar had zero
    `v1-compat` receipts in-window and 187/40 fresh `unified-v2` ones. A
    consumer that picks one lane serves a numbered claim with no proof."""
    conn = FakeConn(
        movement=RISING_TODAY,
        evidence=[],                      # the v1-compat projection is stale
        fallback=[
            {"topic_id": "dynamic-topic-4257", "id": 3, "headline": "Fresh one",
             "source_name": "d.com", "source_url": "http://d", "source_lang": "en",
             "source_origin_country": "US",
             "timestamp": datetime(2026, 8, 12, 9, 45, tzinfo=timezone.utc)},
        ],
    )
    payload = await fetch_rising(conn, hours=24, window_end=NOW)
    assert conn.calls == ["movement", "evidence", "fallback"]
    first, second = payload["items"]
    assert first["receipts"][0]["headline"] == "Fresh one"
    assert first["receipt_basis"] == "unified_membership_fallback"
    # The story neither lane could serve stays honestly receipt-less.
    assert second["receipt_status"] == "unavailable"
    assert second["receipt_basis"] is None


@pytest.mark.asyncio
async def test_fetch_rising_does_not_reach_for_the_fallback_when_the_edition_answers():
    conn = FakeConn(
        movement=[RISING_TODAY[0]],
        evidence=[
            {"topic_id": "dynamic-topic-4257", "id": 1, "headline": "One",
             "source_name": "a.com", "source_url": "http://a", "source_lang": "en",
             "source_origin_country": "US",
             "timestamp": datetime(2026, 8, 12, 9, tzinfo=timezone.utc)},
        ],
    )
    payload = await fetch_rising(conn, hours=24, window_end=NOW)
    assert conn.calls == ["movement", "evidence"]
    assert payload["items"][0]["receipt_basis"] == "edition_evidence_v1_compat"


@pytest.mark.asyncio
async def test_fetch_rising_prefers_receipts_the_seal_already_fetched():
    """G-SELLO: inside the seal the receipts are already in hand — the section
    must not re-query for them."""
    conn = FakeConn(movement=[RISING_TODAY[1]])
    payload = await fetch_rising(
        conn, hours=24, window_end=NOW,
        receipts_by_thread={"dynamic-topic-3839": [
            {"id": 9, "headline": "Frozen", "source_name": "c.com",
             "source_url": "http://c", "source_lang": "en",
             "source_origin_country": None, "timestamp": None},
        ]},
    )
    assert payload["items"][0]["receipts"][0]["headline"] == "Frozen"
    assert conn.calls == ["movement"]


@pytest.mark.asyncio
async def test_fetch_rising_degrades_openly_when_movement_is_unreachable():
    payload = await fetch_rising(FakeConn(fail={"movement"}), window_end=NOW)
    assert payload["items"] == []
    assert payload["status"] == "unavailable"
    assert payload["reason"] == "movement_unavailable"


@pytest.mark.asyncio
async def test_fetch_rising_still_serves_when_only_receipts_fail():
    conn = FakeConn(movement=RISING_TODAY, fail={"evidence"})
    payload = await fetch_rising(conn, window_end=NOW)
    assert payload["status"] == "ok"
    assert payload["items"][0]["receipt_status"] == "unavailable"


def _volume_rows(today_tl: int = 28):
    days = [date(2026, 8, 5 + offset) for offset in range(8)]
    rows = []
    for day in days[:-1]:
        rows.append({"day": day, "country_code": "TL", "volume": 2})
        rows.append({"day": day, "country_code": "FR", "volume": 400})
    rows.append({"day": days[-1], "country_code": "TL", "volume": today_tl})
    rows.append({"day": days[-1], "country_code": "FR", "volume": 410})
    return rows


@pytest.mark.asyncio
async def test_fetch_gap_finds_the_witness_and_writes_the_ledger():
    conn = FakeConn(
        volume=_volume_rows(),
        voice=[{"country_code": "TL", "known_origin_n": 53, "domestic_n": 0,
                "total_n": 60}],
        receipts=[{"id": 7, "headline": "East Timorese delegation",
                   "source_name": "gleninnesexaminer.com.au",
                   "source_url": "http://x", "source_lang": "en",
                   "source_origin_country": "AU",
                   "timestamp": datetime(2026, 8, 12, 14, 45, tzinfo=timezone.utc)}],
    )
    payload = await fetch_gap(conn, window_end=NOW, computed_by="live")
    assert payload["status"] == "ok"
    assert payload["country"] == {"code": "TL", "name": "Timor-Leste"}
    assert payload["measured"]["multiplier"] == 14.0   # 28 / mean(2 x 7)
    assert payload["measured"]["self_voice_ratio"] == 0.0
    assert payload["measured"]["unattributed_n"] == 7
    assert payload["receipts"][0]["origin_country"] == "AU"
    assert payload["day_complete"] is False            # 15:00 UTC, partial day
    assert conn.calls == ["volume", "voice", "receipts"]
    ledger_rows = conn.executemany_calls[0][1]
    assert [row[1] for row in ledger_rows] == ["TL"]
    assert ledger_rows[0][8] is True


@pytest.mark.asyncio
async def test_fetch_gap_never_asks_the_voice_lane_about_a_quiet_field():
    """Nothing over 3x -> no narrow query, no ledger row, honest empty."""
    conn = FakeConn(volume=_volume_rows(today_tl=3))
    payload = await fetch_gap(conn, window_end=NOW)
    assert payload["status"] == "empty"
    assert payload["reason"] == "no_country_cleared_the_bar"
    assert conn.calls == ["volume"]
    assert conn.executemany_calls == []


@pytest.mark.asyncio
async def test_fetch_gap_refuses_to_report_silence_it_could_not_measure():
    """The silent-risk rule: no voice lane, no finding — an anomaly alone is
    not a blindspot."""
    conn = FakeConn(volume=_volume_rows(), fail={"voice"})
    payload = await fetch_gap(conn, window_end=NOW)
    assert payload["status"] == "unavailable"
    assert payload["reason"] == "voice_lane_unavailable"
    assert payload["country"] is None


@pytest.mark.asyncio
async def test_fetch_gap_logs_the_near_miss_that_the_sentinel_class_produces():
    conn = FakeConn(
        volume=_volume_rows(),
        voice=[{"country_code": "TL", "known_origin_n": 7, "domestic_n": 3,
                "total_n": 30}],
    )
    payload = await fetch_gap(conn, window_end=NOW)
    assert payload["status"] == "empty"
    row = conn.executemany_calls[0][1][0]
    assert row[1] == "TL"
    assert row[4] is None                  # self_voice_ratio NULL, not 0.5
    assert row[5] == "unknown"
    assert row[8] is False
    assert "known_origin" in row[10]


@pytest.mark.asyncio
async def test_fetch_gap_ships_the_section_even_if_the_ledger_write_fails():
    conn = FakeConn(
        volume=_volume_rows(),
        voice=[{"country_code": "TL", "known_origin_n": 53, "domestic_n": 0,
                "total_n": 60}],
        receipts=[],
        fail={"ledger"},
    )
    payload = await fetch_gap(conn, window_end=NOW)
    assert payload["status"] == "ok"
