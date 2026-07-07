#!/usr/bin/env python
"""FIT + STORE the ONE global e5 whitening (decompression) transform. READ-ONLY
on the DB; writes a small durable artifact the app loads at read time.

WHY: e5 (`signal_embeddings.vec`, `dynamic_topics.centroid_vec`) is anisotropic
— a dominant shared direction + a few rogue dims squash cosine into ~0.88-0.97.
"All-but-the-top" whitening (Mu & Viswanath 2017: subtract corpus mean, project
out the top-k principal components) decompresses it. The dossier neighbors do
this PER-REQUEST (refit on the candidate set each call); a GLOBAL fitted
transform is better — fit once, consistent everywhere, cheap to apply.

Pipeline: sample ~N random e5 signal vectors → mu + top-k_max principal
directions (SVD of centered sample) → store {mean, components, k, ...} to
backend/app/data/e5_whitening.npz. `app/services/whitening.py` loads + applies.

k is MEASURED, not guessed — run `measure_embedding_separation.py --signals`
first (same/diff-topic AUC sweep) and pass the knee via --k. This script also
prints the same sweep on its own fit sample for the record.

This FITS + STORES only. It does NOT flip any consumer threshold — each consumer
re-calibrates its own threshold in whitened space on adoption (see the doc
docs/research/embedding-whitening/2026-07-07-global-whitening-fit.md).
"""
from __future__ import annotations
import os, sys, asyncio, argparse
from datetime import datetime, timezone
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.measure_embedding_separation import (  # noqa: E402
    load_signal_sample, load_evidence_signals, fit_whitening,
    apply_fitted, signal_pair_cosines, auc, load as load_centroids, pair_cosines,
)

ARTIFACT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "app", "data", "e5_whitening.npz")


async def run(n_fit: int, k: int, k_max: int, out: str, sweep: bool):
    print(f"sampling {n_fit} e5 vectors from signal_embeddings…")
    sample = await load_signal_sample(n_fit)
    print(f"  sample shape={sample.shape}")
    mu, comps = fit_whitening(sample, k_max)   # top-k_max, ordered by variance
    print(f"  fitted mu + top-{k_max} components")

    if sweep:
        # Same/diff-topic AUC sweep on the fitted transform (evidence signals).
        topics, V = await load_evidence_signals()
        print(f"\nSIGNAL-level same/diff-topic separation on {len(topics)} evidence "
              f"signals ({len(set(topics))} topics):")
        print("  k   same_p50  diff_p50    gap     AUC")
        for kk in (0, 1, 2, 3, 5):
            if kk > k_max:
                continue
            Vn = apply_fitted(V, mu, comps, kk)
            s, d = signal_pair_cosines(Vn, topics)
            mark = "  <- chosen" if kk == k else ""
            print(f"  {kk:<3} {np.median(s):8.3f} {np.median(d):9.3f} "
                  f"{np.median(s)-np.median(d):+8.3f}  {auc(s, d):.3f}{mark}")

    # CENTROID-level check under the SAME global transform (dynamic_topics
    # centroid_vec, same/diff = share a parent umbrella). This is the compressed
    # space the dossier neighbors + MATCH_THRESHOLD live in — the transform must
    # help HERE, not just at the signal level.
    parents, C = await load_centroids()
    print(f"\nCENTROID-level separation on {len(parents)} umbrella children "
          f"({len(set(parents))} umbrellas), global transform:")
    print("  k   same_p50  diff_p50    gap     AUC")
    for kk in (0, 1, 2, 3, 5):
        if kk > k_max:
            continue
        Cn = apply_fitted(C, mu, comps, kk)
        s, d = pair_cosines(Cn, parents)   # Cn already unit-norm; norm() is idempotent
        mark = "  <- chosen" if kk == k else ""
        print(f"  {kk:<3} {np.median(s):8.3f} {np.median(d):9.3f} "
              f"{np.median(s)-np.median(d):+8.3f}  {auc(s, d):.3f}{mark}")

    # STORE exactly the k chosen components (helper applies all it finds).
    keep = comps[:k]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    np.savez(
        out,
        mean=mu.astype(np.float32),
        components=keep.astype(np.float32),
        k=np.int64(k),
        dim=np.int64(sample.shape[1]),
        fit_n=np.int64(sample.shape[0]),
        fit_at=np.array(datetime.now(timezone.utc).isoformat()),
        method=np.array("all-but-top-k (Mu & Viswanath 2017), global fit"),
    )
    sz = os.path.getsize(out)
    print(f"\nSTORED {out}  ({sz} bytes)  k={k} dim={sample.shape[1]} fit_n={sample.shape[0]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-fit", type=int, default=150_000)
    ap.add_argument("--k", type=int, default=1, help="top-k PCs to remove (knee from --signals sweep)")
    ap.add_argument("--k-max", type=int, default=5, help="how many PCs to compute for the sweep")
    ap.add_argument("--out", default=ARTIFACT)
    ap.add_argument("--no-sweep", action="store_true",
                    help="skip the signal-level evidence sweep (already measured)")
    a = ap.parse_args()
    asyncio.run(run(a.n_fit, a.k, a.k_max, a.out, not a.no_sweep))


if __name__ == "__main__":
    main()
