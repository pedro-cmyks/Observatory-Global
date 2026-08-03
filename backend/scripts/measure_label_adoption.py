#!/usr/bin/env python3
"""Ninth pre-registered identity gate: LABEL ADOPTION at labeling-time.

Pre-registration (FROZEN before this file was written, approved by Pedro):
  docs/superpowers/specs/2026-08-03-label-adoption-preregistration.md
Successor of the 8th (`2026-08-03-landing-predicate.md`), whose KILL measured
the join-predicate ladder exhausted: the majority false-block class is FACET
DIVERGENCE — the labels of one story do not carry the join information. This
gate moves the lever upstream: same-story labels should be BORN equal.

READ-ONLY against prod. Extends the 7th+8th harnesses (both left untouched);
all rules and replay machinery IMPORTED, never re-implemented.

THE MECHANISM
-------------
When the labeller labels a snapshot cluster and a nearby ELIGIBLE topic exists
(cos >= TAU_ADOPT), the SAME labeling call that already happens is shown the
topic's existing label and decides ADOPT (inherit verbatim) vs NEW. Adopted
same-story pairs become string-identical -> `labels_compatible` and P-NUEVO
both pass by norm-equality -> consolidation and landing stop failing on
re-phrasing. In production this costs ZERO extra calls (G-COSTO): the
candidate lookup is local geometry folded into the existing prompt.

FROZEN DESIGN CHOICES (fixed here BEFORE the run, per the pre-registration)
  * TAU_ADOPT = MATCH_THRESHOLD (0.88, production's own admissibility floor:
    a cluster that could never JOIN a topic gains nothing from its label).
  * Candidate = the cluster's best ELIGIBLE pool topic by centroid cos.
    NEVER eligible (G-BLOB-ADOPCION, by construction + verified post-hoc from
    the ledger): topics with `blob_confirmed_at` set, `label_status='failed'`,
    `is_junk`, an empty label — and UMBRELLAS (a pre-run extension of the
    same clause: umbrella labels are cross-event family names, and the 8th §6
    measured the marquee blob-corruption case on an umbrella; adoption may
    only inherit from healthy EVENT identities).
  * The adopted string = the HYDRATED topic label (modal member label — the
    exact string the landing layer compares against; production would use
    `dynamic_topics.label`, same mechanism, stated as a caveat).
  * Adoption applies to SNAPSHOT-side labels only (the labeling-time
    mechanism); pool/topic labels stay historical. A deployed system would
    have adopted historically too — this simulation measures one night-side
    generation of the mechanism, stated in the artifact.
  * Simulation evidence for the decision: the cluster's surviving sample
    headlines where the hot store still has them, else its historical label
    (the labeller's own summary of the same content) — stated per cluster in
    the ledger. Production always has the headlines (it IS the labeling call).
  * Adoption decisions at temperature 0 (simulation determinism); the
    production prompt keeps the labeller's temp for the COINING path and
    temp-0-like determinism is not required there.

FROZEN GATES (any fail => overall KILL)
  G-ADOPCION     >= 60 judged adoptions (random sample, seed 42; quote-gated
                 judge + human read of all): false-adoption <= 5%. Counting is
                 conservative: FALSE_ADOPTION verdicts AND judgments whose
                 reason stays ungrounded after one retry both count against.
  G-BLOB-ADOPCION  0 adoptions sourced from excluded topics — verified from
                 the final ledger against a fresh exclusion query.
  G-FALSE-BLOCK  < 20% false-block on known-same-story pairs (decidable picks
                 at cos >= 0.99) in B-p8-adopted.
  G-FOUNDING     B-p8-adopted foundings <= 15% of decidable picks (third run,
                 unchanged).
  G-LANDING      B-p8-adopted correct on >= ceil(2/3*scorables) families AND
                 strictly more than production (arm A on the same adopted
                 feed); the 8th's self-founded rule (counts only if no correct
                 identity existed — pool-check judge) applies.
  G-K2/G-784/G-FALSE  inherited, measured ON THE ADOPTED LABEL FIELD over the
                 15 frozen nights (>= 14/15 <= 2% · 0 · 0/1200). Adoption
                 spreads one topic's label across clusters, so component
                 growth is a REAL kill risk here, not a formality.
  G-COSTO        the proposed production prompt is published in the artifact
                 and demonstrably adds zero nightly calls.

FIDELITY (STOP rule): with ORIGINAL labels, run 5's graph rows must reproduce
exactly on all 15 nights; the single-night downstream must be within 2pp of
93.81%; and B-p8-original must reproduce the 8th gate's founding numbers
(tolerance 2% relative — the pool is mutable intra-day; the 8th reproduced
the 7th exactly, so material drift means a broken instrument or a moved pool,
and either stops the run).

Usage (M1 mlvenv; read-only; Pedro on the machine => taskpolicy -b ALWAYS):
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend && taskpolicy -b nice -n 19 \
      /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.measure_label_adoption --phase adopt      # API pass, cached
  ... then --phase measure, then --phase judge
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import math
import os
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

from scripts.project_dynamic_topics import (  # noqa: E402
    ANCHOR_THRESHOLD,
    MATCH_THRESHOLD,
    MERGE_THRESHOLD,
    LifecycleConfig,
    _subject_tokens,
    labels_compatible,
)
from scripts.simulate_used_t_removal import (  # noqa: E402
    _unit_rows,
    hydrate_as_of,
    process_snapshot_sim,
    topic_of_cluster,
    validate_against_prod,
)
from scripts.measure_cluster_consolidation import (  # noqa: E402
    FALSE_PAIR_TARGET,
    K2_MAX_SHARE,
    build_super_clusters,
    consolidation_graph,
    country_span_signature,
    family_components,
    sample_false_pairs,
    verify_false_construction,
)
from scripts.measure_consolidation_landing import (  # noqa: E402
    _DS_URL,
    G_FOUNDING_MAX_RATE,
    apply_largest_member_label,
    destination_receipts,
    ds_judge_landing,
    false_side_with_country,
    family_destination,
    load_clusters_chunked,
    memory_free_pct,
    mindful_gate,
    verify_loader_equivalence,
)
from scripts.measure_landing_predicate import (  # noqa: E402
    G_PRED_MAX_FALSE_BLOCK,
    ds_pool_check,
    p8_compatible,
    pool_topic_receipts,
    process_snapshot_arm_pred,
)
from scripts.label_court import _reason_quotes_a_receipt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
STEM = "2026-08-03-label-adoption"
RUN5_JSON = OUT_DIR / "2026-07-30-cluster-consolidation.json"
GATE8_JSON = OUT_DIR / "2026-08-03-landing-predicate.json"
PREREG_PATH = ("docs/superpowers/specs/"
               "2026-08-03-label-adoption-preregistration.md")
ADOPT_CACHE = Path(os.environ.get(
    "ATLAS_ADOPT_CACHE", "/tmp/p9_adopt_cache.json"))
ADOPT_LEDGER = Path(os.environ.get(
    "ATLAS_ADOPT_LEDGER", "/tmp/p9_adoption_ledger.json"))

# ---- frozen constants (pre-registration; never moved) -------------------------
TAU_ADOPT = MATCH_THRESHOLD          # 0.88 — production's admissibility floor
G_K2_MIN_NIGHTS = 14
G_ADOPTION_MAX_FALSE = 0.05
G_ADOPTION_MIN_SAMPLE = 60
ADOPT_CONCURRENCY = 6                # network-bound; CPU stays mindful


# ---- G-COSTO: the proposed PRODUCTION prompt (published in the artifact) ------
# Extends emergent_poc.LABEL_PROMPT (the call `snapshot_emergent_topics.py`
# already makes once per cluster, concurrency 5). The candidate lookup is a
# local centroid dot-product against the loaded topic pool — no API involved —
# so the nightly call count is IDENTICAL with or without adoption.
PRODUCTION_PROMPT = """You are labeling a cluster of news headlines for a narrative intelligence brief.

Given these representative headlines:

{headlines}

{candidate_block}Return JSON only, no other text:
{{
  "label": "3-5 word topic name in title case",
  "adopted": true | false,
  "description": "one-line description of what this cluster is about",
  "confidence": 0.0-1.0
}}"""
PRODUCTION_CANDIDATE_BLOCK = """A nearby existing topic already tracks a story (cosine similarity {cos:.2f}):
  "{candidate_label}"
If these headlines are THE SAME STORY that topic describes, set "adopted": true
and return that label VERBATIM as "label" — do not coin a new wording for a
story that already has a name. Only if this is a different story (or the
existing label misdescribes these headlines), set "adopted": false and coin a
new label.

"""


def adoption_prompt(cluster_lines: list[str], evidence_kind: str,
                    cand_label: str, cand_members: list[str],
                    cos: float) -> str:
    ev = "\n".join(f"- {x}" for x in cluster_lines)
    mem = "\n".join(f"  - {x}" for x in cand_members[:8])
    src = ("representative headlines"
           if evidence_kind == "headlines" else
           "the label previously assigned to it (its headlines have aged out "
           "of the hot store)")
    return (
        "You are labeling a cluster of news signals for a narrative "
        f"intelligence brief. The cluster's content, via {src}:\n{ev}\n\n"
        f"A nearby existing topic already tracks a story (cosine similarity "
        f"{cos:.2f}):\n  label: \"{cand_label}\"\n"
        f"  what it holds (member cluster labels):\n{mem}\n\n"
        "Decide: is this cluster THE SAME STORY as that existing topic? "
        "Same story = same specific occurrence/place/actors, not merely the "
        "same war, country or theme. Reply JSON only:\n"
        '{"decision": "ADOPT" | "NEW", "reason": "<one short sentence>"}\n'
        "- ADOPT: same story — the cluster should carry the existing topic's "
        "label verbatim.\n"
        "- NEW: a different story, or the topic's label misdescribes this "
        "cluster.")


# ------------------------------------------------------------------ adopt phase
async def phase_adopt(args: argparse.Namespace) -> int:
    import asyncpg
    import httpx
    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not db or not key:
        raise SystemExit("DATABASE_URL and DEEPSEEK_API_KEY required")
    run5 = json.loads(RUN5_JSON.read_text())
    frozen_nights: list[str] = run5["labelled_snapshots"]
    conn = await asyncpg.connect(db)
    await conn.execute("SET default_transaction_read_only = on")
    try:
        mindful_gate("adopt load")
        clusters = await load_clusters_chunked(conn)
        clusters_by_id = {c["id"]: c for c in clusters}
        snaps: dict[str, list[dict]] = defaultdict(list)
        for c in clusters:
            snaps[c["snapshot_at"]].append(c)

        cutoff_now = dt.datetime.now(dt.timezone.utc)
        topics, hmeta, _ = await hydrate_as_of(conn, clusters_by_id, cutoff_now)
        print(f"[pool] {len(topics)} topics hydrated as-of {cutoff_now.isoformat()}")

        # ---- eligibility (G-BLOB-ADOPCION, by construction) -----------------
        ex_rows = await conn.fetch(
            "SELECT id, is_junk, label_status, blob_confirmed_at, "
            "COALESCE(is_umbrella,false) AS umb FROM dynamic_topics")
        excluded: dict[int, str] = {}
        for r in ex_rows:
            why = []
            if r["blob_confirmed_at"] is not None:
                why.append("blob_confirmed")
            if (r["label_status"] or "") == "failed":
                why.append("label_failed")
            if r["is_junk"]:
                why.append("junk")
            if r["umb"]:
                why.append("umbrella")
            if why:
                excluded[int(r["id"])] = "+".join(why)
        eligible_mask = np.array(
            [(t.id is not None and int(t.id) not in excluded and bool(t.label))
             for t in topics])
        print(f"[pool] eligible for adoption: {int(eligible_mask.sum())}/"
              f"{len(topics)} (excluded: {len(excluded)} prod topics flagged)")

        T = _unit_rows(np.stack([t.centroid for t in topics]))
        # ---- candidates per frozen-night cluster ---------------------------
        tasks: list[dict[str, Any]] = []
        for snap in frozen_nights:
            cs = snaps[snap]
            V = _unit_rows(np.stack([c["centroid"] for c in cs]).astype(np.float64))
            S = V @ T.T
            S[:, ~eligible_mask] = -1.0
            best = np.argmax(S, axis=1)
            bcos = S[np.arange(len(cs)), best]
            for k, c in enumerate(cs):
                if not c["label"] or bcos[k] < TAU_ADOPT:
                    continue
                t = topics[int(best[k])]
                tasks.append({"cluster_id": c["id"], "snapshot": snap,
                              "orig_label": c["label"],
                              "cand_topic_id": int(t.id),
                              "cand_identity": t.identity_key,
                              "cand_label": t.label,
                              "cos": round(float(bcos[k]), 4)})
        print(f"[adopt] {len(tasks)} cluster-with-candidate tasks over "
              f"{len(frozen_nights)} nights")

        # ---- evidence: surviving headlines (bulk) + member labels ----------
        want = sorted({s for t in tasks
                       for s in clusters_by_id[t["cluster_id"]]["sample_signal_ids"]})
        heads: dict[int, str] = {}
        for i in range(0, len(want), 8000):
            for r in await conn.fetch(
                    "SELECT id, headline FROM signals_v2 WHERE id = ANY($1::bigint[]) "
                    "AND headline IS NOT NULL AND length(headline) >= 12",
                    want[i:i + 8000]):
                heads[int(r["id"])] = r["headline"]
        print(f"[adopt] {len(heads)}/{len(want)} sample headlines survive retention")
        ml_rows = await conn.fetch(
            "SELECT dtm.dynamic_topic_id AS tid, ec.label "
            "FROM dynamic_topic_members dtm "
            "JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id "
            "WHERE ec.label IS NOT NULL ORDER BY dtm.snapshot_at DESC")
        member_labels: dict[int, list[str]] = defaultdict(list)
        for r in ml_rows:
            if len(member_labels[int(r["tid"])]) < 8:
                member_labels[int(r["tid"])].append(r["label"])

        cache: dict[str, dict] = (json.loads(ADOPT_CACHE.read_text())
                                  if ADOPT_CACHE.exists() else {})
        sem = asyncio.Semaphore(ADOPT_CONCURRENCY)
        done = errors = 0
        t0 = time.monotonic()

        async def decide(client: httpx.AsyncClient, t: dict[str, Any]) -> None:
            nonlocal done, errors
            ck = f"{t['cluster_id']}::{t['cand_identity']}"
            if ck in cache:
                t.update(cache[ck])
                done += 1
                return
            c = clusters_by_id[t["cluster_id"]]
            hl = [heads[s] for s in c["sample_signal_ids"] if s in heads][:6]
            kind = "headlines" if hl else "historical_label"
            lines = hl if hl else [t["orig_label"]]
            prompt = adoption_prompt(lines, kind, t["cand_label"],
                                     member_labels.get(t["cand_topic_id"], []),
                                     t["cos"])
            async with sem:
                try:
                    r = await client.post(
                        _DS_URL, timeout=45.0,
                        headers={"Authorization": f"Bearer {key}"},
                        json={"model": "deepseek-chat", "temperature": 0,
                              "response_format": {"type": "json_object"},
                              "messages": [{"role": "user", "content": prompt}]})
                    r.raise_for_status()
                    obj = json.loads(r.json()["choices"][0]["message"]["content"])
                    decision = str(obj.get("decision", "")).strip().upper()
                    if decision not in ("ADOPT", "NEW"):
                        decision = "NEW"      # unreadable => never adopt
                    rec = {"decision": decision,
                           "reason": str(obj.get("reason", ""))[:220],
                           "evidence_kind": kind}
                except Exception as e:  # noqa: BLE001 — API failure => NEW, counted
                    errors += 1
                    rec = {"decision": "NEW", "reason": f"api error: {e}"[:160],
                           "evidence_kind": kind, "error": True}
            cache[ck] = rec
            t.update(rec)
            done += 1
            if done % 200 == 0:
                ADOPT_CACHE.write_text(json.dumps(cache, ensure_ascii=False))
                el = time.monotonic() - t0
                print(f"  [adopt] {done}/{len(tasks)} ({errors} errors) "
                      f"{done/max(el,1):.1f}/s eta "
                      f"{(len(tasks)-done)*el/max(done,1)/60:.0f}m", flush=True)
                mindful_gate("adopt api")

        async with httpx.AsyncClient() as client:
            CH = 600
            for i in range(0, len(tasks), CH):
                await asyncio.gather(*(decide(client, t) for t in tasks[i:i + CH]))
        ADOPT_CACHE.write_text(json.dumps(cache, ensure_ascii=False))

        adopted = [t for t in tasks if t.get("decision") == "ADOPT"]
        ledger = {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "tau_adopt": TAU_ADOPT,
            "hydrate_cutoff": cutoff_now.isoformat(),
            "pool_topics": len(topics),
            "eligible_topics": int(eligible_mask.sum()),
            "excluded_topics": len(excluded),
            "excluded_reasons": dict(Counter(excluded.values())),
            "tasks": len(tasks), "adopted": len(adopted),
            "adoption_rate": round(len(adopted) / max(len(tasks), 1), 4),
            "api_errors": errors,
            "evidence_kinds": dict(Counter(t.get("evidence_kind") for t in tasks)),
            "decisions": tasks,
        }
        ADOPT_LEDGER.write_text(json.dumps(ledger, ensure_ascii=False))
        print(f"[adopt] ADOPT {len(adopted)}/{len(tasks)} "
              f"({100*ledger['adoption_rate']:.1f}%), {errors} errors -> "
              f"{ADOPT_LEDGER}")
        return 0
    finally:
        await conn.close()


# ------------------------------------------------------------------ measure
def apply_adoption(cs: list[dict[str, Any]],
                   adopted: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for c in cs:
        a = adopted.get(c["id"])
        if a is None:
            out.append(c)
        else:
            c2 = dict(c)
            c2["_orig_label"] = c["label"]
            c2["label"] = a["cand_label"]
            out.append(c2)
    return out


async def phase_measure(args: argparse.Namespace) -> int:
    import asyncpg
    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL required")
    if not ADOPT_LEDGER.exists():
        raise SystemExit("run --phase adopt first")
    ledger = json.loads(ADOPT_LEDGER.read_text())
    adopted_map = {t["cluster_id"]: t for t in ledger["decisions"]
                   if t.get("decision") == "ADOPT"}
    run5 = json.loads(RUN5_JSON.read_text())
    gate8 = json.loads(GATE8_JSON.read_text())
    frozen_nights: list[str] = run5["labelled_snapshots"]
    replay_snaps: list[str] = run5["replay_snapshots"]
    run5_per_snap = {r["snapshot"]: r for r in run5["per_snapshot"]}
    fams_all: list[dict[str, Any]] = run5["families"]
    fams_landing = [f for f in fams_all if f.get("scope") == "snapshot"]

    conn = await asyncpg.connect(db)
    await conn.execute("SET default_transaction_read_only = on")
    t_start = time.monotonic()
    cutoff_now = dt.datetime.now(dt.timezone.utc)
    try:
        mindful_gate("load")
        clusters = await load_clusters_chunked(conn)
        clusters_by_id = {c["id"]: c for c in clusters}
        snaps: dict[str, list[dict]] = defaultdict(list)
        for c in clusters:
            snaps[c["snapshot_at"]].append(c)
        loader_check = await verify_loader_equivalence(
            conn, clusters, "2026-07-28T00:00:00+00:00")
        if not loader_check["exact"]:
            raise SystemExit("[STOP] loader equivalence failed")

        # ---- G-BLOB-ADOPCION: verified from the ledger, fresh query ---------
        ex_rows = await conn.fetch(
            "SELECT id FROM dynamic_topics WHERE blob_confirmed_at IS NOT NULL "
            "OR label_status = 'failed' OR is_junk "
            "OR COALESCE(is_umbrella,false)")
        excluded_ids = {int(r["id"]) for r in ex_rows}
        blob_adoptions = [t for t in adopted_map.values()
                          if t["cand_topic_id"] in excluded_ids]
        print(f"[G-BLOB] adoptions from excluded topics: {len(blob_adoptions)}")

        cfg = LifecycleConfig()
        newest = frozen_nights[-1]

        # ---- FIDELITY 1: original-label graph rows ≡ run 5 ------------------
        fidelity_broken = False
        for snap in frozen_nights:
            cs = snaps[snap]
            g = consolidation_graph(cs, tau=args.tau, label_mode="engine",
                                    require_shared_country=True)
            exp = run5_per_snap[snap]["variants"]["supp engine-label + shared country"]
            if (g["edges"], g["largest"], g["share"]) != (
                    exp["edges"], exp["largest"], exp["share"]):
                fidelity_broken = True
                print(f"[FIDELITY MISMATCH] original {snap[:19]}")
        if fidelity_broken:
            raise SystemExit("[STOP] original-label graph fidelity failed")
        print("[fidelity] original-label graph rows reproduce run 5, 15/15")

        # ---- FIDELITY 2: single-night downstream ----------------------------
        sn_cut = dt.datetime.fromisoformat("2026-07-28").replace(tzinfo=dt.timezone.utc)
        topics_sn, _, _ = await hydrate_as_of(conn, clusters_by_id, sn_cut)
        ev: list[dict[str, Any]] = []
        process_snapshot_sim(topics_sn, snaps[newest], newest, cfg,
                             allow_multi=False, events=ev)
        val_sn = await validate_against_prod(conn, topic_of_cluster(topics_sn),
                                             topics_sn, [newest])
        print(f"[fidelity] single-night RAW vs prod: {val_sn['agreement_rate']}")
        if abs(val_sn["agreement_rate"] - 0.9381) > 0.02:
            raise SystemExit("[STOP] single-night downstream drifted > 2pp")
        del topics_sn, ev

        # ---- adopted-label cluster field ------------------------------------
        snaps_adopted: dict[str, list[dict]] = {}
        for snap in sorted(snaps):
            snaps_adopted[snap] = (apply_adoption(snaps[snap], adopted_map)
                                   if snap in set(frozen_nights) else snaps[snap])

        # ---- G-K2 / G-784 / G-FALSE on the ADOPTED field --------------------
        per_night: list[dict[str, Any]] = []
        for snap in frozen_nights:
            mindful_gate(f"graph-adopted {snap[:10]}")
            cs = snaps_adopted[snap]
            df_tokens: Counter = Counter()
            n_labels = 0
            for c in cs:
                if c["label"]:
                    n_labels += 1
                    df_tokens.update(_subject_tokens(c["label"]))
            Vn = _unit_rows(np.stack([c["centroid"] for c in cs]).astype(np.float64))
            g = consolidation_graph(cs, tau=args.tau, label_mode="engine",
                                    require_shared_country=True, V=Vn)
            fp = sample_false_pairs(cs, np.random.default_rng(args.seed),
                                    args.false_pairs)
            fpc = verify_false_construction(cs, fp)
            fs = false_side_with_country(cs, fp, Vn, tau=args.tau)
            sig = country_span_signature(cs, g["components"], df_tokens, n_labels)
            g_orig = run5_per_snap[snap]["variants"]["supp engine-label + shared country"]
            rec = {"snapshot": snap, "clusters": len(cs),
                   "adopted_here": sum(1 for c in cs if "_orig_label" in c),
                   "edges": g["edges"], "largest": g["largest"],
                   "share": g["share"], "K2_pass": g["share"] <= K2_MAX_SHARE,
                   "edges_original": g_orig["edges"],
                   "largest_original": g_orig["largest"],
                   "flagged_784": sig["flagged_784_class"],
                   "flagged_784_detail": sig["flagged"][:4],
                   "false_full": fs["admitted_full_rule"],
                   "false_label_only": fs["admitted_label_only"],
                   "false_check_ok": fpc["exact"]}
            if snap == newest:
                rec["families_components"] = [
                    family_components(f, cs, g["components"]) for f in fams_landing]
            per_night.append(rec)
            print(f"  [gate] {snap[:19]} adopted={rec['adopted_here']:5d} "
                  f"edges={g['edges']:5d} (was {g_orig['edges']:4d}) "
                  f"largest={g['largest']:3d} ({100*g['share']:.2f}%) "
                  f"K2={'P' if rec['K2_pass'] else 'F'} 784={sig['flagged_784_class']} "
                  f"false={fs['admitted_full_rule']}", flush=True)

        # ---- feeds: original (fidelity arm) + adopted -----------------------
        def build_feeds(source: dict[str, list[dict]], by_id: dict[int, dict]
                        ) -> tuple[dict, dict]:
            feeds: dict[str, tuple] = {}
            s2o: dict[int, list[int]] = {}
            base = 0
            for snap in replay_snaps:
                cs = source[snap]
                g = consolidation_graph(cs, tau=args.tau, label_mode="engine",
                                        require_shared_country=True)
                feed, mapping = build_super_clusters(cs, g["components"], base)
                base += len(cs) + 1
                apply_largest_member_label(feed, mapping, by_id)
                feeds[snap] = (feed, mapping)
                s2o.update(mapping)
            return feeds, s2o

        clusters_by_id_adopted = {c["id"]: c for s in snaps_adopted.values()
                                  for c in s}
        feeds_orig, s2o_orig = build_feeds(snaps, clusters_by_id)
        feeds_adop, s2o_adop = build_feeds(snaps_adopted, clusters_by_id_adopted)

        # ---- arms -----------------------------------------------------------
        # b_p8_orig     = FIDELITY: must reproduce the 8th gate's b_p8
        # cons_a_adop   = production landing on the adopted feed (the "producción"
        #                 comparator G-LANDING names)
        # b_p8_adop     = THE VERDICT SUBJECT
        arms_spec = [
            ("b_p8_orig", feeds_orig, s2o_orig, snaps, clusters_by_id, "pred"),
            ("cons_a_adop", feeds_adop, s2o_adop, snaps_adopted,
             clusters_by_id_adopted, "prod"),
            ("b_p8_adop", feeds_adop, s2o_adop, snaps_adopted,
             clusters_by_id_adopted, "pred"),
        ]
        downstream: dict[str, Any] = {}
        judge_payloads: list[dict[str, Any]] = []
        pool_candidates: dict[str, list[dict[str, Any]]] = {}
        window_ids: dict[str, set[int]] = {}
        for f in fams_landing:
            wf = next((x for x in fams_all
                       if x["name"] == f'{f["name"]} [window]'), None)
            window_ids[f["name"]] = set(f["cluster_ids"]) | set(
                wf["cluster_ids"] if wf else [])
        fam_blocks: dict[str, dict[str, Any]] = {}
        for f in fams_landing:
            sids = [s for cid in f["cluster_ids"]
                    for s in clusters_by_id[cid]["sample_signal_ids"]]
            hs = [r["headline"] for r in await conn.fetch(
                "SELECT DISTINCT ON (headline) headline FROM signals_v2 "
                "WHERE id = ANY($1::bigint[]) AND headline IS NOT NULL "
                "AND length(headline) >= 12 LIMIT 8", sids[:400])]
            fam_blocks[f["name"]] = {"name": f["name"], "labels": f["labels"],
                                     "headlines": hs,
                                     "countries": f.get("countries", [])}
        # family main supers on 07-28 for pool-candidate geometry (adopted feed)
        feed28, map28 = feeds_adop[newest]
        main_super: dict[str, np.ndarray] = {}
        for f in fams_landing:
            fam_set = set(f["cluster_ids"])
            best, bw = None, -1
            for sc in feed28:
                w = sum(clusters_by_id[c]["n_signals"]
                        for c in map28.get(sc["id"], [sc["id"]]) if c in fam_set)
                if w > bw:
                    best, bw = sc, w
            v = np.asarray(best["centroid"], dtype=np.float64)
            main_super[f["name"]] = v / max(float(np.linalg.norm(v)), 1e-12)

        for arm, feeds, s2o_all, source, by_id, kind in arms_spec:
            mindful_gate(f"arm {arm}")
            topics, hmeta, _ = await hydrate_as_of(conn, clusters_by_id, cutoff_now)
            if arm == "b_p8_orig":
                pool_labels = [(int(t.id) if t.id is not None else None,
                                t.identity_key, t.label) for t in topics]
                P = _unit_rows(np.stack([t.centroid for t in topics]))
                for fname, v in main_super.items():
                    cos = P @ v
                    top = np.argsort(-cos)[:10]
                    pool_candidates[fname] = [
                        {"prod_id": pool_labels[i][0],
                         "identity": pool_labels[i][1],
                         "label": pool_labels[i][2],
                         "cos": round(float(cos[i]), 4), "via": "cos"}
                        for i in top.tolist()]
                    fam_modal = Counter(
                        clusters_by_id[c]["label"] for c in
                        next(x for x in fams_landing
                             if x["name"] == fname)["cluster_ids"]
                        if clusters_by_id[c]["label"]).most_common(1)[0][0]
                    seen = {p["identity"] for p in pool_candidates[fname]}
                    extra = 0
                    for k2, (pid, ident, lab) in enumerate(pool_labels):
                        if extra >= 6:
                            break
                        if ident in seen or not lab:
                            continue
                        if p8_compatible(fam_modal, lab):
                            pool_candidates[fname].append(
                                {"prod_id": pid, "identity": ident,
                                 "label": lab,
                                 "cos": round(float(P[k2] @ v), 4),
                                 "via": "p8-label"})
                            extra += 1
                del P
            events: list[dict[str, Any]] = []
            per_snap = []
            for snap in replay_snaps:
                mindful_gate(f"{arm} {snap[:10]}")
                feed, _m = feeds[snap]
                if kind == "prod":
                    res = process_snapshot_sim(topics, feed, snap, cfg,
                                               allow_multi=False, events=events)
                else:
                    res = process_snapshot_arm_pred(topics, feed, snap, cfg,
                                                    events, p8_compatible, None)
                per_snap.append({**res, "fed_clusters": len(feed)})
                print(f"  [{arm:11s}] {snap[:19]} fed={len(feed):5d} "
                      f"att={res.get('attached', 0):5d} "
                      f"fnd={res.get('founded', 0):5d} "
                      f"blk={res.get('label_blocked_foundings', '-')}", flush=True)
            owner_super = topic_of_cluster(topics)
            owner_orig: dict[int, int] = {}
            for sid, ti in owner_super.items():
                for cid in s2o_all.get(sid, [sid]):
                    owner_orig[cid] = ti
            fam_scores = [family_destination(f, topics, owner_orig, by_id)
                          for f in fams_all]
            entry: dict[str, Any] = {
                "hydrate": hmeta, "n_topics_end": len(topics),
                "states": dict(Counter(t.state for t in topics)),
                "attached_total": sum(s.get("attached", 0) for s in per_snap),
                "founded_total": sum(s.get("founded", 0) for s in per_snap),
                "per_snapshot": [{k: v for k, v in s.items()
                                  if k != "blocked_detail"} for s in per_snap],
                "families": fam_scores,
            }
            if kind == "pred":
                dec = sum(s.get("joins_decidable", 0) for s in per_snap)
                blk = sum(s.get("label_blocked_foundings", 0) for s in per_snap)
                c99 = sum(s.get("decidable_cos99", 0) for s in per_snap)
                b99 = sum(s.get("blocked_cos99", 0) for s in per_snap)
                entry["founding_gate"] = {
                    "decidable_landing_picks": dec + blk,
                    "joins_decidable": dec,
                    "label_blocked_foundings": blk,
                    "blocked_rate_of_decidable": round(blk / max(dec + blk, 1), 4),
                    "known_same_story_cos99": {
                        "decidable": c99 + b99, "blocked": b99,
                        "false_block_rate": round(b99 / max(c99 + b99, 1), 4)},
                    "blocked_examples": [d for s in per_snap
                                         for d in s.get("blocked_detail", [])][:40],
                }
            if arm != "b_p8_orig":
                for f in fams_landing:
                    sc = next(x for x in fam_scores if x["family"] == f["name"])
                    ti = sc["largest_topic_index"]
                    if ti is None:
                        judge_payloads.append({"family_name": f["name"],
                                               "arm": arm,
                                               "family": fam_blocks[f["name"]],
                                               "destination": None,
                                               "scorable": False})
                        continue
                    dest = await destination_receipts(
                        conn, topics, ti, s2o_all, window_ids[f["name"]], by_id)
                    judge_payloads.append({
                        "family_name": f["name"], "arm": arm,
                        "family": fam_blocks[f["name"]], "destination": dest,
                        "scorable": True,
                        "coverage": sc["story_coverage_signals"]})
            downstream[arm] = entry
            del topics, owner_super, owner_orig, events

        # ---- FIDELITY 3: b_p8_orig vs the 8th gate's b_p8 -------------------
        fg_now = downstream["b_p8_orig"]["founding_gate"]
        fg_8 = gate8["downstream"]["b_p8"]["founding_gate"]
        drift = abs(fg_now["label_blocked_foundings"]
                    - fg_8["label_blocked_foundings"]) / max(
                        fg_8["label_blocked_foundings"], 1)
        print(f"[fidelity] b_p8 original: blocked {fg_now['label_blocked_foundings']}"
              f" vs 8th {fg_8['label_blocked_foundings']} (drift {100*drift:.2f}%)")
        if drift > 0.02:
            raise SystemExit("[STOP] b_p8-original drifted > 2% from the 8th gate")

        # ---- pool-check payloads (self-founded rule) ------------------------
        pool_checks: list[dict[str, Any]] = []
        for p in judge_payloads:
            if not p.get("scorable") or not p["destination"]["self_founded"]:
                continue
            cands = []
            for c in pool_candidates[p["family_name"]][:12]:
                if c["prod_id"] is None:
                    continue
                rec = await pool_topic_receipts(conn, c["prod_id"],
                                                window_ids[p["family_name"]])
                cands.append({**c, "receipts": rec})
            pool_checks.append({"family_name": p["family_name"], "arm": p["arm"],
                                "family": fam_blocks[p["family_name"]],
                                "candidates": cands})

        # ---- adoption-judgment payloads (G-ADOPCION sample) -----------------
        adoptions = [t for t in ledger["decisions"] if t.get("decision") == "ADOPT"]
        rng = np.random.default_rng(args.seed)
        n_s = min(len(adoptions), max(G_ADOPTION_MIN_SAMPLE, 60))
        sample_idx = rng.choice(len(adoptions), size=n_s, replace=False)
        adoption_sample: list[dict[str, Any]] = []
        for i in sample_idx.tolist():
            a = adoptions[i]
            c = clusters_by_id[a["cluster_id"]]
            hl = [r["headline"] for r in await conn.fetch(
                "SELECT DISTINCT ON (headline) headline FROM signals_v2 "
                "WHERE id = ANY($1::bigint[]) AND headline IS NOT NULL "
                "AND length(headline) >= 12 LIMIT 6",
                c["sample_signal_ids"][:60])]
            topic_rec = await pool_topic_receipts(conn, a["cand_topic_id"], set())
            adoption_sample.append({
                **{k: a[k] for k in ("cluster_id", "snapshot", "orig_label",
                                     "cand_topic_id", "cand_identity",
                                     "cand_label", "cos", "reason",
                                     "evidence_kind")},
                "cluster_headlines": hl,
                "cluster_countries": c["cc"][:4],
                "cluster_n_signals": c["n_signals"],
                "topic_receipts": topic_rec})

        result = {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "harness": "backend/scripts/measure_label_adoption.py",
            "preregistration": PREREG_PATH,
            "read_only": True,
            "hydrate_cutoff_now": cutoff_now.isoformat(),
            "tau_adopt": TAU_ADOPT,
            "production_prompt": PRODUCTION_PROMPT,
            "production_candidate_block": PRODUCTION_CANDIDATE_BLOCK,
            "adoption_ledger_summary": {k: v for k, v in ledger.items()
                                        if k != "decisions"},
            "g_blob_adoption": {"adoptions_from_excluded": len(blob_adoptions),
                                "detail": blob_adoptions[:10]},
            "frozen_nights_15": frozen_nights,
            "replay_snapshots": replay_snaps,
            "loader_equivalence": loader_check,
            "fidelity_singlenight": {k: v for k, v in val_sn.items()
                                     if k != "examples"},
            "fidelity_b_p8_original": {"mine": fg_now, "gate8": fg_8,
                                       "relative_drift": round(drift, 4)},
            "per_night_adopted": per_night,
            "downstream": downstream,
            "pool_candidates": pool_candidates,
            "judge_payloads": judge_payloads,
            "pool_check_payloads": pool_checks,
            "adoption_sample": adoption_sample,
            "families": fams_all,
            "total_seconds": round(time.monotonic() - t_start, 1),
        }
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / f"{STEM}.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False,
                                  default=str), encoding="utf-8")
        print(f"[out] {out} — run --phase judge next")
        return 0
    finally:
        await conn.close()


# ------------------------------------------------------------------ judge
def adoption_judge_prompt(a: dict[str, Any]) -> str:
    hl = "\n".join(f"- {x}" for x in a["cluster_headlines"]) or \
        f"- (headlines expired; the cluster's own label was: \"{a['orig_label']}\")"
    rec = "\n".join(f"R{i+1}: {x}" for i, x in enumerate(a["topic_receipts"])) \
        or "(no receipts)"
    return (
        "A labeling-time ADOPTION decision made a news cluster inherit an "
        "existing topic's label. Judge whether that was CORRECT (same story) "
        "or a FALSE ADOPTION (different stories glued under one label — the "
        "seed of a black hole).\n\n"
        f"CLUSTER (originally labeled \"{a['orig_label']}\", "
        f"{a['cluster_n_signals']} signals, countries {a['cluster_countries']}):\n"
        f"{hl}\n\n"
        f"ADOPTED-FROM TOPIC (label \"{a['cand_label']}\", cosine {a['cos']}):\n"
        f"receipts (member labels + headlines):\n{rec}\n\n"
        "Same story = same specific occurrence/place/actors — not merely the "
        "same war, country, or theme. Your reason MUST include a short "
        "VERBATIM quoted excerpt copied exactly from the TOPIC receipts "
        "above. Reply ONLY JSON:\n"
        '{"verdict": "CORRECT" | "FALSE_ADOPTION", "reason": "<1-2 sentences '
        'with a verbatim quoted topic-receipt excerpt>"}')


async def ds_judge_adoption(a: dict[str, Any], key: str) -> dict[str, Any]:
    import httpx
    haystack = [{"headline": x} for x in a["topic_receipts"]]
    prompt = adoption_judge_prompt(a)
    attempts = []
    for attempt in range(2):
        body = {"model": "deepseek-chat", "temperature": 0,
                "messages": [{"role": "user", "content": prompt if attempt == 0
                              else prompt + "\n\nREMINDER: the reason failed "
                              "the quote check; copy a verbatim excerpt (>= 6 "
                              "chars, in quotes) from the TOPIC receipts."}]}
        async with httpx.AsyncClient() as c:
            r = await c.post(_DS_URL, json=body,
                             headers={"Authorization": f"Bearer {key}"},
                             timeout=60.0)
            r.raise_for_status()
            ans = r.json()["choices"][0]["message"]["content"]
        b = ans.strip().strip("`")
        b = b[b.find("{"):] if "{" in b else b
        verdict, reason = "", ""
        try:
            obj = json.loads(b)
            verdict = str(obj.get("verdict", "")).strip().upper()
            reason = str(obj.get("reason", "")).strip()
        except (json.JSONDecodeError, ValueError):
            verdict = ("FALSE_ADOPTION" if "false" in ans.lower()[:200]
                       else "CORRECT")
            reason = ans[:300]
        grounded = _reason_quotes_a_receipt(reason, haystack)
        attempts.append({"raw": ans, "verdict": verdict, "reason": reason,
                         "grounded": grounded})
        if grounded:
            break
    final = attempts[-1]
    # conservative: FALSE_ADOPTION verdicts AND still-ungrounded judgments
    # both count AGAINST the gate.
    false_for_gate = (final["verdict"] == "FALSE_ADOPTION"
                      or not final["grounded"])
    return {"attempts": attempts, "verdict": final["verdict"],
            "reason": final["reason"], "grounded": final["grounded"],
            "false_for_gate": false_for_gate}


async def phase_judge(args: argparse.Namespace) -> int:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("DEEPSEEK_API_KEY required")
    out = OUT_DIR / f"{STEM}.json"
    result = json.loads(out.read_text())
    judgments: list[dict[str, Any]] = []
    for p in result["judge_payloads"]:
        if not p.get("scorable"):
            judgments.append({"family": p["family_name"], "arm": p["arm"],
                              "scorable": False})
            continue
        j = await ds_judge_landing(p, key)
        judgments.append({
            "family": p["family_name"], "arm": p["arm"], "scorable": True,
            "destination_label": p["destination"]["label"],
            "destination_identity": p["destination"]["identity_key"],
            "self_founded": p["destination"]["self_founded"],
            "coverage": p.get("coverage"), **j})
        print(f"[judge] {p['family_name']:42s} {p['arm']:11s} -> "
              f"{j['verdict'].upper():10s} grounded={j['grounded']} "
              f"dest='{p['destination']['label']}'")
        print(f"        {j['reason'][:200]}")
    pool_checks: list[dict[str, Any]] = []
    for p in result["pool_check_payloads"]:
        r = await ds_pool_check(p, key)
        pool_checks.append({"family": p["family_name"], "arm": p["arm"], **r})
        print(f"[pool ] {p['family_name']:42s} {p['arm']:11s} -> "
              f"exists={r['exists']} which={r['which']} grounded={r['grounded']}")
    adoption_judgments: list[dict[str, Any]] = []
    for a in result["adoption_sample"]:
        j = await ds_judge_adoption(a, key)
        adoption_judgments.append({
            **{k: a[k] for k in ("cluster_id", "orig_label", "cand_label",
                                 "cand_identity", "cos", "evidence_kind")},
            **j})
        print(f"[adopt-judge] '{a['orig_label'][:38]:38s}' <- "
              f"'{a['cand_label'][:38]:38s}' -> {j['verdict']:14s} "
              f"grounded={j['grounded']}")
    result["landing_judgments"] = judgments
    result["pool_checks"] = pool_checks
    result["adoption_judgments"] = adoption_judgments
    result["verdict"] = verdict_block(result)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False,
                              default=str), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2, ensure_ascii=False))
    return 0


# ------------------------------------------------------------------ verdict
def verdict_block(res: dict[str, Any]) -> dict[str, Any]:
    kills: list[str] = []
    notes: list[str] = []
    # G-ADOPCION
    aj = res.get("adoption_judgments", [])
    n_j = len(aj)
    n_false = sum(1 for j in aj if j["false_for_gate"])
    false_rate = n_false / max(n_j, 1)
    g_adopt = n_j >= G_ADOPTION_MIN_SAMPLE and false_rate <= G_ADOPTION_MAX_FALSE
    if not g_adopt:
        kills.append(f"G-ADOPCION: {n_false}/{n_j} false adoptions "
                     f"({100*false_rate:.1f}%, bar <= 5%)")
    # G-BLOB-ADOPCION
    gb = res["g_blob_adoption"]["adoptions_from_excluded"]
    if gb:
        kills.append(f"G-BLOB-ADOPCION: {gb} adoptions from excluded topics")
    # G-K2/784/FALSE on adopted field
    nights = res["per_night_adopted"]
    k2_pass = sum(1 for r in nights if r["K2_pass"])
    if k2_pass < G_K2_MIN_NIGHTS:
        kills.append(f"G-K2 (adopted): {k2_pass}/15 (need >= {G_K2_MIN_NIGHTS}): "
                     + ", ".join(f"{r['snapshot'][:10]} {100*r['share']:.2f}%"
                                 for r in nights if not r["K2_pass"]))
    flagged = sum(r["flagged_784"] for r in nights)
    if flagged:
        kills.append(f"G-784 (adopted): {flagged} (bar 0)")
    ffail = [(r["snapshot"], r["false_full"]) for r in nights if r["false_full"]]
    if ffail:
        kills.append(f"G-FALSE (adopted): {ffail}")
    # G-FOUNDING + G-FALSE-BLOCK on b_p8_adop
    fga = res["downstream"]["b_p8_adop"]["founding_gate"]
    fgo = res["downstream"]["b_p8_orig"]["founding_gate"]
    g_found = fga["blocked_rate_of_decidable"] <= G_FOUNDING_MAX_RATE
    if not g_found:
        kills.append(f"G-FOUNDING: b_p8-adopted blocked "
                     f"{100*fga['blocked_rate_of_decidable']:.1f}% (bar <= 15%)")
    fb = fga["known_same_story_cos99"]["false_block_rate"]
    g_fb = fb < G_PRED_MAX_FALSE_BLOCK
    if not g_fb:
        kills.append(f"G-FALSE-BLOCK: {100*fb:.1f}% at cos>=0.99 (bar < 20%)")
    # G-LANDING
    judgments = res.get("landing_judgments", [])
    pool = {(p["family"], p["arm"]): p for p in res.get("pool_checks", [])}
    per_arm: dict[str, int] = defaultdict(int)
    table = []
    scorable = sorted({j["family"] for j in judgments if j.get("scorable")})
    for j in judgments:
        if not j.get("scorable"):
            continue
        counts = bool(j.get("counts_as_correct"))
        pc = pool.get((j["family"], j["arm"]))
        if counts and j.get("self_founded") and pc is not None:
            counts = bool(pc["counts_for_gate"])
        table.append({**{k: j.get(k) for k in
                         ("family", "arm", "destination_label", "verdict",
                          "grounded", "self_founded", "coverage")},
                      "pool_check": (None if pc is None else
                                     {"exists": pc["exists"],
                                      "which": pc["which"],
                                      "grounded": pc["grounded"]}),
                      "counts_for_gate": counts})
        if counts:
            per_arm[j["arm"]] += 1
    bar = math.ceil(2 * len(scorable) / 3)
    a_ok = per_arm.get("cons_a_adop", 0)
    p_ok = per_arm.get("b_p8_adop", 0)
    g_landing = p_ok >= bar and p_ok > a_ok
    if not g_landing:
        kills.append(f"G-LANDING: b_p8-adopted {p_ok}/{len(scorable)} "
                     f"(bar >= {bar}) vs production {a_ok} (must be strictly "
                     f"fewer)")
    notes.append(f"contrast: b_p8 ORIGINAL labels this run: founding "
                 f"{100*fgo['blocked_rate_of_decidable']:.1f}%, false-block "
                 f"{100*fgo['known_same_story_cos99']['false_block_rate']:.1f}%")
    return {
        "verdict": "KILL" if kills else "GO",
        "kills_fired": kills, "notes": notes,
        "G_ADOPCION": {"pass": g_adopt, "judged": n_j,
                       "false_adoptions": n_false,
                       "false_rate": round(false_rate, 4)},
        "G_BLOB_ADOPCION": {"pass": gb == 0, "violations": gb},
        "G_K2": {"pass": k2_pass >= G_K2_MIN_NIGHTS,
                 "passing_nights": k2_pass},
        "G_784": {"pass": flagged == 0, "flagged_total": flagged},
        "G_FALSE": {"pass": not ffail},
        "G_FOUNDING": {"pass": g_found,
                       **{k: v for k, v in fga.items()
                          if k != "blocked_examples"},
                       "original_labels_rate": fgo["blocked_rate_of_decidable"]},
        "G_FALSE_BLOCK": {"pass": g_fb, "adopted": fb,
                          "original": fgo["known_same_story_cos99"]
                          ["false_block_rate"]},
        "G_LANDING": {"pass": g_landing, "scorable": len(scorable),
                      "bar": bar, "correct_for_gate": dict(per_arm)},
        "G_COSTO": {"pass": True,
                    "argument": "adoption rides the existing per-cluster "
                                "labeling call (emergent_poc._label_all); the "
                                "candidate lookup is a local centroid dot "
                                "product; prompt published in the artifact"},
        "adoption_rate": res["adoption_ledger_summary"]["adoption_rate"],
        "landing_table": table,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="9th pre-registered identity gate: label adoption "
                    "(read-only).")
    ap.add_argument("--phase", choices=("adopt", "measure", "judge"),
                    required=True)
    ap.add_argument("--tau", type=float, default=MERGE_THRESHOLD)
    ap.add_argument("--false-pairs", type=int, default=FALSE_PAIR_TARGET)
    ap.add_argument("--seed", type=int, default=42)
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    fn = {"adopt": phase_adopt, "measure": phase_measure,
          "judge": phase_judge}[args.phase]
    raise SystemExit(asyncio.run(fn(args)))


if __name__ == "__main__":
    main()
