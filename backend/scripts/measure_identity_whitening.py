#!/usr/bin/env python3
"""T1 — measure whether WHITENED space separates same-story from different-story
centroid pairs at the IDENTITY layer, and fit the three gate thresholds.

WHY (diagnosis `docs/research/recall-229/2026-07-28-identity-layer-raw-cosine.md`):
`project_dynamic_topics.py` compares centroids in RAW e5 cosine at three gates —
MATCH_THRESHOLD 0.88 (cluster vs topic running centroid), ANCHOR_THRESHOLD 0.93
(cluster vs the topic's founding anchor), MERGE_THRESHOLD 0.90 (topic vs topic).
Raw e5 is anisotropic: same-story and different-story pairs both live in a narrow
~0.93-0.99 band, so every gate sits INSIDE the overlap. Measured witness: a
Colombian assassination-plot cluster sits 0.9391 raw from a New Zealand
sexual-assault anchor (ABOVE the 0.93 gate) while a true continuation sits 0.9971.
In whitened space (`app/data/e5_whitening.npz`, already shipped) the same pairs
read 0.4501 vs 0.9751.

WHAT THIS DOES (read-only; writes NOTHING to any prod table):
  1. collects TRUE pairs (same story) and FALSE pairs (different story) by
     MECHANICAL rules stated below — never by eyeballing similarity;
  2. computes raw AND whitened cosine for every pair;
  3. reports both distributions per gate + the overlap + candidate taus;
  4. applies the PRE-REGISTERED KILL RULE: if p5(true) <= p95(false) in whitened
     space for a gate, the verdict for that gate is STOP.

PAIR CONSTRUCTION (pre-registered, mechanical)
----------------------------------------------
Vectors. `C_i` = `emergent_clusters.centroid_vec` (768-dim e5 mean of the kept
set). `A_t` = topic anchor = the centroid of the topic's EARLIEST member cluster
(the engine's `anchor_centroid`; not persisted, reconstructed from
`dynamic_topic_members` order). `R_t,k` = the topic's running centroid just
BEFORE its k-th attach = arithmetic mean of member centroids 0..k-1 (exactly what
`Topic.attach`'s `running_mean` produces). `T_t` = `dynamic_topics.centroid_vec`
(the persisted running mean — what MERGE compares).

TRUE (same story)
  * `lineage`   — topics whose label court PASSED (`label_status='entailed'`):
                  every attach k>=1 yields (C_k vs R_t,k) for the MATCH gate and
                  (C_k vs A_t) for the ANCHOR gate. Member cluster label must be
                  non-NULL (a blackout attach is unverifiable). CAVEAT, stated
                  loudly: these pairs were SELECTED BY the raw gates, so the true
                  raw distribution is truncated from below at 0.88/0.93. That is
                  why `fragment` exists.
  * `fragment`  — clusters in the SAME snapshot whose labels are near-identical
                  (SequenceMatcher >= 0.80 on a unicode-normalised label, the
                  engine's own MERGE_LABEL_MIN) => nine ways of writing the same
                  event, which the engine FAILED to unify. Ground truth here is
                  independent of the engine, which makes it the load-bearing set.
                  Variant `fragment_loose` (>= 3 shared distinctive tokens AND
                  token-Jaccard >= 0.40) is collected separately and only used in
                  the sensitivity check.
  * `topic_dup` — pairs of live topics whose labels are near-identical: duplicate
                  identities that SHOULD merge. Feeds the MERGE gate.

FALSE (different story)
  * `false_lineage` — attaches onto court-FAILED topics where the absorbed
                  cluster's countries are DISJOINT from the anchor's AND the
                  labels are dissimilar (SequenceMatcher < 0.35 and ZERO shared
                  distinctive tokens). This is exactly the measured failure mode;
                  the diagnosis's named witnesses (topics 784 and 52) fall out of
                  this rule mechanically, and are additionally tagged `witness`.
  * `false_cluster` — same-snapshot cluster pairs, disjoint non-empty country
                  sets, dissimilar labels. Geometry = the ANCHOR gate.
  * `false_match`   — cluster vs an UNRELATED topic's running centroid `T_t`
                  (disjoint countries, dissimilar labels, and — when both sides
                  carry a typed category — different categories). Geometry = the
                  MATCH gate.
  * `false_merge`   — topic vs topic on `T_t` under the same disjointness rule.

Every FALSE rule requires both labels non-NULL: during the 07-23..07-27 DeepSeek
402 blackout `emergent_clusters.label` was 100% NULL, and an unlabelled cluster
cannot be mechanically called "a different story".

EXCLUSION RULE (stated, mechanical, sensitivity-reported)
  A court-PASSED topic can still be a black hole (a vague label trivially entails
  a diverse set), which would put false pairs inside the TRUE set and fatten its
  left tail. The one mechanical exclusion applied: drop lineage pairs whose topic
  id appears in ANY `detect_overmerge` demotion ledger (`*-demotions.jsonl`, repo
  + `~/AtlasLocalWorker`). `--sensitivity` re-fits without it and the artifact
  reports both.

CONSTRUCTION v0 -> v1
  The v0 tail audit (the `--no-artifacts` first pass) exposed four GROUND-TRUTH
  errors in the rules above, not threshold problems. `Rules` (below) documents
  each and its repair; the harness runs BOTH constructions every time and the
  artifact reports both verdicts, so the effect of the repairs is visible rather
  than asserted. v1 is primary. No threshold was moved at any point.

Usage (read-only; M1 mlvenv has numpy):
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend && /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.measure_identity_whitening --days 21

Exit code: 0 = PROCEED (all gates clear the kill rule), 1 = STOP, 2 = no data.
Artifacts are written on every run, including STOP — the STOP is the deliverable.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import random
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np

try:  # module-run from backend/ or repo root
    from app.services.whitening import apply_whitening, load_whitening
except ImportError:  # pragma: no cover
    from backend.app.services.whitening import apply_whitening, load_whitening

# ------------------------------------------------------------------ constants
REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
ARTIFACT_STEM = "2026-07-28-whitened-identity-taus"
OVERMERGE_LEDGER_DIRS = [
    REPO_ROOT / "docs" / "research" / "overmerge",
    Path.home() / "AtlasLocalWorker" / "docs" / "research" / "overmerge",
]

# Engine gates being re-fitted (raw values, for the contrast table).
RAW_GATES = {"match": 0.88, "anchor": 0.93, "merge": 0.90}

# Label rules (measurement-side; see module docstring).
SAME_LABEL_MIN = 0.80      # == project_dynamic_topics.MERGE_LABEL_MIN
DIFF_LABEL_MAX = 0.35      # below this AND zero shared tokens => different story
LOOSE_SHARED_TOKENS = 3    # fragment_loose: shared distinctive tokens
LOOSE_JACCARD = 0.40       # fragment_loose: token Jaccard
BLOCK_MIN_SHARED = 2       # inverted-index blocking for the same-event search
BLOCK_DF_MAX_SHARE = 0.05  # a token in >5% of a snapshot's labels is not distinctive

PCTS = [1, 5, 25, 50, 75, 95, 99]


class Rules:
    """Pair-construction rule set. `v0` is the first (pre-registered) pass; `v1`
    repairs the four defects the v0 TAIL AUDIT exposed — each is a ground-truth
    error, not a threshold move:

      D1 `false_lineage` was scored at the MATCH gate too, but the rule that
         calls it false compares the cluster to the topic's ANCHOR. A drifted
         running centroid can legitimately sit on the absorbed story, so those
         MATCH pairs were mislabelled. v1 scores `false_lineage` at ANCHOR only.
      D2 cross-SCRIPT pairs were auto-"different" (zero shared tokens is trivial
         between Cyrillic and Latin), filing one war as many. v1 refuses to
         judge across scripts.
      D3 TRUE `fragment`/`topic_dup` accepted templated labels naming DIFFERENT
         events ('Severe Storms in Serbia' vs '...in Germany', 'Violent Crimes
         and Sentences' MX vs UA). v1 additionally requires a shared country.
      D4 FALSE `false_cluster`/`false_match` could pair two clusters of the same
         typed category. v1 skips those when both categories are known.

    D3 costs recall on genuine CROSS-country/cross-language fragments (the
    Franco-Spanish wildfire case), and those are the pairs whitening scores
    LOWEST — so v1's true set is biased in whitening's FAVOUR. A STOP under v1
    is therefore the stronger result.
    """

    def __init__(self, name: str):
        self.name = name
        v1 = name == "v1"
        self.false_lineage_at_match = not v1     # D1
        self.require_same_script = v1            # D2
        self.fragment_requires_shared_cc = v1    # D3
        self.false_needs_diff_category = v1      # D4

# Generic tokens that recur in labels WITHOUT naming a subject. Mirrors
# project_dynamic_topics._GENERIC_TOKENS, plus label-specific desk words.
_GENERIC_TOKENS = {
    "news", "live", "update", "updates", "latest", "today", "report", "reports",
    "day", "daily", "the", "and", "for", "with", "from", "after", "over", "amid",
    "say", "says", "new", "top", "watch", "video", "photos", "roundup", "mix",
    "mixed", "various", "diverse", "headlines", "local", "regional", "general",
    "national", "international", "world", "global", "events", "issues", "story",
    "stories", "crisis", "amidst", "against", "into", "about", "during", "under",
    "las", "los", "del", "que", "con", "por", "para", "una", "noticias",
    "notícias", "hoy", "dia", "día", "nesta", "esta", "resumen",
    "haber", "için", "ile", "son", "dakika", "berita", "ini", "yang", "dan",
    "untuk", "dari", "les", "des", "une", "pour", "avec", "der", "die", "das",
    "und", "für", "tin", "tức", "tổng", "hợp",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "2025", "2026",
}


# ------------------------------------------------------------------ label utils
def norm_label(s: str | None) -> str:
    """Unicode-aware lowercase + punctuation collapse.

    Deliberately NOT `project_dynamic_topics.labels_compatible`'s `[^a-z0-9]`
    normaliser: that maps every non-Latin label to the empty string, which is
    correct-by-accident for the engine (it then refuses to merge) but would make
    this measurement blind to Arabic/CJK/Cyrillic labels.
    """
    if not s:
        return ""
    x = unicodedata.normalize("NFKC", s).lower()
    x = re.sub(r"[^\w\s]+", " ", x, flags=re.UNICODE)
    return re.sub(r"\s+", " ", x).strip()


def label_sim(a: str | None, b: str | None) -> float:
    na, nb = norm_label(a), norm_label(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


def subject_tokens(s: str | None) -> set[str]:
    """Letter-only tokens (len>=3) minus generic/desk/date words."""
    toks = re.findall(r"[^\W\d_]{3,}", norm_label(s), re.UNICODE)
    return {t for t in toks if t not in _GENERIC_TOKENS}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def same_event(la: str | None, lb: str | None) -> bool:
    return label_sim(la, lb) >= SAME_LABEL_MIN


def same_event_loose(la: str | None, lb: str | None) -> bool:
    ta, tb = subject_tokens(la), subject_tokens(lb)
    return len(ta & tb) >= LOOSE_SHARED_TOKENS and jaccard(ta, tb) >= LOOSE_JACCARD


def dominant_script(s: str | None) -> str:
    """Dominant Unicode script of a label's letters ('latin', 'cyrillic', ...)."""
    c: Counter = Counter()
    for ch in s or "":
        if not ch.isalpha():
            continue
        try:
            c[unicodedata.name(ch).split()[0].lower()] += 1
        except ValueError:
            continue
    return c.most_common(1)[0][0] if c else "none"


def different_story(la: str | None, lb: str | None, *, require_same_script: bool = False) -> bool:
    """Mechanically 'not the same story' by LABEL alone (countries checked separately).

    `require_same_script` (construction v1) is a CONTAMINATION fix found by the v0
    tail audit: across scripts, "zero shared tokens" is trivially true, so
    'Уничтожение Пунктов Управления БПЛА' vs 'Russian Artillery Strikes on
    Ukrainian Forces' — one war — was being filed as a different story and
    inflating p95(false).
    """
    if not la or not lb:
        return False  # unlabelled => unverifiable, never counted as false
    if require_same_script:
        sa, sb = dominant_script(la), dominant_script(lb)
        if sa == "none" or sb == "none" or sa != sb:
            return False  # cross-script: not mechanically judgeable
    if label_sim(la, lb) >= DIFF_LABEL_MAX:
        return False
    return not (subject_tokens(la) & subject_tokens(lb))


def countries_share(a: Sequence[str] | None, b: Sequence[str] | None) -> bool:
    sa, sb = {x for x in (a or []) if x}, {x for x in (b or []) if x}
    return bool(sa & sb)


def countries_disjoint(a: Sequence[str] | None, b: Sequence[str] | None) -> bool:
    sa, sb = {x for x in (a or []) if x}, {x for x in (b or []) if x}
    return bool(sa) and bool(sb) and not (sa & sb)


# ------------------------------------------------------------------ math utils
def cos_rows(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Row-wise cosine between two [n, dim] float32 matrices."""
    un = u / np.clip(np.linalg.norm(u, axis=1, keepdims=True), 1e-12, None)
    vn = v / np.clip(np.linalg.norm(v, axis=1, keepdims=True), 1e-12, None)
    return np.sum(un * vn, axis=1)


def describe(vals: Iterable[float]) -> dict[str, Any]:
    a = np.asarray(list(vals), dtype=np.float64)
    if a.size == 0:
        return {"n": 0}
    out: dict[str, Any] = {"n": int(a.size), "mean": round(float(a.mean()), 4),
                           "min": round(float(a.min()), 4), "max": round(float(a.max()), 4)}
    for p in PCTS:
        out[f"p{p}"] = round(float(np.percentile(a, p)), 4)
    return out


def auc(true_vals: Sequence[float], false_vals: Sequence[float]) -> float | None:
    """Mann-Whitney AUC: P(true score > false score), ties at 0.5."""
    if not true_vals or not false_vals:
        return None
    t = np.asarray(true_vals, dtype=np.float64)
    f = np.asarray(false_vals, dtype=np.float64)
    allv = np.concatenate([t, f])
    order = allv.argsort()
    ranks = np.empty_like(order, dtype=np.float64)
    ranks[order] = np.arange(1, allv.size + 1)
    # average ranks over ties
    srt = allv[order]
    i = 0
    while i < srt.size:
        j = i
        while j + 1 < srt.size and srt[j + 1] == srt[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    r_t = ranks[: t.size].sum()
    return round(float((r_t - t.size * (t.size + 1) / 2) / (t.size * f.size)), 4)


# ------------------------------------------------------------------ ledger
def overmerge_demoted_ids() -> tuple[set[int], list[str]]:
    ids: set[int] = set()
    seen: list[str] = []
    for d in OVERMERGE_LEDGER_DIRS:
        if not d.is_dir():
            continue
        for p in sorted(d.glob("*demot*.jsonl")):
            seen.append(str(p))
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                tid = row.get("topic_id")
                if isinstance(tid, int):
                    ids.add(tid)
    return ids, seen


# ------------------------------------------------------------------ data model
class Pair:
    __slots__ = ("gate", "truth", "source", "a_kind", "a_id", "b_kind", "b_id",
                 "a_label", "b_label", "a_cc", "b_cc", "raw", "wht", "story",
                 "flags", "a_cids", "b_cids", "a_lang", "b_lang")

    def __init__(self, gate, truth, source, a_kind, a_id, b_kind, b_id,
                 a_label, b_label, a_cc, b_cc, story, flags=None,
                 a_cids=None, b_cids=None):
        self.gate = gate; self.truth = truth; self.source = source
        self.a_kind = a_kind; self.a_id = a_id
        self.b_kind = b_kind; self.b_id = b_id
        self.a_label = a_label; self.b_label = b_label
        self.a_cc = list(a_cc or []); self.b_cc = list(b_cc or [])
        self.story = story
        self.flags = set(flags or ())
        self.a_cids = list(a_cids or ([a_id] if a_kind == "cluster" else []))
        self.b_cids = list(b_cids or ([b_id] if b_kind == "cluster" else []))
        self.a_lang: str | None = None
        self.b_lang: str | None = None
        self.raw: float = float("nan")
        self.wht: float = float("nan")

    @property
    def lang_rel(self) -> str:
        if not self.a_lang or not self.b_lang:
            return "unknown"
        return "same_lang" if self.a_lang == self.b_lang else "cross_lang"

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate, "truth": self.truth, "source": self.source,
            "a": {"kind": self.a_kind, "id": self.a_id,
                  "label": (self.a_label or "")[:90], "cc": self.a_cc[:4],
                  "lang": self.a_lang},
            "b": {"kind": self.b_kind, "id": self.b_id,
                  "label": (self.b_label or "")[:90], "cc": self.b_cc[:4],
                  "lang": self.b_lang},
            "story": self.story, "lang_rel": self.lang_rel,
            "raw": round(self.raw, 4), "whitened": round(self.wht, 4),
            "flags": sorted(self.flags),
        }


# ------------------------------------------------------------------ collection
async def load_clusters(conn, days: int) -> dict[int, dict[str, Any]]:
    """Cluster METADATA only (no vectors) for the window."""
    rows = await conn.fetch(
        """SELECT id, snapshot_at, cluster_id, label, top_country_codes, n_signals, cohesion
             FROM emergent_clusters
            WHERE centroid_vec IS NOT NULL AND snapshot_at > now() - ($1 || ' days')::interval
            ORDER BY snapshot_at, cluster_id""",
        str(days),
    )
    return {
        int(r["id"]): {
            "id": int(r["id"]),
            "snapshot_at": r["snapshot_at"],
            "cluster_id": int(r["cluster_id"]),
            "label": r["label"],
            "cc": list(r["top_country_codes"] or []),
            "n_signals": int(r["n_signals"] or 0),
        }
        for r in rows
    }


async def load_cluster_meta(conn, ids: Sequence[int]) -> dict[int, dict[str, Any]]:
    """Metadata for specific clusters regardless of the sampling window.

    The engine's `anchor_centroid` is the topic's FIRST-EVER member cluster. If a
    topic was founded before `--days`, window-filtering its members would hand the
    measurement a truncated anchor and quietly change what it is measuring.
    """
    out: dict[int, dict[str, Any]] = {}
    ids = list(dict.fromkeys(ids))
    for i in range(0, len(ids), 2000):
        rows = await conn.fetch(
            """SELECT id, snapshot_at, cluster_id, label, top_country_codes, n_signals
                 FROM emergent_clusters
                WHERE id = ANY($1::bigint[]) AND centroid_vec IS NOT NULL""",
            ids[i:i + 2000])
        for r in rows:
            out[int(r["id"])] = {
                "id": int(r["id"]), "snapshot_at": r["snapshot_at"],
                "cluster_id": int(r["cluster_id"]), "label": r["label"],
                "cc": list(r["top_country_codes"] or []), "n_signals": int(r["n_signals"] or 0),
            }
    return out


async def load_topics(conn, days: int) -> dict[int, dict[str, Any]]:
    rows = await conn.fetch(
        """SELECT id, label, label_status, state, category, is_roundup, is_umbrella,
                  parent_id, last_seen, centroid_vec IS NOT NULL AS has_vec
             FROM dynamic_topics
            WHERE last_seen > now() - ($1 || ' days')::interval""",
        str(days),
    )
    return {
        int(r["id"]): {
            "id": int(r["id"]), "label": r["label"], "label_status": r["label_status"],
            "state": r["state"], "category": r["category"],
            "is_roundup": bool(r["is_roundup"]), "is_umbrella": bool(r["is_umbrella"]),
            "parent_id": r["parent_id"], "last_seen": r["last_seen"],
            "has_vec": bool(r["has_vec"]),
        }
        for r in rows
    }


async def load_members(conn, topic_ids: Sequence[int]) -> dict[int, list[dict[str, Any]]]:
    out: dict[int, list[dict[str, Any]]] = defaultdict(list)
    ids = list(topic_ids)
    for i in range(0, len(ids), 5000):
        rows = await conn.fetch(
            """SELECT dynamic_topic_id, emergent_cluster_id, snapshot_at
                 FROM dynamic_topic_members
                WHERE dynamic_topic_id = ANY($1::bigint[])
                ORDER BY snapshot_at, emergent_cluster_id""",
            ids[i:i + 5000],
        )
        for r in rows:
            out[int(r["dynamic_topic_id"])].append(
                {"cluster_id": int(r["emergent_cluster_id"]), "snapshot_at": r["snapshot_at"]}
            )
    return out


async def fetch_cluster_vecs(conn, ids: Sequence[int]) -> dict[int, np.ndarray]:
    out: dict[int, np.ndarray] = {}
    ids = list(dict.fromkeys(ids))
    for i in range(0, len(ids), 2000):
        rows = await conn.fetch(
            "SELECT id, centroid_vec FROM emergent_clusters WHERE id = ANY($1::bigint[])",
            ids[i:i + 2000],
        )
        for r in rows:
            if r["centroid_vec"] is not None:
                out[int(r["id"])] = np.asarray(r["centroid_vec"], dtype=np.float32)
    return out


async def fetch_topic_vecs(conn, ids: Sequence[int]) -> dict[int, np.ndarray]:
    out: dict[int, np.ndarray] = {}
    ids = list(dict.fromkeys(ids))
    for i in range(0, len(ids), 2000):
        rows = await conn.fetch(
            "SELECT id, centroid_vec FROM dynamic_topics WHERE id = ANY($1::bigint[])",
            ids[i:i + 2000],
        )
        for r in rows:
            if r["centroid_vec"] is not None:
                out[int(r["id"])] = np.asarray(r["centroid_vec"], dtype=np.float32)
    return out


async def cluster_langs(conn, cluster_ids: Sequence[int]) -> dict[int, str]:
    """Dominant language key per cluster: `source_lang` where known, else the
    dominant Unicode SCRIPT of its headlines.

    `signals_v2.source_lang` is only ~45% populated (the GDELT lane writes 'xx'),
    so the script fallback is what keeps this measurable. LIMITATION, stated:
    Latin-script rows with unknown lang all collapse to `script:latin`, so
    Romanian-vs-English reads as SAME language. That biases the cross-language
    effect DOWNWARD — the measured effect is a lower bound.
    """
    ids = list(dict.fromkeys(cluster_ids))
    samples: dict[int, list[int]] = {}
    for i in range(0, len(ids), 2000):
        rows = await conn.fetch(
            "SELECT id, sample_signal_ids FROM emergent_clusters WHERE id = ANY($1::bigint[])",
            ids[i:i + 2000])
        for r in rows:
            samples[int(r["id"])] = [int(x) for x in (r["sample_signal_ids"] or [])][:8]
    sig_ids = sorted({s for v in samples.values() for s in v})
    info: dict[int, tuple[str | None, str]] = {}
    for i in range(0, len(sig_ids), 5000):
        rows = await conn.fetch(
            "SELECT id, source_lang, headline FROM signals_v2 WHERE id = ANY($1::bigint[])",
            sig_ids[i:i + 5000])
        for r in rows:
            info[int(r["id"])] = (r["source_lang"], r["headline"] or "")
    out: dict[int, str] = {}
    for cid, sids in samples.items():
        votes: Counter = Counter()
        for s in sids:
            lang, head = info.get(s, (None, ""))
            if lang and lang not in ("xx", ""):
                votes[lang] += 1
            else:
                sc = dominant_script(head)
                if sc != "none":
                    votes[f"script:{sc}"] += 1
        if votes:
            out[cid] = votes.most_common(1)[0][0]
    return out


def same_event_candidates(items: list[dict[str, Any]], key: str = "label"
                          ) -> Iterable[tuple[dict, dict]]:
    """Blocked candidate generation: only compare items sharing >=2 distinctive tokens.

    Bounds an O(n^2) SequenceMatcher sweep (a snapshot holds up to ~3.8k clusters).
    Tokens present in >5% of the block's labels are dropped as non-distinctive, so
    a ubiquitous name ('trump') cannot create a giant block.
    """
    n = len(items)
    if n < 2:
        return []
    toks = [subject_tokens(it.get(key)) for it in items]
    df: Counter = Counter()
    for s in toks:
        df.update(s)
    cap = max(2, int(BLOCK_DF_MAX_SHARE * n))
    inv: dict[str, list[int]] = defaultdict(list)
    for i, s in enumerate(toks):
        for t in s:
            if df[t] <= cap:
                inv[t].append(i)
    shared: dict[tuple[int, int], int] = defaultdict(int)
    for t, idxs in inv.items():
        if len(idxs) < 2 or len(idxs) > 400:  # runaway block: skip, reported as bounded recall
            continue
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                shared[(idxs[x], idxs[y])] += 1
    for (i, j), c in shared.items():
        if c >= BLOCK_MIN_SHARED:
            yield items[i], items[j]


# ------------------------------------------------------------------ main build
async def build_pairs(conn, args, rules: Rules,
                      cache: dict[str, Any] | None = None) -> tuple[list[Pair], dict[str, Any]]:
    rng = random.Random(args.seed)
    cache = cache if cache is not None else {}
    if "clusters" not in cache:
        cache["clusters"] = await load_clusters(conn, args.days)
        cache["topics"] = await load_topics(conn, args.days)
        cache["ledger"] = overmerge_demoted_ids()
    clusters = cache["clusters"]
    topics = cache["topics"]
    demoted, ledger_files = cache["ledger"]
    diff = lambda a, b: different_story(a, b, require_same_script=rules.require_same_script)

    if "members" not in cache:
        mem = await load_members(conn, list(topics.keys()))
        # FULL member history (never window-filtered): the anchor is the first-ever
        # member. Drop only members whose cluster row is gone (retention trim).
        extra = {m["cluster_id"] for ms in mem.values() for m in ms} - set(clusters)
        cmeta_extra = await load_cluster_meta(conn, sorted(extra)) if extra else {}
        cache["cmeta"] = {**clusters, **cmeta_extra}
        for tid, ms in list(mem.items()):
            mem[tid] = [m for m in ms if m["cluster_id"] in cache["cmeta"]]
        cache["members"] = mem
    members = cache["members"]
    cmeta: dict[int, dict[str, Any]] = cache["cmeta"]

    meta: dict[str, Any] = {
        "construction": rules.name,
        "window_days": args.days,
        "seed": args.seed,
        "clusters_in_window": len(clusters),
        "clusters_with_label": sum(1 for c in clusters.values() if c["label"]),
        "topics_in_window": len(topics),
        "overmerge_ledger_files": ledger_files,
        "overmerge_demoted_topic_ids": len(demoted),
    }

    pairs: list[Pair] = []
    need_cvecs: set[int] = set()
    need_tvecs: set[int] = set()

    # ---------------- TRUE lineage (match + anchor) --------------------------
    entailed = [t for t in topics.values()
                if t["label_status"] == "entailed" and len(members.get(t["id"], [])) >= 2]
    entailed.sort(key=lambda t: t["id"])
    if args.max_lineage_topics and len(entailed) > args.max_lineage_topics:
        entailed = rng.sample(entailed, args.max_lineage_topics)
    lineage_specs: list[dict[str, Any]] = []
    for t in entailed:
        ms = members[t["id"]]
        anchor_cid = ms[0]["cluster_id"]
        for k in range(1, len(ms)):
            cid = ms[k]["cluster_id"]
            if not cmeta[cid]["label"]:
                continue  # blackout attach: unverifiable
            prior = [m["cluster_id"] for m in ms[:k]]
            lineage_specs.append({"topic": t, "cid": cid, "anchor": anchor_cid, "prior": prior})
            need_cvecs.update(prior); need_cvecs.add(cid)

    # ---------------- FALSE lineage (the measured failure mode) --------------
    failed = [t for t in topics.values()
              if t["label_status"] == "failed" and len(members.get(t["id"], [])) >= 2]
    false_lineage_specs: list[dict[str, Any]] = []
    for t in failed:
        ms = members[t["id"]]
        anchor = cmeta[ms[0]["cluster_id"]]
        for k in range(1, len(ms)):
            c = cmeta[ms[k]["cluster_id"]]
            if not diff(anchor["label"], c["label"]):
                continue
            if not countries_disjoint(anchor["cc"], c["cc"]):
                continue
            prior = [m["cluster_id"] for m in ms[:k]]
            false_lineage_specs.append(
                {"topic": t, "cid": c["id"], "anchor": anchor["id"], "prior": prior})
            need_cvecs.update(prior); need_cvecs.add(c["id"])

    # ---------------- TRUE fragments / FALSE cluster pairs (anchor geometry) --
    by_snap: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for c in clusters.values():
        if c["label"]:
            by_snap[c["snapshot_at"]].append(c)

    cluster_topic: dict[int, int] = {}
    for tid, ms in members.items():
        for m in ms:
            cluster_topic[m["cluster_id"]] = tid

    def ccat(cid: int) -> str | None:
        t = topics.get(cluster_topic.get(cid, -1))
        return t["category"] if t else None

    def category_blocks(ca: str | None, cb: str | None) -> bool:
        """v1/D4: refuse a FALSE pair whose two sides carry the same typed category."""
        return bool(rules.false_needs_diff_category and ca and cb and ca == cb)

    frag_strict: list[tuple[dict, dict]] = []
    frag_loose: list[tuple[dict, dict]] = []
    for snap, items in by_snap.items():
        for a, b in same_event_candidates(items):
            if rules.fragment_requires_shared_cc and not countries_share(a["cc"], b["cc"]):
                continue  # D3: templated label, different event
            if same_event(a["label"], b["label"]):
                frag_strict.append((a, b))
            elif same_event_loose(a["label"], b["label"]):
                frag_loose.append((a, b))

    false_cluster: list[tuple[dict, dict]] = []
    snaps = [s for s, items in by_snap.items() if len(items) >= 20]
    tries = 0
    target = args.max_false_cluster
    while len(false_cluster) < target and tries < target * 60 and snaps:
        tries += 1
        items = by_snap[rng.choice(snaps)]
        a, b = rng.choice(items), rng.choice(items)
        if a["id"] == b["id"]:
            continue
        if not countries_disjoint(a["cc"], b["cc"]):
            continue
        if not diff(a["label"], b["label"]):
            continue
        if category_blocks(ccat(a["id"]), ccat(b["id"])):
            continue
        false_cluster.append((a, b))

    for a, b in frag_strict + frag_loose + false_cluster:
        need_cvecs.add(a["id"]); need_cvecs.add(b["id"])

    # ---------------- MERGE gate: topic <-> topic on persisted centroids -----
    live = [t for t in topics.values()
            if t["has_vec"] and not t["is_roundup"] and not t["is_umbrella"] and t["label"]]
    tprim: dict[int, list[str]] = {}
    for t in live:
        ms = members.get(t["id"], [])
        cc: list[str] = []
        for m in ms:
            cc.extend(cmeta[m["cluster_id"]]["cc"])
        tprim[t["id"]] = [x for x, _ in Counter(cc).most_common(4)]

    topic_dup: list[tuple[dict, dict]] = []
    for a, b in same_event_candidates(live):
        if a["id"] == b["id"]:
            continue
        if a.get("parent_id") == b["id"] or b.get("parent_id") == a["id"]:
            continue
        if rules.fragment_requires_shared_cc and not countries_share(
                tprim.get(a["id"]), tprim.get(b["id"])):
            continue  # D3
        if same_event(a["label"], b["label"]):
            topic_dup.append((a, b))

    false_merge: list[tuple[dict, dict]] = []
    tries = 0
    while len(false_merge) < args.max_false_merge and tries < args.max_false_merge * 60 and len(live) > 2:
        tries += 1
        a, b = rng.choice(live), rng.choice(live)
        if a["id"] == b["id"]:
            continue
        if not diff(a["label"], b["label"]):
            continue
        if not countries_disjoint(tprim.get(a["id"]), tprim.get(b["id"])):
            continue
        if a["category"] and b["category"] and a["category"] == b["category"]:
            continue
        false_merge.append((a, b))

    # ---------------- FALSE match: cluster <-> unrelated topic centroid ------
    false_match: list[tuple[dict, dict]] = []
    labelled = [c for c in clusters.values() if c["label"]]
    tries = 0
    while len(false_match) < args.max_false_match and tries < args.max_false_match * 60 and live and labelled:
        tries += 1
        c, t = rng.choice(labelled), rng.choice(live)
        if cluster_topic.get(c["id"]) == t["id"]:
            continue
        if not diff(c["label"], t["label"]):
            continue
        if not countries_disjoint(c["cc"], tprim.get(t["id"])):
            continue
        if category_blocks(ccat(c["id"]), t["category"]):
            continue
        false_match.append((c, t))

    for a, b in topic_dup + false_merge:
        need_tvecs.add(a["id"]); need_tvecs.add(b["id"])
    for c, t in false_match:
        need_cvecs.add(c["id"]); need_tvecs.add(t["id"])

    # ---------------- fetch vectors -----------------------------------------
    cvec = await fetch_cluster_vecs(conn, sorted(need_cvecs))
    tvec = await fetch_topic_vecs(conn, sorted(need_tvecs))
    meta["cluster_vectors_fetched"] = len(cvec)
    meta["topic_vectors_fetched"] = len(tvec)

    def tmem(tid: int) -> list[int]:
        return [m["cluster_id"] for m in members.get(tid, [])][:6]

    def C(cid: int) -> np.ndarray | None:
        return cvec.get(cid)

    def running(prior: list[int]) -> np.ndarray | None:
        vs = [cvec[c] for c in prior if c in cvec]
        return np.mean(np.stack(vs), axis=0) if vs else None

    vec_a: list[np.ndarray] = []
    vec_b: list[np.ndarray] = []

    def add(p: Pair, va: np.ndarray | None, vb: np.ndarray | None) -> None:
        if va is None or vb is None:
            return
        pairs.append(p); vec_a.append(va); vec_b.append(vb)

    # TRUE lineage
    for sp in lineage_specs:
        t, c = sp["topic"], cmeta[sp["cid"]]
        anchor = cmeta[sp["anchor"]]
        flags = {"overmerge_demoted"} if t["id"] in demoted else set()
        add(Pair("anchor", "true", "lineage", "cluster", c["id"], "topic_anchor", t["id"],
                 c["label"], anchor["label"], c["cc"], anchor["cc"], f"topic:{t['id']}", flags,
                 b_cids=[sp["anchor"]]),
            C(c["id"]), C(sp["anchor"]))
        add(Pair("match", "true", "lineage", "cluster", c["id"], "topic_running", t["id"],
                 c["label"], t["label"], c["cc"], tprim.get(t["id"], []), f"topic:{t['id']}", flags,
                 b_cids=sp["prior"]),
            C(c["id"]), running(sp["prior"]))

    # FALSE lineage (+ witnesses)
    for sp in false_lineage_specs:
        t, c = sp["topic"], cmeta[sp["cid"]]
        anchor = cmeta[sp["anchor"]]
        flags = {"witness"} if t["id"] in args.witness_topics else set()
        add(Pair("anchor", "false", "false_lineage", "cluster", c["id"], "topic_anchor", t["id"],
                 c["label"], anchor["label"], c["cc"], anchor["cc"], f"topic:{t['id']}", flags,
                 b_cids=[sp["anchor"]]),
            C(c["id"]), C(sp["anchor"]))
        if rules.false_lineage_at_match:  # D1: unsound — the rule is an ANCHOR relation
            add(Pair("match", "false", "false_lineage", "cluster", c["id"], "topic_running",
                     t["id"], c["label"], t["label"], c["cc"], tprim.get(t["id"], []),
                     f"topic:{t['id']}", flags, b_cids=sp["prior"]),
                C(c["id"]), running(sp["prior"]))

    # TRUE fragments (anchor geometry: cluster <-> cluster == a fresh topic's anchor)
    for src, lst in (("fragment", frag_strict), ("fragment_loose", frag_loose)):
        if args.max_fragment and len(lst) > args.max_fragment:
            lst = rng.sample(lst, args.max_fragment)
        for a, b in lst:
            story = f"frag:{min(a['id'], b['id'])}"
            add(Pair("anchor", "true", src, "cluster", a["id"], "cluster", b["id"],
                     a["label"], b["label"], a["cc"], b["cc"], story),
                C(a["id"]), C(b["id"]))

    # FALSE cluster pairs (anchor geometry)
    for a, b in false_cluster:
        add(Pair("anchor", "false", "false_cluster", "cluster", a["id"], "cluster", b["id"],
                 a["label"], b["label"], a["cc"], b["cc"], f"xc:{a['id']}-{b['id']}"),
            C(a["id"]), C(b["id"]))

    # MERGE gate
    for a, b in topic_dup:
        add(Pair("merge", "true", "topic_dup", "topic", a["id"], "topic", b["id"],
                 a["label"], b["label"], tprim.get(a["id"], []), tprim.get(b["id"], []),
                 f"dup:{min(a['id'], b['id'])}",
                 a_cids=tmem(a["id"]), b_cids=tmem(b["id"])),
            tvec.get(a["id"]), tvec.get(b["id"]))
    for a, b in false_merge:
        add(Pair("merge", "false", "false_merge", "topic", a["id"], "topic", b["id"],
                 a["label"], b["label"], tprim.get(a["id"], []), tprim.get(b["id"], []),
                 f"xt:{a['id']}-{b['id']}",
                 a_cids=tmem(a["id"]), b_cids=tmem(b["id"])),
            tvec.get(a["id"]), tvec.get(b["id"]))

    # FALSE match (cluster <-> unrelated topic running centroid)
    for c, t in false_match:
        add(Pair("match", "false", "false_match", "cluster", c["id"], "topic_running", t["id"],
                 c["label"], t["label"], c["cc"], tprim.get(t["id"], []),
                 f"xm:{c['id']}-{t['id']}", b_cids=tmem(t["id"])),
            C(c["id"]), tvec.get(t["id"]))

    if not pairs:
        return [], meta

    A = np.stack(vec_a).astype(np.float32)
    B = np.stack(vec_b).astype(np.float32)
    raw = cos_rows(A, B)
    w = load_whitening()
    wht = cos_rows(apply_whitening(A, w), apply_whitening(B, w))
    for p, r, x in zip(pairs, raw, wht):
        p.raw = float(r); p.wht = float(x)

    # language keys (the explanatory axis: whitening's residual is language-heavy)
    langs = cache.setdefault("langs", {})
    want = {c for p in pairs for c in (p.a_cids + p.b_cids)} - set(langs)
    if want:
        langs.update(await cluster_langs(conn, sorted(want)))

    def side_lang(cids: list[int]) -> str | None:
        v: Counter = Counter(langs[c] for c in cids if c in langs)
        return v.most_common(1)[0][0] if v else None

    for p in pairs:
        p.a_lang = side_lang(p.a_cids)
        p.b_lang = side_lang(p.b_cids)

    meta["whitening"] = {"k": w.k, "dim": w.dim, "fit_n": w.fit_n, "fit_at": w.fit_at,
                         "artifact": os.path.relpath(
                             os.path.abspath(os.path.join(
                                 os.path.dirname(__file__), "..", "app", "data", "e5_whitening.npz")),
                             str(REPO_ROOT))}
    return pairs, meta


# ------------------------------------------------------------------ analysis
def fit_gate(pairs: list[Pair], gate: str, space: str,
             include: set[str] | None = None,
             exclude_flags: set[str] | None = None) -> dict[str, Any]:
    """Distributions + candidate tau for one gate in one space."""
    val = (lambda p: p.wht) if space == "whitened" else (lambda p: p.raw)
    sel = [p for p in pairs if p.gate == gate
           and (include is None or p.source in include)
           and not (exclude_flags and (p.flags & exclude_flags))]
    tv = [val(p) for p in sel if p.truth == "true"]
    fv = [val(p) for p in sel if p.truth == "false"]
    out: dict[str, Any] = {
        "gate": gate, "space": space,
        "true": describe(tv), "false": describe(fv),
        "true_stories": len({p.story for p in sel if p.truth == "true"}),
        "false_stories": len({p.story for p in sel if p.truth == "false"}),
        "auc": auc(tv, fv),
    }
    if not tv or not fv:
        out["verdict"] = "INSUFFICIENT"
        return out
    p5t = float(np.percentile(tv, 5))
    p95f = float(np.percentile(fv, 95))
    out["p5_true"] = round(p5t, 4)
    out["p95_false"] = round(p95f, 4)
    out["gap"] = round(p5t - p95f, 4)
    out["false_above_p5_true"] = round(float(np.mean(np.asarray(fv) >= p5t)), 4)
    out["true_below_p95_false"] = round(float(np.mean(np.asarray(tv) <= p95f)), 4)
    if p5t > p95f:
        tau = (p5t + p95f) / 2.0
        out["tau"] = round(tau, 4)
        out["true_kept_at_tau"] = round(float(np.mean(np.asarray(tv) >= tau)), 4)
        out["false_rejected_at_tau"] = round(float(np.mean(np.asarray(fv) < tau)), 4)
        out["verdict"] = "PROCEED"
    else:
        out["tau"] = None
        out["verdict"] = "STOP"
    return out


def tails(pairs: list[Pair], gate: str, truth: str, n: int, lowest: bool) -> list[dict[str, Any]]:
    sel = [p for p in pairs if p.gate == gate and p.truth == truth]
    sel.sort(key=lambda p: p.wht, reverse=not lowest)
    return [p.as_dict() for p in sel[:n]]


def analyse(pairs: list[Pair], meta: dict[str, Any]) -> dict[str, Any]:
    gates = ["match", "anchor", "merge"]
    primary_exclude = {"overmerge_demoted"}
    primary_include = {
        "match": None, "anchor": {"lineage", "fragment", "false_lineage", "false_cluster"},
        "merge": None,
    }
    result: dict[str, Any] = {
        "contract": "whitened-identity-taus-v1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "meta": meta,
        "raw_gates": RAW_GATES,
        "counts": {},
        "gates": {},
        "sensitivity": {},
        "tails": {},
    }
    cnt: dict[str, Any] = {}
    for g in gates:
        sel = [p for p in pairs if p.gate == g]
        cnt[g] = {
            "true": sum(1 for p in sel if p.truth == "true"),
            "false": sum(1 for p in sel if p.truth == "false"),
            "by_source": dict(Counter(f"{p.truth}:{p.source}" for p in sel)),
            "true_stories": len({p.story for p in sel if p.truth == "true"}),
            "false_stories": len({p.story for p in sel if p.truth == "false"}),
        }
    result["counts"] = cnt

    for g in gates:
        inc = primary_include[g]
        result["gates"][g] = {
            "whitened": fit_gate(pairs, g, "whitened", inc, primary_exclude),
            "raw": fit_gate(pairs, g, "raw", inc, primary_exclude),
        }
        result["tails"][g] = {
            "true_left_tail": tails(pairs, g, "true", 15, lowest=True),
            "false_right_tail": tails(pairs, g, "false", 15, lowest=False),
        }

    # ---- sensitivity: exclusion rule + true-source composition --------------
    variants: dict[str, dict[str, Any]] = {
        "no_overmerge_exclusion": {"exclude": set()},
        "with_overmerge_exclusion": {"exclude": primary_exclude},
        "lineage_only": {"exclude": primary_exclude,
                         "include": {"lineage", "false_lineage", "false_cluster",
                                     "false_match", "false_merge"}},
        "fragment_only": {"exclude": primary_exclude,
                          "include": {"fragment", "false_cluster", "false_lineage"}},
        "fragment_plus_loose": {"exclude": primary_exclude,
                                "include": {"fragment", "fragment_loose", "false_cluster",
                                            "false_lineage"}},
        "false_lineage_only": {"exclude": primary_exclude,
                               "include": {"lineage", "fragment", "false_lineage"}},
        "false_random_only": {"exclude": primary_exclude,
                              "include": {"lineage", "fragment", "false_cluster",
                                          "false_match", "false_merge"}},
        "no_witnesses": {"exclude": primary_exclude | {"witness"}},
    }
    for name, spec in variants.items():
        row: dict[str, Any] = {}
        for g in gates:
            f = fit_gate(pairs, g, "whitened", spec.get("include"), spec.get("exclude"))
            row[g] = {"n_true": f["true"].get("n", 0), "n_false": f["false"].get("n", 0),
                      "p5_true": f.get("p5_true"), "p95_false": f.get("p95_false"),
                      "gap": f.get("gap"), "tau": f.get("tau"), "verdict": f["verdict"]}
        result["sensitivity"][name] = row

    # ---- language effect: is whitened cosine measuring STORY or LANGUAGE? -----
    lang: dict[str, Any] = {}
    for g in gates:
        row: dict[str, Any] = {}
        for truth in ("true", "false"):
            for rel in ("same_lang", "cross_lang"):
                sel = [p for p in pairs
                       if p.gate == g and p.truth == truth and p.lang_rel == rel
                       and not (p.flags & primary_exclude)]
                row[f"{truth}/{rel}"] = {
                    "whitened": describe([p.wht for p in sel]),
                    "raw": describe([p.raw for p in sel]),
                }
        lang[g] = row
    result["language_effect"] = lang
    result["language_coverage"] = dict(Counter(p.lang_rel for p in pairs))

    verdicts = {g: result["gates"][g]["whitened"]["verdict"] for g in gates}
    result["verdict"] = ("PROCEED" if all(v == "PROCEED" for v in verdicts.values())
                         else "STOP")
    result["verdict_by_gate"] = verdicts
    result["taus"] = {g: result["gates"][g]["whitened"].get("tau") for g in gates}
    return result


# ------------------------------------------------------------------ family probe
async def family_probes(conn, patterns: Sequence[str]) -> list[dict[str, Any]]:
    """Pairwise raw/whitened cosine INSIDE a known same-event family.

    The diagnosis's own shredding exhibits (GQ-12 `%caspian%` = nine clusters of
    one event; GQ-05 `%espriella%`). Every pair here is the SAME event by
    construction, so the spread is a direct read on whether whitened space can
    reconverge a shredded story — the primary metric this plan exists to move.
    """
    w = load_whitening()
    out: list[dict[str, Any]] = []
    for pat in patterns:
        rows = await conn.fetch(
            """SELECT id, snapshot_at, label, n_signals, top_country_codes, centroid_vec
                 FROM emergent_clusters
                WHERE centroid_vec IS NOT NULL AND label ILIKE $1
                ORDER BY snapshot_at, id""",
            f"%{pat}%",
        )
        by_day: dict[str, list[Any]] = defaultdict(list)
        for r in rows:
            by_day[r["snapshot_at"].date().isoformat()].append(r)
        for day, items in sorted(by_day.items()):
            if len(items) < 3:
                continue
            V = np.stack([np.asarray(r["centroid_vec"], dtype=np.float32) for r in items])
            W = apply_whitening(V, w)
            iu = np.triu_indices(len(items), 1)
            raw = (V @ V.T)[iu]
            wht = (W @ W.T)[iu]
            out.append({
                "pattern": pat, "day": day, "n_clusters": len(items), "n_pairs": int(raw.size),
                "countries": sorted({c for r in items for c in (r["top_country_codes"] or [])}),
                "raw": {"min": round(float(raw.min()), 4), "p50": round(float(np.median(raw)), 4),
                        "max": round(float(raw.max()), 4)},
                "whitened": {"min": round(float(wht.min()), 4),
                             "p50": round(float(np.median(wht)), 4),
                             "max": round(float(wht.max()), 4)},
                "labels": [f"{r['label']} [{','.join(list(r['top_country_codes'] or [])[:2])}"
                           f"·{r['n_signals']}]" for r in items][:12],
            })
    return out


# ------------------------------------------------------------------ witnesses
async def witness_probe(conn, topic_ids: Sequence[int],
                        in_false: set[tuple[int, int]]) -> list[dict[str, Any]]:
    """FULL member-vs-anchor readout for the diagnosis's named topics.

    Reported regardless of whether a row cleared the mechanical FALSE rule, so the
    artifact shows the exhibits as the diagnosis states them AND marks which ones
    the conservative rule actually admitted (`in_false_set`).
    """
    w = load_whitening()
    out: list[dict[str, Any]] = []
    for tid in topic_ids:
        t = await conn.fetchrow(
            "SELECT id, label, state, label_status FROM dynamic_topics WHERE id=$1", tid)
        rows = await conn.fetch(
            """SELECT m.emergent_cluster_id AS cid, m.snapshot_at, c.label,
                      c.top_country_codes, c.n_signals, c.centroid_vec
                 FROM dynamic_topic_members m JOIN emergent_clusters c
                   ON c.id = m.emergent_cluster_id
                WHERE m.dynamic_topic_id=$1 AND c.centroid_vec IS NOT NULL
                ORDER BY m.snapshot_at, m.emergent_cluster_id""", tid)
        if not t or len(rows) < 2:
            continue
        V = np.stack([np.asarray(r["centroid_vec"], dtype=np.float32) for r in rows])
        W = apply_whitening(V, w)
        for i, r in enumerate(rows):
            out.append({
                "topic_id": tid, "topic_label": t["label"],
                "topic_label_status": t["label_status"], "topic_state": t["state"],
                "cluster_id": int(r["cid"]), "day": r["snapshot_at"].date().isoformat(),
                "cc": list(r["top_country_codes"] or [])[:3], "n_signals": int(r["n_signals"] or 0),
                "label": r["label"], "is_anchor": i == 0,
                "raw_vs_anchor": round(float(V[i] @ V[0]), 4),
                "whitened_vs_anchor": round(float(W[i] @ W[0]), 4),
                "in_false_set": (tid, int(r["cid"])) in in_false,
            })
    return out


# ------------------------------------------------------------------ rendering
def _pct_row(d: dict[str, Any]) -> str:
    if not d.get("n"):
        return "| — | 0 | | | | | | | |"
    return (f"{d['n']} | {d['p1']} | {d['p5']} | {d['p25']} | {d['p50']} | "
            f"{d['p75']} | {d['p95']} | {d['p99']}")


def render_md(res: dict[str, Any], witnesses: list[dict[str, Any]]) -> str:  # noqa: C901
    m = res["meta"]
    L: list[str] = []
    L.append("# Whitened identity thresholds — measurement (T1)\n")
    L.append(f"**Generated:** {res['generated_at']} · read-only · "
             "harness `backend/scripts/measure_identity_whitening.py`  ")
    L.append("**Plan:** `docs/superpowers/plans/2026-07-28-identity-whitening.md` (T1) · "
             "**Diagnosis:** `docs/research/recall-229/2026-07-28-identity-layer-raw-cosine.md`  ")
    w = m.get("whitening", {})
    L.append(f"**Whitening:** `{w.get('artifact')}` k={w.get('k')} dim={w.get('dim')} "
             f"fit_n={w.get('fit_n')} fit_at={w.get('fit_at')}\n")
    L.append(f"## VERDICT: **{res['verdict']}**\n")
    if res["verdict"] == "PROCEED":
        L.append("Whitened space separates same-story from different-story centroid pairs at "
                 "all three identity gates: `p5(true) > p95(false)` with a non-empty gap. "
                 "Candidate thresholds (midpoint of the gap):\n")
        L.append("| gate | raw gate today | **whitened tau** | gap width | true kept @tau | "
                 "false rejected @tau | AUC (whitened) | AUC (raw) |")
        L.append("|---|---|---|---|---|---|---|---|")
        for g in ("match", "anchor", "merge"):
            gw, gr = res["gates"][g]["whitened"], res["gates"][g]["raw"]
            L.append(f"| `{g.upper()}_THRESHOLD_W` | {res['raw_gates'][g]} | **{gw['tau']}** | "
                     f"{gw['gap']} | {gw['true_kept_at_tau']} | {gw['false_rejected_at_tau']} | "
                     f"{gw['auc']} | {gr['auc']} |")
    else:
        L.append("At least one gate fails the pre-registered kill rule "
                 "(`p5(true) <= p95(false)` in whitened space). Per-gate verdicts: "
                 + ", ".join(f"**{g}: {v}**" for g, v in res["verdict_by_gate"].items()) + ".\n")
        L.append("| gate | raw gate today | whitened p5(true) | whitened p95(false) | gap | "
                 "AUC (whitened) | AUC (raw) | tau |")
        L.append("|---|---|---|---|---|---|---|---|")
        for g in ("match", "anchor", "merge"):
            gw, gr = res["gates"][g]["whitened"], res["gates"][g]["raw"]
            L.append(f"| `{g}` | {res['raw_gates'][g]} | {gw.get('p5_true')} | "
                     f"{gw.get('p95_false')} | **{gw.get('gap')}** | {gw.get('auc')} | "
                     f"{gr.get('auc')} | {gw.get('tau')} |")
        L.append("")
        L.append("**No thresholds are handed to T2.** Whitening's RANKING separation is strong "
                 "(AUC above) and materially better than raw at every gate — but ranking is not "
                 "what an identity gate needs. A gate is a hard cut, and at the tails the two "
                 "populations overlap: §5 shows label-identical same-snapshot same-country "
                 "fragments scoring ~0.0 whitened while unambiguously different stories score "
                 "0.89-0.92. §6 gives the mechanism.\n")
        L.append("**The collision, in one line.** §3: the absorptions the diagnosis names — an "
                 "unrelated Bolivian/Colombian cluster on a New Zealand anchor — read whitened "
                 "**0.387-0.452**. §7: the 22 clusters of ONE event (the Berlin Pride attack, "
                 "one day, all tagged DE) read whitened **median 0.390, min -0.060**. A cut high "
                 "enough to reject the first rejects most of the second. The two populations do "
                 "not merely overlap — over much of the range they are interleaved.\n")
        L.append("`match` reads PROCEED under v1, and that is an ARTIFACT, not a pass: its only "
                 "TRUE source is `lineage`, i.e. pairs the raw 0.88/0.93 gates already admitted. "
                 "There is no engine-independent same-story set at the running-centroid "
                 "geometry, so `match` is untested here — it must not be read as validated.\n")
    L.append("")
    L.append("**Kill rule (pre-registered, frozen before the run):** if `p5(true) <= p95(false)` "
             "in whitened space the verdict is STOP for that gate. No threshold is tuned after "
             "seeing any downstream outcome — this measurement is upstream of GQ-05.\n")

    L.append("## 1. Pair collection\n")
    L.append(f"Window: last **{m['window_days']} days** · seed `{m['seed']}` · "
             f"{m['clusters_in_window']} clusters ({m['clusters_with_label']} labelled) · "
             f"{m['topics_in_window']} topics · "
             f"{m['cluster_vectors_fetched']} cluster + {m['topic_vectors_fetched']} topic "
             "centroids fetched.\n")
    L.append("| gate | geometry | true pairs | true stories | false pairs | false groups |")
    L.append("|---|---|---|---|---|---|")
    geom = {"match": "cluster ↔ topic running centroid",
            "anchor": "cluster ↔ topic founding anchor (a cluster centroid)",
            "merge": "topic ↔ topic running centroid"}
    for g in ("match", "anchor", "merge"):
        c = res["counts"][g]
        L.append(f"| `{g}` | {geom[g]} | {c['true']} | {c['true_stories']} | "
                 f"{c['false']} | {c['false_stories']} |")
    L.append("")
    L.append("Sources per gate (`truth:source`):\n")
    for g in ("match", "anchor", "merge"):
        srcs = ", ".join(f"`{k}` {v}" for k, v in sorted(res["counts"][g]["by_source"].items()))
        L.append(f"- **{g}** — {srcs}")
    L.append("")
    L.append("Rules (all mechanical, pre-registered — see the harness docstring):\n")
    L.append("- **TRUE `lineage`** — attaches onto a topic whose label court returned "
             "`entailed`, member label non-NULL. *Selection caveat:* these pairs were "
             "admitted BY the raw gates, so the true RAW distribution is truncated below "
             "0.88/0.93. `fragment` carries the engine-independent ground truth.")
    L.append("- **TRUE `fragment`** — same-snapshot clusters with near-identical labels "
             "(SequenceMatcher ≥ 0.80, the engine's own `MERGE_LABEL_MIN`): one event the "
             "engine shredded and never reconverged. Ground truth independent of the gates.")
    L.append("- **TRUE `topic_dup`** — live non-roundup, non-umbrella topics with "
             "near-identical labels: duplicate identities that SHOULD merge.")
    L.append("- **FALSE `false_lineage`** — attaches onto court-FAILED topics where the "
             "absorbed cluster's countries are disjoint from the anchor's AND labels are "
             "dissimilar (ratio < 0.35 and zero shared distinctive tokens). This is the "
             "measured failure mode; the diagnosis's named witnesses fall out of it.")
    L.append("- **FALSE `false_cluster` / `false_match` / `false_merge`** — random picks "
             "under the same disjoint-country + dissimilar-label rule (plus different typed "
             "`category` for `false_merge`), at each gate's own geometry.")
    L.append("- Every rule requires **both labels non-NULL**: during the 07-23→07-27 "
             "DeepSeek-402 blackout `emergent_clusters.label` was 100% NULL, and an "
             "unlabelled cluster cannot be mechanically called a different story.")
    L.append("")

    L.append("## 2. Distributions\n")
    for g in ("match", "anchor", "merge"):
        L.append(f"### `{g}` — {geom[g]}\n")
        L.append("| space | truth | n | p1 | p5 | p25 | p50 | p75 | p95 | p99 |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for space in ("raw", "whitened"):
            f = res["gates"][g][space]
            for truth in ("true", "false"):
                L.append(f"| {space} | {truth} | {_pct_row(f[truth])} |")
        gw, gr = res["gates"][g]["whitened"], res["gates"][g]["raw"]
        L.append("")
        L.append(f"- **raw**: p5(true) {gr.get('p5_true')} vs p95(false) {gr.get('p95_false')} → "
                 f"gap **{gr.get('gap')}** · AUC {gr.get('auc')} · "
                 f"{gr.get('false_above_p5_true')} of false pairs sit above p5(true) · "
                 f"verdict **{gr['verdict']}**")
        L.append(f"- **whitened**: p5(true) {gw.get('p5_true')} vs p95(false) "
                 f"{gw.get('p95_false')} → gap **{gw.get('gap')}** · AUC {gw.get('auc')} · "
                 f"{gw.get('false_above_p5_true')} of false pairs sit above p5(true) · "
                 f"verdict **{gw['verdict']}**")
        L.append("")

    L.append("## 3. Named witnesses (the diagnosis's exhibits)\n")
    L.append("Every member cluster of the named topics against that topic's TRUE founding "
             "anchor (first-ever member, not window-truncated) — `gate=anchor` geometry, i.e. "
             "exactly the 0.93 comparison the engine makes.\n")
    L.append("| topic | day | cc | n | raw | **whitened** | in FALSE set | cluster label |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in witnesses:
        lab = (r["label"] or "*(null)*").replace("|", "/")
        mark = "anchor" if r["is_anchor"] else ("yes" if r["in_false_set"] else "no")
        L.append(f"| {r['topic_id']} | {r['day']} | {','.join(r['cc'][:2])} | {r['n_signals']} | "
                 f"{r['raw_vs_anchor']} | **{r['whitened_vs_anchor']}** | {mark} | {lab[:50]} |")
    L.append("")
    L.append("`in FALSE set` = the row also cleared the conservative mechanical rule "
             "(disjoint countries + dissimilar same-script labels). Rows marked `no` are "
             "still real absorptions — they are simply not counted as evidence here, which "
             "keeps the FALSE distribution free of judgement calls.")
    L.append("")

    L.append("## 4. Sensitivity\n")
    L.append("Whitened tau under alternative pair-set compositions. The primary fit uses the "
             "overmerge exclusion; every variant is reported so the fit's dependence on that "
             "rule is visible.\n")
    L.append("| variant | gate | n true | n false | p5(true) | p95(false) | gap | tau | verdict |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for name, row in res["sensitivity"].items():
        for g in ("match", "anchor", "merge"):
            r = row[g]
            L.append(f"| `{name}` | {g} | {r['n_true']} | {r['n_false']} | {r['p5_true']} | "
                     f"{r['p95_false']} | {r['gap']} | {r['tau']} | {r['verdict']} |")
    L.append("")
    L.append(f"Overmerge exclusion set: **{m['overmerge_demoted_topic_ids']}** topic ids from "
             f"{len(m['overmerge_ledger_files'])} `detect_overmerge` demotion ledger(s).\n")

    L.append("## 5. Tails (contamination audit)\n")
    L.append("The lowest-whitened TRUE pairs and the highest-whitened FALSE pairs per gate. "
             "A same-story pair reported under disjoint countries with disjoint label tokens "
             "would land in the false right tail; a fused blob that passed the court would "
             "land in the true left tail. Read these before trusting the taus.\n")
    for g in ("match", "anchor", "merge"):
        L.append(f"### `{g}` — TRUE left tail (lowest whitened)\n")
        L.append("| whitened | raw | source | A | B |")
        L.append("|---|---|---|---|---|")
        for r in res["tails"][g]["true_left_tail"]:
            L.append(f"| {r['whitened']} | {r['raw']} | `{r['source']}` | "
                     f"{(r['a']['label'] or '—')[:46].replace('|','/')} | "
                     f"{(r['b']['label'] or '—')[:46].replace('|','/')} |")
        L.append("")
        L.append(f"### `{g}` — FALSE right tail (highest whitened)\n")
        L.append("| whitened | raw | source | A | B |")
        L.append("|---|---|---|---|---|")
        for r in res["tails"][g]["false_right_tail"]:
            L.append(f"| {r['whitened']} | {r['raw']} | `{r['source']}` | "
                     f"{(r['a']['label'] or '—')[:46].replace('|','/')} | "
                     f"{(r['b']['label'] or '—')[:46].replace('|','/')} |")
        L.append("")

    L.append("## 6. Is whitened cosine measuring STORY or LANGUAGE?\n")
    L.append("Whitened cosine, split by whether the two sides share a dominant language key "
             "(`signals_v2.source_lang` where known — ~45% — else the dominant Unicode script "
             "of the headlines). If whitening were a story detector, TRUE pairs would score "
             "high in both columns.\n")
    L.append("| gate | truth | relation | n | whitened p5 | p50 | p95 | raw p50 |")
    L.append("|---|---|---|---|---|---|---|---|")
    for g in ("match", "anchor", "merge"):
        for truth in ("true", "false"):
            for rel in ("same_lang", "cross_lang"):
                d = res["language_effect"][g][f"{truth}/{rel}"]
                wd, rd = d["whitened"], d["raw"]
                if not wd.get("n"):
                    continue
                L.append(f"| {g} | {truth} | {rel} | {wd['n']} | {wd['p5']} | {wd['p50']} | "
                         f"{wd['p95']} | {rd['p50']} |")
    L.append("")
    L.append(f"Pair language coverage: {res['language_coverage']}\n")
    L.append("**Limitation (biases the effect DOWNWARD):** Latin-script rows whose `source_lang` "
             "is unknown all collapse to `script:latin`, so Romanian-vs-English counts as "
             "*same* language. The measured cross-language penalty is therefore a lower bound.\n")

    if res.get("family_probes"):
        L.append("## 7. Shredded-event families (the primary metric's own exhibits)\n")
        L.append("Every pair inside a family is the SAME event by construction. This is the "
                 "direct read on whether whitened space can RECONVERGE a shredded story.\n")
        L.append("| family | day | clusters | pairs | countries | raw min/p50/max | "
                 "**whitened min/p50/max** |")
        L.append("|---|---|---|---|---|---|---|")
        for f in res["family_probes"]:
            r, w = f["raw"], f["whitened"]
            L.append(f"| `%{f['pattern']}%` | {f['day']} | {f['n_clusters']} | {f['n_pairs']} | "
                     f"{','.join(f['countries'][:5])} | {r['min']}/{r['p50']}/{r['max']} | "
                     f"**{w['min']}/{w['p50']}/{w['max']}** |")
        L.append("")

    L.append("## 8. Construction v0 vs v1\n")
    L.append("v0 = the first pass; v1 repairs the four ground-truth defects its tail audit "
             "exposed (D1-D4, see the harness docstring). Verdicts under both:\n")
    L.append("| construction | match | anchor | merge | overall |")
    L.append("|---|---|---|---|---|")
    for name, c in res["constructions"].items():
        vb = c["verdict_by_gate"]
        L.append(f"| `{name}` | {vb['match']} | {vb['anchor']} | {vb['merge']} | "
                 f"**{c['verdict']}** |")
    L.append("")
    L.append("v1's D3 (a TRUE fragment pair must share a country) drops exactly the "
             "cross-country/cross-language fragments that whitening scores LOWEST, so v1's true "
             "set is biased in whitening's FAVOUR. The STOP survives that bias.\n")

    L.append("## 9. Honest limits\n")
    L.append("- The TRUE `lineage` set is engine-selected (admitted by the raw gates); its raw "
             "distribution is truncated from below and must not be read as \"raw works\". The "
             "`fragment_only` sensitivity row is the engine-independent read.")
    L.append("- The FALSE rules can misfile a genuinely-shared story told with disjoint "
             "vocabulary in disjoint countries. That error is CONSERVATIVE — it raises "
             "p95(false) and narrows the gap — so a PROCEED verdict survives it. The false "
             "right tail above is the audit surface for it.")
    L.append("- `topic_dup` true-merge pairs are duplicate LABELS, not adjudicated duplicates; "
             "a recurring label form (\"X Presidential Election\") across genuinely different "
             "events would contaminate them. Within a short window this is unlikely but not "
             "impossible.")
    L.append("- Blocking (≥2 shared distinctive tokens, token doc-freq ≤ 5% of the block, "
             "blocks >400 members skipped) bounds RECALL of the same-event search; it does not "
             "affect precision, and the pairs it finds are a fair sample of same-event pairs.")
    L.append("- Percentile estimates carry sampling error; the reported gap should be read "
             "with the n column beside it, not as an exact constant.")
    L.append("- The §6 language split resolves only pairs whose sample signals still exist in "
             "`signals_v2` (7-day hot retention), so it covers a recent subset of the pairs; the "
             "`unknown` bucket in the coverage line is that retention gap, not a failure of the "
             "rule.")
    L.append("- `different_story` requires SequenceMatcher < 0.35 on the whole label string. Two "
             "unrelated English labels often score above that by character coincidence, so the "
             "FALSE sets are smaller than the true rate of different-story pairs. Conservative: "
             "it can only shrink evidence, never manufacture it (§3 shows real absorptions "
             "marked `no`).")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ entry
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Measure raw vs whitened separation at the identity layer and fit taus "
                    "(read-only; writes no prod table).")
    ap.add_argument("--days", type=int, default=21, help="snapshot window (default 21)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-lineage-topics", type=int, default=500)
    ap.add_argument("--max-fragment", type=int, default=3000)
    ap.add_argument("--max-false-cluster", type=int, default=1500)
    ap.add_argument("--max-false-match", type=int, default=1500)
    ap.add_argument("--max-false-merge", type=int, default=1500)
    ap.add_argument("--witness-topics", default="784,52",
                    help="comma ids from the diagnosis, tagged `witness` in the artifact")
    ap.add_argument("--family-probe", default="caspian,iran%ukrain,berlin pride,espriella",
                    help="comma label substrings whose same-event families get a "
                         "pairwise raw/whitened spread readout (the shredding exhibits)")
    ap.add_argument("--out-dir", default=str(ARTIFACT_DIR))
    ap.add_argument("--stem", default=ARTIFACT_STEM)
    ap.add_argument("--no-artifacts", action="store_true",
                    help="print the summary only; do not write the .md/.json artifacts")
    a = ap.parse_args()
    a.witness_topics = {int(x) for x in str(a.witness_topics).split(",") if x.strip()}
    a.family_probe = [x.strip() for x in str(a.family_probe).split(",") if x.strip()]
    return a


async def run(args: argparse.Namespace) -> int:
    import asyncpg

    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("DATABASE_URL required", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(url, timeout=30)
    built: dict[str, tuple[list[Pair], dict[str, Any]]] = {}
    try:
        await conn.execute("SET default_transaction_read_only = on")
        cache: dict[str, Any] = {}
        for name in ("v0", "v1"):
            built[name] = await build_pairs(conn, args, Rules(name), cache)
        families = await family_probes(conn, args.family_probe)
        in_false = {(p.b_id, p.a_id) for p in built["v1"][0]
                    if p.truth == "false" and p.b_kind == "topic_anchor"}
        witnesses = await witness_probe(conn, sorted(args.witness_topics), in_false)
    finally:
        await conn.close()

    if not built["v1"][0]:
        print("no pairs collected — widen --days or check the corpus", file=sys.stderr)
        return 2

    constructions = {n: analyse(p, m) for n, (p, m) in built.items()}
    pairs, _ = built["v1"]
    res = dict(constructions["v1"])
    res["constructions"] = {
        n: {k: c[k] for k in ("verdict", "verdict_by_gate", "taus", "counts", "gates")}
        for n, c in constructions.items()
    }
    res["family_probes"] = families
    res["witnesses"] = witnesses
    wit = witnesses
    res["pairs"] = [p.as_dict() for p in pairs]

    print(json.dumps({"verdict (v1)": res["verdict"],
                      "verdict_by_gate (v1)": res["verdict_by_gate"],
                      "taus (v1)": res["taus"],
                      "verdict (v0)": constructions["v0"]["verdict"],
                      "counts (v1)": res["counts"]},
                     indent=2, ensure_ascii=False))

    if not args.no_artifacts:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{args.stem}.json").write_text(
            json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / f"{args.stem}.md").write_text(render_md(res, wit), encoding="utf-8")
        print(f"\nartifacts -> {out / (args.stem + '.md')}\n"
              f"             {out / (args.stem + '.json')}", file=sys.stderr)
    return 0 if res["verdict"] == "PROCEED" else 1


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
