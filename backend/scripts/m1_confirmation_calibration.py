#!/usr/bin/env python3
"""M1 — calibración de la familia ① (coseno + confirmación barata) sobre la
muestra congelada del A0.

Mandato: M1-GATE (`docs/superpowers/specs/2026-08-20-assignment-lane-
preregistration.md`) — la familia ① exige medir ANTES el costo por señal y la
viabilidad de la confirmación ortogonal. Esto NO es G-PRECISIÓN (esa barra se
mide sobre una muestra FRESCA y ciega de adjuntos nuevos del fix, n>=50); esto
es la calibración previa: sobre los 40 candidatos coseno>=0.88 que el A0 juzgó
a mano (seed 229, 17.5% sí / 17.5% dudoso / 65% no), ¿qué señal de
confirmación barata separa la historia correcta del vecino falso, y a qué
costo?

Señales de confirmación medidas (cada una y sus combos):
  - TOK   : p8_compatible(headline, label) — el predicado P-NUEVO congelado del
            8º gate (Unicode-norm + contención de tokens de sujeto), importado
            VERBATIM de measure_landing_predicate.py.
  - COV   : cobertura de tokens del label por el headline (|shared|/|label|),
            umbrales 0.5 / 0.67 — variante direccional señal→topic (el P-NUEVO
            fue diseñado label↔label; un headline trae más residuo).
  - ENT   : >=1 persona compartida entre la señal (persons ∪ nlp_persons) y el
            pool de personas de los miembros actuales del topic.
  - JUDGE : DeepSeek "¿misma historia específica?" (patrón del juez de
            overmerge, precision-first: unsure/no-parse = NO adjuntar).

READ-ONLY sobre la base (SET TRANSACTION READ ONLY); las únicas llamadas
externas son las del juez (--no-judge las apaga). Artefacto JSON companion:
docs/research/recall-229/2026-08-24-m1-confirmation-calibration.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import unicodedata
from collections import Counter

import asyncpg
import httpx

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
sys.path.insert(0, _BACKEND)

from scripts.measure_landing_predicate import (  # noqa: E402  (frozen P-NUEVO)
    p8_compatible,
    p8_subject_tokens,
    unicode_norm,
)
from scripts.ensemble.model_clients import call_llm  # noqa: E402

ENV_PATH = "/Users/pedro/AtlasLocalWorker/.env"
A0_JSON = os.path.join(
    _BACKEND, "..", "docs", "research", "recall-229",
    "2026-08-20-m1a0-unified-v2-coverage.json")
OUT_JSON = os.path.join(
    _BACKEND, "..", "docs", "research", "recall-229",
    "2026-08-24-m1-confirmation-calibration.json")
STATEMENT_TIMEOUT = "45s"

JUDGE_SYSTEM = (
    "You judge whether a news headline belongs to a specific story topic. "
    "Answer STRICT JSON only: {\"same_story\": \"yes\"|\"no\"|\"unsure\"}. "
    "Say \"yes\" ONLY if the headline reports the same specific real-world "
    "story the topic tracks — same event and actors/place. Same theme, same "
    "country, a similar category, or a twin story elsewhere is \"no\". "
    "When in doubt, \"unsure\"."
)


def judge_user(label: str, members: list[str], headline: str,
               cc: str | None, fam: str | None) -> str:
    mem = "\n".join(f"- {h}" for h in members) if members else "(none available)"
    tag = ", ".join(x for x in (cc, fam) if x)
    return (f"TOPIC label: {label}\nTOPIC member headlines:\n{mem}\n\n"
            f"CANDIDATE headline ({tag}): {headline}\n\nSame specific story?")


def load_db_url() -> str:
    with open(ENV_PATH) as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                return line.strip().split("=", 1)[1]
    raise SystemExit("DATABASE_URL not found in " + ENV_PATH)


def norm_hand(v: str | None) -> str:
    x = (v or "").strip().lower()
    if x in ("si", "sí", "yes"):
        return "si"
    if x in ("dudoso", "unsure", "maybe"):
        return "dudoso"
    return "no"


def norm_person(p: str) -> str:
    x = unicodedata.normalize("NFKC", p).casefold().strip()
    return re.sub(r"\s+", " ", x)


def label_coverage(headline: str, label: str) -> float:
    lt = p8_subject_tokens(unicode_norm(label))
    if not lt:
        return 0.0
    ht = p8_subject_tokens(unicode_norm(headline))
    return len(lt & ht) / len(lt)


async def fetch_context(conn: asyncpg.Connection, rows: list[dict]) -> dict:
    """Signals vivos + estado actual de cada topic + pool de miembros."""
    ids = [int(r["id"]) for r in rows]
    async with conn.transaction():
        await conn.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'")
        await conn.execute("SET TRANSACTION READ ONLY")
        sig = await conn.fetch(
            "SELECT id, headline, persons, nlp_persons, source_lang, timestamp"
            " FROM signals_v2 WHERE id = ANY($1::bigint[])", ids)
    sig_by_id = {int(r["id"]): dict(r) for r in sig}

    topics: dict[str, dict] = {}
    for r in rows:
        tid = r["topic_id"]
        if tid in topics:
            continue
        num = int(tid.rsplit("-", 1)[1])
        async with conn.transaction():
            await conn.execute(
                f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'")
            await conn.execute("SET TRANSACTION READ ONLY")
            trow = await conn.fetchrow(
                "SELECT label, state FROM dynamic_topics WHERE id = $1", num)
            mem = await conn.fetch(
                "SELECT s.id, s.headline, s.persons, s.nlp_persons"
                " FROM topic_members tm JOIN signals_v2 s ON s.id = tm.signal_id"
                " WHERE tm.topic_id = $1 AND tm.role = 'evidence'"
                "   AND tm.quarantined IS NOT TRUE"
                " ORDER BY s.timestamp DESC LIMIT 40", tid)
        persons: Counter = Counter()
        headlines: list[str] = []
        for m in mem:
            if int(m["id"]) in sig_by_id:
                continue  # la señal candidata no se auto-confirma
            if m["headline"] and len(headlines) < 3:
                headlines.append(m["headline"])
            for src in ("persons", "nlp_persons"):
                val = m[src]
                if isinstance(val, str):
                    try:
                        val = json.loads(val)
                    except ValueError:
                        val = None
                if isinstance(val, list):
                    for p in val:
                        if isinstance(p, str) and p.strip():
                            persons[norm_person(p)] += 1
        topics[tid] = {
            "current_label": trow["label"] if trow else None,
            "current_state": trow["state"] if trow else "GONE",
            "n_members_now": len(mem),
            "member_headlines": headlines,
            "member_persons": persons,
        }
    return {"signals": sig_by_id, "topics": topics}


def signal_persons(sig_row: dict | None) -> set[str]:
    out: set[str] = set()
    if not sig_row:
        return out
    for src in ("persons", "nlp_persons"):
        val = sig_row.get(src)
        if isinstance(val, str):
            try:
                val = json.loads(val)
            except ValueError:
                val = None
        if isinstance(val, list):
            for p in val:
                if isinstance(p, str) and p.strip():
                    out.add(norm_person(p))
    return out


RULES = [
    # (nombre, fn(row) -> bool). El coseno >=0.88 ya lo pasaron todos: cada
    # regla es la CONFIRMACIÓN encima del candidato por distancia.
    ("cos_alone", lambda r: True),
    ("cos_gate090", lambda r: bool(r["gate_kept"])),
    ("TOK", lambda r: r["tok_compat"]),
    ("COV50", lambda r: r["label_cov"] >= 0.5),
    ("COV67", lambda r: r["label_cov"] >= 0.67),
    ("ENT1", lambda r: r["ent_shared"] >= 1),
    ("TOK_or_ENT", lambda r: r["tok_compat"] or r["ent_shared"] >= 1),
    ("JUDGE", lambda r: r["judge"] == "yes"),
    ("JUDGE_and_TOKorENT",
     lambda r: r["judge"] == "yes" and (r["tok_compat"] or r["ent_shared"] >= 1)),
    ("JUDGE_and_COV50",
     lambda r: r["judge"] == "yes" and r["label_cov"] >= 0.5),
    ("JUDGE_or_TOK", lambda r: r["judge"] == "yes" or r["tok_compat"]),
]


def evaluate(rows: list[dict]) -> list[dict]:
    n_si = sum(1 for r in rows if r["hand"] == "si")
    out = []
    for name, fn in RULES:
        acc = [r for r in rows if fn(r)]
        c = Counter(r["hand"] for r in acc)
        si, dud, no = c.get("si", 0), c.get("dudoso", 0), c.get("no", 0)
        out.append({
            "rule": name,
            "accepted": len(acc),
            "si": si, "dudoso": dud, "no": no,
            "precision_strict": round(si / len(acc), 3) if acc else None,
            "precision_lenient": round((si + dud) / len(acc), 3) if acc else None,
            "recall_si": round(si / n_si, 3) if n_si else None,
        })
    return out


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-judge", action="store_true",
                    help="solo señales locales (sin DeepSeek)")
    ap.add_argument("--out", default=OUT_JSON)
    args = ap.parse_args()

    with open(A0_JSON) as f:
        sample = json.load(f)["u2_only_sample"]
    print(f"[load] muestra A0: {len(sample)} filas, "
          f"hand={Counter(norm_hand(r['hand_judgment']) for r in sample)}")

    conn = await asyncpg.connect(load_db_url(), statement_cache_size=0,
                                 timeout=30)
    try:
        ctx = await fetch_context(conn, sample)
    finally:
        await conn.close()
    alive = sum(1 for r in sample if int(r["id"]) in ctx["signals"])
    print(f"[db] señales de la muestra aún en retención: {alive}/{len(sample)}")

    rows: list[dict] = []
    for r in sample:
        sig = ctx["signals"].get(int(r["id"]))
        top = ctx["topics"][r["topic_id"]]
        headline = (sig or {}).get("headline") or r["headline"]
        sp = signal_persons(sig)
        shared = {p for p in sp if top["member_persons"].get(p)}
        rows.append({
            "id": int(r["id"]),
            "headline": headline,
            "cc": r.get("cc"),
            "source_family": r.get("source_family"),
            "topic_id": r["topic_id"],
            "label": r["label"],           # frozen: lo que el juicio a mano vio
            "current_label": top["current_label"],
            "current_state": top["current_state"],
            "n_members_now": top["n_members_now"],
            "confidence": r["confidence"],
            "gate_kept": r["gate_kept"],
            "hand": norm_hand(r["hand_judgment"]),
            "signal_alive": sig is not None,
            "tok_compat": p8_compatible(headline, r["label"]),
            "label_cov": round(label_coverage(headline, r["label"]), 3),
            "ent_shared": len(shared),
            "ent_shared_names": sorted(shared)[:5],
            "judge": None, "judge_latency_s": None,
        })

    judge_stats = {"called": 0, "yes": 0, "no": 0, "unsure": 0,
                   "failed": 0, "est_tokens_in": 0, "tokens_out_cap": 60,
                   "wall_s": 0.0}
    if not args.no_judge:
        t0 = time.monotonic()
        async with httpx.AsyncClient(timeout=90.0) as client:
            sem = asyncio.Semaphore(4)

            async def one(row: dict) -> None:
                mems = ctx["topics"][row["topic_id"]]["member_headlines"]
                user = judge_user(row["label"], mems, row["headline"],
                                  row["cc"], row["source_family"])
                judge_stats["est_tokens_in"] += (len(JUDGE_SYSTEM) + len(user)) // 4
                async with sem:
                    tj = time.monotonic()
                    try:
                        out = await call_llm(
                            "deepseek", system=JUDGE_SYSTEM, user=user,
                            client=client, max_tokens=60, temperature=0.0,
                            json_mode=True)
                        verdict = json.loads(out).get("same_story")
                        row["judge"] = verdict if verdict in (
                            "yes", "no", "unsure") else "unsure"
                    except Exception as exc:  # precision-first: sin confirmación
                        print(f"[judge] FAIL id={row['id']}: {exc!r}",
                              file=sys.stderr)
                        row["judge"] = "failed"
                        judge_stats["failed"] += 1
                    row["judge_latency_s"] = round(time.monotonic() - tj, 2)
                    judge_stats["called"] += 1
                    if row["judge"] in ("yes", "no", "unsure"):
                        judge_stats[row["judge"]] += 1

            await asyncio.gather(*(one(row) for row in rows))
        judge_stats["wall_s"] = round(time.monotonic() - t0, 1)

    table = evaluate(rows)
    print("\nregla                 acc  si dud  no  P_strict P_lenient R_si")
    for t in table:
        print(f"{t['rule']:<20} {t['accepted']:>4} {t['si']:>3} "
              f"{t['dudoso']:>3} {t['no']:>3}   "
              f"{t['precision_strict'] if t['precision_strict'] is not None else '—':>6}   "
              f"{t['precision_lenient'] if t['precision_lenient'] is not None else '—':>6}  "
              f"{t['recall_si'] if t['recall_si'] is not None else '—':>5}")
    print(f"\n[judge] {judge_stats}")

    artifact = {
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mandate": "M1-GATE familia ① — calibración previa (NO es G-PRECISIÓN)",
        "sample": "A0 u2_only_sample n=40 seed 229 (juicio a mano 2026-08-20)",
        "signals_alive_at_measure": alive,
        "judge_stats": judge_stats,
        "rules_table": table,
        "rows": rows,
    }
    with open(args.out, "w") as f:
        json.dump(artifact, f, ensure_ascii=False, indent=1, default=str)
    print(f"[out] {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
