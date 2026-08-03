"""Pure-part tests for the condemnation-rate instrument
(`scripts/measure_condemnation_rate.py`) — the pool-health alarm clock frozen
by `docs/superpowers/specs/2026-08-03-condemnation-trigger-preregistration.md`.

No DB, no network: seed derivation, verdict parsing, the conservative
condemned-counting rule, the frozen 15% trigger + 15-25% zone-of-interest
logic, and ledger-line construction/reading."""
from __future__ import annotations

import datetime as dt
import json

from scripts.measure_condemnation_rate import (
    SAMPLE_N,
    TRIGGER_RATE,
    append_ledger,
    condemned_for_ledger,
    default_seed,
    ledger_line,
    parse_condemnation_verdict,
    read_previous_rate,
    trigger_status,
)


# ------------------------------------------------------------------ constants
def test_frozen_constants_match_preregistration():
    assert SAMPLE_N == 60
    assert TRIGGER_RATE == 0.15


# ------------------------------------------------------------------ seed
def test_default_seed_derives_from_date():
    assert default_seed(dt.date(2026, 8, 3)) == 20260803


def test_default_seed_changes_with_date():
    assert default_seed(dt.date(2026, 8, 6)) != default_seed(dt.date(2026, 8, 3))


# ------------------------------------------------------------------ parsing
def test_parse_verdict_json_supported():
    v, r = parse_condemnation_verdict(
        '{"verdict": "SUPPORTED", "reason": "matches \\"Berlin Pride\\""}')
    assert v == "supported"
    assert "Berlin Pride" in r


def test_parse_verdict_json_condemned_with_fences():
    v, _ = parse_condemnation_verdict(
        '```json\n{"verdict": "CONDEMNED", "reason": "grab-bag"}\n```')
    assert v == "condemned"


def test_parse_verdict_bare_word_fallback():
    v, _ = parse_condemnation_verdict("The identity is clearly CONDEMNED here.")
    assert v == "condemned"


def test_parse_verdict_unparseable():
    v, r = parse_condemnation_verdict("garbage with no verdict word")
    assert v == "unparseable"
    assert r.startswith("garbage")


# ------------------------------------------------------------------ counting
def test_only_grounded_supported_clears():
    # the frozen conservative rule: a judgment that cannot prove health
    # never fires the trigger early
    assert condemned_for_ledger("supported", grounded=True) is False
    assert condemned_for_ledger("supported", grounded=False) is True
    assert condemned_for_ledger("condemned", grounded=True) is True
    assert condemned_for_ledger("condemned", grounded=False) is True
    assert condemned_for_ledger("unparseable", grounded=False) is True


# ------------------------------------------------------------------ trigger
def test_trigger_fires_at_or_below_15():
    assert trigger_status(0.15, None) == "TRIGGER: re-run gates 8-9"
    assert trigger_status(0.0333, 0.39) == "TRIGGER: re-run gates 8-9"


def test_trigger_does_not_fire_above_15():
    assert "TRIGGER" not in trigger_status(0.1501, None)
    assert "TRIGGER" not in trigger_status(0.39, 0.16)


def test_zone_of_interest_first_run_is_watch():
    s = trigger_status(0.20, 0.39)     # previous run was OUTSIDE the band
    assert "watch" in s
    assert "does NOT advance" not in s


def test_zone_of_interest_two_consecutive_reports_trend_never_advances():
    s = trigger_status(0.20, 0.22)     # second consecutive run inside 15-25%
    assert "ZONE OF INTEREST" in s
    assert "does NOT advance" in s
    assert "TRIGGER: re-run" not in s


def test_above_zone_is_no_trigger():
    assert trigger_status(0.39, 0.40) == "no trigger"


# ------------------------------------------------------------------ ledger
def test_ledger_line_shape_and_rate():
    line = ledger_line(date="2026-08-03", seed=42, n=31,
                       condemned_ids=["b", "a"], protocol="p",
                       baseline=True)
    assert line["rate"] == round(2 / 31, 4)
    assert line["condemned"] == 2
    assert line["condemned_ids"] == ["a", "b"]      # sorted, deterministic
    assert line["baseline"] is True
    assert line["protocol"] == "p"


def test_ledger_line_omits_baseline_by_default():
    line = ledger_line(date="2026-08-06", seed=20260806, n=60,
                       condemned_ids=[], protocol="p")
    assert "baseline" not in line
    assert line["rate"] == 0.0


def test_ledger_append_and_read_previous_rate(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    assert read_previous_rate(ledger) is None
    append_ledger(ledger, ledger_line(date="d1", seed=1, n=60,
                                      condemned_ids=["x"] * 12, protocol="p"))
    append_ledger(ledger, ledger_line(date="d2", seed=2, n=60,
                                      condemned_ids=["y"] * 9, protocol="p"))
    assert read_previous_rate(ledger) == round(9 / 60, 4)
    lines = ledger.read_text().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["condemned"] == 12


def test_read_previous_rate_tolerates_corrupt_tail(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text('{"rate": 0.2}\nnot-json\n')
    assert read_previous_rate(ledger) is None
