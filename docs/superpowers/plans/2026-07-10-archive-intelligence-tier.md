# Archive Intelligence Tier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Process the FULL history (May-03 → hot boundary) into archive topics on the M1 — heavy data stays on the external disk, Supabase gets only topics + aggregates + samples, served by a new `archive/search` endpoint.

**Architecture:** Offline builder reads the already-computed OpenAI shards (42GB, `/Volumes/Ext/Atlas/Embeddings/openai-3-small`), clusters per (country, week) with HDBSCAN, types with DeepSeek against the living taxonomy, upserts light rows to Supabase, writes per-story assignments to parquet on disk. Fly serves search by embedding the query with OpenAI and cosine-scanning the few thousand `archive_topics` centroids — no HNSW, no per-story rows in the DB.

**Tech Stack:** Python (mlvenv: numpy/hdbscan installed; duckdb to install), asyncpg, FastAPI, OpenAI embeddings API (query-side), DeepSeek chat API (typing).

**Spec:** `docs/specs/2026-07-10-archive-intelligence-tier.md`

**Grounded facts (verified 2026-07-10, do not re-derive):**
- Shards: `shard-NNNN.npz` (`z['vecs']`, float16, ≤5000×1536) + `shard-NNNN.meta.jsonl`, one row per vector: `{"sha1","headline"(≤300 chars, HTML-escaped),"date":"YYYY-MM-DD","cc","lang"}`. 166 shard pairs + `manifest.json`.
- `sha1 = hashlib.sha1(_norm(headline).encode()).hexdigest()` where `_norm = re.sub(r"\s+"," ", html.unescape(h).strip().lower())` (from `archive_embed_pipeline.py:49`).
- Archive partitions (`/Volumes/Ext/Atlas/Archive/cutovers/*/signals/year=*/month=*/day=*/source_family=*/part-*.jsonl.gz`) carry full rows incl. `source_url`, `source_name`, `headline`, `timestamp`, `sentiment`, `signal_class`, `source_family` → evidence lookup by recomputing the sha1 from the partition headline.
- `historical_topic_country_daily` PK = (day, topic_slug, country_code, source_family, signal_class, model_version); `historical_evidence_samples` PK = sample_id, requires `archive_relative_path`, `selection_reason`, `model_version` (migration 029).
- mlvenv: `hdbscan`, `numpy`, `sklearn` present; `duckdb`, `pyarrow` MISSING.
- Supabase pooler enforces `statement_timeout=2min`; every long-running connection must `SET statement_timeout = 0` (session pooler honours it; see `docs/state/2026-07-08-embedding-throughput-fix.md`).
- DB discipline: `archive_topics.centroid_vec` = `REAL[]`, **never** add a vector index to it.
- Env keys live in `~/AtlasLocalWorker/.env` (`DATABASE_URL`, `OPENAI_API_KEY`, `DEEPSEEK_API_KEY`).

---

### Task 1: Migration 073 — `archive_topics`

**Files:**
- Create: `backend/migrations/073_archive_topics.sql`

- [ ] **Step 1: Write the migration**

```sql
-- 073_archive_topics.sql
-- Archive Intelligence Tier (spec 2026-07-10): one LIGHT row per historical
-- topic. Centroids are REAL[] (OpenAI text-embedding-3-small, 1536d) with NO
-- vector index — at thousands of rows a scan+cosine answers in <100ms, and a
-- second HNSW competing for the Micro's ~1GB RAM is the exact failure mode
-- measured on 2026-07-08/10 (36h thrashing rebuild). Per-story detail and the
-- 42GB of vectors stay on the external disk (parquet + shards).

CREATE TABLE IF NOT EXISTS archive_topics (
    id               BIGSERIAL PRIMARY KEY,
    label            TEXT NOT NULL,
    category         TEXT,
    crisis_relevant  BOOLEAN,
    country_code     CHAR(2),
    period_start     DATE NOT NULL,
    period_end       DATE NOT NULL,
    n_stories        INT NOT NULL CHECK (n_stories > 0),
    n_signals        INT,
    centroid_vec     REAL[] NOT NULL,
    top_sources      JSONB,
    sample_story_ids TEXT[],
    build_id         TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT archive_topics_period_valid CHECK (period_end >= period_start)
);

CREATE INDEX IF NOT EXISTS idx_archive_topics_period
    ON archive_topics (period_start, period_end);
CREATE INDEX IF NOT EXISTS idx_archive_topics_country
    ON archive_topics (country_code, period_start);
CREATE INDEX IF NOT EXISTS idx_archive_topics_build
    ON archive_topics (build_id);

ALTER TABLE archive_topics ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS archive_topics_read ON archive_topics;
CREATE POLICY archive_topics_read ON archive_topics FOR SELECT USING (true);
```

- [ ] **Step 2: Apply to Supabase** (MCP `apply_migration` with name `073_archive_topics`, or psql). Verify:

Run: `SELECT indexname FROM pg_indexes WHERE tablename='archive_topics';`
Expected: 4 indexes (pkey + the 3 created).

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/073_archive_topics.sql
git commit -m "feat(archive): migration 073 archive_topics — light topic rows, REAL[] centroids, no vector index"
```

---

### Task 2: Builder pure helpers + tests (TDD)

**Files:**
- Create: `backend/scripts/archive_cluster_offline.py` (helpers first, main flow in Task 3)
- Test: `backend/tests/test_archive_cluster_offline.py`

- [ ] **Step 1: Write the failing tests** — pure logic only (no disk/DB/network):

```python
"""Tests for the archive-topics offline builder (pure helpers)."""
from datetime import date

from scripts.archive_cluster_offline import (
    iter_windows, group_scopes, checkpoint_load, checkpoint_done, checkpoint_mark,
    sha1_of_headline, build_topic_row,
)


def test_iter_windows_walks_backward_in_weeks():
    ws = list(iter_windows(date(2026, 5, 3), date(2026, 5, 24)))
    # newest first, 7-day windows, inclusive bounds, no gap/overlap
    assert ws[0] == (date(2026, 5, 18), date(2026, 5, 24))
    assert ws[-1][0] == date(2026, 5, 3)
    for (s1, e1), (s0, e0) in zip(ws, ws[1:]):
        assert (s1 - e0).days == 1  # contiguous
    assert all(s >= date(2026, 5, 3) for s, _ in ws)


def test_group_scopes_by_country_with_global_fallback():
    rows = [
        {"sha1": "a", "cc": "CO"}, {"sha1": "b", "cc": "CO"},
        {"sha1": "c", "cc": None}, {"sha1": "d", "cc": ""},
    ]
    scopes = group_scopes(rows)
    assert [r["sha1"] for r in scopes["CO"]] == ["a", "b"]
    assert [r["sha1"] for r in scopes["__global__"]] == ["c", "d"]


def test_checkpoint_roundtrip(tmp_path):
    p = tmp_path / "build-test.json"
    ck = checkpoint_load(p)
    assert not checkpoint_done(ck, date(2026, 6, 1), date(2026, 6, 7))
    checkpoint_mark(ck, p, date(2026, 6, 1), date(2026, 6, 7))
    ck2 = checkpoint_load(p)
    assert checkpoint_done(ck2, date(2026, 6, 1), date(2026, 6, 7))
    assert not checkpoint_done(ck2, date(2026, 6, 8), date(2026, 6, 14))


def test_sha1_matches_embed_pipeline_norm():
    # must reproduce archive_embed_pipeline._norm exactly (unescape+ws+lower)
    assert (sha1_of_headline("Peru&#x2019;s  Vote \n Count")
            == sha1_of_headline("peru’s vote count"))


def test_build_topic_row_shapes_the_upsert():
    import numpy as np
    members = [
        {"sha1": "a", "headline": "x", "cc": "CO", "date": "2026-06-02"},
        {"sha1": "b", "headline": "y", "cc": "CO", "date": "2026-06-03"},
    ]
    centroid = np.ones(4, dtype=np.float32)
    row = build_topic_row(
        label="Test topic", category="election-legitimacy", crisis=True,
        scope="CO", members=members, centroid=centroid, build_id="b1",
    )
    assert row["country_code"] == "CO" and row["n_stories"] == 2
    assert row["period_start"] == date(2026, 6, 2)
    assert row["period_end"] == date(2026, 6, 3)
    assert row["sample_story_ids"] == ["a", "b"]
    assert len(row["centroid_vec"]) == 4 and row["build_id"] == "b1"


def test_build_topic_row_global_scope_maps_to_null_country():
    import numpy as np
    members = [{"sha1": "a", "headline": "x", "cc": None, "date": "2026-06-02"}]
    row = build_topic_row(
        label="G", category=None, crisis=None, scope="__global__",
        members=members, centroid=np.zeros(3, dtype=np.float32), build_id="b1",
    )
    assert row["country_code"] is None
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_archive_cluster_offline.py -q`
Expected: FAIL — `ModuleNotFoundError`/`ImportError` (module doesn't exist yet). NOTE: pure tests run in the repo `.venv` (no torch needed).

- [ ] **Step 3: Implement the helpers** — create `backend/scripts/archive_cluster_offline.py`:

```python
"""Archive Intelligence Tier builder (spec 2026-07-10).

Clusters the ALREADY-EMBEDDED history (OpenAI shards on the external disk)
into archive topics, window by window, and writes ONLY light rows to Supabase
(archive_topics + daily aggregates + evidence samples). Per-story assignments
go to parquet on the external disk. Resumable via a checkpoint file.

Heavy data NEVER leaves the disk — see the spec's golden rule and the
2026-07-08 DB-capacity incident (docs/state/2026-07-08-embedding-throughput-fix.md).

Usage (M1, mlvenv, nightly/mindful):
    python -m scripts.archive_cluster_offline \
        [--from 2026-05-03] [--to 2026-07-03] [--build-id archive-v1] \
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
from datetime import date, timedelta
from pathlib import Path

MODEL_VERSION = "archive-topics-v1"
GLOBAL_SCOPE = "__global__"


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


def checkpoint_load(path: Path) -> dict:
    if Path(path).exists():
        return json.loads(Path(path).read_text())
    return {"done_windows": []}


def _wkey(s: date, e: date) -> str:
    return f"{s.isoformat()}..{e.isoformat()}"


def checkpoint_done(ck: dict, s: date, e: date) -> bool:
    return _wkey(s, e) in ck.get("done_windows", [])


def checkpoint_mark(ck: dict, path: Path, s: date, e: date) -> None:
    ck.setdefault("done_windows", []).append(_wkey(s, e))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(ck, indent=1))
    tmp.replace(path)


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
```

- [ ] **Step 4: Run tests to verify pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_archive_cluster_offline.py -q`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/archive_cluster_offline.py backend/tests/test_archive_cluster_offline.py
git commit -m "feat(archive): offline builder pure helpers — windows, scopes, checkpoint, sha1 parity (TDD)"
```

---

### Task 3: Builder main flow (shards → clusters → DeepSeek → Supabase + parquet)

**Files:**
- Modify: `backend/scripts/archive_cluster_offline.py` (append below the helpers)

No new unit tests (IO/network flow); verified live in Task 5. Keep every DB conn on `SET statement_timeout = 0`.

- [ ] **Step 1: Append the shard/partition loaders**

```python
# ── disk IO ──────────────────────────────────────────────────────────────────

def load_window_vectors(shards_root: Path, win_start: date, win_end: date,
                        junk_re=re.compile(
                            r"^(digit:|in words:|story\d|doc \S+\.shtml)|^\W*$", re.I)):
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
                r = json.loads(line)
                d = r.get("date") or ""
                if not (lo <= d <= hi):
                    continue
                h = html.unescape(r.get("headline") or "")
                if len(h) < 20 or junk_re.search(h):
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
    """sha1 -> {url, source, family, klass, ts, sentiment} from the day partitions.

    One gzip scan per day in the window; ~160K rows/day, seconds each on the M1.
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
                        if k not in out:
                            out[k] = {
                                "url": r.get("source_url"),
                                "source": r.get("source_name"),
                                "family": r.get("source_family") or "press",
                                "klass": r.get("signal_class") or "news",
                                "ts": r.get("timestamp"),
                                "sentiment": r.get("nlp_sentiment") or r.get("sentiment"),
                                "path": rel,
                            }
                    # count duplicates for n_signals later
            except OSError as e:
                print(f"  WARN: unreadable partition {part}: {e}", file=sys.stderr)
        d += timedelta(days=1)
    return out
```

- [ ] **Step 2: Append clustering + DeepSeek typing**

```python
# ── clustering + typing ──────────────────────────────────────────────────────

def cluster_scope(vecs, min_cluster_size: int = 4):
    """HDBSCAN leaf over L2-normalized vecs (euclidean ≡ cosine order)."""
    import hdbscan
    cl = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, min_samples=2,
                         metric="euclidean", cluster_selection_method="leaf")
    return cl.fit_predict(vecs)


_DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"


def _deepseek(messages: list[dict], api_key: str) -> str | None:
    import urllib.request
    body = json.dumps({"model": "deepseek-chat", "messages": messages,
                       "temperature": 0, "max_tokens": 120}).encode()
    req = urllib.request.Request(
        _DEEPSEEK_URL, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read())["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001 — retry then honest None
            time.sleep(2 * (attempt + 1))
            last = e
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
```

- [ ] **Step 3: Append the Supabase writers + parquet writer + main**

```python
# ── writers ──────────────────────────────────────────────────────────────────

async def upsert_window(conn, topic_rows: list[dict], daily_rows: list[dict],
                        evidence_rows: list[dict], build_id: str,
                        win_start: date, win_end: date) -> None:
    """Idempotent per window: delete this build's rows for the window, insert."""
    async with conn.transaction():
        await conn.execute("SET LOCAL statement_timeout = 0")
        await conn.execute(
            "DELETE FROM archive_topics WHERE build_id=$1 "
            "AND period_start >= $2 AND period_end <= $3",
            build_id, win_start, win_end)
        await conn.execute(
            "DELETE FROM historical_topic_country_daily WHERE model_version=$1 "
            "AND day BETWEEN $2 AND $3", MODEL_VERSION, win_start, win_end)
        await conn.execute(
            "DELETE FROM historical_evidence_samples WHERE model_version=$1 "
            "AND day BETWEEN $2 AND $3", MODEL_VERSION, win_start, win_end)
        ids = []
        for t in topic_rows:
            tid = await conn.fetchval(
                """INSERT INTO archive_topics
                   (label, category, crisis_relevant, country_code, period_start,
                    period_end, n_stories, n_signals, centroid_vec, top_sources,
                    sample_story_ids, build_id)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12) RETURNING id""",
                t["label"], t["category"], t["crisis_relevant"], t["country_code"],
                t["period_start"], t["period_end"], t["n_stories"], t.get("n_signals"),
                t["centroid_vec"], json.dumps(t.get("top_sources") or {}),
                t["sample_story_ids"], build_id)
            ids.append(tid)
        for d in daily_rows:
            await conn.execute(
                """INSERT INTO historical_topic_country_daily
                   (day, topic_slug, country_code, source_family, signal_class,
                    signal_count, avg_sentiment, model_version)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
                   ON CONFLICT (day, topic_slug, country_code, source_family,
                                signal_class, model_version)
                   DO UPDATE SET signal_count=EXCLUDED.signal_count,
                                 avg_sentiment=EXCLUDED.avg_sentiment,
                                 updated_at=NOW()""",
                d["day"], d["topic_slug"], d["country_code"], d["family"],
                d["klass"], d["count"], d.get("avg_sentiment"), MODEL_VERSION)
        for e in evidence_rows:
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
                e["headline"], e["ts"], e.get("sentiment"),
                "archive-topic-member", MODEL_VERSION)
    print(f"  upserted {len(topic_rows)} topics for {win_start}..{win_end}",
          file=sys.stderr)


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


# ── main ─────────────────────────────────────────────────────────────────────

async def process_window(conn, args, categories, win_start, win_end) -> None:
    import numpy as np
    t0 = time.monotonic()
    rows, vecs = load_window_vectors(Path(args.shards_root), win_start, win_end)
    print(f"[{win_start}..{win_end}] {len(rows)} embedded stories", file=sys.stderr)
    if not rows:
        return
    lookup = load_evidence_lookup(Path(args.archive_root), win_start, win_end)
    scopes = group_scopes(rows)
    idx_of = {id(r): i for i, r in enumerate(rows)}
    topic_rows, all_assignments, daily_rows, evidence_rows = [], [], [], []
    for scope, srows in sorted(scopes.items(), key=lambda kv: -len(kv[1])):
        if len(srows) < 4:
            continue
        if len(srows) > args.max_scope:
            print(f"  WARN scope {scope}: {len(srows)} > cap {args.max_scope}; "
                  f"clustering the newest {args.max_scope} (dropped logged, not silent)",
                  file=sys.stderr)
            srows = sorted(srows, key=lambda r: r["date"], reverse=True)[:args.max_scope]
        sv = np.vstack([vecs[idx_of[id(r)]] for r in srows])
        labels = cluster_scope(sv)
        for cid in sorted(set(labels) - {-1}):
            mask = labels == cid
            members = [r for r, m in zip(srows, mask) if m]
            centroid = sv[mask].mean(axis=0)
            centroid /= (np.linalg.norm(centroid) + 1e-9)
            label, cat, crisis = label_and_type_topic(
                [m["headline"] for m in members], categories, args.deepseek_key)
            trow = build_topic_row(label=label, category=cat, crisis=crisis,
                                   scope=scope, members=members,
                                   centroid=centroid, build_id=args.build_id)
            # source mix from the evidence lookup (light JSONB)
            fams: dict = defaultdict(int)
            for m in members:
                fams[(lookup.get(m["sha1"]) or {}).get("family", "press")] += 1
            trow["top_sources"] = dict(fams)
            trow["_members"] = members
            trow["_sims"] = (sv[mask] @ centroid).tolist()
            topic_rows.append(trow)
    if args.dry_run:
        print(f"  DRY RUN: {len(topic_rows)} topics; skipping writes", file=sys.stderr)
        return
    # single insert pass gives us topic ids, then aggregates/evidence/parquet
    async with conn.transaction():
        await conn.execute("SET LOCAL statement_timeout = 0")
        await conn.execute(
            "DELETE FROM archive_topics WHERE build_id=$1 "
            "AND period_start >= $2 AND period_end <= $3",
            args.build_id, win_start, win_end)
    for t in topic_rows:
        members, sims = t.pop("_members"), t.pop("_sims")
        tid = await conn.fetchval(
            """INSERT INTO archive_topics
               (label, category, crisis_relevant, country_code, period_start,
                period_end, n_stories, centroid_vec, top_sources,
                sample_story_ids, build_id)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11) RETURNING id""",
            t["label"], t["category"], t["crisis_relevant"], t["country_code"],
            t["period_start"], t["period_end"], t["n_stories"], t["centroid_vec"],
            json.dumps(t["top_sources"]), t["sample_story_ids"], args.build_id)
        slug = f"archive-topic-{tid}"
        per_day: dict = defaultdict(lambda: defaultdict(int))
        for m, s in zip(members, sims):
            info = lookup.get(m["sha1"]) or {}
            cc = t["country_code"] or (m.get("cc") or "GLOBAL")
            per_day[(m["date"], cc, info.get("family", "press"),
                     info.get("klass", "news"))]["n"] += 1
            all_assignments.append({"sha1": m["sha1"], "topic_id": tid,
                                    "sim": float(s), "cc": m.get("cc"),
                                    "day": date.fromisoformat(m["date"])})
        for (d, cc, fam, kl), agg in per_day.items():
            daily_rows.append({"day": date.fromisoformat(d), "topic_slug": slug,
                               "country_code": cc, "family": fam, "klass": kl,
                               "count": agg["n"], "avg_sentiment": None})
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
    print(f"  window done in {time.monotonic()-t0:.0f}s: {len(topic_rows)} topics, "
          f"{len(all_assignments)} assignments", file=sys.stderr)


async def upsert_window_aggregates(conn, daily_rows, evidence_rows) -> None:
    from datetime import datetime
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
            ts = e["ts"]
            if isinstance(ts, str):
                try:
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                except ValueError:
                    ts = None
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
                e["headline"], ts, e.get("sentiment"),
                "archive-topic-member", MODEL_VERSION)


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
```

- [ ] **Step 4: Remove the now-dead `upsert_window` helper** (the flow inlines the topic insert to get ids; keep only `upsert_window_aggregates`). Verify no references: `grep -n "upsert_window(" backend/scripts/archive_cluster_offline.py` → only `upsert_window_aggregates`.

- [ ] **Step 5: Install duckdb into mlvenv + syntax check**

Run: `~/AtlasLocalWorker/mlvenv/bin/pip install duckdb && cd backend && .venv/bin/python -m pytest tests/test_archive_cluster_offline.py -q && .venv/bin/python -c "import ast; ast.parse(open('scripts/archive_cluster_offline.py').read()); print('parse OK')"`
Expected: 6 passed + parse OK.

- [ ] **Step 6: Commit**

```bash
git add backend/scripts/archive_cluster_offline.py
git commit -m "feat(archive): builder main flow — shard window load, scoped HDBSCAN, DeepSeek typing, light upserts, parquet assignments"
```

---

### Task 4: Sync to ALW + dry-run one window

- [ ] **Step 1: Sync the script to the executed tree**

```bash
mkdir -p ~/AtlasLocalWorker/backend/scripts
cp backend/scripts/archive_cluster_offline.py ~/AtlasLocalWorker/backend/scripts/
```

- [ ] **Step 2: Dry-run the newest archive week** (no writes, proves shard IO + clustering):

```bash
cd ~/AtlasLocalWorker/backend
set -a; DATABASE_URL="$(grep -E '^DATABASE_URL=' ../.env | head -1 | cut -d= -f2-)"; set +a
DATABASE_URL="$DATABASE_URL" ../mlvenv/bin/python -m scripts.archive_cluster_offline \
  --to 2026-06-07 --windows 1 --dry-run
```
Expected: `[2026-06-01..2026-06-07] N embedded stories` with N in the ~500K-1M range, then `DRY RUN: M topics` with M ≥ 50, no traceback. If N==0, the date filter or shard root is wrong — stop and diagnose.

---

### Task 5: Live build of the validation window + acceptance checks

- [ ] **Step 1: Live run (first June week)**

```bash
cd ~/AtlasLocalWorker/backend
set -a; source ../.env 2>/dev/null; set +a   # DATABASE_URL + DEEPSEEK_API_KEY
../mlvenv/bin/python -m scripts.archive_cluster_offline --to 2026-06-07 --windows 1
```
Expected: `upserted`-style lines, `parquet: .../month=2026-06/part-2026-06-01.parquet`, `run complete: 1 windows processed`, exit 0.

- [ ] **Step 2: Acceptance SQL** (any client):

```sql
SELECT count(*) topics, count(DISTINCT country_code) countries,
       count(*) FILTER (WHERE category IS NOT NULL) typed
FROM archive_topics WHERE build_id='archive-v1';
SELECT label, category, country_code, n_stories FROM archive_topics
WHERE build_id='archive-v1' ORDER BY n_stories DESC LIMIT 10;
SELECT count(*) FROM historical_topic_country_daily WHERE model_version='archive-topics-v1';
SELECT count(*) FROM historical_evidence_samples WHERE model_version='archive-topics-v1';
SELECT pg_size_pretty(pg_total_relation_size('archive_topics'));
```
Expected: topics > 50; top labels read as real stories; daily + evidence counts > 0; table size ≤ tens of MB.

- [ ] **Step 3: Idempotency check** — re-run Step 1 with the checkpoint file DELETED for that window (edit `checkpoints/build-archive-v1.json`, remove the window key). Topic count for the window must stay ~equal (delete-and-replace, no duplication):

```sql
SELECT count(*) FROM archive_topics WHERE build_id='archive-v1';
```

- [ ] **Step 4: Commit any fixes + note**

```bash
git add -A backend/scripts/archive_cluster_offline.py
git commit -m "fix(archive): builder adjustments from first live window"
```

---

### Task 6: `GET /api/v2/archive/search` endpoint (TDD on the pure ranking)

**Files:**
- Create: `backend/app/routers/archive_search.py`
- Modify: `backend/app/main_v2.py` (register router — follow the existing `app.include_router(...)` block)
- Test: `backend/tests/test_archive_search.py`

- [ ] **Step 1: Write the failing tests** (pure cosine ranking + response shaping):

```python
from app.routers.archive_search import rank_topics


def _t(id_, vec, **kw):
    base = {"id": id_, "label": f"t{id_}", "category": None,
            "crisis_relevant": None, "country_code": "CO",
            "period_start": "2026-06-01", "period_end": "2026-06-07",
            "n_stories": 5, "centroid_vec": vec, "top_sources": {}}
    base.update(kw)
    return base


def test_rank_topics_orders_by_cosine_and_applies_floor():
    q = [1.0, 0.0]
    rows = [_t(1, [1.0, 0.0]), _t(2, [0.7071, 0.7071]), _t(3, [0.0, 1.0])]
    out = rank_topics(q, rows, floor=0.5, limit=10)
    assert [r["id"] for r in out] == [1, 2]
    assert out[0]["similarity"] > out[1]["similarity"] >= 0.5


def test_rank_topics_respects_limit():
    q = [1.0, 0.0]
    rows = [_t(i, [1.0, 0.0]) for i in range(20)]
    assert len(rank_topics(q, rows, floor=0.0, limit=5)) == 5


def test_rank_topics_empty_is_honest():
    assert rank_topics([1.0, 0.0], [], floor=0.3, limit=10) == []
```

- [ ] **Step 2: Run to verify failure**

Run: `cd backend && .venv/bin/python -m pytest tests/test_archive_search.py -q`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement the router**

```python
"""Archive search — the Archive Intelligence Tier serving path (spec 2026-07-10).

Query → OpenAI text-embedding-3-small (query-side only, ~$0.00002) → cosine
scan over the few-thousand archive_topics centroids (REAL[], NO vector index
by design) → topics + daily series + evidence samples, tier-labeled 'archive'.
"""
from __future__ import annotations

import math
import os
from datetime import date

import httpx
from fastapi import APIRouter, HTTPException, Query

from ..db import get_pool  # follow the actual helper used by sibling routers

router = APIRouter(prefix="/api/v2/archive", tags=["archive"])

CONTRACT = "archive-search-v0"
_OPENAI_URL = "https://api.openai.com/v1/embeddings"
_MODEL = "text-embedding-3-small"
_FLOOR = 0.30  # topic-centroid floor; calibrated vs 2026-07-05 tau artifact


def rank_topics(qvec: list[float], rows: list[dict], *, floor: float,
                limit: int) -> list[dict]:
    """Pure cosine ranking of archive topic rows against a query vector."""
    qn = math.sqrt(sum(x * x for x in qvec)) or 1.0
    out = []
    for r in rows:
        v = r["centroid_vec"]
        vn = math.sqrt(sum(x * x for x in v)) or 1.0
        sim = sum(a * b for a, b in zip(qvec, v)) / (qn * vn)
        if sim >= floor:
            out.append({**r, "similarity": round(sim, 4)})
    out.sort(key=lambda r: -r["similarity"])
    return out[:limit]


async def _embed_query(q: str) -> list[float] | None:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    async with httpx.AsyncClient(timeout=8.0) as cli:
        resp = await cli.post(_OPENAI_URL, json={"model": _MODEL, "input": [q[:2000]]},
                              headers={"Authorization": f"Bearer {key}"})
        resp.raise_for_status()
        return resp.json()["data"][0]["embedding"]


@router.get("/search")
async def archive_search(
    q: str = Query(..., min_length=2, max_length=300),
    country: str | None = Query(None, min_length=2, max_length=2),
    date_from: date | None = Query(None, alias="from"),
    date_to: date | None = Query(None, alias="to"),
    limit: int = Query(10, ge=1, le=25),
):
    try:
        qvec = await _embed_query(q)
    except httpx.HTTPError:
        qvec = None
    if qvec is None:
        return {"contract": CONTRACT, "tier": "archive", "query": q,
                "topics": [], "gap": "archive semantic search unavailable "
                "(query embedding lane down)"}
    pool = await get_pool()
    async with pool.acquire() as conn:
        sql = ["SELECT id, label, category, crisis_relevant, country_code,",
               "period_start, period_end, n_stories, centroid_vec, top_sources",
               "FROM archive_topics WHERE 1=1"]
        params: list = []
        if country:
            params.append(country.upper())
            sql.append(f"AND country_code = ${len(params)}")
        if date_from:
            params.append(date_from)
            sql.append(f"AND period_end >= ${len(params)}")
        if date_to:
            params.append(date_to)
            sql.append(f"AND period_start <= ${len(params)}")
        rows = [dict(r) for r in await conn.fetch(" ".join(sql), *params)]
        if not rows:
            return {"contract": CONTRACT, "tier": "archive", "query": q,
                    "topics": [], "gap": "archive has no topics for that scope "
                    "(coverage starts 2026-05-03)"}
        ranked = rank_topics(qvec, rows, floor=_FLOOR, limit=limit)
        out = []
        for t in ranked:
            slug = f"archive-topic-{t['id']}"
            series = await conn.fetch(
                "SELECT day, SUM(signal_count) n FROM historical_topic_country_daily "
                "WHERE topic_slug=$1 AND model_version='archive-topics-v1' "
                "GROUP BY day ORDER BY day", slug)
            evid = await conn.fetch(
                "SELECT day, headline, source_name, source_url FROM "
                "historical_evidence_samples WHERE topic_slug=$1 "
                "AND model_version='archive-topics-v1' ORDER BY day LIMIT 5", slug)
            t.pop("centroid_vec", None)
            out.append({**t, "topic_slug": slug,
                        "daily": [{"day": r["day"].isoformat(), "n": int(r["n"])}
                                  for r in series],
                        "evidence": [dict(r) | {"day": r["day"].isoformat()}
                                     for r in evid]})
        return {"contract": CONTRACT, "tier": "archive", "query": q,
                "topics": out,
                "gap": None if out else "no archive topic clears the "
                f"similarity floor ({_FLOOR}) for that query"}
```

NOTE for implementer: check how sibling routers acquire the pool (e.g. `app/routers/universe.py` or `dossier.py`) and mirror EXACTLY — if they use `from ..main_v2 import pool`-style access or a `Depends`, copy that pattern instead of `get_pool`.

- [ ] **Step 4: Register the router in `app/main_v2.py`** — find the `include_router` block (grep `include_router`) and add, mirroring neighbors:

```python
from .routers import archive_search
app.include_router(archive_search.router)
```

- [ ] **Step 5: Run tests**

Run: `cd backend && .venv/bin/python -m pytest tests/test_archive_search.py -q`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/archive_search.py backend/app/main_v2.py backend/tests/test_archive_search.py
git commit -m "feat(archive): GET /api/v2/archive/search — OpenAI query embed vs centroid scan (archive-search-v0)"
```

---

### Task 7: Deploy + prod smoke

- [ ] **Step 1: Ensure `OPENAI_API_KEY` is set on Fly**

Run: `fly secrets list -a atlas-api-pedro | grep -i openai`
If missing: `fly secrets set OPENAI_API_KEY=<key from ~/AtlasLocalWorker/.env> -a atlas-api-pedro` (this restarts machines — fine off-peak).

- [ ] **Step 2: Deploy**

Run: `./scripts/deploy-fly-api.sh`
Expected: deploy green, health checks pass.

- [ ] **Step 3: Prod smoke**

```bash
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/archive/search?q=peru%20election%20recount&from=2026-06-01&to=2026-06-07' | python3 -m json.tool | head -40
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/archive/search?q=colombia%20espriella%20election' | python3 -m json.tool | head -40
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/archive/search?q=zzz&from=2020-01-01&to=2020-01-02' | python3 -m json.tool
```
Expected: first two return topics with `daily` series + `evidence` URLs and `tier:"archive"`; third returns the honest empty `gap`. Also re-smoke the hot paths: `curl -s .../api/v2/threads?hours=24 | head -c 300` unchanged.

- [ ] **Step 4: Commit + push**

```bash
git push
```

---

### Task 8: Full backfill kickoff + docs

- [ ] **Step 1: Launch the full backfill on the M1** (nohup, mindful, resumable — walks newest→oldest; safe to interrupt any time):

```bash
cd ~/AtlasLocalWorker/backend
set -a; source ../.env; set +a
nohup taskpolicy -b ../mlvenv/bin/python -m scripts.archive_cluster_offline \
  --to 2026-07-03 > ../logs/archive-topics-backfill.log 2>&1 &
```
(`--to` = the hot boundary ≈ today−7d at run time; adjust.)

- [ ] **Step 2: Write the state doc** `docs/state/2026-07-10-archive-tier-build.md` with: windows processed, topics/table size, prod smoke results, backfill ETA, and the standing DB-discipline rules from the spec §5.

- [ ] **Step 3: Update CLAUDE.md** — add a short dated block pointing at the spec + state doc (follow the existing dated-block convention, keep it ≤15 lines).

- [ ] **Step 4: Final commit**

```bash
git add docs/state/2026-07-10-archive-tier-build.md CLAUDE.md
git commit -m "docs(archive): tier build state + registry pointer"
git push
```

---

## Self-review notes (done at plan-write time)

- Spec coverage: §3.1→Task 1, §3.2 parquet→Task 3 (write_parquet), §3.3 builder→Tasks 2-5+8, §3.4 endpoint→Tasks 6-7, §6 acceptance→Tasks 5+7, §5 discipline→encoded in migration comment + doc task.
- Umbrella folding + frontend surface: explicitly deferred by spec §7 — no tasks, correct.
- Type consistency: `build_topic_row` returns `period_start/period_end` as `date` objects; asyncpg accepts `date` for DATE columns. `sample_story_ids` TEXT[] ← list[str]. `centroid_vec` REAL[] ← list[float]. `top_sources` JSONB ← json.dumps.
- Known judgment calls the implementer may tune on live data: HDBSCAN `min_cluster_size=4`, similarity `_FLOOR=0.30` (re-measure vs the 2026-07-05 tau artifact after the first window), `--max-scope 60000` cap (logged, never silent).
