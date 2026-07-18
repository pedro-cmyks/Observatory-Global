#!/usr/bin/env python
"""Narrative lineage census — stitch LIVE dynamic topics to the ARCHIVE story
units, entirely in OpenAI text-embedding-3-small space (2026-07-18).

Pedro's frame: not one forced giant superthread — a CENSUS of the giant
threads that actually exist and HOW they evolved. The stitch never compares
e5 to OpenAI (different spaces): a live topic's member HEADLINES are sha1'd
(the archive pipeline's exact normalization) and looked up in the durable
OpenAI shards on the external volume; their mean is the topic's OpenAI-space
centroid, directly comparable to archive_story_units.vec (same construction:
mean of member headline vectors, L2-normalized).

Phases (subcommands, `all` runs the chain):

  index      stream the shard-*.meta.jsonl files once -> sorted sha1 ->
             (shard, row) lookup cached under
             /Volumes/Ext/Atlas/Embeddings/lineage-index/ (re-runs cheap;
             fingerprint = shard count + meta byte total).

  centroids  ACTIVE dynamic topics -> member headlines (topic_members
             role='evidence', both engine versions, deduped; fallback
             dynamic_topic_members -> emergent_clusters.sample_signal_ids)
             -> sha1 -> shard vectors -> mean -> OpenAI centroid. Coverage
             (matched/eligible) recorded per topic; topics with < --min-matched
             matched vectors are EXCLUDED (honest floor), never guessed.

  census     unit vectors (DB ids joined to the local Stage-B jsonl by
             (day,label); DB vec::text fallback), topic-vs-unit and
             unit-vs-unit cosine, MEASURED thresholds (bimodal valley of the
             best-adjacent-week-match distribution + a negative control of
             >=3-weeks-apart cross-country pairs, the wild-junk-quantile
             idiom), union-find lineages (intra-week + adjacent-week edges +
             component-level 1-week gap bridges), the census tables, and the
             edges JSON the build lanes consume.

Honesty rules honored: drift = measured cosine, labeled; the Jul-04->present
unit hole (Stage-B clustered through 2026-07-03) is reported, not papered
over; low-confidence stitches live below the measured threshold and are NOT
emitted as edges; coverage is a first-class output.

Read-only against serving (3 bounded SELECTs, statement_timeout set). All
vector work is local disk/CPU (M1). Run with the mlvenv python:

  /Users/pedro/AtlasLocalWorker/mlvenv/bin/python \
      backend/scripts/narrative_lineage_census.py all
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

EMB_ROOT = Path("/Volumes/Ext/Atlas/Embeddings/openai-3-small")
INDEX_ROOT = Path("/Volumes/Ext/Atlas/Embeddings/lineage-index")
UNITS_JSONL = Path("/Volumes/Ext/Atlas/Embeddings/archive-story-units.jsonl")
REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = REPO_ROOT / "docs" / "research" / "narrative-lineage"
DIM = 1536

# ── EXACT copies of the archive pipeline's normalization + junk filter ──────
# (archive_embed_pipeline.py — the sha1 key is sha1(_norm(headline)); any
# deviation here silently zeroes the lookup, so these are verbatim.)
_JUNK = re.compile(r"^(digit:|in words:|story\d|doc \S+\.shtml)|^\W*$", re.I)


def _norm(h: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(h).strip().lower())


def _is_junk(h: str) -> bool:
    if len(h) < 20 or len(h) > 500:
        return True
    if _JUNK.search(h):
        return True
    alpha = sum(1 for w in h.split() if sum(c.isalpha() for c in w) >= 3)
    return alpha < 3


def _monday(d: date) -> str:
    return (d - timedelta(days=d.weekday())).isoformat()


# ── Phase 1: sha1 -> (shard, row) index ─────────────────────────────────────

def _shard_fingerprint() -> dict:
    metas = sorted(EMB_ROOT.glob("shard-*.meta.jsonl"))
    return {"n_shards": len(metas),
            "meta_bytes": sum(m.stat().st_size for m in metas)}


def cmd_index(force: bool = False) -> dict:
    INDEX_ROOT.mkdir(parents=True, exist_ok=True)
    fp = _shard_fingerprint()
    fp_path = INDEX_ROOT / "sha1-index.meta.json"
    idx_path = INDEX_ROOT / "sha1-index.npz"
    if not force and idx_path.exists() and fp_path.exists():
        if json.loads(fp_path.read_text()) == fp:
            print(f"index fresh ({fp['n_shards']} shards) — reuse", file=sys.stderr)
            return fp
    t0 = time.time()
    metas = sorted(EMB_ROOT.glob("shard-*.meta.jsonl"))
    sha_buf = bytearray()
    shard_ids: list[int] = []
    row_ids: list[int] = []
    n_bad = 0
    for si, mp in enumerate(metas):
        with open(mp) as f:
            for ri, line in enumerate(f):
                # fast path: sha1 is always the first key the pipeline writes
                sha = line[10:50] if line.startswith('{"sha1": "') else None
                try:
                    sha_buf += bytes.fromhex(sha) if sha else b""
                    if not sha:
                        raise ValueError
                except ValueError:
                    try:
                        sha_buf += bytes.fromhex(json.loads(line)["sha1"])
                    except Exception:  # noqa: BLE001
                        n_bad += 1
                        continue
                shard_ids.append(si)
                row_ids.append(ri)
        if (si + 1) % 40 == 0:
            print(f"  indexed {si + 1}/{len(metas)} shards "
                  f"({len(shard_ids)} rows)", file=sys.stderr)
    sha_arr = np.frombuffer(bytes(sha_buf), dtype="S20")
    shard_arr = np.asarray(shard_ids, dtype=np.uint16)
    row_arr = np.asarray(row_ids, dtype=np.uint32)
    order = np.argsort(sha_arr, kind="stable")
    sha_arr, shard_arr, row_arr = sha_arr[order], shard_arr[order], row_arr[order]
    n_dup = int((sha_arr[1:] == sha_arr[:-1]).sum())
    np.savez(idx_path, sha=sha_arr, shard=shard_arr, row=row_arr)
    fp_path.write_text(json.dumps(fp))
    print(f"index: {len(sha_arr)} vectors, {n_dup} dup sha1 "
          f"(pipeline dedupes globally; dups keep first), {n_bad} bad lines, "
          f"{time.time() - t0:.0f}s", file=sys.stderr)
    return fp


def _load_index() -> tuple[np.ndarray, np.ndarray, np.ndarray, list[Path]]:
    z = np.load(INDEX_ROOT / "sha1-index.npz")
    shards = sorted(EMB_ROOT.glob("shard-*.npz"))
    return z["sha"], z["shard"], z["row"], shards


def _gather_vectors(norms: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """sha1 the normalized headlines, look them up, load shard rows.

    Returns (vecs float32 (N,1536) — zero rows where unmatched, hit bool (N,)).
    """
    sha_sorted, shard_sorted, row_sorted, shard_paths = _load_index()
    need = np.frombuffer(
        b"".join(hashlib.sha1(n.encode()).digest() for n in norms), dtype="S20")
    pos = np.searchsorted(sha_sorted, need)
    pos_c = np.clip(pos, 0, len(sha_sorted) - 1)
    hit = sha_sorted[pos_c] == need
    out = np.zeros((len(norms), DIM), dtype=np.float32)
    by_shard: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for i in np.nonzero(hit)[0]:
        p = int(pos_c[i])
        by_shard[int(shard_sorted[p])].append((int(row_sorted[p]), int(i)))
    t0 = time.time()
    for k, (si, pairs) in enumerate(sorted(by_shard.items())):
        vecs = np.load(shard_paths[si])["vecs"]
        rows = np.asarray([r for r, _ in pairs])
        dest = np.asarray([d for _, d in pairs])
        out[dest] = vecs[rows].astype(np.float32)
        if (k + 1) % 40 == 0:
            print(f"  gathered {k + 1}/{len(by_shard)} shards "
                  f"({time.time() - t0:.0f}s)", file=sys.stderr)
    return out, hit


# ── Live-embed path (the hot-window reality) ────────────────────────────────
# MEASURED 2026-07-18: the shards end at 2026-07-10 — the archive lags the hot
# window by ~7 days (retention design), while topic_members evidence joinable
# to signals_v2 IS the hot window (last 168h). Overlap ≈ zero, so live topic
# members are embedded FRESH with the exact same model + normalization +
# truncation as the shards (archive_embed_pipeline.openai_embed, verbatim).
# Cost: ~38 tok/headline, tens of thousands of headlines -> a few cents.
# Cached under lineage-index/ so re-runs are free. A space-consistency check
# re-embeds a sample of shard-HIT norms and reports cos(api, shard) — the
# proof the two vector sources are the same space, not an assumption.

def _openai_embed(texts: list[str]) -> np.ndarray:
    import openai
    client = openai.OpenAI(timeout=120.0)
    vecs: list[list[float]] = []
    for i in range(0, len(texts), 512):
        chunk = [t[:2000] for t in texts[i: i + 512]]
        for attempt in range(1, 7):
            try:
                resp = client.embeddings.create(
                    model="text-embedding-3-small", input=chunk)
                break
            except Exception:  # noqa: BLE001
                if attempt == 6:
                    raise
                time.sleep(2.0 * attempt)
        vecs.extend(d.embedding for d in resp.data)
        if len(texts) > 2000 and (i // 512) % 10 == 9:
            print(f"  embedded {i + len(chunk)}/{len(texts)}", file=sys.stderr)
    a = np.asarray(vecs, dtype=np.float32)
    a /= np.linalg.norm(a, axis=1, keepdims=True)
    return a


_CACHE_PATH = INDEX_ROOT / "live-embed-cache.npz"


def _load_embed_cache() -> tuple[np.ndarray, np.ndarray]:
    if _CACHE_PATH.exists():
        z = np.load(_CACHE_PATH)
        return z["sha"], z["vecs"]
    return (np.empty(0, dtype="S20"), np.empty((0, DIM), dtype=np.float16))


def _fill_missing_via_api(norms: list[str], out: np.ndarray, hit: np.ndarray,
                          max_embed: int) -> tuple[np.ndarray, dict]:
    """Fill non-hit rows of `out` from the live-embed cache + OpenAI API."""
    miss_idx = np.nonzero(~hit)[0]
    sha_of = {i: hashlib.sha1(norms[i].encode()).digest() for i in miss_idx}
    c_sha, c_vecs = _load_embed_cache()
    cache = {bytes(s): k for k, s in enumerate(c_sha)}
    from_cache = from_api = 0
    todo: dict[bytes, str] = {}
    for i in miss_idx:
        s = sha_of[i]
        k = cache.get(s)
        if k is not None:
            out[i] = c_vecs[k].astype(np.float32)
            hit[i] = True
            from_cache += 1
        else:
            todo.setdefault(s, norms[i])
    if todo:
        if len(todo) > max_embed:
            print(f"ABORT: {len(todo)} headlines to embed exceeds "
                  f"--max-embed {max_embed} (cost guard)", file=sys.stderr)
            raise SystemExit(3)
        keys = list(todo.keys())
        print(f"live-embedding {len(keys)} unique headlines "
              f"(~{len(keys) * 38 / 1e6:.2f}M tok)", file=sys.stderr)
        new_vecs = _openai_embed([todo[k] for k in keys])
        new_map = {k: v for k, v in zip(keys, new_vecs)}
        for i in miss_idx:
            v = new_map.get(sha_of[i])
            if v is not None and not hit[i]:
                out[i] = v
                hit[i] = True
                from_api += 1
        np.savez(_CACHE_PATH,
                 sha=np.concatenate([c_sha, np.frombuffer(
                     b"".join(keys), dtype="S20")]),
                 vecs=np.concatenate([c_vecs,
                                      new_vecs.astype(np.float16)]))
    stats = {"filled_from_cache": from_cache, "filled_from_api": from_api,
             "still_missing": int((~hit).sum())}
    print(f"live-embed fill: {stats}", file=sys.stderr)
    return hit, stats


def _space_consistency_check(norms: list[str], vecs: np.ndarray,
                             shard_hit: np.ndarray, n_sample: int = 24) -> dict:
    """Re-embed a sample of shard-HIT norms via the API; cos should be ~1."""
    idx = np.nonzero(shard_hit)[0]
    if not len(idx):
        return {"n": 0, "note": "no shard hits to check"}
    rng = np.random.default_rng(7)
    pick = rng.choice(idx, size=min(n_sample, len(idx)), replace=False)
    api = _openai_embed([norms[int(i)] for i in pick])
    cos = np.asarray([float(api[k] @ vecs[int(i)] /
                            max(np.linalg.norm(vecs[int(i)]), 1e-9))
                      for k, i in enumerate(pick)])
    res = {"n": int(len(pick)), "cos_min": round(float(cos.min()), 4),
           "cos_median": round(float(np.median(cos)), 4)}
    print(f"space check (api vs shard, same string): {res}", file=sys.stderr)
    return res


# ── Phase 2: topic OpenAI centroids ─────────────────────────────────────────

TOPICS_SQL = """
    SELECT id, label, state, first_seen, last_seen, agg_n_signals,
           category, is_umbrella, parent_id
    FROM dynamic_topics
    WHERE state = 'active' AND NOT is_junk
"""

MEMBERS_SQL = """
    SELECT tm.topic_id, s.headline
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.role = 'evidence' AND tm.topic_id LIKE 'dynamic-topic-%'
"""

FALLBACK_SQL = """
    SELECT dtm.dynamic_topic_id, s.headline
    FROM dynamic_topic_members dtm
    JOIN emergent_clusters ec ON ec.id = dtm.emergent_cluster_id
    JOIN signals_v2 s ON s.id = ANY(ec.sample_signal_ids)
    WHERE dtm.dynamic_topic_id = ANY($1::bigint[])
"""


async def _connect():
    import asyncpg
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set (source /Users/pedro/AtlasLocalWorker/.env)",
              file=sys.stderr)
        raise SystemExit(2)
    conn = await asyncpg.connect(url, statement_cache_size=0)
    try:
        await conn.execute("SET statement_timeout = '180s'")
    except Exception:  # noqa: BLE001 — pooler transaction mode rejects SET
        pass
    return conn


async def cmd_centroids(min_matched: int, cap: int, max_embed: int) -> None:
    conn = await _connect()
    try:
        topics = await conn.fetch(TOPICS_SQL)
        members = await conn.fetch(MEMBERS_SQL)
        print(f"{len(topics)} active topics, {len(members)} evidence rows",
              file=sys.stderr)
        by_topic: dict[int, dict[str, None]] = defaultdict(dict)  # ordered set
        for r in members:
            tid = int(r["topic_id"].rsplit("-", 1)[1])
            n = _norm(r["headline"] or "")
            if n and not _is_junk(n) and len(by_topic[tid]) < cap:
                by_topic[tid].setdefault(n)

        # top-up under-floor topics from emergent sample headlines BEFORE
        # embedding (the fallback lane of the task brief)
        tids = [int(t["id"]) for t in topics]
        short = [tid for tid in tids if len(by_topic.get(tid, ())) < min_matched]
        if short:
            fb = await conn.fetch(FALLBACK_SQL, short)
            print(f"fallback: {len(short)} topics under floor, "
                  f"{len(fb)} sample rows", file=sys.stderr)
            for r in fb:
                tid = int(r["dynamic_topic_id"])
                n = _norm(r["headline"] or "")
                if n and not _is_junk(n) and len(by_topic[tid]) < cap:
                    by_topic[tid].setdefault(n)
    finally:
        await conn.close()

    flat: list[str] = []
    spans: dict[int, tuple[int, int]] = {}
    for tid in tids:
        ns = list(by_topic.get(tid, ()))
        spans[tid] = (len(flat), len(ns))
        flat.extend(ns)

    vecs, hit = _gather_vectors(flat)
    shard_hit = hit.copy()
    print(f"shard hits: {int(shard_hit.sum())}/{len(flat)} "
          "(hot-window members are expected to miss — archive lags ~7d)",
          file=sys.stderr)
    space_check = (_space_consistency_check(flat, vecs, shard_hit)
                   if shard_hit.any() else {"n": 0})
    hit, fill_stats = _fill_missing_via_api(flat, vecs, hit, max_embed)

    ids, cents, cov_rows = [], [], []
    for t in topics:
        tid = int(t["id"])
        o, n = spans[tid]
        h = hit[o:o + n]
        m = int(h.sum())
        row = {
            "topic_id": tid, "label": t["label"],
            "first_seen": t["first_seen"].date().isoformat(),
            "last_seen": t["last_seen"].date().isoformat(),
            "agg_n_signals": int(t["agg_n_signals"]),
            "category": t["category"], "is_umbrella": bool(t["is_umbrella"]),
            "parent_id": t["parent_id"] and int(t["parent_id"]),
            "n_eligible": n, "n_matched": m,
            "n_from_shards": int(shard_hit[o:o + n].sum()),
            "coverage": round(m / n, 3) if n else 0.0,
            "included": m >= min_matched,
        }
        cov_rows.append(row)
        if m >= min_matched:
            c = vecs[o:o + n][h].mean(axis=0)
            c /= np.linalg.norm(c)
            ids.append(tid)
            cents.append(c)
    np.savez(INDEX_ROOT / "topic-centroids.npz",
             topic_ids=np.asarray(ids, dtype=np.int64),
             centroids=np.asarray(cents, dtype=np.float32))
    with open(INDEX_ROOT / "topic-coverage.jsonl", "w") as f:
        for r in cov_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    (INDEX_ROOT / "centroid-provenance.json").write_text(json.dumps({
        "space_check": space_check, "fill": fill_stats,
        "shard_hits": int(shard_hit.sum()), "total_member_norms": len(flat),
    }, indent=1))
    inc = [r for r in cov_rows if r["included"]]
    covs = np.asarray([r["coverage"] for r in inc])
    print(f"centroids: {len(inc)}/{len(cov_rows)} topics included "
          f"(floor {min_matched} matched); coverage median "
          f"{np.median(covs):.2f} / p10 {np.percentile(covs, 10):.2f}")


# ── Phase 3: the census ─────────────────────────────────────────────────────

def compute_country_floors(dominant_cc: list, unit_wk: np.ndarray,
                           U: np.ndarray, *, min_pairs: int = 150,
                           week_gap: int = 3, percentile: float = 95.0,
                           max_pairs_per_cc: int = 20_000,
                           rng: np.random.Generator | None = None) -> dict:
    """Per-country (language proxy) noise floor from a negative control.

    Leak this kills (2026-07-18 gate review, leak 5): in OpenAI space the
    SAME-LANGUAGE cosine floor of small-language countries sits ABOVE the
    global p75-fallback theta — e.g. UNRELATED Icelandic domestic units
    (accessibility policy vs footballer vs tasers) chain at >=0.862 purely
    on language, fabricating multi-week "steady" lineages. Same lesson as
    the 2026-07-03 per-centroid adaptive noise floor: a fixed threshold
    always serves junk where the local background is hot.

    Control construction: for each dominant country, pairs of that country's
    units >= `week_gap` weeks apart. Units are per-day archive clusters, so
    cross-week pairs share NO member signals by construction — the "no member
    overlap" guarantee without needing member ids. The `percentile` of their
    cosine distribution is that country's noise floor. Countries with fewer
    than `min_pairs` such pairs get NO floor (fall back to global theta) —
    never guessed from thin data.

    Pure (no I/O). Returns {cc: {floor, n_pairs, n_units}}.
    """
    rng = rng or np.random.default_rng(23)
    by_cc: dict[str, list[int]] = defaultdict(list)
    for i, cc in enumerate(dominant_cc):
        if cc:
            by_cc[cc].append(i)
    floors: dict[str, dict] = {}
    for cc, members in by_cc.items():
        idx = np.asarray(members)
        if len(idx) < 2:
            continue
        wk = unit_wk[idx].astype(np.int64)
        gap = np.abs(wk[:, None] - wk[None, :])
        xs, ys = np.nonzero(np.triu(gap >= week_gap, 1))
        if len(xs) < min_pairs:
            continue
        if len(xs) > max_pairs_per_cc:
            pick = rng.choice(len(xs), size=max_pairs_per_cc, replace=False)
            xs, ys = xs[pick], ys[pick]
        sims = np.einsum("ij,ij->i", U[idx[xs]], U[idx[ys]])
        floors[cc] = {
            "floor": round(float(np.percentile(sims, percentile)), 4),
            "n_pairs": int(len(xs)), "n_units": int(len(idx))}
    return floors


def effective_edge_threshold(theta: float, cc_a: str | None, cc_b: str | None,
                             floors: dict, margin: float) -> float:
    """A same-dominant-country edge must clear its country's noise floor.

    Cross-country (== usually cross-language) pairs keep the global theta —
    the leak is same-language chaining, and cross-language cosines are
    naturally depressed. Pure; testable.
    """
    if cc_a is not None and cc_a == cc_b and cc_a in floors:
        return max(theta, floors[cc_a]["floor"] + margin)
    return theta


def dominant_country_share(cc_lists: list, weights: list) -> tuple:
    """(dominant country, signal-weighted share) over units' top_cc[0].

    Pure. Used both to flag single_country lineages in the emission and to
    pick the country a gap-bridge must clear the floor for.
    """
    w: Counter = Counter()
    tot = 0.0
    for ccs, n in zip(cc_lists, weights):
        tot += n
        if ccs:
            w[ccs[0]] += n
    if not w or tot <= 0:
        return None, 0.0
    cc, x = w.most_common(1)[0]
    return cc, x / tot


SINGLE_COUNTRY_SHARE = 0.8


def _find_valley(vals: np.ndarray, lo: float = 0.30, hi: float = 0.98) -> dict:
    """Measured threshold: valley between the two dominant modes of `vals`.

    Same idiom as the umbrella 0.98 measurement — never guess, find the gap.
    Falls back (flagged) to the 25th percentile of the upper mode when the
    histogram is not clearly bimodal.
    """
    bins = np.arange(0.0, 1.0001, 0.01)
    hist, edges = np.histogram(vals, bins=bins)
    sm = np.convolve(hist.astype(float), np.ones(3) / 3, mode="same")
    centers = (edges[:-1] + edges[1:]) / 2
    keep = (centers >= lo) & (centers <= hi)
    peaks = [i for i in range(1, len(sm) - 1)
             if keep[i] and sm[i] >= sm[i - 1] and sm[i] >= sm[i + 1]
             and sm[i] > 0]
    peaks.sort(key=lambda i: -sm[i])
    valley, mode_lo, mode_hi, bimodal = None, None, None, False
    for a in peaks[:6]:
        for b in peaks[:6]:
            if centers[b] - centers[a] >= 0.08:  # distinct modes
                seg = slice(a + 1, b)
                v = a + 1 + int(np.argmin(sm[seg]))
                # a real valley dips well below both modes
                if sm[v] < 0.6 * min(sm[a], sm[b]):
                    if valley is None or sm[v] < sm[valley]:
                        valley, mode_lo, mode_hi, bimodal = v, a, b, True
    if valley is None:
        thr = float(np.percentile(vals, 75))
        return {"threshold": round(thr, 3), "bimodal": False,
                "note": "no clear valley — fallback p75, treat with caution",
                "hist": hist.tolist()}
    return {"threshold": round(float(centers[valley]), 3), "bimodal": True,
            "mode_low": round(float(centers[mode_lo]), 2),
            "mode_high": round(float(centers[mode_hi]), 2),
            "hist": hist.tolist()}


class _UF:
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
            self.p[rb] = ra


async def cmd_census(theta_uu: float | None, theta_tu: float | None,
                     edges_out: Path, summary_out: Path,
                     dead_min_signals: int, floor_margin: float = 0.02,
                     floor_min_pairs: int = 150, floor_week_gap: int = 3,
                     floor_percentile: float = 95.0) -> None:
    rng = np.random.default_rng(11)
    conn = await _connect()
    try:
        units_db = await conn.fetch(
            "SELECT id, day, label, n_signals, cohesion, top_cc "
            "FROM archive_story_units ORDER BY id")
    finally:
        await conn.close()

    # unit vectors: local Stage-B jsonl joined by (day,label) — first wins,
    # matching the loader's ON CONFLICT DO NOTHING insert semantics.
    local: dict[tuple[str, str], list[float]] = {}
    for line in open(UNITS_JSONL):
        d = json.loads(line)
        if d.get("centroid"):
            local.setdefault((d["day"], d["label"][:300]), d["centroid"])
    U = np.zeros((len(units_db), DIM), dtype=np.float32)
    unit_ids, unit_day, unit_week, unit_n, unit_label, unit_cc = [], [], [], [], [], []
    missing = []
    for i, r in enumerate(units_db):
        key = (r["day"].isoformat(), r["label"])
        v = local.get(key)
        if v is None:
            missing.append(int(r["id"]))
        else:
            U[i] = np.asarray(v, dtype=np.float32)
        unit_ids.append(int(r["id"]))
        unit_day.append(r["day"].isoformat())
        unit_week.append(_monday(r["day"]))
        unit_n.append(int(r["n_signals"]))
        unit_label.append(html.unescape(r["label"]))
        unit_cc.append(list(r["top_cc"] or []))
    if missing:
        print(f"WARN {len(missing)} units missing from local jsonl — "
              f"fetching vec from DB", file=sys.stderr)
        conn = await _connect()
        try:
            rows = await conn.fetch(
                "SELECT id, vec::text AS v FROM archive_story_units "
                "WHERE id = ANY($1::bigint[])", missing)
        finally:
            await conn.close()
        pos = {uid: i for i, uid in enumerate(unit_ids)}
        for r in rows:
            U[pos[int(r["id"])]] = np.asarray(
                json.loads(r["v"]), dtype=np.float32)
    U /= np.maximum(np.linalg.norm(U, axis=1, keepdims=True), 1e-9)

    weeks = sorted(set(unit_week))
    widx = {w: k for k, w in enumerate(weeks)}
    unit_wk = np.asarray([widx[w] for w in unit_week])
    by_week = {k: np.nonzero(unit_wk == k)[0] for k in range(len(weeks))}
    print(f"{len(unit_ids)} units across {len(weeks)} weeks "
          f"({weeks[0]} .. {weeks[-1]})", file=sys.stderr)

    # topic centroids
    tz = np.load(INDEX_ROOT / "topic-centroids.npz")
    topic_ids = tz["topic_ids"]
    C = tz["centroids"]
    cov = {json.loads(l)["topic_id"]: json.loads(l)
           for l in open(INDEX_ROOT / "topic-coverage.jsonl")}

    # ---- threshold measurement ----
    best_next: list[float] = []
    for k in range(len(weeks) - 1):
        a, b = by_week[k], by_week[k + 1]
        if len(a) and len(b):
            best_next.extend((U[a] @ U[b].T).max(axis=1).tolist())
    best_next = np.asarray(best_next)
    uu_measure = _find_valley(best_next)

    # negative control — >=3 weeks apart, disjoint top_cc (junk anchor)
    n_ctrl, ctrl = 200_000, []
    ii = rng.integers(0, len(unit_ids), n_ctrl * 2)
    jj = rng.integers(0, len(unit_ids), n_ctrl * 2)
    for i, j in zip(ii, jj):
        if abs(int(unit_wk[i]) - int(unit_wk[j])) >= 3 and \
                not (set(unit_cc[i]) & set(unit_cc[j])):
            ctrl.append(float(U[i] @ U[j]))
            if len(ctrl) >= n_ctrl:
                break
    ctrl = np.asarray(ctrl)
    ctrl_p = {p: round(float(np.percentile(ctrl, p)), 3)
              for p in (50, 95, 99, 99.9)}

    # per-country noise floors (leak 5 — the Icelandic-blob killer)
    dom_cc = [ccs[0] if ccs else None for ccs in unit_cc]
    floors = compute_country_floors(
        dom_cc, unit_wk, U, min_pairs=floor_min_pairs,
        week_gap=floor_week_gap, percentile=floor_percentile)

    G_tu = C @ U.T                      # (T, U)
    tu_best = G_tu.max(axis=1)
    tu_measure = _find_valley(tu_best)

    # when a distribution has no clean valley, never trust a bare percentile:
    # anchor to the negative-control junk quantile (wild-junk-quantile idiom)
    def _effective(measure: dict) -> float:
        t = measure["threshold"]
        return t if measure.get("bimodal") else max(t, ctrl_p[99.9])
    THETA_UU = theta_uu if theta_uu is not None else _effective(uu_measure)
    THETA_TU = theta_tu if theta_tu is not None else _effective(tu_measure)
    print(f"theta_uu={THETA_UU} (measured {uu_measure}), "
          f"theta_tu={THETA_TU} (measured {tu_measure}), "
          f"control p99={ctrl_p[99]} p99.9={ctrl_p[99.9]}", file=sys.stderr)
    hot = {cc: f for cc, f in floors.items()
           if f["floor"] + floor_margin > THETA_UU}
    print(f"country floors: {len(floors)} measured (min_pairs="
          f"{floor_min_pairs}, gap>={floor_week_gap}w, p{floor_percentile:g}"
          f"+{floor_margin}); {len(hot)} ABOVE theta_uu: "
          + ", ".join(f"{cc}={f['floor']}" for cc, f in
                      sorted(hot.items(), key=lambda kv: -kv[1]["floor"])),
          file=sys.stderr)

    # ---- edges ----
    def _keep(th: float, i: int, j: int, s: float) -> bool:
        return s >= effective_edge_threshold(
            th, dom_cc[i], dom_cc[j], floors, floor_margin)

    def build_edges(th: float):
        uu = []
        for k in range(len(weeks)):
            a = by_week[k]
            if len(a) > 1:                       # intra-week (same story, other day)
                B = U[a] @ U[a].T
                for x, y in zip(*np.nonzero(np.triu(B >= th, 1))):
                    i, j, s = int(a[x]), int(a[y]), float(B[x, y])
                    if _keep(th, i, j, s):
                        uu.append((i, j, s, "intra"))
            if k + 1 < len(weeks):
                b = by_week[k + 1]
                if len(a) and len(b):
                    B = U[a] @ U[b].T
                    for x, y in zip(*np.nonzero(B >= th)):
                        i, j, s = int(a[x]), int(b[y]), float(B[x, y])
                        if _keep(th, i, j, s):
                            uu.append((i, j, s, "adjacent"))
        return uu

    def build_lineages(th: float):
        uu = build_edges(th)
        uf = _UF(len(unit_ids))
        for x, y, _, _ in uu:
            uf.union(x, y)
        # component-level 1-week gap bridge (era centroid vs era centroid)
        comps: dict[int, list[int]] = defaultdict(list)
        for i in range(len(unit_ids)):
            comps[uf.find(i)].append(i)
        # era centroid per (comp, week)
        def era_centroid(members, k):
            m = [i for i in members if unit_wk[i] == k]
            if not m:
                return None
            w = np.asarray([unit_n[i] for i in m], dtype=np.float32)
            c = (U[m] * w[:, None]).sum(axis=0)
            nrm = np.linalg.norm(c)
            return c / nrm if nrm > 0 else None
        bridges = []
        comp_list = list(comps.items())
        ends = []   # (comp_root, last_week, centroid)
        starts = []  # (comp_root, first_week, centroid)
        for root, members in comp_list:
            ks = sorted({int(unit_wk[i]) for i in members})
            ce = era_centroid(members, ks[-1])
            cs = era_centroid(members, ks[0])
            if ce is not None:
                ends.append((root, ks[-1], ce, members))
            if cs is not None:
                starts.append((root, ks[0], cs, members))
        starts_by_week: dict[int, list] = defaultdict(list)
        for root_b, wb, cb, mem_b in starts:
            starts_by_week[wb].append((root_b, wb, cb, mem_b))
        def comp_dom(members):
            return dominant_country_share(
                [unit_cc[i] for i in members],
                [unit_n[i] for i in members])[0]
        for root_a, wa, ca, mem_a in ends:
            for root_b, wb, cb, mem_b in starts_by_week.get(wa + 2, ()):
                if root_a != root_b:
                    s = float(ca @ cb)
                    if s >= effective_edge_threshold(
                            th, comp_dom(mem_a), comp_dom(mem_b),
                            floors, floor_margin):
                        # representative unit pair for the edge dump
                        aa = [i for i in mem_a if unit_wk[i] == wa]
                        bb = [i for i in mem_b if unit_wk[i] == wb]
                        B = U[aa] @ U[bb].T
                        x, y = np.unravel_index(int(B.argmax()), B.shape)
                        bridges.append((int(aa[x]), int(bb[y]),
                                        float(B[x, y]), "gap-bridge"))
        for x, y, _, _ in bridges:
            uf.union(x, y)
        final: dict[int, list[int]] = defaultdict(list)
        for i in range(len(unit_ids)):
            final[uf.find(i)].append(i)
        return uu + bridges, final

    uu_edges, comps = build_lineages(THETA_UU)

    # sensitivity: census counts at theta +/- 0.02 (span counts only —
    # singletons are span-1 and cannot affect the >=4w / >=8w numbers)
    def census_counts(th: float):
        _, cc = build_lineages(th)
        spans = np.asarray([
            max(int(unit_wk[i]) for i in members)
            - min(int(unit_wk[i]) for i in members) + 1
            for members in cc.values()])
        return {"span_ge_4w": int((spans >= 4).sum()),
                "span_ge_8w": int((spans >= 8).sum())}
    sensitivity = {f"{round(THETA_UU + d, 2):.2f}":
                   census_counts(round(THETA_UU + d, 2))
                   for d in (-0.02, 0.0, 0.02)}

    # topic->unit edges
    tu_edges = []
    for t in range(len(topic_ids)):
        for u in np.nonzero(G_tu[t] >= THETA_TU)[0]:
            tu_edges.append((int(topic_ids[t]), int(u), float(G_tu[t, u])))

    # ---- lineage records ----
    unit_to_comp = {}
    for root, members in comps.items():
        for i in members:
            unit_to_comp[i] = root
    topics_by_comp: dict[int, dict[int, float]] = defaultdict(dict)
    for tid, u, s in tu_edges:
        root = unit_to_comp[u]
        topics_by_comp[root][tid] = max(topics_by_comp[root].get(tid, 0.0), s)

    lineages = []
    for root, members in comps.items():
        ks = sorted({int(unit_wk[i]) for i in members})
        span = ks[-1] - ks[0] + 1
        total = sum(unit_n[i] for i in members)
        if len(members) == 1 and span == 1 and not topics_by_comp.get(root):
            continue  # singleton with no live attach — not a lineage
        weekly = {}
        prev_c = None
        drift = []
        for k in range(ks[0], ks[-1] + 1):
            m = [i for i in members if unit_wk[i] == k]
            if not m:
                weekly[weeks[k]] = None  # era gap inside the lineage
                continue
            w = np.asarray([unit_n[i] for i in m], dtype=np.float32)
            c = (U[m] * w[:, None]).sum(axis=0)
            c /= max(np.linalg.norm(c), 1e-9)
            big = max(m, key=lambda i: unit_n[i])
            ccs = Counter()
            for i in m:
                for rank, cc0 in enumerate(unit_cc[i]):
                    ccs[cc0] += unit_n[i] / (rank + 1)
            weekly[weeks[k]] = {
                "n_units": len(m), "n_signals": int(sum(unit_n[i] for i in m)),
                "label": unit_label[big][:120],
                "countries": [c0 for c0, _ in ccs.most_common(4)],
                "drift_cos_prev": (round(float(prev_c @ c), 4)
                                   if prev_c is not None else None),
            }
            if prev_c is not None:
                drift.append(float(prev_c @ c))
            prev_c = c
        att = sorted(topics_by_comp.get(root, {}).items(),
                     key=lambda kv: -kv[1])
        dom_l, dom_share = dominant_country_share(
            [unit_cc[i] for i in members], [unit_n[i] for i in members])
        lineages.append({
            "lineage_id": f"lin-{min(unit_ids[i] for i in members)}",
            "n_units": len(members),
            "dominant_country": dom_l,
            "dominant_share": round(dom_share, 3),
            # single-dominant-country lineages survive their country's noise
            # floor but stay CAVEATED: one language, one press pool — the
            # census cannot distinguish a national story arc from national
            # news adjacency as strongly as cross-country lineages.
            "single_country": bool(dom_l) and dom_share >= SINGLE_COUNTRY_SHARE,
            "first_week": weeks[ks[0]], "last_week": weeks[ks[-1]],
            "span_weeks": span, "weeks_present": len(ks),
            "total_signals": total,
            "weekly": weekly,
            "min_drift_cos": round(min(drift), 4) if drift else None,
            "attached_topics": [
                {"topic_id": tid, "sim": round(s, 4),
                 "label": cov.get(tid, {}).get("label"),
                 "topic_first_seen": cov.get(tid, {}).get("first_seen"),
                 "topic_last_seen": cov.get(tid, {}).get("last_seen")}
                for tid, s in att],
            "unit_ids": sorted(unit_ids[i] for i in members),
        })
    lineages.sort(key=lambda l: -l["total_signals"])

    # ---- census tables ----
    spans = np.asarray([l["span_weeks"] for l in lineages])
    living = [l for l in lineages if l["attached_topics"]]
    dead = [l for l in lineages
            if not l["attached_topics"] and l["span_weeks"] >= 3
            and l["total_signals"] >= dead_min_signals]
    census = {
        "lineages_total": len(lineages),
        "span_ge_4w": int((spans >= 4).sum()),
        "span_ge_8w": int((spans >= 8).sum()),
        "living": len(living),
        "living_span_ge_4w": sum(1 for l in living if l["span_weeks"] >= 4),
        "dead_ge_3w": len(dead),
        "single_country_ge_4w": sum(
            1 for l in lineages
            if l["span_weeks"] >= 4 and l["single_country"]),
        "sensitivity": sensitivity,
    }

    # ---- outputs ----
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    inc_cov = [c for c in cov.values() if c.get("included")]
    method = {
        "generated_at": date.today().isoformat(),
        "space": "openai/text-embedding-3-small (unit vecs + topic centroids "
                 "both = mean of member-headline vectors, L2-normalized)",
        "units": {"n": len(unit_ids), "first_day": min(unit_day),
                  "last_day": max(unit_day), "weeks": weeks},
        "unit_hole": "archive units end 2026-07-03 (Stage-B clustered through "
                     "then); live topics carry 2026-07-04..present — the "
                     "stitch crosses this hole and is labeled, not hidden",
        "topics": {"active_considered": len(cov),
                   "included": len(inc_cov),
                   "coverage_median": round(float(np.median(
                       [c["coverage"] for c in inc_cov])), 3)},
        "theta_unit_unit": THETA_UU, "theta_topic_unit": THETA_TU,
        "theta_measurement": {"unit_unit": uu_measure,
                              "topic_unit": tu_measure,
                              "negative_control_percentiles": ctrl_p,
                              "control_n": len(ctrl)},
        # leak 1 folded honestly: the global thresholds STAY p75-fallback
        # all-candidate (no faked valley); leak 5 fix = per-country floors
        # layered ON TOP of theta for same-dominant-country edges.
        "per_country_floor": {
            "margin": floor_margin, "week_gap": floor_week_gap,
            "percentile": floor_percentile, "min_pairs": floor_min_pairs,
            "n_countries": len(floors),
            "n_above_theta_uu": len(hot),
            "rule": "same-dominant-country edge survives only if sim > "
                    "max(theta, country_p95_negative_control + margin); "
                    "control pairs are same-country units >= week_gap weeks "
                    "apart (per-day clusters -> no member overlap by "
                    "construction)",
            "floors": {cc: f["floor"]
                       for cc, f in sorted(floors.items())},
        },
    }
    with open(edges_out, "w") as f:
        json.dump({
            "method": method,
            "topic_unit_edges": [
                {"topic_id": t, "unit_id": unit_ids[u], "sim": round(s, 4),
                 "week": unit_week[u]} for t, u, s in tu_edges],
            "unit_unit_edges": [
                {"src_unit_id": unit_ids[x], "dst_unit_id": unit_ids[y],
                 "sim": round(s, 4), "src_week": unit_week[x],
                 "dst_week": unit_week[y], "kind": kind}
                for x, y, s, kind in uu_edges],
            "lineages": lineages,
        }, f, ensure_ascii=False)
    with open(summary_out, "w") as f:
        json.dump({"method": method, "census": census,
                   "top_living": living[:20], "top_dead": dead[:15]},
                  f, ensure_ascii=False, indent=1)

    print(json.dumps({"census": census,
                      "edges": {"topic_unit": len(tu_edges),
                                "unit_unit": len(uu_edges)}}, indent=1))
    print("\nTOP 15 LIVING LINEAGES")
    for l in living[:15]:
        att = l["attached_topics"][0]
        print(f"  {l['lineage_id']:>10} span={l['span_weeks']}w "
              f"n={l['total_signals']:>6} {l['first_week']}..{l['last_week']} "
              f"-> [{att['topic_id']}] {str(att['label'])[:60]} "
              f"(sim {att['sim']})")
    print("\nTOP 10 DEAD LINEAGES (no living descendant)")
    for l in dead[:10]:
        lw = [w for w, v in l["weekly"].items() if v]
        lab = l["weekly"][lw[-1]]["label"] if lw else "?"
        print(f"  {l['lineage_id']:>10} span={l['span_weeks']}w "
              f"n={l['total_signals']:>6} {l['first_week']}..{l['last_week']} "
              f"last-era: {lab[:70]}")


# ── main ────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_idx = sub.add_parser("index")
    p_idx.add_argument("--force", action="store_true")
    p_cen = sub.add_parser("centroids")
    p_cen.add_argument("--min-matched", type=int, default=5)
    p_cen.add_argument("--cap", type=int, default=500)
    p_cen.add_argument("--max-embed", type=int, default=150_000,
                       help="cost guard: abort if more unique headlines than "
                            "this would go to the OpenAI API")
    p_cns = sub.add_parser("census")
    p_all = sub.add_parser("all")
    for p in (p_cns, p_all):
        p.add_argument("--theta-uu", type=float, default=None,
                       help="override the measured unit-unit threshold")
        p.add_argument("--theta-tu", type=float, default=None,
                       help="override the measured topic-unit threshold")
        p.add_argument("--edges-out", type=Path,
                       default=OUT_DIR / "lineage-edges.json")
        p.add_argument("--summary-out", type=Path,
                       default=INDEX_ROOT / "census-summary.json")
        p.add_argument("--dead-min-signals", type=int, default=400)
        p.add_argument("--floor-margin", type=float, default=0.02,
                       help="margin above the per-country p95 noise floor")
        p.add_argument("--floor-min-pairs", type=int, default=150,
                       help="min same-country cross-week control pairs to "
                            "measure a floor (else global theta only)")
        p.add_argument("--floor-week-gap", type=int, default=3,
                       help="min week separation of control pairs")
        p.add_argument("--floor-percentile", type=float, default=95.0)
    p_all.add_argument("--min-matched", type=int, default=5)
    p_all.add_argument("--cap", type=int, default=500)
    p_all.add_argument("--max-embed", type=int, default=150_000)
    args = ap.parse_args()

    def _census():
        return cmd_census(args.theta_uu, args.theta_tu,
                          args.edges_out, args.summary_out,
                          args.dead_min_signals,
                          floor_margin=args.floor_margin,
                          floor_min_pairs=args.floor_min_pairs,
                          floor_week_gap=args.floor_week_gap,
                          floor_percentile=args.floor_percentile)

    if args.cmd == "index":
        cmd_index(force=args.force)
    elif args.cmd == "centroids":
        cmd_index()
        asyncio.run(cmd_centroids(args.min_matched, args.cap, args.max_embed))
    elif args.cmd == "census":
        asyncio.run(_census())
    else:
        cmd_index()
        asyncio.run(cmd_centroids(args.min_matched, args.cap, args.max_embed))
        asyncio.run(_census())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
