#!/usr/bin/env python3
"""Eighth pre-registered identity gate: the LANDING JOIN PREDICATE.

Pre-registration (FROZEN before this file was written, approved by Pedro):
  docs/superpowers/specs/2026-08-03-landing-predicate-preregistration.md
Direct successor of the 7th gate (`2026-08-03-consolidation-landing.md`), whose
KILL on G-FOUNDING left the diagnosis: the landing PRINCIPLE works (2/6 -> 6/6)
and the PREDICATE `labels_compatible` is the defect (~50% false block on
known-same-story pairs + structural self-block outside ASCII).

READ-ONLY. Extends the 7th harness (`measure_consolidation_landing.py`, left
byte-untouched) exactly as that one extended run 5's: orchestration is copied,
every rule/constant/replay mechanism is IMPORTED. The consolidation graph rule
is INHERITED INTACT from the 7th (cos>=0.90 AND labels_compatible AND
countries_share — "se hereda intacto", so its G-K2/G-784/G-FALSE rows double
as fidelity anchors); P-NUEVO replaces the predicate at the LANDING JOIN only,
which is the layer the 7th diagnosed.

P-NUEVO (frozen here, calibrated BEFORE the measured run — G-PREDICADO part 1)
------------------------------------------------------------------------------
    P8(a, b):
      na, nb = unicode_norm(a), unicode_norm(b)   # NFKC + casefold + NFKD,
      if not na or not nb: False                  #   combining marks stripped —
      if na == nb: True                           #   NEVER the ASCII [^a-z0-9]
      Sa, Sb = subject tokens of na, nb           # >=3 alpha chars, one
      if not Sa or not Sb: False                  #   trailing-'s' fold,
      shared = Sa & Sb                            #   minus G_STATIC
      if not shared: False                        # "exige solape"
      ra, rb = Sa - Sb, Sb - Sa
      if not ra or not rb: True                   # containment
      if |shared| >= 3: min(|ra|, |rb|) <= 1      # bounded residual
      if |shared| == 2: max(|ra|, |rb|) <= 1
      else: False

G_STATIC = `measure_evidence_fingerprint._GENERIC_TOKENS` (imported verbatim —
the same frozen multilingual generic set the FALSE construction uses) UNION a
frozen TEMPLATE_EXTRA set (the war-template frame words run 5 §7 measured
bridging three wars: conflict/escalation/tension/...).

TWO pre-run predicate decisions, made while calibrating (allowed; gates frozen):
  * NIGHT-DF PLAYS NO ROLE. The spec sketched "genéricos del df-alto de la
    noche" for the containment relaxation; measured on the program's own pairs,
    df-forgiveness re-admits the three-war fusion the moment big war families
    push russia/ukraine/iran into the top decile — the exact mirror of run 5
    §11.1, where df-VETO killed Berlin Pride. Both directions of night-df are
    self-inflating; the generic set is STATIC and frozen instead.
  * STRICT containment is replaced by containment-with-bounded-residual,
    because the spec's own must-pass anchor ("US Citizen Released by Iran" <->
    "American Released from Iran") carries one non-generic leftover token on
    EACH side ({citizen} vs {american}) — strict containment cannot pass it.
    The residual bound is direction-aware: >=3 shared tokens tolerate one
    leftover on the smaller side (cross-language pairs live here); exactly 2
    shared tolerate one leftover TOTAL per side (kills Kyiv<->Poland, which
    shares {russian, missile} and contradicts in the residuals).

ARMS (landing, against TODAY's pool, replay = the 7th's exact 12 nights)
  raw      production on raw clusters                  (baseline)
  cons_a   production on consolidated super-clusters   (arm A)
  b_p7     found-biased join gated on labels_compatible (7th's arm B, verbatim
           semantics — comparability)
  b_p8     found-biased join gated on P-NUEVO           (THE VERDICT SUBJECT)
  b_court  P-NUEVO; on gray band (predicate fails AND pick-cos >= 0.93) a
           court-style DeepSeek entailment decides join/found — with a call
           counter; if projected nightly volume > 150 calls the arm is
           reported INVIABLE-AT-VOLUME however well it measures (refutation-3
           lesson), and an absolute in-run budget caps spend (beyond budget the
           gray pick resolves as FOUND and is counted as skipped).

FROZEN GATES (any fail => overall KILL):
  G-K2         >= 14/15 inherited nights <= 2%       (consolidation, inherited)
  G-784        0 across the 15 nights                (inherited)
  G-LANDING    b_p8 correct on >= ceil(2/3*scorables) families AND strictly
               more than arm A. NEW self-founded rule (closes the 7th's
               quasi-tautology): a self-founded landing counts ONLY if no
               correct identity EXISTED in the pool that night — decided by a
               quote-gated pool-check judge over candidate pool identities
               (top-10 by centroid cos to the family's main super at hydration
               UNION pool topics whose label is P8-compatible with the family's
               modal label), plus human spot-check.
  G-FOUNDING   b_p8 foundings <= 15% of decidable landing picks (the bar that
               killed the 7th; proved its value, does not move)
  G-COVERAGE   b_p8 family coverage >= RAW, per scorable family (secondary)
  G-FALSE      0/1200 per night (inherited rule; structural note stands)
  G-PREDICADO  (1) the 10-pair calibration table passes 10/10 BEFORE the
               measured run; (2) false-block < 20% on the program's known
               same-story pairs = decidable picks at cos >= 0.99 (the 7th §5
               argued the as-of-now replay makes those same-story by
               construction), vs labels_compatible's measured rate reported
               beside it from b_p7.

FIDELITY (STOP rule): identical to the 7th — run 5's graph rows on all 15
frozen nights + the 07-28 variant rows + fastpath + false construction +
loader equivalence must reproduce EXACTLY; the single-night downstream RAW
agreement must be within 2pp of run 5's 93.81%. Any miss aborts before a gate
is read.

Usage (M1 mlvenv; read-only; Pedro on the machine => taskpolicy -b ALWAYS):
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend && taskpolicy -b nice -n 19 \
      /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.measure_landing_predicate --phase calibrate
  ... then --phase measure, then --phase judge
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import math
import os
import re
import time
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

import numpy as np

# --- production: rules imported, never re-implemented --------------------------
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

# --- replay machinery (used_t harness) -----------------------------------------
from scripts.simulate_used_t_removal import (  # noqa: E402
    _unit_rows,
    candidate_pairs,
    hydrate_as_of,
    process_snapshot_sim,
    topic_of_cluster,
    validate_against_prod,
)

# --- run 5's consolidation machinery -------------------------------------------
from scripts.measure_cluster_consolidation import (  # noqa: E402
    FALSE_PAIR_TARGET,
    K2_MAX_SHARE,
    build_super_clusters,
    consolidation_graph,
    country_span_signature,
    family_components,
    sample_false_pairs,
    verify_false_construction,
    verify_fastpath,
)

# --- the frozen generic vocabulary, shared with the FALSE construction ---------
from scripts.measure_evidence_fingerprint import _GENERIC_TOKENS  # noqa: E402

# --- the 7th gate's harness: everything reusable is IMPORTED -------------------
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
from scripts.label_court import _reason_quotes_a_receipt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
STEM = "2026-08-03-landing-predicate"
RUN5_JSON = OUT_DIR / "2026-07-30-cluster-consolidation.json"
GATE7_JSON = OUT_DIR / "2026-08-03-consolidation-landing.json"
PREREG_PATH = ("docs/superpowers/specs/"
               "2026-08-03-landing-predicate-preregistration.md")
COURT_CACHE = Path(os.environ.get(
    "ATLAS_P8_COURT_CACHE",
    str(REPO_ROOT / "backend" / ".p8_court_cache.json")))

# ---- frozen gate constants (from the pre-registration; never moved) -----------
G_K2_MIN_NIGHTS = 14
G_PRED_MAX_FALSE_BLOCK = 0.20     # on decidable picks at cos >= 0.99
KNOWN_SAME_STORY_COS = 0.99
COURT_GRAY_COS = 0.93
COURT_NIGHTLY_CAP = 150           # refutation-3 viability line
COURT_BUDGET_TOTAL = 1500         # absolute in-run spend cap; beyond => found

# ---- P-NUEVO: frozen normalizer + vocabulary ----------------------------------
TEMPLATE_EXTRA = frozenset({
    # the war-template frame words run 5 §7 measured bridging three wars,
    # plus their nearest frame siblings. STATIC by design (see docstring).
    "conflict", "conflicts", "escalation", "escalations", "tension",
    "tensions", "situation", "situations", "incident", "incidents",
    "development", "developments", "coverage", "breaking",
})
G_STATIC = frozenset(_GENERIC_TOKENS) | TEMPLATE_EXTRA

_TOKEN_RE = re.compile(r"[^\W\d_]{3,}", re.UNICODE)
_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)


def unicode_norm(s: str | None) -> str:
    """NFKC + casefold + NFKD with combining marks stripped — the Unicode
    normalizer the pre-registration demands (never `[^a-z0-9]+`). 'Irán' and
    'iran' meet; a Cyrillic label survives as itself instead of vanishing."""
    if not s:
        return ""
    x = unicodedata.normalize("NFKC", s).casefold()
    x = unicodedata.normalize("NFKD", x)
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = _PUNCT_RE.sub(" ", x)
    return re.sub(r"\s+", " ", x).strip()


def _fold(tok: str) -> str:
    """One trailing-'s' plural fold (len >= 4): attacks->attack,
    strikes->strike. Deliberately minimal; known misses (launches->launche)
    are frozen and stated rather than patched per-case."""
    return tok[:-1] if len(tok) >= 4 and tok.endswith("s") else tok


def p8_subject_tokens(norm: str) -> frozenset[str]:
    return frozenset(_fold(t) for t in _TOKEN_RE.findall(norm)
                     if t not in G_STATIC and _fold(t) not in G_STATIC)


def p8_compatible(a: str | None, b: str | None) -> bool:
    """P-NUEVO. See module docstring for the frozen definition + rationale."""
    na, nb = unicode_norm(a), unicode_norm(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    sa, sb = p8_subject_tokens(na), p8_subject_tokens(nb)
    if not sa or not sb:
        return False
    shared = sa & sb
    if not shared:
        return False
    ra, rb = sa - sb, sb - sa
    if not ra or not rb:
        return True
    if len(shared) >= 3:
        return min(len(ra), len(rb)) <= 1
    if len(shared) == 2:
        return max(len(ra), len(rb)) <= 1
    return False


# ---- G-PREDICADO part 1: the 10-pair calibration table, WRITTEN FIRST ---------
# Two anchors fixed by the pre-registration; the other eight are REAL pairs
# from the program's artifacts (7th gate §5 blocked examples, run 5 §7/§6a
# wrong landings), covering re-wording, cross-language, the Cyrillic self-pair,
# and negatives that must fail. Frozen before the measured run.
CALIBRATION_PAIRS: list[dict[str, Any]] = [
    {"n": 1, "cat": "anchor · re-wording (spec)", "expect": True,
     "a": "US Citizen Released by Iran", "b": "American Released from Iran"},
    {"n": 2, "cat": "anchor · different event (spec)", "expect": False,
     "a": "Berlin Pride Van Attack", "b": "Drone Attacks on Moscow"},
    {"n": 3, "cat": "re-wording (7th §5 block)", "expect": True,
     "a": "Shania Twain Missed Wedding", "b": "Shania Missed Taylor's Wedding"},
    {"n": 4, "cat": "re-wording (7th §5 block)", "expect": True,
     "a": "Soviet Flag Sold at Auction", "b": "Soviet Moon Flag Auction"},
    {"n": 5, "cat": "containment (7th identity_ok false-negative)", "expect": True,
     "a": "Iran Accuses Ukraine of Caspian Attack",
     "b": "Iran Ukraine Caspian Attack"},
    {"n": 6, "cat": "cross-language (7th §5 block)", "expect": True,
     "a": "Trump Naval Blockade Iran",
     "b": "Trump Restablece Bloqueo Naval a Irán"},
    {"n": 7, "cat": "Cyrillic self-pair (7th §5 witness)", "expect": True,
     "a": "Галявиев Женился в Колонии", "b": "Галявиев Женился в Колонии"},
    {"n": 8, "cat": "NEGATIVE · three-war template (run 5 §7 bridge)",
     "expect": False,
     "a": "Russia-Ukraine Conflict Escalation", "b": "US-Iran Conflict Escalation"},
    {"n": 9, "cat": "NEGATIVE · same-actors different place (7th arm-A wrong)",
     "expect": False,
     "a": "Russian Missile Strikes on Kyiv", "b": "Russian Missile in Poland"},
    {"n": 10, "cat": "NEGATIVE · same-country different event (run 5 §6a wrong)",
     "expect": False,
     "a": "Iran Attacks UAE Tankers", "b": "Iran Ukraine Caspian Attack"},
]


def run_calibration() -> dict[str, Any]:
    rows = []
    ok = True
    for p in CALIBRATION_PAIRS:
        got = p8_compatible(p["a"], p["b"])
        rows.append({**p, "got": got, "pass": got == p["expect"]})
        ok &= got == p["expect"]
        # the OLD predicate on the same pair, for the artifact's contrast column
        rows[-1]["labels_compatible_old"] = labels_compatible(p["a"], p["b"])
    return {"pairs": rows, "all_pass": ok,
            "passed": sum(1 for r in rows if r["pass"]), "of": len(rows)}


# ------------------------------------------------------------------ the arm
def process_snapshot_arm_pred(topics: list[Topic],
                              snap_clusters: list[dict[str, Any]],
                              snap: str, cfg: LifecycleConfig,
                              events: list[dict[str, Any]],
                              predicate: Callable[[str | None, str | None], bool],
                              court: Callable[[dict, Topic, float], bool] | None = None,
                              ) -> dict[str, Any]:
    """COPY of the 7th gate's `process_snapshot_arm_b` with the join predicate
    PARAMETERIZED (### PREDICATE below) and an optional gray-band court hook
    (### COURT). predicate=labels_compatible reproduces the 7th's arm B;
    predicate=p8_compatible is the verdict subject. Everything else — gates,
    order, attach, founding, state advance — is production's."""
    if not snap_clusters:
        return {"snapshot": snap, "n_clusters": 0}
    cvecs = np.stack([np.asarray(c["centroid"], dtype=np.float64)
                      for c in snap_clusters])
    tcent = (np.stack([t.centroid for t in topics]) if topics
             else np.zeros((0, cvecs.shape[1])))
    tanch = (np.stack([t.anchor_centroid for t in topics]) if topics
             else np.zeros((0, cvecs.shape[1])))
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
    decidable_cos99 = 0
    blocked_cos99 = 0
    court_consulted = 0
    court_joined = 0
    blocked_detail: list[dict[str, Any]] = []
    for k in range(s_arr.size):
        s = float(s_arr[k]); ci = int(ci_arr[k]); ti = int(ti_arr[k])
        if ci in used_c or ci in blocked:
            continue
        if ti in used_t:
            continue
        clabel = snap_clusters[ci].get("label")
        tlabel = topic_labels_start[ti]
        if clabel:
            # ### PREDICATE — the ONE parameterized decision (7th: labels_compatible)
            compatible = predicate(clabel, tlabel)
            if s >= KNOWN_SAME_STORY_COS:
                decidable_cos99 += 1
            if not compatible and court is not None and s >= COURT_GRAY_COS:
                # ### COURT — gray band: predicate fails but geometry is
                # near-anchor; a court-style entailment gets the last word.
                court_consulted += 1
                if court(snap_clusters[ci], topics[ti], s):
                    compatible = True
                    court_joined += 1
            if compatible:
                joins_decidable += 1
            else:
                blocked.add(ci)
                if s >= KNOWN_SAME_STORY_COS:
                    blocked_cos99 += 1
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
        if ci not in used_c:
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

    return {
        "snapshot": snap, "n_clusters": len(snap_clusters),
        "attached": len(used_c), "founded": founded,
        "joins_decidable": joins_decidable,
        "joins_undecidable_super": joins_undecidable,
        "label_blocked_foundings": len(blocked),
        "blocked_empty_target": blocked_empty_target,
        "decidable_cos99": decidable_cos99,
        "blocked_cos99": blocked_cos99,
        "court_consulted": court_consulted,
        "court_joined": court_joined,
        "blocked_detail": blocked_detail,
        **diag,
    }


# ------------------------------------------------------------------ court arm
class CourtJudge:
    """Gray-band entailment: SUPER (label + member-cluster labels) vs TARGET
    (label + what it actually holds). Synchronous DeepSeek temp-0, quote-gated
    on the TARGET material (court GB3 pattern, imported checker), disk-cached
    keyed (super_label, target_identity) so re-runs are deterministic, hard
    budget beyond which a gray pick resolves as FOUND (counted)."""

    def __init__(self, key: str, member_labels: dict[int, list[str]],
                 clusters_by_id: dict[int, dict],
                 super_to_orig: dict[int, list[int]], budget: int):
        self.key = key
        self.member_labels = member_labels          # prod topic id -> labels
        self.clusters_by_id = clusters_by_id
        self.super_to_orig = super_to_orig
        self.budget = budget
        self.calls = 0
        self.errors = 0
        self.skipped_budget = 0
        self.cache: dict[str, dict] = {}
        if COURT_CACHE.exists():
            try:
                self.cache = json.loads(COURT_CACHE.read_text())
            except Exception:
                self.cache = {}
        self.log: list[dict[str, Any]] = []

    def _target_material(self, t: Topic) -> list[str]:
        if t.id is not None:
            labs = self.member_labels.get(int(t.id), [])
        else:
            orig = [cid for m in t.members
                    for cid in self.super_to_orig.get(int(m["cluster_id"]),
                                                      [int(m["cluster_id"])])]
            labs = [self.clusters_by_id[c]["label"] for c in orig
                    if c in self.clusters_by_id and self.clusters_by_id[c]["label"]]
        out = [t.label] + labs if t.label else labs
        return list(dict.fromkeys(x for x in out if x))[:10]

    def _super_material(self, c: dict[str, Any]) -> list[str]:
        orig = self.super_to_orig.get(int(c["id"]), [int(c["id"])])
        labs = [self.clusters_by_id[x]["label"] for x in orig
                if x in self.clusters_by_id and self.clusters_by_id[x]["label"]]
        return list(dict.fromkeys([c["label"]] + labs))[:8]

    def __call__(self, c: dict[str, Any], t: Topic, cos: float) -> bool:
        key = f"{c['label']} :: {t.identity_key}"
        if key in self.cache:
            return bool(self.cache[key].get("join"))
        if self.calls >= self.budget:
            self.skipped_budget += 1
            return False
        tgt = self._target_material(t)
        sup = self._super_material(c)
        prompt = (
            "You are a strict news-identity court. A cluster of same-event "
            "fragments wants to JOIN an existing topic identity.\n\n"
            f"FRAGMENTS (label + member labels):\n"
            + "\n".join(f"- {x}" for x in sup)
            + "\n\nTARGET identity (label + what it actually holds):\n"
            + "\n".join(f"T{i+1}: {x}" for i, x in enumerate(tgt))
            + "\n\nAre these the SAME specific real-world event (same "
            "occurrence, place, actors — not merely the same war, country or "
            "theme)? Your reason MUST include a short VERBATIM quoted excerpt "
            "copied exactly from the TARGET lines above. Reply ONLY JSON:\n"
            '{"verdict": "same" | "different", "reason": "<short, with a '
            'verbatim quoted TARGET excerpt>"}')
        import httpx
        self.calls += 1
        verdict, reason, grounded = "different", "", False
        try:
            r = httpx.post(_DS_URL, timeout=45.0,
                           headers={"Authorization": f"Bearer {self.key}"},
                           json={"model": "deepseek-chat", "temperature": 0,
                                 "messages": [{"role": "user", "content": prompt}]})
            r.raise_for_status()
            ans = r.json()["choices"][0]["message"]["content"]
            body = ans.strip().strip("`")
            body = body[body.find("{"):] if "{" in body else body
            try:
                obj = json.loads(body)
                verdict = str(obj.get("verdict", "")).strip().lower()
                reason = str(obj.get("reason", "")).strip()
            except (json.JSONDecodeError, ValueError):
                low = ans.lower()
                verdict = "same" if "\"same\"" in low or "'same'" in low else "different"
                reason = ans[:200]
            grounded = _reason_quotes_a_receipt(reason, [{"headline": x} for x in tgt])
        except Exception as e:  # noqa: BLE001 — network failure => found, counted
            self.errors += 1
            reason = f"court error: {e}"
        join = verdict == "same" and grounded
        rec = {"super": c["label"], "target": t.identity_key,
               "target_label": t.label, "cos": round(cos, 4),
               "verdict": verdict, "grounded": grounded, "join": join,
               "reason": reason[:300]}
        self.cache[key] = rec
        self.log.append(rec)
        if self.calls % 25 == 0:
            COURT_CACHE.write_text(json.dumps(self.cache, ensure_ascii=False))
            print(f"    [court] {self.calls} calls, {sum(1 for x in self.log if x['join'])} joins",
                  flush=True)
        return join

    def flush(self) -> None:
        COURT_CACHE.write_text(json.dumps(self.cache, ensure_ascii=False))


# ------------------------------------------------------------------ pool check
async def pool_topic_receipts(conn, topic_id: int,
                              exclude_ids: set[int]) -> list[str]:
    rows = await conn.fetch(
        "SELECT ec.label, ec.n_signals, ec.snapshot_at, ec.sample_signal_ids "
        "FROM dynamic_topic_members dtm "
        "JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id "
        "WHERE dtm.dynamic_topic_id = $1 "
        "  AND NOT (dtm.emergent_cluster_id = ANY($2::bigint[])) "
        "ORDER BY dtm.snapshot_at DESC LIMIT 10", topic_id, sorted(exclude_ids))
    lines = [f"{r['label']} ({int(r['n_signals'] or 0)} signals, "
             f"{r['snapshot_at'].date()})" for r in rows if r["label"]]
    sids = [int(x) for r in rows for x in (r["sample_signal_ids"] or [])][:200]
    if sids:
        heads = await conn.fetch(
            "SELECT DISTINCT ON (headline) headline FROM signals_v2 "
            "WHERE id = ANY($1::bigint[]) AND headline IS NOT NULL "
            "AND length(headline) >= 12 LIMIT 6", sids)
        lines += [r["headline"] for r in heads]
    return lines[:14]


def pool_check_prompt(payload: dict[str, Any]) -> str:
    fam = payload["family"]
    cands = payload["candidates"]
    blocks = []
    for i, c in enumerate(cands):
        rec = "\n".join(f"   - {x}" for x in c["receipts"]) or "   (no receipts)"
        blocks.append(f"CANDIDATE {i+1}: \"{c['label']}\" ({c['identity']})\n{rec}")
    fam_lines = "\n".join(f"- {x}" for x in fam["labels"][:8])
    fam_heads = "\n".join(f"- {x}" for x in fam["headlines"][:6]) or "- (none)"
    return (
        "A clustering engine FOUNDED a brand-new identity for a known event. "
        "The pre-registered rule: the founding only counts as a correct "
        "landing if NO correct identity for this event already existed in the "
        "topic pool that night.\n\n"
        f"KNOWN EVENT family: {fam['name']}\nfragment labels:\n{fam_lines}\n"
        f"sample headlines:\n{fam_heads}\n\n"
        "EXISTING pool identities that night (the closest candidates by "
        "geometry and by label):\n\n" + "\n\n".join(blocks) + "\n\n"
        "QUESTION: Does ANY candidate above already describe THE SAME specific "
        "real-world event as the KNOWN EVENT (same occurrence, place, actors "
        "— not merely the same war/country/theme)? If YES, your reason MUST "
        "include a short VERBATIM quoted excerpt copied exactly from that "
        "candidate's receipt lines. Reply ONLY JSON:\n"
        '{"exists": "YES" | "NO", "which": "<candidate number or none>", '
        '"reason": "<short; if YES, with a verbatim quoted candidate excerpt>"}')


async def ds_pool_check(payload: dict[str, Any], key: str) -> dict[str, Any]:
    import httpx
    haystack = [{"headline": x} for c in payload["candidates"]
                for x in c["receipts"]]
    prompt = pool_check_prompt(payload)
    attempts = []
    for attempt in range(2):
        body = {"model": "deepseek-chat", "temperature": 0,
                "messages": [{"role": "user", "content": prompt if attempt == 0
                              else prompt + "\n\nREMINDER: a YES answer failed "
                              "the quote check; copy a verbatim excerpt (>= 6 "
                              "chars, in quotes) from the candidate receipts."}]}
        async with httpx.AsyncClient() as c:
            r = await c.post(_DS_URL, json=body,
                             headers={"Authorization": f"Bearer {key}"},
                             timeout=60.0)
            r.raise_for_status()
            ans = r.json()["choices"][0]["message"]["content"]
        b = ans.strip().strip("`")
        b = b[b.find("{"):] if "{" in b else b
        exists, which, reason = "", "", ""
        try:
            obj = json.loads(b)
            exists = str(obj.get("exists", "")).strip().upper()
            which = str(obj.get("which", "")).strip()
            reason = str(obj.get("reason", "")).strip()
        except (json.JSONDecodeError, ValueError):
            exists = "YES" if "yes" in ans.lower()[:200] else "NO"
            reason = ans[:300]
        grounded = _reason_quotes_a_receipt(reason, haystack)
        attempts.append({"raw": ans, "exists": exists, "which": which,
                         "reason": reason, "grounded": grounded})
        if exists != "YES" or grounded:
            break
    final = attempts[-1]
    # STRICT direction: an ungrounded YES still voids the founding credit
    # (treated as "a correct identity may have existed") — flagged for the
    # human spot-check rather than silently trusted either way.
    correct_existed = final["exists"] == "YES"
    return {"attempts": attempts, "exists": final["exists"],
            "which": final["which"], "reason": final["reason"],
            "grounded": final["grounded"],
            "correct_identity_existed": correct_existed,
            "counts_for_gate": not correct_existed}


# ------------------------------------------------------------------ measure
async def phase_measure(args: argparse.Namespace) -> int:
    import asyncpg
    db = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not db:
        raise SystemExit("DATABASE_URL required")
    ds_key = os.environ.get("DEEPSEEK_API_KEY")
    if not ds_key:
        raise SystemExit("DEEPSEEK_API_KEY required (b_court arm)")

    calib = run_calibration()
    print(f"[calib] {calib['passed']}/{calib['of']} pairs pass")
    if not calib["all_pass"]:
        raise SystemExit("[STOP] G-PREDICADO part 1: calibration table failed — "
                         "fix the predicate BEFORE the measured run")

    run5 = json.loads(RUN5_JSON.read_text())
    frozen_nights: list[str] = run5["labelled_snapshots"]
    replay_snaps: list[str] = run5["replay_snapshots"]
    run5_per_snap = {r["snapshot"]: r for r in run5["per_snapshot"]}
    fams_all: list[dict[str, Any]] = run5["families"]
    fams_landing = [f for f in fams_all if f.get("scope") == "snapshot"]
    assert len(fams_landing) == 6

    conn = await asyncpg.connect(db)
    await conn.execute("SET default_transaction_read_only = on")
    t_start = time.monotonic()
    cutoff_now = dt.datetime.now(dt.timezone.utc)
    try:
        mindful_gate("load")
        clusters = await load_clusters_chunked(conn)
        print(f"[load] {len(clusters)} clusters")
        clusters_by_id = {c["id"]: c for c in clusters}
        snaps: dict[str, list[dict]] = defaultdict(list)
        for c in clusters:
            snaps[c["snapshot_at"]].append(c)
        loader_check = await verify_loader_equivalence(
            conn, clusters, "2026-07-28T00:00:00+00:00")
        if not loader_check["exact"]:
            raise SystemExit("[STOP] loader equivalence failed")
        missing = [s for s in frozen_nights if s not in snaps]
        if missing:
            raise SystemExit(f"[STOP] frozen nights pruned: {missing}")

        # ---- graph fidelity + inherited gates (rule unchanged from 7th) ----
        fidelity_broken = False
        per_night: list[dict[str, Any]] = []
        newest = frozen_nights[-1]
        for snap in frozen_nights:
            mindful_gate(f"graph {snap[:10]}")
            cs = snaps[snap]
            df_tokens: Counter = Counter()
            n_labels = 0
            for c in cs:
                if c["label"]:
                    n_labels += 1
                    df_tokens.update(_subject_tokens(c["label"]))
            Vn = _unit_rows(np.stack([c["centroid"] for c in cs]).astype(np.float64))
            g = consolidation_graph(cs, tau=args.tau, label_mode="engine",
                                    require_shared_country=True, V=Vn)
            cand = (g["_cand_ii"], g["_cand_jj"])
            fp = sample_false_pairs(cs, np.random.default_rng(args.seed),
                                    args.false_pairs)
            fpc = verify_false_construction(cs, fp)
            fs = false_side_with_country(cs, fp, Vn, tau=args.tau)
            sig = country_span_signature(cs, g["components"], df_tokens, n_labels)
            exp = run5_per_snap[snap]["variants"]["supp engine-label + shared country"]
            exact = (g["edges"] == exp["edges"] and g["largest"] == exp["largest"]
                     and g["share"] == exp["share"]
                     and sig["flagged_784_class"]
                     == exp["country_span_signature"]["flagged_784_class"]
                     and fs["admitted_label_only"] == exp["false_side"]["admitted"]
                     and fpc["exact"])
            if not exact:
                fidelity_broken = True
                print(f"[FIDELITY MISMATCH] {snap[:19]}")
            rec = {"snapshot": snap, "clusters": len(cs),
                   "edges": g["edges"], "largest": g["largest"],
                   "share": g["share"], "K2_pass": g["share"] <= K2_MAX_SHARE,
                   "flagged_784": sig["flagged_784_class"],
                   "false_full": fs["admitted_full_rule"],
                   "false_label_only": fs["admitted_label_only"],
                   "fidelity_exact": exact}
            if snap == newest:
                rec["fastpath"] = verify_fastpath(
                    [c["label"] for c in cs], cand[0], cand[1],
                    np.random.default_rng(args.seed))
                fidelity_broken |= not rec["fastpath"]["exact"]
                rec["families_components"] = [
                    family_components(f, cs, g["components"]) for f in fams_landing]
            per_night.append(rec)
            print(f"  [gate] {snap[:19]} edges={g['edges']:4d} "
                  f"largest={g['largest']:3d} ({100*g['share']:.2f}%) "
                  f"K2={'P' if rec['K2_pass'] else 'F'} 784={rec['flagged_784']} "
                  f"fid={'OK' if exact else 'MISMATCH'}", flush=True)
        if fidelity_broken:
            raise SystemExit("[STOP] graph fidelity failed to reproduce run 5")
        print("[fidelity] graph rows reproduce run 5 exactly on all 15 nights")

        # ---- single-night downstream fidelity ------------------------------
        mindful_gate("singlenight")
        cfg = LifecycleConfig()
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

        # ---- feeds (inherited consolidation rule) --------------------------
        feeds: dict[str, tuple[list[dict], dict[int, list[int]]]] = {}
        id_base = 0
        all_s2o: dict[int, list[int]] = {}
        for snap in replay_snaps:
            cs = snaps[snap]
            g = consolidation_graph(cs, tau=args.tau, label_mode="engine",
                                    require_shared_country=True)
            feed, mapping = build_super_clusters(cs, g["components"], id_base)
            id_base += len(cs) + 1
            apply_largest_member_label(feed, mapping, clusters_by_id)
            feeds[snap] = (feed, mapping)
            all_s2o.update(mapping)

        # ---- court material: prod topic -> member cluster labels -----------
        ml_rows = await conn.fetch(
            "SELECT dtm.dynamic_topic_id AS tid, ec.label "
            "FROM dynamic_topic_members dtm "
            "JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id "
            "WHERE ec.label IS NOT NULL ORDER BY dtm.snapshot_at DESC")
        member_labels: dict[int, list[str]] = defaultdict(list)
        for r in ml_rows:
            if len(member_labels[int(r["tid"])]) < 12:
                member_labels[int(r["tid"])].append(r["label"])

        window_ids: dict[str, set[int]] = {}
        for f in fams_landing:
            wf = next((x for x in fams_all
                       if x["name"] == f'{f["name"]} [window]'), None)
            window_ids[f["name"]] = set(f["cluster_ids"]) | set(
                wf["cluster_ids"] if wf else [])

        # family headline blocks (for judge + pool-check prompts)
        fam_blocks: dict[str, dict[str, Any]] = {}
        for f in fams_landing:
            sids = [s for cid in f["cluster_ids"]
                    for s in clusters_by_id[cid]["sample_signal_ids"]]
            heads = [r["headline"] for r in await conn.fetch(
                "SELECT DISTINCT ON (headline) headline FROM signals_v2 "
                "WHERE id = ANY($1::bigint[]) AND headline IS NOT NULL "
                "AND length(headline) >= 12 LIMIT 8", sids[:400])]
            fam_blocks[f["name"]] = {"name": f["name"], "labels": f["labels"],
                                     "headlines": heads,
                                     "countries": f.get("countries", [])}

        # family "main super" on 07-28 (for pool-candidate geometry)
        main_super: dict[str, np.ndarray] = {}
        feed28, map28 = feeds[newest]
        for f in fams_landing:
            fam_set = set(f["cluster_ids"])
            best, best_w = None, -1
            for sc in feed28:
                w = sum(clusters_by_id[c]["n_signals"]
                        for c in map28.get(sc["id"], [sc["id"]]) if c in fam_set)
                if w > best_w:
                    best, best_w = sc, w
            v = np.asarray(best["centroid"], dtype=np.float64)
            main_super[f["name"]] = v / max(float(np.linalg.norm(v)), 1e-12)

        # ---- the five arms --------------------------------------------------
        arms_spec = [
            ("raw", None, None),
            ("cons_a", None, None),
            ("b_p7", labels_compatible, None),
            ("b_p8", p8_compatible, None),
            ("b_court", p8_compatible, "court"),
        ]
        downstream: dict[str, Any] = {}
        judge_payloads: list[dict[str, Any]] = []
        pool_candidates: dict[str, list[dict[str, Any]]] = {}
        court_stats: dict[str, Any] = {}
        for arm, pred, courtflag in arms_spec:
            mindful_gate(f"arm {arm}")
            topics, hmeta, _ = await hydrate_as_of(conn, clusters_by_id, cutoff_now)
            if arm == "raw":
                # pool snapshot for the self-founded rule (identical hydration
                # across arms — captured once, BEFORE any replay attach)
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
                    # label route: P8-compatible pool labels (cap 6 extra)
                    fam_modal = Counter(
                        clusters_by_id[c]["label"] for c in
                        next(x for x in fams_landing if x["name"] == fname)["cluster_ids"]
                        if clusters_by_id[c]["label"]).most_common(1)[0][0]
                    seen_ids = {p["identity"] for p in pool_candidates[fname]}
                    extra = 0
                    for k2, (pid, ident, lab) in enumerate(pool_labels):
                        if extra >= 6:
                            break
                        if ident in seen_ids or not lab:
                            continue
                        if p8_compatible(fam_modal, lab):
                            pool_candidates[fname].append(
                                {"prod_id": pid, "identity": ident, "label": lab,
                                 "cos": round(float(P[k2] @ v), 4), "via": "p8-label"})
                            extra += 1
                del P
            court = None
            if courtflag:
                court = CourtJudge(ds_key, member_labels, clusters_by_id,
                                   all_s2o, COURT_BUDGET_TOTAL)
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
                if pred is None:
                    res = process_snapshot_sim(topics, feed, snap, cfg,
                                               allow_multi=False, events=events)
                else:
                    res = process_snapshot_arm_pred(topics, feed, snap, cfg,
                                                    events, pred, court)
                per_snap.append({**res, "fed_clusters": len(feed)})
                print(f"  [{arm:8s}] {snap[:19]} fed={len(feed):5d} "
                      f"att={res.get('attached', 0):5d} "
                      f"fnd={res.get('founded', 0):5d} "
                      f"blk={res.get('label_blocked_foundings', '-')} "
                      f"court={res.get('court_consulted', '-')}", flush=True)
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
            if pred is not None:
                dec = sum(s.get("joins_decidable", 0) for s in per_snap)
                blk = sum(s.get("label_blocked_foundings", 0) for s in per_snap)
                c99 = sum(s.get("decidable_cos99", 0) for s in per_snap)
                b99 = sum(s.get("blocked_cos99", 0) for s in per_snap)
                entry["founding_gate"] = {
                    "decidable_landing_picks": dec + blk,
                    "joins_decidable": dec,
                    "label_blocked_foundings": blk,
                    "blocked_rate_of_decidable": round(blk / max(dec + blk, 1), 4),
                    "blocked_empty_target": sum(
                        s.get("blocked_empty_target", 0) for s in per_snap),
                    "joins_undecidable_super_null_label": sum(
                        s.get("joins_undecidable_super", 0) for s in per_snap),
                    "known_same_story_cos99": {
                        "decidable": c99 + b99, "blocked": b99,
                        "false_block_rate": round(b99 / max(c99 + b99, 1), 4)},
                    "blocked_examples": [d for s in per_snap
                                         for d in s.get("blocked_detail", [])][:60],
                }
            if courtflag and court is not None:
                court.flush()
                labelled_nights = sum(
                    1 for s in entry["per_snapshot"]
                    if s.get("joins_decidable", 0) + s.get("label_blocked_foundings", 0) > 0)
                gray = sum(s.get("court_consulted", 0) for s in entry["per_snapshot"])
                court_stats = {
                    "gray_band_picks": gray, "calls_made": court.calls,
                    "cache_hits": gray - court.calls - court.skipped_budget,
                    "skipped_over_budget": court.skipped_budget,
                    "errors": court.errors,
                    "joins_granted": sum(
                        s.get("court_joined", 0) for s in entry["per_snapshot"]),
                    "labelled_nights": labelled_nights,
                    "projected_calls_per_night": round(gray / max(labelled_nights, 1), 1),
                    "nightly_cap": COURT_NIGHTLY_CAP,
                    "viable_at_volume": (gray / max(labelled_nights, 1))
                    <= COURT_NIGHTLY_CAP,
                    "sample_log": court.log[:40],
                }
                entry["court"] = court_stats
            if arm == "raw" and args.validate:
                entry["validation_last_night_vs_prod"] = await validate_against_prod(
                    conn, owner_orig, topics, replay_snaps)
            # ---- judge payloads for THIS arm, then drop topics (memory) ----
            if arm != "raw":
                for f in fams_landing:
                    sc = next(x for x in fam_scores if x["family"] == f["name"])
                    ti = sc["largest_topic_index"]
                    if ti is None:
                        judge_payloads.append({"family_name": f["name"], "arm": arm,
                                               "family": fam_blocks[f["name"]],
                                               "destination": None, "scorable": False})
                        continue
                    dest = await destination_receipts(
                        conn, topics, ti, super_to_orig,
                        window_ids[f["name"]], clusters_by_id)
                    judge_payloads.append({
                        "family_name": f["name"], "arm": arm,
                        "family": fam_blocks[f["name"]], "destination": dest,
                        "scorable": True,
                        "coverage": sc["story_coverage_signals"],
                        "identity_ok_lexical_proxy": sc["identity_ok"]})
            downstream[arm] = entry
            del topics, owner_super, owner_orig, events

        # ---- pool-check payloads for self-founded landings ------------------
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

        result = {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "harness": "backend/scripts/measure_landing_predicate.py",
            "preregistration": PREREG_PATH,
            "read_only": True,
            "hydrate_cutoff_now": cutoff_now.isoformat(),
            "predicate": {
                "name": "P-nuevo (unicode norm + subject-token containment, "
                        "bounded residual)",
                "G_STATIC": "measure_evidence_fingerprint._GENERIC_TOKENS "
                            "(imported) UNION TEMPLATE_EXTRA",
                "TEMPLATE_EXTRA": sorted(TEMPLATE_EXTRA),
                "night_df_role": "NONE (pre-run decision; see harness docstring)",
            },
            "calibration": calib,
            "consolidation_rule": "INHERITED from 7th: cos>=0.90 AND "
                                  "labels_compatible AND countries_share",
            "gates_downstream": {"MATCH_THRESHOLD": MATCH_THRESHOLD,
                                 "ANCHOR_THRESHOLD": ANCHOR_THRESHOLD,
                                 "used_t": "INTACT in ALL arms"},
            "frozen_nights_15": frozen_nights,
            "replay_snapshots": replay_snaps,
            "loader_equivalence": loader_check,
            "fidelity_singlenight": {k: v for k, v in val_sn.items()
                                     if k != "examples"},
            "per_night": per_night,
            "downstream": downstream,
            "court_stats": court_stats,
            "pool_candidates": pool_candidates,
            "judge_payloads": judge_payloads,
            "pool_check_payloads": pool_checks,
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
            "family_native": p["destination"]["family_native"],
            "coverage": p.get("coverage"), **j})
        print(f"[judge] {p['family_name']:42s} {p['arm']:8s} -> "
              f"{j['verdict'].upper():10s} grounded={j['grounded']} "
              f"dest='{p['destination']['label']}'")
        print(f"        {j['reason'][:220]}")
    pool_checks: list[dict[str, Any]] = []
    for p in result["pool_check_payloads"]:
        r = await ds_pool_check(p, key)
        pool_checks.append({"family": p["family_name"], "arm": p["arm"], **r})
        print(f"[pool ] {p['family_name']:42s} {p['arm']:8s} -> "
              f"exists={r['exists']} which={r['which']} grounded={r['grounded']}")
        print(f"        {r['reason'][:220]}")
    result["landing_judgments"] = judgments
    result["pool_checks"] = pool_checks
    result["verdict"] = verdict_block(result)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False,
                              default=str), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2, ensure_ascii=False))
    return 0


# ------------------------------------------------------------------ verdict
def verdict_block(res: dict[str, Any]) -> dict[str, Any]:
    kills: list[str] = []
    notes: list[str] = []
    nights = res["per_night"]
    k2_pass = sum(1 for r in nights if r["K2_pass"])
    if k2_pass < G_K2_MIN_NIGHTS:
        kills.append(f"G-K2: {k2_pass}/15 (need >= {G_K2_MIN_NIGHTS})")
    flagged = sum(r["flagged_784"] for r in nights)
    if flagged:
        kills.append(f"G-784: {flagged} (bar 0)")
    ffail = [(r["snapshot"], r["false_full"]) for r in nights if r["false_full"]]
    if ffail:
        kills.append(f"G-FALSE: {ffail}")
    notes.append("G-FALSE structural for the +country rule; label-only also 0")
    # G-PREDICADO
    calib = res["calibration"]
    fg8 = res["downstream"]["b_p8"]["founding_gate"]
    fg7 = res["downstream"]["b_p7"]["founding_gate"]
    fb8 = fg8["known_same_story_cos99"]["false_block_rate"]
    fb7 = fg7["known_same_story_cos99"]["false_block_rate"]
    g_pred = calib["all_pass"] and fb8 < G_PRED_MAX_FALSE_BLOCK
    if not g_pred:
        kills.append(f"G-PREDICADO: calibration {calib['passed']}/10, "
                     f"false-block@cos99 {100*fb8:.1f}% (bar < 20%; old "
                     f"predicate {100*fb7:.1f}%)")
    # G-FOUNDING (verdict subject = b_p8)
    g_found = fg8["blocked_rate_of_decidable"] <= G_FOUNDING_MAX_RATE
    if not g_found:
        kills.append(f"G-FOUNDING: b_p8 blocked "
                     f"{100*fg8['blocked_rate_of_decidable']:.1f}% of decidable "
                     f"(bar <= {100*G_FOUNDING_MAX_RATE:.0f}%)")
    # G-LANDING with the self-founded rule
    judgments = res.get("landing_judgments", [])
    pool = {(p["family"], p["arm"]): p for p in res.get("pool_checks", [])}
    per_arm_correct: dict[str, int] = defaultdict(int)
    table = []
    scorable_fams = sorted({j["family"] for j in judgments if j.get("scorable")})
    for j in judgments:
        if not j.get("scorable"):
            continue
        counts = bool(j.get("counts_as_correct"))
        pc = pool.get((j["family"], j["arm"]))
        if counts and j.get("self_founded") and pc is not None:
            counts = bool(pc["counts_for_gate"])
        j2 = {**{k: j.get(k) for k in ("family", "arm", "destination_label",
                                       "verdict", "grounded", "self_founded",
                                       "coverage")},
              "pool_check": (None if pc is None else
                             {"exists": pc["exists"], "which": pc["which"],
                              "grounded": pc["grounded"]}),
              "counts_for_gate": counts}
        table.append(j2)
        if counts:
            per_arm_correct[j["arm"]] += 1
    n_scorable = len(scorable_fams)
    bar = math.ceil(2 * n_scorable / 3)
    a_ok = per_arm_correct.get("cons_a", 0)
    p8_ok = per_arm_correct.get("b_p8", 0)
    g_landing = p8_ok >= bar and p8_ok > a_ok
    if not g_landing:
        kills.append(f"G-LANDING: b_p8 {p8_ok}/{n_scorable} (bar >= {bar}) "
                     f"vs arm A {a_ok} (must be strictly fewer)")
    # G-COVERAGE
    raw_f = {f["family"]: f for f in res["downstream"]["raw"]["families"]}
    p8_f = {f["family"]: f for f in res["downstream"]["b_p8"]["families"]}
    cov_fail = [nm for nm in scorable_fams
                if p8_f[nm]["story_coverage_signals"]
                < raw_f[nm]["story_coverage_signals"]]
    if cov_fail:
        kills.append(f"G-COVERAGE: b_p8 < RAW on {cov_fail}")
    # court viability (report, not a gate on b_p8)
    cs = res.get("court_stats") or {}
    if cs and not cs.get("viable_at_volume", True):
        notes.append(f"b_court INVIABLE-AT-VOLUME: {cs['projected_calls_per_night']}"
                     f" projected calls/night > {COURT_NIGHTLY_CAP}")
    return {
        "verdict": "KILL" if kills else "GO",
        "kills_fired": kills, "notes": notes,
        "G_K2": {"pass": k2_pass >= G_K2_MIN_NIGHTS, "passing_nights": k2_pass},
        "G_784": {"pass": flagged == 0, "flagged_total": flagged},
        "G_FALSE": {"pass": not ffail},
        "G_PREDICADO": {"pass": g_pred, "calibration": f"{calib['passed']}/10",
                        "false_block_cos99_p8": fb8,
                        "false_block_cos99_p7_old": fb7},
        "G_FOUNDING": {"pass": g_found,
                       **{k: v for k, v in fg8.items() if k != "blocked_examples"},
                       "b_p7_rate_for_contrast": fg7["blocked_rate_of_decidable"]},
        "G_LANDING": {"pass": g_landing, "scorable": n_scorable, "bar": bar,
                      "correct_for_gate": dict(per_arm_correct)},
        "G_COVERAGE": {"pass": not cov_fail, "failing": cov_fail},
        "court": cs and {k: cs[k] for k in
                         ("gray_band_picks", "calls_made", "joins_granted",
                          "projected_calls_per_night", "viable_at_volume")},
        "founding_rates": {a: res["downstream"][a].get("founding_gate", {})
                           .get("blocked_rate_of_decidable")
                           for a in ("b_p7", "b_p8", "b_court")},
        "landing_table": table,
    }


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="8th pre-registered identity gate: the landing join "
                    "predicate (read-only).")
    ap.add_argument("--phase", choices=("calibrate", "measure", "judge"),
                    required=True)
    ap.add_argument("--tau", type=float, default=MERGE_THRESHOLD)
    ap.add_argument("--false-pairs", type=int, default=FALSE_PAIR_TARGET)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--validate", action="store_true")
    return ap.parse_args()


def phase_calibrate(_args: argparse.Namespace) -> int:
    calib = run_calibration()
    for r in calib["pairs"]:
        print(f"  {r['n']:2d} [{'PASS' if r['pass'] else 'FAIL'}] "
              f"expect={'compat' if r['expect'] else 'incompat'} "
              f"got={'compat' if r['got'] else 'incompat'} "
              f"old_pred={'compat' if r['labels_compatible_old'] else 'incompat'} "
              f"| {r['cat']}\n      '{r['a']}'  ~  '{r['b']}'")
    print(f"[calib] {calib['passed']}/{calib['of']} "
          f"{'ALL PASS' if calib['all_pass'] else 'FAILED'}")
    return 0 if calib["all_pass"] else 1


def main() -> None:
    args = parse_args()
    if args.phase == "calibrate":
        raise SystemExit(phase_calibrate(args))
    fn = phase_measure if args.phase == "measure" else phase_judge
    raise SystemExit(asyncio.run(fn(args)))


if __name__ == "__main__":
    main()
