# Global e5 whitening — fit + store (the ASSET), 2026-07-07

**One fitted "all-but-the-top" (Mu & Viswanath 2017) decompression transform over
the e5 corpus, persisted so the whole pipeline can apply a consistent decompressed
view of the SAME stored vectors — no re-embedding, no new engine.** This is the
FIT + STORE step only. **No consumer threshold is flipped here.** Each consumer
re-calibrates its own threshold in whitened space, separately, on adoption.

## Why

e5 (`signal_embeddings.vec` halfvec/768, `dynamic_topics.centroid_vec` real[]) is
anisotropic — a dominant shared direction + a few rogue dims squash cosine into a
narrow ~0.88–0.97 band, so a fixed similarity threshold can't cleanly separate
real neighbors from noise. "All-but-the-top" whitening subtracts the corpus mean
and projects out the top-k principal components, then re-normalizes. The dossier
neighbors/edges already do this PER-REQUEST (refit on the candidate set each call,
`app/routers/dossier.py`); a GLOBAL fitted transform is strictly better — fit
once, apply consistently everywhere, cheap at read time. This asset **supersedes**
the per-request whitening in the dossier (it can switch to the global transform).

## What was produced (this task)

- `backend/app/data/e5_whitening.npz` — `{mean float32[768], components
  float32[k][768], k, dim, fit_n, fit_at, method}`. Small, committed.
- `backend/app/services/whitening.py` — `load_whitening()` (cached, thread-safe)
  + `apply_whitening(vecs)` (center by μ, project out stored components,
  L2-normalize). Pure, unit-tested (`backend/tests/test_whitening.py`, 7 tests).
- `backend/scripts/fit_global_whitening.py` — fits μ + top-k PCs on a broad
  `signal_embeddings` sample (SVD of the centered sample), records the AUC
  sweeps, writes the artifact. READ-ONLY on the DB.
- `backend/scripts/measure_embedding_separation.py` — extended with a
  **signal-level** `--signals` sweep (same-topic vs diff-topic evidence pairs
  from `topic_members role='evidence'`).

Fit params: **fit_n = 99,871**, dim = 768, **k = 1**, method = all-but-top-k
global fit. Sampled via `TABLESAMPLE BERNOULLI` (a full `ORDER BY random()` sort
of 186k×768 trips the pooler statement_timeout). Top directions via
eigendecomposition of the 768×768 covariance, not a full n×768 SVD (the latter
computes the huge U we don't need and crawls on the mindful M1; eigenvectors of
Xcᵀ Xc == the right singular vectors, verified sign-agnostic |cos|=1.0).

## Measured k sweep — pick k at the knee, don't guess

Separation = median cosine gap (same-topic − diff-topic) + ROC-AUC (0.5 = space
can't tell them apart, 1.0 = perfectly separable). Two spaces measured because
the ONE global transform must serve BOTH:

### Signal level (`signal_embeddings` × `topic_members role='evidence'`)
19,211 evidence signals, 746 topics (≥4 members). Sweep ran on a 49,968-signal
fit (`--signals`); the stored artifact uses a fresh 99,871-signal fit — the
anisotropy directions are identical across both, so the knee is unchanged.

| k | same p50 | diff p50 | gap | AUC |
|---|----------|----------|------|-----|
| 0 | 0.382 | −0.003 | +0.385 | **0.940** |
| 1 | 0.344 | 0.010 | +0.334 | 0.927 |
| 2 | 0.323 | −0.005 | +0.327 | 0.934 |
| 3 | 0.308 | −0.005 | +0.313 | 0.929 |
| 5 | 0.279 | −0.004 | +0.283 | 0.922 |

At the **signal** level, centering + normalization alone (k=0) is already the best
separator; the 1st PC carries real topical signal, so removing it *costs* ~1pp AUC.
The signal space is nearly indifferent to k (0.940 → 0.927 across k=0→1).

### Centroid level (`dynamic_topics.centroid_vec`, same/diff = share a parent umbrella)
Global signal-fit transform applied to centroids — the compressed space the dossier
neighbors + `MATCH_THRESHOLD` actually live in.

22 umbrella children, 11 umbrellas (same = share a parent).

| k | same p50 | diff p50 | gap | AUC |
|---|----------|----------|------|-----|
| 0 | 0.863 | 0.180 | +0.683 | 0.995 |
| 1 | 0.851 | 0.115 | +0.736 | 0.993 |
| 2 | 0.826 | 0.036 | +0.790 | 0.992 |
| 3 | 0.826 | 0.034 | +0.792 | 0.987 |
| 5 | 0.810 | 0.050 | +0.760 | 0.984 |

Small sample (11 umbrellas) → AUC saturates near 0.99 and is not discriminating;
read the **gap** instead. Removing the top PC pushes *unrelated* centroids apart
(diff p50 0.180 → 0.115 at k=1, → 0.036 at k=2) while same-topic stays high — the
gap widens monotonically with k. This agrees with the earlier per-request finding
on the full centroid set (raw AUC 0.80 → k=1 0.87, `dossier.py`): the centroid
space — where the compression actually bites ("Kate Middleton" flooding neighbors)
— genuinely benefits from PC removal.

## Decision: k = 1

The two spaces disagree at the margin, so k=1 is the honest compromise:

- **Signal space** barely needs it — k=0 is best (AUC 0.940), k=1 costs ~1pp
  (0.927). The 1st PC there still carries topical signal.
- **Centroid space** wants it — k=1 widens the gap (+0.683 → +0.736), dropping
  unrelated-centroid similarity 0.180 → 0.115. This is the space the dossier
  neighbors + `MATCH_THRESHOLD` live in, and the motivating problem.

The signal space costs ~1pp AUC at k=1 vs k=0; the centroid space — the worst-
compressed and the ACTUAL motivating problem ("Kate Middleton" flooding neighbors)
— is where PC removal earns its keep. k=1 is the minimum that fixes the centroid
space while barely touching the signal space, and it matches the already-validated
dossier-neighbor k=1. `components` beyond k=1 are NOT stored (the artifact holds
exactly the chosen k); re-fit if a future consumer needs a different k in its space.

## CONSUMER LIST — each RE-CALIBRATES its own threshold before adopting

Adoption is **per-consumer, one at a time**. Whitening changes the cosine scale,
so every threshold below must be RE-MEASURED in whitened space — never a big-bang
flip. This task wires **none** of them.

| Consumer | Current threshold (raw e5) | Space | Notes |
|----------|----------------------------|-------|-------|
| Semantic-assignment lane taus | wild-junk-quantile taus (`sem-assign-v0`) | signal (OpenAI space!) | ⚠ lane uses **OpenAI** embeddings, not e5 — this e5 transform does NOT apply; separate OpenAI whitening if ever wanted |
| `dynamic_topics` MATCH_THRESHOLD / resurrection | 0.85 | centroid | primary beneficiary; re-measure noise floor in whitened space |
| HDBSCAN cluster params | `min_cluster_size` / `cluster_selection_epsilon` | signal | clustering runs on raw e5; whitened distances change ε — re-sweep recall/purity |
| Dossier `SEM_EDGE_THRESHOLD` | 0.88 (edges), `NEIGHBOR_TAU` 0.40 (per-request whitened) | centroid | already whitens per-request at k=1; switch to global transform + re-confirm 0.40 |
| Thread-coherence tiers | avg_confidence bands | signal/centroid | coherence uses cosine to centroid — re-band in whitened space |
| Semantic thread-members ANN | signal_embeddings HNSW | signal | HNSW index is on RAW halfvec; whitening is a read-time re-rank, not an index change |
| Research semantic-lane taus | 0.84 (signal), top-margin cuts | signal | re-measure junk quantile in whitened space |
| SignalDetail semantic neighbors | HNSW 0.84 | signal | e5 space — applies; **NOT the scope gate** (that's OpenAI, leave it) |

**Explicitly NOT a consumer:** the scope gate (`atlas-scope-gate-v1-openai`) runs
in OpenAI embedding space — this e5 whitening does not touch it.

## How to reproduce

```bash
# measurement (read-only, M1 mlvenv):
PYTHONPATH=backend .../mlvenv/bin/python backend/scripts/measure_embedding_separation.py --signals
# fit + store:
PYTHONPATH=backend .../mlvenv/bin/python backend/scripts/fit_global_whitening.py --k 1
# sanity:
python -c "from app.services.whitening import load_whitening, apply_whitening; import numpy as np; \
  w=load_whitening(); print(w.k, w.dim, w.fit_n); \
  print(apply_whitening(np.ones((2,768),dtype='float32')).shape)"
```

No deploy — nothing reads the artifact yet.
