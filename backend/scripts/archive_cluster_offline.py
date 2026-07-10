"""Archive Intelligence Tier builder (spec 2026-07-10).

Clusters the ALREADY-EMBEDDED history (OpenAI shards on the external disk)
into archive topics, window by window, and writes ONLY light rows to Supabase
(archive_topics + daily aggregates + evidence samples). Per-story assignments
go to parquet on the external disk. Resumable via a checkpoint file.

Heavy data NEVER leaves the disk — see the spec's golden rule and the
2026-07-08 DB-capacity incident (docs/state/2026-07-08-embedding-throughput-fix.md).

Usage (M1, mlvenv, nightly/mindful):
    python -m scripts.archive_cluster_offline \
        [--from 2026-05-03] --to 2026-07-03 [--build-id archive-v1] \
        [--shards-root /Volumes/Ext/Atlas/Embeddings/openai-3-small] \
        [--out-root /Volumes/Ext/Atlas/ArchiveTopics] \
        [--archive-root /Volumes/Ext/Atlas/Archive] \
        [--max-scope 60000] [--windows 1] [--dry-run]
"""
from __future__ import annotations

import argparse
import asyncio
import glob
import gzip
import hashlib
import html
import json
import os
import re
import sys
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

MODEL_VERSION = "archive-topics-v1"
GLOBAL_SCOPE = "__global__"

_JUNK = re.compile(r"^(digit:|in words:|story\d|doc \S+\.shtml)|^\W*$", re.I)


# ── pure helpers (unit-tested) ────────────────────────────────────────────────

def _norm(h: str) -> str:
    # MUST mirror archive_embed_pipeline._norm — sha1 keys join shards↔partitions.
    return re.sub(r"\s+", " ", html.unescape(h).strip().lower())


def sha1_of_headline(h: str) -> str:
    return hashlib.sha1(_norm(h).encode()).hexdigest()


def iter_windows(start: date, end: date):
    """Yield contiguous ≤7-day (win_start, win_end) inclusive windows, NEWEST first."""
    cur_end = end
    while cur_end >= start:
        cur_start = max(start, cur_end - timedelta(days=6))
        yield (cur_start, cur_end)
        cur_end = cur_start - timedelta(days=1)


def group_scopes(rows: list[dict]) -> dict[str, list[dict]]:
    """Country scopes (R1 pattern); stories without a cc go to one global scope."""
    scopes: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        cc = (r.get("cc") or "").strip().upper()
        scopes[cc if len(cc) == 2 else GLOBAL_SCOPE].append(r)
    return dict(scopes)


def checkpoint_load(path) -> dict:
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return {"done_windows": []}


def _wkey(s: date, e: date) -> str:
    return f"{s.isoformat()}..{e.isoformat()}"


def checkpoint_done(ck: dict, s: date, e: date) -> bool:
    return _wkey(s, e) in ck.get("done_windows", [])


def checkpoint_mark(ck: dict, path, s: date, e: date) -> None:
    ck.setdefault("done_windows", []).append(_wkey(s, e))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(p) + ".tmp")
    tmp.write_text(json.dumps(ck, indent=1))
    tmp.replace(p)


def build_topic_row(*, label: str, category: str | None, crisis: bool | None,
                    scope: str, members: list[dict], centroid, build_id: str) -> dict:
    dates = sorted(m["date"] for m in members)
    return {
        "label": label,
        "category": category,
        "crisis_relevant": crisis,
        "country_code": None if scope == GLOBAL_SCOPE else scope,
        "period_start": date.fromisoformat(dates[0]),
        "period_end": date.fromisoformat(dates[-1]),
        "n_stories": len(members),
        "centroid_vec": [float(x) for x in centroid],
        "sample_story_ids": [m["sha1"] for m in members[:24]],
        "build_id": build_id,
    }


# ── disk IO ──────────────────────────────────────────────────────────────────

def load_window_vectors(shards_root: Path, win_start: date, win_end: date):
    """One pass over shard metas; collect rows+vecs whose date ∈ window.

    Returns (rows, vecs float32 L2-normalized). Junk filter mirrors
    archive_embed_pipeline._is_junk.
    """
    import numpy as np
    rows: list[dict] = []
    vec_chunks: list[np.ndarray] = []
    metas = sorted(glob.glob(str(shards_root / "shard-*.meta.jsonl")))
    lo, hi = win_start.isoformat(), win_end.isoformat()
    for meta_path in metas:
        keep_idx: list[int] = []
        keep_rows: list[dict] = []
        with open(meta_path) as f:
            for i, line in enumerate(f):
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                d = r.get("date") or ""
                if not (lo <= d <= hi):
                    continue
                h = html.unescape(r.get("headline") or "")
                if len(h) < 20 or _JUNK.search(h):
                    continue
                r["headline"] = h
                keep_idx.append(i)
                keep_rows.append(r)
        if not keep_idx:
            continue
        npz = np.load(meta_path.replace(".meta.jsonl", ".npz"))
        v = npz["vecs"][keep_idx].astype(np.float32)
        v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
        vec_chunks.append(v)
        rows.extend(keep_rows)
    if not rows:
        return [], None
    return rows, np.vstack(vec_chunks)


def load_evidence_lookup(archive_root: Path, win_start: date, win_end: date) -> dict:
    """sha1 -> {url, source, family, klass, ts, sentiment, path, dup} from day
    partitions. One gzip scan per day; ~160K rows/day, seconds each on the M1.
    `dup` counts syndicated repeats of the same headline (feeds n_signals).
    """
    out: dict[str, dict] = {}
    d = win_start
    while d <= win_end:
        pat = str(archive_root / "cutovers" / "*" / "signals" /
                  f"year={d.year}" / f"month={d.month:02d}" / f"day={d.day:02d}" /
                  "source_family=*" / "part-*.jsonl.gz")
        for part in glob.glob(pat):
            rel = os.path.relpath(part, archive_root)
            try:
                with gzip.open(part, "rt") as f:
                    for line in f:
                        try:
                            r = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        h = r.get("headline") or ""
                        if len(h) < 20:
                            continue
                        k = sha1_of_headline(h)
                        cur = out.get(k)
                        if cur is None:
                            out[k] = {
                                "url": r.get("source_url"),
                                "source": r.get("source_name"),
                                "family": r.get("source_family") or "press",
                                "klass": r.get("signal_class") or "news",
                                "ts": r.get("timestamp"),
                                "sentiment": r.get("nlp_sentiment") or r.get("sentiment"),
                                "path": rel,
                                "dup": 1,
                            }
                        else:
                            cur["dup"] += 1
            except OSError as e:
                print(f"  WARN: unreadable partition {part}: {e}", file=sys.stderr)
        d += timedelta(days=1)
    return out


# ── clustering + typing ──────────────────────────────────────────────────────

def cluster_scope(vecs, min_cluster_size: int = 4):
    """HDBSCAN leaf over L2-normalized vecs (euclidean ≡ cosine order).

    2026-07-10 perf fix: HDBSCAN in raw 1536d over a 60K scope ran >50 min on
    the M1 (US scope alone) — O(n²) distances in high dim. For clustering ONLY,
    reduce with randomized PCA to 128d + renormalize (cosine structure holds at
    this granularity; same practice as the universe layout). Topic CENTROIDS
    are still computed from the ORIGINAL 1536d vectors by the caller, so the
    serving-side query match space is untouched.
    """
    import hdbscan
    import numpy as np
    work = vecs
    if work.shape[0] > 2000 and work.shape[1] > 128:
        from sklearn.decomposition import PCA
        work = PCA(n_components=128, svd_solver="randomized",
                   random_state=0).fit_transform(work)
        work = work / (np.linalg.norm(work, axis=1, keepdims=True) + 1e-9)
    cl = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=2,
                         metric="euclidean", cluster_selection_method="leaf")
    return cl.fit_predict(work)


_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def _deepseek(messages: list[dict], api_key: str) -> str | None:
    import urllib.request
    body = json.dumps({"model": "deepseek-chat", "messages": messages,
                       "temperature": 0, "max_tokens": 120}).encode()
    last: Exception | None = None
    for attempt in range(3):
        req = urllib.request.Request(
            _DEEPSEEK_URL, data=body, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001 — retry then honest None
            last = e
            time.sleep(2 * (attempt + 1))
    print(f"  WARN: DeepSeek failed after retries: {last}", file=sys.stderr)
    return None


def label_and_type_topic(headlines: list[str], categories: list[str],
                         api_key: str) -> tuple[str, str | None, bool | None]:
    """One DeepSeek call: short label + category from the LIVING menu (or none)."""
    menu = "\n".join(f"- {c}" for c in categories)
    sample = "\n".join(h[:140] for h in headlines[:12])
    content = _deepseek([
        {"role": "system", "content":
            "You label news story clusters. Reply STRICT JSON: "
            '{"label": "<max 8 words>", "category": "<slug from menu or none>", '
            '"crisis": true|false}. Use "none" when no menu category fits — '
            "never force-fit."},
        {"role": "user", "content":
            f"Category menu:\n{menu}\n\nCluster headlines:\n{sample}"},
    ], api_key)
    if not content:
        return (headlines[0][:80], None, None)
    try:
        m = re.search(r"\{.*\}", content, re.S)
        obj = json.loads(m.group(0)) if m else {}
        cat = obj.get("category")
        cat = None if (not cat or cat == "none" or cat not in categories) else cat
        return (str(obj.get("label") or headlines[0][:80])[:120], cat,
                obj.get("crisis") if isinstance(obj.get("crisis"), bool) else None)
    except (json.JSONDecodeError, AttributeError):
        return (headlines[0][:80], None, None)


# ── writers ──────────────────────────────────────────────────────────────────

async def upsert_window_aggregates(conn, daily_rows: list[dict],
                                   evidence_rows: list[dict]) -> None:
    async with conn.transaction():
        await conn.execute("SET LOCAL statement_timeout = 0")
        for d in daily_rows:
            await conn.execute(
                """INSERT INTO historical_topic_country_daily
                   (day, topic_slug, country_code, source_family, signal_class,
                    signal_count, model_version)
                   VALUES ($1,$2,$3,$4,$5,$6,$7)
                   ON CONFLICT (day, topic_slug, country_code, source_family,
                                signal_class, model_version)
                   DO UPDATE SET signal_count=EXCLUDED.signal_count, updated_at=NOW()""",
                d["day"], d["topic_slug"], d["country_code"], d["family"],
                d["klass"], d["count"], MODEL_VERSION)
        for e in evidence_rows:
            ts = e.get("ts")
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    ts = None
            sent = e.get("sentiment")
            try:
                sent = float(sent) if sent is not None else None
            except (TypeError, ValueError):
                sent = None
            await conn.execute(
                """INSERT INTO historical_evidence_samples
                   (sample_id, day, topic_slug, country_code, source_family,
                    signal_class, archive_relative_path, source_name, source_url,
                    headline, signal_timestamp, sentiment, selection_reason,
                    model_version)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                   ON CONFLICT (sample_id) DO NOTHING""",
                e["sample_id"], e["day"], e["topic_slug"], e["country_code"],
                e["family"], e["klass"], e["path"], e["source"], e["url"],
                e["headline"], ts, sent, "archive-topic-member", MODEL_VERSION)


def write_parquet(out_root: Path, assignments: list[dict], win_start: date) -> None:
    """Per-story assignments → month-partitioned parquet via DuckDB (stays on disk)."""
    import duckdb
    part_dir = out_root / "assignments" / f"month={win_start.strftime('%Y-%m')}"
    part_dir.mkdir(parents=True, exist_ok=True)
    dst = part_dir / f"part-{win_start.isoformat()}.parquet"
    con = duckdb.connect()
    con.execute("CREATE TABLE a (story_sha1 TEXT, topic_id BIGINT, sim REAL, "
                "country TEXT, day DATE)")
    con.executemany("INSERT INTO a VALUES (?,?,?,?,?)",
                    [(x["sha1"], x["topic_id"], x["sim"], x["cc"], x["day"])
                     for x in assignments])
    con.execute(f"COPY a TO '{dst}' (FORMAT PARQUET)")
    con.close()
    print(f"  parquet: {dst} ({len(assignments)} assignments)", file=sys.stderr)


# ── main flow ────────────────────────────────────────────────────────────────

async def process_window(conn, args, categories: list[str],
                         win_start: date, win_end: date) -> None:
    import numpy as np
    t0 = time.monotonic()
    rows, vecs = load_window_vectors(Path(args.shards_root), win_start, win_end)
    print(f"[{win_start}..{win_end}] {len(rows)} embedded stories", file=sys.stderr)
    if not rows:
        return

    scopes = group_scopes(rows)
    idx_of = {id(r): i for i, r in enumerate(rows)}
    topic_specs: list[dict] = []
    for scope, srows in sorted(scopes.items(), key=lambda kv: -len(kv[1])):
        if len(srows) < 4:
            continue
        if len(srows) > args.max_scope:
            print(f"  WARN scope {scope}: {len(srows)} > cap {args.max_scope}; "
                  f"clustering the newest {args.max_scope} "
                  f"({len(srows) - args.max_scope} dropped — logged, not silent)",
                  file=sys.stderr)
            srows = sorted(srows, key=lambda r: r["date"],
                           reverse=True)[:args.max_scope]
        sv = np.vstack([vecs[idx_of[id(r)]] for r in srows])
        labels = cluster_scope(sv)
        n_topics = 0
        for cid in sorted(set(labels) - {-1}):
            mask = labels == cid
            members = [r for r, m in zip(srows, mask) if m]
            centroid = sv[mask].mean(axis=0)
            centroid /= (np.linalg.norm(centroid) + 1e-9)
            topic_specs.append({"scope": scope, "members": members,
                                "centroid": centroid,
                                "sims": (sv[mask] @ centroid).tolist()})
            n_topics += 1
        print(f"  scope {scope}: {len(srows)} stories → {n_topics} clusters",
              file=sys.stderr)

    if args.dry_run:
        print(f"  DRY RUN: {len(topic_specs)} topics; skipping typing/writes "
              f"({time.monotonic()-t0:.0f}s)", file=sys.stderr)
        return

    lookup = load_evidence_lookup(Path(args.archive_root), win_start, win_end)
    print(f"  evidence lookup: {len(lookup)} distinct headlines", file=sys.stderr)

    # idempotency: delete-and-replace this build's window before inserting
    async with conn.transaction():
        await conn.execute("SET LOCAL statement_timeout = 0")
        await conn.execute(
            "DELETE FROM archive_topics WHERE build_id=$1 "
            "AND period_start >= $2 AND period_end <= $3",
            args.build_id, win_start, win_end)
        await conn.execute(
            "DELETE FROM historical_topic_country_daily WHERE model_version=$1 "
            "AND day BETWEEN $2 AND $3", MODEL_VERSION, win_start, win_end)
        await conn.execute(
            "DELETE FROM historical_evidence_samples WHERE model_version=$1 "
            "AND day BETWEEN $2 AND $3", MODEL_VERSION, win_start, win_end)

    daily_rows: list[dict] = []
    evidence_rows: list[dict] = []
    all_assignments: list[dict] = []
    for spec in topic_specs:
        members, sims, scope = spec["members"], spec["sims"], spec["scope"]
        label, cat, crisis = label_and_type_topic(
            [m["headline"] for m in members], categories, args.deepseek_key)
        t = build_topic_row(label=label, category=cat, crisis=crisis, scope=scope,
                            members=members, centroid=spec["centroid"],
                            build_id=args.build_id)
        fams: dict = defaultdict(int)
        n_signals = 0
        for m in members:
            info = lookup.get(m["sha1"]) or {}
            fams[info.get("family", "press")] += 1
            n_signals += info.get("dup", 1)
        tid = await conn.fetchval(
            """INSERT INTO archive_topics
               (label, category, crisis_relevant, country_code, period_start,
                period_end, n_stories, n_signals, centroid_vec, top_sources,
                sample_story_ids, build_id)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) RETURNING id""",
            t["label"], t["category"], t["crisis_relevant"], t["country_code"],
            t["period_start"], t["period_end"], t["n_stories"], n_signals,
            t["centroid_vec"], json.dumps(dict(fams)), t["sample_story_ids"],
            t["build_id"])
        slug = f"archive-topic-{tid}"
        per_day: dict = defaultdict(int)
        for m, s in zip(members, sims):
            info = lookup.get(m["sha1"]) or {}
            cc = t["country_code"] or (m.get("cc") or "GLOBAL")
            per_day[(m["date"], cc, info.get("family", "press"),
                     info.get("klass", "news"))] += info.get("dup", 1)
            all_assignments.append({"sha1": m["sha1"], "topic_id": tid,
                                    "sim": float(s), "cc": m.get("cc"),
                                    "day": date.fromisoformat(m["date"])})
        for (d, cc, fam, kl), n in per_day.items():
            daily_rows.append({"day": date.fromisoformat(d), "topic_slug": slug,
                               "country_code": cc, "family": fam, "klass": kl,
                               "count": n})
        seen_src: set = set()
        for m in sorted(members, key=lambda x: x["date"]):
            info = lookup.get(m["sha1"])
            if not info or not info.get("url") or info.get("source") in seen_src:
                continue
            seen_src.add(info.get("source"))
            evidence_rows.append({
                "sample_id": f"{slug}:{m['sha1'][:16]}",
                "day": date.fromisoformat(m["date"]), "topic_slug": slug,
                "country_code": t["country_code"] or (m.get("cc") or "GLOBAL"),
                "family": info["family"], "klass": info["klass"],
                "path": info["path"], "source": info["source"], "url": info["url"],
                "headline": m["headline"][:300], "ts": info.get("ts"),
                "sentiment": info.get("sentiment"),
            })
            if len(seen_src) >= 5:
                break

    await upsert_window_aggregates(conn, daily_rows, evidence_rows)
    write_parquet(Path(args.out_root), all_assignments, win_start)
    print(f"  window done in {time.monotonic()-t0:.0f}s: {len(topic_specs)} topics, "
          f"{len(all_assignments)} assignments, {len(evidence_rows)} evidence",
          file=sys.stderr)


async def amain() -> int:
    import asyncpg
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="dfrom", default="2026-05-03")
    p.add_argument("--to", dest="dto", required=True)
    p.add_argument("--build-id", default="archive-v1")
    p.add_argument("--shards-root",
                   default="/Volumes/Ext/Atlas/Embeddings/openai-3-small")
    p.add_argument("--out-root", default="/Volumes/Ext/Atlas/ArchiveTopics")
    p.add_argument("--archive-root", default="/Volumes/Ext/Atlas/Archive")
    p.add_argument("--max-scope", type=int, default=60000)
    p.add_argument("--windows", type=int, default=0,
                   help="process at most N windows this run (0 = all remaining)")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    args.deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not args.deepseek_key and not args.dry_run:
        print("DEEPSEEK_API_KEY missing", file=sys.stderr)
        return 2
    if not Path(args.shards_root).exists():
        print(f"shards root not mounted: {args.shards_root}", file=sys.stderr)
        return 2

    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    await conn.execute("SET statement_timeout = 0")
    try:
        categories = [r["slug"] for r in await conn.fetch(
            "SELECT slug FROM atlas_topics WHERE is_active ORDER BY slug")]
        ck_path = Path(args.out_root) / "checkpoints" / f"build-{args.build_id}.json"
        ck = checkpoint_load(ck_path)
        done = 0
        for ws, we in iter_windows(date.fromisoformat(args.dfrom),
                                   date.fromisoformat(args.dto)):
            if checkpoint_done(ck, ws, we):
                continue
            await process_window(conn, args, categories, ws, we)
            if not args.dry_run:
                checkpoint_mark(ck, ck_path, ws, we)
            done += 1
            if args.windows and done >= args.windows:
                break
        print(f"run complete: {done} windows processed", file=sys.stderr)
        return 0
    finally:
        await conn.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(amain()))
