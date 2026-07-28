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

import datetime as _dt
import os as _os
import sys as _sys


def ledger_alert(tag: str, message: str) -> None:
    """One dated line to the shared reliability ledger (if configured) + stderr.

    Mirrors the runners' `atlas_alert` line format exactly so python- and
    shell-emitted alerts interleave in one ledger. The ledger path comes from
    `ATLAS_RELIABILITY_ALERTS_LOG` (exported by the runners); unset means
    stderr-only — never a crash. Motivation (2026-07-23..27): the labeler was
    down for five nights and `emergent_clusters.label` went 100% NULL, which
    silently disabled fragment merging for the whole week — nothing anywhere
    said so. An alert the runner cannot see is an alert that does not exist,
    so the WRITER of the defective artifact ledgers it directly."""
    line = f"{_dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} [{tag}] {message}"
    print(line, file=_sys.stderr)
    path = _os.environ.get("ATLAS_RELIABILITY_ALERTS_LOG")
    if path:
        try:
            _os.makedirs(_os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass

# Keep in sync with app.services.thread_intelligence._PLACEHOLDER_LABELS
# (the serving-side mirror; app/ must not import from scripts/).
PLACEHOLDER_LABELS = {"", "(no label)", "(label failed)", "(label failed.)", "none", "null"}

# LLM-refusal PROSE ("Unable to determine a single news cluster from these
# diverse headlines" — served at prod /threads #8, 2026-07-19) is a labeler
# failure the fixed sentinel set cannot enumerate. Precision-first shape test:
# a refusal stem at the START of the label plus a self-referential TASK word
# anywhere. A real headline-label like "Unable to determine cause of blast"
# has no task word and passes through untouched.
# Keep in sync with app.services.thread_intelligence (serving-side mirror).
REFUSAL_STEMS = (
    "unable to ", "cannot ", "can't ", "could not ", "couldn't ",
    "i cannot", "i am unable", "i'm unable", "i can't",
    "no single ", "no clear ", "no coherent", "no majority",
    "not enough ", "there is no ", "the provided ",
    "these headlines", "the headlines", "sorry", "as an ai",
)
REFUSAL_TASK_WORDS = (
    "headline", "cluster", "grouping", "articles", "these threads",
    "single event", "single topic", "single news", "common theme",
    "majority topic", "majority cluster", "coherent group",
    "labels provided", "provided labels",
)
# Unambiguous refusal phrases caught ANYWHERE ("Multiple unrelated headlines;
# no single label applies") — no plausible news title contains them.
REFUSAL_PHRASES = (
    "no single label", "no majority label", "no unifying topic",
    "do not form a single", "does not form a single", "too diverse to form",
    "no cluster exists",
)


def is_refusal_label(label: str) -> bool:
    """True when the label reads as LLM-refusal prose about the labeling task
    itself, not a news title."""
    low = str(label).strip().lower()
    if any(p in low for p in REFUSAL_PHRASES):
        return True
    return low.startswith(REFUSAL_STEMS) and any(w in low for w in REFUSAL_TASK_WORDS)


def is_placeholder_label(label: object) -> bool:
    """True when the label is empty or a known labeler-failure sentinel."""
    if label is None:
        return True
    s = str(label).strip()
    if not s:
        return True
    low = s.lower()
    return (
        low in PLACEHOLDER_LABELS
        or low.startswith("(label failed")
        or is_refusal_label(low)
    )


def normalize_persisted_label(label: object) -> str | None:
    """The value a writer may persist: the real label, or NULL — never a
    placeholder string."""
    if is_placeholder_label(label):
        return None
    return str(label).strip()
