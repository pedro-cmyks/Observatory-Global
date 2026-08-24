#!/usr/bin/env python3
"""Corte-con-cuerpos — harness del prereg 2026-08-12 (corrida offline, ledger).

Prereg congelado: `docs/superpowers/specs/2026-08-12-court-with-bodies-
preregistration.md`. Pregunta: cuando el juicio por titulares no clara, ¿el
TEXTO COMPLETO de los recibos cambia el veredicto en la dirección correcta?

Diseño (del prereg, sin movimiento):
  - Población: topics ACTIVOS `label_status='failed'` O withheld (aquí:
    label_status IS NULL entre activos con miembros — la zona gris real de
    la última pasada). Cap N=40, seed 42. Testigo de conflación forzado si
    vive (clase "…Ormuz…").
  - Brazo H (paridad nocturna): el MISMO `_ds_judge` de label_court.py
    importado VERBATIM (prompt idéntico, 8 recibos, deepseek temp 0).
  - Brazo B (cuerpos): fetch de ≤4 recibos congelados del topic vía la
    maquinaria article_fetch existente (gate SSRF/dominio + trafilatura),
    mismo texto de prompt con las líneas de evidencia = titular + excerpt
    de cuerpo con cap FIJADO PRE-RUN (EXCERPT_CAP=500 chars/recibo).
  - Brazo internet (DOC 2.0): NO corre en run-1 — se reporta como no-corrido
    (el prereg lo declara opcional y medido aparte).
  - Cohorte EXTRA declarada (motivada por el hallazgo Z1 2026-08-24, SIN
    gate — observación aparte): los ids CONDENADOS de la última línea del
    condemnation-ledger (la clase court-entailed-con-recibos-podridos, que
    el prereg no pudo anticipar). Mismo juicio pareado, reporte separado.

Barras (congeladas en el prereg): flips ≥80% correctos a mano (muestra 20,
seed 42) · testigo-fusión jamás MENOS rechazado con cuerpos · yield de
fetch ≥30% · costo REPORTADO (sin barra — decisión de Pedro).

READ-ONLY sobre la base; escrituras = ledger JSONL + artefacto JSON.
Lo scrapeado NO toca sustrato (frontera del prereg).
"""

from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import random
import sys
import time

import aiohttp
import asyncpg
import httpx

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
sys.path.insert(0, _BACKEND)

from scripts.label_court import _ds_judge, parse_verdict  # noqa: E402
from scripts.m1_confirmation_calibration import load_db_url  # noqa: E402
from app.services.article_fetch import (  # noqa: E402
    _extract, _fetch_raw, _host_public, host_of, strip_leading_boilerplate)

# ---- parámetros FIJADOS ANTES DE CORRER (prereg + esta cabecera) -----------
N_CAP = 40
SEED = 42
RECEIPTS_HEADLINE_ARM = 8      # paridad con la corte nocturna (default 8)
BODIES_PER_TOPIC = 4           # prereg: ≤4 recibos/topic al fetch
EXCERPT_CAP = 500              # chars de cuerpo por recibo (cap pre-run)
FETCH_CONCURRENCY = 6
JUDGE_CONCURRENCY = 4
FLIP_HAND_SAMPLE = 20

OUT_DIR = os.path.join(_BACKEND, "..", "docs", "research", "label-court")
CONDEMN_LEDGER = os.path.join(_BACKEND, "..", "docs", "research",
                              "recall-229", "condemnation-ledger.jsonl")

_RECEIPTS_URL_SQL = """
    SELECT s.headline, s.country_code, s.source_url
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = $1 AND tm.role = 'evidence'
      AND tm.engine_version = 'v1-compat'
      AND COALESCE(tm.quarantined, false) = false
      AND s.headline IS NOT NULL AND length(s.headline) >= 12
    GROUP BY s.headline, s.country_code, s.source_url
    ORDER BY max(tm.assigned_at) DESC
    LIMIT $2
"""

_POP_SQL = """
    SELECT d.id, d.label, d.label_status
    FROM dynamic_topics d
    WHERE d.state = 'active'
      AND COALESCE(d.is_junk, false) = false
      AND (d.label_status = 'failed' OR d.label_status IS NULL)
      AND EXISTS (SELECT 1 FROM topic_members tm
                  WHERE tm.topic_id = 'dynamic-topic-' || d.id
                    AND tm.role = 'evidence'
                    AND tm.engine_version = 'v1-compat'
                    AND COALESCE(tm.quarantined, false) = false)
"""


def body_prompt(label: str, rows: list[dict]) -> str:
    """El MISMO texto del prompt plano de label_court._judge_prompt; la única
    diferencia pre-registrada es la evidencia: titular + excerpt de cuerpo
    (cap EXCERPT_CAP) en vez de titular[:160]."""
    lines = "\n".join(
        f"- {(r['headline'] or '')[:160]} :: {r['excerpt'][:EXCERPT_CAP]}"
        for r in rows)
    return (
        "You are a strict fact-checker auditing a news-cluster LABEL against the "
        "actual headlines assigned to it.\n\n"
        f'LABEL: "{label}"\n\nHEADLINES:\n{lines}\n\n'
        "Does the LABEL accurately describe the MAJORITY of these headlines? "
        "Judge on subject and geography, not vibe. Reply ONLY with JSON:\n"
        '{"verdict": "entailed" | "partial" | "failed" | "too_broad", "reason": "<one short sentence>"}\n'
        "- entailed: the label fits most headlines.\n"
        "- partial: the label fits some but a large minority are off-topic.\n"
        "- failed: the label does NOT describe most headlines (wrong subject or "
        "wrong country) — but the headlines themselves belong to one story a "
        "BETTER label could describe.\n"
        "- too_broad: the headlines span MULTIPLE distinct unrelated stories — "
        "no single label (including this one) could describe the majority; the "
        "cluster is a fusion, not a mislabeling. Use this ONLY when you can see "
        "at least three clearly unrelated stories; a label that is merely "
        "generic over one diverse-but-real family is entailed, not too_broad.")


async def fetch_body(session: aiohttp.ClientSession, url: str) -> dict:
    """Un recibo → cuerpo extraído u outcome honesto. Reusa gate+extract de
    article_fetch (SSRF/dominio; trafilatura)."""
    try:
        # Gate del harness: SSRF real (esquema + host público) — el lookup de
        # dominios-conocidos del servicio (known_domains) exige su pool y en
        # local devuelve unavailable/fail-closed; aquí la PROCEDENCIA de cada
        # url ya es signals_v2 (recibos del topic), que es exactamente lo que
        # ese lookup certifica. Declarado; el harness jamás recibe urls de
        # otra fuente.
        if not url.startswith(("http://", "https://")):
            return {"status": "gated", "why": "scheme"}
        host = host_of(url)
        if not host or not await _host_public(host):
            return {"status": "gated", "why": "ssrf_host"}
        status, ctype, raw, final_url = await _fetch_raw(session, url)
        if status != 200 or not raw:
            return {"status": "http_error", "why": str(status)}
        ex = _extract(raw, ctype, final_url)
        if not ex or not ex.get("text"):
            return {"status": "no_extract"}
        text = strip_leading_boilerplate(ex["text"])
        if len(text) < 120:
            return {"status": "thin", "chars": len(text)}
        return {"status": "ok", "excerpt": text[:EXCERPT_CAP],
                "chars": len(text)}
    except Exception as exc:
        return {"status": "error", "why": repr(exc)[:120]}


async def judge_bodies(label: str, rows: list[dict], key: str) -> tuple[str, str, dict]:
    body = {"model": "deepseek-chat", "temperature": 0,
            "messages": [{"role": "user", "content": body_prompt(label, rows)}]}
    async with httpx.AsyncClient() as c:
        r = await c.post("https://api.deepseek.com/chat/completions", json=body,
                         headers={"Authorization": f"Bearer {key}"}, timeout=60.0)
        r.raise_for_status()
        payload = r.json()
    ans = payload["choices"][0]["message"]["content"]
    verdict, reason = parse_verdict(ans)
    u = payload.get("usage") or {}
    return verdict, reason, {"input_tokens": u.get("prompt_tokens", 0) or 0,
                             "output_tokens": u.get("completion_tokens", 0) or 0}


def load_condemned_cohort() -> list[str]:
    """Última línea del ledger de condenación → identity_keys condenados."""
    try:
        last = None
        for line in open(CONDEMN_LEDGER):
            last = json.loads(line)
        return list(last.get("condemned_ids") or [])
    except Exception:
        return []


async def run_topic(conn, session, sem_j, key, dyn_id: int, label: str,
                    status: str | None, cohort: str, ledger) -> dict:
    tid = f"dynamic-topic-{dyn_id}"
    rows = await conn.fetch(_RECEIPTS_URL_SQL, tid, RECEIPTS_HEADLINE_ARM)
    receipts = [{"headline": html.unescape(r["headline"] or ""),
                 "country_code": r["country_code"],
                 "source_url": r["source_url"]} for r in rows]
    rec: dict = {"id": dyn_id, "label": label, "label_status": status,
                 "cohort": cohort, "n_receipts": len(receipts)}
    if not receipts:
        rec["outcome"] = "no_receipts"
        ledger.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    # brazo H — paridad nocturna (import verbatim)
    async with sem_j:
        try:
            v_h, reason_h, use_h = await _ds_judge(label, receipts, key)
        except Exception as exc:
            rec["outcome"] = f"judge_h_error:{exc!r}"[:120]
            ledger.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec
    rec.update(verdict_h=v_h, reason_h=reason_h, usage_h=use_h)

    # brazo B — fetch de cuerpos (≤4)
    fetched, outcomes = [], []
    for r in receipts:
        if len(fetched) >= BODIES_PER_TOPIC:
            break
        if not r["source_url"]:
            continue
        out = await fetch_body(session, r["source_url"])
        outcomes.append({"url": r["source_url"][:120], **{k: v for k, v in out.items() if k != "excerpt"}})
        if out["status"] == "ok":
            fetched.append({"headline": r["headline"], "excerpt": out["excerpt"]})
    rec["fetch_outcomes"] = outcomes
    rec["bodies_ok"] = len(fetched)
    if not fetched:
        rec["outcome"] = "unfetchable"
        ledger.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    async with sem_j:
        try:
            v_b, reason_b, use_b = await judge_bodies(label, fetched, key)
        except Exception as exc:
            rec["outcome"] = f"judge_b_error:{exc!r}"[:120]
            ledger.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return rec
    rec.update(verdict_b=v_b, reason_b=reason_b, usage_b=use_b,
               flip=(v_h != v_b), outcome="judged")
    ledger.write(json.dumps(rec, ensure_ascii=False) + "\n")
    ledger.flush()
    return rec


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=N_CAP)
    args = ap.parse_args()
    key = os.environ.get("DEEPSEEK_API_KEY") or ""
    if not key:
        raise SystemExit("DEEPSEEK_API_KEY missing")
    os.makedirs(OUT_DIR, exist_ok=True)
    run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    ledger_path = os.path.join(OUT_DIR, f"2026-08-24-court-bodies-{run_id}.jsonl")
    ledger = open(ledger_path, "a")

    conn = await asyncpg.connect(load_db_url(), statement_cache_size=0, timeout=30)
    t0 = time.monotonic()
    try:
        async with conn.transaction():
            await conn.execute("SET LOCAL statement_timeout='60s'")
            await conn.execute("SET TRANSACTION READ ONLY")
            pop = await conn.fetch(_POP_SQL)
        gray_total = len(pop)
        rng = random.Random(SEED)
        pop = list(pop)
        # testigo forzado (clase Ormuz) si vive en la población
        forced = [p for p in pop if "ormuz" in (p["label"] or "").lower()
                  or "hormuz" in (p["label"] or "").lower()]
        rest = [p for p in pop if p not in forced]
        rng.shuffle(rest)
        chosen = (forced + rest)[: args.cap]
        print(f"[pop] zona gris total={gray_total} (failed+withheld activos) · "
              f"corrida n={len(chosen)} · testigos-ormuz forzados={len(forced)}")

        condemned = load_condemned_cohort()
        print(f"[cohorte-extra] condenados hoy: {len(condemned)} ids")
        cond_rows = []
        if condemned:
            async with conn.transaction():
                await conn.execute("SET TRANSACTION READ ONLY")
                cond_rows = await conn.fetch(
                    "SELECT id, label, label_status FROM dynamic_topics"
                    " WHERE identity_key = ANY($1::text[])", condemned)

        sem_j = asyncio.Semaphore(JUDGE_CONCURRENCY)
        results, cond_results = [], []
        timeout = aiohttp.ClientTimeout(total=25)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for p in chosen:
                results.append(await run_topic(
                    conn, session, sem_j, key, int(p["id"]), p["label"] or "",
                    p["label_status"], "gray", ledger))
            for p in cond_rows:
                cond_results.append(await run_topic(
                    conn, session, sem_j, key, int(p["id"]), p["label"] or "",
                    p["label_status"], "condemned", ledger))
    finally:
        await conn.close()
        ledger.close()
    wall = round(time.monotonic() - t0, 1)

    # ---- medidas ----
    def summarize(rs: list[dict], name: str) -> dict:
        judged = [r for r in rs if r.get("outcome") == "judged"]
        unfetch = [r for r in rs if r.get("outcome") == "unfetchable"]
        flips = [r for r in judged if r.get("flip")]
        toks = sum((r.get("usage_h", {}).get("input_tokens", 0)
                    + r.get("usage_h", {}).get("output_tokens", 0)
                    + r.get("usage_b", {}).get("input_tokens", 0)
                    + r.get("usage_b", {}).get("output_tokens", 0)) for r in judged)
        fetch_eligible = [r for r in rs if r.get("n_receipts", 0) > 0
                          and "verdict_h" in r]
        return {
            "name": name, "n": len(rs), "judged_paired": len(judged),
            "unfetchable": len(unfetch),
            "fetch_yield": round(len(judged) / max(len(fetch_eligible), 1), 3),
            "flips": len(flips),
            "flip_matrix": dict(
                __import__("collections").Counter(
                    f"{r['verdict_h']}→{r['verdict_b']}" for r in flips)),
            "tokens_total": toks,
        }

    s_gray = summarize(results, "gray")
    s_cond = summarize(cond_results, "condemned")
    flips_gray = [r for r in results if r.get("flip")]
    rng2 = random.Random(SEED)
    hand = rng2.sample(flips_gray, min(FLIP_HAND_SAMPLE, len(flips_gray)))

    report = {
        "run_id": run_id, "prereg": "2026-08-12-court-with-bodies",
        "params": {"n_cap": args.cap, "excerpt_cap": EXCERPT_CAP,
                   "bodies_per_topic": BODIES_PER_TOPIC,
                   "receipts_headline_arm": RECEIPTS_HEADLINE_ARM,
                   "seed": SEED},
        "gray_zone_total": gray_total, "wall_s": wall,
        "internet_arm": "not_run (opcional del prereg; se declara)",
        "summary_gray": s_gray, "summary_condemned": s_cond,
        "ledger": ledger_path,
    }
    out_json = os.path.join(OUT_DIR, f"2026-08-24-court-bodies-{run_id}.json")
    with open(out_json, "w") as f:
        json.dump({**report,
                   "hand_check_sample": hand,
                   "results_gray": results,
                   "results_condemned": cond_results},
                  f, ensure_ascii=False, indent=1, default=str)

    print("\n[report] " + json.dumps(report, indent=1, ensure_ascii=False))
    print("\n— FLIPS zona gris (muestra para juicio a mano) —")
    for r in hand:
        print(f"  dt-{r['id']} [{r['label_status']}] \"{str(r['label'])[:64]}\"")
        print(f"    H: {r['verdict_h']} — {str(r['reason_h'])[:110]}")
        print(f"    B: {r['verdict_b']} — {str(r['reason_b'])[:110]}")
    print("\n— COHORTE CONDENADOS (todos) —")
    for r in cond_results:
        if r.get("outcome") == "judged":
            mark = " *FLIP*" if r.get("flip") else ""
            print(f"  dt-{r['id']} \"{str(r['label'])[:56]}\" "
                  f"H:{r['verdict_h']} → B:{r['verdict_b']}{mark}")
    print(f"\n[out] {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
