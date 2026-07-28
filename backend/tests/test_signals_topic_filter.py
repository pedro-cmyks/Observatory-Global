"""`topic=` filter on /api/v2/signals — the Eclipse/Shadow stream tabs (spec §6.4).

A signal row carries no topic linkage, so scoping the stream to a thread means
a semi-join through topic_members. Two things must hold and stay held:

1. **Scoping hygiene** — topic_members spans two membership regimes (v1-compat ‖
   unified-v2) and carries quarantined black-hole rows. Reading it unscoped
   double-counts; that exact class of bug cost a 4-day outage (2026-07-27). The
   scoping here is copied verbatim from routers/attention_eclipse.py.
2. **Honest empty** — a requested-but-unparseable scope must return nothing, not
   the global firehose relabelled "Eclipse".

Query-shape assertions are source-level, matching the house style of
test_signals_lane_contract.py / test_signals_query_bounded.py (these run with no
DB); parse_topic_filter is exercised directly as the pure unit it is.
"""
import re
from pathlib import Path

import pytest

from app.routers.signals import (
    _TOPIC_ASSIGNED_SLACK_H,
    _TOPIC_FILTER_MAX,
    _TOPIC_MEMBER_POOL,
    parse_topic_filter,
)

SRC = (Path(__file__).resolve().parents[1] / "app" / "routers" /
       "signals.py").read_text(encoding="utf-8")


def _topic_condition() -> str:
    """The topic_members subquery appended to the signals WHERE clause."""
    m = re.search(r'"id IN \(SELECT tm\.signal_id FROM topic_members tm "(.*?)\)\n',
                  SRC, re.S)
    assert m, "topic_members condition not found in signals.py"
    return m.group(0)


# --------------------------------------------------------------------------
# parse_topic_filter — the pure gate
# --------------------------------------------------------------------------

def test_absent_param_means_no_filter():
    """None (no param) is distinct from '' (asked, nothing valid)."""
    assert parse_topic_filter(None) is None


def test_parses_a_comma_separated_list():
    assert parse_topic_filter("dynamic-topic-8072,armed-conflict-escalation") == [
        "dynamic-topic-8072", "armed-conflict-escalation",
    ]


def test_trims_whitespace_and_drops_blanks():
    assert parse_topic_filter(" a-topic , , b-topic ") == ["a-topic", "b-topic"]


def test_dedupes_preserving_order():
    assert parse_topic_filter("a,b,a,c,b") == ["a", "b", "c"]


@pytest.mark.parametrize("bad", [
    "'; DROP TABLE signals_v2; --",
    "topic id with spaces",
    "a/../b",
    "%",
    "-leading-dash",
    "x" * 65,
])
def test_rejects_malformed_ids(bad):
    assert parse_topic_filter(bad) == []


def test_keeps_the_good_ids_when_one_is_malformed():
    """A partial-garbage list narrows to what is valid; it never widens."""
    assert parse_topic_filter("dynamic-topic-1,bad id,slug-two") == [
        "dynamic-topic-1", "slug-two",
    ]


def test_empty_string_is_a_requested_but_empty_scope():
    """'' asked for a scope. Not None (= unfiltered) — the honest-empty case."""
    assert parse_topic_filter("") == []


def test_caps_the_id_list():
    ids = ",".join(f"topic-{i}" for i in range(50))
    out = parse_topic_filter(ids)
    assert len(out) == _TOPIC_FILTER_MAX
    assert out[0] == "topic-0"          # most-significant first, truncated at the tail


def test_cap_is_configurable_per_call():
    assert parse_topic_filter("a,b,c,d", max_ids=2) == ["a", "b"]


# --------------------------------------------------------------------------
# Query shape — scoping hygiene + bounding
# --------------------------------------------------------------------------

def test_topic_condition_scopes_role_engine_and_quarantine():
    """The 2026-07-27 guard: an unscoped topic_members read double-counts."""
    cond = _topic_condition()
    assert "tm.role = 'evidence'" in cond
    assert "tm.engine_version = 'v1-compat'" in cond
    assert "tm.quarantined IS NOT TRUE" in cond


def test_topic_condition_drives_from_topic_members_not_a_correlated_exists():
    """MEASURED: the correlated-EXISTS shape makes the planner scan the
    timestamp index and probe topic_members per row — 528K buffers / 8s. The
    materialised member set is 10K buffers / 1.6s warm for the same answer."""
    cond = _topic_condition()
    assert "id IN (SELECT tm.signal_id FROM topic_members tm" in cond
    # the correlated form, in the emitted condition (prose about it is fine)
    assert "signals_v2.id" not in cond


def test_topic_member_set_is_hard_bounded():
    cond = _topic_condition()
    assert "ORDER BY tm.assigned_at DESC LIMIT {_TOPIC_MEMBER_POOL}" in cond
    assert _TOPIC_MEMBER_POOL <= 10000, "member pool must stay a real ceiling"


def test_member_window_is_widened_past_the_signal_window():
    """assigned_at can PRECEDE the signal timestamp (measured -2.45h worst
    case), so the member window must be wider than `hours` or edge-of-window
    signals silently vanish."""
    cond = _topic_condition()
    assert "tm.assigned_at > NOW() -" in cond
    assert "params.append(hours + _TOPIC_ASSIGNED_SLACK_H)" in SRC
    assert _TOPIC_ASSIGNED_SLACK_H >= 3


def test_topic_ids_are_bound_never_interpolated():
    cond = _topic_condition()
    assert "tm.topic_id = ANY(${p_topics})" in cond
    assert "params.append(topic_ids)" in SRC


def test_requested_but_empty_scope_returns_nothing():
    assert 'conditions.append("FALSE")' in SRC


# --------------------------------------------------------------------------
# Contract
# --------------------------------------------------------------------------

def test_topic_is_an_optional_query_param():
    assert "topic: Optional[str] = Query(None" in SRC


def test_topic_scope_suppresses_the_global_own_voice_interleave():
    """Own-voice interleaving injects signals from OUTSIDE the requested scope."""
    m = re.search(r"is_global = not \((.*?)\)\n", SRC, re.S)
    assert m, "is_global guard not found"
    assert "topic_ids is not None" in m.group(1)


def test_topic_filter_echo_is_additive():
    """Absent key when unfiltered => the existing contract is untouched."""
    assert 'if topic_ids is not None:\n            payload["topic_filter"] = topic_ids' in SRC


def test_unfiltered_response_keys_unchanged():
    m = re.search(r"payload = \{(.*?)\n        \}", SRC, re.S)
    assert m, "response payload not found"
    body = m.group(1)
    assert '"count"' in body and '"velocity"' in body and '"signals"' in body
    assert "topic_filter" not in body, "topic_filter must be added conditionally"
