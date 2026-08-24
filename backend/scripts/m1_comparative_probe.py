#!/usr/bin/env python3
"""M1 familia ① — sonda A1c: top-K COMPARATIVO sobre pool activos∪candidatos.

Lo que las dos sondas previas enseñaron (2026-08-24):
  - Juez binario sobre argmax único: 0 falsos aceptados pero recall bajo —
    hereda la dispersión de argmax (m1_confirmation_calibration.py).
  - Juez binario sobre top-5 de ACTIVOS: comparaciones múltiples — ~1.6% de
    falso-yes por par × K pares = 3/5 adjuntos falsos; y el pool de solo
    activos EXCLUYE la historia correcta cuando vive como 'candidate'
    (dt-9844, dt-15350) (m1_topk_judge_probe.py).

A1c corrige ambas: pool = active ∪ candidate, y UNA llamada por señal con los
K candidatos numerados — el juez ELIGE uno o ninguno (juicio comparativo, no
K binarios independientes). Es además la forma más barata (1 call/señal).

READ-ONLY; artefacto: 2026-08-24-m1-comparative-probe.json
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
    load_db_url, norm_hand)

FIXTURE = os.path.join(_BACKEND, "..", "docs", "research", "recall-229",
                       "fixtures", "2026-08-24-m1-shadow-fixture.json.gz")
A0_JSON = os.path.join(_BACKEND, "..", "docs", "research", "recall-229",
                       "2026-08-20-m1a0-unified-v2-coverage.json")
OUT_JSON = os.path.join(_BACKEND, "..", "docs", "research", "recall-229",
                        "2026-08-24-m1-comparative-probe.json")
K = 5
COS_FLOOR = 0.80

PICK_SYSTEM = (
    "You match a news headline to the story topic it belongs to. You are "
    "given numbered candidate topics (label + recent member headlines). "
    "Answer STRICT JSON only: {\"pick\": <candidate number>} or "
    "{\"pick\": null}. Pick a candidate ONLY if the headline reports the "
    "SAME specific real-world story — same event and actors/place. Same "
    "theme, same country, a similar category, or a twin story elsewhere "
    "does NOT qualify. If none qualifies, pick null. Be strict: a wrong "
    "attachment is worse than no attachment."
)


def pick_user(headline: str, cc: str | None, fam: str | None,
              cands: list[dict], members: dict[int, list[str]]) -> str:
    lines = []
    for i, c in enumerate(cands, 1):
        lines.append(f"{i}. \"{c['label']}\"")
        for h in members.get(c["tnum"], [])[:2]:
            lines.append(f"   - {h}")
    tag = ", ".join(x for x in (cc, fam) if x)
    return (f"CANDIDATE headline ({tag}): {headline}\n\nCandidate topics:\n"
            + "\n".join(lines) + "\n\nWhich topic, if any, is the same "
            "specific story?")


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
            await conn.execute("SET LOCAL statement_timeout='120s'")
            await conn.execute("SET TRANSACTION READ ONLY")
            topics = await conn.fetch(
                "SELECT id, label, state FROM dynamic_topics"
                " WHERE state IN ('active','candidate')"
                "   AND centroid_vec IS NOT NULL")
            print(f"[db] pool {len(topics)} topics "
                  f"({sum(1 for t in topics if t['state']=='active')} active)")
            vecs = await conn.fetch(
                "SELECT id, centroid_vec FROM dynamic_topics"
                " WHERE state IN ('active','candidate')"
                "   AND centroid_vec IS NOT NULL")
        tids = [int(t["id"]) for t in vecs]
        meta = {int(t["id"]): (t["label"], t["state"]) for t in topics}
        C = np.array([t["centroid_vec"] for t in vecs], dtype=np.float32)
        C /= (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)

        rows = []
        cand_topics: set[int] = set()
        for sid in ids:
            v = np.array(emb[sid], dtype=np.float32)
            v /= (np.linalg.norm(v) + 1e-9)
            sims = C @ v
            top = np.argsort(-sims)[:K]
            cands = [{"topic_id": f"dynamic-topic-{tids[j]}",
                      "tnum": tids[j], "label": meta[tids[j]][0],
                      "state": meta[tids[j]][1],
                      "cos": round(float(sims[j]), 4)}
                     for j in top if sims[j] >= COS_FLOOR]
            cand_topics.update(c["tnum"] for c in cands)
            h, ftid, flabel, headline, cc, fam = hand[sid]
            rows.append({"id": sid, "headline": headline, "cc": cc,
                         "source_family": fam, "hand_argmax": h,
                         "frozen_topic": ftid, "frozen_label": flabel,
                         "candidates": cands})

        members: dict[int, list[str]] = {}
        for tnum in cand_topics:
            async with conn.transaction():
                await conn.execute("SET LOCAL statement_timeout='30s'")
                await conn.execute("SET TRANSACTION READ ONLY")
                mem = await conn.fetch(
                    "SELECT s.headline FROM topic_members tm"
                    " JOIN signals_v2 s ON s.id = tm.signal_id"
                    " WHERE tm.topic_id = $1 AND tm.role='evidence'"
                    "   AND tm.quarantined IS NOT TRUE"
                    "   AND s.headline IS NOT NULL"
                    " ORDER BY s.timestamp DESC LIMIT 2",
                    f"dynamic-topic-{tnum}")
            members[tnum] = [m["headline"] for m in mem]
    finally:
        await conn.close()

    stats = {"calls": 0, "picked": 0, "null": 0, "failed": 0}
    t0 = time.monotonic()
    async with httpx.AsyncClient(timeout=90.0) as client:
        sem = asyncio.Semaphore(6)

        async def one(row: dict) -> None:
            if not row["candidates"]:
                row["pick"] = None
                return
            user = pick_user(row["headline"], row["cc"], row["source_family"],
                             row["candidates"], members)
            async with sem:
                stats["calls"] += 1
                try:
                    out = await call_llm(
                        "deepseek", system=PICK_SYSTEM, user=user,
                        client=client, max_tokens=40, temperature=0.0,
                        json_mode=True)
                    p = json.loads(out).get("pick")
                    if isinstance(p, int) and 1 <= p <= len(row["candidates"]):
                        row["pick"] = row["candidates"][p - 1]
                        stats["picked"] += 1
                    else:
                        row["pick"] = None
                        stats["null"] += 1
                except Exception as exc:
                    print(f"[pick] FAIL {row['id']}: {exc!r}", file=sys.stderr)
                    row["pick"] = None
                    stats["failed"] += 1

        await asyncio.gather(*(one(r) for r in rows))
    wall = round(time.monotonic() - t0, 1)

    print(f"\n[pick] {stats} wall={wall}s")
    print("\n— ADJUNTOS ELEGIDOS (juicio a mano abajo de cada uno) —")
    for r in rows:
        if r.get("pick"):
            same = " (=argmax A0)" if r["pick"]["topic_id"] == r["frozen_topic"] else ""
            print(f"  [{r['hand_argmax']:>6}] {r['headline'][:84]}")
            print(f"      → {r['pick']['topic_id']} [{r['pick']['state']}] "
                  f"\"{r['pick']['label'][:72]}\" cos={r['pick']['cos']}{same}")
    artifact = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mandate": "M1 familia ① — sonda A1c comparativa (pre-shadow)",
        "k": K, "cos_floor": COS_FLOOR, "pool": "active+candidate",
        "stats": stats, "wall_s": wall, "rows": rows,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(artifact, f, ensure_ascii=False, indent=1)
    print(f"[out] {OUT_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
