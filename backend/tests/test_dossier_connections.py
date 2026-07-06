"""Pure-helper tests for the dossier connection endpoint (dossier-connections-v0)."""
from app.routers import dossier


def test_base_topic_id_strips_country_scope():
    assert dossier._base_topic_id("armed-conflict-escalation--CO") == "armed-conflict-escalation"
    assert dossier._base_topic_id("dynamic-topic-84") == "dynamic-topic-84"
    assert dossier._base_topic_id("  spaced--US ") == "spaced"


def test_cosine_bounds():
    assert dossier._cosine([1, 0, 0], [1, 0, 0]) == 1.0
    assert dossier._cosine([1, 0, 0], [0, 1, 0]) == 0.0
    assert dossier._cosine([0, 0, 0], [1, 1, 1]) == 0.0  # zero vector guarded


def test_project_positions_needs_three_and_is_normalized():
    assert dossier._project_positions({"a": [1, 0], "b": [0, 1]}) == {}  # < 3 → none
    pos = dossier._project_positions({
        "a": [1, 0, 0, 0], "b": [0, 1, 0, 0], "c": [0, 0, 1, 0], "d": [0.5, 0.5, 0, 0],
    })
    assert set(pos) == {"a", "b", "c", "d"}
    for p in pos.values():
        assert 0.0 <= p["x"] <= 1.0 and 0.0 <= p["y"] <= 1.0
