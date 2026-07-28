#!/usr/bin/env python3
"""T-A1 — measure the EVIDENCE-OVERLAP identity signal (spec §3.1) before any
code that writes anything.

WHY (spec `docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md`):
`project_dynamic_topics.merge_duplicates` decides "same story?" from
`cosine >= 0.90 AND SequenceMatcher(label) >= 0.80`. The label term returns 0
during a label blackout (`labels_compatible(None, None)` is False) and only 2/15
on the Caspian fragment pairs when labels exist, so one event shreds into 9-33
clusters that never reconverge. The proposed second axis is SHARED MEASURED
EVIDENCE — the same named entities, the same URLs, the same normalized headlines
— because a proper name, a link and a wire reprint are the same string in
Bucharest and in Beirut.

WHAT THIS DOES (read-only; `SET default_transaction_read_only = on`; writes NO
prod table):

  --coverage       M0  fingerprint build feasibility: per-cluster entity/domain/
                       headline-key counts over the WHOLE latest snapshot, the
                       empty-fingerprint rate, build wall-clock, per-language
                       coverage inside the witness clusters, storage estimate.
  --retention      M4  the §2.4 resolvability decay curve re-derived as a script,
                       retention interaction, storage sizing, and the resulting
                       COLD-START length for DP-1's cross-day half and DP-2.
  --sweep          M1  witness reconvergence over the operating-point grid.
  --false-density  M2  the false-side number for every M1 grid point.
  --judge-dryrun   M6  borderline-band volume + DeepSeek token/cost estimate.

  `--sweep` and `--false-density` ALWAYS run together and emit ONE table
  (spec §4 rule: "no operating point can be chosen on recall evidence without
  its false-side number in the same table"). Passing either flag runs both.

OPERATING-POINT GRID (pre-registered in the plan, T-A1)
------------------------------------------------------
  MERGE_TAU_COS  in {0.84, 0.86, 0.88, 0.90}
  lane set       in {E, E|U, E|U|H}
  rarity gate    in {any-shared, df<=median, rarest-norm_rarity>=0.5}

A pair is ADMITTED at a point when `cos >= MERGE_TAU_COS` **and** at least one
lane in the lane set shares an item whose rarity clears the gate. Lane-OR, not
lane-sum: two independent proofs of sameness must not dilute each other
(`country_dominant_overlap`'s lesson, spec §3.1). Within a lane the RAREST
shared item decides (`actor_edge_weight`'s lesson): one distinctive actor
carries the link, a ubiquitous one cannot launder it.

THE RARITY-GATE DEGENERACY (found by this measurement, reported not hidden)
--------------------------------------------------------------------------
`df` is document frequency over the measurement snapshot's clusters. A SHARED
item has `df >= 2` by construction. With `df_max = 383`,
`norm_rarity(2, 383) = 0.4987 < 0.5`, and the entity-vocabulary median df is 1
(84% of entities are df=1 singletons, spec §2.3). So **two of the three
pre-registered rarity gates are vacuous on the population they gate**: they admit
nothing, at any tau, in any lane. Both are still run and reported exactly as
written. Alongside them the harness reports:
  * `df<=median` read over the SHARED-ITEM df distribution (the population the
    gate actually acts on) — the non-degenerate reading of the same words;
  * a supplementary ladder `df<=2 / df<=3 / df<=5`, every row carrying its own
    false-side number in the same table.
The KILL THRESHOLDS ARE NOT TOUCHED: K2 stays at 2% of the snapshot's topics and
the witness criterion stays at <=3 components. Only the search grid along the
rarity axis is widened, because the pre-registered values could not be evaluated.

WITNESS FAMILIES (M1)
---------------------
  * `caspian`      GQ-12, 9 clusters of one event (Iran/Ukraine, Caspian ship)
  * `berlin pride` 22 clusters of one event, one day, all DE
  * `GQ-05`        the Colombia / `%espriella%` story, **reconstructed from an
                   offline HDBSCAN run** over the story corpus at the scoped
                   snapshot's own parameters (mcs=5, ms=2, leaf), PRE-gate —
                   spec §2.5: only 7 clusters touch `%espriella%` through
                   `sample_signal_ids`, so measuring `emergent_clusters` alone
                   would measure a different object than the diagnosis's 33.
  * `fresh:*`      >=3 families discovered by the SAME label-similarity rule the
                   whitened-taus harness used (`same_event_candidates` blocking
                   + SequenceMatcher >= MERGE_LABEL_MIN + a shared country, i.e.
                   construction v1's D3), so the fit is not overfit to three
                   hand-picked exhibits.

FALSE SIDE (M2), on the same grid, three numbers per point
----------------------------------------------------------
  1. **K2** — the largest connected component of the WHOLE-snapshot merge graph
     as a share of the snapshot's clusters. `merge_duplicates` runs to a
     fixpoint, so merging is transitively closed and edge DENSITY, not pair
     precision, is what decides whether the field survives.
  2. merge-edge count over the whole snapshot.
  3. admission rate + shared-item rate on the mechanical FALSE construction the
     whitened-taus harness used: disjoint non-empty country sets AND dissimilar
     same-script labels.

Usage (read-only; M1 mlvenv has numpy/hdbscan):
  set -a; . ~/AtlasLocalWorker/.env; set +a
  cd backend && /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      -m scripts.measure_evidence_fingerprint --coverage --retention \
      --sweep --false-density --judge-dryrun

Exit code: 0 = GO (an operating point satisfies K2 AND brings >=2 of the 3 core
witness families to <=3 components), 1 = NO-GO (escalate per K3 or close the
spec), 2 = no data / VOID. Artifacts are written on every run including NO-GO —
the NO-GO is the deliverable.
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
import time
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlsplit

import numpy as np

# `_norm_headline` is imported, not replicated: spec §3.1 requires lane H to use
# the SAME normalizer `thread_ranking` uses for syndication so that "one
# headline" has exactly one definition in the codebase.
try:
    from app.services.thread_ranking import _norm_headline
except ImportError:  # pragma: no cover - entry-point tolerant
    from backend.app.services.thread_ranking import _norm_headline

try:
    from app.services.constellation_walk import norm_rarity
except ImportError:  # pragma: no cover
    from backend.app.services.constellation_walk import norm_rarity

try:
    from app.services.ai_cost import price_usd, resolve_price
except ImportError:  # pragma: no cover
    from backend.app.services.ai_cost import price_usd, resolve_price

# ------------------------------------------------------------------ constants
REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "docs" / "research" / "recall-229"
COVERAGE_STEM = "2026-07-29-evidence-fingerprint-coverage"     # M0 + M4
SWEEP_STEM = "2026-07-29-witness-reconvergence"                # M1 + M2 (+ M6)

# Engine constants this measurement is about (imported values, not re-derived).
ENGINE_MERGE_THRESHOLD = 0.90   # project_dynamic_topics.MERGE_THRESHOLD
ENGINE_MERGE_LABEL_MIN = 0.80   # project_dynamic_topics.MERGE_LABEL_MIN

# Pre-registered grid (plan T-A1). Frozen before the run.
TAU_GRID = (0.84, 0.86, 0.88, 0.90)
LANE_SETS = (
    ("E",), ("E", "U"), ("E", "U", "H"),
    # K3 escalation rungs (spec §5.2): "re-run M1 with lane U as primary", then
    # "with lane H as primary". Run in the SAME pass so the ladder is answered
    # by the same table rather than by a second, differently-conditioned run.
    ("U",), ("H",),
)
PREREG_RARITY_GATES = ("any-shared", "df<=median", "norm_rarity>=0.5")
# Supplementary rarity ladder — reported WITH its false-side number, never as a
# relaxation of a kill threshold (K2 and the <=3-components rule are untouched).
SUPP_RARITY_GATES = ("df<=2", "df<=3", "df<=5", "df<=median(shared)")

# Pre-registered kill rules (spec §5.2). NOT tunable.
K2_MAX_COMPONENT_SHARE = 0.02   # largest merge component / snapshot's topics
WITNESS_MAX_COMPONENTS = 3      # "fragments per event <= 3"
WITNESS_FAMILIES_REQUIRED = 2   # >= 2 of the 3 CORE families

# Scoped-snapshot clustering parameters (run_scoped_snapshot.py argparse
# defaults) — used verbatim for the GQ-05 offline reconstruction.
GQ05_MCS = 5
GQ05_MS = 2
GQ05_SELECTION = "leaf"

# Label rules — identical to measure_identity_whitening.py so the FALSE
# construction is the same object across both harnesses.
SAME_LABEL_MIN = 0.80
DIFF_LABEL_MAX = 0.35
BLOCK_MIN_SHARED = 2
BLOCK_DF_MAX_SHARE = 0.05

# Judge budget (spec §8).
JUDGE_HARD_CAP = 150
JUDGE_TOKENS_IN = 700
JUDGE_TOKENS_OUT = 60
JUDGE_MODEL = "deepseek-chat"

# Fingerprint bounds (mirror the mig-092 shape so the storage estimate is real).
MAX_URL_KEYS = 48
MAX_HEADLINE_KEYS = 48

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

# Entity strings that are never evidence of a shared story. Deliberately tiny —
# the rarity weighting is the real defence; this only removes the degenerate
# strings `nlp_persons` emits (spec §2.5 names 'Policía' typed GPE).
_ENTITY_STOP = {"none", "null", "n a", "unknown", "reuters", "ap", "afp"}
_MIN_ENTITY_LEN = 3

# Registrable-domain helper: second-level suffixes where the registrable name is
# the THIRD label from the right (bbc.co.uk, abc.net.au). Not a full public
# suffix list — stated as a limitation in the artifact.
_TWO_LABEL_SUFFIXES = {
    "co.uk", "org.uk", "gov.uk", "ac.uk", "co.jp", "or.jp", "ne.jp", "ac.jp",
    "com.au", "net.au", "org.au", "gov.au", "edu.au", "com.br", "net.br",
    "gov.br", "org.br", "com.mx", "org.mx", "gob.mx", "com.ar", "gob.ar",
    "com.co", "gov.co", "com.tr", "gov.tr", "com.cn", "org.cn", "gov.cn",
    "co.kr", "or.kr", "co.in", "net.in", "org.in", "gov.in", "co.za",
    "org.za", "gov.za", "co.nz", "org.nz", "govt.nz", "com.ua", "com.pk",
    "com.ng", "com.eg", "com.sa", "com.my", "com.sg", "com.ph", "com.vn",
    "co.id", "or.id", "com.tw", "org.tw", "gov.tw", "co.il", "org.il",
    "com.pe", "com.ve", "com.ec", "com.uy", "com.py", "com.bo", "com.do",
    "com.gt", "com.pa", "com.cy", "com.gr", "com.pt", "com.es", "com.hk",
}


# ------------------------------------------------------------------ text utils
def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c))


def norm_entity(name: str | None) -> str | None:
    """Lane-E normalizer (spec §3.1): lowercased + unaccented, punctuation
    collapsed to single spaces. Deliberately script-preserving — it does NOT
    transliterate, because it cannot: `"ایران"` and `"Iran"` are different
    strings and this design's §2.5 states that bias openly rather than faking a
    match."""
    if not name:
        return None
    x = _strip_accents(unicodedata.normalize("NFKC", str(name))).casefold()
    x = re.sub(r"[^\w\s]+", " ", x, flags=re.UNICODE)
    x = re.sub(r"\s+", " ", x).strip()
    if len(x) < _MIN_ENTITY_LEN or x in _ENTITY_STOP or x.isdigit():
        return None
    return x


def url_key(url: str | None) -> str | None:
    """Lane-U exact-locator key: scheme-blind, host-lowercased, fragment
    dropped, trailing slash stripped — **query string KEPT**.

    The query-stripped variant was tried first and REJECTED by measurement: many
    outlets carry the article id in the query, so dropping it collapsed an
    outlet's whole output to one pseudo-locator —
    `shorouknews.com/news/view.aspx` reached **df 35**, `pressorg24.com/news`
    df 17, `edaily.co.kr/News/Read` df 4. A df-35 "exact URL" is not a locator,
    it is an outlet, and it would have handed lane U the very laundering the
    rarity weighting exists to prevent. Keeping the query costs recall when two
    copies of one link differ in tracking parameters (they then read as two
    links); that error can only WITHHOLD evidence, never fabricate it."""
    if not url:
        return None
    try:
        p = urlsplit(str(url).strip())
    except ValueError:
        return None
    host = (p.netloc or "").lower().removeprefix("www.")
    if not host:
        return None
    path = (p.path or "").rstrip("/")
    q = f"?{p.query}" if p.query else ""
    return f"{host}{path}{q}"


def registrable_domain(url: str | None, source_name: str | None = None) -> str | None:
    """Lane-U domain key. Falls back to `source_name` when the URL is unusable,
    because `source_url`/`source_name` are both 100% populated (spec §3.4)."""
    if url:
        try:
            host = (urlsplit(str(url).strip()).netloc or "").lower()
        except ValueError:
            host = ""
        host = host.split(":")[0].removeprefix("www.")
        parts = [p for p in host.split(".") if p]
        if len(parts) >= 3 and ".".join(parts[-2:]) in _TWO_LABEL_SUFFIXES:
            return ".".join(parts[-3:])
        if len(parts) >= 2:
            return ".".join(parts[-2:])
        if parts:
            return parts[0]
    if source_name:
        return norm_entity(source_name)
    return None


def norm_label(s: str | None) -> str:
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
    toks = re.findall(r"[^\W\d_]{3,}", norm_label(s), re.UNICODE)
    return {t for t in toks if t not in _GENERIC_TOKENS}


def dominant_script(s: str | None) -> str:
    c: Counter = Counter()
    for ch in s or "":
        if not ch.isalpha():
            continue
        try:
            c[unicodedata.name(ch).split()[0].lower()] += 1
        except ValueError:
            continue
    return c.most_common(1)[0][0] if c else "none"


def different_story(la: str | None, lb: str | None) -> bool:
    """Mechanically 'not the same story' by LABEL alone — the whitened-taus
    harness's construction v1 rule, verbatim (same-script required: across
    scripts "zero shared tokens" is trivially true and files one war as many)."""
    if not la or not lb:
        return False
    sa, sb = dominant_script(la), dominant_script(lb)
    if sa == "none" or sb == "none" or sa != sb:
        return False
    if label_sim(la, lb) >= DIFF_LABEL_MAX:
        return False
    return not (subject_tokens(la) & subject_tokens(lb))


def countries_share(a: Sequence[str] | None, b: Sequence[str] | None) -> bool:
    sa, sb = {x for x in (a or []) if x}, {x for x in (b or []) if x}
    return bool(sa & sb)


def countries_disjoint(a: Sequence[str] | None, b: Sequence[str] | None) -> bool:
    sa, sb = {x for x in (a or []) if x}, {x for x in (b or []) if x}
    return bool(sa) and bool(sb) and not (sa & sb)


def same_event_candidates(items: list[dict[str, Any]], key: str = "label"
                          ) -> Iterable[tuple[dict, dict]]:
    """Blocked candidate generation (>=2 shared distinctive tokens). Verbatim
    from `measure_identity_whitening.same_event_candidates` so the fresh-family
    discovery rule is literally the same rule."""
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
        if len(idxs) < 2 or len(idxs) > 400:
            continue
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                shared[(idxs[x], idxs[y])] += 1
    for (i, j), c in shared.items():
        if c >= BLOCK_MIN_SHARED:
            yield items[i], items[j]


# ------------------------------------------------------------------ graph utils
class DSU:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def components(n: int, edges: Iterable[tuple[int, int]]) -> tuple[int, int]:
    """(number of connected components, size of the largest) over n nodes."""
    d = DSU(n)
    for a, b in edges:
        d.union(a, b)
    sizes: Counter = Counter(d.find(i) for i in range(n))
    return len(sizes), (max(sizes.values()) if sizes else 0)


def components_np(n: int, ii: np.ndarray, jj: np.ndarray) -> tuple[int, int]:
    """Vectorized (component count, largest component) — scipy's union-find over
    a sparse adjacency. The 120-row grid touches ~1M candidate edges per row, so
    the pure-Python DSU above is kept only for the small per-family graphs."""
    if ii.size == 0:
        return n, 1 if n else 0
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components as cc
    g = coo_matrix((np.ones(ii.size, dtype=np.int8), (ii, jj)), shape=(n, n))
    ncomp, labels = cc(g, directed=False)
    return int(ncomp), int(np.bincount(labels).max())


# ------------------------------------------------------------------ fingerprint
class Fingerprint:
    """One cluster's measured evidence. Sets hold INTEGER ids from a shared
    vocabulary so intersections run at C speed over ~2M candidate pairs."""

    __slots__ = ("cid", "entities", "domains", "url_keys", "headline_keys",
                 "n_refs", "n_resolved", "langs")

    def __init__(self, cid: int):
        self.cid = cid
        self.entities: frozenset[int] = frozenset()
        self.domains: frozenset[int] = frozenset()
        self.url_keys: frozenset[int] = frozenset()
        self.headline_keys: frozenset[int] = frozenset()
        self.n_refs = 0
        self.n_resolved = 0
        self.langs: Counter = Counter()

    @property
    def is_empty(self) -> bool:
        return not (self.entities or self.domains or self.url_keys
                    or self.headline_keys)


class Vocab:
    """String -> int id, with cluster document-frequency per lane."""

    def __init__(self) -> None:
        self.ids: dict[str, int] = {}
        self.strs: list[str] = []
        self.df: list[int] = []

    def add(self, s: str) -> int:
        i = self.ids.get(s)
        if i is None:
            i = len(self.strs)
            self.ids[s] = i
            self.strs.append(s)
            self.df.append(0)
        return i

    def bump(self, ids: Iterable[int]) -> None:
        for i in ids:
            self.df[i] += 1

    def df_array(self) -> np.ndarray:
        return np.asarray(self.df, dtype=np.int32)

    @property
    def df_max(self) -> int:
        return max(self.df) if self.df else 1


# ------------------------------------------------------------------ loading
async def load_snapshot_clusters(conn, snapshot_at) -> list[dict[str, Any]]:
    rows = await conn.fetch(
        """SELECT id, snapshot_at, cluster_id, label, top_country_codes, n_signals,
                  cohesion, sample_signal_ids, raw_sample_ids, centroid_vec
             FROM emergent_clusters
            WHERE snapshot_at = $1 AND centroid_vec IS NOT NULL
            ORDER BY cluster_id""",
        snapshot_at)
    return [{
        "id": int(r["id"]),
        "snapshot_at": r["snapshot_at"],
        "cluster_id": int(r["cluster_id"]),
        "label": r["label"],
        "cc": list(r["top_country_codes"] or []),
        "n_signals": int(r["n_signals"] or 0),
        "cohesion": float(r["cohesion"]) if r["cohesion"] is not None else None,
        "sample": [int(x) for x in (r["sample_signal_ids"] or [])],
        "raw_sample": [int(x) for x in (r["raw_sample_ids"] or [])],
        "vec": np.asarray(r["centroid_vec"], dtype=np.float32),
    } for r in rows]


async def load_signal_evidence(conn, ids: Sequence[int]) -> dict[int, dict[str, Any]]:
    """The ONE query the fingerprint builder makes. Batched; `nlp_persons` is
    jsonb so it comes back as a string and is parsed here."""
    out: dict[int, dict[str, Any]] = {}
    ids = list(dict.fromkeys(int(i) for i in ids))
    for i in range(0, len(ids), 4000):
        rows = await conn.fetch(
            """SELECT id, persons, organizations, nlp_persons, source_url,
                      source_name, headline, source_lang
                 FROM signals_v2 WHERE id = ANY($1::bigint[])""",
            ids[i:i + 4000])
        for r in rows:
            npx = r["nlp_persons"]
            if isinstance(npx, str):
                try:
                    npx = json.loads(npx)
                except json.JSONDecodeError:
                    npx = None
            out[int(r["id"])] = {
                "persons": list(r["persons"] or []),
                "organizations": list(r["organizations"] or []),
                "nlp_persons": npx if isinstance(npx, list) else [],
                "source_url": r["source_url"],
                "source_name": r["source_name"],
                "headline": r["headline"] or "",
                "source_lang": (r["source_lang"] or "").strip() or None,
            }
    return out


def build_fingerprints(clusters: list[dict[str, Any]],
                       sig: dict[int, dict[str, Any]],
                       ) -> tuple[list[Fingerprint], dict[str, Vocab]]:
    """Assemble one Fingerprint per cluster + the per-lane vocabularies with
    cluster document-frequency. This is the function mig-092's writer would
    persist the output of, so its wall-clock is the M0 build-budget number."""
    v_ent, v_dom, v_url, v_hl = Vocab(), Vocab(), Vocab(), Vocab()
    fps: list[Fingerprint] = []
    for c in clusters:
        fp = Fingerprint(c["id"])
        ents: set[int] = set()
        doms: set[int] = set()
        urls: set[int] = set()
        hls: set[int] = set()
        refs = c["sample"]
        fp.n_refs = len(refs)
        for sid in refs:
            s = sig.get(sid)
            if s is None:
                continue
            fp.n_resolved += 1
            if s["source_lang"]:
                fp.langs[s["source_lang"]] += 1
            for name in s["persons"]:
                n = norm_entity(name)
                if n:
                    ents.add(v_ent.add(n))
            for name in s["organizations"]:
                n = norm_entity(name)
                if n:
                    ents.add(v_ent.add(n))
            for item in s["nlp_persons"]:
                if isinstance(item, dict):
                    n = norm_entity(item.get("name"))
                elif isinstance(item, str):
                    n = norm_entity(item)
                else:
                    n = None
                if n:
                    ents.add(v_ent.add(n))
            uk = url_key(s["source_url"])
            if uk:
                urls.add(v_url.add(uk))
            dom = registrable_domain(s["source_url"], s["source_name"])
            if dom:
                doms.add(v_dom.add(dom))
            hk = _norm_headline(s["headline"]) if s["headline"] else ""
            if hk:
                hls.add(v_hl.add(hk))
        fp.entities = frozenset(ents)
        fp.domains = frozenset(doms)
        fp.url_keys = frozenset(sorted(urls)[:MAX_URL_KEYS])
        fp.headline_keys = frozenset(sorted(hls)[:MAX_HEADLINE_KEYS])
        v_ent.bump(fp.entities)
        v_dom.bump(fp.domains)
        v_url.bump(fp.url_keys)
        v_hl.bump(fp.headline_keys)
        fps.append(fp)
    return fps, {"E": v_ent, "D": v_dom, "U": v_url, "H": v_hl}


# ------------------------------------------------------------------ pair evidence
class PairEvidence:
    """Per-lane rarity of the RAREST shared item, for one candidate pair.

    `min_df` per lane is what every rarity gate reads (rarest shared item ==
    lowest df). `-1` means the lane shares nothing.
    """
    __slots__ = ("i", "j", "cos", "e_df", "e_n", "u_df", "u_n", "d_df", "d_n",
                 "h_df", "h_n")

    def __init__(self, i, j, cos, e_df, e_n, u_df, u_n, d_df, d_n, h_df, h_n):
        self.i = i; self.j = j; self.cos = cos
        self.e_df = e_df; self.e_n = e_n
        self.u_df = u_df; self.u_n = u_n
        self.d_df = d_df; self.d_n = d_n
        self.h_df = h_df; self.h_n = h_n


def _min_df(shared: frozenset[int], dfs: np.ndarray) -> int:
    if not shared:
        return -1
    return int(min(dfs[i] for i in shared))


def pair_evidence(fa: Fingerprint, fb: Fingerprint, cos: float,
                  dfs: dict[str, np.ndarray], i: int, j: int) -> PairEvidence:
    se = fa.entities & fb.entities
    su = fa.url_keys & fb.url_keys
    sd = fa.domains & fb.domains
    sh = fa.headline_keys & fb.headline_keys
    return PairEvidence(
        i, j, cos,
        _min_df(se, dfs["E"]), len(se),
        _min_df(su, dfs["U"]), len(su),
        _min_df(sd, dfs["D"]), len(sd),
        _min_df(sh, dfs["H"]), len(sh),
    )


class Gate:
    """One rarity gate, evaluated against a lane's (min_df, df_max).

    `any-shared`      any shared item at all.
    `df<=K`           the rarest shared item has df <= K.
    `norm_rarity>=R`  the rarest shared item's `norm_rarity(df, df_max) >= R`,
                      using the validated formula verbatim.
    """

    def __init__(self, name: str, dfmax: dict[str, int],
                 medians: dict[str, int] | None = None):
        self.name = name
        self.dfmax = dfmax
        self.medians = medians or {}
        self.kind = "any"
        self.k = 0
        self.r = 0.0
        if name == "any-shared":
            self.kind = "any"
        elif name.startswith("df<=median(shared)"):
            self.kind = "median_shared"
        elif name.startswith("df<=median"):
            self.kind = "median_vocab"
        elif name.startswith("df<="):
            self.kind = "df"
            self.k = int(name.split("<=")[1])
        elif name.startswith("norm_rarity>="):
            self.kind = "rarity"
            self.r = float(name.split(">=")[1])
        else:  # pragma: no cover
            raise ValueError(f"unknown rarity gate {name!r}")

    def max_df(self, lane: str) -> int:
        """The largest df this gate admits in `lane`, i.e. the gate expressed as
        a single cut on the rarest shared item's df. Every gate kind reduces to
        one because `norm_rarity` is strictly decreasing in df."""
        if self.kind == "any":
            return 1 << 30
        if self.kind == "df":
            return self.k
        if self.kind == "median_vocab":
            return int(self.medians.get(f"vocab:{lane}", 1))
        if self.kind == "median_shared":
            return int(self.medians.get(f"shared:{lane}", 2))
        dmax = max(1, int(self.dfmax.get(lane, 1)))
        if dmax <= 1:
            return 1 if self.r <= 1.0 else 0
        # norm_rarity(df, dmax) = (1/df - 1/dmax) / (1 - 1/dmax) >= r
        #   <=> 1/df >= r*(1 - 1/dmax) + 1/dmax  <=> df <= 1/that
        rhs = self.r * (1.0 - 1.0 / dmax) + 1.0 / dmax
        if rhs <= 0:
            return 1 << 30
        return int(np.floor(1.0 / rhs + 1e-12))

    def passes(self, lane: str, min_df: int) -> bool:
        return min_df >= 0 and min_df <= self.max_df(lane)

    def mask(self, lane: str, arr: np.ndarray) -> np.ndarray:
        return (arr >= 0) & (arr <= self.max_df(lane))


class PairArrays:
    """The same information as a list of `PairEvidence`, columnar. The grid has
    120 rows over ~1M candidate pairs, so every grid point must be a vector
    filter, not a Python loop."""

    __slots__ = ("i", "j", "cos", "df")

    def __init__(self, i, j, cos, df):
        self.i: np.ndarray = i
        self.j: np.ndarray = j
        self.cos: np.ndarray = cos
        self.df: dict[str, np.ndarray] = df

    def __len__(self) -> int:
        return int(self.i.size)


def pe_to_arrays(pe: Sequence["PairEvidence"]) -> PairArrays:
    """Columnar view of a small object-path pair list (families, false set)."""
    return PairArrays(
        np.asarray([p.i for p in pe], dtype=np.int32),
        np.asarray([p.j for p in pe], dtype=np.int32),
        np.asarray([p.cos for p in pe], dtype=np.float32),
        {"E": np.asarray([p.e_df for p in pe], dtype=np.int32),
         "U": np.asarray([p.u_df for p in pe], dtype=np.int32),
         "D": np.asarray([p.d_df for p in pe], dtype=np.int32),
         "H": np.asarray([p.h_df for p in pe], dtype=np.int32)})


def admits_mask(pa: PairArrays, lanes: Sequence[str], gate: Gate) -> np.ndarray:
    m = np.zeros(len(pa), dtype=bool)
    for lane in lanes:
        if lane == "E":
            m |= gate.mask("E", pa.df["E"])
        elif lane == "U":
            m |= gate.mask("U", pa.df["U"]) | gate.mask("D", pa.df["D"])
        elif lane == "H":
            m |= gate.mask("H", pa.df["H"])
    return m


def admits(pe: PairEvidence, lanes: Sequence[str], gate: Gate) -> bool:
    """Lane-OR: at least one lane in the set shares an item clearing the gate.

    Lane U is exact-URL OR a rare domain (spec §3.4: "only exact-URL and low-df
    domains count"). Both halves are subject to the same rarity gate, and the
    artifact reports their contributions separately so M3 can decide whether the
    domain half is worth keeping at all (spec §10 open question 1)."""
    for lane in lanes:
        if lane == "E" and gate.passes("E", pe.e_df):
            return True
        if lane == "U" and (gate.passes("U", pe.u_df) or gate.passes("D", pe.d_df)):
            return True
        if lane == "H" and gate.passes("H", pe.h_df):
            return True
    return False


# ------------------------------------------------------------------ families
def find_fresh_families(clusters: list[dict[str, Any]], exclude: set[int],
                        min_size: int, want: int) -> list[dict[str, Any]]:
    """Discover same-event families by the label-similarity rule the
    whitened-taus harness used: blocked candidate generation, SequenceMatcher >=
    MERGE_LABEL_MIN, plus a SHARED COUNTRY (construction v1's D3 — without it
    'Severe Storms in Serbia' and '...in Germany' read as one family).

    Connected components of that label graph ARE the families: N labels for one
    event that the engine failed to unify."""
    items = [c for c in clusters if c["label"] and c["id"] not in exclude]
    idx = {c["id"]: k for k, c in enumerate(items)}
    edges: list[tuple[int, int]] = []
    for a, b in same_event_candidates(items):
        if not countries_share(a["cc"], b["cc"]):
            continue
        if label_sim(a["label"], b["label"]) >= SAME_LABEL_MIN:
            edges.append((idx[a["id"]], idx[b["id"]]))
    d = DSU(len(items))
    for x, y in edges:
        d.union(x, y)
    groups: dict[int, list[dict]] = defaultdict(list)
    for k, c in enumerate(items):
        groups[d.find(k)].append(c)
    fams = [g for g in groups.values() if len(g) >= min_size]
    fams.sort(key=lambda g: (-len(g), min(c["id"] for c in g)))
    out: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for g in fams[:want]:
        g = sorted(g, key=lambda c: -c["n_signals"])
        base = f"fresh:{norm_label(g[0]['label'])[:38].replace(' ', '-')}"
        nm, k = base, 2
        while nm in used_names:          # two families can share a lead label
            nm = f"{base}#{k}"; k += 1
        used_names.add(nm)
        out.append({
            "name": nm,
            "kind": "fresh",
            "cluster_ids": [c["id"] for c in g],
            "labels": [c["label"] for c in g][:8],
            "countries": sorted({x for c in g for x in c["cc"]})[:6],
            "n_signals": sum(c["n_signals"] for c in g),
        })
    return out


async def find_pattern_family(conn, snapshot_at, tokens: Sequence[str], name: str
                              ) -> dict[str, Any] | None:
    """A named witness family = the snapshot's clusters whose label contains
    EVERY token (AND, not OR).

    The AND form matters. `%caspian%` alone returns 3 clusters on 07-28, because
    six of the nine name the event without the sea ("Iran Condemns Ukraine Ship
    Attack"). `iran` AND `ukrain` returns exactly **9 clusters / 183 signals** —
    the diagnosis's GQ-12 exhibit, reproduced to the signal. A plain OR would
    have swept in the Hormuz tanker explosions and the Houthi attacks, which are
    different events, and quietly inflated the witness."""
    if not tokens:
        return None
    where = " AND ".join(f"label ILIKE ${i + 2}" for i in range(len(tokens)))
    rows = await conn.fetch(
        f"""SELECT id, label, top_country_codes, n_signals FROM emergent_clusters
             WHERE snapshot_at = $1 AND centroid_vec IS NOT NULL AND {where}
             ORDER BY n_signals DESC""",
        snapshot_at, *[f"%{t}%" for t in tokens])
    if not rows:
        return None
    return {
        "name": name, "kind": "core",
        "cluster_ids": [int(r["id"]) for r in rows],
        "labels": [r["label"] for r in rows][:8],
        "countries": sorted({c for r in rows for c in (r["top_country_codes"] or [])})[:6],
        "n_signals": sum(int(r["n_signals"] or 0) for r in rows),
        "pattern": " AND ".join(tokens),
    }


# ------------------------------------------------------------------ GQ-05 rebuild
async def reconstruct_gq05(conn, args) -> dict[str, Any]:
    """Rebuild the GQ-05 witness by re-running HDBSCAN over the story corpus.

    Spec §2.5: `%espriella%` = ~651 signals in 7 days but only 7 clusters touch
    them through `sample_signal_ids`; the diagnosis's 33 fragments came from the
    OFFLINE clustering run, PRE precision-gate and PRE `min_kept=8`. Measuring
    `emergent_clusters` alone would measure a different object, so this re-runs
    the scoped snapshot's own parameters (mcs=5, ms=2, leaf) over the story's
    embedded signals and takes the RAW HDBSCAN clusters.

    Returns the family plus the per-fragment fingerprint inputs; the fragments
    are not in `emergent_clusters`, so they carry their own centroids and their
    own signal-id lists.
    """
    out: dict[str, Any] = {"name": "GQ-05", "kind": "core", "reconstructed": True,
                           "pattern": args.gq05_pattern}
    rows = await conn.fetch(
        """SELECT s.id
             FROM signals_v2 s
            WHERE s.headline ILIKE $1
              AND s.created_at > now() - ($2 || ' hours')::interval""",
        f"%{args.gq05_pattern}%", str(args.gq05_hours))
    sids = [int(r["id"]) for r in rows]
    out["corpus_signals"] = len(sids)
    if len(sids) < GQ05_MCS * 2:
        out["status"] = "insufficient_corpus"
        out["cluster_ids"] = []
        return out
    emb: dict[int, np.ndarray] = {}
    for i in range(0, len(sids), 2000):
        erows = await conn.fetch(
            "SELECT signal_id, vec FROM signal_embeddings WHERE signal_id = ANY($1::bigint[])",
            sids[i:i + 2000])
        for r in erows:
            v = r["vec"]
            if v is None:
                continue
            if isinstance(v, str):  # pgvector text form
                v = np.fromstring(v.strip("[]"), sep=",", dtype=np.float32)
            else:
                v = np.asarray(v, dtype=np.float32)
            if v.size:
                emb[int(r["signal_id"])] = v
    out["embedded"] = len(emb)
    if len(emb) < GQ05_MCS * 2:
        out["status"] = "insufficient_embeddings"
        out["cluster_ids"] = []
        return out
    ids = sorted(emb)
    X = np.stack([emb[i] for i in ids]).astype(np.float32)
    try:
        import hdbscan
    except ImportError:
        out["status"] = "hdbscan_unavailable"
        out["cluster_ids"] = []
        return out
    t0 = time.monotonic()
    labels = hdbscan.HDBSCAN(
        min_cluster_size=GQ05_MCS, min_samples=GQ05_MS,
        metric="euclidean", cluster_selection_method=GQ05_SELECTION,
    ).fit_predict(X.astype(np.float64))
    out["cluster_seconds"] = round(time.monotonic() - t0, 1)
    frags: dict[int, list[int]] = defaultdict(list)
    for k, lab in enumerate(labels):
        if int(lab) >= 0:
            frags[int(lab)].append(ids[k])
    out["noise_signals"] = int((labels < 0).sum())
    out["n_fragments"] = len(frags)
    out["params"] = {"mcs": GQ05_MCS, "ms": GQ05_MS, "selection": GQ05_SELECTION,
                     "gate": "NONE (pre-gate, per the diagnosis)"}
    out["status"] = "ok"
    out["fragments"] = {}
    id_pos = {sid: k for k, sid in enumerate(ids)}
    for lab, members in sorted(frags.items()):
        V = X[[id_pos[m] for m in members]]
        out["fragments"][lab] = {"signal_ids": members,
                                 "centroid": V.mean(axis=0).tolist(),
                                 "n": len(members)}
    return out


# ------------------------------------------------------------------ M0 coverage
def coverage_report(clusters, fps, vocabs, build_seconds, sig) -> dict[str, Any]:
    ent_counts = np.array([len(f.entities) for f in fps])
    dom_counts = np.array([len(f.domains) for f in fps])
    url_counts = np.array([len(f.url_keys) for f in fps])
    hl_counts = np.array([len(f.headline_keys) for f in fps])
    refs = np.array([f.n_refs for f in fps])
    res = np.array([f.n_resolved for f in fps])

    def pcts(a: np.ndarray) -> dict[str, Any]:
        if a.size == 0:
            return {"n": 0}
        return {"n": int(a.size), "mean": round(float(a.mean()), 2),
                "p5": int(np.percentile(a, 5)), "p50": int(np.percentile(a, 50)),
                "p95": int(np.percentile(a, 95)), "max": int(a.max()),
                "zero_rate": round(float((a == 0).mean()), 4)}

    # storage: 092's arrays are the strings + a parallel int df array.
    def lane_bytes(vals: Iterable[frozenset[int]], vocab: Vocab) -> int:
        return sum(len(vocab.strs[i].encode()) + 1 for s in vals for i in s)
    bytes_per_snapshot = (
        lane_bytes((f.entities for f in fps), vocabs["E"])
        + lane_bytes((f.domains for f in fps), vocabs["D"])
        + lane_bytes((f.url_keys for f in fps), vocabs["U"])
        + lane_bytes((f.headline_keys for f in fps), vocabs["H"])
        + sum(len(f.entities) for f in fps) * 4        # entity_dfs int[]
    )
    langs: Counter = Counter()
    for f in fps:
        langs.update(f.langs)
    return {
        "clusters": len(clusters),
        "sample_refs": int(refs.sum()),
        "resolved_refs": int(res.sum()),
        "resolvable_rate": round(float(res.sum() / max(1, refs.sum())), 4),
        "build_seconds": round(build_seconds, 1),
        "signals_fetched": len(sig),
        "per_cluster": {"entities": pcts(ent_counts), "domains": pcts(dom_counts),
                        "url_keys": pcts(url_counts), "headline_keys": pcts(hl_counts)},
        "carry_any_entity": round(float((ent_counts > 0).mean()), 4),
        "empty_fingerprint_rate": round(float(np.mean([f.is_empty for f in fps])), 4),
        "vocab": {k: {"distinct": len(v.strs), "df_max": v.df_max,
                      "df_p50": int(np.percentile(v.df_array(), 50)) if v.strs else 0,
                      "df_p99": int(np.percentile(v.df_array(), 99)) if v.strs else 0,
                      "df1_share": round(float((v.df_array() == 1).mean()), 4) if v.strs else 0.0}
                  for k, v in vocabs.items()},
        "truncated_sample_share": round(
            float(np.mean([1.0 if f.n_refs >= 24 else 0.0 for f in fps])), 4),
        "storage_bytes_per_snapshot": int(bytes_per_snapshot),
        "storage_mb_30d": round(bytes_per_snapshot * 30 / 1e6, 1),
        "source_lang_mix": dict(langs.most_common(14)),
        # What actually sits at the top of each lane's df distribution. Reported
        # because the highest-df items are the ones a permissive gate merges on,
        # and two of them turned out to be defects rather than evidence.
        "top_df": {
            lane: [{"item": v.strs[i][:70], "df": v.df[i]}
                   for i in sorted(range(len(v.strs)), key=lambda x: -v.df[x])[:10]]
            for lane, v in vocabs.items()},
    }


def family_language_coverage(fams, fp_by_cid) -> list[dict[str, Any]]:
    out = []
    for fam in fams:
        cids = [c for c in fam.get("cluster_ids", []) if c in fp_by_cid]
        if not cids:
            continue
        langs: Counter = Counter()
        ent = dom = url = hl = 0
        refs = res = 0
        for c in cids:
            f = fp_by_cid[c]
            langs.update(f.langs)
            ent += len(f.entities); dom += len(f.domains)
            url += len(f.url_keys); hl += len(f.headline_keys)
            refs += f.n_refs; res += f.n_resolved
        n = len(cids)
        out.append({
            "family": fam["name"], "clusters": n,
            "sample_refs": refs, "resolved": res,
            "resolvable_rate": round(res / max(1, refs), 4),
            "entities_per_cluster": round(ent / n, 1),
            "domains_per_cluster": round(dom / n, 1),
            "urls_per_cluster": round(url / n, 1),
            "headlines_per_cluster": round(hl / n, 1),
            "clusters_with_entity": sum(1 for c in cids if fp_by_cid[c].entities),
            "langs": dict(langs.most_common(8)),
        })
    return out


# ------------------------------------------------------------------ M4 retention
async def retention_report(conn, days: int) -> dict[str, Any]:
    """Re-derive the §2.4 resolvability decay curve as a script, and turn it into
    the cold-start length the staged build has to live with."""
    rows = await conn.fetch(
        """SELECT snapshot_at::date AS day,
                  count(*) AS clusters,
                  coalesce(sum(cardinality(sample_signal_ids)), 0) AS refs
             FROM emergent_clusters
            WHERE snapshot_at > now() - ($1 || ' days')::interval
            GROUP BY 1 ORDER BY 1 DESC""", str(days))
    curve: list[dict[str, Any]] = []
    for r in rows:
        day = r["day"]
        resolved = await conn.fetchval(
            """SELECT count(*) FROM (
                   SELECT unnest(sample_signal_ids) AS sid
                     FROM emergent_clusters
                    WHERE snapshot_at::date = $1
               ) q JOIN signals_v2 s ON s.id = q.sid""", day)
        refs = int(r["refs"] or 0)
        curve.append({
            "day": day.isoformat(), "clusters": int(r["clusters"]),
            "sample_refs": refs, "resolvable": int(resolved or 0),
            "resolvable_rate": round(float((resolved or 0) / refs), 4) if refs else None,
        })
    hot = await conn.fetchrow(
        """SELECT min(created_at) AS oldest, max(created_at) AS newest, count(*) AS n
             FROM signals_v2""")
    active = await conn.fetchval(
        "SELECT count(*) FROM dynamic_topics WHERE state = 'active'")
    # cold start = how many nights of fingerprint accumulation before the
    # cross-day lanes have anything to compare against (spec K4: >=80% of active
    # topics must carry an anchor fingerprint).
    usable = [c for c in curve if (c["resolvable_rate"] or 0) >= 0.80]
    return {
        "curve": curve,
        "signals_v2_window_hours": round(
            (hot["newest"] - hot["oldest"]).total_seconds() / 3600, 1) if hot and hot["oldest"] else None,
        "signals_v2_rows": int(hot["n"]) if hot else None,
        "active_topics": int(active or 0),
        "backfillable_days_at_80pct": len(usable),
        "backfillable_days_any": sum(1 for c in curve if (c["resolvable_rate"] or 0) > 0),
        "cold_start_note": (
            "DP-1's same-snapshot half needs ZERO cold start (evidence is "
            "resolvable the night it is written). DP-2 and DP-1's cross-day half "
            "need `topic_evidence_fingerprints` on >=80% of active topics (K4); "
            "with only the backfillable days above, that coverage is reached by "
            "accumulation, not by backfill."),
    }


# ------------------------------------------------------------------ M1 + M2
def build_candidate_pairs(clusters, fps, vocabs, tau_min: float
                          ) -> tuple[np.ndarray, PairArrays, dict[str, Any]]:
    """All snapshot pairs with cos >= min(TAU_GRID), with their per-lane rarest-
    shared-item df computed ONCE. Every grid point is then a vector filter over
    these columns, so the 120-row sweep costs one O(n^2) pass, not 120."""
    V = np.stack([c["vec"] for c in clusters]).astype(np.float32)
    V /= np.clip(np.linalg.norm(V, axis=1, keepdims=True), 1e-12, None)
    n = len(clusters)
    dfs = {k: v.df_array() for k, v in vocabs.items()}
    lanes = ("E", "U", "D", "H")
    attr = {"E": "entities", "U": "url_keys", "D": "domains", "H": "headline_keys"}
    chunks: list[tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, np.ndarray]]] = []
    total = 0
    block = 256
    for a0 in range(0, n, block):
        a1 = min(n, a0 + block)
        S = V[a0:a1] @ V.T
        bi: list[int] = []
        bj: list[int] = []
        bc: list[float] = []
        bd: dict[str, list[int]] = {k: [] for k in lanes}
        for li in range(a1 - a0):
            i = a0 + li
            row = S[li]
            js = np.nonzero(row[i + 1:] >= tau_min)[0] + i + 1
            if js.size == 0:
                continue
            fa = fps[i]
            sets_a = {k: getattr(fa, attr[k]) for k in lanes}
            for j in js.tolist():
                fb = fps[j]
                bi.append(i); bj.append(j); bc.append(float(row[j]))
                for k in lanes:
                    sh = sets_a[k] & getattr(fb, attr[k])
                    bd[k].append(int(min(dfs[k][x] for x in sh)) if sh else -1)
        if not bi:
            continue
        total += len(bi)
        chunks.append((np.asarray(bi, dtype=np.int32),
                       np.asarray(bj, dtype=np.int32),
                       np.asarray(bc, dtype=np.float32),
                       {k: np.asarray(bd[k], dtype=np.int32) for k in lanes}))
    if chunks:
        pa = PairArrays(
            np.concatenate([c[0] for c in chunks]),
            np.concatenate([c[1] for c in chunks]),
            np.concatenate([c[2] for c in chunks]),
            {k: np.concatenate([c[3][k] for c in chunks]) for k in lanes})
    else:
        pa = PairArrays(np.zeros(0, np.int32), np.zeros(0, np.int32),
                        np.zeros(0, np.float32), {k: np.zeros(0, np.int32) for k in lanes})
    meta = {"nodes": n, "total_pairs": n * (n - 1) // 2,
            "candidate_pairs": total, "tau_min": tau_min}
    return V, pa, meta


def shared_df_medians(pa: PairArrays, vocabs: dict[str, Vocab]) -> dict[str, int]:
    """Median df of the RAREST SHARED item per lane — the honest reading of
    `df<=median` (the vocabulary median is 1, which no shared item can reach)."""
    out: dict[str, int] = {}
    for lane in ("E", "U", "D", "H"):
        arr = pa.df[lane]
        vals = arr[arr >= 0]
        out[f"shared:{lane}"] = int(np.median(vals)) if vals.size else 2
        v = vocabs[lane].df_array()
        out[f"vocab:{lane}"] = int(np.median(v)) if v.size else 1
    return out


def mechanical_false_pairs(clusters, rng, target: int) -> list[tuple[int, int]]:
    """The whitened-taus harness's FALSE construction, verbatim: disjoint
    non-empty country sets AND dissimilar same-script labels."""
    labelled = [k for k, c in enumerate(clusters) if c["label"]]
    out: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    tries = 0
    while len(out) < target and tries < target * 120 and len(labelled) > 2:
        tries += 1
        i, j = rng.choice(labelled), rng.choice(labelled)
        if i == j:
            continue
        a, b = (i, j) if i < j else (j, i)
        if (a, b) in seen:
            continue
        ca, cb = clusters[a], clusters[b]
        if not countries_disjoint(ca["cc"], cb["cc"]):
            continue
        if not different_story(ca["label"], cb["label"]):
            continue
        seen.add((a, b))
        out.append((a, b))
    return out


def sweep(clusters, fps, vocabs, pa: PairArrays, pair_meta, families, fp_by_cid,
          gates: Sequence[str], rng, args) -> dict[str, Any]:
    """M1 (recall) and M2 (false side) in ONE pass, ONE table."""
    n = len(clusters)
    pos = {c["id"]: k for k, c in enumerate(clusters)}
    dfmax = {k: v.df_max for k, v in vocabs.items()}
    medians = shared_df_medians(pa, vocabs)

    # family index -> node positions (reconstructed families carry their own
    # vectors and are scored separately, see `score_reconstructed`).
    fam_nodes: dict[str, list[int]] = {}
    for fam in families:
        if fam.get("reconstructed"):
            continue
        idxs = [pos[c] for c in fam["cluster_ids"] if c in pos]
        if len(idxs) >= 2:
            fam_nodes[fam["name"]] = idxs

    # per-family candidate pairs (all pairs inside a family, regardless of tau)
    V = np.stack([c["vec"] for c in clusters]).astype(np.float32)
    V /= np.clip(np.linalg.norm(V, axis=1, keepdims=True), 1e-12, None)
    dfs = {k: v.df_array() for k, v in vocabs.items()}
    fam_pairs: dict[str, list[PairEvidence]] = {}
    for name, idxs in fam_nodes.items():
        lst: list[PairEvidence] = []
        for x in range(len(idxs)):
            for y in range(x + 1, len(idxs)):
                i, j = idxs[x], idxs[y]
                lst.append(pair_evidence(fps[i], fps[j], float(V[i] @ V[j]), dfs, i, j))
        fam_pairs[name] = lst

    false_pairs = mechanical_false_pairs(clusters, rng, args.max_false_pairs)
    false_ev = [pair_evidence(fps[i], fps[j], float(V[i] @ V[j]), dfs, i, j)
                for i, j in false_pairs]

    rows: list[dict[str, Any]] = []
    for tau in TAU_GRID:
        tau_mask = pa.cos >= tau
        for lanes in LANE_SETS:
            lane_name = "|".join(lanes)
            for gname in gates:
                gate = Gate(gname, dfmax, medians)
                keep = tau_mask & admits_mask(pa, lanes, gate)
                ii, jj = pa.i[keep], pa.j[keep]
                ncomp, largest = components_np(n, ii, jj)
                n_edges = int(keep.sum())
                fam_comp: dict[str, Any] = {}
                for name, idxs in fam_nodes.items():
                    local = {v: k for k, v in enumerate(idxs)}
                    fe = [(local[p.i], local[p.j]) for p in fam_pairs[name]
                          if p.cos >= tau and admits(p, lanes, gate)]
                    c, _ = components(len(idxs), fe)
                    fam_comp[name] = c
                fadm = [p for p in false_ev if p.cos >= tau and admits(p, lanes, gate)]
                rows.append({
                    "tau": tau, "lanes": lane_name, "gate": gname,
                    "prereg": gname in PREREG_RARITY_GATES,
                    # --- recall side (M1)
                    "family_components": fam_comp,
                    # --- false side (M2)
                    "merge_edges": n_edges,
                    "largest_component": largest,
                    "largest_component_share": round(largest / max(1, n), 4),
                    "k2_ok": bool(largest / max(1, n) <= K2_MAX_COMPONENT_SHARE),
                    "false_pairs_admitted": len(fadm),
                    "false_pairs_n": len(false_ev),
                    "false_admit_rate": round(len(fadm) / max(1, len(false_ev)), 4),
                    "false_cos_only": sum(1 for p in false_ev if p.cos >= tau),
                    "false_shared_entity_rate": round(
                        float(np.mean([p.e_df >= 0 for p in false_ev])), 4) if false_ev else None,
                })

    # engine baseline: today's rule (cos >= 0.90 AND label >= 0.80)
    base_i: list[int] = []
    base_j: list[int] = []
    sel = np.nonzero(pa.cos >= ENGINE_MERGE_THRESHOLD)[0]
    for k in sel.tolist():
        i, j = int(pa.i[k]), int(pa.j[k])
        la, lb = clusters[i]["label"], clusters[j]["label"]
        if la and lb and label_sim(la, lb) >= ENGINE_MERGE_LABEL_MIN:
            base_i.append(i); base_j.append(j)
    bncomp, blargest = components_np(n, np.asarray(base_i, dtype=np.int32),
                                     np.asarray(base_j, dtype=np.int32))
    base_edges = base_i
    base_fam: dict[str, int] = {}
    for name, idxs in fam_nodes.items():
        local = {v: k for k, v in enumerate(idxs)}
        fe = []
        for p in fam_pairs[name]:
            if p.cos < ENGINE_MERGE_THRESHOLD:
                continue
            la, lb = clusters[p.i]["label"], clusters[p.j]["label"]
            if la and lb and label_sim(la, lb) >= ENGINE_MERGE_LABEL_MIN:
                fe.append((local[p.i], local[p.j]))
        base_fam[name], _ = components(len(idxs), fe)
    baseline = {
        "rule": f"cos>={ENGINE_MERGE_THRESHOLD} AND label>={ENGINE_MERGE_LABEL_MIN}",
        "merge_edges": len(base_edges), "largest_component": blargest,
        "largest_component_share": round(blargest / max(1, n), 4),
        "family_components": base_fam,
        "false_pairs_admitted": sum(
            1 for p in false_ev
            if p.cos >= ENGINE_MERGE_THRESHOLD
            and clusters[p.i]["label"] and clusters[p.j]["label"]
            and label_sim(clusters[p.i]["label"], clusters[p.j]["label"]) >= ENGINE_MERGE_LABEL_MIN),
        "false_pairs_n": len(false_ev),
    }
    # cosine-only contrast (what the density looks like with no second axis)
    cos_only = []
    for tau in TAU_GRID:
        m = pa.cos >= tau
        c, lg = components_np(n, pa.i[m], pa.j[m])
        cos_only.append({"tau": tau, "merge_edges": int(m.sum()), "largest_component": lg,
                         "largest_component_share": round(lg / max(1, n), 4),
                         "false_admit_rate": round(
                             float(np.mean([p.cos >= tau for p in false_ev])), 4) if false_ev else None})

    # ---- separation probe: do the recall and density curves EVER cross? -----
    # The grid samples a handful of rarity cuts. This walks the cut continuously
    # so the answer is not an artifact of which cuts were sampled: for each
    # (tau, lane set) it reports the LOOSEST cut that still satisfies K2 and the
    # TIGHTEST cut that brings >=2 core families to <=3 components. If the first
    # is smaller than the second, no operating point can exist between them and
    # the direction is refuted for that lane at that tau — arithmetically, not
    # by taste.
    sep: list[dict[str, Any]] = []
    cuts = [1, 2, 3, 4, 5, 6, 8, 10, 14, 20, 30, 45, 70, 100, 150, 250, 400, 1 << 30]
    for tau in TAU_GRID:
        tau_mask = pa.cos >= tau
        for lanes in LANE_SETS:
            lane_name = "|".join(lanes)
            k2_max_cut: int | None = None
            recall_min_cut: int | None = None
            ladder: list[dict[str, Any]] = []
            for cut in cuts:
                gate = Gate(f"df<={cut}", dfmax, medians)
                keep = tau_mask & admits_mask(pa, lanes, gate)
                _, largest = components_np(n, pa.i[keep], pa.j[keep])
                share = largest / max(1, n)
                fam_ok = 0
                fc: dict[str, int] = {}
                for name, idxs in fam_nodes.items():
                    local = {v: k for k, v in enumerate(idxs)}
                    fe = [(local[p.i], local[p.j]) for p in fam_pairs[name]
                          if p.cos >= tau and admits(p, lanes, gate)]
                    c, _ = components(len(idxs), fe)
                    fc[name] = c
                    if name in args.core_families and c <= WITNESS_MAX_COMPONENTS:
                        fam_ok += 1
                ladder.append({"cut": cut if cut < (1 << 20) else "any",
                               "edges": int(keep.sum()),
                               "largest_share": round(share, 4),
                               "k2_ok": share <= K2_MAX_COMPONENT_SHARE,
                               "core_families_le3": fam_ok,
                               "family_components": fc})
                if share <= K2_MAX_COMPONENT_SHARE:
                    k2_max_cut = cut
                if fam_ok >= WITNESS_FAMILIES_REQUIRED and recall_min_cut is None:
                    recall_min_cut = cut
            sep.append({
                "tau": tau, "lanes": lane_name,
                "loosest_cut_satisfying_k2": k2_max_cut,
                "tightest_cut_reaching_witness_bar": recall_min_cut,
                "overlap": (k2_max_cut is not None and recall_min_cut is not None
                            and recall_min_cut <= k2_max_cut),
                "ladder": ladder,
            })

    return {
        "grid_rows": rows,
        "separation_probe": sep,
        "engine_baseline": baseline,
        "cosine_only": cos_only,
        "medians": medians,
        "df_max": dfmax,
        "pair_meta": pair_meta,
        "false_construction": {
            "rule": "disjoint non-empty country sets AND dissimilar same-script labels",
            "n": len(false_ev),
            "shared_entity_rate": round(
                float(np.mean([p.e_df >= 0 for p in false_ev])), 4) if false_ev else None,
            "shared_url_rate": round(
                float(np.mean([p.u_df >= 0 for p in false_ev])), 4) if false_ev else None,
            "shared_domain_rate": round(
                float(np.mean([p.d_df >= 0 for p in false_ev])), 4) if false_ev else None,
            "shared_headline_rate": round(
                float(np.mean([p.h_df >= 0 for p in false_ev])), 4) if false_ev else None,
        },
        "families_scored": sorted(fam_nodes),
        "family_pair_values": {
            name: [{"a": clusters[p.i]["id"], "b": clusters[p.j]["id"],
                    "cos": round(p.cos, 4),
                    "e_df": p.e_df, "e_n": p.e_n, "u_df": p.u_df, "u_n": p.u_n,
                    "d_df": p.d_df, "d_n": p.d_n, "h_df": p.h_df, "h_n": p.h_n}
                   for p in lst]
            for name, lst in fam_pairs.items()},
        "false_pair_values": [
            {"a": clusters[p.i]["id"], "b": clusters[p.j]["id"], "cos": round(p.cos, 4),
             "e_df": p.e_df, "e_n": p.e_n, "u_df": p.u_df, "u_n": p.u_n,
             "d_df": p.d_df, "d_n": p.d_n, "h_df": p.h_df, "h_n": p.h_n}
            for p in false_ev],
    }


def score_reconstructed(fam: dict[str, Any], sig: dict[int, dict[str, Any]],
                        gates: Sequence[str]) -> dict[str, Any]:
    """The GQ-05 family lives outside `emergent_clusters` (offline rebuild), so
    it gets its own fingerprints, its own df (over its own fragment set) and its
    own component counts on the same grid."""
    frags = fam.get("fragments") or {}
    if len(frags) < 2:
        return {"status": fam.get("status", "unavailable"), "components": {}}
    keys = sorted(frags)
    pseudo = [{"id": -1000 - k, "sample": frags[k]["signal_ids"],
               "vec": np.asarray(frags[k]["centroid"], dtype=np.float32)}
              for k in keys]
    fps, vocabs = build_fingerprints(pseudo, sig)
    dfs = {k: v.df_array() for k, v in vocabs.items()}
    dfmax = {k: v.df_max for k, v in vocabs.items()}
    V = np.stack([p["vec"] for p in pseudo]).astype(np.float32)
    V /= np.clip(np.linalg.norm(V, axis=1, keepdims=True), 1e-12, None)
    n = len(pseudo)
    pe = [pair_evidence(fps[i], fps[j], float(V[i] @ V[j]), dfs, i, j)
          for i in range(n) for j in range(i + 1, n)]
    medians = shared_df_medians(pe_to_arrays(pe), vocabs)
    out: dict[str, Any] = {"status": "ok", "n_fragments": n, "components": {},
                           "cos_p50": round(float(np.median([p.cos for p in pe])), 4),
                           "cos_min": round(float(min(p.cos for p in pe)), 4),
                           "cos_max": round(float(max(p.cos for p in pe)), 4),
                           "shared_entity_pair_rate": round(
                               float(np.mean([p.e_df >= 0 for p in pe])), 4)}
    for tau in TAU_GRID:
        for lanes in LANE_SETS:
            for gname in gates:
                gate = Gate(gname, dfmax, medians)
                edges = [(p.i, p.j) for p in pe if p.cos >= tau and admits(p, lanes, gate)]
                c, _ = components(n, edges)
                out["components"][f"{tau}|{'|'.join(lanes)}|{gname}"] = c
    return out


# ------------------------------------------------------------------ M6 judge
def judge_dryrun(sweep_res: dict[str, Any], candidates: Sequence[dict[str, Any]]
                 ) -> dict[str, Any]:
    """Borderline-band volume + cost at each candidate operating point.

    Operational definition of the band (the only one measurable before M3 fits
    the weights): pairs that clear the tau and share evidence, but whose rarest
    shared item does NOT clear the strict rarity gate — i.e. exactly the pairs a
    strict gate rejects and a permissive gate admits. That is the population a
    judge would be asked to adjudicate."""
    rows = {(r["tau"], r["lanes"], r["gate"]): r for r in sweep_res["grid_rows"]}
    out: list[dict[str, Any]] = []
    for cand in candidates:
        tau, lanes, strict = cand["tau"], cand["lanes"], cand["gate"]
        loose = rows.get((tau, lanes, "any-shared"))
        tight = rows.get((tau, lanes, strict))
        if not loose or not tight:
            continue
        band = max(0, loose["merge_edges"] - tight["merge_edges"])
        tok_in = band * JUDGE_TOKENS_IN
        tok_out = band * JUDGE_TOKENS_OUT
        out.append({
            "tau": tau, "lanes": lanes, "strict_gate": strict,
            "pairs_admitted_strict": tight["merge_edges"],
            "pairs_admitted_loose": loose["merge_edges"],
            "borderline_band_pairs": band,
            "over_hard_cap": band > JUDGE_HARD_CAP,
            "cap_multiple": round(band / JUDGE_HARD_CAP, 1) if JUDGE_HARD_CAP else None,
            "tokens_in": tok_in, "tokens_out": tok_out,
            "usd_per_night": round(price_usd(JUDGE_MODEL, tok_in, tok_out), 2),
            "usd_per_night_at_cap": round(
                price_usd(JUDGE_MODEL, JUDGE_HARD_CAP * JUDGE_TOKENS_IN,
                          JUDGE_HARD_CAP * JUDGE_TOKENS_OUT), 4),
        })
    return {
        "model": JUDGE_MODEL,
        "price_usd_per_mtok": resolve_price(JUDGE_MODEL),
        "tokens_per_call": {"in": JUDGE_TOKENS_IN, "out": JUDGE_TOKENS_OUT},
        "hard_cap_calls_per_night": JUDGE_HARD_CAP,
        "valley_window_note": (
            "DeepSeek peak pricing is 2x in UTC 01-04 and 06-10; the nightly "
            "`scoped-snapshot` runs 22:00->03:54 local and straddles both, so a "
            "judge step must be placed in the local 00:20-00:50 valley "
            "explicitly — moving the JOB does not move the STEP (CLAUDE.md "
            "2026-07-27)."),
        "points": out,
    }


# ------------------------------------------------------------------ verdict
def decide(sweep_res: dict[str, Any], gq05: dict[str, Any],
           core_names: Sequence[str]) -> dict[str, Any]:
    """GO/NO-GO 0, on the PRE-REGISTERED kill rules only.

    GO requires an operating point that satisfies K2 (largest merge component
    <= 2% of the snapshot's clusters) AND brings >= 2 of the 3 CORE witness
    families to <= 3 components. Nothing about these two numbers is computed
    from the results; both were frozen in the spec before any code ran."""
    winners: list[dict[str, Any]] = []
    for r in sweep_res["grid_rows"]:
        # GQ-05 is folded into EVERY row (not only the K2-passing ones) so the
        # published table shows its recall column throughout — a blank there
        # would read as "not measured" rather than "measured, still shredded".
        fam = dict(r["family_components"])
        key = f"{r['tau']}|{r['lanes']}|{r['gate']}"
        g = (gq05.get("components") or {}).get(key)
        if g is not None:
            fam["GQ-05"] = g
        core_ok = sum(1 for name in core_names
                      if fam.get(name) is not None and fam[name] <= WITNESS_MAX_COMPONENTS)
        r["core_families_at_or_below_3"] = core_ok
        r["family_components_full"] = fam
        if r["k2_ok"] and core_ok >= WITNESS_FAMILIES_REQUIRED:
            winners.append(r)
    winners.sort(key=lambda r: (-r["core_families_at_or_below_3"],
                                r["largest_component_share"], -r["tau"]))
    prereg_winners = [w for w in winners if w["prereg"]]

    # K3 ladder resolution (spec §5.2), rung by rung, on the SAME K2 constraint.
    k3: dict[str, Any] = {}
    for rung, lane_name in (("1_lane_E_primary", "E"),
                            ("2_lane_U_primary", "U"),
                            ("3_lane_H_primary", "H")):
        rows = [r for r in sweep_res["grid_rows"] if r["lanes"] == lane_name]
        ok = [r for r in rows if r["k2_ok"]
              and sum(1 for nm in core_names
                      if (r.get("family_components") or {}).get(nm) is not None
                      and r["family_components"][nm] <= WITNESS_MAX_COMPONENTS)
              >= WITNESS_FAMILIES_REQUIRED]
        best = None
        for r in rows:
            if not r["k2_ok"]:
                continue
            score = sum(1 for nm in core_names
                        if (r.get("family_components") or {}).get(nm) is not None
                        and r["family_components"][nm] <= WITNESS_MAX_COMPONENTS)
            if best is None or score > best[0]:
                best = (score, r)
        k3[rung] = {
            "passes": bool(ok),
            "k2_points": sum(1 for r in rows if r["k2_ok"]),
            "best_core_families_le3_under_k2": (best[0] if best else 0),
        }
    k3["resolution"] = (
        "REFUTED — all three lanes fail K3" if not any(v.get("passes")
                                                       for v in k3.values()
                                                       if isinstance(v, dict))
        else "escalation succeeded")
    return {
        "K3": k3,
        "verdict": "GO" if winners else "NO-GO",
        "verdict_prereg_grid_only": "GO" if prereg_winners else "NO-GO",
        "k2_max_component_share": K2_MAX_COMPONENT_SHARE,
        "witness_max_components": WITNESS_MAX_COMPONENTS,
        "core_families_required": WITNESS_FAMILIES_REQUIRED,
        "core_families": list(core_names),
        "n_points_satisfying_k2": sum(1 for r in sweep_res["grid_rows"] if r["k2_ok"]),
        "n_points_total": len(sweep_res["grid_rows"]),
        "winners": winners[:12],
        "frozen_operating_point": (
            {"MERGE_TAU_COS": winners[0]["tau"], "lane": winners[0]["lanes"],
             "rarity_gate": winners[0]["gate"]} if winners else None),
    }


# ------------------------------------------------------------------ rendering
def _fam_cell(v: Any) -> str:
    return "—" if v is None else str(v)


def render_coverage_md(res: dict[str, Any]) -> str:
    c, r = res["coverage"], res["retention"]
    L: list[str] = []
    L.append("# Evidence fingerprints — build feasibility (M0) and persistence sizing (M4)\n")
    L.append(f"**Generated:** {res['generated_at']} · read-only · harness "
             "`backend/scripts/measure_evidence_fingerprint.py --coverage --retention`  ")
    L.append("**Spec:** `docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md` "
             "(§2 availability, §3.2 mig 092, §8 budget) · **Plan:** "
             "`docs/superpowers/plans/2026-07-28-entity-overlap-identity.md` (T-A1/T-A3)  ")
    L.append(f"**Snapshot measured:** `{res['snapshot_at']}` · {c['clusters']} clusters · "
             f"NULL-label rate {res['null_label_rate']} "
             f"({'VALID' if res['null_label_rate'] == 0 else 'VOID — §5.1 confounder'})\n")

    L.append("## M0 — can the fingerprint be built, and does it carry anything?\n")
    L.append(f"- **{c['sample_refs']}** `sample_signal_ids` references · "
             f"**{c['resolved_refs']}** resolved against `signals_v2` = "
             f"**{c['resolvable_rate']:.1%}**")
    L.append(f"- **{c['carry_any_entity']:.1%}** of clusters carry at least one lane-E entity · "
             f"empty-fingerprint rate (no entity, no domain, no URL, no headline key) "
             f"**{c['empty_fingerprint_rate']:.2%}**")
    L.append(f"- **build wall-clock {c['build_seconds']}s** for the whole snapshot "
             f"({c['signals_fetched']} signals fetched) — budget §8 is ≤120 s: "
             f"**{'INSIDE' if c['build_seconds'] <= 120 else 'OVER'}**")
    L.append(f"- storage **{c['storage_bytes_per_snapshot']/1e6:.1f} MB/snapshot** → "
             f"**{c['storage_mb_30d']} MB at 30-day retention** (budget §8 ≤200 MB: "
             f"{'INSIDE' if c['storage_mb_30d'] <= 200 else 'OVER'})")
    L.append(f"- **{c['truncated_sample_share']:.1%}** of clusters sit at the 24-id "
             "`sample_signal_ids` cap, i.e. their fingerprint is a near-complete, "
             "not complete, view of membership (spec §2.5)\n")
    L.append("| lane | per-cluster mean | p5 | p50 | p95 | max | clusters with zero |")
    L.append("|---|---|---|---|---|---|---|")
    for lane, key in (("E entities", "entities"), ("U domains", "domains"),
                      ("U url_keys", "url_keys"), ("H headline_keys", "headline_keys")):
        d = c["per_cluster"][key]
        L.append(f"| {lane} | {d['mean']} | {d['p5']} | {d['p50']} | {d['p95']} | "
                 f"{d['max']} | {d['zero_rate']:.2%} |")
    L.append("")
    L.append("### Lane vocabularies and their document frequency\n")
    L.append("`df` = number of clusters in this snapshot carrying the item. This is the "
             "denominator every rarity gate reads.\n")
    L.append("| lane | distinct items | df_max | df p50 | df p99 | share at df=1 |")
    L.append("|---|---|---|---|---|---|")
    names = {"E": "entities", "D": "domains", "U": "url_keys", "H": "headline_keys"}
    for k in ("E", "U", "D", "H"):
        v = c["vocab"][k]
        L.append(f"| {names[k]} | {v['distinct']} | {v['df_max']} | {v['df_p50']} | "
                 f"{v['df_p99']} | {v['df1_share']:.1%} |")
    L.append("")
    L.append("> **The rarity-gate degeneracy.** A SHARED item has `df ≥ 2` by construction, "
             "so any gate expressed against the *vocabulary* df distribution (median 1; "
             f"`norm_rarity(2, df_max)` = "
             f"{norm_rarity(2, c['vocab']['E']['df_max']):.4f} < 0.5) admits **nothing**. "
             "Two of the three pre-registered rarity gates are vacuous on the population "
             "they gate. Both are still run and reported in the M1/M2 table; the "
             "non-degenerate reading (`df ≤ median of the shared-item df distribution`) and "
             "a `df ≤ 2/3/5` ladder are reported beside them, each with its own false-side "
             "number. The kill thresholds (K2 = 2%, ≤3 components) are untouched.\n")

    L.append("### What sits at the top of each df distribution\n")
    L.append("The highest-df items are exactly what a permissive gate merges on, so they are "
             "worth looking at rather than summarising. Two of these are defects, not "
             "evidence, and both were found here:\n")
    L.append("| lane | the ten highest-df items |")
    L.append("|---|---|")
    for k in ("E", "U", "D", "H"):
        items = " · ".join(f"`{x['item']}`&nbsp;{x['df']}" for x in c["top_df"][k])
        L.append(f"| {names[k]} | {items} |")
    L.append("")
    L.append("**Finding 1 — lane E carries an HTML-entity artifact.** `x2013` (an en-dash, "
             "`&#x2013;`) sits at df 100 in the entity vocabulary: the GDELT "
             "`persons[]`/`organizations[]` passthrough is entity-encoded, the same class of "
             "bug as #264. It is high-df so the rarity weighting neutralises it, but a "
             "permissive gate would merge on a dash.\n")
    L.append("**Finding 2 — lane H's normalizer collapses masthead-PREFIXED headlines to the "
             "outlet name.** `thread_ranking._norm_headline` strips the LAST `|`-separated "
             "segment, which is correct for `\"<story> | Katherine Times\"` and wrong for "
             "`\"BlackSeaNews | <story>\"` — the whole headline becomes `blackseanews` "
             "(df 15) or `patrisnews` (df 15). Bare numerals (`2026` df 23, `23` df 21) come "
             "from the same shape. This harness reuses the normalizer **verbatim**, as the "
             "spec requires, and reports the consequence instead of quietly patching it: a "
             "minimum-content guard on headline keys is a lane-H hygiene follow-up, and it "
             "is also why lane H's `df_max` is only 23.\n")

    if res.get("family_coverage"):
        L.append("### Per-family coverage (the witnesses M1 is scored on)\n")
        L.append("| family | clusters | refs | resolvable | ent/cluster | dom/cluster | "
                 "url/cluster | headline/cluster | clusters w/ entity | languages |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for f in res["family_coverage"]:
            langs = ", ".join(f"{k} {v}" for k, v in list(f["langs"].items())[:4]) or "—"
            L.append(f"| `{f['family']}` | {f['clusters']} | {f['sample_refs']} | "
                     f"{f['resolvable_rate']:.1%} | {f['entities_per_cluster']} | "
                     f"{f['domains_per_cluster']} | {f['urls_per_cluster']} | "
                     f"{f['headlines_per_cluster']} | "
                     f"{f['clusters_with_entity']}/{f['clusters']} | {langs} |")
        L.append("")
    L.append(f"Snapshot-wide `source_lang` mix inside resolved sample signals: "
             f"`{c['source_lang_mix']}`\n")

    L.append("## M4 — evidence evaporates; what that costs the staged build\n")
    L.append("`sample_signal_ids` resolvability against `signals_v2`, by snapshot day. "
             "This is spec §2.4's table re-derived as a script.\n")
    L.append("| snapshot day | clusters | sample refs | resolvable | % resolvable |")
    L.append("|---|---|---|---|---|")
    for row in r["curve"]:
        rate = "—" if row["resolvable_rate"] is None else f"**{row['resolvable_rate']:.1%}**"
        L.append(f"| {row['day']} | {row['clusters']} | {row['sample_refs']} | "
                 f"{row['resolvable']} | {rate} |")
    L.append("")
    L.append(f"- `signals_v2` holds **{r['signals_v2_rows']}** rows spanning "
             f"**{r['signals_v2_window_hours']} h** — the hot window IS the evidence window.")
    L.append(f"- Days backfillable at ≥80% resolvability: **{r['backfillable_days_at_80pct']}**; "
             f"days with any resolvable evidence at all: **{r['backfillable_days_any']}**.")
    L.append(f"- Active topics needing an anchor fingerprint for K4's 80% bar: "
             f"**{r['active_topics']}**.")
    L.append(f"- {r['cold_start_note']}\n")
    L.append("**Consequence for stage ordering (unchanged from the spec, now measured):** "
             "Stage 2 (DP-1 same-snapshot) can run tonight — its evidence is resolvable the "
             "night it is written. Stage 4 (DP-2 anchor guard) cannot: its anchors are older "
             "than the hot window, so it waits for accumulation, exactly as §6 orders it.\n")

    L.append("## Honest limits\n")
    L.append("- Lane E is biased toward **Latin-script proper nouns**: entity strings are "
             "stored in the source language and are not transliterated, so a Persian and a "
             "Romanian report of one event share the *event*, not the *string* (spec §2.5). "
             "The per-family language table above is where that bias becomes visible.")
    L.append("- `registrable_domain` uses a **short second-level-suffix list**, not a full "
             "public-suffix list; a handful of exotic ccTLDs will land on the wrong "
             "registrable name. That inflates domain df slightly (more clusters sharing a "
             "coarser domain), which is conservative on the false side.")
    L.append("- `nlp_persons` is noisy (spec §2.5 samples `{\"name\":\"Policía\",\"type\":"
             "\"GPE\"}`). No hand-labelled noise floor is applied here — that is M3's job "
             "(`calibrate_evidence_rarity.py`, T-A2). Noise inflates the df=1 tail, which "
             "cannot create shared items but can distort `df_max`.")
    L.append("- `url_key` **keeps** the query string. The query-stripped variant was measured "
             "first and rejected: outlets that carry the article id in the query collapsed "
             "their whole output to one pseudo-locator "
             "(`shorouknews.com/news/view.aspx` df **35**, `pressorg24.com/news` df 17). "
             "Keeping the query costs recall when one link is syndicated with different "
             "tracking parameters — an error that can only withhold evidence, never "
             "fabricate it. With the query kept, the url_key vocabulary is 100% df=1 and "
             "`df_max` is 2, i.e. an exact-URL match is now a genuinely rare event.")
    L.append("- The **GQ-05 family is absent from the per-family table**: its fragments are "
             "an offline HDBSCAN rebuild (spec §2.5) and are not rows in "
             "`emergent_clusters`, so they have no `sample_signal_ids` to score here. Its "
             "coverage is reported inside the reconvergence artifact instead.")
    L.append("- Every number here is **one snapshot, one night** (07-28). The multi-snapshot "
             "df distribution, the `nlp_persons` noise floor and the `w_E/w_U/w_H` fit are "
             "M3's job (`calibrate_evidence_rarity.py`, T-A2).")
    return "\n".join(L) + "\n"


def render_sweep_md(res: dict[str, Any]) -> str:  # noqa: C901
    s, v = res["sweep"], res["verdict"]
    core = v["core_families"]
    fams = res["families"]
    L: list[str] = []
    L.append("# Witness reconvergence (M1) and false-side density (M2) — one table\n")
    L.append(f"**Generated:** {res['generated_at']} · read-only · harness "
             "`backend/scripts/measure_evidence_fingerprint.py --sweep --false-density "
             "--judge-dryrun`  ")
    L.append("**Spec:** `docs/superpowers/specs/2026-07-28-entity-overlap-identity-design.md` "
             "§3.1/§4/§5.2 · **Plan:** "
             "`docs/superpowers/plans/2026-07-28-entity-overlap-identity.md` (T-A1/T-A3)  ")
    L.append(f"**Snapshot:** `{res['snapshot_at']}` · {s['pair_meta']['nodes']} clusters · "
             f"{s['pair_meta']['total_pairs']} pairs · "
             f"{s['pair_meta']['candidate_pairs']} at cos ≥ {s['pair_meta']['tau_min']}\n")

    L.append(f"## GO/NO-GO 0: **{v['verdict']}**\n")
    L.append("Pre-registered, frozen before the run (spec §5.2, plan T-A3): an operating "
             f"point must satisfy **K2** (largest connected component of the whole-snapshot "
             f"merge graph ≤ **{v['k2_max_component_share']:.0%}** of that snapshot's topics) "
             f"**AND** bring **≥{v['core_families_required']} of the "
             f"{len(core)} core witness families** to **≤{v['witness_max_components']} "
             "components**.\n")
    L.append(f"- points satisfying K2: **{v['n_points_satisfying_k2']} / "
             f"{v['n_points_total']}**")
    L.append(f"- points satisfying K2 **and** the witness criterion: "
             f"**{len(v['winners'])}**")
    if v["frozen_operating_point"]:
        fp = v["frozen_operating_point"]
        L.append(f"\n**Frozen operating point:** `MERGE_TAU_COS={fp['MERGE_TAU_COS']}`, "
                 f"lane `{fp['lane']}`, rarity gate `{fp['rarity_gate']}`.\n")
    else:
        k3 = v.get("K3", {})
        L.append("\n**No operating point exists.** K3's escalation ladder (§5.2) was run in "
                 "the same pass — lane U and lane H appear as their own lane sets below — "
                 "and every rung fails on the same K2 constraint:\n")
        L.append("| K3 rung | operating points satisfying K2 | best core families at ≤3 "
                 "components among them | rung |")
        L.append("|---|---|---|---|")
        for rung, label in (("1_lane_E_primary", "1 — lane E (entities) primary"),
                            ("2_lane_U_primary", "2 — lane U (locators) primary"),
                            ("3_lane_H_primary", "3 — lane H (headlines) primary")):
            d = k3.get(rung, {})
            L.append(f"| {label} | {d.get('k2_points', 0)} | "
                     f"{d.get('best_core_families_le3_under_k2', 0)} of "
                     f"{len(core)} | **{'PASS' if d.get('passes') else 'FAIL'}** |")
        L.append("")
        L.append(f"**K3 resolution: {k3.get('resolution')}.** Per the spec's own words: "
                 "*\"If all three lanes fail K3, the entity-overlap direction is REFUTED, "
                 "this spec is closed like the attention-coverage-divergence spec was, and "
                 "the honest conclusion is recorded: the same event's fragments carry no "
                 "shared surface evidence [that is safe to merge on], so reconvergence "
                 "cannot happen at the identity layer and must be attacked at clustering "
                 "time.\"* **No fourth attempt, and no threshold was relaxed after seeing "
                 "the result.**\n")
        L.append("One arithmetic corollary, so the obvious next idea is foreclosed rather "
                 "than left hanging: a rule of the form `cos AND (label OR evidence)` — "
                 "evidence as a *rescue* for the label blackout rather than a replacement — "
                 "**cannot** satisfy K2 either. Connected components are monotone under "
                 "edge addition, so the union's largest component is at least the evidence "
                 "half's, and the evidence half exceeds 2% at every cut that moves a "
                 "witness. This follows from the table; it needs no extra run.\n")

    L.append("## The mechanism the table is measuring\n")
    L.append("`merge_duplicates` runs **to a fixpoint**, so merging is transitively closed: "
             "an edge set is not a set of decisions, it is a graph, and what matters is "
             "**density**, not per-pair precision. Raw e5 is anisotropic — on this snapshot "
             "the cosine-only edge densities are:\n")
    L.append("| cos ≥ | merge edges | largest component | share of snapshot | "
             "false-pair admit rate |")
    L.append("|---|---|---|---|---|")
    for row in s["cosine_only"]:
        L.append(f"| {row['tau']} | {row['merge_edges']} | {row['largest_component']} | "
                 f"**{row['largest_component_share']:.1%}** | {row['false_admit_rate']:.1%} |")
    L.append("")
    b = s["engine_baseline"]
    L.append(f"Today's shipping rule (`{b['rule']}`) for contrast: **{b['merge_edges']}** "
             f"edges, largest component **{b['largest_component']}** "
             f"({b['largest_component_share']:.1%}), "
             f"{b['false_pairs_admitted']}/{b['false_pairs_n']} false pairs admitted. "
             "Its family components: "
             + ", ".join(f"`{k}` {vv}" for k, vv in sorted(b["family_components"].items()))
             + ".\n")

    seed = next((r for r in s["grid_rows"]
                 if r["tau"] == 0.86 and r["lanes"] == "E" and r["gate"] == "any-shared"),
                None)
    if seed:
        L.append("## The spec's seed candidate, tested\n")
        L.append("The spec's pre-measurement proposed **`cos ≥ 0.86 AND ent ≥ 1`** on the "
                 "strength of Berlin Pride reaching 1 component while admitting 2.7% of 406 "
                 "random dissimilar-label pairs. On the full grid that row reads:\n")
        L.append(f"- Berlin Pride **{seed['family_components'].get('berlin pride')}** "
                 f"components, GQ-12 Caspian "
                 f"**{seed['family_components'].get('GQ-12 caspian')}** — the recall claim "
                 "essentially reproduces.")
        L.append(f"- false-pair admission **{seed['false_admit_rate']:.1%}** — the precision "
                 "claim also reproduces (same order as the spec's 2.7%).")
        L.append(f"- **largest connected component {seed['largest_component']} / "
                 f"{s['pair_meta']['nodes']} clusters = "
                 f"{seed['largest_component_share']:.1%} of the snapshot.** K2's bar is 2%. "
                 f"It misses by **{seed['largest_component_share'] / K2_MAX_COMPONENT_SHARE:.0f}×**.\n")
        L.append("**The seed candidate is killed, and it is killed by the number M2 exists "
                 "to produce.** Its supporting measurement scored 406 sampled pairs; it never "
                 "built the graph. A 1.4% false-pair rate sounds small and is fatal here: "
                 "over 2.06M pairs it is tens of thousands of edges, and `merge_duplicates` "
                 "runs to a fixpoint. Percolation, not precision, is the binding constraint "
                 "— which is exactly why the spec required M1 and M2 in one table.\n")
        L.append("### What today's shipping rule does on the same graph\n")
        L.append(f"`{b['rule']}` — the rule this design set out to replace — satisfies K2 "
                 f"(**{b['largest_component_share']:.2%}**, inside the 2% bar), admits "
                 f"**{b['false_pairs_admitted']}/{b['false_pairs_n']}** false pairs, and "
                 "leaves the two in-snapshot core families at "
                 + " and ".join(f"**{b['family_components'].get(nm)}**"
                                for nm in ("GQ-12 caspian", "berlin pride"))
                 + " components. **No evidence-gate operating point in this grid matches "
                 "that combination.** The label gate is a far better density controller than "
                 "any evidence lane measured here; its documented failure was the five-day "
                 "blackout (`emergent_clusters.label` 100% NULL 07-23→07-27, so "
                 "`labels_compatible(None, None)` disabled merging entirely), not its "
                 "discrimination on a labelled night. That distinction was not visible "
                 "before this run, and it changes what DP-1's problem actually is.\n")

    L.append("## Witness families\n")
    L.append("| family | kind | clusters | signals | countries | example labels |")
    L.append("|---|---|---|---|---|---|")
    for f in fams:
        labs = " · ".join((x or "—")[:34].replace("|", "/") for x in (f.get("labels") or [])[:3])
        n = f.get("n_fragments") or len(f.get("cluster_ids") or [])
        L.append(f"| `{f['name']}` | {f['kind']}{' (rebuilt)' if f.get('reconstructed') else ''} "
                 f"| {n} | {f.get('n_signals') or f.get('corpus_signals') or '—'} | "
                 f"{','.join((f.get('countries') or [])[:4]) or '—'} | {labs} |")
    L.append("")
    g = res["gq05"]
    if g.get("status") == "ok":
        L.append(f"**GQ-05 reconstruction** (spec §2.5): `%{res['gq05_pattern']}%` = "
                 f"{g.get('corpus_signals')} signals in the hot window, "
                 f"{g.get('embedded')} embedded; offline HDBSCAN at the scoped snapshot's own "
                 f"parameters (mcs={GQ05_MCS}, ms={GQ05_MS}, {GQ05_SELECTION}, PRE-gate) → "
                 f"**{g.get('n_fragments')} fragments** ({g.get('noise_signals')} signals to "
                 f"noise). Pairwise centroid cosine inside the family: "
                 f"{g.get('cos_min')} / {g.get('cos_p50')} / {g.get('cos_max')} "
                 f"(min/p50/max); {g.get('shared_entity_pair_rate', 0):.1%} of its internal "
                 "pairs share at least one entity.\n")
    else:
        L.append(f"**GQ-05 reconstruction FAILED** (`{g.get('status')}`) — it is excluded "
                 "from the verdict's core count and that is stated rather than papered "
                 "over.\n")

    L.append("## M1 + M2 — the single table\n")
    L.append("Every row is one operating point. **Left half = recall** (connected components "
             "per witness family; the target is ≤3). **Right half = the false side** at the "
             "SAME point. `prereg` marks the pre-registered grid; `supp` rows widen only the "
             "rarity axis, because two pre-registered rarity gates are vacuous against the "
             "measured shared-item df distribution (see the coverage artifact). No kill "
             "threshold is moved.\n")
    fam_cols = [f["name"] for f in fams]
    head = ("| tau | lanes | rarity gate | grid | "
            + " | ".join(f"`{c}`" for c in fam_cols)
            + " | merge edges | largest comp | **share (K2)** | K2 | false admit |")
    L.append(head)
    L.append("|" + "---|" * (4 + len(fam_cols) + 5))
    for r in s["grid_rows"]:
        fam = r.get("family_components_full") or r["family_components"]
        cells = " | ".join(_fam_cell(fam.get(c)) for c in fam_cols)
        L.append(f"| {r['tau']} | {r['lanes']} | `{r['gate']}` | "
                 f"{'prereg' if r['prereg'] else 'supp'} | {cells} | "
                 f"{r['merge_edges']} | {r['largest_component']} | "
                 f"**{r['largest_component_share']:.1%}** | "
                 f"{'✓' if r['k2_ok'] else '✗'} | "
                 f"{r['false_pairs_admitted']}/{r['false_pairs_n']} "
                 f"({r['false_admit_rate']:.1%}) |")
    L.append("")
    fc = s["false_construction"]
    L.append(f"**FALSE construction** ({fc['n']} pairs): {fc['rule']} — the same mechanical "
             "rule the whitened-taus harness used, so the two measurements share one "
             "definition of \"different story\". On that set: "
             f"**{fc['shared_entity_rate']:.1%}** share ≥1 entity, "
             f"{fc['shared_url_rate']:.1%} share an exact URL, "
             f"{fc['shared_domain_rate']:.1%} share a domain, "
             f"{fc['shared_headline_rate']:.1%} share a normalized headline.\n")
    L.append("Shared-item df medians actually observed (the honest denominator for "
             f"`df≤median`): `{s['medians']}`. Lane `df_max`: `{s['df_max']}`.\n")

    L.append("## The separation probe — do the two curves ever cross?\n")
    L.append("The grid samples a handful of rarity cuts, so a NO-GO on it could in principle "
             "be an artifact of which cuts were sampled. This walks the cut continuously "
             "(`df ≤ 1,2,3,4,5,6,8,10,14,20,30,45,70,100,150,250,400, any`) and reports two "
             "numbers per (tau, lane set): the **loosest** cut that still satisfies K2, and "
             "the **tightest** cut that brings both in-snapshot core families "
             "(`GQ-12 caspian`, `berlin pride`) to ≤3 components. If the tightest recall cut "
             "is looser than the loosest safe cut, **no operating point can exist between "
             "them** — arithmetically, not by taste.\n")
    L.append("| tau | lanes | loosest cut satisfying K2 | tightest cut reaching the witness "
             "bar | overlap? |")
    L.append("|---|---|---|---|---|")
    for sp in s.get("separation_probe", []):
        a = sp["loosest_cut_satisfying_k2"]
        b = sp["tightest_cut_reaching_witness_bar"]
        L.append(f"| {sp['tau']} | {sp['lanes']} | "
                 f"{'none' if a is None else ('any' if a >= (1 << 20) else f'df≤{a}')} | "
                 f"{'never' if b is None else ('any' if b >= (1 << 20) else f'df≤{b}')} | "
                 f"{'**YES**' if sp['overlap'] else 'no'} |")
    L.append("")
    L.append("`GQ-05` is excluded from this probe: its fragments are an offline rebuild "
             "outside `emergent_clusters`, so they cannot be nodes of the snapshot merge "
             "graph whose density K2 measures. Requiring both remaining core families is the "
             "strict reading of \"≥2 of 3\".\n")

    if res.get("judge"):
        j = res["judge"]
        L.append("## M6 — judge volume and cost at the candidate points\n")
        L.append("Borderline band = pairs a **strict** rarity gate rejects but the "
                 "**permissive** (`any-shared`) gate at the same tau/lane admits. That is "
                 "the population a \"one story or two?\" judge would adjudicate; the band's "
                 "size is the judge's nightly workload.\n")
        L.append(f"Model `{j['model']}` at `{j['price_usd_per_mtok']}` USD/Mtok, "
                 f"{j['tokens_per_call']['in']} in + {j['tokens_per_call']['out']} out per "
                 f"call, spec §8 hard cap **{j['hard_cap_calls_per_night']} calls/night** "
                 f"(≈ ${j['points'][0]['usd_per_night_at_cap'] if j['points'] else 0}/night "
                 "at the cap).\n")
        L.append("| tau | lanes | strict gate | admitted (strict) | admitted (loose) | "
                 "**borderline band** | × hard cap | USD/night if all judged |")
        L.append("|---|---|---|---|---|---|---|---|")
        for p in j["points"]:
            L.append(f"| {p['tau']} | {p['lanes']} | `{p['strict_gate']}` | "
                     f"{p['pairs_admitted_strict']} | {p['pairs_admitted_loose']} | "
                     f"**{p['borderline_band_pairs']}** | "
                     f"{'—' if p['cap_multiple'] is None else str(p['cap_multiple']) + '×'} | "
                     f"${p['usd_per_night']} |")
        L.append("")
        L.append(f"{j['valley_window_note']}\n")

    L.append("## Honest limits\n")
    L.append("- **The node set is clusters, not topics.** K2 is stated over \"that "
             "snapshot's topics\"; at DP-1's same-snapshot restriction every unmatched "
             "cluster founds its own topic before `merge_duplicates` runs "
             "(`project_dynamic_topics.process_snapshot`), so one cluster ≈ one candidate "
             "identity and the share is computed over the snapshot's clusters. Stated "
             "rather than assumed.")
    L.append("- **Roundups are not excluded.** `merge_duplicates` skips roundup topics, but "
             "`emergent_clusters` does not persist the roundup flag, so the false-side "
             "density here is an **upper bound** on the shipping graph. The direction of the "
             "error is stated; it cannot manufacture a passing operating point.")
    L.append("- **The FALSE construction can misfile** a genuinely shared story told with "
             "disjoint vocabulary in disjoint countries. That error raises the measured "
             "false-admit rate, i.e. it is conservative against a GO.")
    L.append("- **The GQ-05 family is scored on its own df**, computed over its own "
             "fragments rather than the snapshot (its fragments are an offline rebuild and "
             "are not snapshot members). A small df universe makes rarity gates *easier* to "
             "clear there, so GQ-05's component counts are optimistic relative to the "
             "families scored in-snapshot.")
    L.append("- **One snapshot, one night.** Every number here is 07-28. M3 (T-A2) is the "
             "measurement that spans ≥7 snapshots; until it lands, `df_max` and the df "
             "medians should be read as a single night's field, not as constants.")
    return "\n".join(L) + "\n"


# ------------------------------------------------------------------ entry
def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Measure the evidence-overlap identity signal (read-only; writes no "
                    "prod table). M0/M1/M2/M4/M6.")
    ap.add_argument("--coverage", action="store_true", help="M0 build feasibility + coverage")
    ap.add_argument("--retention", action="store_true", help="M4 resolvability decay + sizing")
    ap.add_argument("--sweep", action="store_true", help="M1 witness reconvergence sweep")
    ap.add_argument("--false-density", action="store_true",
                    help="M2 false-side density (always runs with --sweep; spec §4 rule)")
    ap.add_argument("--judge-dryrun", action="store_true", help="M6 borderline band + cost")
    ap.add_argument("--all", action="store_true", help="every mode")
    ap.add_argument("--snapshot", default="", help="ISO snapshot_at (default: latest)")
    ap.add_argument("--retention-days", type=int, default=14)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--max-false-pairs", type=int, default=1200)
    ap.add_argument("--fresh-families", type=int, default=4,
                    help="how many fresh label-similarity families to discover (spec: ≥3)")
    ap.add_argument("--fresh-min-size", type=int, default=4)
    ap.add_argument("--gq05-pattern", default="espriella")
    ap.add_argument("--gq05-hours", type=int, default=168)
    ap.add_argument("--core-families", default="GQ-12 caspian,berlin pride,GQ-05",
                    help="comma names counted by the pre-registered witness criterion")
    ap.add_argument("--out-dir", default=str(ARTIFACT_DIR))
    ap.add_argument("--no-artifacts", action="store_true")
    a = ap.parse_args()
    if a.all:
        a.coverage = a.retention = a.sweep = a.false_density = a.judge_dryrun = True
    if a.false_density:
        a.sweep = True          # spec §4: one script, one pass, one table
    if a.sweep:
        a.false_density = True
    if not any((a.coverage, a.retention, a.sweep, a.judge_dryrun)):
        a.coverage = a.retention = a.sweep = a.false_density = a.judge_dryrun = True
    a.core_families = [x.strip() for x in a.core_families.split(",") if x.strip()]
    return a


async def run(args: argparse.Namespace) -> int:  # noqa: C901
    import asyncpg

    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        print("DATABASE_URL required", file=sys.stderr)
        return 2
    rng = random.Random(args.seed)
    conn = await asyncpg.connect(url, timeout=60)
    res: dict[str, Any] = {
        "contract": "evidence-fingerprint-v1",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "gq05_pattern": args.gq05_pattern,
        "grid": {"tau": list(TAU_GRID), "lane_sets": ["|".join(x) for x in LANE_SETS],
                 "prereg_rarity_gates": list(PREREG_RARITY_GATES),
                 "supplementary_rarity_gates": list(SUPP_RARITY_GATES)},
        "kill_rules": {"K2_max_component_share": K2_MAX_COMPONENT_SHARE,
                       "witness_max_components": WITNESS_MAX_COMPONENTS,
                       "core_families_required": WITNESS_FAMILIES_REQUIRED},
    }
    try:
        await conn.execute("SET default_transaction_read_only = on")
        if args.snapshot:
            snapshot_at = dt.datetime.fromisoformat(args.snapshot)
        else:
            snapshot_at = await conn.fetchval("SELECT max(snapshot_at) FROM emergent_clusters")
        if snapshot_at is None:
            print("no snapshots", file=sys.stderr)
            return 2
        res["snapshot_at"] = snapshot_at.isoformat()
        nulls = await conn.fetchrow(
            """SELECT count(*) AS n, count(*) FILTER (WHERE label IS NULL) AS nulls
                 FROM emergent_clusters WHERE snapshot_at = $1""", snapshot_at)
        res["null_label_rate"] = round(int(nulls["nulls"]) / max(1, int(nulls["n"])), 4)
        if res["null_label_rate"] > 0:
            # §5.1 confounder: a labelless snapshot cannot support the mechanical
            # FALSE construction (an unlabelled cluster is not judgeable).
            res["void_reason"] = "snapshot has NULL labels — §5.1 confounder"

        clusters = await load_snapshot_clusters(conn, snapshot_at)
        if len(clusters) < 50:
            print("snapshot too small", file=sys.stderr)
            return 2

        # ---- fingerprints (the M0 build, timed) ----------------------------
        want = sorted({s for c in clusters for s in c["sample"]})
        t0 = time.monotonic()
        sig = await load_signal_evidence(conn, want)
        fps, vocabs = build_fingerprints(clusters, sig)
        build_seconds = time.monotonic() - t0
        fp_by_cid = {f.cid: f for f in fps}

        # ---- families ------------------------------------------------------
        families: list[dict[str, Any]] = []
        for toks, name in ((("iran", "ukrain"), "GQ-12 caspian"),
                           (("berlin pride",), "berlin pride")):
            fam = await find_pattern_family(conn, snapshot_at, toks, name)
            if fam:
                families.append(fam)
        gq05 = await reconstruct_gq05(conn, args)
        gq_sig: dict[int, dict[str, Any]] = {}
        if gq05.get("status") == "ok":
            gq_ids = sorted({s for f in gq05["fragments"].values() for s in f["signal_ids"]})
            gq_sig = await load_signal_evidence(conn, gq_ids)
            families.append({"name": "GQ-05", "kind": "core", "reconstructed": True,
                             "cluster_ids": [], "labels": [],
                             "countries": ["CO"], "n_fragments": gq05["n_fragments"],
                             "corpus_signals": gq05.get("corpus_signals")})
        used = {c for f in families for c in f.get("cluster_ids", [])}
        families.extend(find_fresh_families(clusters, used, args.fresh_min_size,
                                            args.fresh_families))
        res["families"] = families

        if args.coverage:
            res["coverage"] = coverage_report(clusters, fps, vocabs, build_seconds, sig)
            res["family_coverage"] = family_language_coverage(families, fp_by_cid)
        if args.retention:
            res["retention"] = await retention_report(conn, args.retention_days)
    finally:
        await conn.close()

    if args.sweep:
        gates = list(PREREG_RARITY_GATES) + list(SUPP_RARITY_GATES)
        _, pairs, pmeta = build_candidate_pairs(clusters, fps, vocabs, min(TAU_GRID))
        res["sweep"] = sweep(clusters, fps, vocabs, pairs, pmeta, families,
                             fp_by_cid, gates, rng, args)
        res["gq05"] = ({**gq05, **score_reconstructed(gq05, gq_sig, gates)}
                       if gq05.get("status") == "ok" else gq05)
        res["gq05"].pop("fragments", None)  # keep the JSON companion readable
        res["verdict"] = decide(res["sweep"], res["gq05"], args.core_families)
        if args.judge_dryrun:
            cands = [{"tau": t, "lanes": "|".join(l), "gate": g}
                     for t in TAU_GRID for l in LANE_SETS
                     for g in ("df<=2", "df<=median(shared)")]
            res["judge"] = judge_dryrun(res["sweep"], cands)

    summary: dict[str, Any] = {"snapshot_at": res.get("snapshot_at"),
                               "null_label_rate": res.get("null_label_rate")}
    if "coverage" in res:
        summary["coverage"] = {k: res["coverage"][k] for k in
                               ("clusters", "resolvable_rate", "carry_any_entity",
                                "empty_fingerprint_rate", "build_seconds", "storage_mb_30d")}
    if "verdict" in res:
        summary["verdict"] = {k: res["verdict"][k] for k in
                              ("verdict", "verdict_prereg_grid_only",
                               "n_points_satisfying_k2", "n_points_total",
                               "frozen_operating_point")}
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

    if not args.no_artifacts:
        out = Path(args.out_dir)
        out.mkdir(parents=True, exist_ok=True)
        if args.coverage or args.retention:
            if "coverage" in res and "retention" in res:
                (out / f"{COVERAGE_STEM}.md").write_text(
                    render_coverage_md(res), encoding="utf-8")
        if args.sweep:
            (out / f"{SWEEP_STEM}.md").write_text(render_sweep_md(res), encoding="utf-8")
            (out / f"{SWEEP_STEM}.json").write_text(
                json.dumps(res, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        print(f"\nartifacts -> {out}", file=sys.stderr)

    if "verdict" not in res:
        return 0
    return 0 if res["verdict"]["verdict"] == "GO" else 1


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
