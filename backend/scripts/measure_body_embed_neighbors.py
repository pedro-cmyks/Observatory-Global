#!/usr/bin/env python3
"""F3b measurement gate (spec 2026-07-20 §6) — do BODY embeddings behave in the
headline-calibrated e5 space?

The /connections neighbor lane runs whitened e5 cosine with NEIGHBOR_TAU=0.40,
calibrated on HEADLINE-derived centroids. Article bodies (300-800 words) are a
different text distribution — this harness measures whether body embeddings
separate own-topic from other-topic BEFORE any serving wire (the engine-surgery
rule: measure first, serve second).

Method (read-only vs the engine; only writes the shared pinned_articles cache):
  1. Sample active dynamic topics w/ centroid_vec + up to 3 evidence URLs each.
  2. Fetch bodies through the F1 pipeline (bounded wait; partial yield normal).
  3. Embed bodies + their headlines (passage: prefix, snapshot-identical
     pooling via research_semantic.embed_texts).
  4. Pos pairs = text ↔ OWN topic centroid; neg = text ↔ 8 other centroids.
     Raw + whitened (all-but-top k=1) cosine; AUC + p50 gap + tau behavior.
  5. Verdict PASS iff whitened body AUC ≥ headline AUC − 0.05 AND tau=0.40
     keeps ≥60% of pos and ≤10% of neg. FAIL → do NOT serve (honest negative).

Run (M1, mindful):
  cd backend && taskpolicy -b /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.measure_body_embed_neighbors
Artifacts: docs/research/body-embed/2026-07-20-body-embed-measurement.{md,json}
"""
from __future__ import annotations

import asyncio
import json
import os
import random
import sys
from pathlib import Path

import asyncpg
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import db  # noqa: E402

N_TOPICS = 24
URLS_PER_TOPIC = 6
NEG_PER_TEXT = 8
NEIGHBOR_TAU = 0.40      # the served whitened connect threshold
BODY_CAP_CHARS = 4000
FETCH_WAIT_S = 300       # poll ceiling — 144 urls at concurrency 3 need minutes
OUT_DIR = Path(__file__).resolve().parents[2] / "docs" / "research" / "body-embed"

_TOPIC_SQL = """
SELECT dt.id, dt.label, dt.centroid_vec
FROM dynamic_topics dt
WHERE dt.state = 'active' AND dt.centroid_vec IS NOT NULL AND NOT dt.is_umbrella
ORDER BY dt.last_seen DESC
LIMIT $1
"""

_EVIDENCE_SQL = """
SELECT s.source_url, s.headline
FROM topic_members tm JOIN signals_v2 s ON s.id = tm.signal_id
WHERE tm.topic_id = $1 AND tm.role = 'evidence' AND tm.quarantined IS NOT TRUE
  AND s.source_url LIKE 'http%' AND s.headline IS NOT NULL
ORDER BY tm.assigned_at DESC
LIMIT $2
"""


def _auc(pos: list[float], neg: list[float]) -> float:
    if not pos or not neg:
        return float("nan")
    wins = ties = 0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1
            elif p == n:
                ties += 1
    return (wins + 0.5 * ties) / (len(pos) * len(neg))


def _cos(a: np.ndarray, b: np.ndarray) -> float:
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(a @ b / (na * nb))


def _stats(pos: list[float], neg: list[float]) -> dict:
    return {
        "n_pos": len(pos), "n_neg": len(neg),
        "pos_p50": round(float(np.median(pos)), 4) if pos else None,
        "neg_p50": round(float(np.median(neg)), 4) if neg else None,
        "gap_p50": round(float(np.median(pos) - np.median(neg)), 4) if pos and neg else None,
        "auc": round(_auc(pos, neg), 4),
        "pos_ge_tau": round(sum(1 for x in pos if x >= NEIGHBOR_TAU) / len(pos), 3) if pos else None,
        "neg_ge_tau": round(sum(1 for x in neg if x >= NEIGHBOR_TAU) / len(neg), 3) if neg else None,
    }


async def main() -> None:
    random.seed(20260720)
    db.pool = await asyncpg.create_pool(
        os.environ["DATABASE_URL"], min_size=1, max_size=2, command_timeout=60,
        statement_cache_size=0,
    )
    from app.services.article_fetch import enqueue_fetches, full_texts_for
    from app.services.research_semantic import embed_texts
    from app.services.whitening import apply_whitening, load_whitening

    async with db.pool.acquire() as conn:
        topics = await conn.fetch(_TOPIC_SQL, N_TOPICS)
        evidence: dict[int, list[dict]] = {}
        for t in topics:
            # topic_members keys on the serving id ('dynamic-topic-<n>')
            rows = await conn.fetch(_EVIDENCE_SQL, f"dynamic-topic-{t['id']}", URLS_PER_TOPIC)
            evidence[t["id"]] = [dict(r) for r in rows]

    # 2. fetch bodies through the F1 pipeline
    all_urls = [r["source_url"] for tid in evidence for r in evidence[tid]]
    all_urls = list(dict.fromkeys(all_urls))
    print(f"topics={len(topics)} urls={len(all_urls)} — fetching…")
    from app.services.article_fetch import article_states
    # enqueue accepts ≤64 per call — chunk the sample
    for off in range(0, len(all_urls), 60):
        await enqueue_fetches(all_urls[off:off + 60])
    waited = 0
    while waited < FETCH_WAIT_S:
        await asyncio.sleep(10)
        waited += 10
        states = []
        for off in range(0, len(all_urls), 60):
            states += await article_states(all_urls[off:off + 60])
        pending = sum(1 for s in states if s.get("status") == "pending")
        ok_n = sum(1 for s in states if s.get("status") == "ok")
        print(f"  t={waited}s ok={ok_n} pending={pending}")
        if pending == 0 and len(states) >= len(all_urls):
            break
    texts = {}
    for off in range(0, len(all_urls), 60):
        texts.update(await full_texts_for(all_urls[off:off + 60], cap_chars=BODY_CAP_CHARS))
    print(f"bodies fetched: {len(texts)}/{len(all_urls)}")

    # 3. eval set: (topic, headline, body)
    centroid_by_id = {
        t["id"]: np.asarray(json.loads(t["centroid_vec"])
                            if isinstance(t["centroid_vec"], str) else list(t["centroid_vec"]),
                            dtype=np.float32)
        for t in topics
    }
    samples = []   # (topic_id, headline, body)
    for tid, rows in evidence.items():
        for r in rows:
            body = (texts.get(r["source_url"]) or {}).get("text")
            if body:
                samples.append((tid, r["headline"], body))
    covered_topics = sorted({s[0] for s in samples})
    print(f"samples={len(samples)} across {len(covered_topics)} topics")
    if len(samples) < 8 or len(covered_topics) < 4:
        print("UNDERPOWERED — refusing to emit a verdict on this few samples.")
        verdict = "underpowered"
        result = {"verdict": verdict, "samples": len(samples), "topics": len(covered_topics)}
    else:
        # 4. embed (snapshot-identical pooling; passage prefix like the engine)
        body_vecs = embed_texts([f"passage: {b[:BODY_CAP_CHARS]}" for _, _, b in samples])
        head_vecs = embed_texts([f"passage: {h}" for _, h, _ in samples])
        assert body_vecs is not None and head_vecs is not None, "embedder unavailable"
        body_vecs = [np.asarray(v, dtype=np.float32) for v in body_vecs]
        head_vecs = [np.asarray(v, dtype=np.float32) for v in head_vecs]

        w = load_whitening()

        def _wvec(v: np.ndarray) -> np.ndarray:
            out = apply_whitening(v.reshape(1, -1), w)[0]
            n = np.linalg.norm(out)
            return out / n if n else out

        wcentroid = {tid: _wvec(c) for tid, c in centroid_by_id.items()}
        topic_ids = list(centroid_by_id)

        def _pairs(vecs: list[np.ndarray]) -> dict:
            raw_pos, raw_neg, w_pos, w_neg = [], [], [], []
            for (tid, _h, _b), v in zip(samples, vecs):
                own = centroid_by_id[tid]
                raw_pos.append(_cos(v, own))
                wv = _wvec(v)
                w_pos.append(float(wv @ wcentroid[tid]))
                others = [x for x in topic_ids if x != tid]
                for o in random.sample(others, min(NEG_PER_TEXT, len(others))):
                    raw_neg.append(_cos(v, centroid_by_id[o]))
                    w_neg.append(float(wv @ wcentroid[o]))
            return {"raw": _stats(raw_pos, raw_neg), "whitened": _stats(w_pos, w_neg)}

        body_m = _pairs(body_vecs)
        head_m = _pairs(head_vecs)
        bw, hw = body_m["whitened"], head_m["whitened"]
        passed = (
            bw["auc"] >= hw["auc"] - 0.05
            and (bw["pos_ge_tau"] or 0) >= 0.60
            and (bw["neg_ge_tau"] or 1) <= 0.10
        )
        verdict = "PASS" if passed else "FAIL"
        result = {
            "verdict": verdict, "samples": len(samples), "topics": len(covered_topics),
            "neighbor_tau": NEIGHBOR_TAU, "body": body_m, "headline_baseline": head_m,
            "criteria": "whitened body AUC >= headline AUC - 0.05 AND pos@tau>=0.60 AND neg@tau<=0.10",
        }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "2026-07-20-body-embed-measurement.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    await db.pool.close()


if __name__ == "__main__":
    asyncio.run(main())
