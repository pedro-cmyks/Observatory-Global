#!/usr/bin/env python3
"""Z4 unassigned census — READ-ONLY measurement (plan-identidad Z4, 2026-08-18).

Measures, over the last 7 full UTC days, what fraction of the SERVABLE corpus
never becomes a story (no dynamic-topic membership), per day and per country;
attributes the unassigned mass to clustering-recall vs assignment-lane using
the engine's own taus; and re-measures the three 2026-08-14 witness cases
(espriella / golán / ungrd) with the same member filter the query protocol
uses (topic_members role='evidence', engine_version, quarantined IS NOT TRUE).

Design constraints honored:
  * READ ONLY: every transaction runs SET TRANSACTION READ ONLY.
  * Pooler discipline: statement_cache_size=0; SET LOCAL statement_timeout
    inside each transaction (pooler kills at 2 min; we stay under 110s).
  * No unbounded full scans in one statement: signals_v2 is walked in
    adaptive id-range chunks behind a MATERIALIZED fence (the timestamp
    index plan measured 60s+ per probe on 2026-08-18; the pkey walk is the
    only plan that stays under the pooler ceiling). Resumable: partial chunk
    state is persisted after every chunk.
  * Joins happen CLIENT-SIDE: topic_members (~300k rows) and the political
    slice of signal_topic_assignments (~132k rows total) are small; shipping
    id lists once beats 1.2M correlated EXISTS probes on a slow heap.

Populations (declared; ingest_basis discipline):
  P0 total      = signals_v2 rows with timestamp in [day, day+1) UTC.
  P1 servable   = P0 AND headline IS NOT NULL AND NOT junk (the engine's own
                  is_junk_headline translated to SQL: .shtml/doc/untitled,
                  digit-spelling bot template, >=3 whitespace-separated
                  tokens containing a letter) AND source_family <> 'social'
                  (the F2 guard: social never seeds clusters).
  P2 política   = P1 AND EXISTS signal_topic_assignments row (any method,
                  any gate status) to one of the POLITICAL_SLUGS atlas
                  categories declared below. gate_kept subset also reported.

Assignment (the serving definition, parity with the 2026-08-14 protocol):
  assigned_any   = EXISTS topic_members WHERE role='evidence'
                   AND engine_version=<serving> AND quarantined IS NOT TRUE.
  assigned_story = same, restricted to topic_id LIKE 'dynamic-topic-%'
                   ("se vuelve historia"; atlas category membership alone
                   does not count as a story).

Attribution taus (the engine's own, declared, not invented):
  0.82 = DEFAULT_ASSIGN_THRESHOLD (build_unified_topics.py:62) — the only
         signal->topic-centroid assign tau the engine defines.
  0.88 = MATCH_THRESHOLD (project_dynamic_topics.py:42) — cluster-centroid
         -> identity match tau; used here as the strict band.
  Buckets over max cosine(signal e5 vec, active story centroid):
    >= 0.88            assignment-lane class (a story the engine itself
                       would call the same identity already exists)
    [0.82, 0.88)       assignable band (above the signal-level assign tau)
    <  0.82            clustering-recall class (no active story within any
                       engine tau; a new story would have had to form)
    no embedding       embed-lane starvation (neither lane ever saw it)

Usage (from backend/, .venv):
  .venv/bin/python scripts/z4_unassigned_census.py \
      --out ../docs/research/recall-229/2026-08-18-z4-unassigned-census.json
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

import asyncpg
import numpy as np

ENV_PATH = "/Users/pedro/AtlasLocalWorker/.env"
STATEMENT_TIMEOUT = "110s"          # pooler ceiling is 2 min; stay under
SEED = 229                          # sampling seed (recall-229 program)

# ---- the engine's own taus (declared sources, do not edit blindly) ----
TAU_ASSIGN = 0.82   # build_unified_topics.py:62 DEFAULT_ASSIGN_THRESHOLD
TAU_MATCH = 0.88    # scripts/project_dynamic_topics.py:42 MATCH_THRESHOLD

# is_junk_headline (app/services/research_semantic.py:367-389) in SQL form.
JUNK_RE_1 = r"\.s?html?\y|^doc\s|^untitled\y"                 # ~* (ci)
JUNK_RE_2 = r"^\s*digit:\s*[0-9,.]+"                          # ~* (ci)
JUNK_RE_3 = (r"\yin words:\s*(zero|one|two|three|four|five|six|seven|eight"
             r"|nine|ten|eleven|twelve|(thir|four|fif|six|seven|eigh|nine)teen"
             r"|(twen|thir|for|fif|six|seven|eigh|nine)ty"
             r"|hundred|thousand|million|billion)\y")          # ~* (ci)
# ">= 3 whitespace-separated tokens each containing a letter" as one regex.
THREE_WORD_RE = (r"[^[:space:]]*[[:alpha:]][^[:space:]]*([[:space:]]+[^[:space:]]+)*"
                 r"[[:space:]]+[^[:space:]]*[[:alpha:]][^[:space:]]*([[:space:]]+[^[:space:]]+)*"
                 r"[[:space:]]+[^[:space:]]*[[:alpha:]][^[:space:]]*")

SERVABLE_SQL = (
    "(headline IS NOT NULL"
    " AND headline !~* $JUNK1$" + JUNK_RE_1 + "$JUNK1$"
    " AND headline !~* $JUNK2$" + JUNK_RE_2 + "$JUNK2$"
    " AND headline !~* $JUNK3$" + JUNK_RE_3 + "$JUNK3$"
    " AND headline ~ $TW$" + THREE_WORD_RE + "$TW$"
    " AND COALESCE(source_family,'') <> 'social')"
)

# Política := assignment to one of these atlas categories (engine's own
# category-relevance measurement; lexical + semantic lanes, gate splits
# reported separately). Declared, not exhaustive of "politics" in the world.
POLITICAL_SLUGS = [
    "armed-attacks-security-incidents", "armed-conflict-escalation",
    "bangladesh-domestic-affairs", "constitutional-institutional-crisis",
    "corruption-investigation", "disinformation-influence-operation",
    "election-administration-voting", "election-legitimacy-dispute",
    "elections-and-political-campaigns", "elections-and-voting",
    "elections-political-campaigns", "forced-displacement",
    "fuel-subsidy-unrest", "german-domestic-politics", "greek-politics",
    "humanitarian-access-conflict", "india-diplomacy",
    "international-diplomacy", "labor-strike-disruption",
    "migration-border-pressure", "press-freedom-crackdown",
    "romanian-politics-and-governance", "sanctions-diplomatic-pressure",
    "student-youth-protest", "telecom-internet-shutdown", "turkish-politics",
    "us-redistricting-and-voting-rights", "vietnam-politics-governance",
]

# Witnesses of 2026-08-14 (query_verbs.like_needle parity: lowercased,
# accents PRESERVED, LIKE over lower(headline) — the trgm-indexed predicate).
WITNESS_NEEDLES = {"espriella": "%espriella%", "golán": "%golán%",
                   "ungrd": "%ungrd%"}
# ruta C committed 2026-08-14T09:46-05:00 = 14:46Z; frozen window approximates
# the 24h the investigation looked at (rounded to 15:00Z).
FROZEN_WINDOW = ("2026-08-13T15:00:00+00:00", "2026-08-14T15:00:00+00:00")


def load_db_url() -> str:
    with open(ENV_PATH) as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                return line.strip().split("=", 1)[1]
    raise SystemExit("DATABASE_URL not found in " + ENV_PATH)


class Census:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.state_path = args.out + ".state.json"
        self.state: dict = {}
        if args.resume and os.path.exists(self.state_path):
            with open(self.state_path) as f:
                self.state = json.load(f)
            print(f"[resume] loaded state: chunks done up to id "
                  f"{self.state.get('last_id')}")
        self.conn: asyncpg.Connection | None = None
        self.rng = random.Random(SEED)

    # ---------- infra ----------
    async def connect(self) -> None:
        if self.conn is not None and not self.conn.is_closed():
            return
        self.conn = await asyncpg.connect(load_db_url(), statement_cache_size=0,
                                          timeout=30)

    async def q(self, sql: str, *params, timeout: str = STATEMENT_TIMEOUT):
        """One read-only transaction per statement, SET LOCAL timeout."""
        for attempt in (1, 2, 3):
            try:
                await self.connect()
                async with self.conn.transaction():
                    await self.conn.execute(
                        f"SET LOCAL statement_timeout = '{timeout}'")
                    await self.conn.execute("SET TRANSACTION READ ONLY")
                    return await self.conn.fetch(sql, *params)
            except asyncpg.QueryCanceledError:
                raise
            except (asyncpg.PostgresConnectionError, OSError,
                    asyncio.TimeoutError) as e:
                print(f"  [conn retry {attempt}] {type(e).__name__}: {e}")
                try:
                    if self.conn:
                        await self.conn.close()
                except Exception:
                    pass
                self.conn = None
                await asyncio.sleep(5 * attempt)
        raise RuntimeError("connection retries exhausted")

    def save_state(self) -> None:
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.state, f)
        os.replace(tmp, self.state_path)

    # ---------- stage 0: meta ----------
    async def stage_meta(self) -> None:
        if "meta" in self.state:
            return
        r = await self.q("SELECT now() AS now")
        now = r[0]["now"]
        mn_ts = (await self.q(
            "SELECT timestamp FROM signals_v2 ORDER BY timestamp ASC LIMIT 1"
        ))[0]["timestamp"]
        mx_id = (await self.q(
            "SELECT id FROM signals_v2 ORDER BY id DESC LIMIT 1"))[0]["id"]
        mn_id = (await self.q(
            "SELECT id FROM signals_v2 ORDER BY id ASC LIMIT 1"))[0]["id"]
        end_day = now.date()                      # today (exclusive)
        start_day = end_day - dt.timedelta(days=self.args.days)
        # boundary id: first id with created_at >= start_day - 2d slack
        target = dt.datetime.combine(start_day - dt.timedelta(days=2),
                                     dt.time(0), tzinfo=dt.timezone.utc)
        lo, hi = mn_id, mx_id
        while lo < hi:
            mid = (lo + hi) // 2
            rr = await self.q(
                "SELECT created_at FROM signals_v2 WHERE id >= $1 "
                "ORDER BY id LIMIT 1", mid)
            ca = rr[0]["created_at"] if rr else None
            if ca is None or ca >= target:
                hi = mid
            else:
                lo = mid + 1
        pol = await self.q(
            "SELECT id, slug FROM atlas_topics WHERE slug = ANY($1::text[])",
            POLITICAL_SLUGS)
        self.state["meta"] = {
            "measured_at": now.isoformat(),
            "retention_min_timestamp": mn_ts.isoformat(),
            "window_start": start_day.isoformat(),
            "window_end": end_day.isoformat(),
            "id_min": mn_id, "id_max": mx_id, "boundary_id": lo,
            "political_topic_ids": {r["slug"]: r["id"] for r in pol},
            "engine_version": os.environ.get(
                "ATLAS_TOPIC_MEMBERS_ENGINE_VERSION", "v1-compat"),
        }
        self.save_state()
        print(f"[meta] window {start_day}..{end_day} boundary_id={lo} "
              f"max_id={mx_id} span={mx_id-lo}")

    # ---------- stage 1: chunked signals_v2 walk ----------
    async def stage_chunks(self) -> None:
        m = self.state["meta"]
        if self.state.get("chunks_done"):
            return
        last = self.state.get("last_id", m["boundary_id"])
        size = self.state.get("chunk_size", 60_000)
        sig_path = self.args.out + ".sigrows.jsonl"
        if last == m["boundary_id"] and os.path.exists(sig_path):
            os.remove(sig_path)
        ws = dt.datetime.fromisoformat(m["window_start"] + "T00:00:00+00:00")
        we = dt.datetime.fromisoformat(m["window_end"] + "T00:00:00+00:00")
        sql = f"""
        WITH chunk AS MATERIALIZED (
            SELECT id, timestamp, country_code, headline, source_family
            FROM signals_v2
            WHERE id > $1 AND id <= $2
        )
        SELECT id,
               TRIM(COALESCE(country_code,'')) AS cc,
               ((timestamp AT TIME ZONE 'UTC')::date)::text AS day,
               (headline IS NOT NULL) AS has_h,
               {SERVABLE_SQL} AS servable
        FROM chunk
        WHERE timestamp >= $3::timestamptz AND timestamp < $4::timestamptz
        """
        while last < m["id_max"]:
            hi = min(last + size, m["id_max"])
            t0 = time.time()
            try:
                rows = await self.q(sql, last, hi, ws, we)
            except asyncpg.QueryCanceledError:
                size = max(10_000, size // 2)
                self.state["chunk_size"] = size
                print(f"  [chunk] timeout at size {size*2} -> retry {size}")
                continue
            el = time.time() - t0
            with open(sig_path, "a") as f:
                for r in rows:
                    f.write(json.dumps([r["id"], r["cc"], r["day"],
                                        r["has_h"], r["servable"]]) + "\n")
            last = hi
            self.state["last_id"] = last
            self.state["sig_rows_count"] = (
                self.state.get("sig_rows_count", 0) + len(rows))
            if el < 45 and size < 150_000:
                size = int(size * 1.5)
                self.state["chunk_size"] = size
            self.save_state()
            done = last - m["boundary_id"]
            total = m["id_max"] - m["boundary_id"]
            print(f"  [chunk] id<={last} rows+{len(rows)} "
                  f"({el:.0f}s, size {size}) {done*100//total}%", flush=True)
        self.state["chunks_done"] = True
        self.save_state()
        print(f"[chunks] total window rows: "
              f"{self.state.get('sig_rows_count', 0)}")

    # ---------- stage 2: topic_members (client-side join table) ----------
    async def stage_tm(self) -> None:
        if "tm_breakdown" not in self.state:
            rows = await self.q("""
                SELECT engine_version, role,
                       COUNT(*) FILTER (WHERE topic_id LIKE 'dynamic-topic-%')
                           AS dyn, COUNT(*) AS n
                FROM topic_members GROUP BY 1, 2 ORDER BY n DESC""")
            self.state["tm_breakdown"] = [dict(r) for r in rows]
            self.save_state()
        tm_path = self.args.out + ".tmpairs.json"
        if not self.state.get("tm_done"):
            ev = self.state["meta"]["engine_version"]
            rows = await self.q("""
                SELECT signal_id,
                       BOOL_OR(topic_id LIKE 'dynamic-topic-%') AS story
                FROM topic_members
                WHERE role = 'evidence' AND engine_version = $1
                  AND quarantined IS NOT TRUE
                GROUP BY signal_id""", ev)
            with open(tm_path, "w") as f:
                json.dump([[r["signal_id"], r["story"]] for r in rows], f)
            self.state["tm_done"] = True
            self.state["tm_count"] = len(rows)
            self.save_state()
            print(f"[tm] {len(rows)} distinct evidence signal_ids "
                  f"(engine_version={ev})")

    # ---------- stage 3: embedded ids (chunked index walk) ----------
    async def stage_emb(self) -> None:
        if self.state.get("emb_done"):
            return
        m = self.state["meta"]
        emb_path = self.args.out + ".embids.jsonl"
        last = self.state.get("emb_last", m["boundary_id"])
        if last == m["boundary_id"] and os.path.exists(emb_path):
            os.remove(emb_path)
        size = 250_000
        while last < m["id_max"]:
            hi = min(last + size, m["id_max"])
            t0 = time.time()
            rows = await self.q(
                "SELECT signal_id FROM signal_embeddings "
                "WHERE signal_id > $1 AND signal_id <= $2 ORDER BY signal_id",
                last, hi)
            with open(emb_path, "a") as f:
                f.write(json.dumps([r["signal_id"] for r in rows]) + "\n")
            last = hi
            self.state["emb_last"] = last
            self.save_state()
            print(f"  [emb] id<={last} +{len(rows)} ({time.time()-t0:.0f}s)",
                  flush=True)
        self.state["emb_done"] = True
        self.save_state()

    # ---------- stage 4: political assignments ----------
    async def stage_pol(self) -> None:
        if self.state.get("pol_done"):
            return
        ids = list(self.state["meta"]["political_topic_ids"].values())
        rows = await self.q("""
            SELECT signal_id, BOOL_OR(COALESCE(gate_kept, false)) AS gk
            FROM signal_topic_assignments
            WHERE topic_id = ANY($1::bigint[])
            GROUP BY signal_id""", ids)
        with open(self.args.out + ".polpairs.json", "w") as f:
            json.dump([[r["signal_id"], r["gk"]] for r in rows], f)
        self.state["pol_done"] = True
        self.state["pol_count"] = len(rows)
        meth = await self.q("""
            SELECT method, COUNT(*) AS n,
                   COUNT(*) FILTER (WHERE gate_kept) AS kept
            FROM signal_topic_assignments
            WHERE topic_id = ANY($1::bigint[]) GROUP BY 1""", ids)
        self.state["pol_methods"] = [dict(r) for r in meth]
        self.save_state()
        print(f"[pol] {len(rows)} signals with political assignments")

    # ---------- stage 5: witnesses ----------
    async def stage_witness(self) -> None:
        if "witness" in self.state:
            return
        out: dict = {}
        now = dt.datetime.fromisoformat(self.state["meta"]["measured_at"])
        wins = {
            "last24h": (now - dt.timedelta(hours=24), now),
            "frozen_aug13_14": tuple(
                dt.datetime.fromisoformat(x) for x in FROZEN_WINDOW),
        }
        needles = dict(WITNESS_NEEDLES)
        needles["OR_protocol"] = None  # special: OR of the three
        for wname, (w0, w1) in wins.items():
            out[wname] = {}
            for nname, needle in needles.items():
                if needle is None:
                    pred = ("(lower(headline) LIKE '%espriella%' OR "
                            "lower(headline) LIKE '%golán%' OR "
                            "lower(headline) LIKE '%ungrd%')")
                    rows = await self.q(f"""
                        SELECT id, headline,
                               TRIM(COALESCE(country_code,'')) AS cc
                        FROM signals_v2
                        WHERE timestamp >= $1::timestamptz
                          AND timestamp < $2::timestamptz AND {pred}
                        LIMIT 4000""", w0, w1)
                else:
                    rows = await self.q("""
                        SELECT id, headline,
                               TRIM(COALESCE(country_code,'')) AS cc
                        FROM signals_v2
                        WHERE timestamp >= $1::timestamptz
                          AND timestamp < $2::timestamptz
                          AND lower(headline) LIKE $3
                        LIMIT 4000""", w0, w1, needle)
                ids = [r["id"] for r in rows]
                landing = []
                if ids:
                    ev = self.state["meta"]["engine_version"]
                    landing = await self.q("""
                        SELECT tm.topic_id,
                               COUNT(DISTINCT tm.signal_id) AS n,
                               dt.label, dt.state
                        FROM topic_members tm
                        LEFT JOIN dynamic_topics dt ON dt.id = CASE
                            WHEN tm.topic_id ~ '^dynamic-topic-[0-9]+$'
                            THEN substring(tm.topic_id FROM 15)::bigint END
                        WHERE tm.signal_id = ANY($1::bigint[])
                          AND tm.role = 'evidence' AND tm.engine_version = $2
                          AND tm.quarantined IS NOT TRUE
                        GROUP BY 1, 3, 4 ORDER BY n DESC LIMIT 40""", ids, ev)
                out[wname][nname] = {
                    "matched": len(ids),
                    "ids": ids,
                    "sample_headlines": [r["headline"] for r in rows[:6]],
                    "countries": sorted({r["cc"] for r in rows}),
                    "landing": [dict(r) for r in landing],
                }
                print(f"[witness] {wname}/{nname}: matched={len(ids)}")
        self.state["witness"] = out
        self.save_state()

    # ---------- stage 6: centroids ----------
    async def stage_centroids(self) -> None:
        if self.state.get("cent_done"):
            return
        rows = await self.q("""
            SELECT id, state, is_umbrella, label
            FROM dynamic_topics
            WHERE state IN ('active','candidate')
              AND centroid_vec IS NOT NULL
              AND COALESCE(is_junk, false) = false""")
        metas = [dict(r) for r in rows]
        self.state["cent_meta"] = metas
        self.save_state()
        ids = [m["id"] for m in metas]
        vec_path = self.args.out + ".centroids.npy"
        got: dict[int, list] = {}
        for i in range(0, len(ids), 1500):
            batch = ids[i:i + 1500]
            rows = await self.q(
                "SELECT id, centroid_vec FROM dynamic_topics "
                "WHERE id = ANY($1::bigint[])", batch)
            for r in rows:
                got[r["id"]] = r["centroid_vec"]
            print(f"  [centroids] {len(got)}/{len(ids)}")
        mat = np.array([got[i] for i in ids], dtype=np.float32)
        np.save(vec_path, mat)
        self.state["cent_done"] = True
        self.save_state()
        print(f"[centroids] {mat.shape} saved")

    # ---------- stage 7: samples + vec fetch ----------
    def _client_join(self):
        """Build numpy views of the census matrix (cached on self)."""
        if hasattr(self, "_cj"):
            return self._cj
        rows: list = []
        with open(self.args.out + ".sigrows.jsonl") as f:
            for line in f:
                rows.append(json.loads(line))
        n = len(rows)
        ids = np.fromiter((r[0] for r in rows), dtype=np.int64, count=n)
        days = sorted({r[2] for r in rows})
        day_idx = {d: i for i, d in enumerate(days)}
        ccs = sorted({r[1] for r in rows})
        cc_idx = {c: i for i, c in enumerate(ccs)}
        day_a = np.fromiter((day_idx[r[2]] for r in rows), dtype=np.int16,
                            count=n)
        cc_a = np.fromiter((cc_idx[r[1]] for r in rows), dtype=np.int16,
                           count=n)
        has_h = np.fromiter((r[3] for r in rows), dtype=bool, count=n)
        srv = np.fromiter((r[4] for r in rows), dtype=bool, count=n)

        with open(self.args.out + ".tmpairs.json") as f:
            tm = json.load(f)
        tm_ids = np.fromiter((p[0] for p in tm), dtype=np.int64, count=len(tm))
        tm_story = np.fromiter((p[1] for p in tm), dtype=bool, count=len(tm))
        o = np.argsort(tm_ids)
        tm_ids, tm_story = tm_ids[o], tm_story[o]
        pos = np.searchsorted(tm_ids, ids)
        pos_ok = (pos < len(tm_ids))
        safe = np.where(pos_ok, pos, 0)
        assigned_any = pos_ok & (tm_ids[safe] == ids)
        assigned_story = assigned_any & tm_story[safe]

        emb_list: list = []
        with open(self.args.out + ".embids.jsonl") as f:
            for line in f:
                emb_list.extend(json.loads(line))
        emb_ids = np.array(sorted(emb_list), dtype=np.int64)
        p2 = np.searchsorted(emb_ids, ids)
        p2ok = p2 < len(emb_ids)
        embedded = p2ok & (emb_ids[np.where(p2ok, p2, 0)] == ids)

        with open(self.args.out + ".polpairs.json") as f:
            pol = json.load(f)
        pol_ids = np.fromiter((p[0] for p in pol), dtype=np.int64,
                              count=len(pol))
        pol_gk = np.fromiter((p[1] for p in pol), dtype=bool, count=len(pol))
        o = np.argsort(pol_ids)
        pol_ids, pol_gk = pol_ids[o], pol_gk[o]
        p3 = np.searchsorted(pol_ids, ids)
        p3ok = p3 < len(pol_ids)
        is_pol = p3ok & (pol_ids[np.where(p3ok, p3, 0)] == ids)
        is_pol_gk = is_pol & pol_gk[np.where(p3ok, p3, 0)]

        self._cj = dict(ids=ids, days=days, ccs=ccs, day_a=day_a, cc_a=cc_a,
                        has_h=has_h, srv=srv, assigned_any=assigned_any,
                        assigned_story=assigned_story, embedded=embedded,
                        is_pol=is_pol, is_pol_gk=is_pol_gk)
        return self._cj

    async def _fetch_vecs(self, ids: list[int]) -> dict[int, np.ndarray]:
        out: dict[int, np.ndarray] = {}
        for i in range(0, len(ids), 300):
            batch = ids[i:i + 300]
            rows = await self.q(
                "SELECT signal_id, vec::text AS v, model "
                "FROM signal_embeddings WHERE signal_id = ANY($1::bigint[])",
                batch)
            for r in rows:
                out[r["signal_id"]] = np.array(
                    r["v"].strip("[]").split(","), dtype=np.float32)
            self.state.setdefault("emb_model", rows[0]["model"] if rows else None)
        return out

    async def stage_samples(self) -> None:
        if "samples" in self.state:
            return
        cj = self._client_join()
        srv, story = cj["srv"], cj["assigned_story"]
        emb, ids = cj["embedded"], cj["ids"]
        pol = cj["is_pol"]
        cc_co = cj["ccs"].index("CO") if "CO" in cj["ccs"] else -1

        def pick(mask: np.ndarray, k: int) -> list[int]:
            idx = np.flatnonzero(mask)
            if len(idx) > k:
                idx = np.array(self.rng.sample(list(idx), k))
            return [int(ids[i]) for i in idx]

        frames = {
            # unassigned-to-story, embedded, servable — the attribution frame
            "global_unassigned": pick(srv & ~story & emb, 1050),
            "co_unassigned": pick(srv & ~story & emb &
                                  (cj["cc_a"] == cc_co), 300),
            "political_unassigned": pick(srv & ~story & emb & pol, 400),
            # positive control: assigned-to-story signals
            "control_assigned": pick(srv & story & emb, 250),
        }
        # witness splits use the FULL tm/emb id sets (the last24h window
        # includes signals newer than the census window)
        with open(self.args.out + ".tmpairs.json") as f:
            tm_full = json.load(f)
        tm_any_set = {p[0] for p in tm_full}
        tm_story_set = {p[0] for p in tm_full if p[1]}
        emb_set: set = set()
        with open(self.args.out + ".embids.jsonl") as f:
            for line in f:
                emb_set.update(json.loads(line))
        for wname, per in self.state["witness"].items():
            for nname, w in per.items():
                wids = w["ids"]
                un_any = [i for i in wids if i not in tm_any_set]
                un_story = [i for i in wids if i not in tm_story_set]
                w["unassigned_any"] = len(un_any)       # protocol parity
                w["unassigned_story"] = len(un_story)   # "no story" (strict)
                w["unassigned_story_embedded"] = sum(
                    1 for i in un_story if i in emb_set)
                frames[f"witness_{wname}_{nname}"] = [
                    i for i in un_story if i in emb_set][:200]
        self.state["samples"] = frames
        self.save_state()
        for k, v in frames.items():
            print(f"[samples] {k}: {len(v)}")

    async def stage_attribution(self) -> None:
        if "attribution" in self.state:
            return
        cent = np.load(self.args.out + ".centroids.npy")
        metas = self.state["cent_meta"]
        cn = cent / (np.linalg.norm(cent, axis=1, keepdims=True) + 1e-9)
        active_story = np.array([(m["state"] == "active" and
                                  not m["is_umbrella"]) for m in metas])
        anycand = np.ones(len(metas), dtype=bool)   # active+candidate, no junk
        results: dict = {}
        all_ids = sorted({i for v in self.state["samples"].values()
                          for i in v})
        vecs = await self._fetch_vecs(all_ids)
        print(f"[attr] fetched {len(vecs)} vecs "
              f"(model={self.state.get('emb_model')})")
        heads: dict[int, tuple] = {}
        for i in range(0, len(all_ids), 400):
            rows = await self.q(
                "SELECT id, headline, TRIM(COALESCE(country_code,'')) AS cc "
                "FROM signals_v2 WHERE id = ANY($1::bigint[])",
                all_ids[i:i + 400])
            for r in rows:
                heads[r["id"]] = (r["headline"], r["cc"])
        # junk parity: every non-witness sampled id passed the SQL servable
        # predicate; count Python is_junk_headline disagreements
        sys.path.insert(0, os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))))
        from app.services.research_semantic import is_junk_headline
        nonwit = {i for f, v in self.state["samples"].items()
                  if not f.startswith("witness_") for i in v}
        disagree = sum(1 for i in nonwit
                       if i in heads and is_junk_headline(heads[i][0]))
        self.state["junk_parity"] = {
            "sampled_servable": len(nonwit),
            "python_says_junk": disagree,
        }
        labels = {m["id"]: m["label"] for m in metas}
        for frame, fids in self.state["samples"].items():
            have = [i for i in fids if i in vecs and len(vecs[i]) == cent.shape[1]]
            if not have:
                results[frame] = {"n": 0}
                continue
            v = np.stack([vecs[i] for i in have])
            v = v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-9)
            sims = v @ cn.T                                    # (n, topics)
            out_f: dict = {"n": len(have)}
            for scope, mask in (("active_stories", active_story),
                                ("active_plus_candidates", anycand)):
                s = sims[:, mask]
                mx = s.max(axis=1)
                am = s.argmax(axis=1)
                midx = np.flatnonzero(mask)
                out_f[scope] = {
                    "ge_088": int((mx >= TAU_MATCH).sum()),
                    "band_082_088": int(((mx >= TAU_ASSIGN) &
                                         (mx < TAU_MATCH)).sum()),
                    "lt_082": int((mx < TAU_ASSIGN).sum()),
                    "p50": round(float(np.percentile(mx, 50)), 4),
                    "p90": round(float(np.percentile(mx, 90)), 4),
                    "examples_top": [
                        {"signal_id": int(have[i]),
                         "max_cos": round(float(mx[i]), 4),
                         "headline": (heads.get(int(have[i]),
                                                ("?", "?"))[0] or "")[:110],
                         "cc": heads.get(int(have[i]), ("?", "?"))[1],
                         "topic_id": int(metas[int(midx[am[i]])]["id"]),
                         "label": labels[metas[int(midx[am[i]])]["id"]]}
                        for i in list(np.argsort(-mx)[:5])],
                }
            results[frame] = out_f
            print(f"[attr] {frame}: n={out_f['n']} "
                  f"active ge088={out_f['active_stories']['ge_088']} "
                  f"band={out_f['active_stories']['band_082_088']} "
                  f"lt082={out_f['active_stories']['lt_082']}")
        self.state["attribution"] = results
        self.save_state()

    # ---------- stage 8: final tables ----------
    def stage_tables(self) -> None:
        cj = self._client_join()
        days, ccs = cj["days"], cj["ccs"]
        nd, nc = len(days), len(ccs)
        key = cj["day_a"].astype(np.int32) * nc + cj["cc_a"]

        def agg(mask: np.ndarray) -> np.ndarray:
            return np.bincount(key[mask], minlength=nd * nc).reshape(nd, nc)

        t = {
            "total": agg(np.ones(len(key), dtype=bool)),
            "with_headline": agg(cj["has_h"]),
            "servable": agg(cj["srv"]),
            "srv_assigned_any": agg(cj["srv"] & cj["assigned_any"]),
            "srv_assigned_story": agg(cj["srv"] & cj["assigned_story"]),
            "srv_embedded": agg(cj["srv"] & cj["embedded"]),
            "pol": agg(cj["srv"] & cj["is_pol"]),
            "pol_story": agg(cj["srv"] & cj["is_pol"] & cj["assigned_story"]),
            "pol_gk": agg(cj["srv"] & cj["is_pol_gk"]),
            "pol_gk_story": agg(cj["srv"] & cj["is_pol_gk"] &
                                cj["assigned_story"]),
        }
        self.state["tables"] = {
            "days": days, "countries": ccs,
            **{k: v.tolist() for k, v in t.items()},
        }
        # sanity: python-side is_junk parity on a sample of servable headlines
        self.save_state()

    def write_output(self) -> None:
        out = {k: v for k, v in self.state.items()
               if k not in ("sig_rows", "tm_pairs", "emb_ids", "pol_pairs")}
        # witness ids are long; keep counts, drop raw id lists
        for wname, per in out.get("witness", {}).items():
            for nname, w in per.items():
                w["ids"] = f"<{len(w['ids'])} ids omitted>"
        with open(self.args.out, "w") as f:
            json.dump(out, f, indent=1, default=str)
        print(f"[done] wrote {self.args.out}")

    async def run(self) -> None:
        await self.stage_meta()
        await self.stage_chunks()
        await self.stage_tm()
        await self.stage_emb()
        await self.stage_pol()
        await self.stage_witness()
        await self.stage_centroids()
        await self.stage_samples()
        await self.stage_attribution()
        self.stage_tables()
        self.write_output()
        if self.conn:
            await self.conn.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--resume", action="store_true", default=True)
    ap.add_argument("--fresh", dest="resume", action="store_false")
    args = ap.parse_args()
    asyncio.run(Census(args).run())


if __name__ == "__main__":
    main()
