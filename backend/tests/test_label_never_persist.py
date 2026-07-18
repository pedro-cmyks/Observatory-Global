"""Lane A (2026-07-18): a labeler-failure sentinel must never PERSIST.

"(label failed)" reached production `dynamic_topics.label` through the chain
emergent_poc labeler error → emergent_clusters.label → the mode-label vote in
project_dynamic_topics → dynamic_topics.label → served. These tests freeze the
upstream rule at each link: placeholder strings are process artifacts, the
writers persist NULL (or keep the previous label) instead.
"""

from scripts.label_hygiene import (
    is_placeholder_label,
    normalize_persisted_label,
)
from scripts.project_dynamic_topics import Topic


def _topic(label):
    return Topic(
        identity_key="k1", label=label, centroid=[0.0, 1.0],
        snap="2026-07-18T00:00:00+00:00", n_signals=10, cohesion=0.9,
    )


# --- shared hygiene helpers --------------------------------------------------

def test_is_placeholder_label_catches_the_sentinels():
    for bad in (None, "", "  ", "(no label)", "(label failed)", "(label failed.)",
                "(LABEL FAILED)", "(label failed: timeout)", "none", "NULL"):
        assert is_placeholder_label(bad), bad


def test_is_placeholder_label_passes_real_labels():
    for good in ("Ukraine War Updates", "Emerging: Peru recount",
                 "Atentado a Ranucci", "زلزال فنزويلا"):
        assert not is_placeholder_label(good), good


def test_normalize_persisted_label_returns_null_for_sentinels():
    assert normalize_persisted_label("(label failed)") is None
    assert normalize_persisted_label("(no label)") is None
    assert normalize_persisted_label(None) is None
    assert normalize_persisted_label("  ") is None


def test_normalize_persisted_label_keeps_and_strips_real_labels():
    assert normalize_persisted_label("  Venezuela Earthquake  ") == "Venezuela Earthquake"


# --- project_dynamic_topics: the mode-label vote -----------------------------

def test_topic_never_counts_placeholder_label_at_creation():
    t = _topic("(label failed)")
    assert t.label == ""          # no votes — persists as NULL (label or None)
    assert not t.label_counts


def test_topic_attach_ignores_placeholder_labels():
    t = _topic("Venezuela Earthquake")
    # a later failed-label cluster must not outvote the real label
    for _ in range(3):
        t.attach(
            {"id": 2, "label": "(label failed)", "centroid": [0.0, 1.0],
             "n_signals": 5, "cohesion": 0.9},
            "2026-07-18T01:00:00+00:00", 0.95,
        )
    assert t.label == "Venezuela Earthquake"
    assert "(label failed)" not in t.label_counts


def test_topic_all_placeholder_labels_yields_empty_label():
    t = _topic("(no label)")
    t.attach(
        {"id": 2, "label": "(label failed)", "centroid": [0.0, 1.0],
         "n_signals": 5, "cohesion": 0.9},
        "2026-07-18T01:00:00+00:00", 0.95,
    )
    assert t.label == ""
    # persist writes `t.label or None` → NULL, never a placeholder string
    assert (t.label or None) is None
