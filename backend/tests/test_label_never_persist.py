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


# --- 2026-07-19: writer side must also treat LLM-refusal prose as failure ---

def test_refusal_prose_never_persists():
    from scripts.label_hygiene import is_placeholder_label, normalize_persisted_label

    refusal = "Unable to determine a single news cluster from these diverse headlines"
    assert is_placeholder_label(refusal)
    assert normalize_persisted_label(refusal) is None
    # a real title with a refusal-like stem but no task word persists
    real = "Unable to determine cause of deadly blast, officials say"
    assert not is_placeholder_label(real)
    assert normalize_persisted_label(real) == real


def test_ledger_alert_reaches_the_ledger_and_stderr(tmp_path, monkeypatch, capsys):
    """THE 2026-07-23..27 BLACKOUT: five nights of 100% NULL labels silently
    disabled fragment merging (labels_compatible(None, None) is False) and
    nothing anywhere said so. The writer of the defective artifact must ledger
    it directly, in the exact atlas_alert line format, so python- and
    shell-emitted alerts interleave in one ledger."""
    from scripts.label_hygiene import ledger_alert

    ledger = tmp_path / "logs" / "reliability-alerts.log"
    monkeypatch.setenv("ATLAS_RELIABILITY_ALERTS_LOG", str(ledger))
    ledger_alert("test-tag", "SNAPSHOT_UNLABELLED 30 clusters labeled, 0 usable")

    line = ledger.read_text(encoding="utf-8").strip()
    assert "[test-tag] SNAPSHOT_UNLABELLED 30 clusters labeled, 0 usable" in line
    # dated like atlas_alert: "YYYY-mm-dd HH:MM:SS [tag] msg"
    assert line[:4].isdigit() and line[10] == " " and line[19] == " "
    assert "SNAPSHOT_UNLABELLED" in capsys.readouterr().err


def test_ledger_alert_without_env_is_stderr_only(monkeypatch, capsys):
    from scripts.label_hygiene import ledger_alert

    monkeypatch.delenv("ATLAS_RELIABILITY_ALERTS_LOG", raising=False)
    ledger_alert("t", "no ledger configured")  # must not raise
    assert "no ledger configured" in capsys.readouterr().err


def test_failure_sentinels_count_as_unusable_for_the_unlabelled_alert():
    """The alert's 'usable' count must use the SAME normalize_persisted_label
    that decides what persists — a snapshot of pure failure sentinels is an
    unlabelled snapshot."""
    from scripts.label_hygiene import normalize_persisted_label

    sentinel_batch = [{"label": "(label failed)"}, {"label": "(no label)"},
                      {"label": ""}, {"label": None}]
    usable = sum(1 for dl in sentinel_batch
                 if normalize_persisted_label(dl.get("label")))
    assert usable == 0
    assert normalize_persisted_label("Iran Accuses Ukraine of Caspian Attack")
