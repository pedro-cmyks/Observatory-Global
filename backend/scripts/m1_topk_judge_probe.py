#!/usr/bin/env python3
"""M1 familia ① — sonda top-K + juez sobre la muestra A0 (n=40).

La calibración del confirmador (m1_confirmation_calibration.py, 2026-08-24)
midió que el juez DeepSeek "¿misma historia específica?" no acepta NINGÚN
vecino falso (0/26) pero solo confirma 3/40 del ARGMAX único — consistente
con la dispersión de argmax del Z4: la historia correcta existe cerca pero el
argmax cae en una hermana. Esta sonda mide la variante natural de la familia
①: el coseno PROPONE top-K (K=5, floor 0.80, centroides activos — la mecánica
del build u2) y el juez ELIGE entre ellos o rechaza todos.

Pregunta pre-declarada: ¿qué fracción de los 40 obtiene un adjunto confirmado,
y los adjuntos elegidos son la historia correcta? (El segundo juicio es a mano
sobre los pares aceptados — el output los lista para lectura.)

READ-ONLY sobre la base; llamadas externas solo el juez.
Artefacto: docs/research/recall-229/2026-08-24-m1-topk-judge-probe.json
"""

from __future__ import annotations

import asyncio
import gzip
import json
import os
import sys
import time

import asyncpg
import httpx
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
sys.path.insert(0, _BACKEND)

from scripts.ensemble.model_clients import call_llm  # noqa: E402
from scripts.m1_confirmation_calibration import (  # noqa: E402
    JUDGE_SYSTEM, judge_user, load_db_url, norm_hand)

FIXTURE = os.path.join(_BACKEND, "..", "docs", "research", "recall-229",
                       "fixtures", "2026-08-24-m1-shadow-fixture.json.gz")
A0_JSON = os.path.join(_BACKEND, "..", "docs", "research", "recall-229",
                       "2026-08-20-m1a0-unified-v2-coverage.json")
OUT_JSON = os.path.join(_BACKEND, "..", "docs", "research", "recall-229",
                        "2026-08-24-m1-topk-judge-probe.json")
K = 5
COS_FLOOR = 0.80


async def main() -> int:
    with gzip.open(FIXTURE, "rt") as f:
        fx = json.load(f)
    emb = {int(r["id"]): r["embedding"] for r in fx["a0_sample"]
           if r.get("embedding")}
    hand = {int(r["id"]): (norm_hand(r["hand_judgment"]), r["topic_id"],
                           r["label"], r["headline"], r.get("cc"),
                           r.get("source_family"))
            for r in json.load(open(A0_JSON))["u2_only_sample"]}
    ids = [i for i in hand if i in emb]
    print(f"[load] {len(ids)}/40 con embedding")

    conn = await asyncpg.connect(load_db_url(), statement_cache_size=0,
                                 timeout=30)
    try:
        async with conn.transaction():
            await conn.execute("SET LOCAL statement_timeout='90s'")
            await conn.execute("SET TRANSACTION READ ONLY")
            topics = await conn.fetch(
                "SELECT id, label, centroid_vec FROM dynamic_topics"
                " WHERE state='active' AND centroid_vec IS NOT NULL")
        print(f"[db] {len(topics)} topics activos con centroide")
        tids = [int(t["id"]) for t in topics]
        tlabels = {int(t["id"]): t["label"] for t in topics}
        C = np.array([t["centroid_vec"] for t in topics], dtype=np.float32)
        C /= (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)

        rows = []
        cand_topics: set[int] = set()
        for sid in ids:
            v = np.array(emb[sid], dtype=np.float32)
            v /= (np.linalg.norm(v) + 1e-9)
            sims = C @ v
            top = np.argsort(-sims)[:K]
            cands = [{"topic_id": f"dynamic-topic-{tids[j]}",
                      "tnum": tids[j], "label": tlabels[tids[j]],
                      "cos": round(float(sims[j]), 4)}
                     for j in top if sims[j] >= COS_FLOOR]
            for c in cands:
                cand_topics.add(c["tnum"])
            h, frozen_tid, frozen_label, headline, cc, fam = hand[sid]
            rows.append({"id": sid, "headline": headline, "cc": cc,
                         "source_family": fam, "hand_argmax": h,
                         "frozen_topic": frozen_tid,
                         "frozen_label": frozen_label, "candidates": cands})

        members: dict[int, list[str]] = {}
        for tnum in cand_topics:
            async with conn.transaction():
                await conn.execute("SET LOCAL statement_timeout='30s'")
                await conn.execute("SET TRANSACTION READ ONLY")
                mem = await conn.fetch(
                    "SELECT s.headline FROM topic_members tm"
                    " JOIN signals_v2 s ON s.id = tm.signal_id"
                    " WHERE tm.topic_id = $1 AND tm.role='evidence'"
                    "   AND tm.quarantined IS NOT TRUE AND s.headline IS NOT NULL"
                    " ORDER BY s.timestamp DESC LIMIT 3",
                    f"dynamic-topic-{tnum}")
            members[tnum] = [m["headline"] for m in mem]
    finally:
        await conn.close()

    stats = {"calls": 0, "yes": 0, "no": 0, "unsure": 0, "failed": 0}
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=90.0) as client:
        sem = asyncio.Semaphore(6)

        async def judge_pair(row: dict, cand: dict) -> None:
            user = judge_user(cand["label"], members.get(cand["tnum"], []),
                              row["headline"], row["cc"], row["source_family"])
            async with sem:
                stats["calls"] += 1
                try:
                    out = await call_llm(
                        "deepseek", system=JUDGE_SYSTEM, user=user,
                        client=client, max_tokens=60, temperature=0.0,
                        json_mode=True)
                    v = json.loads(out).get("same_story")
                    cand["judge"] = v if v in ("yes", "no", "unsure") else "unsure"
                except Exception as exc:
                    print(f"[judge] FAIL {row['id']}→{cand['topic_id']}: "
                          f"{exc!r}", file=sys.stderr)
                    cand["judge"] = "failed"
                    stats["failed"] += 1
                if cand["judge"] in stats:
                    stats[cand["judge"]] += 1

        await asyncio.gather(*(judge_pair(r, c) for r in rows
                               for c in r["candidates"]))
    wall = round(time.monotonic() - t0, 1)

    attached = 0
    for r in rows:
        pick = next((c for c in r["candidates"] if c.get("judge") == "yes"),
                    None)  # candidatos ya vienen orden cos desc
        r["picked"] = pick
        if pick:
            attached += 1

    print(f"\n[judge] {stats} wall={wall}s")
    print(f"[result] adjuntos confirmados: {attached}/{len(rows)}")
    print("\n— PARES ELEGIDOS (para juicio a mano) —")
    for r in rows:
        if r["picked"]:
            same = " (=argmax A0)" if r["picked"]["topic_id"] == r["frozen_topic"] else ""
            print(f"  [{r['hand_argmax']:>6}] {r['headline'][:80]}")
            print(f"      → {r['picked']['topic_id']} \"{r['picked']['label'][:70]}\""
                  f" cos={r['picked']['cos']}{same}")
    n_no = sum(1 for r in rows if r["hand_argmax"] == "no")
    resc = sum(1 for r in rows
               if r["hand_argmax"] == "no" and r["picked"]
               and r["picked"]["topic_id"] != r["frozen_topic"])
    print(f"\n[modo-ii] filas 'no' del argmax con adjunto NUEVO confirmado: "
          f"{resc}/{n_no}")

    artifact = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mandate": "M1 familia ① — sonda top-K+juez (pre-shadow, NO es el gate)",
        "k": K, "cos_floor": COS_FLOOR,
        "topics_pool": len(topics), "judge_stats": stats, "wall_s": wall,
        "attached_confirmed": attached, "n": len(rows),
        "rows": rows,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(artifact, f, ensure_ascii=False, indent=1)
    print(f"[out] {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
