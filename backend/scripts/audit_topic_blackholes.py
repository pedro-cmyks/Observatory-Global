"""M2 — Topic-level black-hole audit + measured prune (#224 heir).

Disease: dynamic-topic identities absorb unrelated content (running-centroid
drift + compressed e5 scale), so `topic_members` evidence carries members that
are statistically indistinguishable from random background vs the topic's OWN
centroid. Council evidence 2026-07: same-story precision ~77.5%; unrelated
events served inside umbrellas.

Method (the 2026-07-03 adaptive-floor precedent, `public_attention.py
adaptive_noise_cut`): per-centroid floor over a shared random-background
sample of signal embeddings — the e5 noise floor VARIES per centroid
(measured 0.875-0.900), so fixed cutoffs always serve junk. Two floors are
computed per topic:

  naive  = bg_mean   + SIGMAS * bg_std              (07-03 formula, exact)
  robust = bg_median + SIGMAS * 1.4826 * MAD        (contamination-resistant)

The robust floor is the PRUNE floor: for mega-stories (Ukraine class) the
random background itself contains genuine same-story coverage, which inflates
bg_std and over-flags cross-language members (measured in this audit's pilot:
a Lithuanian Zelensky headline at sim 0.851 vs naive floor 0.921). Median/MAD
resist that tail while keeping the same "SIGMAS above background" meaning.
The topic's own members are EXCLUDED from its background sample.

Junk fraction per (topic, engine) lane = measured members with sim < floor /
measured members. Prune threshold is DERIVED from the distribution (kneedle
max-distance-to-chord over the sorted eligible fractions), never guessed.

Prune is measured + reversible (migration 087): rows are NEVER deleted —
below-floor evidence rows in qualifying lanes get `quarantined=true` +
reason + timestamp. Serving readers exclude quarantined evidence, so gated
counts recompute honestly. `etl_topic_members` is ON CONFLICT DO NOTHING, so
flags on the v1-compat lane SURVIVE re-projection. The unified-v2 lane is
DELETE+rebuilt nightly by `build_unified_topics.py`, so flags there would
evaporate — the default prune scope is v1-compat only (the serving default
per `thread_intelligence.topic_members_engine_version`).

Usage:
  python -m scripts.audit_topic_blackholes                     # audit, read-only
  python -m scripts.audit_topic_blackholes --write             # prune (guarded)
  python -m scripts.audit_topic_blackholes --revert RUN_ID     # undo one run

Reversal one-liner (SQL):
  UPDATE topic_members SET quarantined=false, quarantine_reason=NULL,
         quarantined_at=NULL WHERE quarantine_reason LIKE 'blackhole-floor-v1%';
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import html
import json
import math
import os
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

# ---------------------------------------------------------------- constants
SIGMAS = 2.5                 # the 07-03 precedent
MAD_TO_SIGMA = 1.4826        # normal-consistency constant for MAD
N_BG = 400                   # background sample size (shared draw, per-topic sims)
MIN_BG = 100                 # below this the floor is not computable (honest skip)
MIN_MEMBERS_PRUNE = 8        # lanes smaller than this are audited, never pruned
DEFAULT_SEED = 42
REASON_PREFIX = "blackhole-floor-v1"
DURABLE_ENGINE = "v1-compat"          # survives ETL ON CONFLICT DO NOTHING
EPHEMERAL_ENGINES = {"unified-v2"}    # DELETE+rebuilt nightly; flags evaporate
ARTIFACT_DIR = Path(__file__).resolve().parents[2] / "docs" / "research" / "topic-quality"

TOPIC_CHUNK = 250
UPDATE_CHUNK = 500


# ---------------------------------------------------------------- pure math
@dataclass(frozen=True)
class FloorStats:
    """Per-centroid background statistics + both floors (None = not computable)."""
    n: int
    mean: Optional[float]
    std: Optional[float]
    median: Optional[float]
    mad: Optional[float]
    naive_floor: Optional[float]
    robust_floor: Optional[float]


def floor_stats(bg_sims: Sequence[float], *, sigmas: float = SIGMAS,
                min_bg: int = MIN_BG) -> FloorStats:
    """Adaptive per-centroid floor from a random-background similarity sample.

    naive  = mean + sigmas*std           (07-03 `adaptive_noise_cut` formula)
    robust = median + sigmas*1.4826*MAD  (same meaning, contamination-resistant)

    Too small a sample -> floors None (honest skip; the 07-03 precedent keeps a
    fixed fallback floor, but for the AUDIT an uncomputable floor must not
    fabricate junk fractions).
    """
    n = len(bg_sims)
    if n < min_bg:
        return FloorStats(n, None, None, None, None, None, None)
    mean = statistics.fmean(bg_sims)
    std = statistics.stdev(bg_sims) if n > 1 else 0.0
    med = statistics.median(bg_sims)
    mad = statistics.median([abs(s - med) for s in bg_sims])
    return FloorStats(
        n=n, mean=mean, std=std, median=med, mad=mad,
        naive_floor=mean + sigmas * std,
        robust_floor=med + sigmas * MAD_TO_SIGMA * mad,
    )


def junk_split(sims: Sequence[float], floor: Optional[float]) -> tuple[int, int]:
    """(below_floor_count, measured_count). No floor -> nothing is junk."""
    total = len(sims)
    if floor is None:
        return 0, total
    return sum(1 for s in sims if s < floor), total


def knee_threshold(fracs: Sequence[float]) -> Optional[float]:
    """Kneedle-style knee over the sorted ascending junk-fraction curve.

    The point of maximum distance between the curve and its first-to-last
    chord marks the END of the healthy mass (for the typical flat-then-rising
    audit shape the gap is widest at the last healthy lane). The prune
    threshold is the FIRST value STRICTLY ABOVE that point — the tail's
    entry value — so "junk_frac >= knee" selects exactly the anomalous tail
    and never the healthy bulk. Returns None when the curve is degenerate
    (fewer than 4 points, flat, or no value above the elbow) — caller must
    not prune then.
    """
    ys = sorted(float(f) for f in fracs)
    n = len(ys)
    if n < 4:
        return None
    y0, y1 = ys[0], ys[-1]
    if y1 - y0 <= 1e-12:
        return None  # flat distribution: no tail to cut
    best_d, best_i = -1.0, 0
    for i, y in enumerate(ys):
        x = i / (n - 1)
        chord = y0 + (y1 - y0) * x
        d = abs(y - chord) / (y1 - y0)
        if d > best_d:
            best_d, best_i = d, i
    elbow_y = ys[best_i]
    for y in ys[best_i:]:
        if y > elbow_y + 1e-12:
            return y
    return None  # elbow at the max: no tail above it


def quarantine_reason(sim: float, floor: float, run_id: str) -> str:
    return f"{REASON_PREFIX} run={run_id} sim={sim:.4f} floor={floor:.4f}"


def run_id_for(seed: int, day: dt.date) -> str:
    return f"m2-{day.strftime('%Y%m%d')}-s{seed}"


def lane_eligible(measured: int, floor: Optional[float],
                  *, min_members: int = MIN_MEMBERS_PRUNE) -> bool:
    return floor is not None and measured >= min_members


MAX_PRUNE_FRAC = 0.5   # median-core guard, see classify_lane


def classify_lane(frac: float, knee: Optional[float],
                  *, max_frac: float = MAX_PRUNE_FRAC) -> str:
    """Prune-safety triage of an eligible lane, receipts-validated 2026-07-20.

    'healthy'           frac below the knee — leave alone.
    'prune'             knee <= frac < max_frac: the topic keeps a resolvable
                        core (member MEDIAN above its floor ⟺ frac < 0.5), and
                        the below-floor minority are absorbed strangers — the
                        #224 class receipts confirmed (Bad Bunny concert inside
                        "Ryanair Window Incident"; Zaporizhzhia strikes inside
                        "Monaco Explosion"; budget-deficit stories inside
                        "Russia Imports Aviation Fuel").
    'centroid_divorced' frac >= max_frac: the centroid cannot distinguish its
                        OWN MEDIAN member from random background. Receipts show
                        this class MIXES true absorption (a Brussels FIRE event
                        as the entire membership of the Molenbeek-shooting
                        topic dt-346) with mush-centroid mega-stories whose
                        members are genuine (dt-10 "Ukraine War Updates",
                        floor 0.9351 — the centroid drifted toward the corpus
                        mean, the space resolves nothing). Member-pruning
                        cannot tell those apart, so this class is REPORTED for
                        topic-level surgery (label court / is_junk / re-found),
                        never member-pruned.
    """
    if knee is None or frac < knee:
        return "healthy"
    if frac < max_frac:
        return "prune"
    return "centroid_divorced"


# ---------------------------------------------------------------- SQL
_TOPICS_SQL = """
SELECT dt.id, dt.label, dt.category, dt.agg_n_signals
FROM dynamic_topics dt
WHERE dt.state = 'active'
  AND COALESCE(dt.is_umbrella, false) = false
  AND COALESCE(dt.is_junk, false) = false
  AND dt.centroid_vec IS NOT NULL
ORDER BY dt.id
"""

# Row-level iid + story-deduped background. TABLESAMPLE SYSTEM was measured
# WRONG here (2026-07-20): it samples PAGES, and pages cluster by ingest batch
# — syndication bursts land contiguously — so the 400-draw came back clumped
# and bimodal, exploding median/MAD (topic-10 floor swung 0.9209 -> 0.945
# between draws; whole lanes read 100% junk). DISTINCT ON a headline hash
# collapses syndicated copies to one story; ORDER BY random() (seeded via
# setseed) makes the draw iid over STORIES, reproducibly.
# Two stages keep it inside the statement timeout on the shared pooler:
# (1) iid row draw of ~{N_BG}*8 via top-N heapsort, (2) headline-hash dedupe
# of that SMALL set (collapses syndicated copies to one story), (3) cut to
# N_BG. A full-table DISTINCT-ON-md5 join was measured >180s and cancelled.
_BG_TEMP_SQL = f"""
CREATE TEMP TABLE bg AS
SELECT signal_id, vec FROM (
    SELECT DISTINCT ON (md5(lower(s.headline)))
           draw.signal_id, draw.vec
    FROM (
        SELECT signal_id, vec FROM signal_embeddings
        ORDER BY random() LIMIT {N_BG * 8}
    ) draw
    JOIN signals_v2 s ON s.id = draw.signal_id
    ORDER BY md5(lower(s.headline)), draw.signal_id
) dedup
ORDER BY random()
LIMIT {N_BG}
"""

# Per-topic background sims, EXCLUDING the topic's own evidence members from
# its background (a mega-story's own coverage in the random draw would
# contaminate its floor).
_BG_SIMS_SQL = """
SELECT dt.id,
       array_agg(1 - (dt.c <=> bg.vec)) AS sims
FROM (
    SELECT id, centroid_vec::vector(768)::halfvec(768) AS c
    FROM dynamic_topics WHERE id = ANY($1::bigint[])
) dt
CROSS JOIN bg
WHERE NOT EXISTS (
    SELECT 1 FROM topic_members tm
    WHERE tm.topic_id = 'dynamic-topic-' || dt.id
      AND tm.signal_id = bg.signal_id AND tm.role = 'evidence'
)
GROUP BY dt.id
"""

_MEMBER_SIMS_SQL = """
SELECT dt.id, tm.engine_version, tm.signal_id,
       1 - (dt.c <=> se.vec) AS sim,
       s.source_lang
FROM (
    SELECT id, centroid_vec::vector(768)::halfvec(768) AS c
    FROM dynamic_topics WHERE id = ANY($1::bigint[])
) dt
JOIN topic_members tm
  ON tm.topic_id = 'dynamic-topic-' || dt.id AND tm.role = 'evidence' {quarantine_filter}
JOIN signal_embeddings se ON se.signal_id = tm.signal_id
JOIN signals_v2 s ON s.id = tm.signal_id
"""

_MEMBER_MISSING_SQL = """
SELECT count(*)
FROM dynamic_topics dt
JOIN topic_members tm
  ON tm.topic_id = 'dynamic-topic-' || dt.id AND tm.role = 'evidence'
LEFT JOIN signal_embeddings se ON se.signal_id = tm.signal_id
WHERE dt.id = ANY($1::bigint[]) AND se.signal_id IS NULL
"""

_RECEIPT_HEADLINES_SQL = """
SELECT s.id, s.headline, s.source_lang, s.source_name
FROM signals_v2 s WHERE s.id = ANY($1::bigint[])
"""

_QUARANTINE_COL_SQL = """
SELECT count(*) FROM information_schema.columns
WHERE table_name = 'topic_members' AND column_name = 'quarantined'
"""


def _member_sims_sql(has_quarantine_col: bool) -> str:
    # When the mig-087 column exists, already-quarantined rows are OUT of the
    # junk-fraction denominator: serving no longer counts them, and a re-audit
    # must measure the topic as it is served (that IS the "after" number).
    filt = "AND tm.quarantined IS NOT TRUE" if has_quarantine_col else ""
    return _MEMBER_SIMS_SQL.format(quarantine_filter=filt)


# ---------------------------------------------------------------- helpers
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


def _nightly_running() -> bool:
    try:
        res = subprocess.run(["pgrep", "-f", "run-scoped-snapshot.sh"],
                             capture_output=True, text=True, timeout=10)
        return bool(res.stdout.strip())
    except Exception:
        return True  # cannot verify -> assume running (safe side)


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
async def run_audit(seed: int, artifact_path: Optional[Path]) -> dict:
    conn = await _connect()
    try:
        has_qcol = (await conn.fetchval(_QUARANTINE_COL_SQL)) > 0
        topics = await conn.fetch(_TOPICS_SQL)
        topic_meta = {r["id"]: {"label": r["label"], "category": r["category"],
                                "agg_n_signals": r["agg_n_signals"]} for r in topics}
        ids = list(topic_meta.keys())
        print(f"population: {len(ids)} active non-umbrella non-junk topics "
              f"(quarantine col: {'present' if has_qcol else 'absent'})")

        # one shared, seeded, story-deduped iid background draw
        await conn.execute("SELECT setseed($1)", (seed % 100) / 100.0)
        await conn.execute(_BG_TEMP_SQL)
        n_bg = await conn.fetchval("SELECT count(*) FROM bg")
        print(f"background sample: {n_bg} distinct-story embeddings (seed {seed})")

        floors: dict[int, FloorStats] = {}
        member_rows: list = []
        missing_embeddings = 0
        msql = _member_sims_sql(has_qcol)
        for chunk in _chunks(ids, TOPIC_CHUNK):
            for r in await conn.fetch(_BG_SIMS_SQL, chunk):
                floors[r["id"]] = floor_stats([float(x) for x in r["sims"]])
            member_rows.extend(await conn.fetch(msql, chunk))
            missing_embeddings += await conn.fetchval(_MEMBER_MISSING_SQL, chunk)
            print(f"  scored {min(len(floors), len(ids))}/{len(ids)} topics…",
                  end="\r", flush=True)
        print()

        # assemble lanes
        lanes: dict[tuple[int, str], dict] = {}
        for r in member_rows:
            key = (r["id"], r["engine_version"])
            lane = lanes.setdefault(key, {"sims": [], "ids": [], "langs": []})
            lane["sims"].append(float(r["sim"]))
            lane["ids"].append(int(r["signal_id"]))
            lane["langs"].append(r["source_lang"] or "xx")

        lane_reports = []
        for (tid, engine), lane in lanes.items():
            fs = floors.get(tid)
            if fs is None:
                continue
            below_naive, total = junk_split(lane["sims"], fs.naive_floor)
            below_robust, _ = junk_split(lane["sims"], fs.robust_floor)
            below: list[tuple[float, int, str]] = []
            if fs.robust_floor is not None:
                below = sorted(
                    (s, sid, lg)
                    for s, sid, lg in zip(lane["sims"], lane["ids"], lane["langs"])
                    if s < fs.robust_floor
                )  # worst (lowest sim) first
            below_ids = [sid for _, sid, _ in below]
            below_langs = [lg for _, _, lg in below]
            below_sims = [round(s, 4) for s, _, _ in below]
            lane_reports.append({
                "topic_id": tid,
                "label": topic_meta[tid]["label"],
                "category": topic_meta[tid]["category"],
                "engine": engine,
                "member_median_sim": round(statistics.median(lane["sims"]), 4),
                "measured": total,
                "below_naive": below_naive,
                "below_robust": below_robust,
                "frac_naive": round(below_naive / total, 4) if total else 0.0,
                "frac_robust": round(below_robust / total, 4) if total else 0.0,
                "floor_naive": round(fs.naive_floor, 4) if fs.naive_floor else None,
                "floor_robust": round(fs.robust_floor, 4) if fs.robust_floor else None,
                "bg": {"n": fs.n, "mean": round(fs.mean, 4), "std": round(fs.std, 4),
                       "median": round(fs.median, 4), "mad": round(fs.mad, 4)},
                "below_ids_robust": below_ids,
                "below_sims_robust": below_sims,
                "below_langs": below_langs,
                "all_langs": lane["langs"],
                "eligible": lane_eligible(total, fs.robust_floor),
            })

        eligible = [l for l in lane_reports if l["eligible"]]
        fracs = [l["frac_robust"] for l in eligible]
        knee = knee_threshold(fracs)
        dist = _percentiles(fracs, [0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99])
        floor_dist = _percentiles(
            [l["floor_robust"] for l in eligible if l["floor_robust"] is not None],
            [0.10, 0.50, 0.90])
        # CANARY: if the MEDIAN member of many lanes sits below its own floor,
        # the floor method itself is suspect (a topic's central mass should
        # clear a background floor) — refuse to trust the run silently.
        canary_bad = sum(
            1 for l in eligible
            if l["floor_robust"] is not None
            and l["member_median_sim"] < l["floor_robust"])
        canary_frac = round(canary_bad / len(eligible), 3) if eligible else 0.0

        # fairness: language mix below-floor vs overall (eligible lanes)
        def _lang_mix(key: str) -> dict[str, int]:
            mix: dict[str, int] = {}
            for l in eligible:
                for lg in l[key]:
                    mix[lg] = mix.get(lg, 0) + 1
            return dict(sorted(mix.items(), key=lambda kv: -kv[1])[:12])
        fairness = {"below_floor": _lang_mix("below_langs"),
                    "all_members": _lang_mix("all_langs")}

        # receipts: worst 20 eligible lanes by robust junk fraction
        worst = sorted(eligible, key=lambda l: (-l["frac_robust"], -l["measured"]))[:20]
        receipt_ids: list[int] = []
        for l in worst:
            receipt_ids.extend(l["below_ids_robust"][:8])
        headlines = {}
        if receipt_ids:
            for r in await conn.fetch(_RECEIPT_HEADLINES_SQL, receipt_ids[:200]):
                headlines[r["id"]] = {
                    "headline": html.unescape(r["headline"] or "")[:140],
                    "lang": r["source_lang"], "source": r["source_name"]}
        receipts = []
        for l in worst:
            samples = [
                {"signal_id": sid, "sim": sim, **headlines.get(sid, {})}
                for sid, sim in zip(l["below_ids_robust"][:8],
                                    l["below_sims_robust"][:8])
                if sid in headlines
            ]
            receipts.append({
                "topic_id": l["topic_id"], "label": l["label"],
                "engine": l["engine"], "frac_robust": l["frac_robust"],
                "floor_robust": l["floor_robust"], "measured": l["measured"],
                "below_robust": l["below_robust"], "below_samples": samples,
            })

        # lane triage (knee + median-core guard)
        for l in lane_reports:
            l["class"] = (classify_lane(l["frac_robust"], knee)
                          if l["eligible"] else "ineligible")
        lane_classes = {
            eng: {
                cls: sum(1 for l in lane_reports
                         if l["engine"] == eng and l["class"] == cls)
                for cls in ("healthy", "prune", "centroid_divorced")
            }
            for eng in sorted({l["engine"] for l in lane_reports})
        }

        run = run_id_for(seed, dt.date.today())
        artifact = {
            "run_id": run,
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "params": {"sigmas": SIGMAS, "n_bg": N_BG, "seed": seed,
                       "min_bg": MIN_BG, "min_members_prune": MIN_MEMBERS_PRUNE,
                       "max_prune_frac": MAX_PRUNE_FRAC,
                       "durable_engine": DURABLE_ENGINE},
            "population": {
                "topics": len(ids),
                "lanes": len(lane_reports),
                "eligible_lanes": len(eligible),
                "members_measured": sum(l["measured"] for l in lane_reports),
                "members_missing_embedding": missing_embeddings,
                "quarantine_col_present": has_qcol,
            },
            "distribution_frac_robust": dist,
            "floor_robust_distribution": floor_dist,
            "canary_median_below_floor_frac": canary_frac,
            "knee_threshold": knee,
            "lane_classes": lane_classes,
            "centroid_divorced": [
                {"topic_id": l["topic_id"], "engine": l["engine"],
                 "label": l["label"], "frac_robust": l["frac_robust"],
                 "measured": l["measured"], "floor_robust": l["floor_robust"],
                 "member_median_sim": l["member_median_sim"]}
                for l in lane_reports if l["class"] == "centroid_divorced"
            ],
            "fairness_langs": fairness,
            "receipts": receipts,
            "lanes": [
                {k: v for k, v in l.items()
                 if k not in ("below_langs", "all_langs")}
                for l in lane_reports
            ],
        }
        if artifact_path:
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(json.dumps(artifact, indent=1))
            print(f"artifact -> {artifact_path}")

        # console summary
        print(f"\nlanes: {len(lane_reports)} ({len(eligible)} prune-eligible ≥{MIN_MEMBERS_PRUNE} members)")
        print(f"lane classes: {lane_classes}")
        print(f"junk-fraction (robust floor) distribution: {dist}")
        print(f"robust-floor distribution: {floor_dist}")
        print(f"CANARY lanes with median member below own floor: {canary_frac}"
              + ("  ⚠ FLOOR METHOD SUSPECT — do not prune from this run"
                 if canary_frac > 0.30 else ""))
        print(f"knee threshold: {knee}")
        qual = [l for l in eligible if knee is not None and l["frac_robust"] >= knee]
        by_engine: dict[str, int] = {}
        for l in qual:
            by_engine[l["engine"]] = by_engine.get(l["engine"], 0) + 1
        print(f"lanes at/above knee: {len(qual)} {by_engine}")
        print(f"\nWORST 20 (robust floor):")
        for l in worst:
            print(f"  dt-{l['topic_id']:>5} [{l['engine']:<10}] frac={l['frac_robust']:.3f} "
                  f"({l['below_robust']}/{l['measured']}) floor={l['floor_robust']} "
                  f"{(l['label'] or '')[:48]}")
        return artifact
    finally:
        await conn.close()


# ---------------------------------------------------------------- prune
async def run_write(artifact_path: Path, engines: set[str],
                    threshold: Optional[float], force_unsafe: bool) -> None:
    if _nightly_running() and not force_unsafe:
        print("REFUSING to write: run-scoped-snapshot.sh is running (hard rule: "
              "never touch a running M1 nightly). Re-run when it exits, or "
              "--force-unsafe if you are certain.", file=sys.stderr)
        sys.exit(3)
    artifact = json.loads(artifact_path.read_text())
    age_h = (dt.datetime.now(dt.timezone.utc)
             - dt.datetime.fromisoformat(artifact["generated_at"])).total_seconds() / 3600
    if age_h > 24:
        print(f"REFUSING: artifact is {age_h:.1f}h old (>24h) — re-audit first.",
              file=sys.stderr)
        sys.exit(3)
    thr = threshold if threshold is not None else artifact.get("knee_threshold")
    if thr is None:
        print("REFUSING: no knee threshold in artifact and none supplied.",
              file=sys.stderr)
        sys.exit(3)
    run = artifact["run_id"]
    # 'prune' class only: knee <= frac < MAX_PRUNE_FRAC. centroid_divorced
    # lanes (frac >= 0.5) are NEVER member-pruned — see classify_lane.
    lanes = [l for l in artifact["lanes"]
             if l["eligible"] and l["engine"] in engines
             and classify_lane(l["frac_robust"], thr) == "prune"
             and l["below_ids_robust"]]
    skipped_divorced = [l for l in artifact["lanes"]
                        if l["eligible"] and l["engine"] in engines
                        and classify_lane(l["frac_robust"], thr) == "centroid_divorced"]
    print(f"prune plan: run={run} threshold={thr} engines={sorted(engines)} "
          f"-> {len(lanes)} lanes, "
          f"{sum(len(l['below_ids_robust']) for l in lanes)} rows to quarantine")
    print(f"centroid-divorced lanes SKIPPED (topic-level surgery, not member "
          f"prune): {len(skipped_divorced)}")

    conn = await _connect()
    try:
        if (await conn.fetchval(_QUARANTINE_COL_SQL)) == 0:
            print("REFUSING: topic_members.quarantined missing — apply migration "
                  "087 first.", file=sys.stderr)
            sys.exit(3)
        total = 0
        for l in lanes:
            tid = f"dynamic-topic-{l['topic_id']}"
            floor = l["floor_robust"]
            for id_chunk in _chunks(l["below_ids_robust"], UPDATE_CHUNK):
                res = await conn.execute(
                    """UPDATE topic_members
                       SET quarantined = true,
                           quarantine_reason = $4,
                           quarantined_at = NOW()
                       WHERE topic_id = $1 AND role = 'evidence'
                         AND engine_version = $2 AND signal_id = ANY($3::bigint[])
                         AND quarantined IS NOT TRUE""",
                    tid, l["engine"], list(id_chunk),
                    f"{REASON_PREFIX} run={run} floor={floor}",
                )
                total += int(res.split()[-1])
            after = await conn.fetchval(
                """SELECT count(*) FROM topic_members
                   WHERE topic_id=$1 AND role='evidence' AND engine_version=$2
                     AND quarantined IS NOT TRUE""", tid, l["engine"])
            print(f"  dt-{l['topic_id']} [{l['engine']}] quarantined "
                  f"{len(l['below_ids_robust'])} -> serving evidence now {after} "
                  f"(was {l['measured']}) · junk_frac {l['frac_robust']:.3f} -> 0.000")
        print(f"\nTOTAL quarantined: {total} rows across {len(lanes)} lanes")
        print(f"REVERSAL: UPDATE topic_members SET quarantined=false, "
              f"quarantine_reason=NULL, quarantined_at=NULL "
              f"WHERE quarantine_reason LIKE '{REASON_PREFIX} run={run}%';")
    finally:
        await conn.close()


async def run_revert(run_id: str) -> None:
    conn = await _connect()
    try:
        res = await conn.execute(
            """UPDATE topic_members
               SET quarantined=false, quarantine_reason=NULL, quarantined_at=NULL
               WHERE quarantine_reason LIKE $1""",
            f"{REASON_PREFIX} run={run_id}%")
        print(f"reverted: {res}")
    finally:
        await conn.close()


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--artifact", type=Path, default=None,
                    help="artifact JSON path (default docs/research/topic-quality/<date>-blackhole-audit.json)")
    ap.add_argument("--write", action="store_true", help="apply the prune from the artifact")
    ap.add_argument("--engines", default=DURABLE_ENGINE,
                    help="comma-separated engine_versions to prune (default v1-compat; "
                         "unified-v2 is rebuilt nightly so flags there evaporate)")
    ap.add_argument("--threshold", type=float, default=None,
                    help="junk-fraction prune threshold (default: artifact knee)")
    ap.add_argument("--revert", metavar="RUN_ID", default=None)
    ap.add_argument("--force-unsafe", action="store_true", help=argparse.SUPPRESS)
    args = ap.parse_args()

    artifact_path = args.artifact or (
        ARTIFACT_DIR / f"{dt.date.today().isoformat()}-blackhole-audit.json")

    if args.revert:
        asyncio.run(run_revert(args.revert))
    elif args.write:
        asyncio.run(run_write(artifact_path, set(args.engines.split(",")),
                              args.threshold, args.force_unsafe))
    else:
        asyncio.run(run_audit(args.seed, artifact_path))


if __name__ == "__main__":
    main()
