#!/usr/bin/env python3
"""Phase B feasibility probe: a learned 'is-evidence' scope gate.

Question this answers (cheaply, $0 API): can a learned classifier reading
the headline + candidate topic separate signals where the Atlas v2
assignment is *evidence* (consensus correct) from those where the topic is
only *context / noise* (consensus incorrect)? That scope-mismatch error is
the dominant residual the rule-based classifier cannot fix; the roadmap
bets a learned gate can. This probe measures whether the bet is plausible
on the existing 7-LLM consensus corpus BEFORE spending on 5k-row scaling.

Target = `is_evidence` from the consensus corpus
(`build_consensus_corpus.py`): consensus correct -> 1, incorrect -> 0,
ambiguous rows dropped. Positive class = evidence = "the gate KEEPS this
assignment". Precision-at-keep is the metric that matters (precision-first
project rule): of the assignments the gate keeps, how many are real
evidence, and at what recall can we hold >=90% / >=85% precision?

Feature ladder (cheapest first), each with the same numpy logistic
regression and pooled stratified 5-fold out-of-fold probabilities:
  1. atlas_conf : [atlas_confidence, atlas_matched_terms] — does Atlas's
     own score already separate evidence from context?
  2. charngram  : hashed char 3-5 grams over "headline | topic_label"
     (multilingual-robust, leakage-free hashing, no fitted vocab).
  3. charngram+conf : char n-grams stacked with the atlas_conf features.

Dependency-light by design: numpy only. The rest of the repo's research
toolkit is stdlib/numpy-only; sklearn/pandas in this venv live on an
iCloud-synced path and stall on dataless-file reads, so they are avoided.
Metric implementations are self-tested against known sklearn values
(`--selftest`).

Small-N caveat: ~207 binary rows, ~18 positives per fold. Feasibility
signal, not a production metric. CIs are bootstrapped over the pooled
out-of-fold predictions and are wide by construction.

Schema version: atlas-phase-b-scope-gate-probe-v2
"""

from __future__ import annotations

import argparse
import json
import zlib
from pathlib import Path
from typing import Any

import numpy as np

SEED = 0
N_FOLDS = 5
N_BOOTSTRAP = 2000
HASH_DIM = 1 << 14  # 16384


# --------------------------------------------------------------------------
# features
# --------------------------------------------------------------------------
def _char_ngram_vector(text: str, lo: int = 3, hi: int = 5, dim: int = HASH_DIM) -> np.ndarray:
    """Hashed char n-gram TF vector (char_wb style: pad each token). Hashing
    is deterministic (crc32) and fit-free, so it cannot leak across folds."""
    vec = np.zeros(dim, dtype=np.float64)
    for token in str(text).lower().split():
        padded = f" {token} "
        for n in range(lo, hi + 1):
            if len(padded) < n:
                continue
            for i in range(len(padded) - n + 1):
                gram = padded[i : i + n]
                idx = zlib.crc32(gram.encode("utf-8")) % dim
                vec[idx] += 1.0
    nz = vec > 0
    vec[nz] = 1.0 + np.log(vec[nz])  # sublinear TF
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm  # L2 row norm (so the linear model sees comparable rows)
    return vec


def _charngram_matrix(texts: list[str]) -> np.ndarray:
    return np.vstack([_char_ngram_vector(t) for t in texts])


def _standardize_fit(X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return mu, sd


# --------------------------------------------------------------------------
# logistic regression (numpy, L2, class-balanced)
# --------------------------------------------------------------------------
class NumpyLogReg:
    def __init__(self, l2: float = 1.0, lr: float = 0.5, n_iter: int = 1500):
        self.l2 = l2
        self.lr = lr
        self.n_iter = n_iter
        self.w: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> "NumpyLogReg":
        n, d = X.shape
        Xb = np.hstack([X, np.ones((n, 1))])  # bias column last
        w = np.zeros(d + 1)
        n_pos = max(int(y.sum()), 1)
        n_neg = max(int((1 - y).sum()), 1)
        # balanced sample weights (sklearn class_weight="balanced" convention)
        sw = np.where(y == 1, n / (2.0 * n_pos), n / (2.0 * n_neg))
        reg_mask = np.ones(d + 1)
        reg_mask[-1] = 0.0  # do not regularize bias
        for _ in range(self.n_iter):
            z = Xb @ w
            p = 1.0 / (1.0 + np.exp(-z))
            grad = Xb.T @ (sw * (p - y)) / n + self.l2 * reg_mask * w / n
            w -= self.lr * grad
        self.w = w
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        assert self.w is not None
        Xb = np.hstack([X, np.ones((X.shape[0], 1))])
        return 1.0 / (1.0 + np.exp(-(Xb @ self.w)))


# --------------------------------------------------------------------------
# CV
# --------------------------------------------------------------------------
def _stratified_folds(y: np.ndarray, k: int, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    folds: list[list[int]] = [[] for _ in range(k)]
    for cls in (0, 1):
        idx = np.where(y == cls)[0]
        rng.shuffle(idx)
        for j, i in enumerate(idx):
            folds[j % k].append(int(i))
    return [np.array(sorted(f)) for f in folds]


def _pooled_oof(X: np.ndarray, y: np.ndarray, standardize: bool) -> np.ndarray:
    folds = _stratified_folds(y, N_FOLDS, SEED)
    p = np.zeros(len(y))
    for te in folds:
        tr = np.array([i for i in range(len(y)) if i not in set(te.tolist())])
        Xtr, Xte = X[tr].copy(), X[te].copy()
        if standardize:
            mu, sd = _standardize_fit(Xtr)
            Xtr = (Xtr - mu) / sd
            Xte = (Xte - mu) / sd
        model = NumpyLogReg().fit(Xtr, y[tr])
        p[te] = model.predict_proba(Xte)
    return p


# --------------------------------------------------------------------------
# metrics (self-tested against known sklearn values)
# --------------------------------------------------------------------------
def roc_auc(y: np.ndarray, s: np.ndarray) -> float:
    """Mann-Whitney U / rank AUC with tie-averaged ranks."""
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), dtype=float)
    sorted_s = s[order]
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0  # 1-based, averaged over ties
        ranks[order[i : j + 1]] = avg_rank
        i = j + 1
    n_pos = float(y.sum())
    n_neg = float((1 - y).sum())
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    sum_pos = ranks[y == 1].sum()
    return float((sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def average_precision(y: np.ndarray, s: np.ndarray) -> float:
    """sklearn AP: sum_n (R_n - R_{n-1}) * P_n."""
    order = np.argsort(-s, kind="mergesort")
    y_sorted = y[order]
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    n_pos = float(y.sum())
    if n_pos == 0:
        return float("nan")
    precision = tp / np.maximum(tp + fp, 1e-12)
    recall = tp / n_pos
    ap = 0.0
    prev_r = 0.0
    for i in range(len(y_sorted)):
        ap += (recall[i] - prev_r) * precision[i]
        prev_r = recall[i]
    return float(ap)


def max_recall_at_precision(y: np.ndarray, s: np.ndarray, target: float) -> dict[str, float]:
    """Max recall achievable while keep-precision >= target, sweeping the
    decision threshold over distinct scores."""
    order = np.argsort(-s, kind="mergesort")
    y_sorted = y[order]
    s_sorted = s[order]
    tp = np.cumsum(y_sorted)
    fp = np.cumsum(1 - y_sorted)
    n_pos = float(y.sum())
    precision = tp / np.maximum(tp + fp, 1e-12)
    recall = tp / n_pos
    best_rec = 0.0
    best_thr = 1.0
    for i in range(len(y_sorted)):
        # threshold = keep all with score >= s_sorted[i]
        if precision[i] >= target and recall[i] > best_rec:
            best_rec = float(recall[i])
            best_thr = float(s_sorted[i])
    return {"max_recall": round(best_rec, 4), "threshold": round(best_thr, 4)}


def _bootstrap_ci(y: np.ndarray, p: np.ndarray, fn, n: int = N_BOOTSTRAP) -> list[float]:
    rng = np.random.default_rng(SEED)
    vals = []
    idx = np.arange(len(y))
    for _ in range(n):
        b = rng.choice(idx, size=len(idx), replace=True)
        yb = y[b]
        if yb.sum() == 0 or yb.sum() == len(yb):
            continue
        vals.append(fn(yb, p[b]))
    if not vals:
        return [float("nan"), float("nan")]
    return [round(float(np.percentile(vals, 2.5)), 4), round(float(np.percentile(vals, 97.5)), 4)]


# --------------------------------------------------------------------------
def _selftest() -> None:
    y = np.array([0, 0, 1, 1])
    s = np.array([0.1, 0.4, 0.35, 0.8])
    auc = roc_auc(y, s)
    ap = average_precision(y, s)
    assert abs(auc - 0.75) < 1e-9, f"roc_auc {auc} != 0.75"
    assert abs(ap - 0.8333333333) < 1e-6, f"ap {ap} != 0.8333"
    # perfect ranking
    yp = np.array([0, 0, 1, 1])
    sp = np.array([0.1, 0.2, 0.9, 0.95])
    assert abs(roc_auc(yp, sp) - 1.0) < 1e-9
    assert abs(average_precision(yp, sp) - 1.0) < 1e-9
    print("selftest OK: roc_auc=0.75, ap=0.8333 match sklearn references")


# --------------------------------------------------------------------------
def _load(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [r for r in rows if r.get("is_evidence") in (0, 1)]


def _texts(rows: list[dict[str, Any]]) -> list[str]:
    out = []
    for r in rows:
        h = (r.get("headline") or "").strip()
        t = (r.get("assigned_topic_label") or "").strip()
        out.append(f"{h} | {t}")
    return out


def _atlas_feats(rows: list[dict[str, Any]]) -> np.ndarray:
    conf = [float(r.get("atlas_confidence") or 0.0) for r in rows]
    mt = [float(r.get("atlas_matched_terms") or 0.0) for r in rows]
    return np.column_stack([conf, mt])


def _load_embeddings(path: Path) -> dict[tuple[int, str], np.ndarray]:
    out: dict[tuple[int, str], np.ndarray] = {}
    for l in path.read_text(encoding="utf-8").splitlines():
        l = l.strip()
        if not l:
            continue
        r = json.loads(l)
        out[(int(r["signal_id"]), r.get("assigned_topic_slug"))] = np.asarray(
            r["embedding"], dtype=np.float64
        )
    return out


def _evaluate(name: str, X: np.ndarray, y: np.ndarray, standardize: bool) -> dict[str, Any]:
    p = _pooled_oof(X, y, standardize)
    return {
        "feature_set": name,
        "n": int(len(y)),
        "n_positive": int(y.sum()),
        "base_rate_precision": round(float(y.mean()), 4),
        "roc_auc": round(roc_auc(y, p), 4),
        "roc_auc_ci95": _bootstrap_ci(y, p, roc_auc),
        "pr_auc": round(average_precision(y, p), 4),
        "pr_auc_ci95": _bootstrap_ci(y, p, average_precision),
        "keep_at_precision_0.90": max_recall_at_precision(y, p, 0.90),
        "keep_at_precision_0.85": max_recall_at_precision(y, p, 0.85),
    }


def main() -> None:
    base = Path("docs/research/atlas-paper/phase-1-validation")
    ap = argparse.ArgumentParser(description="Phase B scope-gate feasibility probe (numpy-only).")
    ap.add_argument("--corpus", type=Path, default=base / "labels/consensus/2026-05-28-7llm-consensus-corpus.jsonl")
    ap.add_argument("--out", type=Path, default=base / "reports/phase-b/2026-05-28-scope-gate-probe.json")
    ap.add_argument("--embeddings", type=Path, default=None,
                    help="Optional JSONL {signal_id, assigned_topic_slug, embedding} to add semantic feature sets.")
    ap.add_argument("--selftest", action="store_true", help="Run metric self-tests and exit.")
    args = ap.parse_args()

    if args.selftest:
        _selftest()
        return

    _selftest()  # always guard the metrics before reporting numbers
    rows = _load(args.corpus)
    y = np.array([r["is_evidence"] for r in rows], dtype=int)
    texts = _texts(rows)
    atlas = _atlas_feats(rows)
    print(f"loaded {len(y)} binary rows ({int(y.sum())} evidence / {int((1-y).sum())} not)")

    ngram = _charngram_matrix(texts)

    results = [
        _evaluate("atlas_conf", atlas, y, standardize=True),
        _evaluate("charngram", ngram, y, standardize=False),
        _evaluate("charngram+conf", np.hstack([ngram, atlas]), y, standardize=False),
    ]

    if args.embeddings:
        emb_map = _load_embeddings(args.embeddings)
        keys = [(int(r["signal_id"]), r.get("assigned_topic_slug")) for r in rows]
        mask = np.array([k in emb_map for k in keys])
        if int(mask.sum()) == 0:
            print("WARNING: no embeddings matched corpus rows — skipping semantic sets")
        else:
            emb = np.vstack([emb_map[k] for k in keys if k in emb_map])
            ym, atlasm, ngramm = y[mask], atlas[mask], ngram[mask]
            print(f"embeddings matched {int(mask.sum())}/{len(rows)} rows (dim={emb.shape[1]})")
            results.append(_evaluate("openai_emb", emb, ym, standardize=True))
            results.append(_evaluate("openai_emb+conf", np.hstack([emb, atlasm]), ym, standardize=True))
            results.append(
                _evaluate("openai_emb+charngram+conf",
                          np.hstack([emb, ngramm, atlasm]), ym, standardize=False)
            )

    report = {
        "schema_version": "atlas-phase-b-scope-gate-probe-v2",
        "corpus": str(args.corpus),
        "n_rows_binary": int(len(y)),
        "n_evidence": int(y.sum()),
        "n_not_evidence": int((1 - y).sum()),
        "seed": SEED,
        "n_folds": N_FOLDS,
        "n_bootstrap": N_BOOTSTRAP,
        "hash_dim": HASH_DIM,
        "note": (
            "Feasibility probe on binary consensus rows. Positive class = "
            "evidence (gate keeps). base_rate_precision is the no-op keep-all "
            "precision = current Atlas precision on this decided subset. "
            "keep_at_precision_X = max recall while keeping >=X precision. "
            "numpy-only; metrics self-tested against sklearn references."
        ),
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
