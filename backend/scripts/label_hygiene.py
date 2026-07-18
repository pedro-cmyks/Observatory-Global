"""Pure label-hygiene helpers shared by the topic writers (Lane A, 2026-07-18).

The "(label failed)" placeholder reached PRODUCTION `dynamic_topics.label`
through this chain: `emergent_poc._label_one` returns the sentinel on any
DeepSeek error → `snapshot_emergent_topics` persisted it verbatim into
`emergent_clusters.label` → `project_dynamic_topics` counted it in
`Topic.label_counts` (it is truthy) → the mode label was persisted into
`dynamic_topics.label` and served.

Rule: a labeler-failure sentinel is a PROCESS artifact, never a label. On
failure persist NULL (or keep the previous label); the serving guard
(`app/services/thread_intelligence.clean_thread_label`) then renders an
honest receipt-derived fallback. Never persist a placeholder string.

Zero-dependency module so both writer scripts and the tests can import it
regardless of entry point (`-m scripts.*` or `-m backend.scripts.*`).
"""
from __future__ import annotations

# Keep in sync with app.services.thread_intelligence._PLACEHOLDER_LABELS
# (the serving-side mirror; app/ must not import from scripts/).
PLACEHOLDER_LABELS = {"", "(no label)", "(label failed)", "(label failed.)", "none", "null"}


def is_placeholder_label(label: object) -> bool:
    """True when the label is empty or a known labeler-failure sentinel."""
    if label is None:
        return True
    s = str(label).strip()
    if not s:
        return True
    low = s.lower()
    return low in PLACEHOLDER_LABELS or low.startswith("(label failed")


def normalize_persisted_label(label: object) -> str | None:
    """The value a writer may persist: the real label, or NULL — never a
    placeholder string."""
    if is_placeholder_label(label):
        return None
    return str(label).strip()
