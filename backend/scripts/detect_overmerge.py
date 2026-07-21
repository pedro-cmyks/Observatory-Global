"""M4 — over-merge blob-topic detector (the merge-sprint residual).

The 2026-07-20 merge sprint drove label-court failure 47.9% -> 24.3% by collapsing
duplicate identities, but audit of the 926 relabels showed ~26% got VAGUE UMBRELLA
labels ("Diverse Local Incidents Across Regions", "Mixed Local News: Floods, Drones,
and Housing", "Multiple Deadly Incidents Across Peru and Ukraine"). These are
OVER-MERGES — a topic fusing 2+ distinct stories — and they slip past every guard:

  - the label court passes them (a vague label trivially entails a diverse set);
  - flag_junk_topics passes them (each member is a real news item, not feed-dump);
  - the M2 radial floor (audit_topic_blackholes) passes them (the centroid falls
    BETWEEN the sub-clusters, so few members read "below floor").

The signal that catches them: MEMBERSHIP MULTIMODALITY. Run 2-means over a topic's
member embeddings; a topic whose members split into two WELL-SEPARATED sub-clusters
of SUBSTANTIAL size is a fusion. The false-positive trap — a legit MEGA-STORY
(Ukraine War: frontline + diplomacy + sanctions + refugees) also splits — is
handled by three signals (see `app/services/overmerge.py`): the gap magnitude vs
intra-cluster spread (a real fusion has a WIDE gap), whether the sub-clusters share
actors (one story shares countries/entities), and, for borderline cases, a DeepSeek
"one story or two?" judge. Precision-first: when unsure, KEEP.

DATA ACCESS mirrors `audit_topic_blackholes.py` (member embeddings via topic_members
JOIN signal_embeddings, engine_version v1-compat = the serving default, quarantined
rows excluded). REVERSIBILITY mirrors `flag_junk_topics.py` (demote active ->
candidate, NEVER delete; a split-back next nightly resurrects the sub-stories). No
silent filtering: every demote prints a loud per-topic log with the two sub-cluster
headlines + the reason, and a run ledger records exactly what moved.

Usage:
  python -m scripts.detect_overmerge                    # audit, read-only (Step 1)
  python -m scripts.detect_overmerge --judge            # + DeepSeek borderline judge
  python -m scripts.detect_overmerge --write            # demote (guarded; later step)
  python -m scripts.detect_overmerge --revert RUN_ID    # undo one run

The audit is READ-ONLY. --write is implemented but GATED (nightly + heavy-lock
guard) and is NOT part of the Step-1 audit-only deliverable.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import html
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

try:  # module-run from backend/ (pytest pythonpath=.) or repo root
    from app.services.overmerge import (
        BORDERLINE, DEMOTE, KEEP, OverMergeParams, apply_judge_verdict,
        country_dominant_overlap, country_multimodality, decide, is_over_merge,
        normalize_rows, parse_split_judge_response, partition, split_judge_user,
        SPLIT_JUDGE_SYSTEM,
    )
except ImportError:  # pragma: no cover
    from backend.app.services.overmerge import (
        BORDERLINE, DEMOTE, KEEP, OverMergeParams, apply_judge_verdict,
        country_dominant_overlap, country_multimodality, decide, is_over_merge,
        normalize_rows, parse_split_judge_response, partition, split_judge_user,
        SPLIT_JUDGE_SYSTEM,
    )

# ---------------------------------------------------------------- constants
DEFAULT_SEED = 42
DURABLE_ENGINE = "v1-compat"     # the serving default; survives ETL re-projection
TOPIC_CHUNK = 60                 # topics per member fetch (bounded memory + timeout)
REPS_PER_SIDE = 6                # representative headlines kept per sub-cluster
REASON_PREFIX = "overmerge-v1"
ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "docs" / "research" / "overmerge"
LEDGER_DIR = ARTIFACT_DIR
HEAVY_LOCK_DIR = os.environ.get("ATLAS_HEAVY_LOCK_DIR", "/tmp/atlas-heavy-job.lock")

# The Natalia-gap lane: a SEPARATE, embedding-free over-merge signal for old
# black-holes the 2-means path is blind to (their >7d members' embeddings are
# pruned at retention -> below min_members -> skipped). A topic qualifies for this
# lane ONLY when it is embedding-unevaluable (< min_members embedded members) AND
# court-failed AND cross-country-multimodal. Own kill-switch so it can be disabled
# independently of the embedding lane.
COUNTRY_FALLBACK_ENABLED = os.environ.get(
    "ATLAS_OVERMERGE_COUNTRY_FALLBACK", "on").strip().lower() == "on"
LANE_EMBEDDING = "embedding"
LANE_COUNTRY = "country-fallback"

# The relabel-ledger vague-blob CROSS-REF set. The merge sprint's ledger is the
# ground-truth-ish population of relabels; these tokens flag the vague UMBRELLA
# labels a fusion tends to acquire. Deliberately a COARSE proxy — the whole point
# of the detector is to be MORE precise than the keyword (it must spare "Libyan
# Attorney General Orders Detention of Multiple Officials", one story with
# "multiple" in it). The audit reports the detector-vs-keyword agreement, never
# uses the keyword to decide.
RELABEL_LEDGER = (Path(__file__).resolve().parents[2] / "docs" / "research"
                  / "label-court" / "2026-07-20-relabel-ledger.jsonl")
VAGUE_BLOB_TOKENS = (
    "diverse", "mixed ", "multiple ", "roundup", "round-up", "various",
    "several ", "assorted", "miscellaneous", "incidents across", "news roundup",
    "local news", "local incidents", "and related stories", "and other",
    "across regions", "unrelated", "news cluster", "global incidents",
    "news updates", "multiple events",
)


# ---------------------------------------------------------------- SQL
_TOPICS_SQL = """
SELECT dt.id, dt.label, dt.category, dt.agg_n_signals, dt.label_status
FROM dynamic_topics dt
WHERE dt.state = 'active'
  AND COALESCE(dt.is_umbrella, false) = false
  AND COALESCE(dt.is_junk, false) = false
  AND dt.centroid_vec IS NOT NULL
ORDER BY dt.id
"""

_MEMBERS_SQL = """
SELECT (split_part(tm.topic_id, '-', 3))::int AS tid,
       tm.signal_id,
       se.vec::text AS vec,
       s.country_code,
       s.persons
FROM topic_members tm
JOIN signal_embeddings se ON se.signal_id = tm.signal_id
JOIN signals_v2 s ON s.id = tm.signal_id
WHERE tm.topic_id = ANY($1::text[])
  AND tm.role = 'evidence'
  AND tm.engine_version = $2 {quarantine_filter}
"""

# The Natalia-gap lane's fetch: ALL v1-compat evidence members' country + persons,
# with NO signal_embeddings JOIN (the whole point — these members have no
# embeddings). Used only for the small fallback-eligible set (embedding-unevaluable
# AND court-failed), so it stays bounded.
_ALL_MEMBERS_SQL = """
SELECT (split_part(tm.topic_id, '-', 3))::int AS tid,
       tm.signal_id,
       s.country_code,
       s.persons
FROM topic_members tm
JOIN signals_v2 s ON s.id = tm.signal_id
WHERE tm.topic_id = ANY($1::text[])
  AND tm.role = 'evidence'
  AND tm.engine_version = $2 {quarantine_filter}
"""

_HEADLINES_SQL = """
SELECT s.id, s.headline, s.source_lang, s.source_name, s.country_code
FROM signals_v2 s WHERE s.id = ANY($1::bigint[])
"""

_QUARANTINE_COL_SQL = """
SELECT count(*) FROM information_schema.columns
WHERE table_name = 'topic_members' AND column_name = 'quarantined'
"""


def _members_sql(has_qcol: bool) -> str:
    filt = "AND tm.quarantined IS NOT TRUE" if has_qcol else ""
    return _MEMBERS_SQL.format(quarantine_filter=filt)


def _all_members_sql(has_qcol: bool) -> str:
    filt = "AND tm.quarantined IS NOT TRUE" if has_qcol else ""
    return _ALL_MEMBERS_SQL.format(quarantine_filter=filt)


# ---------------------------------------------------------------- helpers
def _parse_vec(text: str) -> np.ndarray:
    # halfvec / real[] render as '[...]' or '{...}' (the build_unified idiom)
    return np.asarray(json.loads(text.replace("{", "[").replace("}", "]")),
                      dtype=np.float32)


def _chunks(seq: Sequence, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def _percentiles(values: Sequence[float], probs: Sequence[float]) -> dict[str, float]:
    if not values:
        return {}
    ordered = sorted(values)
    out = {}
    for p in probs:
        k = (len(ordered) - 1) * p
        lo, hi = math.floor(k), math.ceil(k)
        v = ordered[lo] if lo == hi else ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)
        out[f"p{int(p * 100)}"] = round(v, 4)
    return out


def _member_actors(country_code: Optional[str], persons) -> set[str]:
    """Actor set for one signal: subject country + NER persons, prefixed so a
    country code can never collide with a person token."""
    actors: set[str] = set()
    if country_code:
        actors.add(f"c:{country_code.strip().upper()}")
    if persons:
        for p in persons:
            if p and str(p).strip():
                actors.add(f"p:{str(p).strip().lower()}")
    return actors


def _rep_indices(matn: np.ndarray, labels: np.ndarray, side: int,
                 k: int = REPS_PER_SIDE) -> list[int]:
    """Indices (into the topic's member arrays) of the k members most central to
    a sub-cluster — the representatives shown in the loud log + fed to the judge."""
    idx = np.where(labels == side)[0]
    if idx.size == 0:
        return []
    centroid = matn[idx].mean(axis=0)
    centroid = centroid / max(float(np.linalg.norm(centroid)), 1e-9)
    sims = matn[idx] @ centroid
    order = idx[np.argsort(-sims)]
    return [int(i) for i in order[:k]]


def _nightly_running() -> bool:
    try:
        res = subprocess.run(["pgrep", "-f", "run-scoped-snapshot.sh"],
                             capture_output=True, text=True, timeout=10)
        return bool(res.stdout.strip())
    except Exception:
        return True  # cannot verify -> assume running (safe side)


def _heavy_lock_held() -> bool:
    # atomic-mkdir lock dir (scripts/heavy-job-lock.sh). Its presence = a heavy
    # job holds the mutex; do not contend from a write path.
    return os.path.isdir(HEAVY_LOCK_DIR)


def _load_vague_blob_ids() -> set[int]:
    ids: set[int] = set()
    if not RELABEL_LEDGER.exists():
        return ids
    for line in RELABEL_LEDGER.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        new = (r.get("new") or "").lower()
        if any(tok in new for tok in VAGUE_BLOB_TOKENS):
            tid = r.get("topic_id")
            if isinstance(tid, int):
                ids.add(tid)
    return ids


def run_id_for(seed: int, day: dt.date) -> str:
    return f"m4-{day.strftime('%Y%m%d')}-s{seed}"


async def _connect():
    import asyncpg
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(2)
    conn = await asyncpg.connect(url, timeout=30)
    await conn.execute("SET statement_timeout = '180s'")
    return conn


# ---------------------------------------------------------------- audit
async def run_audit(seed: int, params: OverMergeParams, artifact_path: Path,
                    do_judge: bool, limit: int = 0) -> dict:
    conn = await _connect()
    try:
        has_qcol = (await conn.fetchval(_QUARANTINE_COL_SQL)) > 0
        topics = await conn.fetch(_TOPICS_SQL)
        meta = {r["id"]: {"label": r["label"], "category": r["category"],
                          "agg_n_signals": r["agg_n_signals"],
                          "label_status": r["label_status"]} for r in topics}
        ids = list(meta.keys())
        if limit and limit > 0:
            ids = ids[:limit]
            meta = {i: meta[i] for i in ids}
            print(f"[--limit {limit}] scanning a bounded subset (read-only smoke)")
        print(f"population: {len(ids)} active non-umbrella non-junk topics "
              f"(quarantine col: {'present' if has_qcol else 'absent'})")
        vague_ids = _load_vague_blob_ids()
        print(f"relabel-ledger vague-blob cross-ref set: {len(vague_ids)} topic ids")

        msql = _members_sql(has_qcol)
        records: list[dict] = []          # one per scanned topic (with a verdict)
        reps_wanted: dict[int, list[int]] = {}   # topic -> signal_ids to headline
        scanned = 0
        for chunk in _chunks(ids, TOPIC_CHUNK):
            keys = [f"dynamic-topic-{i}" for i in chunk]
            rows = await conn.fetch(msql, keys, DURABLE_ENGINE)
            by_topic: dict[int, list] = {}
            for r in rows:
                by_topic.setdefault(r["tid"], []).append(r)
            for tid in chunk:
                mem = by_topic.get(tid, [])
                rec = _score_topic(tid, meta[tid], mem, params, seed)
                rec["lane"] = LANE_EMBEDDING
                records.append(rec)
                if rec["verdict"] in (DEMOTE, BORDERLINE):
                    reps_wanted[tid] = rec["rep_ids_a"] + rec["rep_ids_b"]
            scanned += len(chunk)
            print(f"  scored {scanned}/{len(ids)} topics…", end="\r", flush=True)
        print()

        # ---- Natalia-gap lane: embedding-free country multimodality -----------
        # The 2-means path above is BLIND to old black-holes (their >7d members'
        # embeddings are pruned -> below min_members -> the record is a KEEP
        # "too few embedded members"). Re-score those, but ONLY the court-FAILED
        # ones (the black-hole signature: court-failed + relabel-refused +
        # detector-blind), via country distribution — no embeddings needed.
        fallback_stats = await _run_country_fallback(
            conn, records, meta, params, has_qcol, reps_wanted)

        # headlines for demote + borderline receipts (bounded)
        want_ids: list[int] = []
        for sids in reps_wanted.values():
            want_ids.extend(sids)
        headlines: dict[int, dict] = {}
        for id_chunk in _chunks(list(dict.fromkeys(want_ids)), 500):
            for r in await conn.fetch(_HEADLINES_SQL, id_chunk):
                headlines[r["id"]] = {
                    "headline": html.unescape(r["headline"] or "")[:140],
                    "lang": r["source_lang"], "source": r["source_name"],
                    "country": r["country_code"]}

        # optional borderline judge (one DeepSeek call per borderline topic)
        judge_stats = {"called": 0, "one_story_keep": 0, "two_stories_demote": 0,
                       "unavailable_keep": 0}
        if do_judge:
            await _run_borderline_judge(records, headlines, judge_stats)

        artifact = _assemble_artifact(seed, params, records, headlines,
                                      vague_ids, has_qcol, judge_stats, do_judge,
                                      fallback_stats)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(json.dumps(artifact, indent=1))
        print(f"artifact -> {artifact_path}")
        _print_summary(artifact, records, headlines, params)
        return artifact
    finally:
        await conn.close()


def _score_topic(tid: int, meta: dict, mem: list, params: OverMergeParams,
                 seed: int) -> dict:
    """Pure-math scoring of one topic from its fetched member rows -> a verdict
    record. All decision logic lives in app/services/overmerge (tested)."""
    n = len(mem)
    base = {"topic_id": tid, "label": meta["label"], "category": meta["category"],
            "agg_n_signals": meta["agg_n_signals"], "n_members": n,
            "rep_ids_a": [], "rep_ids_b": [], "entity_overlap": None,
            "over_merge_raw": False}
    if n < 2:
        base.update(verdict=KEEP, reason="too few embedded members to split",
                    gap_ratio=None, balance=None, separation=None,
                    mean_silhouette=None)
        return base
    raw = np.vstack([_parse_vec(r["vec"]) for r in mem]).astype(np.float64)
    labels, stats = partition(raw, seed=seed)
    if stats is None:
        base.update(verdict=KEEP, reason="unpartitionable", gap_ratio=None,
                    balance=None, separation=None, mean_silhouette=None)
        return base
    # shared-actor overlap between the two sub-clusters
    entity_overlap: Optional[float] = None
    if stats.size_a and stats.size_b:
        actors_a: set[str] = set()
        actors_b: set[str] = set()
        for i, r in enumerate(mem):
            (actors_a if labels[i] == 0 else actors_b).update(
                _member_actors(r["country_code"], r["persons"]))
        if actors_a or actors_b:
            # country-dominant, NOT the combined-set Jaccard: the combined form
            # is person-swamped (a single-country story's halves share the one
            # country token but name different people -> diluted below the veto ->
            # wrongly demoted). See app/services/overmerge.country_dominant_overlap.
            entity_overlap = country_dominant_overlap(actors_a, actors_b)
    verdict, reason = decide(stats, entity_overlap, params)
    matn = normalize_rows(raw)   # same normalization partition used -> labels align
    rep_a = [int(mem[i]["signal_id"]) for i in _rep_indices(matn, labels, 0)]
    rep_b = [int(mem[i]["signal_id"]) for i in _rep_indices(matn, labels, 1)]
    base.update(
        verdict=verdict, reason=reason,
        gap_ratio=round(stats.gap_ratio, 4), balance=round(stats.balance, 4),
        separation=round(stats.separation, 4),
        mean_silhouette=round(stats.mean_silhouette, 4),
        intra_spread=round(stats.intra_spread, 4),
        size_a=stats.size_a, size_b=stats.size_b,
        entity_overlap=round(entity_overlap, 4) if entity_overlap is not None else None,
        over_merge_raw=is_over_merge(stats, params),
        rep_ids_a=rep_a, rep_ids_b=rep_b)
    return base


# ----------------------------------------- Natalia-gap country-fallback lane
async def _run_country_fallback(conn, records: list[dict], meta: dict,
                                params: OverMergeParams, has_qcol: bool,
                                reps_wanted: dict[int, list[int]]) -> dict:
    """SEPARATE embedding-free lane, via MEMBER COUNTRY MULTIMODALITY. Re-scores
    the court-failed topics the embedding 2-means lane KEPT, catching the fusions
    it is blind to. Mutates those KEEP records in place.

    MEASURED (2026-07-21, docs/research/recall-229): the spec's premise — old
    black-holes going *embedding-unevaluable* because their >7d embeddings are
    pruned — does NOT hold: topic_members(v1-compat) and signal_embeddings CO-PRUNE
    for active topics, so 0/518 active court-failed topics are large-yet-embedding-
    blind (dt-726 itself was 37 members, all embedded, absorbing FRESH cross-country
    drift). The real blind spot is that a fusion of 3+ distinct stories has NO clean
    BIMODAL split, so the 2-means gap_ratio stays narrow and `decide` KEEPS it —
    while the country distribution fans across countries with no dominant one
    (dt-371 'Heat Wave Europe' = IT healthcare + PL football + RU cyber; dt-2451 =
    NL shooting + US rape fugitive + MY fraud). So the eligibility is 'embedding
    lane KEPT + court-failed' (a superset of the spec's embedding-unevaluable case,
    which lands here as KEEP 'too few embedded').

    Precision-first gates before flagging (all conjunctive):
      1. embedding lane KEPT it   (the embedding lane already flagged demote/
         borderline otherwise — this is only for what it MISSED);
      2. court-failed             (label_status='failed' — the black-hole signature;
         a court-ENTAILED generic bucket like 'Violent Crimes and Incidents' is
         spared, its diverse-but-honest members entailed by its label);
      3. >= min_members located members with a country;
      4. cross-country-multimodal (>= tau_countries distinct, no dominant country);
      5. NO cross-country shared actors (a summit that genuinely spans borders
         shares its principals -> vetoed like the embedding mega-story guard).
    A survivor is flagged BORDERLINE, never a direct DEMOTE: the raw country signal
    hand-checks ~73-87% precise (single multi-country stories — a World Cup, one
    war theatre — are the FP mode), so the DeepSeek 'one story or two?' judge is the
    REQUIRED confirmer (it kills the World-Cup FPs -> one_story). Without --judge
    the candidate stays borderline and is NOT written.
    """
    if not COUNTRY_FALLBACK_ENABLED:
        print("[fallback] country-multimodality lane DISABLED "
              "(ATLAS_OVERMERGE_COUNTRY_FALLBACK=off)")
        return {"enabled": False, "eligible": 0, "scored": 0, "flagged": 0,
                "keep": 0, "reasons": {}}
    rec_by_id = {r["topic_id"]: r for r in records}
    eligible = [tid for tid, r in rec_by_id.items()
                if r["verdict"] == KEEP
                and str((meta[tid].get("label_status") or "")).strip().lower()
                == "failed"]
    print(f"[fallback] court-failed topics the embedding lane KEPT: {len(eligible)} "
          f"-> country-multimodality")
    if not eligible:
        return {"enabled": True, "eligible": 0, "scored": 0, "flagged": 0,
                "keep": 0, "reasons": {}}

    amsql = _all_members_sql(has_qcol)
    reasons: dict[str, int] = {}
    n_flagged = 0
    scored = 0
    for chunk in _chunks(eligible, TOPIC_CHUNK):
        keys = [f"dynamic-topic-{i}" for i in chunk]
        rows = await conn.fetch(amsql, keys, DURABLE_ENGINE)
        by_topic: dict[int, list] = {}
        for r in rows:
            by_topic.setdefault(r["tid"], []).append(r)
        for tid in chunk:
            rec = rec_by_id[tid]
            _apply_country_fallback(rec, by_topic.get(tid, []), params)
            scored += 1
            key = rec["reason"].split(":")[0].split("(")[0].strip()[:40]
            reasons[key] = reasons.get(key, 0) + 1
            if rec["verdict"] in (DEMOTE, BORDERLINE):
                reps_wanted[tid] = rec["rep_ids_a"] + rec["rep_ids_b"]
                n_flagged += 1
    print(f"[fallback] scored {scored}; country-multimodal BORDERLINE candidates "
          f"(judge confirms): {n_flagged}")
    return {"enabled": True, "eligible": len(eligible), "scored": scored,
            "flagged": n_flagged, "keep": scored - n_flagged, "reasons": reasons}


def _apply_country_fallback(rec: dict, all_mem: list,
                            params: OverMergeParams) -> None:
    """Country-multimodality verdict for one court-failed, embedding-KEPT topic.
    Mutates the record: sets lane, country_signal, verdict, reason, rep_ids and
    (when multimodal) the cross-country actor overlap. All decision math is the
    tested pure `country_multimodality` + `country_dominant_overlap`. A survivor is
    BORDERLINE (the judge confirms), never a direct DEMOTE — the raw country signal
    is only ~73-87% precise (single multi-country stories are the FP mode)."""
    from collections import Counter
    counts: Counter = Counter()
    for r in all_mem:
        cc = (r["country_code"] or "").strip().upper()
        if cc:
            counts[cc] += 1
    cm = country_multimodality(dict(counts), tau_countries=params.tau_countries,
                               tau_dominance=params.tau_dominance)
    rec["lane"] = LANE_COUNTRY
    rec["embedding_gap_ratio"] = rec.get("gap_ratio")  # keep the 2-means context
    rec["country_signal"] = {
        "distinct": cm.distinct,
        "dominant_share": round(cm.dominant_share, 4),
        "total_located": cm.total,
        "all_members": len(all_mem),
        "countries": dict(counts.most_common(10)),
    }
    # too few LOCATED members -> cannot honestly assess a cross-country fusion.
    if cm.total < params.min_members:
        rec["verdict"] = KEEP
        rec["reason"] = (f"country-lane KEEP: too few located members "
                         f"({cm.total} < {params.min_members})")
        return
    if not cm.is_multimodal:
        rec["verdict"] = KEEP
        rec["reason"] = (f"country-lane KEEP: not multimodal "
                         f"(distinct {cm.distinct}, dominant {cm.dominant_share:.2f})")
        return
    # multimodal: split top-country vs the rest, veto if they SHARE actors
    # (a cross-border single story — a summit — shares its principals).
    top_cc = counts.most_common(1)[0][0]
    actors_top: set[str] = set()
    actors_rest: set[str] = set()
    rep_a: list[int] = []
    rep_b: list[int] = []
    for r in all_mem:
        cc = (r["country_code"] or "").strip().upper()
        if not cc:
            continue
        acts = _member_actors(cc, r["persons"])
        if cc == top_cc:
            actors_top |= acts
            if len(rep_a) < REPS_PER_SIDE:
                rep_a.append(int(r["signal_id"]))
        else:
            actors_rest |= acts
            if len(rep_b) < REPS_PER_SIDE:
                rep_b.append(int(r["signal_id"]))
    # country_dominant_overlap MAX(country,person): the two groups are disjoint by
    # country (top vs rest) so this reduces to the shared-PERSON Jaccard — exactly
    # the cross-border-single-story guard (a summit's principals recur on both
    # sides). Empty/sparse persons -> 0.0 (no veto; the judge is the backstop).
    overlap = country_dominant_overlap(actors_top, actors_rest)
    rec["entity_overlap"] = round(overlap, 4)
    rec["rep_ids_a"] = rep_a
    rec["rep_ids_b"] = rep_b
    if overlap >= params.tau_overlap:
        rec["verdict"] = KEEP
        rec["reason"] = (f"country-lane KEEP: shared actors across countries "
                         f"(overlap {overlap:.2f} >= {params.tau_overlap:.2f}): "
                         f"one cross-border story")
        return
    rec["verdict"] = BORDERLINE
    rec["reason"] = (f"country-multimodal BORDERLINE (judge confirms): court-failed "
                     f"+ embedding-KEPT (gap {rec.get('gap_ratio')}) + cross-country "
                     f"(distinct {cm.distinct}, dominant {cm.dominant_share:.2f} < "
                     f"{params.tau_dominance:.2f}, actor-overlap {overlap:.2f})")


async def _run_borderline_judge(records: list[dict], headlines: dict[int, dict],
                                stats: dict) -> None:
    """One DeepSeek 'one story or two?' call per FLAGGED candidate — BOTH the
    borderline band AND the structural-demote band.

    The structural+country stage produces a CANDIDATE set; the judge is the
    precision gate. A candidate becomes a real demote ONLY on a positive
    'two_stories' confirmation; one_story or an unavailable/unparseable call KEEPS
    (precision-first — never demote a real story on the absence of a positive
    confirmation). Gating the demote band too is what catches the cross-country-
    SAME-story residual (a single global story split by outlet-country/language
    that the country veto misses because the outlet countries genuinely differ).
    Gated behind --judge."""
    import httpx
    try:
        from scripts.ensemble.model_clients import call_llm
    except ImportError:  # pragma: no cover
        from backend.scripts.ensemble.model_clients import call_llm
    candidates = [r for r in records if r["verdict"] in (BORDERLINE, DEMOTE)]
    if not candidates:
        return
    n_bl = sum(1 for r in candidates if r["verdict"] == BORDERLINE)
    n_dm = len(candidates) - n_bl
    print(f"[judge] {len(candidates)} flagged candidates -> DeepSeek confirm "
          f"({n_dm} structural-demote + {n_bl} borderline)…")
    async with httpx.AsyncClient(timeout=90.0) as client:
        for r in candidates:
            band = r["verdict"]            # remember which band it came from
            ha = [headlines[s]["headline"] for s in r["rep_ids_a"]
                  if s in headlines][:REPS_PER_SIDE]
            hb = [headlines[s]["headline"] for s in r["rep_ids_b"]
                  if s in headlines][:REPS_PER_SIDE]
            stats["called"] += 1
            try:
                out = await call_llm(
                    "deepseek", system=SPLIT_JUDGE_SYSTEM,
                    user=split_judge_user(r["label"] or "?", ha, hb),
                    client=client, max_tokens=200, temperature=0.0, json_mode=True)
                judge = parse_split_judge_response(out)
            except Exception as exc:
                print(f"[judge] call FAILED for dt-{r['topic_id']} ({exc!r}) — "
                      f"KEEP (precision-first)", file=sys.stderr)
                judge = None
            final, note = apply_judge_verdict(judge)
            r["verdict"] = final
            r["reason"] = f"{band} -> {note} ({r['reason']})"
            if judge is False:
                stats["two_stories_demote"] += 1
            elif judge is True:
                stats["one_story_keep"] += 1
            else:
                stats["unavailable_keep"] += 1


def _receipts(records: list[dict], headlines: dict[int, dict],
              verdict: str, limit: int = 40) -> list[dict]:
    out = []
    picked = [r for r in records if r["verdict"] == verdict]
    picked.sort(key=lambda r: -(r.get("gap_ratio") or 0.0))
    for r in picked[:limit]:
        def _hl(ids):
            return [{"signal_id": s, **headlines[s]} for s in ids if s in headlines][:3]
        out.append({
            "topic_id": r["topic_id"], "label": r["label"],
            "category": r["category"], "n_members": r["n_members"],
            "lane": r.get("lane"), "country_signal": r.get("country_signal"),
            "gap_ratio": r.get("gap_ratio"), "balance": r.get("balance"),
            "separation": r.get("separation"),
            "mean_silhouette": r.get("mean_silhouette"),
            "entity_overlap": r.get("entity_overlap"), "reason": r["reason"],
            "group_a": _hl(r["rep_ids_a"]), "group_b": _hl(r["rep_ids_b"])})
    return out


def _fallback_receipts(records: list[dict], headlines: dict[int, dict],
                       limit: int = 60) -> list[dict]:
    """Country-fallback flagged candidates (lane=country-fallback, DEMOTE or
    BORDERLINE) with their two country groups' headlines — the Measure/hand-check
    surface. Sorted by fewest-dominant (most clearly multimodal) first."""
    picked = [r for r in records if r.get("lane") == LANE_COUNTRY
              and r["verdict"] in (DEMOTE, BORDERLINE)]
    picked.sort(key=lambda r: (r.get("country_signal") or {}).get("dominant_share", 1.0))
    out = []
    for r in picked[:limit]:
        def _hl(ids):
            return [{"signal_id": s, **headlines[s]} for s in ids if s in headlines][:6]
        out.append({
            "topic_id": r["topic_id"], "label": r["label"],
            "category": r["category"], "verdict": r["verdict"],
            "n_embedded": r["n_members"], "country_signal": r.get("country_signal"),
            "entity_overlap": r.get("entity_overlap"), "reason": r["reason"],
            "top_country_group": _hl(r["rep_ids_a"]),
            "other_countries_group": _hl(r["rep_ids_b"])})
    return out


def _assemble_artifact(seed, params, records, headlines, vague_ids, has_qcol,
                       judge_stats, did_judge, fallback_stats) -> dict:
    eligible = [r for r in records if r["n_members"] >= params.min_members
                and r.get("gap_ratio") is not None]
    verdict_hist: dict[str, int] = {}
    keep_reasons: dict[str, int] = {}
    for r in records:
        verdict_hist[r["verdict"]] = verdict_hist.get(r["verdict"], 0) + 1
        if r["verdict"] == KEEP:
            key = r["reason"].split("(")[0].strip().split(":")[0][:40]
            keep_reasons[key] = keep_reasons.get(key, 0) + 1
    demotes = [r for r in records if r["verdict"] == DEMOTE]
    borderlines = [r for r in records if r["verdict"] == BORDERLINE]

    # cross-ref vs the relabel-ledger vague-blob keyword set (a coarse proxy)
    scanned_ids = {r["topic_id"] for r in records}
    vague_scanned = vague_ids & scanned_ids
    flagged_ids = {r["topic_id"] for r in demotes + borderlines}
    xref = {
        "vague_blob_in_ledger": len(vague_ids),
        "vague_blob_active_scanned": len(vague_scanned),
        "detector_flags_total": len(flagged_ids),
        "vague_blob_flagged": len(vague_scanned & flagged_ids),
        "vague_blob_kept_by_detector": len(vague_scanned - flagged_ids),
        "flagged_not_vague_labeled": len(flagged_ids - vague_ids),
    }
    return {
        "run_id": run_id_for(seed, dt.date.today()),
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "params": {"tau_sep": params.tau_sep, "tau_sep_low": params.tau_sep_low,
                   "tau_bal": params.tau_bal, "tau_overlap": params.tau_overlap,
                   "min_members": params.min_members,
                   "tau_countries": params.tau_countries,
                   "tau_dominance": params.tau_dominance,
                   "country_fallback_enabled": COUNTRY_FALLBACK_ENABLED,
                   "seed": seed, "engine": DURABLE_ENGINE, "judge_ran": did_judge},
        "population": {
            "topics": len(records), "eligible": len(eligible),
            "quarantine_col_present": has_qcol,
        },
        "verdicts": verdict_hist,
        "keep_reasons": keep_reasons,
        "over_merge_raw_count": sum(1 for r in records if r.get("over_merge_raw")),
        "distribution_eligible": {
            "gap_ratio": _percentiles([r["gap_ratio"] for r in eligible],
                                      [0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]),
            "balance": _percentiles([r["balance"] for r in eligible],
                                    [0.10, 0.50, 0.90]),
            "mean_silhouette": _percentiles([r["mean_silhouette"] for r in eligible],
                                            [0.10, 0.50, 0.90, 0.99]),
            "separation": _percentiles([r["separation"] for r in eligible],
                                       [0.10, 0.50, 0.90, 0.99]),
        },
        "ledger_xref": xref,
        "lane_counts": {
            "embedding_demote": sum(1 for r in demotes
                                    if r.get("lane") == LANE_EMBEDDING),
            "country_fallback_demote": sum(1 for r in demotes
                                           if r.get("lane") == LANE_COUNTRY),
            "embedding_borderline": sum(1 for r in borderlines
                                        if r.get("lane") == LANE_EMBEDDING),
            "country_fallback_borderline": sum(1 for r in borderlines
                                               if r.get("lane") == LANE_COUNTRY),
        },
        "country_fallback": {
            **(fallback_stats or {}),
            "receipts": _fallback_receipts(records, headlines),
        },
        "judge": judge_stats if did_judge else None,
        "demote_receipts": _receipts(records, headlines, DEMOTE),
        "borderline_receipts": _receipts(records, headlines, BORDERLINE),
        # full per-topic table (for --write + re-analysis); rep ids kept for the
        # loud demote log.
        "topics": [
            {k: v for k, v in r.items()} for r in records
        ],
    }


def _print_summary(artifact: dict, records: list, headlines: dict,
                   params: OverMergeParams) -> None:
    print(f"\nverdicts: {artifact['verdicts']}")
    print(f"raw over_merge (gap>=tau_sep AND balance>=tau_bal): "
          f"{artifact['over_merge_raw_count']}")
    print(f"keep reasons: {artifact['keep_reasons']}")
    print(f"gap_ratio distribution (eligible ≥{params.min_members} members): "
          f"{artifact['distribution_eligible']['gap_ratio']}")
    print(f"mean_silhouette distribution: "
          f"{artifact['distribution_eligible']['mean_silhouette']}")
    x = artifact["ledger_xref"]
    print(f"\nLEDGER CROSS-REF (vague-blob keyword proxy):")
    print(f"  vague-blob ids in ledger: {x['vague_blob_in_ledger']}  "
          f"active+scanned now: {x['vague_blob_active_scanned']}")
    print(f"  detector flags (demote+borderline): {x['detector_flags_total']}")
    print(f"  of the vague-blob scanned: FLAGGED {x['vague_blob_flagged']} · "
          f"KEPT {x['vague_blob_kept_by_detector']} "
          f"(kept = keyword false-positives the detector spares)")
    print(f"  detector flags NOT vague-labeled: {x['flagged_not_vague_labeled']} "
          f"(over-merges the sprint's relabel missed)")
    dem = artifact["demote_receipts"]
    print(f"\nDEMOTE candidates: {len(dem)} (top by gap_ratio)")
    for r in dem[:20]:
        print(f"  dt-{r['topic_id']:>5} gap={r['gap_ratio']} bal={r['balance']} "
              f"sil={r['mean_silhouette']} ovl={r['entity_overlap']} "
              f"n={r['n_members']} · {(r['label'] or '')[:46]}")
        a = r["group_a"][0]["headline"] if r["group_a"] else "(no headline)"
        b = r["group_b"][0]["headline"] if r["group_b"] else "(no headline)"
        print(f"        A: {a[:70]}")
        print(f"        B: {b[:70]}")
    print(f"\nBORDERLINE: {len(artifact['borderline_receipts'])}"
          + ("" if artifact["params"]["judge_ran"] else " (run --judge to resolve)"))

    # Natalia-gap country-multimodality lane (court-failed + embedding-KEPT)
    cf = artifact.get("country_fallback") or {}
    lc = artifact.get("lane_counts") or {}
    print(f"\nCOUNTRY-MULTIMODALITY LANE (court-failed topics the embedding lane KEPT):")
    if not cf.get("enabled", True):
        print("  DISABLED (ATLAS_OVERMERGE_COUNTRY_FALLBACK=off)")
    else:
        print(f"  eligible {cf.get('eligible', 0)} · scored {cf.get('scored', 0)} "
              f"· flagged BORDERLINE {cf.get('flagged', 0)} "
              f"· post-judge DEMOTE {lc.get('country_fallback_demote', 0)} "
              f"(judge {'ran' if artifact['params']['judge_ran'] else 'NOT run'})")
        for r in (cf.get("receipts") or [])[:15]:
            cs = r.get("country_signal") or {}
            print(f"  dt-{r['topic_id']:>5} [{r['verdict']}] distinct="
                  f"{cs.get('distinct')} dominant={cs.get('dominant_share')} "
                  f"located={cs.get('total_located')} ovl={r.get('entity_overlap')} "
                  f"· {(r['label'] or '')[:42]}")
            print(f"        countries: {cs.get('countries')}")
            a = (r["top_country_group"] or [{}])[0].get("headline", "(none)")
            b = (r["other_countries_group"] or [{}])[0].get("headline", "(none)")
            print(f"        top:   {a[:66]}")
            print(f"        other: {b[:66]}")


# ---------------------------------------------------------------- write / revert
async def run_write(artifact_path: Path, params: OverMergeParams,
                    force_unsafe: bool) -> None:
    """Demote DEMOTE-verdict topics active -> candidate (reversible, loud).

    NOTE: this is the WIRING-STEP path, not the Step-1 audit deliverable. It is
    guarded (nightly + heavy-lock) and writes a run ledger for precise --revert.
    Durable stickiness against the next promotion cycle is the follow-up
    (a dynamic_topics over-merge marker, like flag_junk's is_junk) — until then a
    demoted blob may re-promote next nightly; this path exists for that wiring."""
    if (_nightly_running() or _heavy_lock_held()) and not force_unsafe:
        print("REFUSING to write: a nightly / heavy job is running (hard rule: "
              "never touch a running M1 nightly). Re-run when it exits, or "
              "--force-unsafe if certain.", file=sys.stderr)
        sys.exit(3)
    artifact = json.loads(artifact_path.read_text())
    age_h = (dt.datetime.now(dt.timezone.utc)
             - dt.datetime.fromisoformat(artifact["generated_at"])).total_seconds() / 3600
    if age_h > 24:
        print(f"REFUSING: artifact is {age_h:.1f}h old (>24h) — re-audit first.",
              file=sys.stderr)
        sys.exit(3)
    run = artifact["run_id"]
    demote = [r for r in artifact["topics"] if r["verdict"] == DEMOTE]
    if not demote:
        print("no DEMOTE verdicts in artifact — nothing to write")
        return
    print(f"write plan: run={run} -> demote {len(demote)} topics active->candidate")

    conn = await _connect()
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    ledger_path = LEDGER_DIR / f"{run}-demotions.jsonl"
    try:
        moved = 0
        with ledger_path.open("w") as ledger:
            for r in demote:
                tid = r["topic_id"]
                # loud per-topic log with the two sub-cluster headlines
                a = _first_headline(r.get("rep_ids_a"), artifact)
                b = _first_headline(r.get("rep_ids_b"), artifact)
                res = await conn.execute(
                    "UPDATE dynamic_topics SET state='candidate', "
                    "last_state_change=NOW(), updated_at=NOW() "
                    "WHERE id=$1 AND state='active'", tid)
                changed = int(res.split()[-1])
                moved += changed
                lane = r.get("lane") or LANE_EMBEDDING
                ledger.write(json.dumps({
                    "run_id": run, "topic_id": tid, "label": r["label"],
                    "lane": lane, "reason": r["reason"],
                    "gap_ratio": r.get("gap_ratio"), "balance": r.get("balance"),
                    "country_signal": r.get("country_signal"), "changed": changed,
                    "group_a_signal": (r.get("rep_ids_a") or [None])[0],
                    "group_b_signal": (r.get("rep_ids_b") or [None])[0],
                    "at": dt.datetime.now(dt.timezone.utc).isoformat()}) + "\n")
                if lane == LANE_COUNTRY:
                    cs = r.get("country_signal") or {}
                    print(f"[overmerge] DEMOTE dt-{tid} '{(r['label'] or '')[:46]}' "
                          f"COUNTRY-FALLBACK (distinct={cs.get('distinct')} "
                          f"dominant={cs.get('dominant_share')} "
                          f"located={cs.get('total_located')} "
                          f"ovl={r.get('entity_overlap')}) -> candidate ({changed})")
                    print(f"           court-failed cross-country fusion "
                          f"(embedding gap too narrow to split) —")
                    print(f"             top country:      {a}")
                    print(f"             other countries:  {b}")
                else:
                    print(f"[overmerge] DEMOTE dt-{tid} '{(r['label'] or '')[:46]}' "
                          f"EMBEDDING (gap={r.get('gap_ratio')} bal={r.get('balance')} "
                          f"ovl={r.get('entity_overlap')}) -> candidate ({changed})")
                    print(f"           two stories fused —")
                    print(f"             A: {a}")
                    print(f"             B: {b}")
        print(f"\nTOTAL demoted: {moved}/{len(demote)} topics")
        print(f"ledger -> {ledger_path}")
        print(f"REVERSAL: python -m scripts.detect_overmerge --revert {run}")
    finally:
        await conn.close()


def _first_headline(rep_ids, artifact) -> str:
    # best-effort: the receipts already carry headlines
    if not rep_ids:
        return "(no representative)"
    target = rep_ids[0]
    for section in ("demote_receipts", "borderline_receipts"):
        for rec in artifact.get(section, []):
            for grp in (rec.get("group_a", []), rec.get("group_b", [])):
                for h in grp:
                    if h.get("signal_id") == target:
                        return (h.get("headline") or "")[:70]
    return f"signal {target}"


async def run_revert(run_id: str) -> None:
    """Restore topics this run demoted (state candidate -> active), from the
    run ledger. Guarded: only rows still 'candidate' are touched."""
    ledger_path = LEDGER_DIR / f"{run_id}-demotions.jsonl"
    if not ledger_path.exists():
        print(f"no ledger for run {run_id} at {ledger_path}", file=sys.stderr)
        sys.exit(2)
    ids = []
    for line in ledger_path.read_text().splitlines():
        line = line.strip()
        if line:
            ids.append(json.loads(line)["topic_id"])
    conn = await _connect()
    try:
        res = await conn.execute(
            "UPDATE dynamic_topics SET state='active', last_state_change=NOW(), "
            "updated_at=NOW() WHERE id = ANY($1::bigint[]) AND state='candidate'",
            ids)
        print(f"reverted {run_id}: {res} ({len(ids)} ledger ids)")
    finally:
        await conn.close()


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--artifact", type=Path, default=None)
    ap.add_argument("--judge", action="store_true",
                    help="resolve borderline topics with a DeepSeek 'one story or "
                         "two?' call (off in pure audit)")
    ap.add_argument("--write", action="store_true",
                    help="demote DEMOTE-verdict topics active->candidate (guarded; "
                         "wiring-step path, not the Step-1 audit)")
    ap.add_argument("--revert", metavar="RUN_ID", default=None)
    ap.add_argument("--limit", type=int, default=0,
                    help="scan only the first N topics (read-only smoke/dev; 0=all)")
    ap.add_argument("--force-unsafe", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    import dataclasses
    params = dataclasses.replace(OverMergeParams.from_env(), seed=args.seed)
    artifact_path = args.artifact or (
        ARTIFACT_DIR / f"{dt.date.today().isoformat()}-overmerge-audit.json")

    if args.revert:
        asyncio.run(run_revert(args.revert))
    elif args.write:
        asyncio.run(run_write(artifact_path, params, args.force_unsafe))
    else:
        asyncio.run(run_audit(args.seed, params, artifact_path, args.judge,
                              args.limit))


if __name__ == "__main__":
    main()
