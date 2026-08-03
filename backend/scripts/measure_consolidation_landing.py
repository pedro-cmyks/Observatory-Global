#!/usr/bin/env python3
"""Seventh pre-registered identity gate: consolidation with the shared-country
conjunct PROMOTED TO PRIMARY, scored on IDENTITY-LANDING.

Pre-registration (FROZEN before this file was written, approved by Pedro):
  docs/superpowers/specs/2026-08-03-consolidation-landing-preregistration.md
Every bar in that file is immovable; this harness measures against it and a
single failed gate is a KILL, written plainly.

READ-ONLY. Writes no prod table (`SET default_transaction_read_only = on`).

EXTENDS `measure_cluster_consolidation.py` (the 5th gate's harness). That file
is left byte-untouched so its published numbers stay reproducible from its own
code; everything under test here is IMPORTED from it / from production —
`consolidation_graph`, `build_super_clusters`, `labels_compatible`,
`countries_share`, `process_snapshot_sim`, `hydrate_as_of`, the false-pair
construction, the 784-class signature, the quote-gate — never re-implemented.
The ONE copied-and-modified function is `process_snapshot_arm_b` (one decision
changed, marked `### ARM-B`), following the same convention
`simulate_used_t_removal.process_snapshot_sim` used for `used_t`.

THE RULE UNDER TEST (inherited; run 5 §11.1 measured it post-hoc, this run
pre-registers it as primary — exactly what that artifact demanded):

    cos(centroid_a, centroid_b) >= 0.90          (MERGE_THRESHOLD, imported)
    AND labels_compatible(label_a, label_b)      (production, verbatim)
    AND countries_share(a, b)                    (the D3 conjunct, verbatim)

Connected components = ONE super-cluster = ONE pick against the pool.

TWO TERRAIN DIFFERENCES vs run 5 (both stated in the artifact):
  1. The downstream replay hydrates the topic pool AS-OF NOW — the cleaned
     pool (TF-3b + court + blob-veto + junk have operated since 08-01); run 5
     hydrated as-of 2026-07-17 (the pre-cleanup July field).
  2. Landing is measured under two arms per super-cluster:
       Arm A (production): join if the best admissible pair clears MATCH 0.88
         + ANCHOR 0.93, `used_t` intact — `process_snapshot_sim`
         (allow_multi=False), verbatim.
       Arm B (found-biased): the SAME production pick, additionally gated on
         labels_compatible(super_label, target_label at snapshot start); an
         incompatible pick FOUNDS a new identity instead of joining (the
         target topic is NOT consumed, and the super-cluster does NOT fall
         through to its next-best target — found-biased by construction).

SUPER-CLUSTER LABEL POLICY (stated per the task): the label of the LARGEST
member cluster by n_signals (ties -> smallest cluster id), overriding
`build_super_clusters`' modal/longest choice; the modal label is kept in
`_modal_label` and the override count is published.

BLACKOUT SEMANTICS (pre-registration: the 5 NULL-label nights "no pueden
portar la regla"): a NULL-label super-cluster cannot carry arm B's gate, so
on those picks arm B DEGRADES TO PRODUCTION SEMANTICS (join), counted in
`undecidable_super` — the alternative (found-everything on 5 nights of
2-4k clusters) would be the trivialization G-FOUNDING exists to forbid.
A labelled super-cluster picking an EMPTY-labelled target IS decidable
(production's `labels_compatible` returns False on empty) and founds; counted
separately in `blocked_empty_target`.

FROZEN GATES (any fail => overall KILL):
  G-K2        largest component <= 2% of the night's clusters on >= 14 of the
              15 inherited labelled nights (run 5's exact snapshot list).
  G-784       components spanning >= 3 primary countries AND carrying an
              incompatible label pair = 0 across those 15 nights.
  G-LANDING   (primary) arm B lands the event on a CORRECT identity in
              >= ceil(2/3 * scorables) of the scorable witness families
              (>= 4 of 6 when all 6 score) AND strictly more correct
              families than arm A.  Judged: DeepSeek temp-0 with the court's
              quote-gate + human spot-check of all judgments.
  G-COVERAGE  (secondary, never reported alone) arm B family coverage >= the
              RAW arm's, per scorable family.
  G-FOUNDING  arm B's label-blocked foundings <= 15% of decidable landing
              picks (found-everything = hiding the problem).
  G-FALSE     0/1200 mechanically-FALSE pairs admitted per labelled night.
              (For the +country rule the construction is disjoint-country by
              definition, so admission is structurally 0 — computed anyway
              and the label-only admission is published beside it.)

FIDELITY (STOP RULE): before any gate is read, run 5's published numbers must
reproduce from today's DB — per-night graph rows (edges/largest/share) for
both the label-only and +country variants, all five variant rows + fastpath
equivalence + false-construction check on 07-28, and the single-night
downstream RAW-arm agreement vs prod (93.81%). Any mismatch beyond stated
tolerance aborts the run: a broken instrument measures nothing.

Usage (M1 mlvenv; read-only; Pedro on the machine => taskpolicy -b ALWAYS):
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend && taskpolicy -b nice -n 19 \
      /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.measure_consolidation_landing --phase measure
  ... then --phase judge
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import math
import os
import re
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np

# --- production module: the rules are IMPORTED, never re-implemented ----------
from scripts.project_dynamic_topics import (  # noqa: E402
    ANCHOR_THRESHOLD,
    MATCH_THRESHOLD,
    MERGE_LABEL_MIN,
    MERGE_THRESHOLD,
    LifecycleConfig,
    Topic,
    _subject_tokens,
    labels_compatible,
    next_state,
)

# --- the used_t harness: replay machinery, imported so every arm shares it ----
from scripts.simulate_used_t_removal import (  # noqa: E402
    _unit_rows,
    candidate_pairs,
    hydrate_as_of,
    load_clusters,
    process_snapshot_sim,
    topic_of_cluster,
    validate_against_prod,
)

# --- the 5th gate's harness: the consolidation machinery under test -----------
from scripts.measure_cluster_consolidation import (  # noqa: E402
    FALSE_PAIR_TARGET,
    K2_MAX_SHARE,
    build_super_clusters,
    consolidation_graph,
    country_span_signature,
    family_components,
    sample_false_pairs,
    score_false_pairs,
    score_family_downstream,
    super_cluster_geometry,
    verify_false_construction,
    verify_fastpath,
)  # component_detail deliberately not imported: unused here

# --- shared predicates ---------------------------------------------------------
from scripts.measure_evidence_fingerprint import countries_share  # noqa: E402

# --- the court's quote-gate, verbatim (GB3 pattern) ---------------------------
from scripts.label_court import _reason_quotes_a_receipt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
STEM = "2026-08-03-consolidation-landing"
RUN5_JSON = OUT_DIR / "2026-07-30-cluster-consolidation.json"
PREREG_PATH = ("docs/superpowers/specs/"
               "2026-08-03-consolidation-landing-preregistration.md")

# ---- frozen gate constants (from the pre-registration; never moved) ----------
G_K2_MIN_NIGHTS = 14          # of the 15 inherited labelled nights
G_FOUNDING_MAX_RATE = 0.15
MEM_ABORT_BELOW_PCT = 15      # mindful: pause/abort rather than push
_DS_URL = "https://api.deepseek.com/chat/completions"


# ------------------------------------------------------------------ mindful
def memory_free_pct() -> int | None:
    try:
        out = subprocess.run(["memory_pressure", "-Q"], capture_output=True,
                             text=True, timeout=15).stdout
        m = re.search(r"free percentage:\s*(\d+)", out)
        return int(m.group(1)) if m else None
    except Exception:
        return None


def mindful_gate(tag: str, *, wait_minutes: int = 30) -> None:
    """Pedro is on this machine. If free memory drops below the abort floor,
    PAUSE (up to `wait_minutes`) and then abort rather than push into swap."""
    waited = 0
    while True:
        pct = memory_free_pct()
        if pct is None or pct >= MEM_ABORT_BELOW_PCT:
            return
        if waited >= wait_minutes * 60:
            raise SystemExit(
                f"[mindful] free memory {pct}% < {MEM_ABORT_BELOW_PCT}% for "
                f"{wait_minutes} min at {tag} — aborting rather than swapping")
        print(f"[mindful] free memory {pct}% < {MEM_ABORT_BELOW_PCT}% at {tag}; "
              f"pausing 60s …", flush=True)
        time.sleep(60)
        waited += 60


# ------------------------------------------------------------------ loading
async def load_clusters_chunked(conn) -> list[dict[str, Any]]:
    """Memory-safe equivalent of `simulate_used_t_removal.load_clusters(conn,
    None)`: one query per snapshot so the asyncpg Records (python-float lists,
    ~24KB/row transient) never all coexist. Output shape is IDENTICAL row for
    row; equivalence vs the imported loader is PROVEN on a bounded window by
    `verify_loader_equivalence`, not assumed."""
    snaps = await conn.fetch(
        "SELECT DISTINCT snapshot_at FROM emergent_clusters "
        "WHERE centroid_vec IS NOT NULL ORDER BY snapshot_at")
    out: list[dict[str, Any]] = []
    for i, s in enumerate(snaps):
        rows = await conn.fetch(
            "SELECT id, snapshot_at, cluster_id, label, n_signals, cohesion, "
            "sample_signal_ids, centroid_vec, role_noise_rate, top_country_codes "
            "FROM emergent_clusters WHERE centroid_vec IS NOT NULL "
            "AND snapshot_at = $1 ORDER BY snapshot_at, cluster_id",
            s["snapshot_at"])
        for r in rows:
            out.append({
                "id": int(r["id"]), "snapshot_at": r["snapshot_at"].isoformat(),
                "snapshot_ts": r["snapshot_at"],
                "cluster_id": r["cluster_id"], "label": r["label"],
                "n_signals": int(r["n_signals"] or 0),
                "cohesion": float(r["cohesion"]) if r["cohesion"] is not None else None,
                "sample_signal_ids": [int(x) for x in (r["sample_signal_ids"] or [])],
                "centroid": np.array(r["centroid_vec"], dtype=np.float64),
                "noise": (float(r["role_noise_rate"])
                          if r["role_noise_rate"] is not None else None),
                "cc": [str(x) for x in (r["top_country_codes"] or [])],
            })
        if (i + 1) % 20 == 0:
            print(f"  [load] {i+1}/{len(snaps)} snapshots, {len(out)} clusters",
                  flush=True)
    return out


async def verify_loader_equivalence(conn, mine: list[dict[str, Any]],
                                    start_iso: str) -> dict[str, Any]:
    """Prove the chunked loader ≡ the imported `load_clusters` on the window
    [start_iso, ∞). Field-by-field, centroids exact."""
    start = dt.datetime.fromisoformat(start_iso)
    theirs = await load_clusters(conn, start)
    mine_w = [c for c in mine if c["snapshot_ts"] >= start]
    if len(theirs) != len(mine_w):
        return {"exact": False, "theirs": len(theirs), "mine": len(mine_w)}
    bad = 0
    for a, b in zip(mine_w, theirs):
        if (a["id"] != b["id"] or a["label"] != b["label"]
                or a["n_signals"] != b["n_signals"] or a["cc"] != b["cc"]
                or a["sample_signal_ids"] != b["sample_signal_ids"]
                or not np.array_equal(a["centroid"], b["centroid"])):
            bad += 1
    return {"exact": bad == 0, "compared": len(theirs), "mismatches": bad}


# ------------------------------------------------------------------ feed
def apply_largest_member_label(supers: list[dict[str, Any]],
                               mapping: dict[int, list[int]],
                               by_id: dict[int, dict]) -> int:
    """Pre-registered label policy: a merged super-cluster's label = the label
    of its LARGEST member cluster (n_signals; ties -> smallest cluster id).
    `build_super_clusters`' modal/longest label is preserved in `_modal_label`;
    returns how many merged supers changed label under this policy."""
    changed = 0
    for sc in supers:
        cids = mapping.get(sc["id"], [])
        if len(cids) < 2:
            continue
        largest = max((by_id[c] for c in cids),
                      key=lambda m: (m["n_signals"], -m["id"]))
        sc["_modal_label"] = sc["label"]
        if sc["label"] != largest["label"]:
            changed += 1
        sc["label"] = largest["label"]
    return changed


# ------------------------------------------------------------------ arm B
def process_snapshot_arm_b(topics: list[Topic], snap_clusters: list[dict[str, Any]],
                           snap: str, cfg: LifecycleConfig,
                           events: list[dict[str, Any]]) -> dict[str, Any]:
    """COPY of `simulate_used_t_removal.process_snapshot_sim` with
    allow_multi=False hard-wired (production `used_t` INTACT) and ONE decision
    changed, marked `### ARM-B` below. Everything else — gates, order, attach,
    founding, state advance — is production's, byte-for-byte in behaviour."""
    if not snap_clusters:
        return {"snapshot": snap, "n_clusters": 0}
    cvecs = np.stack([np.asarray(c["centroid"], dtype=np.float64)
                      for c in snap_clusters])
    tcent = (np.stack([t.centroid for t in topics]) if topics
             else np.zeros((0, cvecs.shape[1])))
    tanch = (np.stack([t.anchor_centroid for t in topics]) if topics
             else np.zeros((0, cvecs.shape[1])))
    # target labels FROZEN at snapshot start: attach() mid-loop can shift a
    # topic's modal label, and a gate that moves during the pass is untestable.
    topic_labels_start = [t.label for t in topics]
    if topics:
        s_arr, ci_arr, ti_arr, diag = candidate_pairs(cvecs, tcent, tanch)
    else:
        s_arr = np.array([]); ci_arr = np.array([], dtype=np.int64)
        ti_arr = np.array([], dtype=np.int64)
        diag = {"near_gate": 0, "match_only_blocked_by_anchor": 0,
                "anchor_only_blocked_by_match": 0, "n_pairs": 0}

    used_c: set[int] = set()
    used_t: set[int] = set()
    blocked: set[int] = set()
    seen_topics: set[int] = set()
    absorbed: dict[int, list[int]] = defaultdict(list)
    joins_decidable = 0
    joins_undecidable = 0
    blocked_empty_target = 0
    blocked_detail: list[dict[str, Any]] = []
    for k in range(s_arr.size):
        s = float(s_arr[k]); ci = int(ci_arr[k]); ti = int(ti_arr[k])
        if ci in used_c or ci in blocked:
            continue
        if ti in used_t:
            continue
        # ### ARM-B — this pair is production's pick for this super-cluster
        # (arm A joins here unconditionally). Arm B additionally requires
        # labels_compatible(super_label, target_label_at_start); an
        # incompatible pick FOUNDS a new identity instead — the super-cluster
        # never falls through to a lower-cos target (found-biased, per the
        # pre-registration) and the target topic is NOT consumed. A NULL-label
        # super-cluster (blackout feed) cannot carry the gate and degrades to
        # production semantics (join), counted as undecidable.
        clabel = snap_clusters[ci].get("label")
        tlabel = topic_labels_start[ti]
        if clabel:
            if labels_compatible(clabel, tlabel):
                joins_decidable += 1
            else:
                blocked.add(ci)
                if not tlabel:
                    blocked_empty_target += 1
                if len(blocked_detail) < 400:
                    blocked_detail.append({
                        "cluster_id": snap_clusters[ci]["id"],
                        "super_label": clabel,
                        "target_identity": topics[ti].identity_key,
                        "target_label": tlabel, "cos": round(s, 4)})
                continue
        else:
            joins_undecidable += 1
        used_c.add(ci)
        used_t.add(ti)
        topics[ti].attach(snap_clusters[ci], snap, s)
        seen_topics.add(ti)
        absorbed[ti].append(ci)
        events.append({"snapshot": snap, "topic_idx": ti,
                       "topic_identity": topics[ti].identity_key,
                       "cluster_id": snap_clusters[ci]["id"],
                       "score": round(s, 6),
                       "rank_in_topic": len(absorbed[ti])})

    founded = 0
    for ci, c in enumerate(snap_clusters):
        if ci not in used_c:          # blocked cis are NOT in used_c => they found
            t = Topic(
                identity_key=f"dyn-{c['snapshot_at']}-{c['cluster_id']}",
                label=c["label"], centroid=c["centroid"], snap=snap,
                n_signals=c["n_signals"], cohesion=c.get("cohesion"),
                noise=c.get("noise"),
                content_roundup=bool(c.get("content_roundup")),
            )
            t.members.append({"cluster_id": c["id"], "snapshot_at": snap,
                              "match_score": 1.0})
            topics.append(t)
            seen_topics.add(len(topics) - 1)
            founded += 1

    for ti, t in enumerate(topics):
        seen = ti in seen_topics
        t.since_seen = 0 if seen else t.since_seen + 1
        new_state = next_state(
            t.state, seen_now=seen, n_snapshots=len(t.snapshots),
            mean_cohesion=t.mean_cohesion, agg_n_signals=t.agg_n_signals,
            is_roundup=t.is_roundup, since_seen=t.since_seen, cfg=cfg,
            noise_rate=t.noise_rate, is_junk=t.is_junk,
        )
        if new_state != t.state:
            t.state = new_state
            t.dirty = True

    sizes = [len(v) for v in absorbed.values()]
    return {
        "snapshot": snap, "n_clusters": len(snap_clusters),
        "n_topics_before": len(topics) - founded,
        "attached": len(used_c), "founded": founded,
        "joins_decidable": joins_decidable,
        "joins_undecidable_super": joins_undecidable,
        "label_blocked_foundings": len(blocked),
        "blocked_empty_target": blocked_empty_target,
        "blocked_detail": blocked_detail,
        "topics_receiving": len(absorbed),
        "max_absorbed": max(sizes) if sizes else 0,
        **diag,
    }


# ------------------------------------------------------------------ scoring
def family_destination(fam: dict[str, Any], topics: list[Topic],
                       owner_orig: dict[int, int],
                       clusters_by_id: dict[int, dict]) -> dict[str, Any]:
    """`score_family_downstream` (imported, verbatim) plus the largest-holder
    INDEX, which the judge needs to reach the Topic object. The index is
    recomputed with the identical construction and ASSERTED to agree with the
    imported function's identity, so the two cannot drift."""
    base = score_family_downstream(fam, topics, owner_orig, clusters_by_id)
    holders_signals: Counter = Counter()
    for cid in fam["cluster_ids"]:
        ti = owner_orig.get(cid)
        if ti is None:
            continue
        n = clusters_by_id[cid]["n_signals"] if cid in clusters_by_id else 0
        holders_signals[ti] += n
    ti = holders_signals.most_common(1)[0][0] if holders_signals else None
    if ti is not None:
        assert topics[ti].identity_key == base["largest_topic_identity"], \
            f"destination drift for {fam['name']}"
    return {**base, "largest_topic_index": ti}


async def destination_receipts(conn, topics: list[Topic], t_idx: int,
                               super_to_orig: dict[int, list[int]],
                               exclude_ids: set[int],
                               clusters_by_id: dict[int, dict]) -> dict[str, Any]:
    """What the destination identity ACTUALLY holds, for the judge — with the
    witness family's own clusters EXCLUDED so a family that lands somewhere
    cannot vouch for itself through the receipts it just brought.

    Pre-existing prod topic (t.id set): member clusters + sample headlines from
    `dynamic_topic_members` (prod state, immutable history). If exclusion
    leaves nothing, the topic is BUILT FROM this family (`family_native`) and
    its own receipts are shown — the judgment then reads "does this identity's
    label describe the event", which is exactly the founding case.
    Sim-founded topic (t.id None): receipts from its founding clusters via
    `super_to_orig`; all-family founders are `self_founded`."""
    t = topics[t_idx]
    lines: list[dict[str, str]] = []
    flags = {"self_founded": False, "family_native": False}

    async def _headlines(sids: list[int], cap: int = 12) -> list[str]:
        if not sids:
            return []
        rows = await conn.fetch(
            "SELECT DISTINCT ON (headline) headline FROM signals_v2 "
            "WHERE id = ANY($1::bigint[]) AND headline IS NOT NULL "
            "AND length(headline) >= 12 LIMIT $2", sids[:400], cap)
        return [r["headline"] for r in rows]

    def _cluster_lines(cids: list[int]) -> tuple[list[dict[str, str]], list[int]]:
        out: list[dict[str, str]] = []
        sids: list[int] = []
        for cid in cids:
            c = clusters_by_id.get(cid)
            if c is None:
                continue
            if c["label"]:
                out.append({"kind": "member_cluster_label",
                            "text": f"{c['label']} ({c['n_signals']} signals, "
                                    f"{c['snapshot_at'][:10]})"})
            sids.extend(c["sample_signal_ids"])
        return out, sids

    if t.id is not None:
        rows = await conn.fetch(
            "SELECT ec.id, ec.label, ec.n_signals, ec.snapshot_at, "
            "       ec.sample_signal_ids "
            "FROM dynamic_topic_members dtm "
            "JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id "
            "WHERE dtm.dynamic_topic_id = $1 "
            "  AND NOT (dtm.emergent_cluster_id = ANY($2::bigint[])) "
            "ORDER BY dtm.snapshot_at DESC LIMIT 15",
            t.id, sorted(exclude_ids))
        if not rows:
            flags["family_native"] = True
            rows = await conn.fetch(
                "SELECT ec.id, ec.label, ec.n_signals, ec.snapshot_at, "
                "       ec.sample_signal_ids "
                "FROM dynamic_topic_members dtm "
                "JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id "
                "WHERE dtm.dynamic_topic_id = $1 "
                "ORDER BY dtm.snapshot_at DESC LIMIT 15", t.id)
        sids: list[int] = []
        for r in rows:
            if r["label"]:
                lines.append({"kind": "member_cluster_label",
                              "text": f"{r['label']} ({int(r['n_signals'] or 0)} "
                                      f"signals, {r['snapshot_at'].date()})"})
            sids.extend(int(x) for x in (r["sample_signal_ids"] or []))
        for h in await _headlines(sids):
            lines.append({"kind": "headline", "text": h})
    else:
        orig = [cid for m in t.members
                for cid in super_to_orig.get(int(m["cluster_id"]),
                                             [int(m["cluster_id"])])]
        non_family = [c for c in orig if c not in exclude_ids]
        if not non_family:
            flags["self_founded"] = True
            source = orig
        else:
            source = non_family
        cl, sids = _cluster_lines(source)
        lines.extend(cl)
        for h in await _headlines(sids):
            lines.append({"kind": "headline", "text": h})
    return {"identity_key": t.identity_key, "prod_topic_id": t.id,
            "label": t.label, "state": t.state, "receipts": lines, **flags}


# ------------------------------------------------------------------ false side
def false_side_with_country(clusters: list[dict[str, Any]],
                            pairs: list[tuple[int, int]], V: np.ndarray,
                            *, tau: float) -> dict[str, Any]:
    """The imported `score_false_pairs` scores cos+label; the promoted rule adds
    `countries_share`. The FALSE construction samples countries_disjoint pairs,
    so admission under the full rule is 0 BY CONSTRUCTION — computed
    mechanically here (never asserted) and published with the label-only
    number, which is the informative one."""
    if not pairs:
        return {"pairs": 0, "admitted_full_rule": 0, "admitted_label_only": 0}
    label_only = score_false_pairs(clusters, pairs, V, tau=tau, label_mode="engine")
    ii = np.array([p[0] for p in pairs]); jj = np.array([p[1] for p in pairs])
    cos = np.einsum("ij,ij->i", V[ii], V[jj])
    full = 0
    for k in range(len(pairs)):
        if cos[k] < tau:
            continue
        a, b = pairs[k]
        if not labels_compatible(clusters[a]["label"], clusters[b]["label"]):
            continue
        if countries_share(clusters[a]["cc"], clusters[b]["cc"]):
            full += 1
    return {"pairs": len(pairs), "admitted_full_rule": full,
            "admitted_label_only": label_only["admitted"],
            "cos_only_admitted": label_only["cos_only_admitted"],
            "label_only_detail": label_only}


# ------------------------------------------------------------------ judge
_JUDGE_VERDICTS = ("correct", "wrong")


def parse_landing_verdict(text: str) -> tuple[str, str]:
    raw = (text or "").strip()
    body = raw
    if body.startswith("```"):
        body = body.strip("`")
        body = body[body.find("{"):] if "{" in body else body
    verdict = ""
    reason = ""
    try:
        obj = json.loads(body)
        if isinstance(obj, dict):
            verdict = str(obj.get("verdict", "")).strip().lower()
            reason = str(obj.get("reason", "")).strip()
    except (json.JSONDecodeError, ValueError):
        pass
    if verdict not in _JUDGE_VERDICTS:
        low = raw.lower()
        for v in _JUDGE_VERDICTS:
            if v in low:
                verdict = v
                break
    if verdict not in _JUDGE_VERDICTS:
        return "unparseable", raw[:300]
    return verdict, (reason or raw[:300])


def judge_prompt(payload: dict[str, Any]) -> str:
    fam = payload["family"]
    dest = payload["destination"]
    fam_lines = "\n".join(f"- {x}" for x in fam["labels"][:8])
    fam_heads = "\n".join(f"- {x}" for x in fam["headlines"][:8]) or "- (none survive retention)"
    rec = "\n".join(f"R{i+1} [{r['kind']}]: {r['text']}"
                    for i, r in enumerate(dest["receipts"][:24])) or "(no receipts)"
    return (
        "You are judging IDENTITY-LANDING for a news clustering engine.\n\n"
        "KNOWN EVENT (ground truth — a family of same-event fragments):\n"
        f"family name: {fam['name']}\n"
        f"fragment labels:\n{fam_lines}\n"
        f"sample headlines from the event:\n{fam_heads}\n\n"
        "DESTINATION (the identity the engine landed this event on):\n"
        f'label: "{dest["label"]}"\n'
        f"receipts (what this destination identity actually contains):\n{rec}\n\n"
        "QUESTION: Is the DESTINATION the same real-world event as the KNOWN "
        "EVENT? \"Same event\" means the same specific incident — same "
        "occurrence, same place, same actors. The same war, the same country, "
        "the same theme, or a related-but-different incident is NOT the same "
        "event.\n"
        "Your reason MUST contain at least one short VERBATIM quoted excerpt, "
        "copied EXACTLY, from the DESTINATION receipts above — this grounds "
        "the verdict and is mechanically checked; an ungrounded verdict is "
        "discarded. Reply ONLY with JSON:\n"
        '{"verdict": "CORRECT" | "WRONG", '
        '"reason": "<1-2 sentences with a verbatim quoted destination-receipt '
        'excerpt>"}\n'
        "- CORRECT: the destination identity is this same event.\n"
        "- WRONG: the destination is a different event, or a broader/unrelated "
        "identity.")


async def ds_judge_landing(payload: dict[str, Any], key: str) -> dict[str, Any]:
    import httpx
    receipts_for_gate = [{"headline": r["text"]} for r in payload["destination"]["receipts"]]
    prompt = judge_prompt(payload)
    out: dict[str, Any] = {"prompt_receipt_count": len(receipts_for_gate)}
    attempts = []
    for attempt in range(2):
        body = {"model": "deepseek-chat", "temperature": 0,
                "messages": [{"role": "user", "content": prompt if attempt == 0 else
                              prompt + "\n\nREMINDER: your previous answer failed "
                              "the quote check. The reason MUST copy a verbatim "
                              "excerpt (>= 6 characters, in double quotes) from "
                              "the DESTINATION receipts listed above."}]}
        async with httpx.AsyncClient() as c:
            r = await c.post(_DS_URL, json=body,
                             headers={"Authorization": f"Bearer {key}"},
                             timeout=60.0)
            r.raise_for_status()
            resp = r.json()
        ans = resp["choices"][0]["message"]["content"]
        verdict, reason = parse_landing_verdict(ans)
        grounded = _reason_quotes_a_receipt(reason, receipts_for_gate)
        attempts.append({"raw": ans, "verdict": verdict, "reason": reason,
                         "grounded": grounded})
        if grounded and verdict in _JUDGE_VERDICTS:
            break
    final = attempts[-1]
    out.update({"attempts": attempts, "verdict": final["verdict"],
                "reason": final["reason"], "grounded": final["grounded"],
                "counts_as_correct": final["verdict"] == "correct" and final["grounded"]})
    return out


# ------------------------------------------------------------------ measure
async def phase_measure(args: argparse.Namespace) -> int:
    import asyncpg
    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL required")
    run5 = json.loads(RUN5_JSON.read_text())
    frozen_nights: list[str] = run5["labelled_snapshots"]          # the 15
    replay_snaps: list[str] = run5["replay_snapshots"]             # the 12
    run5_per_snap = {r["snapshot"]: r for r in run5["per_snapshot"]}
    fams_all: list[dict[str, Any]] = run5["families"]              # verbatim
    fams_landing = [f for f in fams_all if f.get("scope") == "snapshot"]
    assert len(fams_landing) == 6, "expected the 6 snapshot-scoped witness families"

    conn = await asyncpg.connect(db)
    await conn.execute("SET default_transaction_read_only = on")
    t_start = time.monotonic()
    cutoff_now = dt.datetime.now(dt.timezone.utc)
    try:
        mindful_gate("load")
        t0 = time.monotonic()
        clusters = await load_clusters_chunked(conn)
        print(f"[load] {len(clusters)} clusters in {time.monotonic()-t0:.0f}s")
        clusters_by_id = {c["id"]: c for c in clusters}
        snaps: dict[str, list[dict]] = defaultdict(list)
        for c in clusters:
            snaps[c["snapshot_at"]].append(c)

        loader_check = await verify_loader_equivalence(
            conn, clusters, "2026-07-28T00:00:00+00:00")
        print(f"[fidelity] loader equivalence: {loader_check}")
        if not loader_check["exact"]:
            raise SystemExit("[STOP] chunked loader does not reproduce "
                             "load_clusters — instrument broken")

        inventory = []
        for snap in sorted(snaps):
            cs = snaps[snap]
            nulls = sum(1 for c in cs if not c["label"])
            inventory.append({"snapshot": snap, "clusters": len(cs),
                              "null_labels": nulls,
                              "null_rate": round(nulls / len(cs), 4)})
        missing_frozen = [s for s in frozen_nights if s not in snaps]
        if missing_frozen:
            raise SystemExit(f"[STOP] frozen nights pruned from prod: "
                             f"{missing_frozen} — the 15-night gates cannot "
                             f"be measured; report, do not improvise")
        extra_labelled = [i["snapshot"] for i in inventory
                          if i["null_rate"] == 0.0 and i["clusters"] >= 100
                          and i["snapshot"] > frozen_nights[-1]]
        print(f"[inv] {len(inventory)} snapshots; 15 frozen nights present; "
              f"{len(extra_labelled)} extra labelled nights: "
              f"{[s[:10] for s in extra_labelled]}")

        # ============ per-night graph gates + fidelity =====================
        newest = frozen_nights[-1]                                  # 07-28
        per_night: list[dict[str, Any]] = []
        fidelity_rows: list[dict[str, Any]] = []
        fidelity_broken = False
        for snap in frozen_nights + extra_labelled:
            mindful_gate(f"graph {snap[:10]}")
            cs = snaps[snap]
            df_tokens: Counter = Counter()
            n_labels = 0
            for c in cs:
                if c["label"]:
                    n_labels += 1
                    df_tokens.update(_subject_tokens(c["label"]))
            Vn = _unit_rows(np.stack([c["centroid"] for c in cs]).astype(np.float64))
            cand = None
            # candidate set computed once inside the first graph call, reused
            g_primary = consolidation_graph(
                cs, tau=args.tau, label_mode="engine",
                require_shared_country=True, V=Vn)
            cand = (g_primary["_cand_ii"], g_primary["_cand_jj"])
            g_labelonly = consolidation_graph(
                cs, tau=args.tau, label_mode="engine", cand=cand, V=Vn)
            fp = sample_false_pairs(cs, np.random.default_rng(args.seed),
                                    args.false_pairs)
            fp_check = verify_false_construction(cs, fp)
            false_side = false_side_with_country(cs, fp, Vn, tau=args.tau)
            sig = country_span_signature(cs, g_primary["components"],
                                         df_tokens, n_labels)
            rec: dict[str, Any] = {
                "snapshot": snap, "clusters": len(cs),
                "in_frozen_15": snap in frozen_nights,
                "false_pair_check": fp_check,
                "primary_shared_country": {
                    "edges": g_primary["edges"], "largest": g_primary["largest"],
                    "share": g_primary["share"],
                    "K2_pass": g_primary["share"] <= K2_MAX_SHARE,
                    "multi_components": g_primary["multi_components"],
                    "size_histogram": g_primary["size_histogram"],
                },
                "label_only": {
                    "edges": g_labelonly["edges"], "largest": g_labelonly["largest"],
                    "share": g_labelonly["share"],
                },
                "country_span_signature": {k: v for k, v in sig.items()
                                           if k != "flagged"} | {
                    "flagged": sig["flagged"][:5]},
                "false_side": false_side,
            }
            # ---- fidelity vs run 5 (frozen nights only; exact) ------------
            if snap in run5_per_snap:
                r5 = run5_per_snap[snap]["variants"]
                exp_c = r5["supp engine-label + shared country"]
                exp_l = r5["PRIMARY engine-label"]
                row = {"snapshot": snap,
                       "country_edges": (g_primary["edges"], exp_c["edges"]),
                       "country_largest": (g_primary["largest"], exp_c["largest"]),
                       "country_share": (g_primary["share"], exp_c["share"]),
                       "country_784": (sig["flagged_784_class"],
                                       exp_c["country_span_signature"]["flagged_784_class"]),
                       "label_edges": (g_labelonly["edges"], exp_l["edges"]),
                       "label_largest": (g_labelonly["largest"], exp_l["largest"]),
                       "false_admitted_label_only": (
                           false_side["admitted_label_only"],
                           exp_l["false_side"]["admitted"]),
                       "false_cos_only": (false_side["cos_only_admitted"],
                                          exp_l["false_side"]["cos_only_admitted"])}
                row["exact"] = all(v[0] == v[1] for v in row.values()
                                   if isinstance(v, tuple))
                fidelity_rows.append(row)
                if not row["exact"]:
                    fidelity_broken = True
                    print(f"[FIDELITY MISMATCH] {snap[:19]}: {row}")
            if snap == newest:
                # full five-variant reproduction + fastpath on 07-28
                g_uni = consolidation_graph(cs, tau=args.tau, label_mode="unicode",
                                            cand=cand, V=Vn)
                g_cos = consolidation_graph(cs, tau=args.tau, label_mode="none",
                                            cand=cand, V=Vn)
                r5v = run5_per_snap[snap]["variants"]
                rec["fidelity_0728_variants"] = {
                    "unicode": {"mine": [g_uni["edges"], g_uni["largest"], g_uni["share"]],
                                "run5": [r5v["supp unicode-label"]["edges"],
                                         r5v["supp unicode-label"]["largest"],
                                         r5v["supp unicode-label"]["share"]]},
                    "cos_only": {"mine": [g_cos["edges"], g_cos["largest"], g_cos["share"]],
                                 "run5": [r5v["M6 cos-only (no label conjunct)"]["edges"],
                                          r5v["M6 cos-only (no label conjunct)"]["largest"],
                                          r5v["M6 cos-only (no label conjunct)"]["share"]]},
                }
                for k, v in rec["fidelity_0728_variants"].items():
                    if v["mine"] != v["run5"]:
                        fidelity_broken = True
                        print(f"[FIDELITY MISMATCH] 07-28 {k}: {v}")
                rec["fastpath_equivalence"] = verify_fastpath(
                    [c["label"] for c in cs], cand[0], cand[1],
                    np.random.default_rng(args.seed))
                if not rec["fastpath_equivalence"]["exact"]:
                    fidelity_broken = True
                rec["families_components_primary"] = [
                    family_components(f, cs, g_primary["components"])
                    for f in fams_landing]
                # run 5 §11.1 family components under +country (fidelity)
                exp_fam = {f["family"]: f["components"]
                           for f in run5_per_snap[snap]["variants"]
                           ["supp engine-label + shared country"]["families"]}
                for f in rec["families_components_primary"]:
                    if exp_fam.get(f["family"]) != f["components"]:
                        fidelity_broken = True
                        print(f"[FIDELITY MISMATCH] family components "
                              f"{f['family']}: mine={f['components']} "
                              f"run5={exp_fam.get(f['family'])}")
            if not fp_check["exact"]:
                fidelity_broken = True
            per_night.append(rec)
            p = rec["primary_shared_country"]
            print(f"  [gate] {snap[:19]} n={len(cs):5d} edges={p['edges']:5d} "
                  f"largest={p['largest']:3d} ({100*p['share']:.2f}%) "
                  f"K2={'PASS' if p['K2_pass'] else 'FAIL'} "
                  f"784={sig['flagged_784_class']} "
                  f"false_full={false_side['admitted_full_rule']}"
                  f"/label_only={false_side['admitted_label_only']}", flush=True)

        if fidelity_broken:
            raise SystemExit("[STOP] fidelity checks failed to reproduce run 5 "
                             "— the instrument is broken; no gate was read")
        print("[fidelity] ALL frozen-night graph rows, 07-28 variant rows, "
              "fastpath, false construction and §11.1 family components "
              "reproduce run 5 exactly")

        # ============ downstream fidelity: run 5 §2 single-night ===========
        mindful_gate("singlenight fidelity")
        sn_cutoff = dt.datetime.fromisoformat("2026-07-28").replace(
            tzinfo=dt.timezone.utc)
        topics_sn, hmeta_sn, _ = await hydrate_as_of(conn, clusters_by_id, sn_cutoff)
        ev_sn: list[dict[str, Any]] = []
        cfg = LifecycleConfig()
        process_snapshot_sim(topics_sn, snaps[newest], newest, cfg,
                             allow_multi=False, events=ev_sn)
        owner_sn = topic_of_cluster(topics_sn)
        val_sn = await validate_against_prod(conn, owner_sn, topics_sn, [newest])
        print(f"[fidelity] single-night RAW vs prod: "
              f"{val_sn['agreement_rate']} (run 5: 0.9381; "
              f"excl-umbrella {val_sn['agreement_rate_excl_umbrella']})")
        singlenight_fidelity = {"mine": val_sn, "run5_agreement": 0.9381,
                                "hydrate": hmeta_sn,
                                "note": ("dynamic_topics states/labels are "
                                         "MUTABLE (TICK-V2 revert, TF-3b, "
                                         "court since run 5); geometry is "
                                         "member-replayed from immutable "
                                         "emergent_clusters, so small drift "
                                         "here is terrain, not instrument")}
        if abs(val_sn["agreement_rate"] - 0.9381) > 0.02:
            raise SystemExit(f"[STOP] single-night downstream fidelity "
                             f"{val_sn['agreement_rate']} drifted > 2pp from "
                             f"run 5's 0.9381 — investigate before reading gates")
        del topics_sn, ev_sn, owner_sn

        # ============ consolidated feeds (built once, shared by A and B) ===
        feeds: dict[str, tuple[list[dict], dict[int, list[int]]]] = {}
        feed_log: list[dict[str, Any]] = []
        geometry: dict[str, Any] = {}
        id_base = 0
        for snap in replay_snaps:
            mindful_gate(f"feed {snap[:10]}")
            cs = snaps[snap]
            gph = consolidation_graph(cs, tau=args.tau, label_mode="engine",
                                      require_shared_country=True)
            feed, mapping = build_super_clusters(cs, gph["components"], id_base)
            id_base += len(cs) + 1
            overrides = apply_largest_member_label(feed, mapping, clusters_by_id)
            geometry[snap] = super_cluster_geometry(cs, gph["components"],
                                                    feed, mapping)
            feeds[snap] = (feed, mapping)
            feed_log.append({
                "snapshot": snap, "clusters": len(cs), "super_clusters": len(feed),
                "merged_away": len(cs) - len(feed), "edges": gph["edges"],
                "largest_component": gph["largest"],
                "label_overrides_largest_vs_modal": overrides,
                "labelled": all(c["label"] for c in cs) if cs else False})
            print(f"  [feed] {snap[:19]} {len(cs)} -> {len(feed)} supers "
                  f"(merged away {len(cs)-len(feed)}, label overrides {overrides})")

        # ============ downstream: RAW / CONS-A / CONS-B ====================
        downstream: dict[str, Any] = {}
        arm_topics: dict[str, list[Topic]] = {}
        arm_owner: dict[str, dict[int, int]] = {}
        arm_s2o: dict[str, dict[int, list[int]]] = {}
        for arm in ("raw", "cons_a", "cons_b"):
            mindful_gate(f"arm {arm}")
            topics, hmeta, _umb = await hydrate_as_of(conn, clusters_by_id,
                                                      cutoff_now)
            events: list[dict[str, Any]] = []
            super_to_orig: dict[int, list[int]] = {}
            per_snap = []
            t0 = time.monotonic()
            for snap in replay_snaps:
                mindful_gate(f"{arm} {snap[:10]}")
                cs = snaps[snap]
                if arm == "raw":
                    feed = cs
                    super_to_orig.update({c["id"]: [c["id"]] for c in cs})
                else:
                    feed, mapping = feeds[snap]
                    super_to_orig.update(mapping)
                if arm == "cons_b":
                    res = process_snapshot_arm_b(topics, feed, snap, cfg, events)
                else:
                    res = process_snapshot_sim(topics, feed, snap, cfg,
                                               allow_multi=False, events=events)
                res.pop("blocked_detail_full", None)
                per_snap.append({**res, "fed_clusters": len(feed),
                                 "raw_clusters": len(cs)})
                print(f"  [{arm:6s}] {snap[:19]} fed={len(feed):5d} "
                      f"attached={res.get('attached', 0):5d} "
                      f"founded={res.get('founded', 0):5d} "
                      f"blocked={res.get('label_blocked_foundings', '-')} "
                      f"topics={len(topics)}", flush=True)
            owner_super = topic_of_cluster(topics)
            owner_orig: dict[int, int] = {}
            for sid, ti in owner_super.items():
                for cid in super_to_orig.get(sid, [sid]):
                    owner_orig[cid] = ti
            fam_scores = [family_destination(f, topics, owner_orig, clusters_by_id)
                          for f in fams_all]
            entry: dict[str, Any] = {
                "hydrate": hmeta, "seconds": round(time.monotonic() - t0, 1),
                "n_topics_end": len(topics),
                "states": dict(Counter(t.state for t in topics)),
                "attached_total": sum(s.get("attached", 0) for s in per_snap),
                "founded_total": sum(s.get("founded", 0) for s in per_snap),
                "per_snapshot": [{k: v for k, v in s.items()
                                  if k != "blocked_detail"} for s in per_snap],
                "families": fam_scores,
            }
            if arm == "cons_b":
                dec = sum(s.get("joins_decidable", 0) for s in per_snap)
                blk = sum(s.get("label_blocked_foundings", 0) for s in per_snap)
                und = sum(s.get("joins_undecidable_super", 0) for s in per_snap)
                emp = sum(s.get("blocked_empty_target", 0) for s in per_snap)
                entry["founding_gate"] = {
                    "decidable_landing_picks": dec + blk,
                    "joins_decidable": dec,
                    "label_blocked_foundings": blk,
                    "blocked_empty_target": emp,
                    "joins_undecidable_super_null_label": und,
                    "blocked_rate_of_decidable": round(blk / max(dec + blk, 1), 4),
                    "blocked_examples": [d for s in per_snap
                                         for d in s.get("blocked_detail", [])][:60],
                }
            if arm == "raw" and args.validate:
                entry["validation_last_night_vs_prod"] = await validate_against_prod(
                    conn, owner_orig, topics, replay_snaps)
            downstream[arm] = entry
            arm_topics[arm] = topics
            arm_owner[arm] = owner_orig
            arm_s2o[arm] = super_to_orig

        # ============ judge payloads (destinations + receipts) =============
        mindful_gate("judge payloads")
        window_ids: dict[str, set[int]] = {}
        for f in fams_landing:
            wname = f'{f["name"]} [window]'
            wf = next((x for x in fams_all if x["name"] == wname), None)
            window_ids[f["name"]] = set(f["cluster_ids"]) | set(
                wf["cluster_ids"] if wf else [])
        judge_payloads: list[dict[str, Any]] = []
        for f in fams_landing:
            fam_sids = [s for cid in f["cluster_ids"]
                        for s in clusters_by_id[cid]["sample_signal_ids"]]
            fam_heads = [r["headline"] for r in await conn.fetch(
                "SELECT DISTINCT ON (headline) headline FROM signals_v2 "
                "WHERE id = ANY($1::bigint[]) AND headline IS NOT NULL "
                "AND length(headline) >= 12 LIMIT 8", fam_sids[:400])]
            fam_block = {"name": f["name"], "labels": f["labels"],
                         "headlines": fam_heads,
                         "countries": f.get("countries", [])}
            for arm in ("cons_a", "cons_b"):
                sc = next(x for x in downstream[arm]["families"]
                          if x["family"] == f["name"])
                ti = sc["largest_topic_index"]
                if ti is None:
                    judge_payloads.append({
                        "family_name": f["name"], "arm": arm,
                        "family": fam_block, "destination": None,
                        "scorable": False, "note": "no destination (all "
                        "clusters unassigned)"})
                    continue
                dest = await destination_receipts(
                    conn, arm_topics[arm], ti, arm_s2o[arm],
                    window_ids[f["name"]], clusters_by_id)
                judge_payloads.append({
                    "family_name": f["name"], "arm": arm, "family": fam_block,
                    "destination": dest, "scorable": True,
                    "coverage": sc["story_coverage_signals"],
                    "identity_ok_lexical_proxy": sc["identity_ok"]})

        result = {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "harness": "backend/scripts/measure_consolidation_landing.py",
            "preregistration": PREREG_PATH,
            "read_only": True,
            "hydrate_cutoff_now": cutoff_now.isoformat(),
            "rule": {"tau": args.tau, "MERGE_THRESHOLD": MERGE_THRESHOLD,
                     "MERGE_LABEL_MIN": MERGE_LABEL_MIN,
                     "conjuncts": "cos>=0.90 AND labels_compatible AND "
                                  "countries_share (all imported verbatim)"},
            "gates_downstream": {"MATCH_THRESHOLD": MATCH_THRESHOLD,
                                 "ANCHOR_THRESHOLD": ANCHOR_THRESHOLD,
                                 "used_t": "INTACT (production) in ALL arms"},
            "frozen_nights_15": frozen_nights,
            "extra_labelled_nights": extra_labelled,
            "replay_snapshots": replay_snaps,
            "snapshot_inventory": inventory[-16:],
            "loader_equivalence": loader_check,
            "fidelity_graph_rows": fidelity_rows,
            "fidelity_singlenight_downstream": singlenight_fidelity,
            "per_night": per_night,
            "feed_log": feed_log,
            "super_cluster_geometry": geometry,
            "downstream": downstream,
            "families": fams_all,
            "judge_payloads": judge_payloads,
            "total_seconds": round(time.monotonic() - t_start, 1),
        }
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out = OUT_DIR / f"{STEM}.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False,
                                  default=str), encoding="utf-8")
        print(f"[out] {out} ({out.stat().st_size} bytes) — run --phase judge next")
        return 0
    finally:
        await conn.close()


# ------------------------------------------------------------------ judge phase
async def phase_judge(args: argparse.Namespace) -> int:
    key = os.environ.get("DEEPSEEK_API_KEY")
    if not key:
        raise SystemExit("DEEPSEEK_API_KEY required for --phase judge")
    out = OUT_DIR / f"{STEM}.json"
    result = json.loads(out.read_text())
    judgments: list[dict[str, Any]] = []
    for p in result["judge_payloads"]:
        if not p.get("scorable"):
            judgments.append({"family": p["family_name"], "arm": p["arm"],
                              "scorable": False})
            continue
        j = await ds_judge_landing(p, key)
        rec = {"family": p["family_name"], "arm": p["arm"], "scorable": True,
               "destination_label": p["destination"]["label"],
               "destination_identity": p["destination"]["identity_key"],
               "self_founded": p["destination"]["self_founded"],
               "family_native": p["destination"]["family_native"],
               "coverage": p.get("coverage"),
               **j}
        judgments.append(rec)
        print(f"[judge] {p['family_name']:44s} {p['arm']:6s} -> "
              f"{j['verdict'].upper():12s} grounded={j['grounded']} "
              f"dest='{p['destination']['label']}'")
        print(f"        reason: {j['reason']}")
    result["landing_judgments"] = judgments
    result["verdict"] = verdict_block(result)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False,
                              default=str), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2, ensure_ascii=False))
    print(f"[out] {out}")
    return 0


# ------------------------------------------------------------------ verdict
def verdict_block(res: dict[str, Any]) -> dict[str, Any]:
    kills: list[str] = []
    notes: list[str] = []
    frozen = set(res["frozen_nights_15"])
    nights = [r for r in res["per_night"] if r["snapshot"] in frozen]
    # G-K2
    k2_pass = [r["snapshot"] for r in nights
               if r["primary_shared_country"]["K2_pass"]]
    k2_fail = [(r["snapshot"], r["primary_shared_country"]["share"])
               for r in nights if not r["primary_shared_country"]["K2_pass"]]
    g_k2 = len(k2_pass) >= G_K2_MIN_NIGHTS
    if not g_k2:
        kills.append(f"G-K2: only {len(k2_pass)}/15 frozen nights pass "
                     f"(need >= {G_K2_MIN_NIGHTS}); fails: "
                     + ", ".join(f"{s[:10]} {100*v:.2f}%" for s, v in k2_fail))
    # G-784
    flagged = sum(r["country_span_signature"]["flagged_784_class"] for r in nights)
    g_784 = flagged == 0
    if not g_784:
        kills.append(f"G-784: {flagged} country-span+label-clash component(s) "
                     f"across the 15 frozen nights (bar: 0)")
    # G-FALSE
    false_fail = [(r["snapshot"], r["false_side"]["admitted_full_rule"])
                  for r in nights if r["false_side"]["admitted_full_rule"] > 0]
    g_false = not false_fail
    if not g_false:
        kills.append(f"G-FALSE: false pairs admitted on "
                     + ", ".join(f"{s[:10]} ({n})" for s, n in false_fail))
    label_only_fail = [(r["snapshot"], r["false_side"]["admitted_label_only"])
                       for r in nights
                       if r["false_side"]["admitted_label_only"] > 0]
    if label_only_fail:
        notes.append("label-only rule admitted false pairs on "
                     + ", ".join(f"{s[:10]} ({n})" for s, n in label_only_fail))
    notes.append("G-FALSE is structurally 0 for the +country rule (the FALSE "
                 "construction is countries_disjoint by definition); the "
                 "informative number is the label-only admission, also 0")
    # extra nights (outside the frozen gate, honesty disclosure)
    extra = [r for r in res["per_night"] if r["snapshot"] not in frozen]
    extra_k2_fail = [(r["snapshot"], r["primary_shared_country"]["share"])
                     for r in extra if not r["primary_shared_country"]["K2_pass"]]
    extra_784 = sum(r["country_span_signature"]["flagged_784_class"] for r in extra)
    if extra_k2_fail:
        notes.append("OUTSIDE the frozen gate: K2 fails on extra labelled "
                     "night(s) " + ", ".join(f"{s[:10]} {100*v:.2f}%"
                                             for s, v in extra_k2_fail))
    if extra_784:
        notes.append(f"OUTSIDE the frozen gate: {extra_784} 784-class "
                     f"component(s) on extra labelled nights")
    # G-LANDING
    judgments = res.get("landing_judgments", [])
    scorable_fams = sorted({j["family"] for j in judgments if j.get("scorable")})
    n_scorable = len(scorable_fams)
    bar = math.ceil(2 * n_scorable / 3)
    correct = {"cons_a": 0, "cons_b": 0}
    for j in judgments:
        if j.get("scorable") and j.get("counts_as_correct"):
            correct[j["arm"]] += 1
    g_landing = (correct["cons_b"] >= bar
                 and correct["cons_b"] > correct["cons_a"])
    if not g_landing:
        kills.append(f"G-LANDING: arm B correct on {correct['cons_b']}/"
                     f"{n_scorable} (bar >= {bar}) and arm A on "
                     f"{correct['cons_a']} (must be strictly fewer)")
    # G-COVERAGE
    raw_f = {f["family"]: f for f in res["downstream"]["raw"]["families"]}
    b_f = {f["family"]: f for f in res["downstream"]["cons_b"]["families"]}
    cov_fail = [nm for nm in scorable_fams
                if b_f[nm]["story_coverage_signals"]
                < raw_f[nm]["story_coverage_signals"]]
    g_cov = not cov_fail
    if not g_cov:
        kills.append(f"G-COVERAGE: arm B coverage < RAW on: "
                     + ", ".join(cov_fail))
    # G-FOUNDING
    fg = res["downstream"]["cons_b"]["founding_gate"]
    g_found = fg["blocked_rate_of_decidable"] <= G_FOUNDING_MAX_RATE
    if not g_found:
        kills.append(f"G-FOUNDING: label-blocked foundings = "
                     f"{100*fg['blocked_rate_of_decidable']:.1f}% of decidable "
                     f"landing picks (bar <= {100*G_FOUNDING_MAX_RATE:.0f}%)")
    verdict = "KILL" if kills else "GO"
    return {
        "verdict": verdict,
        "kills_fired": kills, "notes": notes,
        "G_K2": {"pass": g_k2, "passing_nights": len(k2_pass),
                 "failing": k2_fail},
        "G_784": {"pass": g_784, "flagged_total": flagged},
        "G_FALSE": {"pass": g_false,
                    "label_only_failures": label_only_fail},
        "G_LANDING": {"pass": g_landing, "scorable": n_scorable, "bar": bar,
                      "arm_a_correct": correct["cons_a"],
                      "arm_b_correct": correct["cons_b"]},
        "G_COVERAGE": {"pass": g_cov, "failing_families": cov_fail,
                       "raw": {k: raw_f[k]["story_coverage_signals"]
                               for k in scorable_fams},
                       "cons_b": {k: b_f[k]["story_coverage_signals"]
                                  for k in scorable_fams}},
        "G_FOUNDING": {"pass": g_found, **{k: v for k, v in fg.items()
                                           if k != "blocked_examples"}},
        "landing_table": [
            {k: j.get(k) for k in ("family", "arm", "destination_label",
                                   "verdict", "grounded", "counts_as_correct",
                                   "self_founded", "family_native", "coverage")}
            for j in judgments if j.get("scorable")],
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="7th pre-registered identity gate: consolidation + "
                    "shared-country with identity-landing (read-only).")
    ap.add_argument("--phase", choices=("measure", "judge"), required=True)
    ap.add_argument("--tau", type=float, default=MERGE_THRESHOLD)
    ap.add_argument("--false-pairs", type=int, default=FALSE_PAIR_TARGET)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--validate", action="store_true")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    fn = phase_measure if args.phase == "measure" else phase_judge
    raise SystemExit(asyncio.run(fn(args)))


if __name__ == "__main__":
    main()
