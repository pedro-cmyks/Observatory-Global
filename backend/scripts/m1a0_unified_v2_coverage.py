#!/usr/bin/env python3
"""M1-A0 — unified-v2 coverage over the Z4 orphans (READ-ONLY, 2026-08-20).

Plan: docs/superpowers/plans/2026-08-20-plan-motor.md (M1-A0). Decides the
assignment-lane arc: does the never-served unified-v2 build already cover the
92.2% of the servable corpus that has no story under the serving engine
version (v1-compat)?

Questions (each with declared window + population):
  Q1  unified-v2 vitality: rows, dates, distinct topics, is the nightly build
      alive or dead?
  Q2  Z4-orphan coverage: fraction of the 7d servable corpus (Aug 13-19 UTC)
      without a story under v1-compat vs v1-compat UNION unified-v2 vs
      unified-v2 alone.  Per-day split (the union delta is structurally
      concentrated in the window the last build saw).
  Q3  frozen witnesses (espriella/golán/ungrd, window Aug 13 15:00Z ->
      Aug 14 15:00Z): of the without-story set, how many have unified-v2
      membership, and to which topics.
  Q4  sample seed 229 of 40 signals unified-v2 attaches and v1-compat does
      not -> headline + topic label dumped for HAND judgment (yes/dudoso/no).
  Q5  political subset (Z4 §5 criterion): % without story under v1-compat vs
      under the union.

Design constraints honored (same as z4_unassigned_census.py):
  * READ ONLY (SET TRANSACTION READ ONLY per transaction).
  * statement_cache_size=0; SET LOCAL statement_timeout='110s'.
  * signals_v2 walked in adaptive id-range chunks behind a MATERIALIZED
    fence; joins client-side; resumable state after every chunk.

Usage (from backend/, .venv):
  .venv/bin/python scripts/m1a0_unified_v2_coverage.py --out <state dir>/m1a0.json
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import os
import random
import time

import asyncpg
import numpy as np

ENV_PATH = "/Users/pedro/AtlasLocalWorker/.env"
STATEMENT_TIMEOUT = "110s"
SEED = 229

# is_junk_headline (app/services/research_semantic.py) in SQL form — copied
# VERBATIM from z4_unassigned_census.py (SQL<->Python parity verified there:
# 0 disagreements in 1,997 sampled).
JUNK_RE_1 = r"\.s?html?\y|^doc\s|^untitled\y"
JUNK_RE_2 = r"^\s*digit:\s*[0-9,.]+"
JUNK_RE_3 = (r"\yin words:\s*(zero|one|two|three|four|five|six|seven|eight"
             r"|nine|ten|eleven|twelve|(thir|four|fif|six|seven|eigh|nine)teen"
             r"|(twen|thir|for|fif|six|seven|eigh|nine)ty"
             r"|hundred|thousand|million|billion)\y")
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

WITNESS_NEEDLES = {"espriella": "%espriella%", "golán": "%golán%",
                   "ungrd": "%ungrd%"}
FROZEN_WINDOW = ("2026-08-13T15:00:00+00:00", "2026-08-14T15:00:00+00:00")

MEMBER_FILTER = ("role = 'evidence' AND engine_version = $1 "
                 "AND quarantined IS NOT TRUE")


def load_db_url() -> str:
    with open(ENV_PATH) as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                return line.strip().split("=", 1)[1]
    raise SystemExit("DATABASE_URL not found in " + ENV_PATH)


class M1A0:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.state_path = args.out + ".state.json"
        self.state: dict = {}
        if args.resume and os.path.exists(self.state_path):
            with open(self.state_path) as f:
                self.state = json.load(f)
            print(f"[resume] state loaded (last_id={self.state.get('last_id')})")
        self.conn: asyncpg.Connection | None = None
        self.rng = random.Random(SEED)

    async def connect(self) -> None:
        if self.conn is not None and not self.conn.is_closed():
            return
        self.conn = await asyncpg.connect(load_db_url(),
                                          statement_cache_size=0, timeout=30)

    async def q(self, sql: str, *params, timeout: str = STATEMENT_TIMEOUT):
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

    # ---------- Q1: unified-v2 vitality ----------
    async def stage_vitality(self) -> None:
        if "vitality" in self.state:
            return
        out: dict = {}
        rows = await self.q("""
            SELECT engine_version, role, COUNT(*) AS n,
                   COUNT(*) FILTER (WHERE topic_id LIKE 'dynamic-topic-%') AS dyn,
                   COUNT(DISTINCT topic_id) AS topics,
                   MIN(assigned_at)::text AS min_at,
                   MAX(assigned_at)::text AS max_at
            FROM topic_members GROUP BY 1, 2 ORDER BY n DESC""")
        out["tm_breakdown"] = [dict(r) for r in rows]
        # unified evidence: distinct signals + per-signal-day distribution
        rows = await self.q("""
            SELECT COUNT(DISTINCT signal_id) AS signals,
                   COUNT(DISTINCT topic_id) AS topics, COUNT(*) AS rows
            FROM topic_members
            WHERE engine_version = 'unified-v2' AND role = 'evidence'
              AND quarantined IS NOT TRUE""")
        out["u2_evidence"] = dict(rows[0])
        # topic-state breakdown of unified topics
        rows = await self.q("""
            SELECT dt.state, COUNT(DISTINCT tm.topic_id) AS topics,
                   COUNT(*) AS member_rows
            FROM topic_members tm
            JOIN dynamic_topics dt
              ON dt.id = substring(tm.topic_id FROM 15)::bigint
            WHERE tm.engine_version = 'unified-v2' AND tm.role = 'evidence'
              AND tm.topic_id ~ '^dynamic-topic-[0-9]+$'
            GROUP BY 1 ORDER BY member_rows DESC""")
        out["u2_topic_states"] = [dict(r) for r in rows]
        self.state["vitality"] = out
        self.save_state()
        print("[vitality]", json.dumps(out["u2_evidence"]))

    # ---------- unified member signal ids + their signal timestamps ----------
    async def stage_u2_span(self) -> None:
        if "u2_span" in self.state:
            return
        rows = await self.q("""
            SELECT DISTINCT signal_id FROM topic_members
            WHERE engine_version = 'unified-v2' AND role = 'evidence'
              AND quarantined IS NOT TRUE""")
        ids = sorted(r["signal_id"] for r in rows)
        with open(self.args.out + ".u2ids.json", "w") as f:
            json.dump(ids, f)
        # signal timestamps, chunked pkey lookups
        per_day: dict[str, int] = {}
        mn, mx = None, None
        for i in range(0, len(ids), 4000):
            batch = ids[i:i + 4000]
            rr = await self.q("""
                SELECT ((timestamp AT TIME ZONE 'UTC')::date)::text AS day,
                       COUNT(*) AS n, MIN(timestamp)::text AS mn,
                       MAX(timestamp)::text AS mx
                FROM signals_v2 WHERE id = ANY($1::bigint[]) GROUP BY 1""",
                batch)
            for r in rr:
                per_day[r["day"]] = per_day.get(r["day"], 0) + r["n"]
                mn = min(mn, r["mn"]) if mn else r["mn"]
                mx = max(mx, r["mx"]) if mx else r["mx"]
        self.state["u2_span"] = {
            "distinct_signals": len(ids),
            "signal_ts_min": mn, "signal_ts_max": mx,
            "signals_per_day": dict(sorted(per_day.items())),
        }
        self.save_state()
        print("[u2_span]", json.dumps(self.state["u2_span"]["signals_per_day"]))

    # ---------- meta / boundary ----------
    async def stage_meta(self) -> None:
        if "meta" in self.state:
            return
        r = await self.q("SELECT now() AS now")
        now = r[0]["now"]
        mx_id = (await self.q(
            "SELECT id FROM signals_v2 ORDER BY id DESC LIMIT 1"))[0]["id"]
        mn_id = (await self.q(
            "SELECT id FROM signals_v2 ORDER BY id ASC LIMIT 1"))[0]["id"]
        mn_ts = (await self.q(
            "SELECT timestamp FROM signals_v2 ORDER BY timestamp ASC LIMIT 1"
        ))[0]["timestamp"]
        end_day = now.date()
        start_day = end_day - dt.timedelta(days=self.args.days)
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
        }
        self.save_state()
        print(f"[meta] window {start_day}..{end_day} boundary={lo} "
              f"max={mx_id} span={mx_id - lo}")

    # ---------- chunked signals_v2 walk ----------
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
                print(f"  [chunk] timeout -> retry at {size}")
                continue
            el = time.time() - t0
            with open(sig_path, "a") as f:
                for r in rows:
                    f.write(json.dumps(
                        [r["id"], r["cc"], r["day"], r["servable"]]) + "\n")
            last = hi
            self.state["last_id"] = last
            self.state["sig_rows_count"] = (
                self.state.get("sig_rows_count", 0) + len(rows))
            if el < 45 and size < 150_000:
                size = int(size * 1.5)
                self.state["chunk_size"] = size
            self.save_state()
            done, total = last - m["boundary_id"], m["id_max"] - m["boundary_id"]
            print(f"  [chunk] id<={last} +{len(rows)} ({el:.0f}s, "
                  f"size {size}) {done * 100 // total}%", flush=True)
        self.state["chunks_done"] = True
        self.save_state()
        print(f"[chunks] window rows: {self.state.get('sig_rows_count', 0)}")

    # ---------- topic_members pairs, both engines ----------
    async def stage_tm(self) -> None:
        for ev, key in (("v1-compat", "tmv1"), ("unified-v2", "tmu2")):
            if self.state.get(f"{key}_done"):
                continue
            rows = await self.q(f"""
                SELECT signal_id,
                       BOOL_OR(topic_id LIKE 'dynamic-topic-%') AS story
                FROM topic_members
                WHERE {MEMBER_FILTER}
                GROUP BY signal_id""", ev)
            with open(self.args.out + f".{key}.json", "w") as f:
                json.dump([[r["signal_id"], r["story"]] for r in rows], f)
            self.state[f"{key}_done"] = True
            self.state[f"{key}_count"] = len(rows)
            self.save_state()
            print(f"[tm] {ev}: {len(rows)} distinct evidence signal_ids")

    # ---------- political pairs ----------
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
        self.save_state()
        print(f"[pol] {len(rows)} signals with political assignments")

    # ---------- witnesses (frozen window) ----------
    async def stage_witness(self) -> None:
        if "witness" in self.state:
            return
        w0, w1 = (dt.datetime.fromisoformat(x) for x in FROZEN_WINDOW)
        out: dict = {}
        needles = dict(WITNESS_NEEDLES)
        needles["OR_protocol"] = None
        for nname, needle in needles.items():
            if needle is None:
                pred = ("(lower(headline) LIKE '%espriella%' OR "
                        "lower(headline) LIKE '%golán%' OR "
                        "lower(headline) LIKE '%ungrd%')")
                rows = await self.q(f"""
                    SELECT id, headline, TRIM(COALESCE(country_code,'')) AS cc
                    FROM signals_v2
                    WHERE timestamp >= $1::timestamptz
                      AND timestamp < $2::timestamptz AND {pred}
                    LIMIT 4000""", w0, w1)
            else:
                rows = await self.q("""
                    SELECT id, headline, TRIM(COALESCE(country_code,'')) AS cc
                    FROM signals_v2
                    WHERE timestamp >= $1::timestamptz
                      AND timestamp < $2::timestamptz
                      AND lower(headline) LIKE $3
                    LIMIT 4000""", w0, w1, needle)
            ids = [r["id"] for r in rows]
            landings = {}
            for ev in ("v1-compat", "unified-v2"):
                if not ids:
                    landings[ev] = []
                    continue
                lr = await self.q(f"""
                    SELECT tm.topic_id, COUNT(DISTINCT tm.signal_id) AS n,
                           dt.label, dt.state
                    FROM topic_members tm
                    LEFT JOIN dynamic_topics dt ON dt.id = CASE
                        WHEN tm.topic_id ~ '^dynamic-topic-[0-9]+$'
                        THEN substring(tm.topic_id FROM 15)::bigint END
                    WHERE tm.signal_id = ANY($2::bigint[]) AND {MEMBER_FILTER}
                    GROUP BY 1, 3, 4 ORDER BY n DESC LIMIT 40""", ev, ids)
                landings[ev] = [dict(r) for r in lr]
            out[nname] = {
                "matched": len(ids), "ids": ids,
                "headlines": {r["id"]: r["headline"] for r in rows},
                "landing_v1": landings["v1-compat"],
                "landing_u2": landings["unified-v2"],
            }
            print(f"[witness] {nname}: matched={len(ids)}")
        self.state["witness"] = out
        self.save_state()

    # ---------- client-side join + tables ----------
    def _client_join(self):
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
        day_a = np.fromiter((day_idx[r[2]] for r in rows), dtype=np.int16,
                            count=n)
        srv = np.fromiter((r[3] for r in rows), dtype=bool, count=n)

        def pair_mask(path: str, story_only: bool = True):
            with open(path) as f:
                pairs = json.load(f)
            pids = np.fromiter((p[0] for p in pairs), dtype=np.int64,
                               count=len(pairs))
            pst = np.fromiter((p[1] for p in pairs), dtype=bool,
                              count=len(pairs))
            o = np.argsort(pids)
            pids, pst = pids[o], pst[o]
            pos = np.searchsorted(pids, ids)
            ok = pos < len(pids)
            safe = np.where(ok, pos, 0)
            member = ok & (pids[safe] == ids)
            story = member & pst[safe]
            return member, story

        _, v1_story = pair_mask(self.args.out + ".tmv1.json")
        u2_any, u2_story = pair_mask(self.args.out + ".tmu2.json")

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

        self._cj = dict(ids=ids, days=days, day_a=day_a, srv=srv,
                        v1_story=v1_story, u2_story=u2_story, u2_any=u2_any,
                        is_pol=is_pol, is_pol_gk=is_pol_gk)
        return self._cj

    def stage_tables(self) -> None:
        cj = self._client_join()
        days = cj["days"]
        srv, v1s, u2s = cj["srv"], cj["v1_story"], cj["u2_story"]
        union = v1s | u2s
        per_day = []
        for i, d in enumerate(days):
            m = srv & (cj["day_a"] == i)
            nt = int(m.sum())
            per_day.append({
                "day": d, "servable": nt,
                "story_v1": int((m & v1s).sum()),
                "story_u2": int((m & u2s).sum()),
                "story_union": int((m & union).sum()),
                "u2_only": int((m & u2s & ~v1s).sum()),
            })
        tot = {
            "servable": int(srv.sum()),
            "story_v1": int((srv & v1s).sum()),
            "story_u2": int((srv & u2s).sum()),
            "story_union": int((srv & union).sum()),
            "u2_only": int((srv & u2s & ~v1s).sum()),
        }
        pol, polgk = cj["is_pol"] & srv, cj["is_pol_gk"] & srv
        pol_t = {
            "political": int(pol.sum()),
            "story_v1": int((pol & v1s).sum()),
            "story_union": int((pol & union).sum()),
            "gate_kept": int(polgk.sum()),
            "gk_story_v1": int((polgk & v1s).sum()),
            "gk_story_union": int((polgk & union).sum()),
        }
        self.state["tables"] = {"per_day": per_day, "total": tot,
                                "political": pol_t}
        self.save_state()
        print("[tables]", json.dumps(tot))
        print("[tables:pol]", json.dumps(pol_t))

    # ---------- witness x unified cross ----------
    def stage_witness_cross(self) -> None:
        if "witness_cross" in self.state:
            return
        with open(self.args.out + ".tmv1.json") as f:
            v1 = json.load(f)
        v1_story_set = {p[0] for p in v1 if p[1]}
        with open(self.args.out + ".tmu2.json") as f:
            u2 = json.load(f)
        u2_set = {p[0] for p in u2}
        u2_story_set = {p[0] for p in u2 if p[1]}
        out = {}
        for nname, w in self.state["witness"].items():
            wids = w["ids"]
            no_story_v1 = [i for i in wids if i not in v1_story_set]
            out[nname] = {
                "matched": len(wids),
                "no_story_v1": len(no_story_v1),
                "of_those_u2_any": sum(1 for i in no_story_v1 if i in u2_set),
                "of_those_u2_story": sum(
                    1 for i in no_story_v1 if i in u2_story_set),
            }
        self.state["witness_cross"] = out
        self.save_state()
        print("[witness_cross]", json.dumps(out))

    # ---------- Q4 sample: unified-only attachments ----------
    async def stage_sample(self) -> None:
        if "u2_only_sample" in self.state:
            return
        cj = self._client_join()
        mask = cj["srv"] & cj["u2_story"] & ~cj["v1_story"]
        pool = [int(x) for x in cj["ids"][np.flatnonzero(mask)]]
        n = min(40, len(pool))
        sample = sorted(self.rng.sample(pool, n)) if pool else []
        rows = await self.q("""
            SELECT s.id, s.headline, TRIM(COALESCE(s.country_code,'')) AS cc,
                   s.source_family, tm.topic_id, tm.confidence, tm.gate_kept,
                   dt.label, dt.state
            FROM signals_v2 s
            JOIN topic_members tm ON tm.signal_id = s.id
             AND tm.engine_version = 'unified-v2' AND tm.role = 'evidence'
             AND tm.quarantined IS NOT TRUE
            LEFT JOIN dynamic_topics dt
              ON dt.id = substring(tm.topic_id FROM 15)::bigint
            WHERE s.id = ANY($1::bigint[])
            ORDER BY s.id, tm.confidence DESC""", sample)
        self.state["u2_only_pool"] = len(pool)
        self.state["u2_only_sample"] = [dict(r) for r in rows]
        self.save_state()
        print(f"[sample] pool={len(pool)} sampled={n} rows={len(rows)}")

    def write_output(self) -> None:
        out = dict(self.state)
        for nname, w in out.get("witness", {}).items():
            w.pop("headlines", None)
            w["ids"] = f"<{len(w['ids'])} ids omitted>"
        with open(self.args.out, "w") as f:
            json.dump(out, f, indent=1, default=str)
        print(f"[done] wrote {self.args.out}")

    async def run(self) -> None:
        await self.stage_vitality()
        await self.stage_u2_span()
        await self.stage_meta()
        await self.stage_chunks()
        await self.stage_tm()
        await self.stage_pol()
        await self.stage_witness()
        self.stage_tables()
        self.stage_witness_cross()
        await self.stage_sample()
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
    asyncio.run(M1A0(args).run())


if __name__ == "__main__":
    main()
