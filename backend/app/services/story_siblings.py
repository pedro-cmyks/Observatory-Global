"""Story-lens sibling ranking — a single-seed view over the constellation walk.

Ranking-with-receipts, NEVER merging: the transitive-collapse failure that
killed these signals as merge gates (recall-229 record) cannot occur here
because nothing is written and no closure is taken. Every sibling carries
the measured WHY.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from app.services.constellation_walk import (
    WalkParams,
    blob_connector_flags,
    build_knn_graph,
    dedup_reached,
    max_product_walk,
)

DEFAULT_CAP = 12


@dataclass(frozen=True)
class Sibling:
    topic_key: str
    label: str
    weight: float          # accumulated walk weight (rank key)
    degree: int            # hops from the anchor
    kinship: str           # 'hermano' (direct edge) | 'primo' (walked)
    through_blob: bool
    folded: tuple = ()     # same-event topic_keys folded under this rep
    reasons: tuple = ()    # ({'basis': str, 'value': str}, ...)


def rank_siblings(
    seed: int,
    whitened: np.ndarray,
    keys: Sequence[str],
    labels: Sequence[str],
    categories: Sequence[Optional[str]],
    params: WalkParams = WalkParams(),
    cap: int = DEFAULT_CAP,
) -> list[Sibling]:
    """Rank the measured neighborhood of one topic.

    whitened: unit-norm rows (apply_whitening output) aligned with keys/labels.
    """
    n = len(keys)
    if n < 2 or seed < 0 or seed >= n:
        return []
    graph = build_knn_graph(whitened, k=params.k)
    blobs = blob_connector_flags(graph, categories, params)
    reached = max_product_walk([seed], graph, params, blob_flags=blobs)
    ranked = sorted(
        (idx for idx in reached if idx != seed),
        key=lambda idx: -reached[idx].acc_weight,
    )
    reps, fold_map = dedup_reached(ranked, whitened, tau=params.dedup_tau)
    out: list[Sibling] = []
    for idx in reps:
        if len(out) >= cap:
            break
        node = reached[idx]
        reasons = [
            {"basis": "whitened_cos", "value": f"{node.via_weight:.2f}"},
            {"basis": "kinship", "value": f"{node.kinship} · {node.degree}º"},
        ]
        out.append(
            Sibling(
                topic_key=keys[idx],
                label=labels[idx],
                weight=float(node.acc_weight),
                degree=int(node.degree),
                kinship=node.kinship,
                through_blob=bool(node.through_blob),
                folded=tuple(keys[j] for j in fold_map.get(idx, [])),
                reasons=tuple(reasons),
            )
        )
    return out
