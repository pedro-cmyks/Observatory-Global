#!/usr/bin/env python3
"""M3 — rarity calibration for the evidence-overlap identity gate (read-only).

WHY (spec `docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md`
§3.1, §3.4, §10; plan T-A2). The design scores same-story evidence as

    strength = max( w_E · max_norm_rarity(shared entities),
                    w_U · locator_score,
                    w_H · max_norm_rarity(shared headline keys) )

with `norm_rarity(df, df_max) = (1/df − 1/df_max) / (1 − 1/df_max)` reused
verbatim from `app/services/constellation_walk.py:461` (#234). Three inputs to
that formula are UNMEASURED and are guessed nowhere else:

  1. `df_max` per lane. The formula's denominator is a property of the night's
     field. `entity_dfs` is FROZEN into the fingerprint at build time (spec
     §3.2), so a df_max that swings night to night silently re-scales every
     stored rarity. This script measures the df distribution per lane over N
     snapshots and proposes a df_max per lane WITH its sensitivity.
  2. The `nlp_persons` NOISE FLOOR. §2.5 sampled garbage like
     `{"name":"sustraer L.190","type":"PERSON"}`. Garbage is overwhelmingly
     df=1, i.e. it lands at norm_rarity 1.0 — the MAXIMUM weight. If the df=1
     stratum is mostly junk, df=1 must not be admissible evidence.
  3. Whether lane U's DOMAIN half discriminates at all (spec §10 Q1). Two
     clusters both carrying a Reuters item prove nothing; the design says
     "delete it rather than leave it decorative".

WHAT THIS DOES (read-only; `SET default_transaction_read_only = on`; writes
NOTHING to any prod table):
  * rebuilds the three evidence lanes per cluster from `sample_signal_ids` →
    `signals_v2`, for each of the last `--days` snapshot days;
  * reports df distributions, df_max volatility and df_max sensitivity per lane;
  * emits a deterministic sample of `--noise-sample` df=1 entities for labeling,
    and — given `--labels` — the measured garbage rate, cut by provenance;
  * measures every lane's TRUE-vs-FALSE discrimination on the witness families
    (Caspian, Berlin Pride) against a mechanical FALSE construction, which is
    what answers Q1 and seeds `w_E/w_U/w_H`.

DOCUMENT UNIT FOR df
--------------------
df(item) = the number of CLUSTERS in that snapshot whose fingerprint contains
the item. Not signals. The fingerprint is compared cluster-to-cluster, so the
document that df must count is the cluster. (This also reproduces the spec's
§2.3 numbers: 31,197 distinct entities / df_max 383 over 07-28.)

FALSE CONSTRUCTION
------------------
Reused verbatim from `scripts/measure_identity_whitening.py` (construction v1):
disjoint non-empty country sets AND `different_story` labels (SequenceMatcher
< 0.35, zero shared distinctive tokens, same dominant script). Importing rather
than re-deriving is deliberate — M1/M2/M3 must share ONE definition of "false"
or their tables cannot be read together (plan: "no operating point chosen on
recall without its false-side number beside it").

HONEST LIMITS (also carried into the artifact, do not drop them)
  * Cross-day snapshots are measured on a DECAYING view: `sample_signal_ids`
    resolvability falls 97.5% → 16.4% over 7 days (spec §2.4). df measured on a
    partially-resolvable snapshot is biased LOW. The primary snapshot (latest,
    ~97.5%) is the one the proposals are anchored on; the older days are the
    volatility check, and their resolvability is printed beside every number.
  * The noise-floor labels are MODEL-LABELED, SINGLE RATER. Every labeled item
    ships in the .json with its verdict so a human can re-check.
  * Lane H's normalizer (`thread_ranking._norm_headline`) folds through
    `normalize_search_text`, whose `[^a-z0-9]` class empties every non-Latin
    headline. Lane H is Latin-only BY CONSTRUCTION; measured here, not assumed.

Usage (M1 mlvenv has numpy):
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend && /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.calibrate_evidence_rarity --days 7

  # first pass: emit the df=1 sample for labeling, then re-run with --labels
  ... --dump-sample-only
  ... --labels docs/research/recall-229/2026-07-30-df1-entity-labels.json

Exit code: 0 ok, 2 = no data / no DSN.
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
from itertools import combinations
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import urlsplit

import numpy as np

try:  # module-run from backend/ or repo root
    from app.services.thread_ranking import _norm_headline
    from app.services.constellation_walk import norm_rarity
except ImportError:  # pragma: no cover
    from backend.app.services.thread_ranking import _norm_headline
    from backend.app.services.constellation_walk import norm_rarity

# ONE definition of "different story" across M1/M2/M3 — see module docstring.
try:
    from scripts.measure_identity_whitening import (
        auc, countries_disjoint, describe, different_story, label_sim,
    )
except ImportError:  # pragma: no cover
    from backend.scripts.measure_identity_whitening import (  # type: ignore
        auc, countries_disjoint, describe, different_story, label_sim,
    )

# ------------------------------------------------------------------ constants
REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
ARTIFACT_STEM = "2026-07-30-evidence-rarity-calibration"
SAMPLE_STEM = "2026-07-30-df1-entity-sample"

# `headline_clean` is lane H with the hygiene rule applied — carried as its own
# lane so the cost/benefit of the rule is visible rather than asserted.
LANES = ("entity", "domain", "url", "headline", "headline_clean")

# df_max candidates swept for the sensitivity table. `observed` is added per lane
# at runtime. Round constants are the alternative to a volatile observed max.
DF_MAX_CANDIDATES = (50, 100, 200, 383, 500, 1000, 2000)
# df values whose norm_rarity is reported across those candidates.
DF_PROBES = (1, 2, 3, 5, 10, 25, 100)

DF_BUCKETS = ((1, 1), (2, 2), (3, 3), (4, 5), (6, 10), (11, 20),
              (21, 50), (51, 100), (101, 10**9))

# Rare-domain sweep for the lane-U question (spec §3.4: "only exact-URL and
# low-df domains count"). Each value = "a shared domain counts only if its df is
# at most this".
DOMAIN_DF_GATES = (1, 2, 3, 5, 10, 20, 50, 10**9)

PCTS = (50, 90, 95, 99)

# Lane-H hygiene: minimum usable key length (see `headline_key_usable`).
HEADLINE_KEY_MIN_CHARS = 8

# Registrable-domain heuristic: second-level suffixes that are NOT the
# registrable label. Approximation of the public suffix list, stated as such.
_SLD_PREFIXES = {
    "co", "com", "net", "org", "gov", "edu", "ac", "or", "ne", "go", "mil",
    "ind", "gen", "nic", "res", "web", "info", "biz", "sch", "in",
}
_TRACKING_PARAM = re.compile(r"(^|&)(utm_[^=]*|fbclid|gclid|igshid|ref|amp)=[^&]*", re.I)


# ------------------------------------------------------------------ normalizers
def norm_entity(s: str | None) -> str:
    """Lowercase + strip combining marks + collapse punctuation, SCRIPT-PRESERVING.

    Deliberately NOT `normalize_search_text`: its `[^a-z0-9]` class maps every
    Arabic/Cyrillic/CJK entity to the empty string, which would delete exactly
    the lanes §2.2 says are already thin. Keeps any-script word characters.

    This is also the union point between the two entity sources: GDELT
    `persons[]` arrives pre-lowercased ("warde manuel") while `nlp_persons`
    arrives cased ("Warde Manuel"); without this fold they are two entities.
    """
    if not s:
        return ""
    x = unicodedata.normalize("NFKD", str(s))
    x = "".join(ch for ch in x if not unicodedata.combining(ch))
    x = x.lower()
    x = re.sub(r"[^\w\s]+", " ", x, flags=re.UNICODE)
    return re.sub(r"\s+", " ", x).strip()


def registrable_domain(url: str | None, source_name: str | None = None) -> str:
    """Host reduced to its registrable label, with `www.` dropped.

    HEURISTIC, not a public-suffix-list lookup: a 2-letter TLD preceded by a
    known second-level prefix (`co.uk`, `com.au`, `com.br`) keeps three labels,
    everything else keeps two. Errors here merge or split a handful of outlets;
    they cannot manufacture a cross-story link because the domain still has to
    be SHARED and (per the lane-U rule) RARE.
    """
    host = ""
    if url:
        try:
            host = (urlsplit(url).hostname or "").lower()
        except ValueError:
            host = ""
    if not host and source_name:
        host = str(source_name).strip().lower()
    host = host.strip(".")
    if not host:
        return ""
    if host.startswith("www."):
        host = host[4:]
    parts = [p for p in host.split(".") if p]
    if len(parts) <= 2:
        return ".".join(parts)
    if len(parts[-1]) == 2 and parts[-2] in _SLD_PREFIXES:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def norm_url(url: str | None) -> str:
    """Exact-locator key: scheme-blind, host-lowered, tracking params dropped,
    trailing slash removed. Two mastheads that republish the SAME link are the
    same locator; a masthead that rewrote the URL is lane H's problem."""
    if not url:
        return ""
    try:
        sp = urlsplit(str(url).strip())
    except ValueError:
        return ""
    host = (sp.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (sp.path or "").rstrip("/")
    query = _TRACKING_PARAM.sub("", sp.query or "").strip("&")
    if not host and not path:
        return ""
    return f"{host}{path}" + (f"?{query}" if query else "")


def headline_key(text: str | None) -> str:
    """`thread_ranking._norm_headline` verbatim — ONE definition of 'one
    headline' shared with syndication detection (spec §3.1).

    Verbatim includes its failure mode, which this script measures rather than
    patches: the normalizer's `[^a-z0-9]` class deletes every non-Latin
    character, so a non-Latin headline does NOT reduce to the empty string —
    it reduces to WHATEVER DIGITS IT CONTAINED. Measured live:
        '27 липня 2026 року — яке сьогодні свято'  -> '27 2026'
        'Атака РФ по АТБ у Чернігові 26 липня'     -> '26'
        'انفجار في كييف 2026'                       -> '2026'
    See `headline_key_usable` for the hygiene rule this forces.
    """
    if not text:
        return ""
    try:
        return _norm_headline(str(text))
    except Exception:  # pragma: no cover - normalizer is total in practice
        return ""


def headline_key_usable(key: str) -> bool:
    """Is a headline key admissible as same-story EVIDENCE?

    A key with no alphabetic character is date/number residue left behind after
    the normalizer deleted a non-Latin headline (see `headline_key`). Two such
    keys matching proves that two headlines mentioned the same number — and
    because a residue like `26` can be rare in a given night, the rarity
    weighting would hand it norm_rarity ≈ 1.0, the MAXIMUM. That is a
    false-merge generator aimed squarely at the ru/uk/ar/CJK corpus.
    """
    if len(key) < HEADLINE_KEY_MIN_CHARS:
        return False
    return any(ch.isalpha() for ch in key)


def headline_key_is_outlet_residue(key: str, domain: str) -> bool:
    """Is a surviving key nothing but the OUTLET's own name?

    The second face of the same normalizer defect: when the masthead stamp is
    not the last `|` segment (it is first, or joined by a dash), the Latin
    outlet name is the only text that survives deletion of a non-Latin headline.
    Measured top `headline_clean` keys on 2026-07-28 are exactly that —
    `blackseanews`, `patrisnews`, `dsnews ua`. Such a key makes any two stories
    from that outlet look like one story, which is the DOMAIN lane wearing lane
    H's clothes — and worse, without the domain lane's df ceiling.
    """
    if not key or not domain:
        return False
    k = key.replace(" ", "")
    d = re.sub(r"[^a-z0-9]", "", domain.lower())
    return bool(k) and bool(d) and (k in d or d.startswith(k))


def entity_items(row: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(normalized, raw, provenance) for every entity on one signal.

    provenance ∈ {gdelt_persons, gdelt_orgs, nlp:<TYPE>} — kept because the
    noise-floor recommendation is only actionable if it can be scoped to the
    source that is actually noisy.
    """
    out: list[tuple[str, str, str]] = []
    for raw in (row.get("persons") or []):
        n = norm_entity(raw)
        if n:
            out.append((n, str(raw), "gdelt_persons"))
    for raw in (row.get("organizations") or []):
        n = norm_entity(raw)
        if n:
            out.append((n, str(raw), "gdelt_orgs"))
    nlp = row.get("nlp_persons")
    if isinstance(nlp, str):
        try:
            nlp = json.loads(nlp)
        except (ValueError, TypeError):
            nlp = None
    if isinstance(nlp, list):
        for ent in nlp:
            if not isinstance(ent, dict):
                continue
            raw = ent.get("name")
            n = norm_entity(raw)
            if n:
                out.append((n, str(raw), f"nlp:{ent.get('type') or 'UNKNOWN'}"))
    return out


# ------------------------------------------------------------------ data model
class ClusterEvidence:
    """One cluster's three lanes, plus the provenance the noise sample needs."""

    __slots__ = ("cid", "label", "countries", "n_refs", "n_resolved",
                 "entity", "domain", "url", "headline", "headline_clean", "langs")

    def __init__(self, cid: int, label: str | None, countries: Sequence[str] | None,
                 n_refs: int):
        self.cid = cid
        self.label = label
        self.countries = list(countries or [])
        self.n_refs = n_refs
        self.n_resolved = 0
        self.entity: set[str] = set()
        self.domain: set[str] = set()
        self.url: set[str] = set()
        self.headline: set[str] = set()
        self.headline_clean: set[str] = set()
        self.langs: Counter = Counter()

    def lane(self, name: str) -> set[str]:
        return getattr(self, name)


class SnapshotEvidence:
    """Every cluster of one snapshot day + the per-lane df tables."""

    def __init__(self, day: str, snapshot_at: str):
        self.day = day
        self.snapshot_at = snapshot_at
        self.clusters: dict[int, ClusterEvidence] = {}
        self.df: dict[str, Counter] = {ln: Counter() for ln in LANES}
        self.n_refs = 0
        self.n_resolved = 0
        self.lang_counts: Counter = Counter()
        self.lang_headline_empty: Counter = Counter()
        self.lang_headline_residue: Counter = Counter()  # key exists but is unusable
        self.n_outlet_residue = 0   # key survives hygiene but IS the outlet's name
        self.n_labeled_clusters = 0

    def finalize(self) -> None:
        for ce in self.clusters.values():
            for ln in LANES:
                for item in ce.lane(ln):
                    self.df[ln][item] += 1

    @property
    def resolvability(self) -> float:
        return (self.n_resolved / self.n_refs) if self.n_refs else 0.0

    def df_max(self, lane: str) -> int:
        c = self.df[lane]
        return max(c.values()) if c else 1

    @property
    def label_null_share(self) -> float:
        n = len(self.clusters)
        return (n - self.n_labeled_clusters) / n if n else 0.0


# ------------------------------------------------------------------ collection
async def load_snapshot(conn, day: str, chunk: int) -> SnapshotEvidence:
    rows = await conn.fetch(
        """
        SELECT id, label, top_country_codes, sample_signal_ids,
               snapshot_at
          FROM emergent_clusters
         WHERE snapshot_at::date = $1::text::date
        """,
        day,
    )
    snap = SnapshotEvidence(day, str(rows[0]["snapshot_at"]) if rows else day)
    ref_to_clusters: dict[int, list[int]] = defaultdict(list)
    for r in rows:
        sids = [int(s) for s in (r["sample_signal_ids"] or [])]
        ce = ClusterEvidence(int(r["id"]), r["label"], r["top_country_codes"], len(sids))
        snap.clusters[ce.cid] = ce
        if r["label"]:
            snap.n_labeled_clusters += 1
        for sid in sids:
            ref_to_clusters[sid].append(ce.cid)
        snap.n_refs += len(sids)

    ids = sorted(ref_to_clusters)
    for i in range(0, len(ids), chunk):
        batch = ids[i:i + chunk]
        sig = await conn.fetch(
            """
            SELECT id, headline, source_url, source_name, source_lang,
                   persons, organizations, nlp_persons
              FROM signals_v2
             WHERE id = ANY($1::bigint[])
            """,
            batch,
        )
        for s in sig:
            row = dict(s)
            sid = int(row["id"])
            ents = {n for n, _raw, _p in entity_items(row)}
            dom = registrable_domain(row.get("source_url"), row.get("source_name"))
            uk = norm_url(row.get("source_url"))
            hk = headline_key(row.get("headline"))
            lang = (row.get("source_lang") or "??").strip() or "??"
            hk_ok = bool(hk) and headline_key_usable(hk)
            snap.lang_counts[lang] += 1
            if not hk:
                snap.lang_headline_empty[lang] += 1
            elif not hk_ok:
                snap.lang_headline_residue[lang] += 1
            elif headline_key_is_outlet_residue(hk, dom):
                snap.n_outlet_residue += 1
            for cid in ref_to_clusters.get(sid, ()):
                ce = snap.clusters[cid]
                ce.n_resolved += 1
                ce.langs[lang] += 1
                ce.entity |= ents
                if dom:
                    ce.domain.add(dom)
                if uk:
                    ce.url.add(uk)
                if hk:
                    ce.headline.add(hk)
                if hk_ok:
                    ce.headline_clean.add(hk)
                snap.n_resolved += 1
    snap.finalize()
    return snap


async def sample_entity_provenance(conn, snap: SnapshotEvidence, names: set[str],
                                   chunk: int) -> dict[str, dict[str, Any]]:
    """Re-walk the primary snapshot's signals to attach, for each sampled
    entity name, its raw spellings, provenance counts and one example headline.
    Two passes rather than one fat in-memory index: the index would be ~4M
    tuples for a benefit only the 200-item sample needs."""
    rows = await conn.fetch(
        "SELECT sample_signal_ids FROM emergent_clusters WHERE snapshot_at::date = $1::text::date",
        snap.day,
    )
    ids = sorted({int(s) for r in rows for s in (r["sample_signal_ids"] or [])})
    out: dict[str, dict[str, Any]] = {
        n: {"name": n, "raw_variants": Counter(), "provenance": Counter(),
            "example_headline": None, "example_lang": None, "example_source": None}
        for n in names
    }
    for i in range(0, len(ids), chunk):
        sig = await conn.fetch(
            """SELECT id, headline, source_name, source_lang, persons,
                      organizations, nlp_persons
                 FROM signals_v2 WHERE id = ANY($1::bigint[])""",
            ids[i:i + chunk],
        )
        for s in sig:
            row = dict(s)
            for n, raw, prov in entity_items(row):
                rec = out.get(n)
                if rec is None:
                    continue
                rec["raw_variants"][raw] += 1
                rec["provenance"][prov] += 1
                if rec["example_headline"] is None:
                    rec["example_headline"] = row.get("headline")
                    rec["example_lang"] = row.get("source_lang")
                    rec["example_source"] = row.get("source_name")
    for rec in out.values():
        rec["raw_variants"] = [w for w, _ in rec["raw_variants"].most_common(4)]
        rec["provenance"] = dict(rec["provenance"].most_common())
    return out


# ------------------------------------------------------------------ df analysis
def df_profile(snap: SnapshotEvidence, lane: str) -> dict[str, Any]:
    c = snap.df[lane]
    if not c:
        return {"lane": lane, "distinct": 0, "clusters_with_item": 0}
    vals = np.asarray(list(c.values()), dtype=np.float64)
    buckets = {}
    for lo, hi in DF_BUCKETS:
        key = f"{lo}" if lo == hi else (f"{lo}+" if hi >= 10**9 else f"{lo}-{hi}")
        buckets[key] = int(np.sum((vals >= lo) & (vals <= hi)))
    n_with = sum(1 for ce in snap.clusters.values() if ce.lane(lane))
    per_cluster = [len(ce.lane(lane)) for ce in snap.clusters.values()]
    out: dict[str, Any] = {
        "lane": lane,
        "distinct": int(vals.size),
        "df_max": int(vals.max()),
        "df_mean": round(float(vals.mean()), 4),
        "share_df1": round(float(np.mean(vals == 1)), 4),
        "share_df_le2": round(float(np.mean(vals <= 2)), 4),
        "buckets": buckets,
        "clusters_total": len(snap.clusters),
        "clusters_with_item": n_with,
        "cluster_coverage": round(n_with / max(1, len(snap.clusters)), 4),
        "items_per_cluster_mean": round(float(np.mean(per_cluster)) if per_cluster else 0.0, 3),
        "items_per_cluster_p50": int(np.percentile(per_cluster, 50)) if per_cluster else 0,
    }
    for p in PCTS:
        out[f"df_p{p}"] = round(float(np.percentile(vals, p)), 3)
    top = c.most_common(12)
    out["top_items"] = [{"item": k, "df": v} for k, v in top]
    return out


def df_max_sensitivity(observed: int) -> dict[str, Any]:
    """How much `norm_rarity` moves across candidate `df_max` values.

    The point of the table: `df_max` sits in the DENOMINATOR of a quantity that
    is frozen into every fingerprint. If the answer is 'barely moves', the right
    call is a FIXED constant (stable across nights) rather than the observed max
    (which one ubiquitous entity can swing)."""
    cands = sorted({int(observed), *DF_MAX_CANDIDATES})
    rows = []
    for dfp in DF_PROBES:
        row = {"df": dfp}
        for cand in cands:
            row[str(cand)] = round(norm_rarity(dfp, cand), 4)
        vals = [row[str(c)] for c in cands]
        row["spread"] = round(max(vals) - min(vals), 4)
        rows.append(row)
    return {"observed_df_max": int(observed), "candidates": cands, "rows": rows}


# ------------------------------------------------------------------ lane scores
def lane_score(a: ClusterEvidence, b: ClusterEvidence, lane: str,
               df: Counter, df_max: int, *, df_gate: int = 10**9) -> tuple[float, list[str]]:
    """max norm_rarity over the shared items of one lane, with an optional df
    ceiling (the lane-U 'only low-df domains count' rule). Returns the score and
    the shared items, rarest first — the receipt the ledger will carry."""
    shared = [it for it in (a.lane(lane) & b.lane(lane)) if df.get(it, 1) <= df_gate]
    if not shared:
        return 0.0, []
    scored = sorted(((norm_rarity(df.get(it, 1), df_max), it) for it in shared),
                    key=lambda t: -t[0])
    return float(scored[0][0]), [it for _s, it in scored[:5]]


# ------------------------------------------------------------------ false pairs
def build_false_pairs(snap: SnapshotEvidence, limit: int, seed: int,
                      exclude: set[int]) -> list[tuple[ClusterEvidence, ClusterEvidence]]:
    """Mechanical FALSE construction, identical to the whitened-taus harness's
    v1 rule: disjoint non-empty countries AND `different_story` labels."""
    rng = random.Random(seed)
    pool = [ce for ce in snap.clusters.values()
            if ce.cid not in exclude and ce.label and ce.countries and ce.n_resolved > 0]
    rng.shuffle(pool)
    out: list[tuple[ClusterEvidence, ClusterEvidence]] = []
    tries = 0
    max_tries = limit * 400
    while len(out) < limit and tries < max_tries and len(pool) >= 2:
        tries += 1
        a, b = rng.sample(pool, 2)
        if not countries_disjoint(a.countries, b.countries):
            continue
        if not different_story(a.label, b.label, require_same_script=True):
            continue
        out.append((a, b))
    return out


def build_family_pairs(snap: SnapshotEvidence, cids: Sequence[int],
                       ) -> list[tuple[ClusterEvidence, ClusterEvidence]]:
    members = [snap.clusters[c] for c in cids if c in snap.clusters]
    return [(a, b) for a, b in combinations(members, 2)
            if a.n_resolved > 0 and b.n_resolved > 0]


# --------------------------------------------------------- cross-day (DP-2 shape)
def xday_score(a: ClusterEvidence, b: ClusterEvidence, lane: str,
               df_a: Counter, df_b: Counter, df_max: int) -> float:
    """Cross-snapshot lane score. Each side's fingerprint carries its OWN frozen
    df (spec §3.2), so a shared item has two rarities; this takes `max(df)` —
    the LESS rare reading — so a cross-day link is never credited with a rarity
    only one night believed in."""
    shared = a.lane(lane) & b.lane(lane)
    if not shared:
        return 0.0
    return max(norm_rarity(max(df_a.get(it, 1), df_b.get(it, 1)), df_max)
               for it in shared)


def build_xday_pairs(new: SnapshotEvidence, old: SnapshotEvidence, limit: int,
                     seed: int) -> tuple[list[tuple], list[tuple]]:
    """TRUE = a cluster tonight and a cluster last night that are the same story
    by the engine's own MERGE label rule (SequenceMatcher ≥ 0.80) AND share a
    country — the v1 `fragment` rule, applied across the day boundary. FALSE =
    the same mechanical disjoint-country / different-label construction.

    This is the DP-2 / cross-day GEOMETRY, which same-snapshot pairs cannot
    exhibit: within one snapshot `sample_signal_ids` PARTITION the corpus, so
    two clusters can never contain the same signal."""
    rng = random.Random(seed + 1)
    new_pool = [c for c in new.clusters.values() if c.label and c.n_resolved > 0]
    old_pool = [c for c in old.clusters.values() if c.label and c.n_resolved > 0]
    true_pairs: list[tuple] = []
    for a in new_pool:
        if len(true_pairs) >= limit:
            break
        for b in old_pool:
            if not (set(a.countries) & set(b.countries)):
                continue
            if label_sim(a.label, b.label) >= 0.80:
                true_pairs.append((a, b))
                break
    false_pairs: list[tuple] = []
    tries = 0
    while len(false_pairs) < limit and tries < limit * 400 and new_pool and old_pool:
        tries += 1
        a, b = rng.choice(new_pool), rng.choice(old_pool)
        if not countries_disjoint(a.countries, b.countries):
            continue
        if not different_story(a.label, b.label, require_same_script=True):
            continue
        false_pairs.append((a, b))
    return true_pairs, false_pairs


async def structural_checks(conn, primary: str, prior: str | None) -> dict[str, Any]:
    """The facts that decide whether a lane CAN fire at all, as opposed to how
    often it does. Cheap SQL; run once.

    Two of them are load-bearing for lane U: whether `sample_signal_ids`
    partition a snapshot (if they do, no signal is in two clusters), and whether
    `signals_v2` carries duplicate `source_url` values (if it does not, two
    clusters cannot share a URL even in principle)."""
    row = await conn.fetchrow(
        """WITH x AS (SELECT unnest(sample_signal_ids) sid FROM emergent_clusters
                       WHERE snapshot_at::date = $1::text::date)
           SELECT count(*) total, count(DISTINCT sid) distinct_ids FROM x""", primary)
    dup = await conn.fetchrow(
        """WITH d AS (SELECT source_url FROM signals_v2
                       WHERE source_url IS NOT NULL AND source_url <> ''
                       GROUP BY 1 HAVING count(*) > 1)
           SELECT count(*) n FROM d""")
    rows_with_url = await conn.fetchval(
        "SELECT count(*) FROM signals_v2 WHERE source_url IS NOT NULL AND source_url <> ''")
    xday = 0
    if prior:
        xday = await conn.fetchval(
            """WITH a AS (SELECT DISTINCT unnest(sample_signal_ids) sid
                            FROM emergent_clusters WHERE snapshot_at::date = $1::text::date),
                    b AS (SELECT DISTINCT unnest(sample_signal_ids) sid
                            FROM emergent_clusters WHERE snapshot_at::date = $2::text::date)
               SELECT count(*) FROM a JOIN b USING (sid)""", primary, prior) or 0
    windows = [int(r["w"]) for r in await conn.fetch(
        """SELECT DISTINCT snapshot_window_h w FROM emergent_clusters
            WHERE snapshot_at::date = $1::text::date AND snapshot_window_h IS NOT NULL""",
        primary)]
    total = int(row["total"] or 0)
    return {
        "primary_day": primary, "prior_day": prior,
        "sample_refs": total,
        "distinct_refs": int(row["distinct_ids"] or 0),
        "sample_refs_are_disjoint": total == int(row["distinct_ids"] or 0),
        "duplicate_source_urls": int(dup["n"] or 0),
        "rows_with_url": int(rows_with_url or 0),
        "snapshot_window_h": windows,
        "xday_shared_signals": int(xday),
        "xday_share": round(xday / total, 4) if total else 0.0,
    }


async def find_families(conn, day: str, probes: Sequence[str]) -> dict[str, list[int]]:
    fams: dict[str, list[int]] = {}
    for probe in probes:
        name, _, patterns = probe.partition("=")
        pats = [p for p in (patterns or name).split("|") if p]
        seen: list[int] = []
        for pat in pats:
            rows = await conn.fetch(
                """SELECT id FROM emergent_clusters
                    WHERE snapshot_at::date = $1::text::date
                      AND lower(label) LIKE $2 ORDER BY id""",
                day, f"%{pat.strip().lower()}%",
            )
            for r in rows:
                if int(r["id"]) not in seen:
                    seen.append(int(r["id"]))
        fams[name.strip()] = seen
    return fams


# ------------------------------------------------------------ lane-U discrimination
def domain_gate_sweep(true_pairs, false_pairs, snap: SnapshotEvidence,
                      df_max: int) -> list[dict[str, Any]]:
    """Q1 (spec §10): does the DOMAIN half of lane U discriminate at all?

    Reads a shared domain as evidence only when its df is at most the gate, and
    reports the true/false fire rates side by side. A gate whose false rate
    tracks its true rate is measuring syndication infrastructure, not identity.
    """
    rows = []
    for gate in DOMAIN_DF_GATES:
        t = sum(1 for a, b in true_pairs
                if lane_score(a, b, "domain", snap.df["domain"], df_max, df_gate=gate)[0] > 0)
        f = sum(1 for a, b in false_pairs
                if lane_score(a, b, "domain", snap.df["domain"], df_max, df_gate=gate)[0] > 0)
        tr = t / max(1, len(true_pairs))
        fr = f / max(1, len(false_pairs))
        rows.append({
            "df_gate": "any" if gate >= 10**9 else gate,
            "true_fire_rate": round(tr, 4),
            "false_fire_rate": round(fr, 4),
            "lift": round(tr / fr, 3) if fr > 0 else None,
            "true_n": t, "false_n": f,
        })
    return rows


def seed_weights(lane_stats: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """SEED `w_E / w_U / w_H` from the measured false-fire rates.

    NOT the operating point. `strength` is a MAX over lanes, so the weights only
    decide (a) which lane wins a tie and (b) where the borderline band falls —
    the M1/M2 grid is the authority on the threshold itself. The seed rule is
    stated so it can be argued with: a lane's weight is its measured PRECISION
    on the witness construction,

        w_lane = true_fire / (true_fire + false_fire)

    normalised so the best lane is 1.0. A lane that fires as often on the false
    construction as on the true one seeds to ~0.5 and should be read as "carries
    no identity information", which is the honest form of Q1's answer.
    """
    raw: dict[str, float] = {}
    for lane, st in lane_stats.items():
        tr = float(st.get("true_fire_rate") or 0.0)
        fr = float(st.get("false_fire_rate") or 0.0)
        raw[lane] = (tr / (tr + fr)) if (tr + fr) > 0 else 0.0

    # The spec names three lanes. Map the four measured ones onto them:
    #   w_E = entity · w_U = the locator lane (exact-URL, else domain) ·
    #   w_H = headline AFTER the §4d hygiene rule (the raw lane is diagnostic only).
    spec = {
        "w_E": raw.get("entity", 0.0),
        "w_U": max(raw.get("url", 0.0), raw.get("domain", 0.0)),
        "w_H": raw.get("headline_clean", 0.0),
    }
    best = max(spec.values()) if spec else 0.0
    norm = {k: (round(v / best, 3) if best > 0 else 0.0) for k, v in spec.items()}

    caveats = []
    for lane, st in lane_stats.items():
        n_false = int(st.get("false_pairs") or 0)
        if (st.get("false_fire_rate") or 0) == 0 and (st.get("true_fire_rate") or 0) > 0:
            ub = 3.0 / max(1, n_false)   # rule of three, 95% upper bound at 0/n
            caveats.append(
                f"`{lane}` fired on 0 of {n_false} false pairs, so its precision of "
                f"1.0000 is an UPPER BOUND, not a measurement — the rule of three puts "
                f"the true false-rate anywhere below {ub:.2%}. Its weight is the least "
                f"trustworthy number in this table.")
        if (st.get("true_fire_rate") or 0) < 0.05:
            caveats.append(
                f"`{lane}` fires on only {st['true_fire_rate']:.1%} of TRUE pairs — "
                f"whatever its precision, it contributes almost no recall, so its "
                f"weight decides very little.")
    return {"rule": "w_lane = precision(true_fire, false_fire), normalised to max=1.0",
            "precision_by_measured_lane": {k: round(v, 4) for k, v in raw.items()},
            "precision": {k: round(v, 4) for k, v in spec.items()},
            "seed_weights": norm,
            "lane_mapping": {"w_E": "entity", "w_U": "max(url, domain) — the locator lane",
                             "w_H": "headline_clean (post-§4d hygiene)"},
            "caveats": caveats,
            "status": "SEED — the M1/M2 grid sets the operating point; these feed it"}


# ------------------------------------------------------------------ noise floor
def build_noise_sample(snap: SnapshotEvidence, n: int, seed: int) -> list[str]:
    """Deterministic sample of df=1 entity names.

    Sampled from the SORTED df=1 name list under a fixed seed and keyed BY NAME,
    so a label file stays valid even if the corpus underneath shifts."""
    df1 = sorted(k for k, v in snap.df["entity"].items() if v == 1)
    rng = random.Random(seed)
    if len(df1) <= n:
        return df1
    return sorted(rng.sample(df1, n))


def _source_families(provenance: dict[str, Any]) -> set[str]:
    """Which SOURCE ARRAYS an entity came from. `nlp_persons` and the two GDELT
    arrays fail differently, and the recommendation is only actionable if it can
    name the array to distrust."""
    fams: set[str] = set()
    for key in provenance or {}:
        if key.startswith("nlp:"):
            fams.add("nlp_persons")
        elif key == "gdelt_persons":
            fams.add("gdelt_persons")
        elif key == "gdelt_orgs":
            fams.add("gdelt_organizations")
    return fams


def score_noise(sample: list[dict[str, Any]], labels: dict[str, str]) -> dict[str, Any]:
    """Garbage rate overall, by exclusive stratum, and BY SOURCE ARRAY.

    The blunt recommendation ('exclude df=1') is only worth making if the noise
    is spread; if one array carries it, the cheaper and more honest cut names
    that array. `REAL_WEAK` counts as REAL in the headline rate (it IS a real
    entity) and is reported separately, because a photo credit or a byline is a
    real entity that is nevertheless bad same-story evidence.
    """
    verdicts: Counter = Counter()
    by_stratum: dict[str, Counter] = defaultdict(Counter)
    by_source: dict[str, Counter] = defaultdict(Counter)
    labeled = []
    for item in sample:
        v = (labels.get(item["name"]) or "").strip().upper()
        if v not in {"GARBAGE", "REAL", "REAL_WEAK"}:
            v = "UNLABELED"
        verdicts[v] += 1
        provs = set(item.get("provenance") or {})
        stratum = "gdelt_any" if any(p.startswith("gdelt") for p in provs) else "nlp_only"
        by_stratum[stratum][v] += 1
        for fam in _source_families(item.get("provenance") or {}):
            by_source[fam][v] += 1
        labeled.append({**item, "verdict": v, "stratum": stratum})

    def _rate(c: Counter) -> dict[str, Any]:
        n = c["GARBAGE"] + c["REAL"] + c["REAL_WEAK"]
        return {"n": n, "garbage": c["GARBAGE"], "real": c["REAL"],
                "real_weak": c["REAL_WEAK"],
                "garbage_rate": round(c["GARBAGE"] / n, 4) if n else None,
                "unusable_rate": round((c["GARBAGE"] + c["REAL_WEAK"]) / n, 4) if n else None}

    overall = _rate(verdicts)
    return {
        "rater": "model-labeled, single rater (see artifact header)",
        "n_sampled": len(sample),
        "n_labeled": overall["n"],
        "counts": dict(verdicts),
        "garbage_rate": overall["garbage_rate"],
        "unusable_rate": overall["unusable_rate"],
        "by_provenance": {k: _rate(v) for k, v in by_stratum.items()},
        "by_source_array": {k: _rate(v) for k, v in by_source.items()},
        "items": labeled,
    }


# ------------------------------------------------------------------ render
def _fmt(v: Any) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def _pct(v: Any) -> str:
    return "—" if v is None else f"{v:.1%}"


def render_md(res: dict[str, Any]) -> str:  # noqa: C901
    L: list[str] = []
    a = L.append
    meta = res["meta"]
    a(f"# M3 — evidence rarity calibration ({meta['generated_at'][:10]})")
    a("")
    a(f"**Script:** `backend/scripts/calibrate_evidence_rarity.py` · read-only "
      f"(`default_transaction_read_only`) · **writes no prod table**")
    a(f"**Spec:** `docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md` "
      f"§3.1/§3.4/§10 · **Plan:** T-A2 (M3)")
    a(f"**Primary snapshot:** `{meta['primary_day']}` "
      f"({meta['primary_clusters']} clusters, sample-ref resolvability "
      f"**{meta['primary_resolvability']:.1%}**) · **days profiled:** {meta['days']}")
    a("")
    a("> **Read this first.** df is measured per SNAPSHOT with the CLUSTER as the "
      "document. Older snapshots are measured through a decaying window — "
      "`sample_signal_ids` resolvability falls from ~97.5% to ~16% over 7 days "
      "(spec §2.4) — so their df is biased LOW and they are used here only as a "
      "**volatility check**. Every proposal is anchored on the primary snapshot, "
      "which is the resolvability the Stage-1 writer will actually see (it builds "
      "fingerprints immediately after the snapshot write).")
    a("")

    # ---- 0 summary
    ld = res["lane_discrimination"]
    a("## 0. What this measured, in one screen")
    a("")
    a("| question (spec) | answer |")
    a("|---|---|")
    a(f"| `df_max` per lane | entity **{res['df_max_proposals']['entity']['proposed']}**, "
      f"domain **{res['df_max_proposals']['domain']['proposed']}**, headline "
      f"**{res['df_max_proposals']['headline_clean']['proposed']}**, url "
      f"**n/a (degenerate — treat as binary)**. Use FIXED constants, not the observed "
      f"max: the observed max swings up to "
      f"{max(p['observed_df_max_range'][1] / max(1, p['observed_df_max_range'][0]) for p in res['df_max_proposals'].values() if p.get('observed_df_max_range') and p['observed_df_max_range'][0]):.1f}× "
      f"night to night while `norm_rarity(df=2)` moves by <0.03 across every candidate "
      f"— the denominator is volatile and the answer is insensitive, so pin it. |")
    a(f"| §10 Q2 — `nlp_persons` noise floor | **{res['noise_floor']['garbage_rate']:.1%} "
      f"garbage** at df=1 (n={res['noise_floor']['n_labeled']}, model-labeled). "
      f"Well over the 30% line → **df=1 is not admissible as sole evidence**. The spec "
      f"blamed `nlp_persons` (§2.5); the measurement says the worst array is "
      f"**GDELT `organizations[]` at "
      f"{res['noise_floor']['by_source_array'].get('gdelt_organizations', {}).get('garbage_rate', 0):.0%}**, "
      f"vs `nlp_persons` "
      f"{res['noise_floor']['by_source_array'].get('nlp_persons', {}).get('garbage_rate', 0):.0%} "
      f"and GDELT `persons[]` "
      f"{res['noise_floor']['by_source_array'].get('gdelt_persons', {}).get('garbage_rate', 0):.0%}. |")
    a(f"| §10 Q1 — does lane U's domain half discriminate? | **Not at DP-1** "
      f"({ld['domain']['true_fire_rate']:.1%} true vs "
      f"{ld['domain']['false_fire_rate']:.1%} false, lift {_fmt(ld['domain']['lift'])}). "
      f"**Yes at DP-2** (cross-day "
      f"{(res.get('cross_day') or {}).get('domain', {}).get('true_fire_rate', 0):.1%} vs "
      f"{(res.get('cross_day') or {}).get('domain', {}).get('false_fire_rate', 0):.1%}). "
      f"The question has two answers and the spec asks it once. |")
    a(f"| lane U's exact-URL half | **structurally silent at DP-1** — clusters partition "
      f"the snapshot and `source_url` is unique, so two same-night clusters cannot share "
      f"a URL. Not a threshold problem. |")
    a(f"| `w_E / w_U / w_H` | seeds **{res['seed_weights']['seed_weights']['w_E']} / "
      f"{res['seed_weights']['seed_weights']['w_U']} / "
      f"{res['seed_weights']['seed_weights']['w_H']}** — but see §5: lane E fires on "
      f"{ld['entity']['true_fire_rate']:.0%} of true pairs and every other lane under "
      f"6%, so at DP-1 `strength` is lane E and the other weights decide almost nothing. |")
    a("")
    a("**Two findings the spec did not anticipate, both actionable before Stage 1:**")
    a("")
    a("1. **Lane H manufactures false evidence on non-Latin headlines** (§4d). "
      "`_norm_headline` deletes non-Latin characters, so a Cyrillic or Arabic headline "
      "reduces to its DIGITS — `'Атака РФ по АТБ у Чернігові 26 липня'` → `'26'`. A "
      "rare digit-residue key scores `norm_rarity ≈ 1.0`, the maximum. T-B2 must filter "
      "these before writing fingerprints; a frozen fingerprint cannot be cleaned later.")
    a("2. **Stage 2 has no script-blind lane.** Lane U is silent at DP-1 (§4c) and lane "
      "H is unusable for ru/uk/ar/fa (§4d), so a Cyrillic-only fragment pair is judged "
      "by lane E alone — whose ru coverage is 10.0% (spec §2.2). The spec's §3.4 "
      "argument that U and H cover the entity lane's holes **does not hold at the "
      "decision point Stage 2 builds first.**")
    a("")

    # ---- 1 df distributions
    a("## 1. df distributions per lane (primary snapshot)")
    a("")
    a("| lane | distinct items | df_max | df p50 | p90 | p95 | p99 | share df=1 | "
      "items/cluster (mean) | cluster coverage |")
    a("|---|---|---|---|---|---|---|---|---|---|")
    for lane in LANES:
        p = res["df_profiles"][meta["primary_day"]][lane]
        if not p.get("distinct"):
            a(f"| {lane} | 0 | — | — | — | — | — | — | — | — |")
            continue
        a(f"| **{lane}** | {p['distinct']:,} | {p['df_max']} | {p['df_p50']} | "
          f"{p['df_p90']} | {p['df_p95']} | {p['df_p99']} | {p['share_df1']:.1%} | "
          f"{p['items_per_cluster_mean']} | {p['cluster_coverage']:.1%} |")
    a("")
    a("df histogram (primary snapshot, item counts):")
    a("")
    bucket_keys = list(res["df_profiles"][meta["primary_day"]][LANES[0]].get("buckets", {}))
    a("| lane | " + " | ".join(bucket_keys) + " |")
    a("|---|" + "---|" * len(bucket_keys))
    for lane in LANES:
        p = res["df_profiles"][meta["primary_day"]][lane]
        b = p.get("buckets") or {}
        a(f"| {lane} | " + " | ".join(f"{b.get(k, 0):,}" for k in bucket_keys) + " |")
    a("")
    a("Most frequent items per lane (the ubiquity that rarity weighting has to defuse):")
    a("")
    for lane in LANES:
        p = res["df_profiles"][meta["primary_day"]][lane]
        top = ", ".join(f"`{t['item'][:44]}` ({t['df']})" for t in (p.get("top_items") or [])[:8])
        a(f"- **{lane}** — {top or '—'}")
    a("")

    # ---- 2 df_max
    a("## 2. `df_max` per lane — proposal, volatility and sensitivity")
    a("")
    a("`norm_rarity(df, df_max) = (1/df − 1/df_max)/(1 − 1/df_max)`. `df_max` is the "
      "denominator that is **frozen into every fingerprint** (spec §3.2), so the "
      "question is not only 'what is the max tonight' but 'does the max hold still'.")
    a("")
    a("### 2a. Observed `df_max` per night (the volatility check)")
    a("")
    days = meta["days_list"]
    a("| lane | " + " | ".join(days) + " | min | max | ratio max/min |")
    a("|---|" + "---|" * (len(days) + 3))
    for lane in LANES:
        vals = [res["df_profiles"][d].get(lane, {}).get("df_max") for d in days]
        clean = [v for v in vals if v]
        ratio = (max(clean) / min(clean)) if clean and min(clean) else None
        a(f"| **{lane}** | " + " | ".join(_fmt(v) for v in vals) + " | "
          f"{min(clean) if clean else '—'} | {max(clean) if clean else '—'} | "
          f"{ratio:.2f}× |" if ratio else
          f"| **{lane}** | " + " | ".join(_fmt(v) for v in vals) + " | — | — | — |")
    a("")
    a("Per-day context for every table in this document (both are confounds, and both "
      "are inherited by M1/M2):")
    a("")
    a("| day | clusters | sample refs | **resolvability** | **NULL-label share** |")
    a("|---|---|---|---|---|")
    for d in days:
        s = res["snapshots"][d]
        void = " ⚠ label-VOID" if s["label_null_share"] >= 0.05 else ""
        a(f"| `{d}` | {s['clusters']:,} | {s['sample_refs']:,} | "
          f"{s['resolvability']:.1%} | {s['label_null_share']:.1%}{void} |")
    a("")
    a("### 2b. Sensitivity — how far `norm_rarity` actually moves")
    a("")
    for lane in LANES:
        sens = res["df_max_sensitivity"].get(lane)
        if not sens:
            continue
        a(f"**{lane}** (observed df_max {sens['observed_df_max']}):")
        a("")
        cands = sens["candidates"]
        a("| df | " + " | ".join(f"df_max={c}" for c in cands) + " | spread |")
        a("|---|" + "---|" * (len(cands) + 1))
        for row in sens["rows"]:
            a(f"| {row['df']} | " + " | ".join(f"{row[str(c)]:.4f}" for c in cands) +
              f" | {row['spread']:.4f} |")
        a("")
    a("### 2c. Proposals")
    a("")
    a("| lane | proposed `df_max` | basis | norm_rarity(df=2) at the proposal | "
      "worst-case move vs the observed max |")
    a("|---|---|---|---|---|")
    for lane in LANES:
        pr = res["df_max_proposals"].get(lane)
        if not pr:
            continue
        prop = ("**n/a — degenerate**" if pr.get("degenerate")
                else f"**{pr['proposed']}**")
        nr2 = ("—" if pr.get("norm_rarity_df2") is None
               else f"{pr['norm_rarity_df2']:.4f}")
        dl = ("—" if pr.get("delta_vs_observed_df2") is None
              else f"{pr['delta_vs_observed_df2']:+.4f}")
        a(f"| **{lane}** | {prop} | {pr['basis']} | {nr2} | {dl} |")
    a("")
    for lane in LANES:
        pr = res["df_max_proposals"].get(lane)
        if pr and pr.get("note"):
            a(f"- **{lane}** — {pr['note']}")
    a("")

    # ---- 3 noise floor
    nf = res["noise_floor"]
    a("## 3. The `nlp_persons` noise floor (df=1 stratum)")
    a("")
    a(f"**Labeling provenance: {nf['rater']}.** Every one of the "
      f"{nf['n_sampled']} sampled items ships in the companion `.json` with its "
      f"verdict, its raw spellings, its provenance counts and an example "
      f"headline, so a human can re-check the call. The sample is deterministic "
      f"(seed {meta['seed']}) and keyed BY NAME, so a re-label stays valid.")
    a("")
    a("Labeling rule (full statement + the borderline policy live in "
      "`2026-07-30-df1-entity-labels.json`): the question is **is this string a "
      "STABLE IDENTIFIER** — one an independent report of the same story would "
      "plausibly also produce — because that, not grammatical entity-hood, is what "
      "makes a df=1 item usable at norm_rarity 1.0. **REAL** = a canonical-ish name "
      "(NER mistyping does not disqualify it — overlap matches the STRING, not the "
      "type). **REAL_WEAK** = a real, stable entity that is nonetheless poor "
      "same-story evidence: photo credits, reporter bylines, the covering outlet's "
      "own name. **GARBAGE** = sentence fragments, GDELT machine-translation "
      "word-salad, generic common nouns, bare ambiguous tokens, truncations, and "
      "two entities glued into one key.")
    a("")
    if nf.get("garbage_rate") is None:
        a("> ⚠ **UNLABELED RUN** — re-run with `--labels <path>` to produce the rate.")
    else:
        a("| stratum | n labeled | garbage | real | real-but-weak | **garbage rate** | "
          "unusable rate (garbage + weak) |")
        a("|---|---|---|---|---|---|---|")
        a(f"| **all df=1 entities** | {nf['n_labeled']} | {nf['counts'].get('GARBAGE', 0)} "
          f"| {nf['counts'].get('REAL', 0)} | {nf['counts'].get('REAL_WEAK', 0)} | "
          f"**{nf['garbage_rate']:.1%}** | {nf['unusable_rate']:.1%} |")
        for prov, st in sorted(nf["by_provenance"].items()):
            a(f"| exclusive: {prov} | {st['n']} | {st['garbage']} | {st['real']} | "
              f"{st['real_weak']} | {_pct(st['garbage_rate'])} | "
              f"{_pct(st['unusable_rate'])} |")
        for src, st in sorted(nf.get("by_source_array", {}).items()):
            a(f"| source array: `{src}` | {st['n']} | {st['garbage']} | {st['real']} | "
              f"{st['real_weak']} | {_pct(st['garbage_rate'])} | "
              f"{_pct(st['unusable_rate'])} |")
        a("")
        a("*(Source-array rows are memberships, not a partition — an entity present in "
          "two arrays counts in both.)*")
        a("")
        a(f"**Recommendation:** {res['noise_recommendation']}")
    a("")

    # ---- 4 lane U
    a("## 4. Does the DOMAIN half of lane U discriminate? (spec §10 Q1)")
    a("")
    a(f"TRUE = every within-family cluster pair of the witness families "
      f"({', '.join(f'**{k}** {v['clusters']} clusters / {v['pairs']} pairs' for k, v in res['families'].items())}). "
      f"FALSE = {res['false_pairs_n']} mechanical pairs: disjoint non-empty country "
      f"sets AND `different_story` labels — the SAME construction as the "
      f"whitened-taus harness (imported, not re-derived).")
    a("")
    a("### 4a. Every lane, true vs false (no df gate)")
    a("")
    a("| lane | TRUE share w/ ≥1 shared item | FALSE share | lift | "
      "TRUE score p50 | FALSE score p95 | AUC |")
    a("|---|---|---|---|---|---|---|")
    for lane in LANES:
        st = res["lane_discrimination"][lane]
        a(f"| **{lane}** | {st['true_fire_rate']:.1%} | {st['false_fire_rate']:.1%} | "
          f"{_fmt(st['lift'])} | {_fmt(st['true_score_p50'])} | "
          f"{_fmt(st['false_score_p95'])} | {_fmt(st['auc'])} |")
    a("")
    a("### 4b. Domain half under a df ceiling (\"only low-df domains count\")")
    a("")
    a("| max df of a shared domain | TRUE fire | FALSE fire | lift |")
    a("|---|---|---|---|")
    for row in res["domain_gate_sweep"]:
        a(f"| {row['df_gate']} | {row['true_fire_rate']:.1%} ({row['true_n']}) | "
          f"{row['false_fire_rate']:.1%} ({row['false_n']}) | {_fmt(row['lift'])} |")
    a("")
    a(f"**Domain verdict:** {res['domain_verdict']}")
    a("")
    a("### 4c. The exact-URL half — a STRUCTURAL result")
    a("")
    st = res["structural"]
    a(f"| check | value |")
    a("|---|---|")
    a(f"| `sample_signal_ids` on the primary snapshot | {st['sample_refs']:,} refs, "
      f"{st['distinct_refs']:,} distinct |")
    a(f"| → do clusters PARTITION the corpus? | "
      f"**{'yes — no signal is in two clusters' if st['sample_refs_are_disjoint'] else 'no'}** |")
    a(f"| duplicate `source_url` values in `signals_v2` | "
      f"**{st['duplicate_source_urls']}** of {st['rows_with_url']:,} rows |")
    a(f"| normalized url keys at df=2 within the snapshot | "
      f"{(res['df_profiles'][meta['primary_day']]['url'].get('buckets') or {}).get('2', 0)} "
      f"of {res['df_profiles'][meta['primary_day']]['url'].get('distinct', 0):,} |")
    a(f"| `snapshot_window_h` | **{st['snapshot_window_h']}** |")
    a(f"| signals sampled on BOTH `{st['primary_day']}` and `{st['prior_day']}` | "
      f"{st['xday_shared_signals']:,} ({st['xday_share']:.1%} of the primary's refs) |")
    a("")
    a(f"**URL verdict:** {res['url_verdict']}")
    a("")
    xd = res.get("cross_day") or {}
    if xd:
        m = xd["_meta"]
        a(f"Cross-day probe (`{m['new_day']}` × `{m['old_day']}`, a **{m['day_gap']}-day "
          f"gap**, {m['true_pairs']} true / {m['false_pairs']} false pairs; old side at "
          f"{m['old_day_resolvability']:.1%} resolvability, so these are FLOORS):")
        a("")
        if m.get("days_skipped_label_void"):
            a(f"> ⚠ The nearest prior nights were **skipped as label-VOID**: "
              f"{', '.join('`' + d + '`' for d in m['days_skipped_label_void'])} carry "
              f"100% NULL `emergent_clusters.label` (the 2026-07-23→07-27 DeepSeek-402 "
              f"blackout). Both constructions here are label-based, so those nights "
              f"cannot be used — spec §5.1's confounder rule. The probe therefore "
              f"reaches back {m['day_gap']} days, where only "
              f"{m['old_day_resolvability']:.1%} of sample refs still resolve. **Treat "
              f"this table as an existence proof, not a rate.**")
            a("")
        a("| lane | TRUE fire | FALSE fire | lift | AUC |")
        a("|---|---|---|---|---|")
        for lane in LANES:
            s = xd.get(lane) or {}
            a(f"| **{lane}** | {s.get('true_fire_rate', 0):.1%} | "
              f"{s.get('false_fire_rate', 0):.1%} | {_fmt(s.get('lift'))} | "
              f"{_fmt(s.get('auc'))} |")
        a("")
    else:
        a("> ⚠ **No cross-day probe.** Every prior night in the profiled window is "
          "label-VOID (100% NULL `emergent_clusters.label`, the 07-23→07-27 blackout), "
          "and both the TRUE and FALSE constructions are label-based.")
        a("")

    # ---- 4d lane H hygiene
    hy = res["lane_h_hygiene"]
    a("### 4d. 🔴 Lane H manufactures date-residue keys on non-Latin headlines")
    a("")
    a("`_norm_headline` folds through `normalize_search_text`, whose `[^a-z0-9]` class "
      "deletes every non-Latin character. A non-Latin headline therefore does **not** "
      "reduce to the empty string — it reduces to whatever DIGITS it contained. "
      "Measured live:")
    a("")
    a("```")
    a("'27 липня 2026 року — яке сьогодні свято'  ->  '27 2026'")
    a("'Атака РФ по АТБ у Чернігові 26 липня'     ->  '26'")
    a("'انفجار في كييف 2026'                        ->  '2026'")
    a("```")
    a("")
    a(f"On the primary snapshot **{hy['residue_share']:.1%}** of resolved signals "
      f"({hy['residue']:,} of {hy['resolved']:,}) produce such a key, and "
      f"{hy['empty_share']:.1%} produce an empty one. The top lane-H keys by df are "
      f"pure residue — " +
      ", ".join(f"`{t['item']}` ({t['df']})" for t in hy["top_raw_keys"][:6]) + ".")
    a("")
    a("**Why this is not cosmetic.** A residue key like `26` can be RARE in a given "
      "night, and the rarity weighting would then hand it `norm_rarity ≈ 1.0` — the "
      "MAXIMUM evidence score — for two headlines that merely mention the same number. "
      "That is a false-merge generator aimed precisely at the ru/uk/ar/CJK corpus the "
      "spec is trying to protect (§2.2, §3.4).")
    a("")
    a(f"**Hygiene rule measured here** (`headline_key_usable`: a key must contain ≥1 "
      f"alphabetic character and be ≥{hy['min_chars']} chars). Its cost and benefit, "
      f"as the `headline_clean` lane:")
    a("")
    a("| lane | distinct keys | TRUE fire | FALSE fire | lift |")
    a("|---|---|---|---|---|")
    for lane in ("headline", "headline_clean"):
        st = res["lane_discrimination"][lane]
        prof = res["df_profiles"][meta["primary_day"]][lane]
        a(f"| `{lane}` | {prof.get('distinct', 0):,} | {st['true_fire_rate']:.1%} | "
          f"{st['false_fire_rate']:.1%} | {_fmt(st['lift'])} |")
    a("")
    a(f"**Verdict:** {res['headline_verdict']}")
    a("")
    a(f"**And the rule is necessary but not sufficient.** After hygiene, the most "
      f"frequent surviving keys are OUTLET NAMES — " +
      ", ".join(f"`{t['item']}` ({t['df']})" for t in hy["top_clean_keys"][:5]) +
      f" — the same defect wearing a different hat: when the masthead stamp is not the "
      f"last `|` segment, the Latin outlet name is the only text that survives deletion "
      f"of a non-Latin headline. **{hy['outlet_residue_share']:.1%}** of resolved "
      f"signals ({hy['outlet_residue']:,}) produce such a key. That makes any two "
      f"stories from one outlet look like one story — the DOMAIN lane in lane H's "
      f"clothes, and without the domain lane's df ceiling. T-B2 should reject keys "
      f"that reduce to the signal's own `source_name`/domain "
      f"(`headline_key_is_outlet_residue` here) as well as alpha-free ones.")
    a("")
    a("Per-language residue on the primary snapshot (top by signal count):")
    a("")
    a("| lang | signals | empty key | digit-residue key | unusable share |")
    a("|---|---|---|---|---|")
    for r in res["lane_h_language_coverage"]:
        unus = (r["empty_headline_keys"] + r["residue_headline_keys"]) / max(1, r["n_signals"])
        a(f"| `{r['lang']}` | {r['n_signals']:,} | {r['empty_headline_keys']:,} | "
          f"{r['residue_headline_keys']:,} | {unus:.1%} |")
    a("")

    # ---- 5 weights
    sw = res["seed_weights"]
    a("## 5. Seed weights `w_E / w_U / w_H`")
    a("")
    a(f"Rule: `{sw['rule']}`.")
    a("")
    a("| spec weight | measured lane | precision | **seed value** |")
    a("|---|---|---|---|")
    for k in ("w_E", "w_U", "w_H"):
        a(f"| `{k}` | {sw['lane_mapping'][k]} | {sw['precision'].get(k, 0):.4f} | "
          f"**{sw['seed_weights'].get(k, 0)}** |")
    a("")
    a("Underlying per-lane precisions: " +
      " · ".join(f"`{k}` {v:.4f}" for k, v in sw["precision_by_measured_lane"].items()))
    a("")
    for c in sw.get("caveats", []):
        a(f"- ⚠ {c}")
    a("")
    a(f"> **{sw['status']}.** `strength` is a MAX over lanes, so these only decide "
      "tie-breaks and where the borderline band lands. They are an INPUT to the "
      "M1/M2 grid, never a contradiction of it — if the sweep lands elsewhere, "
      "the sweep wins.")
    a("")
    a("**The practical reading is blunter than the table.** Lane E fires on "
      f"{res['lane_discrimination']['entity']['true_fire_rate']:.0%} of true pairs; "
      f"every other lane fires on under "
      f"{max(res['lane_discrimination'][l]['true_fire_rate'] for l in ('domain', 'url', 'headline_clean')):.0%}. "
      "At DP-1, **lane E is not the primary lane — it is effectively the only lane**, "
      "and `strength` reduces to `w_E · max_norm_rarity(shared entities)`. The other "
      "two weights are contingency for a corpus mix this snapshot does not contain.")
    a("")

    # ---- 6 residuals
    a("## 6. Residuals and honest limits")
    a("")
    for line in res["residuals"]:
        a(f"- {line}")
    a("")
    a("---")
    a("")
    a(f"_Generated {meta['generated_at']} · seed {meta['seed']} · "
      f"`--days {meta['days']}` · companion data `{ARTIFACT_STEM}.json`._")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ orchestration
def lane_stats_n(res: dict[str, Any]) -> int:
    return int(res["lane_discrimination"]["entity"].get("true_pairs") or 0)


def build_recommendations(res: dict[str, Any]) -> None:
    """Turn measurements into the two named recommendations (noise gate, lane U)."""
    nf = res["noise_floor"]
    rate = nf.get("garbage_rate")
    if rate is None:
        res["noise_recommendation"] = ("UNLABELED — no recommendation. Re-run with "
                                       "`--labels` before go/no-go 0.")
    else:
        src = nf.get("by_source_array") or {}
        ranked = sorted(((k, v) for k, v in src.items() if v.get("garbage_rate") is not None),
                        key=lambda kv: -kv[1]["garbage_rate"])
        detail = "; ".join(f"`{k}` {v['garbage_rate']:.0%} (n={v['n']})" for k, v in ranked)
        if rate > 0.30:
            head = (f"garbage rate **{rate:.1%} > 30%** → **df=1 entities must NOT be "
                    f"admissible as the sole evidence for a merge.** By source array: "
                    f"{detail}. ")
            if ranked and ranked[0][1]["garbage_rate"] - ranked[-1][1]["garbage_rate"] > 0.15:
                head += (f"The noise is NOT uniform — `{ranked[0][0]}` is the worst "
                         f"array and `{ranked[-1][0]}` the cleanest — so the cheapest "
                         f"honest cut is per-array admissibility at df=1, with the "
                         f"excluded count published (`entities_excluded_noise_floor`) "
                         f"rather than silently dropped. Note this INVERTS the spec's "
                         f"§2.5 assumption if the worst array is a GDELT one.")
            else:
                head += ("The noise is spread evenly across the arrays, so the cut must "
                         "be on df itself: require df≥2, or require a second lane to "
                         "corroborate any df=1 entity.")
            res["noise_recommendation"] = head
        else:
            res["noise_recommendation"] = (
                f"garbage rate **{rate:.1%} ≤ 30%** → df=1 entities may stay "
                f"admissible, but the rate is the false-positive floor the merge "
                f"gate inherits and must be republished as fingerprints accumulate. "
                f"By source array: {detail}.")

    # ---- lane U's exact-URL half: a STRUCTURAL result, not a rate
    st = res["structural"]
    url_x = (res.get("cross_day") or {}).get("url") or {}
    url_df = (res["df_profiles"][st["primary_day"]]["url"].get("buckets") or {})
    if st["sample_refs_are_disjoint"] and st["duplicate_source_urls"] == 0:
        res["url_verdict"] = (
            f"**the exact-URL half is structurally silent on same-snapshot pairs — "
            f"this is a consequence of the schema, not a low rate that better "
            f"thresholds could lift.** `sample_signal_ids` PARTITION the snapshot "
            f"({st['sample_refs']:,} refs, {st['distinct_refs']:,} distinct → no signal "
            f"is in two clusters), and `signals_v2` holds {st['duplicate_source_urls']} "
            f"duplicate `source_url` values across {st['rows_with_url']:,} rows. Two "
            f"clusters of one snapshot can therefore only share a URL when the "
            f"normalizer collapses two distinct rows — measured at "
            f"**{url_df.get('2', 0)} keys out of {res['df_profiles'][st['primary_day']]['url'].get('distinct', 0):,}**. "
            f"Fire rates: {res['lane_discrimination']['url']['true_fire_rate']:.1%} true / "
            f"{res['lane_discrimination']['url']['false_fire_rate']:.1%} false. "
            f"**Consequence for the build order: lane U contributes NOTHING to Stage 2 "
            f"(DP-1, same-snapshot merge) — the first thing being built.** Cross-day is "
            f"a different object entirely, and the reason is `snapshot_window_h = "
            f"{st['snapshot_window_h']}`: each snapshot re-clusters a SEVEN-DAY window, "
            f"so {st['xday_shared_signals']:,} signals ({st['xday_share']:.1%} of "
            f"tonight's refs) are also in last night's, and the cross-day probe reads "
            f"{url_x.get('true_fire_rate', 0):.1%} true / "
            f"{url_x.get('false_fire_rate', 0):.1%} false. **Read that number with its "
            f"mechanism**: a cross-day same-story pair is largely the same ARTICLES "
            f"re-clustered, so lane U is measuring membership continuity, not a "
            f"translation-surviving same-story signal. That is still exactly what DP-2 "
            f"needs — but it is not evidence for the spec's §3.4 claim that lane U "
            f"rescues cross-script matching. **Keep lane U, scope it to DP-2, and do "
            f"not let its Stage-2 zero be read as 'lane U fails'.**")
    else:
        res["url_verdict"] = (
            f"exact-URL fires {res['lane_discrimination']['url']['true_fire_rate']:.1%} "
            f"true / {res['lane_discrimination']['url']['false_fire_rate']:.1%} false on "
            f"same-snapshot pairs.")

    # ---- lane H hygiene verdict
    hy = res["lane_h_hygiene"]
    raw_h = res["lane_discrimination"]["headline"]
    cln_h = res["lane_discrimination"]["headline_clean"]
    lost = raw_h["true_fire_rate"] - cln_h["true_fire_rate"]
    saved = raw_h["false_fire_rate"] - cln_h["false_fire_rate"]
    res["headline_verdict"] = (
        f"**the hygiene rule is mandatory, and it is cheap.** Dropping alpha-free / "
        f"short keys removes {hy['residue_share']:.1%} of resolved signals from lane H "
        f"and costs {lost * 100:.1f}pp of the true fire rate ({raw_h['true_fire_rate']:.1%} "
        f"\u2192 {cln_h['true_fire_rate']:.1%}) while removing {saved * 100:.1f}pp of the "
        f"false fire rate ({raw_h['false_fire_rate']:.1%} \u2192 {cln_h['false_fire_rate']:.1%}). `build_evidence_fingerprints.py` (T-B2) must apply "
        f"`headline_key_usable` BEFORE writing `headline_keys`, and publish the "
        f"dropped count — a residue key is not a headline, and a frozen fingerprint "
        f"cannot be cleaned later. Note this is a defect in lane H's INPUT, not in "
        f"`_norm_headline`, which is correct for its own job (syndication detection "
        f"over an English-dominant front page); the design's mistake is reusing it "
        f"unfiltered as an identity signal over a 31-language corpus.")

    sweep = res["domain_gate_sweep"]
    best = None
    for row in sweep:
        if row["lift"] is not None and (best is None or row["lift"] > best["lift"]):
            best = row
    dom = res["lane_discrimination"]["domain"]
    url = res["lane_discrimination"]["url"]
    dom_x = (res.get("cross_day") or {}).get("domain") or {}
    xday_note = (
        f" **The answer flips by decision point.** The same domain lane measured "
        f"across the day boundary reads {dom_x.get('true_fire_rate', 0):.1%} true / "
        f"{dom_x.get('false_fire_rate', 0):.1%} false (AUC {_fmt(dom_x.get('auc'))}) — "
        f"strong, for the §4c reason (a 168-hour clustering window means cross-day "
        f"same-story pairs largely re-use the same articles, hence the same domains). "
        f"So 'does the domain half discriminate' has no single answer: **NO at DP-1, "
        f"YES at DP-2.** The spec asks the question once; it needs asking twice."
    ) if dom_x else ""

    if best is None or best["lift"] is None or best["lift"] < 1.5 or best["true_n"] < 3:
        res["domain_verdict"] = (
            f"**at DP-1 the domain half does NOT discriminate** — best lift over every "
            f"df ceiling is {_fmt(best['lift']) if best else '—'} "
            f"(true {dom['true_fire_rate']:.1%} vs false {dom['false_fire_rate']:.1%} "
            f"ungated). Per spec §3.4 the honest call is to **DELETE the domain half "
            f"from the DP-1 gate** rather than leave it decorative." + xday_note)
    else:
        res["domain_verdict"] = (
            f"**at DP-1 the domain half is nearly worthless and dangerous ungated.** It "
            f"fires on only {dom['true_fire_rate']:.1%} of true pairs against "
            f"{dom['false_fire_rate']:.1%} of false — a lift of {dom['lift']}, i.e. "
            f"syndication infrastructure. A df≤{best['df_gate']} ceiling improves the "
            f"lift to {best['lift']} but on {best['true_n']} true pairs out of "
            f"{lane_stats_n(res)}, which is too few to calibrate on and buys ~"
            f"{best['true_fire_rate']:.0%} recall. **Recommendation: drop the domain "
            f"half from the DP-1 gate**; if it is kept at all, it is kept ONLY with the "
            f"df≤{best['df_gate']} ceiling and only as a borderline-band corroborator, "
            f"never as a merge trigger." + xday_note)


async def run(args: argparse.Namespace) -> int:  # noqa: C901
    import asyncpg

    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("DATABASE_URL required", file=sys.stderr)
        return 2
    conn = await asyncpg.connect(url, timeout=60)
    try:
        await conn.execute("SET default_transaction_read_only = on")
        await conn.execute("SET statement_timeout = '180s'")
        days = [str(r["d"]) for r in await conn.fetch(
            """SELECT snapshot_at::date AS d, count(*) n FROM emergent_clusters
               GROUP BY 1 HAVING count(*) >= $1 ORDER BY 1 DESC LIMIT $2""",
            args.min_clusters, args.days)]
        if not days:
            print("no snapshots found", file=sys.stderr)
            return 2
        days = sorted(days, reverse=True)
        primary = days[0]

        snaps: dict[str, SnapshotEvidence] = {}
        for d in days:
            print(f"  loading snapshot {d} …", file=sys.stderr)
            snaps[d] = await load_snapshot(conn, d, args.chunk)

        snap = snaps[primary]
        families = await find_families(conn, primary, args.families)
        names = build_noise_sample(snap, args.noise_sample, args.seed)
        prov = await sample_entity_provenance(conn, snap, set(names), args.chunk)
        structural = await structural_checks(conn, primary,
                                             days[1] if len(days) > 1 else None)
    finally:
        await conn.close()

    df_max = {ln: snap.df_max(ln) for ln in LANES}

    # ---- df profiles + df_max proposals
    profiles = {d: {ln: df_profile(s, ln) for ln in LANES} for d, s in snaps.items()}
    sensitivity = {ln: df_max_sensitivity(df_max[ln]) for ln in LANES}
    proposals: dict[str, dict[str, Any]] = {}
    for ln in LANES:
        observed = [profiles[d][ln].get("df_max") for d in days]
        observed = [v for v in observed if v]
        p99 = profiles[primary][ln].get("df_p99") or 1
        degenerate = max(observed or [1]) <= 2
        prop = int(args.df_max_fixed.get(ln)
                   or max(50, int(round(max(observed or [1]) / 50.0) * 50)))
        nr_prop = norm_rarity(2, prop)
        nr_obs = norm_rarity(2, df_max[ln])
        if degenerate:
            # A lane whose df never exceeds 2 has no rarity gradient to normalise:
            # every item is effectively unique, so `norm_rarity` degenerates to a
            # 1.0/0.0 step and `df_max` is meaningless. Say so instead of picking
            # a number that looks calibrated.
            basis = ("DEGENERATE — observed df_max ≤ 2, there is no rarity gradient "
                     "to normalise; treat a shared item in this lane as BINARY "
                     "evidence (weight 1.0) and do not store a df_max for it")
            note = (f"observed max is {max(observed or [1])} across every profiled "
                    f"night: essentially every item in this lane is unique, so "
                    f"rarity weighting adds nothing. Any df_max would be arbitrary — "
                    f"the sensitivity table's {abs(nr_prop - nr_obs):.4f} 'move' on "
                    f"df=2 is an artifact of that arbitrariness, not a calibration.")
            prop = 0
        else:
            basis = ("fixed constant ≥ observed max, rounded to 50 — "
                     "stability of a frozen denominator over nightly exactness")
            swing = (max(observed) / min(observed)) if observed and min(observed) else 0
            note = (f"observed max swings {min(observed)}–{max(observed)} across the "
                    f"profiled nights ({swing:.2f}×) while p99 tonight is only {p99} — "
                    f"the max is set by a handful of ubiquitous items and is exactly "
                    f"the kind of quantity that must not drift under a FROZEN "
                    f"fingerprint. Fixing it costs |Δ|={abs(nr_prop - nr_obs):.4f} on a "
                    f"df=2 item, i.e. nothing.")
        proposals[ln] = {
            "proposed": prop,
            "degenerate": degenerate,
            "basis": basis,
            "observed_df_max_primary": df_max[ln],
            "observed_df_max_range": [min(observed), max(observed)] if observed else None,
            "norm_rarity_df2": round(nr_prop, 4) if not degenerate else None,
            "delta_vs_observed_df2": round(nr_prop - nr_obs, 4) if not degenerate else None,
            "note": note,
        }

    # ---- lane discrimination
    fam_cids = {k: v for k, v in families.items() if v}
    true_pairs: list[tuple[ClusterEvidence, ClusterEvidence]] = []
    fam_detail = {}
    for name, cids in fam_cids.items():
        pairs = build_family_pairs(snap, cids)
        fam_detail[name] = {"clusters": len(cids), "pairs": len(pairs),
                            "cluster_ids": cids}
        true_pairs.extend(pairs)
    exclude = {c for cids in fam_cids.values() for c in cids}
    false_pairs = build_false_pairs(snap, args.false_pairs, args.seed, exclude)

    lane_disc: dict[str, dict[str, Any]] = {}
    for lane in LANES:
        ts = [lane_score(a, b, lane, snap.df[lane], df_max[lane])[0] for a, b in true_pairs]
        fs = [lane_score(a, b, lane, snap.df[lane], df_max[lane])[0] for a, b in false_pairs]
        tr = sum(1 for v in ts if v > 0) / max(1, len(ts))
        fr = sum(1 for v in fs if v > 0) / max(1, len(fs))
        lane_disc[lane] = {
            "true_pairs": len(ts), "false_pairs": len(fs),
            "true_fire_rate": round(tr, 4), "false_fire_rate": round(fr, 4),
            "lift": round(tr / fr, 3) if fr > 0 else None,
            "true_score_p50": round(float(np.percentile(ts, 50)), 4) if ts else None,
            "false_score_p95": round(float(np.percentile(fs, 95)), 4) if fs else None,
            "auc": auc(ts, fs),
            "true_score": describe(ts), "false_score": describe(fs),
        }

    sweep = domain_gate_sweep(true_pairs, false_pairs, snap, df_max["domain"])

    # ---- cross-day (the DP-2 geometry the same-snapshot pairs cannot show)
    #
    # The prior day is chosen by LABEL AVAILABILITY, not by recency: the
    # 2026-07-23..07-27 DeepSeek-402 blackout left `emergent_clusters.label`
    # 100% NULL, and both the TRUE and the FALSE constructions are label-based,
    # so those nights are VOID for this probe (spec §5.1's confounder rule).
    cross_day: dict[str, Any] = {}
    labelled_prior = [d for d in days[1:] if snaps[d].label_null_share < 0.05]
    if labelled_prior:
        old_day = labelled_prior[0]
        old = snaps[old_day]
        xt, xf = build_xday_pairs(snap, old, args.false_pairs, args.seed)
        cross_day = {"_meta": {
            "new_day": primary, "old_day": old_day,
            "true_pairs": len(xt), "false_pairs": len(xf),
            "old_day_resolvability": round(old.resolvability, 4),
            "days_skipped_label_void": [d for d in days[1:]
                                        if snaps[d].label_null_share >= 0.05],
            "day_gap": (dt.date.fromisoformat(primary) - dt.date.fromisoformat(old_day)).days,
        }}
        for lane in LANES:
            ts = [xday_score(a, b, lane, snap.df[lane], old.df[lane], df_max[lane])
                  for a, b in xt]
            fs = [xday_score(a, b, lane, snap.df[lane], old.df[lane], df_max[lane])
                  for a, b in xf]
            tr = sum(1 for v in ts if v > 0) / max(1, len(ts))
            fr = sum(1 for v in fs if v > 0) / max(1, len(fs))
            cross_day[lane] = {
                "true_fire_rate": round(tr, 4), "false_fire_rate": round(fr, 4),
                "lift": round(tr / fr, 3) if fr > 0 else None,
                "auc": auc(ts, fs),
            }

    # ---- noise sample
    sample = []
    for n in names:
        rec = prov.get(n) or {}
        sample.append({
            "name": n,
            "raw_variants": rec.get("raw_variants") or [],
            "provenance": rec.get("provenance") or {},
            "example_headline": rec.get("example_headline"),
            "example_lang": rec.get("example_lang"),
            "example_source": rec.get("example_source"),
        })
    labels: dict[str, str] = {}
    if args.labels:
        lp = Path(args.labels)
        if not lp.is_absolute():
            lp = REPO_ROOT / args.labels
        if lp.exists():
            raw = json.loads(lp.read_text(encoding="utf-8"))
            labels = raw.get("labels", raw) if isinstance(raw, dict) else {}
        else:
            print(f"labels file not found: {lp}", file=sys.stderr)
    noise = score_noise(sample, labels)

    # ---- lane H hygiene (the digit-residue check)
    lang_h = []
    for lang, n in snap.lang_counts.most_common(14):
        empty = snap.lang_headline_empty.get(lang, 0)
        resid = snap.lang_headline_residue.get(lang, 0)
        lang_h.append({"lang": lang, "n_signals": n,
                       "empty_headline_keys": empty,
                       "residue_headline_keys": resid,
                       "empty_share": round(empty / n, 4) if n else None,
                       "unusable_share": round((empty + resid) / n, 4) if n else None})
    tot_empty = sum(snap.lang_headline_empty.values())
    tot_resid = sum(snap.lang_headline_residue.values())
    hygiene = {
        "min_chars": HEADLINE_KEY_MIN_CHARS,
        "resolved": snap.n_resolved,
        "empty": tot_empty,
        "residue": tot_resid,
        "empty_share": round(tot_empty / max(1, snap.n_resolved), 4),
        "residue_share": round(tot_resid / max(1, snap.n_resolved), 4),
        "outlet_residue": snap.n_outlet_residue,
        "outlet_residue_share": round(snap.n_outlet_residue / max(1, snap.n_resolved), 4),
        "top_raw_keys": profiles[primary]["headline"].get("top_items", [])[:8],
        "top_clean_keys": profiles[primary]["headline_clean"].get("top_items", [])[:8],
    }

    res: dict[str, Any] = {
        "meta": {
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "script": "backend/scripts/calibrate_evidence_rarity.py",
            "measurement": "M3",
            "days": args.days, "days_list": days, "seed": args.seed,
            "primary_day": primary,
            "primary_clusters": len(snap.clusters),
            "primary_resolvability": round(snap.resolvability, 4),
            "read_only": True,
        },
        "snapshots": {d: {"clusters": len(s.clusters), "sample_refs": s.n_refs,
                          "resolved": s.n_resolved,
                          "resolvability": round(s.resolvability, 4),
                          "label_null_share": round(s.label_null_share, 4)}
                      for d, s in snaps.items()},
        "df_profiles": profiles,
        "df_max_sensitivity": sensitivity,
        "df_max_proposals": proposals,
        "families": fam_detail,
        "false_pairs_n": len(false_pairs),
        "lane_discrimination": lane_disc,
        "domain_gate_sweep": sweep,
        "structural": structural,
        "cross_day": cross_day,
        "seed_weights": seed_weights(lane_disc),
        "lane_h_language_coverage": lang_h,
        "lane_h_hygiene": hygiene,
        "noise_floor": noise,
    }

    unusable = [x for x in lang_h
                if (x["unusable_share"] or 0) > 0.8 and x["n_signals"] >= 15]
    res["residuals"] = [
        (f"**Cross-day df is measured through a decaying window.** Resolvability by "
         f"day: " + " · ".join(f"`{d}` {snaps[d].resolvability:.1%}" for d in days) +
         ". df on the low-resolvability days is biased LOW; only the primary day's "
         "numbers are proposal-grade."),
        (f"**Lane H is Latin-only by construction, and fails UNSAFELY rather than "
         f"emptily** (§4d). Languages whose headline keys are >80% unusable on the "
         f"primary snapshot: " +
         (", ".join(f"`{x['lang']}` ({x['unusable_share']:.0%} of {x['n_signals']:,})"
                    for x in unusable) or "none at n≥15") +
         f". Lane H therefore **cannot** cover the ru/uk entity hole — and spec §3.4 "
         f"reads as though it might. With lane U also silent at DP-1 (§4c), **Stage 2 "
         f"has no script-blind lane at all**: for a Cyrillic-only fragment pair, the "
         f"evidence gate reduces to lane E, whose ru coverage is 10.0% (§2.2). That "
         f"combination should be stated in the plan before go/no-go 0, not discovered "
         f"at go/no-go 2."),
        ("**The noise-floor labels are model-produced and single-rater.** They are a "
         "first pass, published item-by-item in the `.json` precisely so the number "
         "can be contested rather than inherited."),
        (f"**df's document unit is the cluster, and clusters are sampled.** "
         f"`sample_signal_ids` is capped at 24 (spec §2.5: 4.1% of clusters "
         f"truncated), so every df here is a df over a near-complete, not complete, "
         f"membership view."),
        ("**The FALSE construction is mechanical, not adjudicated.** It is imported "
         "verbatim from the whitened-taus harness so M1/M2/M3 share one definition; "
         "it inherits that harness's known bias (cross-script pairs are refused, so "
         "the false set skews same-script)."),
        (f"**The witness families are single-country** (Berlin Pride all DE, Caspian "
         f"8/9 IR) — a true set that is easy for every lane on geography. The "
         f"cross-country/cross-script reconvergence case is NOT represented here and "
         f"is M1's job to supply."),
        (f"**The cross-day probe's TRUE set is label-defined** (SequenceMatcher ≥ 0.80 "
         f"+ shared country across the day boundary) and its old side is measured at "
         f"{(cross_day.get('_meta') or {}).get('old_day_resolvability', 0):.1%} "
         f"resolvability, so its absolute rates are a floor, not an estimate. It is "
         f"here to establish that the DP-2 geometry EXISTS, not to set DP-2's "
         f"threshold — that is M5, and M5 is gated on ≥14 nights of fingerprints."),
        ("**`w_E/w_U/w_H` are seeds, not an operating point.** They are fitted on one "
         "night and two single-country families. The M1/M2 grid is the authority; if "
         "it lands elsewhere, it is right and this table is the prior it moved."),
        (f"**`snapshot_window_h = {structural['snapshot_window_h']}` makes the cross-day "
         f"lanes partly tautological.** Each snapshot re-clusters a seven-day window, so "
         f"{structural['xday_share']:.1%} of tonight's sampled signals were also sampled "
         f"last night. A cross-day 'same story' pair therefore shares ARTICLES, not just "
         f"a story — which is what DP-2 wants, but it means the cross-day URL/domain "
         f"numbers must never be quoted as evidence that locators survive translation."),
        (f"**The 07-23→07-27 label blackout removed five of the eight profiled nights "
         f"from every label-based construction** (100% NULL `emergent_clusters.label`). "
         f"It does not affect the df distributions (those need no labels), but it is why "
         f"the cross-day probe reaches back {(cross_day.get('_meta') or {}).get('day_gap', '—')} "
         f"days. M1/M2 inherit this: their witness families and FALSE sets can only be "
         f"built on labelled nights, and there are currently three in the window."),
    ]
    build_recommendations(res)

    print(json.dumps({
        "primary_day": primary,
        "resolvability": res["meta"]["primary_resolvability"],
        "df_max_proposals": {k: v["proposed"] for k, v in proposals.items()},
        "noise_garbage_rate": noise.get("garbage_rate"),
        "lane_fire_rates": {k: [v["true_fire_rate"], v["false_fire_rate"]]
                            for k, v in lane_disc.items()},
        "seed_weights": res["seed_weights"]["seed_weights"],
    }, indent=2, ensure_ascii=False))

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if args.dump_sample_only:
        p = out / f"{SAMPLE_STEM}.json"
        p.write_text(json.dumps({"meta": res["meta"], "sample": sample},
                                indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nsample -> {p}", file=sys.stderr)
        return 0
    if not args.no_artifacts:
        (out / f"{args.stem}.json").write_text(
            json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        (out / f"{args.stem}.md").write_text(render_md(res), encoding="utf-8")
        print(f"\nartifacts -> {out / (args.stem + '.md')}\n"
              f"             {out / (args.stem + '.json')}", file=sys.stderr)
    return 0


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="M3 — evidence rarity calibration (read-only; writes no prod table).")
    ap.add_argument("--days", type=int, default=8,
                    help="snapshot days to profile, newest first. Default 8, not 7: the "
                         "2026-07-23..07-27 label blackout means the nearest LABELLED "
                         "prior snapshot is 6 days back, and the cross-day probe needs "
                         "one (see §4c).")
    ap.add_argument("--min-clusters", type=int, default=200,
                    help="skip degenerate snapshot days below this cluster count")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--chunk", type=int, default=6000, help="signal fetch batch size")
    ap.add_argument("--noise-sample", type=int, default=200,
                    help="df=1 entities sampled for the noise floor (default 200)")
    ap.add_argument("--false-pairs", type=int, default=500,
                    help="mechanical FALSE cluster pairs (default 500)")
    ap.add_argument("--families", default="caspian=caspian|iran%ukrain,berlin-pride=berlin pride",
                    help="comma list of name=likepat|likepat witness families")
    ap.add_argument("--labels", default=None,
                    help="JSON file of {name: GARBAGE|REAL} for the noise floor")
    ap.add_argument("--dump-sample-only", action="store_true",
                    help="write the df=1 sample for labeling and stop")
    ap.add_argument("--out-dir", default=str(ARTIFACT_DIR))
    ap.add_argument("--stem", default=ARTIFACT_STEM)
    ap.add_argument("--no-artifacts", action="store_true")
    a = ap.parse_args()
    a.families = [x.strip() for x in str(a.families).split(",") if x.strip()]
    # Fixed df_max overrides are intentionally empty: §2c derives them.
    a.df_max_fixed = {}
    return a


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
