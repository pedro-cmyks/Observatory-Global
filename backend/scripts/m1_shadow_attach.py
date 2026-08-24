#!/usr/bin/env python3
"""M1-A2 — la assignment lane familia ① EN SOMBRA.

Mandato: prereg `docs/superpowers/specs/2026-08-20-assignment-lane-
preregistration.md` (6 barras congeladas) + calibración
`docs/research/recall-229/2026-08-24-m1-family1-calibration.md` (la forma
ganadora: COMPARATIVO top-K sobre active∪candidate; 3 modos de fallo con
veto). Nada de esto toca serving: el serving lee engine_version='v1-compat'
(verificado thread_intelligence.py:42); la sombra escribe
engine_version='m1-shadow-v0' y su reversión es
`DELETE FROM topic_members WHERE engine_version='m1-shadow-v0'` + ledger.

Pipeline por señal servible SIN historia en la ventana:
  1. embedding (signal_embeddings; sin fila = skip contado)
  2. top-K=5 coseno >=0.80 sobre centroides active∪candidate
  3. vetos PRE-juez (calibración §"la brecha a 90% tiene nombre"):
     (a) bucket-vago FUERA DEL POOL: is_junk, label_status='too_broad', y
         la heurística DF congelada v0 — un label es vago si TODOS sus
         subject-tokens (P-NUEVO) tienen document-frequency >= TAU_DF=25
         sobre el pool de labels (data-driven, sin vocabulario a mano:
         "Crime and Tragedy" cae, "Mushroom Murder Appeal" sobrevive).
     (b) persona-conflicto (clase Shlosberg→Shipacheva): veto al candidato
         si la señal trae personas Y el topic trae personas de miembros Y
         no comparten NINGUNA (casefold) Y cos < 0.90 (el exempt alto-cos
         evita vetar adjuntos verdaderos con NER ralo). Caveat declarado:
         cross-script (cirílico↔latino) NO se resuelve aquí — se mide.
  4. juez comparativo (1 llamada DeepSeek/señal, pick-or-null,
     precision-first: null/fail = NO adjuntar) — prompt REUSADO de
     m1_comparative_probe.py.

--dry-run (default): cero escrituras; solo ledger + métricas.
--execute: INSERT sombra (columnas introspeccionadas, jamás asumidas).
--sample N (default 2000, seed 229 vía setseed): noches de calibración de
tasas; --sample 0 = población completa (cuidado con el costo del juez).
Ledger JSONL: docs/research/recall-229/shadow-ledger/<runid>.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone

import asyncpg
import httpx
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
sys.path.insert(0, _BACKEND)

from scripts.ensemble.model_clients import call_llm  # noqa: E402
from scripts.m1_confirmation_calibration import (  # noqa: E402
    JUDGE_SYSTEM, judge_user, load_db_url, signal_persons)
from scripts.m1_comparative_probe import pick_user  # noqa: E402

# PICK_SYSTEM de la sonda + la regla anti-hermano (corrida 161438Z: con
# varios fragmentos de la misma zona, el juez debe exigir el MISMO evento,
# no el tema vecino más parecido).
PICK_SYSTEM = (
    "You match a news headline to the story topic it belongs to. You are "
    "given candidate topics (label + recent member headlines). Answer "
    "STRICT JSON only: {\"pick\": <candidate number>} or {\"pick\": null}. "
    "Pick a candidate ONLY if the headline reports the SAME specific "
    "real-world story — same event and actors/place. Same theme, same "
    "country, a similar category, or a twin story elsewhere does NOT "
    "qualify. If several candidates are near the headline's zone, pick the "
    "one whose label names the SAME event as the headline — if none does, "
    "pick null. Be strict: a wrong attachment is worse than no attachment."
)
from scripts.m1a0_unified_v2_coverage import SERVABLE_SQL  # noqa: E402
from scripts.measure_landing_predicate import (  # noqa: E402
    p8_subject_tokens, unicode_norm)

K = 5
COS_FLOOR = 0.80
TAU_DF = 25            # bucket-vago v0: todos los subject-tokens con df>=25
PERSON_VETO_COS_EXEMPT = 0.90
SEED = 229
LEDGER_DIR = os.path.join(_BACKEND, "..", "docs", "research", "recall-229",
                          "shadow-ledger")
ENGINE_VERSION = "m1-shadow-v0"

# Paridad con el prereg/A0: "con historia" = lo que el SERVING ve
# (engine_version='v1-compat', thread_intelligence.py:42). La foto u2 y la
# propia sombra NO cuentan como historia aquí — la primera corrida sin este
# filtro dio un 63% "con historia" imposible (vs 7% del A0) y una muestra
# sesgada a señales sin embedding.
NO_STORY_SQL = (
    "NOT EXISTS (SELECT 1 FROM topic_members tm WHERE tm.signal_id = s.id"
    " AND tm.role = 'evidence' AND tm.quarantined IS NOT TRUE"
    " AND tm.engine_version = 'v1-compat'"
    " AND tm.topic_id LIKE 'dynamic-topic-%')"
)


# ---------------- vetos puros (testeados en test_m1_shadow_attach.py) -------

def label_token_df(labels: list[str]) -> Counter:
    """df de cada subject-token sobre el pool de labels (1 por label)."""
    df: Counter = Counter()
    for lab in labels:
        df.update(set(p8_subject_tokens(unicode_norm(lab))))
    return df


def is_bucket_vague(label: str | None, df: Counter, tau: int = TAU_DF) -> bool:
    """True = ningún token del label es específico (todos df>=tau) o el
    label no tiene subject-tokens. Regla congelada v0 — se mide, no se
    retoca por caso."""
    toks = p8_subject_tokens(unicode_norm(label))
    if not toks:
        return True
    return all(df.get(t, 0) >= tau for t in toks)


def label_persons(label: str | None, member_persons: set[str]) -> set[str]:
    """Personas que el LABEL nombra: miembros cuyo nombre (>=2 tokens de la
    persona) aparece en el label normalizado. La calibración definió el veto
    sobre persona-EN-EL-LABEL (clase Shlosberg→Shipacheva), no sobre el pool
    completo de personas de miembros — la v0.1 amplia vetó 27% de candidatos
    y mató hogares correctos."""
    lab_toks = set(unicode_norm(label).split())
    out = set()
    for p in member_persons:
        toks = [t for t in unicode_norm(p).split() if len(t) >= 3]
        if not toks:
            continue
        # regla apellido: el ÚLTIMO token del nombre (>=4 chars) presente
        # como token del label — "Journalist Shipacheva Sentenced" nombra a
        # "maria shipacheva" por su apellido; "Donald Announces Plan" NO
        # nombra a "donald duck" (duck ausente).
        surname = toks[-1]
        if len(surname) >= 4 and surname in lab_toks:
            out.add(p)
    return out


def person_conflict(sig_persons: set[str], lbl_persons: set[str],
                    cos: float) -> bool:
    """Veto clase gemela-de-persona (v0.2): SOLO cuando el label del
    candidato nombra una persona, la señal trae personas, y no comparten
    ninguna, con exempt de coseno alto."""
    if cos >= PERSON_VETO_COS_EXEMPT:
        return False
    if not sig_persons or not lbl_persons:
        return False
    return not (sig_persons & lbl_persons)


def binomial_ci(k: int, n: int) -> tuple[float, float]:
    """Wilson 95%."""
    if n == 0:
        return (0.0, 0.0)
    p, z = k / n, 1.96
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# ---------------- run ---------------------------------------------------------

async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--sample", type=int, default=2000,
                    help="0 = población completa (costo juez proporcional)")
    ap.add_argument("--execute", action="store_true",
                    help="escribe engine_version='m1-shadow-v0' (default: dry-run)")
    ap.add_argument("--judge-concurrency", type=int, default=6)
    args = ap.parse_args()
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    os.makedirs(LEDGER_DIR, exist_ok=True)
    ledger_path = os.path.join(LEDGER_DIR, f"shadow-{run_id}.jsonl")
    ledger = open(ledger_path, "a")

    def log_ledger(obj: dict) -> None:
        ledger.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")
        ledger.flush()

    conn = await asyncpg.connect(load_db_url(), statement_cache_size=0,
                                 timeout=30)
    try:
        # -- población + denominadores de G-RECALL (misma transacción RO) ----
        async with conn.transaction():
            await conn.execute("SET LOCAL statement_timeout='120s'")
            await conn.execute("SET TRANSACTION READ ONLY")
            denom = await conn.fetchrow(
                f"SELECT count(*) AS servable,"
                f" count(*) FILTER (WHERE NOT ({NO_STORY_SQL})) AS with_story"
                f" FROM signals_v2 s WHERE s.timestamp > now() - ($1||' hours')::interval"
                f" AND {SERVABLE_SQL}", str(args.hours))
            await conn.execute(f"SELECT setseed({SEED / 1000.0})")
            lim = "" if args.sample == 0 else f" ORDER BY random() LIMIT {int(args.sample)}"
            pop = await conn.fetch(
                f"SELECT s.id, s.headline, s.country_code AS cc,"
                f" s.source_family, s.persons, s.nlp_persons"
                f" FROM signals_v2 s WHERE s.timestamp > now() - ($1||' hours')::interval"
                f" AND {SERVABLE_SQL} AND {NO_STORY_SQL}{lim}", str(args.hours))
        print(f"[pop] servible={denom['servable']} con_historia={denom['with_story']}"
              f" ({denom['with_story']/max(denom['servable'],1):.1%}) · "
              f"muestra sin-historia n={len(pop)}")

        ids = [int(r["id"]) for r in pop]
        async with conn.transaction():
            await conn.execute("SET LOCAL statement_timeout='90s'")
            await conn.execute("SET TRANSACTION READ ONLY")
            embs = await conn.fetch(
                "SELECT signal_id, vec::text AS v FROM signal_embeddings"
                " WHERE signal_id = ANY($1::bigint[])", ids)
            topics = await conn.fetch(
                "SELECT id, label, state, centroid_vec,"
                " COALESCE(is_junk, false) AS is_junk, label_status"
                " FROM dynamic_topics WHERE state IN ('active','candidate')"
                " AND centroid_vec IS NOT NULL")
        emap = {int(r["signal_id"]): json.loads(r["v"]) for r in embs}
        print(f"[emb] {len(emap)}/{len(pop)} con embedding")

        # -- pool con veto (a) bucket-vago/junk/too_broad --------------------
        df = label_token_df([t["label"] or "" for t in topics])
        pool, veto_pool = [], Counter()
        for t in topics:
            if t["is_junk"]:
                veto_pool["junk"] += 1
                continue
            if (t["label_status"] or "") == "too_broad":
                veto_pool["too_broad"] += 1
                continue
            if is_bucket_vague(t["label"], df):
                veto_pool["bucket_vague"] += 1
                continue
            pool.append(t)
        print(f"[pool] {len(topics)} topics → {len(pool)} tras veto (a): {dict(veto_pool)}")
        tids = [int(t["id"]) for t in pool]
        meta = {int(t["id"]): (t["label"], t["state"]) for t in pool}
        C = np.array([t["centroid_vec"] for t in pool], dtype=np.float32)
        C /= (np.linalg.norm(C, axis=1, keepdims=True) + 1e-9)

        # -- candidatos por señal -------------------------------------------
        rows, cand_topics = [], set()
        stats = Counter()
        for r in pop:
            sid = int(r["id"])
            if sid not in emap:
                stats["skip_no_embedding"] += 1
                continue
            v = np.array(emap[sid], dtype=np.float32)
            v /= (np.linalg.norm(v) + 1e-9)
            sims = C @ v
            top = np.argsort(-sims)[:K]
            cands = [{"topic_id": f"dynamic-topic-{tids[j]}", "tnum": tids[j],
                      "label": meta[tids[j]][0], "state": meta[tids[j]][1],
                      "cos": round(float(sims[j]), 4)}
                     for j in top if sims[j] >= COS_FLOOR]
            if not cands:
                stats["no_candidate_over_floor"] += 1
                log_ledger({"id": sid, "outcome": "no_candidate"})
                continue
            cand_topics.update(c["tnum"] for c in cands)
            rows.append({"id": sid, "headline": r["headline"], "cc": r["cc"],
                         "source_family": r["source_family"],
                         "sig_persons": signal_persons(dict(r)),
                         "candidates": cands})
        print(f"[cand] {len(rows)} señales con candidato ≥{COS_FLOOR} · {dict(stats)}")

        # -- contexto de candidatos: headlines + personas de miembros --------
        members: dict[int, list[str]] = {}
        topic_persons: dict[int, set[str]] = {}
        topic_countries: dict[int, set[str]] = {}
        for tnum in cand_topics:
            async with conn.transaction():
                await conn.execute("SET LOCAL statement_timeout='30s'")
                await conn.execute("SET TRANSACTION READ ONLY")
                mem = await conn.fetch(
                    "SELECT s.headline, s.persons, s.nlp_persons, s.country_code"
                    " FROM topic_members tm JOIN signals_v2 s ON s.id=tm.signal_id"
                    " WHERE tm.topic_id=$1 AND tm.role='evidence'"
                    "   AND tm.quarantined IS NOT TRUE AND s.headline IS NOT NULL"
                    " ORDER BY s.timestamp DESC LIMIT 25",
                    f"dynamic-topic-{tnum}")
            members[tnum] = [m["headline"] for m in mem[:2]]
            ps: set[str] = set()
            ccs: set[str] = set()
            for m in mem:
                ps |= signal_persons(dict(m))
                if m["country_code"]:
                    ccs.add(m["country_code"])
            topic_persons[tnum] = ps
            topic_countries[tnum] = ccs

        # -- veto (b) persona-conflicto por candidato (v0.2: label-persona) --
        import random as _random
        for row in rows:
            kept = []
            for c in row["candidates"]:
                lp = label_persons(c["label"],
                                   topic_persons.get(c["tnum"], set()))
                if person_conflict(row["sig_persons"], lp, c["cos"]):
                    c["veto"] = "person_conflict"
                    stats["veto_person_conflict"] += 1
                else:
                    kept.append(c)
            # orden ALEATORIO seedeado por señal en el prompt: la corrida
            # 20260824T161438Z mostró sesgo de posición del juez (eligió al
            # hermano listado primero teniendo el hogar correcto más abajo).
            _random.Random(SEED * 1_000_003 + row["id"]).shuffle(kept)
            row["judged_candidates"] = kept
        judgeable = [r for r in rows if r["judged_candidates"]]
        print(f"[veto-b] persona-conflicto vetó {stats['veto_person_conflict']}"
              f" candidatos · {len(judgeable)} señales van al juez")

        # -- juez comparativo ------------------------------------------------
        jstats = Counter()
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=90.0) as client:
            sem = asyncio.Semaphore(args.judge_concurrency)

            async def one(row: dict) -> None:
                user = pick_user(row["headline"], row["cc"],
                                 row["source_family"],
                                 row["judged_candidates"], members)
                async with sem:
                    jstats["calls"] += 1
                    try:
                        out = await call_llm(
                            "deepseek", system=PICK_SYSTEM, user=user,
                            client=client, max_tokens=40, temperature=0.0,
                            json_mode=True)
                        p = json.loads(out).get("pick")
                        if isinstance(p, int) and 1 <= p <= len(row["judged_candidates"]):
                            row["pick"] = row["judged_candidates"][p - 1]
                            jstats["picked"] += 1
                        else:
                            row["pick"] = None
                            jstats["null"] += 1
                    except Exception as exc:
                        print(f"[judge] FAIL {row['id']}: {exc!r}", file=sys.stderr)
                        row["pick"] = None
                        jstats["failed"] += 1
                # v0.4 — DOBLE VOTO: el pick del comparativo debe sobrevivir
                # el juez BINARIO (sonda 1: 0 falsos aceptados). Mata la
                # clase hermano-de-evento (bird-hit→hydraulic-failure) que
                # el comparativo acepta al elegir "el más cercano de la
                # zona". +1 llamada SOLO cuando hay pick.
                if row.get("pick"):
                    p = row["pick"]
                    user2 = judge_user(p["label"], members.get(p["tnum"], []),
                                       row["headline"], row["cc"],
                                       row["source_family"])
                    jstats["confirm_calls"] += 1
                    try:
                        out2 = await call_llm(
                            "deepseek", system=JUDGE_SYSTEM, user=user2,
                            client=client, max_tokens=60, temperature=0.0,
                            json_mode=True)
                        v2 = json.loads(out2).get("same_story")
                    except Exception as exc:
                        print(f"[confirm] FAIL {row['id']}: {exc!r}",
                              file=sys.stderr)
                        v2 = "failed"
                    if v2 != "yes":
                        jstats[f"confirm_veto_{v2}"] += 1
                        row["pick_vetoed_by_confirm"] = {**p, "confirm": v2}
                        row["pick"] = None
                log_ledger({"id": row["id"], "headline": row["headline"],
                            "cc": row["cc"],
                            "candidates": row["candidates"],
                            "pick": row.get("pick"),
                            "confirm_vetoed": row.get("pick_vetoed_by_confirm"),
                            "outcome": "judged"})

            await asyncio.gather(*(one(r) for r in judgeable))
        wall = round(time.monotonic() - t0, 1)
        # -- confirmación post-juez v0.3: coherencia de país -----------------
        # Clase residual de la corrida 161844Z (gemelo-de-categoría entre
        # países: bus NL→"Peru Plane Crash", PFAS AU→ataxia): el pick muere
        # si la señal trae país, el topic trae países de miembros, y el país
        # de la señal NO está entre ellos. Ambos-desconocidos = pasa (no se
        # inventa un veto sin datos). Gemelos DENTRO del mismo país
        # (Reno→Washington, ambos US) quedan como residual declarado.
        for r in judgeable:
            p = r.get("pick")
            if not p:
                continue
            tcc = topic_countries.get(p["tnum"], set())
            if r["cc"] and tcc and r["cc"] not in tcc:
                jstats["veto_country_incoherent"] += 1
                log_ledger({"id": r["id"], "outcome": "pick_vetoed_country",
                            "pick": p, "signal_cc": r["cc"],
                            "topic_ccs": sorted(tcc)})
                r["pick"] = None
        picks = [r for r in judgeable if r.get("pick")]

        # -- escritura sombra (solo --execute) -------------------------------
        written = 0
        if args.execute and picks:
            cols = {r["column_name"] for r in await conn.fetch(
                "SELECT column_name FROM information_schema.columns"
                " WHERE table_name='topic_members'")}
            base = ["signal_id", "topic_id", "role", "engine_version"]
            extra = [c for c in ("assigned_at", "method", "model_version",
                                 "confidence") if c in cols]
            fields = base + extra
            ph = ", ".join(f"${i+1}" for i in range(len(fields)))
            sql = (f"INSERT INTO topic_members ({', '.join(fields)})"
                   f" VALUES ({ph}) ON CONFLICT DO NOTHING")
            extra_vals = {"assigned_at": lambda r: datetime.now(timezone.utc),
                          "method": lambda r: "m1-family1-comparative",
                          "model_version": lambda r: ENGINE_VERSION,
                          "confidence": lambda r: r["pick"]["cos"]}
            for r in picks:
                vals: list = [r["id"], r["pick"]["topic_id"], "evidence",
                              ENGINE_VERSION]
                vals += [extra_vals[c](r) for c in extra]
                await conn.execute(sql, *vals)
                written += 1
            print(f"[write] {written} filas {ENGINE_VERSION} (reversión: DELETE por engine_version)")
        elif picks:
            print(f"[dry-run] {len(picks)} adjuntos NO escritos (usa --execute)")
    finally:
        await conn.close()
        ledger.close()

    # -- métricas de la corrida ---------------------------------------------
    n = len(pop)
    attach_rate = len(picks) / n if n else 0.0
    lo, hi = binomial_ci(len(picks), n)
    no_story = denom["servable"] - denom["with_story"]
    proj = ((denom["with_story"] + no_story * attach_rate) /
            max(denom["servable"], 1))
    proj_lo = (denom["with_story"] + no_story * lo) / max(denom["servable"], 1)
    proj_hi = (denom["with_story"] + no_story * hi) / max(denom["servable"], 1)
    summary = {
        "run_id": run_id, "hours": args.hours, "sample": args.sample,
        "execute": args.execute,
        "servable": denom["servable"], "with_story_now": denom["with_story"],
        "population_no_story_sampled": n,
        "skips": dict(stats), "pool_vetoes": dict(veto_pool),
        "judge": dict(jstats), "judge_wall_s": wall,
        "attached": len(picks), "written": written,
        "attach_rate": round(attach_rate, 4),
        "attach_rate_ci95": [round(lo, 4), round(hi, 4)],
        "g_recall_projection": {
            "now": round(denom["with_story"] / max(denom["servable"], 1), 4),
            "union_projected": round(proj, 4),
            "ci95": [round(proj_lo, 4), round(proj_hi, 4)],
            "bar": 0.20,
        },
        "ledger": ledger_path,
    }
    log2 = open(ledger_path, "a")
    log2.write(json.dumps({"summary": summary}, ensure_ascii=False) + "\n")
    log2.close()
    print("\n[summary] " + json.dumps(summary, indent=1))
    print("\n— PICKS (lectura humana) —")
    for r in picks[:15]:
        print(f"  {str(r['headline'])[:88]}")
        print(f"    → {r['pick']['topic_id']} [{r['pick']['state']}]"
              f" \"{str(r['pick']['label'])[:70]}\" cos={r['pick']['cos']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
