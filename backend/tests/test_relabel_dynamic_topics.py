"""Pure-logic tests for Claude-CLI relabeling (no DB, no subprocess)."""

from datetime import datetime, timedelta, timezone

from scripts.claude_label import build_prompt, parse_label_response
from scripts.relabel_dynamic_topics import needs_relabel

NOW = datetime(2026, 6, 24, 12, 0, tzinfo=timezone.utc)


# ---- parse_label_response ----

def test_parse_plain_json():
    out = parse_label_response('{"label": "Iran Water Crisis", "description": "d", "confidence": 0.9}')
    assert out["label"] == "Iran Water Crisis"
    assert out["confidence"] == 0.9


def test_parse_fenced_json():
    raw = 'Here is the label:\n```json\n{"label": "Maine Primary", "confidence": 0.8}\n```\n'
    out = parse_label_response(raw)
    assert out["label"] == "Maine Primary"


def test_parse_json_with_surrounding_prose():
    raw = 'Sure. {"label": "Gaza Ceasefire Talks", "description": "x"} Hope that helps.'
    out = parse_label_response(raw)
    assert out["label"] == "Gaza Ceasefire Talks"


def test_parse_empty_is_failure_stub():
    out = parse_label_response("")
    assert out["label"] == "(label failed)"
    assert out["confidence"] == 0.0


def test_parse_garbage_is_failure_stub():
    out = parse_label_response("I cannot do that.")
    assert out["label"].startswith("(label failed")


def test_build_prompt_lists_headlines():
    p = build_prompt(["First headline", "Second headline", ""])
    assert "- First headline" in p
    assert "- Second headline" in p
    assert "- \n" not in p  # empty dropped


# ---- needs_relabel ----

def _topic(label="Russia-Ukraine War", updated=NOW):
    return {"label": label, "label_updated_at": updated}


def test_fresh_real_label_not_relabeled():
    assert needs_relabel(_topic(updated=NOW - timedelta(days=1)), now=NOW, max_age_days=7) is False


def test_stale_label_relabeled():
    assert needs_relabel(_topic(updated=NOW - timedelta(days=8)), now=NOW, max_age_days=7) is True


def test_never_stamped_is_overdue():
    assert needs_relabel(_topic(updated=None), now=NOW) is True


def test_placeholder_label_relabeled():
    assert needs_relabel(_topic(label="(no label)", updated=NOW), now=NOW) is True
    assert needs_relabel(_topic(label="", updated=NOW), now=NOW) is True


def test_roundup_marker_label_relabeled():
    assert needs_relabel(_topic(label="Daily News Roundup", updated=NOW), now=NOW) is True


def test_naive_timestamp_treated_as_utc():
    naive = (NOW - timedelta(days=2)).replace(tzinfo=None)
    assert needs_relabel(_topic(updated=naive), now=NOW, max_age_days=7) is False
