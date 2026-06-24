"""Unified narrative-thread ranking (Pedro, 2026-06-24).

Drops the living/aggregate hierarchy: dynamic clusters and atlas topics are all
narrative threads and rank by the SAME score — no source bias. A persistent
atlas topic that keeps growing is a live thread, not a second-class aggregate.

Score blends three min-max-normalised components across the candidate set:

  score = 0.45·volume(log-damped) + 0.35·movement(relative) + 0.20·coherence

- volume = log1p(signal_count): damped so a 3,000-signal category cannot bury a
  50-signal story by raw count alone.
- movement = changed_10h / signal_count: relative acceleration, so "what's
  heating now" rises regardless of absolute size.
- coherence = avg_confidence: tips near-ties toward real stories over loose
  category bins (the guardrail — keeps raw taxonomy from dominating).

Weights are a calibratable v1; tune against live orderings, not in the abstract.
"""
from __future__ import annotations

import math

_W_VOLUME = 0.45
_W_MOVEMENT = 0.35
_W_COHERENCE = 0.20


def _minmax(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    rng = (hi - lo) or 1.0
    return [(v - lo) / rng for v in values]


def thread_score_components(thread: dict) -> tuple[float, float, float]:
    """Raw (pre-normalisation) volume / movement / coherence for one thread."""
    sc = max(int(thread.get("signal_count") or 0), 0)
    ch = int(thread.get("changed_10h") or 0)
    conf = float(thread.get("avg_confidence") or 0.0)
    volume = math.log1p(sc)
    movement = ch / sc if sc > 0 else 0.0
    return volume, movement, conf


def rank_threads(threads: list[dict]) -> list[dict]:
    """Return threads ordered by the unified score (best first). Source-agnostic
    and deterministic: ties fall back to volume then label so order is stable."""
    if not threads:
        return []
    comps = [thread_score_components(t) for t in threads]
    nv = _minmax([c[0] for c in comps])
    nm = _minmax([c[1] for c in comps])
    nc = _minmax([c[2] for c in comps])
    scored = []
    for idx, (t, v, m, c) in enumerate(zip(threads, nv, nm, nc)):
        score = _W_VOLUME * v + _W_MOVEMENT * m + _W_COHERENCE * c
        # deterministic tie-break: score, then raw volume, then label
        scored.append((score, comps[idx][0], str(t.get("label") or ""), t))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)
    return [t for _, _, _, t in scored]
