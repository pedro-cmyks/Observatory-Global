"""Relabel pure logic: generated-label cleaning + no-op detection."""
import json
from datetime import datetime, timedelta, timezone

import scripts.relabel_court_failed as _rcf
from scripts.relabel_court_failed import (
    clean_generated_label, is_label_unchanged,
    _relabel_attempts_last_n_days, _RELABEL_CANDIDATES_SQL,
    _DEFAULT_COOLDOWN_HOURS, _DEFAULT_MAX_ATTEMPTS, _DEFAULT_ATTEMPTS_WINDOW_DAYS,
)


def test_strips_quotes_and_label_prefix():
    assert clean_generated_label('"Label: Venezuela Earthquake Recovery Efforts."') == \
        "Venezuela Earthquake Recovery Efforts"


def test_rejects_placeholder_and_empty_and_extremes():
    assert clean_generated_label("(label failed)") is None
    assert clean_generated_label("") is None
    assert clean_generated_label("Short") is None
    assert clean_generated_label("x" * 120) is None


def test_plain_label_passes():
    assert clean_generated_label("Moldova Political Crisis Deepens") == \
        "Moldova Political Crisis Deepens"


# ---------------------------------------------------------------------------
# No-op relabel detection (GB2 incidental finding, 2026-07-29): the 15:38 pass
# cleared label_status on dt-8172/5549/8170 while writing back the byte-
# identical string that had just failed — the front page lost its court stamp
# with zero label change, and the next court pass re-failed the same string.
# A relabel equal to the current label (modulo whitespace/case) must be a
# NO-OP: keep the existing stamp, ledger reason='relabel_no_change'.
# ---------------------------------------------------------------------------

def test_byte_identical_witness_strings_are_unchanged():
    # the three 2026-07-29 15:38 witnesses, verbatim from the relabel ledger
    for lab in ("Wildfires in France and Spain Force Evacuations",       # dt-8172
                "EU Sanctions, US Arrests, and Defense Moves",           # dt-5549
                "Global heatwaves, wildfires, and power outages"):       # dt-8170
        assert is_label_unchanged(lab, lab)


def test_case_and_whitespace_differences_are_unchanged():
    assert is_label_unchanged("France Heatwave Alerts", "france heatwave alerts")
    assert is_label_unchanged("France  Heatwave\tAlerts", " France Heatwave Alerts ")


def test_real_rewrite_is_a_change():
    # dt-8070's Sites<->Facilities churn is a real text change — stamp reset stands
    assert not is_label_unchanged("Iran Strikes US Sites in Bahrain, Jordan",
                                  "Iran Strikes US Facilities in Bahrain, Jordan")
    assert not is_label_unchanged("France Heatwave Alerts",
                                  "Historic wildfires in France and Spain force evacuations")


def test_missing_old_label_is_a_change():
    assert not is_label_unchanged(None, "France Heatwave Alerts")
    assert not is_label_unchanged("", "France Heatwave Alerts")


# ---------------------------------------------------------------------------
# GB5 Class F livelock fix (2026-07-30, docs/research/label-court/
# 2026-07-29-gb5-blind-check.md): court judges NULL->failed, this script
# rewrites the label and resets ->NULL, court re-judges, ... 154 umbrella
# judgments over 43 rows in one day; dt-8222 judged 12 times; dt-8235 cycled
# 5 distinct labels across 7 judgments. Two brakes: a 24h cooldown (SQL, via
# label_updated_at) and a 7-day/3-attempt cap (read from this script's own
# ledger files, so it survives a process restart).
# ---------------------------------------------------------------------------

def test_relabel_candidates_sql_has_cooldown_clause():
    sql = _RELABEL_CANDIDATES_SQL
    assert "label_updated_at IS NULL" in sql
    assert "label_updated_at < now() - $2::interval" in sql
    assert "label_status='failed'" in sql
    assert "LIMIT $1" in sql


def test_default_livelock_guard_constants():
    # frozen so a drive-by edit can't silently widen the guard
    assert _DEFAULT_COOLDOWN_HOURS == 24
    assert _DEFAULT_MAX_ATTEMPTS == 3
    assert _DEFAULT_ATTEMPTS_WINDOW_DAYS == 7


def _write_ledger(tmp_path, day, entries):
    led = tmp_path / f"{day.isoformat()}-relabel-ledger.jsonl"
    with led.open("a", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def test_relabel_attempts_counts_across_the_trailing_window(tmp_path, monkeypatch):
    monkeypatch.setattr(_rcf, "_LEDGER_DIR", tmp_path)
    now = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
    _write_ledger(tmp_path, now.date(), [
        {"topic_id": 8222, "old": "A", "new": "B", "at": now.isoformat()},
    ])
    _write_ledger(tmp_path, (now - timedelta(days=1)).date(), [
        {"topic_id": 8222, "old": "B", "new": "C", "at": now.isoformat()},
        {"topic_id": 9999, "old": "X", "new": "Y", "at": now.isoformat()},
    ])
    assert _relabel_attempts_last_n_days(8222, now, days=7) == 2
    assert _relabel_attempts_last_n_days(9999, now, days=7) == 1
    assert _relabel_attempts_last_n_days(1, now, days=7) == 0


def test_relabel_attempts_excludes_skip_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(_rcf, "_LEDGER_DIR", tmp_path)
    now = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
    _write_ledger(tmp_path, now.date(), [
        {"topic_id": 8235, "old": "A", "new": "B", "at": now.isoformat()},
        {"topic_id": 8235, "old": "B", "new": None, "reason": "relabel_capped_7d",
         "at": now.isoformat()},
        {"topic_id": 8235, "old": "B", "new": None, "reason": "relabel_cooldown_24h",
         "at": now.isoformat()},
    ])
    # only the real attempt counts — the two skip-markers are not attempts,
    # and must not let a parked topic inflate its own count while capped
    assert _relabel_attempts_last_n_days(8235, now, days=7) == 1


def test_relabel_attempts_counts_no_change_entries_as_real_attempts(tmp_path, monkeypatch):
    # a no-op relabel (GB2's relabel_no_change) still burned a DeepSeek call
    # and is a genuine attempt, even though the label didn't move
    monkeypatch.setattr(_rcf, "_LEDGER_DIR", tmp_path)
    now = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
    _write_ledger(tmp_path, now.date(), [
        {"topic_id": 5549, "old": "A", "new": "A", "reason": "relabel_no_change",
         "at": now.isoformat()},
    ])
    assert _relabel_attempts_last_n_days(5549, now, days=7) == 1


def test_relabel_attempts_ignores_entries_outside_the_window(tmp_path, monkeypatch):
    monkeypatch.setattr(_rcf, "_LEDGER_DIR", tmp_path)
    now = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
    _write_ledger(tmp_path, (now - timedelta(days=10)).date(), [
        {"topic_id": 42, "old": "A", "new": "B", "at": now.isoformat()},
    ])
    assert _relabel_attempts_last_n_days(42, now, days=7) == 0


def test_relabel_attempts_missing_ledger_files_is_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(_rcf, "_LEDGER_DIR", tmp_path)
    now = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
    assert _relabel_attempts_last_n_days(1, now, days=7) == 0


def test_relabel_attempts_tolerates_malformed_lines(tmp_path, monkeypatch):
    monkeypatch.setattr(_rcf, "_LEDGER_DIR", tmp_path)
    now = datetime(2026, 7, 30, 12, 0, tzinfo=timezone.utc)
    led = tmp_path / f"{now.date().isoformat()}-relabel-ledger.jsonl"
    with led.open("a", encoding="utf-8") as f:
        f.write("not json at all\n")
        f.write("\n")
        f.write(json.dumps({"topic_id": 7, "old": "A", "new": "B",
                            "at": now.isoformat()}) + "\n")
    assert _relabel_attempts_last_n_days(7, now, days=7) == 1


def test_relabel_candidates_include_revived_failed():
    # TF-3b: without this arm a court-failed revived candidate is immortal
    # (never promoted, never relabeled, never re-tried).
    from scripts.relabel_court_failed import _RELABEL_CANDIDATES_SQL as sql
    assert "state='candidate' AND revived_at IS NOT NULL" in sql
    assert "label_status='failed'" in sql
