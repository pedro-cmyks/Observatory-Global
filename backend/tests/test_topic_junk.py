"""Locks the content-based junk classifier + the must-survive guard list.

The guard cases are the real 2026-07-09 prod topics Pedro named as must-survive
(NATO / Ebola / Ukraine / Heatwave / real World Cup / elections) plus the real
junk grab-bags that were eating ~38% of assigned coverage. If a change to
topic_junk starts flagging a guard case or stops flagging a known grab-bag, these
fail.
"""
from scripts.topic_junk import (
    DUMP_MAX_SOURCES,
    DUMP_MIN_MEMBERS,
    classify_topic_junk,
)


# --- junk that MUST be flagged (measured on prod 2026-07-09) ---

def test_grabbag_category_flagged():
    assert classify_topic_junk("Local & Community",
                               "Full list of Welsh beaches crowned best in UK",
                               2021, 44)
    assert classify_topic_junk("Celebrity & Sports Drama",
                               "Celebrity Emotional Statements", 1456, 22)
    assert classify_topic_junk("Other", "CentralAsia roundup", 1529, 16)


def test_mixed_prefix_flagged_even_in_real_category():
    # "Mixed:" is the labeler's own grab-bag marker; catch it even when the typer
    # filed it under a real category.
    r = classify_topic_junk("Business & Markets", "Mixed: UK warnings and recalls", 402, 48)
    assert r and "listicle-label" in r


def test_listicle_labels_flagged():
    assert classify_topic_junk("Sports", "WM 2026 Live Streams", 219, 39)
    assert classify_topic_junk("Sports", "World Cup 2026 Match Schedules", 80, 37)
    assert classify_topic_junk("Celebrity & Entertainment",
                               "Who is Ser Torrhen Manderly? Dan Fogler's new House", 826, 45)


def test_feed_dump_flagged_in_legit_category():
    # few-source gravity wells the typer trusted (Indonesian antaranews dump,
    # Korean k-pop mislabeled "AI Policy", single-outlet festival feed).
    assert classify_topic_junk("Crime and Accidents", "Diduga Tenggelam di Sungai Musi", 1607, 5)
    assert classify_topic_junk("AI Industry and Policy", "통신3사 AI 경영", 1879, 7)
    assert classify_topic_junk("Cultural Events and Festivals", "Marcha para Jesus", 1222, 5)


# --- must-survive real stories (guard) ---

def test_guard_real_stories_survive():
    guard = [
        ("Armed conflict escalation", "NATO Summit in Ankara", 778, 12),
        ("Labor strike disruption", "DR Congo Ebola health workers strike over pay", 672, 47),
        ("Armed conflict escalation", "Ukraine War Updates", 589, 19),
        ("Armed conflict escalation", "US-Iran strikes on Bahrain and Kuwait", 524, 33),
        ("Heat and public health risk", "Heatwave Impacts and Disasters", 682, 24),
        ("World Cup 2026", "World Cup 2026 Results", 64, 56),
        ("World Cup 2026", "Morocco World Cup 2026", 52, 19),
        ("Election legitimacy dispute", "Marine Le Pen 2027 presidential bid", 284, 48),
        ("Corruption investigation", "Senegal Political Turmoil", 70, 46),
        # legit non-crisis news is NOT junk
        ("Politics & Governance", "Germany Policy Changes", 196, 19),
        ("Business & Markets", "Financial Market Movements", 198, 30),
    ]
    for cat, label, mem, nsrc in guard:
        assert classify_topic_junk(cat, label, mem, nsrc) is None, f"false-positive: {label}"


# --- boundary behaviour ---

def test_feed_dump_needs_both_size_and_few_sources():
    # small few-source story: NOT a dump (spares genuine regional news)
    assert classify_topic_junk("Crime and Accidents", "Local court ruling", 40, 3) is None
    # large but well-sourced: NOT a dump
    assert classify_topic_junk("Crime and Accidents", "Major event", 900, 30) is None
    # exactly at the floors
    assert classify_topic_junk("Crime and Accidents", "x", DUMP_MIN_MEMBERS, DUMP_MAX_SOURCES)
    assert classify_topic_junk("Crime and Accidents", "x", DUMP_MIN_MEMBERS - 1, DUMP_MAX_SOURCES) is None
    assert classify_topic_junk("Crime and Accidents", "x", DUMP_MIN_MEMBERS, DUMP_MAX_SOURCES + 1) is None


def test_missing_source_count_skips_dump_rule():
    # None distinct_sources: category/label still apply, dump rule skipped
    assert classify_topic_junk("Crime and Accidents", "plain headline", 5000, None) is None
    assert classify_topic_junk("Other", "plain headline", 5000, None)
