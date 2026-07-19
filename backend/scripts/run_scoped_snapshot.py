"""R1 — scoped per-country emergent snapshot writer (#229).

R0 proved (read-only) that clustering WITHIN each country lifts recall ~5.4×
system-wide (~54× more narratives) vs a single global HDBSCAN pass. This is the
PRODUCTION version: it actually FORMS the scoped topics and writes them.

Reuses the proven snapshot pipeline verbatim (clean/dedupe → HDBSCAN → precision
gate → DeepSeek label → _write_snapshot) — the ONLY change vs
snapshot_emergent_topics.py is the pull is scoped per-country and every country's
clusters land under ONE shared snapshot_at with globally-unique cluster_ids, so
the existing project_dynamic_topics folds them into dynamic_topics with the #224
anchor-guard as one coherent snapshot (one lifecycle tick).

Writes emergent_clusters ONLY. Run project_dynamic_topics separately afterwards
(so the write can be inspected before it reaches serving). Reversible: it is a new
snapshot_at; reverting = re-project the prior snapshot.

WALL-TIME BUDGET + CHECKPOINT/RESUME (EXECUTE-1, 2026-07-19 — the failure-budget
philosophy extended to TIME). Forensics: HDBSCAN's brute O(n²·d) MST ran 7+
hours inside ONE country (US = 51% of the night's Σn²) on efficiency cores,
holding the heavy-job mutex (TTL 240min) all morning, and the all-at-end commit
meant killed runs banked NOTHING (07-17/18 lost whole nights). Now:

  - per-country budget (ATLAS_SNAPSHOT_COUNTRY_BUDGET_S, default 1800s): a
    country whose predicted cost exceeds it clusters its NEWEST fitting slice
    (fit over a self-calibrating n²/s rate, ATLAS_SNAPSHOT_N2_PER_SEC seed);
  - hard kill backstop: countries with n ≥ ATLAS_SNAPSHOT_SUBPROC_MIN_N
    cluster in a killable subprocess — timeout ⇒ one halved retry ⇒ honest
    TIME GAP (bounded worst case 1.5× the country budget, never 7h);
  - run budget (ATLAS_SNAPSHOT_RUN_BUDGET_MIN, default 150min): first-fit —
    a country that cannot fit the remaining budget is DEFERRED loudly (the
    smaller ones after it still run); on exhaustion the run STOPS and the
    snapshot stands with what completed;
  - incremental commit: every country's rows land in their own transaction —
    a killed run has banked all completed countries; widespread ERROR failure
    still discards via a compensating DELETE of this snapshot_at (time-gaps/
    deferrals never count against that error budget);
  - checkpoint/resume (ATLAS_SNAPSHOT_STATE_DIR): a crashed run within
    ATLAS_SNAPSHOT_RESUME_MAX_AGE_H (12h) resumes the SAME snapshot_at and
    skips banked countries; budget-stops mark the checkpoint complete (a
    deliberate partial commit is a finished run, not a crash);
  - rotation fairness: deferred/timed-out countries go FIRST next night.

  All knobs are env-reversible: budget 0 = off, state dir unset = stateless
  (exact pre-2026-07-19 behavior).

Run (repo root, M1 ML env, off-peak — heavy + DeepSeek labeling):
  # test first:
  python -m backend.scripts.run_scoped_snapshot --countries US,CN --dry-run
  python -m backend.scripts.run_scoped_snapshot --countries US,CN         # writes 2
  # then all:
  python -m backend.scripts.run_scoped_snapshot --min-embedded 100
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import asyncpg
import numpy as np

from backend.scripts.cluster_subproc import ClusterTimeout, run_cluster_in_subprocess
from backend.scripts.emergent_poc import (
    _apply_gate, _clean_and_dedupe, _cluster, _cluster_stats, _label_all, _load_gate,
    pca_reduce, whiten_all_but_top,
)
from backend.scripts.snapshot_budget import (
    BudgetContext,
    Checkpoint,
    CountryDeferred,
    CountryTimeGap,
    RateEstimator,
    empty_pass_is_benign,
    load_checkpoint,
    load_rotation,
    order_countries,
    plan_country,
    save_checkpoint,
    save_rotation,
    should_resume,
)
from backend.scripts.snapshot_emergent_topics import (
    SAMPLE_TOP_K,
    DEFAULT_GATE,
    _insert_prepared_snapshot,
    _prepare_snapshot_rows,
    _prior_snapshot_clusters,
)

_ID_OFFSET = 100000  # per-country cluster_id block (>> max clusters/country)

# Attempts per country before it counts as failed (transient Supabase
# connection drops on the heaviest fetches — US/EG class — killed three
# consecutive nightly passes via the all-or-nothing guard, 2026-07-13→16).
_COUNTRY_ATTEMPTS = 3

_COUNTRIES = """
    SELECT s.country_code, COUNT(*) AS n
    FROM signal_embeddings e JOIN signals_v2 s ON s.id = e.signal_id
    WHERE s.country_code IS NOT NULL AND s.country_code <> 'XX'
      AND s.timestamp > $1::timestamptz AND s.timestamp <= $2::timestamptz
      AND s.headline IS NOT NULL AND length(s.headline) >= 20
    GROUP BY s.country_code HAVING COUNT(*) >= $3
    ORDER BY n DESC
"""
# Keyset-paginated pull. The single-shot `se.vec::text` fetch of the biggest
# countries (US ~74k × 768-dim halfvec) exceeded statement_timeout='600s' under
# daytime contention and failed all 3 retries (2026-07-17): one statement had to
# scan+sort every row AND text-format 74k×768 floats (~9.5 KB/row). Two measured
# fixes, both here:
#   1. se.vec::real[] instead of ::text — asyncpg decodes float4[] in binary
#      (native, no _parse_vec float() loop) at ~1/3 the bytes and far cheaper
#      server-side formatting (measured 2.7× client-total on a US sample).
#   2. keyset pagination on (timestamp, id) — each statement is bounded to
#      _FETCH_PAGE_ROWS, so no single statement can approach the timeout no
#      matter the contention. Same corpus: (timestamp DESC, id DESC) is the
#      total order over the SAME rows the old timestamp-only pull returned; the
#      id tiebreak only makes ties deterministic (previously undefined).
_FETCH_PAGE = """
    SELECT s.id, s.headline, s.country_code, s.source_name, s.timestamp,
           se.vec::real[] AS emb
    FROM signal_embeddings se JOIN signals_v2 s ON s.id = se.signal_id
    WHERE s.country_code = $1
      AND s.timestamp > $2::timestamptz
      AND s.headline IS NOT NULL AND length(s.headline) >= 20
      AND (s.timestamp, s.id) < ($4::timestamptz, $5::bigint)
    ORDER BY s.timestamp DESC, s.id DESC
    LIMIT $3
"""

_FETCH_PAGE_ROWS = int(os.environ.get("ATLAS_SCOPED_FETCH_PAGE_ROWS", "15000") or "15000")
_MAX_BIGINT = (1 << 63) - 1  # keyset sentinel: first page has no cursor upper bound


async def _fetch_country_embeddings(conn, cc, hours, cap, page_rows,
                                    as_of: datetime | None = None):
    """Keyset-paginate the scoped pull so no single statement times out.

    Returns the same row set (id, headline, country_code, source_name, timestamp,
    emb) the old single-shot _FETCH did, in (timestamp DESC, id DESC) order, with
    `emb` a binary-decoded list[float] (not text). cap>0 stops after `cap` newest
    rows (old LIMIT NULLIF($3,0) semantics); cap<=0 traverses every eligible row.

    as_of (harness knob, --as-of): FREEZES the window to (as_of - hours,
    as_of] — the keyset cursor starts at as_of instead of the open sentinel,
    so a control/treatment dry-run pair launched with the same as_of pulls the
    IDENTICAL row set regardless of wall-clock drift between the two runs
    (the 27h window-shift confound of the 2026-07-18 whitening gold gate).
    None = live behavior, byte-identical.
    """
    out: list = []
    last_ts = as_of or datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    last_id = _MAX_BIGINT
    remaining = cap if cap and cap > 0 else None
    # Freeze the window's lower bound ONCE — NOW() re-evaluated per page made
    # the 168h cutoff slide forward during long paginated pulls (verify-gate
    # note, ~0.04% of window on a contended US pull; now exactly zero).
    cutoff = (as_of or datetime.now(timezone.utc)) - timedelta(hours=hours)
    while True:
        limit = page_rows if remaining is None else min(page_rows, remaining)
        if limit <= 0:
            break
        page = await conn.fetch(_FETCH_PAGE, cc, cutoff, limit, last_ts, last_id)
        if not page:
            break
        out.extend(page)
        if remaining is not None:
            remaining -= len(page)
            if remaining <= 0:
                break
        if len(page) < limit:
            break  # last (short) page
        tail = page[-1]
        last_ts, last_id = tail["timestamp"], int(tail["id"])
    return out


def _env_whiten_k() -> int:
    """ATLAS_CLUSTER_WHITEN_K → int; garbage/negative fall to 0 (off)."""
    try:
        k = int(os.environ.get("ATLAS_CLUSTER_WHITEN_K", "0"))
    except ValueError:
        return 0
    return k if k > 0 else 0


def _whiten_input(embs: np.ndarray, k: int) -> np.ndarray:
    """All-but-top(k) whitening for the HDBSCAN INPUT only.

    k=0 returns the SAME object (zero-cost, byte-identical default path).
    Whitening is a clustering-geometry lever (docs/research/recall-229/
    2026-07-16-whitening-recall-harness.md) — centroids, the precision gate
    and everything persisted stay in the RAW e5 space.
    """
    if k <= 0:
        return embs
    return whiten_all_but_top(embs, k)


def _env_pca_dim() -> int:
    """ATLAS_CLUSTER_PCA_DIM → int; garbage/negative fall to 0 (off)."""
    try:
        d = int(os.environ.get("ATLAS_CLUSTER_PCA_DIM", "0"))
    except ValueError:
        return 0
    return d if d > 0 else 0


def _pca_input(embs: np.ndarray, dim: int) -> np.ndarray:
    """Per-country PCA reduction of the HDBSCAN INPUT only (cost lever).

    dim=0 returns the SAME object (zero-cost, byte-identical default path).
    Applied AFTER any whitening — the composed input transform is
    _pca_input(_whiten_input(embs, k), dim). Like whitening, this touches
    ONLY the vectors HDBSCAN sees: centroids (_cluster_stats), the precision
    gate (_apply_gate) and everything persisted stay raw e5. The fit is per
    country (the batch IS the country) and re-fit each run — see
    emergent_poc.pca_reduce for the no-op guards and drift note.
    """
    if dim <= 0:
        return embs
    return pca_reduce(embs, dim)


def _env_int(name: str, default: int) -> int:
    """Garbage-tolerant env int (same contract as _env_whiten_k)."""
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    """Garbage-tolerant env float."""
    try:
        return float(os.environ.get(name, "") or default)
    except ValueError:
        return default


async def _country_clusters(conn, cc, hours, cap, mcs, ms, gate, min_kept, top_n,
                            whiten_k: int = 0, pca_dim: int = 0,
                            page_rows: int | None = None,
                            budget: BudgetContext | None = None,
                            report: dict | None = None,
                            as_of: datetime | None = None):
    """Scoped pull → (budget plan) → cluster → gate → top-N.

    Returns (clusters, embs, rows) or None. With a BudgetContext, the input
    may be CAPPED to its newest-first fitting slice (the pull is
    (timestamp DESC, id DESC) and _clean_and_dedupe preserves order, so
    rows[:n] is exactly "the newest n deduped signals"); raises
    CountryDeferred when planned out before clustering (run budget /
    below-floor) and CountryTimeGap when the hard-killed clustering budget is
    exhausted even after ONE halved retry. budget=None = exact legacy path.
    """
    recs = await _fetch_country_embeddings(conn, cc, hours, cap,
                                           page_rows or _FETCH_PAGE_ROWS,
                                           as_of=as_of)
    if len(recs) < mcs * 2:
        return None
    rows = _clean_and_dedupe([{k: r[k] for k in
                               ("id", "headline", "country_code", "source_name", "timestamp")}
                              for r in recs])
    if len(rows) < mcs * 2:
        return None
    n_eff = len(rows)
    plan = None
    if budget is not None:
        plan = plan_country(n_eff, remaining_run_s=budget.remaining_run_s,
                            country_budget_s=budget.country_budget_s,
                            rate=budget.rate.rate,
                            min_cluster_n=budget.min_cluster_n)
        if plan.action == "defer":
            raise CountryDeferred(plan.reason, n_eff)
        if plan.capped:
            rows = rows[: plan.n_use]  # newest-first slice (order preserved)
    # Materialize vectors ONLY for kept rows — the whole-country dict of
    # python float lists (US ≈ 100k × 768) was a multi-GB peak driver.
    needed = {int(r["id"]) for r in rows}
    emb_by_id = {i: r["emb"] for r in recs if (i := int(r["id"])) in needed}
    del recs
    embs = np.array([emb_by_id[int(r["id"])] for r in rows], dtype=np.float32)
    del emb_by_id

    cluster_input = _pca_input(_whiten_input(embs, whiten_k), pca_dim)
    hard_timeout = plan.hard_timeout_s if plan is not None else 0.0
    use_subproc = (budget is not None and budget.subproc_min_n > 0
                   and len(rows) >= budget.subproc_min_n)
    halved = False
    t0 = time.monotonic()
    if use_subproc:
        try:
            labels = run_cluster_in_subprocess(cluster_input, mcs, ms, "leaf",
                                               timeout_s=hard_timeout)
        except ClusterTimeout:
            # The rate model was optimistic — recalibrate pessimistically
            # (it ran ≥ hard_timeout without finishing) and retry ONCE at
            # half size (¼ the predicted cost) before declaring a time gap.
            budget.rate.update(len(rows), max(hard_timeout, 1.0) * 2)
            half = len(rows) // 2
            if half < budget.min_cluster_n:
                raise CountryTimeGap(
                    f"killed at {hard_timeout:.0f}s and half-slice {half} is "
                    f"below the {budget.min_cluster_n} floor") from None
            rows = rows[:half]
            embs = embs[:half]
            # NB: slice of the already-fitted transform (whiten/PCA fit on
            # the larger slice; acceptable — both default off, retry is rare).
            cluster_input = cluster_input[:half]
            halved = True
            t0 = time.monotonic()
            try:
                labels = run_cluster_in_subprocess(cluster_input, mcs, ms,
                                                   "leaf", timeout_s=hard_timeout)
            except ClusterTimeout:
                budget.rate.update(len(rows), max(hard_timeout, 1.0) * 2)
                raise CountryTimeGap(
                    f"killed twice at the {hard_timeout:.0f}s hard budget "
                    f"(n={len(rows)} after halving) — honest time gap") from None
    else:
        labels = _cluster(cluster_input, mcs, ms, "leaf")
    dt = time.monotonic() - t0
    if budget is not None:
        budget.rate.update(len(rows), dt)  # self-calibration (EMA, clamped)
    if report is not None:
        report.update({
            "n_eff": n_eff, "n_use": len(rows),
            "capped": bool(plan.capped) if plan is not None else False,
            "halved": halved, "subproc": use_subproc,
            "cluster_seconds": round(dt, 1),
            "input_dim": int(cluster_input.shape[1]),
            "hard_timeout_s": round(hard_timeout),
        })

    all_clusters = _cluster_stats(labels, embs, rows, top_k=SAMPLE_TOP_K)
    if not all_clusters:
        return None
    gated = _apply_gate(all_clusters, embs, gate, min_kept, top_k=SAMPLE_TOP_K)
    clusters = gated if top_n <= 0 else gated[:top_n]
    if not clusters:
        return None
    return clusters, embs, rows


async def _commit_country(conn, db, prepared):
    """Bank ONE country's prepared rows in their own transaction (incremental
    commit, 2026-07-19), retrying once from a fresh connection on a transient
    failure. Returns the (possibly reconnected) connection.

    NB: if a commit lands but its ack is lost, the retry can duplicate one
    country's clusters within this snapshot — projection's centroid matching
    folds them into one identity; strictly better than losing the night."""
    for attempt in (1, 2):
        try:
            if conn.is_closed():
                conn = await asyncpg.connect(db)
                await conn.execute("SET statement_timeout = '600s'")
            async with conn.transaction():
                await _insert_prepared_snapshot(conn, prepared)
            return conn
        except Exception as ex:
            try:
                if not conn.is_closed():
                    await conn.close()
            except Exception:
                pass
            if attempt == 2:
                raise
            print(f"  country commit failed ({ex}) — retrying from a fresh "
                  f"connection", file=sys.stderr, flush=True)
            await asyncio.sleep(3)
    return conn


async def main() -> None:
    ap = argparse.ArgumentParser(description="R1: scoped per-country snapshot writer.")
    ap.add_argument("--hours", type=int, default=168)
    ap.add_argument("--min-embedded", type=int, default=100)
    ap.add_argument("--per-country-cap", type=int, default=0,
                    help="operational diagnostic ceiling; 0 traverses every eligible signal")
    ap.add_argument("--top-per-country", type=int, default=0,
                    help="operational diagnostic ceiling; 0 keeps every gated cluster")
    ap.add_argument("--mcs", type=int, default=5)
    ap.add_argument("--ms", type=int, default=2)
    ap.add_argument("--min-kept", type=int, default=8)
    ap.add_argument("--gate", default=str(DEFAULT_GATE))
    ap.add_argument("--countries", default="", help="comma list to restrict (test)")
    ap.add_argument("--limit-countries", type=int, default=0, help="only first N (test)")
    ap.add_argument("--skip-label", action="store_true", help="headline fallback labels")
    ap.add_argument("--dry-run", action="store_true", help="no INSERT")
    ap.add_argument("--whiten-k", type=int, default=_env_whiten_k(),
                    help="all-but-top(k) whitening of the HDBSCAN input "
                         "(env ATLAS_CLUSTER_WHITEN_K; 0 = off, byte-identical)")
    ap.add_argument("--pca-dim", type=int, default=_env_pca_dim(),
                    help="per-country PCA reduction of the HDBSCAN input to this "
                         "many dims, applied AFTER any whitening (env "
                         "ATLAS_CLUSTER_PCA_DIM; 0 = off, byte-identical). Cost "
                         "lever: brute HDBSCAN is O(n²·d), 768→128 ≈ 6× cheaper")
    ap.add_argument("--as-of", default="",
                    help="ISO timestamp freezing the window to (as_of - hours, "
                         "as_of] and stamping snapshot_at — harness knob so a "
                         "control/treatment dry-run pair sees the IDENTICAL "
                         "corpus (empty = live NOW, byte-identical)")
    ap.add_argument("--dump-json", default="",
                    help="write per-country cluster payloads (members, cohesion, "
                         "gate verdicts) to this path — diagnostic, works with --dry-run")
    # EXECUTE-1 (2026-07-19) wall-time budget + checkpoint knobs. Env-reversible:
    # 0 = that budget off; state dir unset = stateless (pre-07-19 behavior).
    ap.add_argument("--run-budget-min", type=float,
                    default=_env_float("ATLAS_SNAPSHOT_RUN_BUDGET_MIN", 150.0),
                    help="whole-pass wall budget in minutes; on exhaustion the run "
                         "STOPS, commits what completed and defers the rest loudly "
                         "(0 = unlimited; mutex TTL is 240min — stay well under)")
    ap.add_argument("--country-budget-s", type=float,
                    default=_env_float("ATLAS_SNAPSHOT_COUNTRY_BUDGET_S", 1800.0),
                    help="per-country clustering wall budget in seconds; a country "
                         "predicted over it clusters its NEWEST fitting slice "
                         "(0 = unlimited)")
    ap.add_argument("--rate-n2-per-s", type=float,
                    default=_env_float("ATLAS_SNAPSHOT_N2_PER_SEC", 300000.0),
                    help="initial clustering-rate estimate in n²-units/s (forensics "
                         "2026-07-19: ~320-347k at nice-10 on efficiency cores); "
                         "self-calibrates from measured countries within the run")
    ap.add_argument("--subproc-min-n", type=int,
                    default=_env_int("ATLAS_SNAPSHOT_SUBPROC_MIN_N", 12000),
                    help="countries with clustering input >= this run in a "
                         "hard-killable subprocess (0 = never isolate)")
    ap.add_argument("--cap-floor-n", type=int,
                    default=_env_int("ATLAS_SNAPSHOT_CAP_FLOOR_N", 4000),
                    help="never cap the clustering input below this — defer the "
                         "country instead of clustering a garbage sliver")
    ap.add_argument("--state-dir",
                    default=os.environ.get("ATLAS_SNAPSHOT_STATE_DIR", ""),
                    help="dir for checkpoint/rotation files (unset = stateless)")
    ap.add_argument("--resume", choices=["auto", "off"],
                    default=(os.environ.get("ATLAS_SNAPSHOT_RESUME", "auto")
                             or "auto"),
                    help="auto = a fresh crashed checkpoint of the same window "
                         "resumes its snapshot_at, skipping banked countries")
    ap.add_argument("--resume-max-age-h", type=float,
                    default=_env_float("ATLAS_SNAPSHOT_RESUME_MAX_AGE_H", 12.0))
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL not set", file=sys.stderr); sys.exit(2)
    ds_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not ds_key and not args.skip_label:
        print("DEEPSEEK_API_KEY not set (or --skip-label)", file=sys.stderr); sys.exit(2)
    gate = _load_gate(Path(args.gate))

    # SIGTERM (watchdog / operator kill) unwinds as SystemExit so finally
    # blocks run: cluster_subproc's finally kills any live clustering child
    # (no orphan MST burning the M1 for hours) and committed countries stand
    # for the resume.
    try:
        signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    except ValueError:  # non-main thread (tests) — fine without a handler
        pass

    as_of: datetime | None = None
    if args.as_of:
        try:
            as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        except ValueError:
            print(f"--as-of not ISO: {args.as_of!r}", file=sys.stderr); sys.exit(2)
        if as_of.tzinfo is None:
            as_of = as_of.replace(tzinfo=timezone.utc)

    snapshot_at = as_of or datetime.now(timezone.utc)
    t0 = time.time()
    t_mono = time.monotonic()
    run_budget_s = args.run_budget_min * 60.0 if args.run_budget_min > 0 else 0.0
    budget_enabled = args.country_budget_s > 0 or run_budget_s > 0
    rate_est = RateEstimator(initial=args.rate_n2_per_s)

    # Checkpoint/rotation only for full unattended passes — never for
    # --countries test slices, dry runs (a dry run must leave no state a
    # real run could resume) or frozen-window harness runs (--as-of).
    checkpoint_path = rotation_path = None
    if args.state_dir and not args.dry_run and not args.countries and as_of is None:
        sdir = Path(args.state_dir)
        try:
            sdir.mkdir(parents=True, exist_ok=True)
            checkpoint_path = sdir / "scoped-snapshot-checkpoint.json"
            rotation_path = sdir / "scoped-snapshot-rotation.json"
        except OSError as ex:
            print(f"state dir unusable ({ex}) — running stateless", file=sys.stderr)

    # prev_ck is kept even when not resuming: the empty-pass guard below needs
    # to know whether a PREVIOUS cycle recently banked a snapshot (the benign
    # "nothing left to do" case must not be mistaken for a misconfig).
    prev_ck = load_checkpoint(checkpoint_path) if checkpoint_path is not None else None
    resumed = None
    if prev_ck is not None and args.resume != "off":
        if should_resume(prev_ck, now=snapshot_at,
                         hours=args.hours,
                         max_age_h=args.resume_max_age_h):
            resumed = prev_ck
            snapshot_at = datetime.fromisoformat(prev_ck.snapshot_at)
    ck = resumed or Checkpoint(snapshot_at=snapshot_at.isoformat(),
                               hours=args.hours,
                               started_at=datetime.now(timezone.utc).isoformat(),
                               next_base=0)

    conn = await asyncpg.connect(db)
    await conn.execute("SET statement_timeout = '600s'")
    try:
        if args.countries:
            ccs = [c.strip().upper() for c in args.countries.split(",") if c.strip()]
        else:
            # anchor = as_of (frozen harness window) or live NOW; the far-future
            # sentinel keeps the default upper bound open, byte-identical with
            # the old `> NOW() - hours` (no upper-bound) semantics.
            anchor = as_of or datetime.now(timezone.utc)
            upper = as_of or datetime(9999, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
            rows = await conn.fetch(_COUNTRIES,
                                    anchor - timedelta(hours=args.hours),
                                    upper, args.min_embedded)
            ccs = [r["country_code"] for r in rows]
            if args.limit_countries:
                ccs = ccs[: args.limit_countries]
            if rotation_path is not None:
                pri = load_rotation(rotation_path)
                if pri:
                    # Rotation fairness: last pass's deferred/timed-out go FIRST
                    # so first-fit deferral never chronically starves them.
                    ccs = order_countries(ccs, pri)
                    print(f"rotation priority (deferred/timed-out last pass): "
                          f"{', '.join(pri)}", file=sys.stderr)
        if resumed is not None:
            skip = set(ck.done)
            ccs = [c for c in ccs if c not in skip]
            print(f"RESUMING snapshot {snapshot_at.isoformat()} — {len(skip)} "
                  f"countries already banked, {len(ccs)} to go (run started "
                  f"{ck.started_at})", file=sys.stderr, flush=True)
        # NB: with an adopted (resumed) snapshot_at, `< $1` still lands on the
        # true prior snapshot — this run's own committed rows are excluded.
        prior = await _prior_snapshot_clusters(conn, snapshot_at)
        scope = "all gated clusters" if args.top_per_country <= 0 else (
            f"top{args.top_per_country}/country"
        )
        corpus = "all eligible signals" if args.per_country_cap <= 0 else (
            f"latest {args.per_country_cap}/country"
        )
        print(f"snapshot_at={snapshot_at.isoformat()} · {len(ccs)} countries · "
              f"{scope} · {corpus} · dry_run={args.dry_run} · "
              f"whiten_k={args.whiten_k} · pca_dim={args.pca_dim}"
              f"{' · FROZEN WINDOW (as-of)' if as_of else ''}", file=sys.stderr)
        if budget_enabled:
            print(f"time budget: run={args.run_budget_min:.0f}min · "
                  f"country={args.country_budget_s:.0f}s · "
                  f"rate0={rate_est.rate:.0f} n²/s · "
                  f"subproc_n>={args.subproc_min_n} · "
                  f"cap_floor={args.cap_floor_n} · "
                  f"checkpoint={'on' if checkpoint_path else 'off'}",
                  file=sys.stderr)

        total_written = total_clusters = done = failed = 0
        failed_ccs: list[str] = []
        deferred_ccs: list[str] = []
        timegap_ccs: list[str] = []
        processed = 0  # countries that finished (clusters or honest no-clusters)
        dump_countries: list[dict] = []
        base = ck.next_base
        for pos, cc in enumerate(ccs):
            done += 1
            remaining = None
            if run_budget_s > 0:
                remaining = run_budget_s - (time.monotonic() - t_mono)
                if remaining <= 0:
                    rest = ccs[pos:]
                    deferred_ccs.extend(rest)
                    print(f"  RUN BUDGET {args.run_budget_min:.0f}min exhausted — "
                          f"deferring {len(rest)} countries "
                          f"({', '.join(rest[:12])}{', …' if len(rest) > 12 else ''}); "
                          f"committing what completed", file=sys.stderr, flush=True)
                    break
            bctx = BudgetContext(country_budget_s=args.country_budget_s,
                                 remaining_run_s=remaining,
                                 rate=rate_est,
                                 min_cluster_n=args.cap_floor_n,
                                 subproc_min_n=args.subproc_min_n) \
                if budget_enabled else None
            # Resilience for the unattended run: a single transient connection
            # blip must not discard the country (the all-or-nothing guard below
            # is for PERSISTENT failures). Each country gets up to 3 attempts;
            # every retry starts from a fresh connection because "connection
            # was closed in the middle of operation" leaves the old one
            # unusable. Budget outcomes (defer/time-gap) are deterministic and
            # are NEVER retried.
            res = None
            last_ex: Exception | None = None
            report: dict = {}
            try:
                for attempt in range(1, _COUNTRY_ATTEMPTS + 1):
                    if conn.is_closed():
                        conn = await asyncpg.connect(db)
                        await conn.execute("SET statement_timeout = '600s'")
                    try:
                        res = await _country_clusters(conn, cc, args.hours,
                                                      args.per_country_cap,
                                                      args.mcs, args.ms, gate,
                                                      args.min_kept,
                                                      args.top_per_country,
                                                      whiten_k=args.whiten_k,
                                                      pca_dim=args.pca_dim,
                                                      budget=bctx, report=report,
                                                      as_of=as_of)
                        last_ex = None
                        break
                    except (CountryDeferred, CountryTimeGap):
                        raise
                    except Exception as ex:
                        last_ex = ex
                        try:
                            if not conn.is_closed():
                                await conn.close()  # retry from a clean connection
                        except Exception:
                            pass
                        if attempt < _COUNTRY_ATTEMPTS:
                            print(f"  [{done}/{len(ccs)}] {cc}: attempt {attempt} "
                                  f"failed ({ex}) — retrying",
                                  file=sys.stderr, flush=True)
                            await asyncio.sleep(5 * attempt)
            except CountryDeferred as d:
                deferred_ccs.append(cc)
                print(f"  [{done}/{len(ccs)}] {cc}: DEFERRED ({d.reason}, "
                      f"n={d.n_eff}) — rotation priority next pass",
                      file=sys.stderr, flush=True)
                if args.dump_json:
                    dump_countries.append({"country": cc, "deferred": d.reason,
                                           "clusters": []})
                continue
            except CountryTimeGap as tg:
                timegap_ccs.append(cc)
                print(f"  [{done}/{len(ccs)}] {cc}: TIME GAP — {tg}; rotation "
                      f"priority next pass", file=sys.stderr, flush=True)
                if args.dump_json:
                    dump_countries.append({"country": cc, "time_gap": str(tg),
                                           "clusters": []})
                continue
            if last_ex is not None:
                failed += 1
                failed_ccs.append(cc)
                print(f"  [{done}/{len(ccs)}] {cc}: FETCH/CLUSTER failed after "
                      f"{_COUNTRY_ATTEMPTS} attempts ({last_ex})",
                      file=sys.stderr, flush=True)
                if args.dump_json:
                    dump_countries.append({"country": cc, "error": str(last_ex),
                                           "clusters": []})
                continue
            if res is None:
                print(f"  [{done}/{len(ccs)}] {cc}: no gated clusters", file=sys.stderr, flush=True)
                if args.dump_json:
                    # cluster_seconds present when HDBSCAN actually ran (the
                    # gate kept nothing) — the speed harness sums it; None on
                    # the too-few-rows early returns.
                    dump_countries.append({
                        "country": cc, "clusters": [],
                        "n_signals": report.get("n_use"),
                        "cluster_seconds": report.get("cluster_seconds"),
                        "input_dim": report.get("input_dim"),
                    })
                base += _ID_OFFSET
                processed += 1
                if checkpoint_path is not None:
                    ck.done[cc] = "no_clusters"
                    ck.next_base = base
                    save_checkpoint(checkpoint_path, ck)
                continue
            clusters, embs, rows = res
            for i, c in enumerate(clusters):
                c["cluster_id"] = base + i
            base += _ID_OFFSET
            if args.skip_label:
                ds_labels = [{"label": (rows[c["top_signal_idxs"][0]]["headline"] or cc)[:90],
                              "description": "", "confidence": 0.0} for c in clusters]
            else:
                ds_labels = await _label_all(clusters, rows, ds_key)
            total_clusters += len(clusters)
            prepared = _prepare_snapshot_rows(
                snapshot_at=snapshot_at,
                window_hours=args.hours,
                clusters=clusters,
                ds_labels=ds_labels,
                embs=embs,
                rows=rows,
                prior=prior,
                gate_threshold=gate["_threshold"],
            )
            # INCREMENTAL COMMIT (2026-07-19): bank each completed country in
            # its own transaction so a killed run keeps everything finished
            # (07-17/18 lost whole nights to the all-at-end commit). The
            # widespread-error case still rolls back whole via the
            # compensating DELETE below. Mid-run visibility of a partial
            # snapshot_at is bounded: projection (serving) runs only after
            # this script exits successfully.
            if not args.dry_run and prepared:
                conn = await _commit_country(conn, db, prepared)
                total_written += len(prepared)
            processed += 1
            lbls = ", ".join((d.get("label") or "?")[:24] for d in ds_labels[:2])
            capnote = ""
            if report.get("capped") or report.get("halved"):
                capnote = (f" · TIME-CAPPED {report['n_use']}/{report['n_eff']}"
                           + (" (halved)" if report.get("halved") else ""))
            if report.get("cluster_seconds", 0) >= 60:
                capnote += f" · cluster {report['cluster_seconds']:.0f}s"
            print(f"  [{done}/{len(ccs)}] {cc}: n={len(rows)} clusters={len(clusters)} "
                  f"e.g. [{lbls}]{capnote}", file=sys.stderr, flush=True)
            if checkpoint_path is not None:
                # Saved AFTER the commit: a crash inside the tiny window
                # between them re-does one country on resume (projection folds
                # the duplicate by centroid); the reverse order would silently
                # LOSE a country, which is worse.
                ck.done[cc] = "ok"
                ck.next_base = base
                save_checkpoint(checkpoint_path, ck)
            if args.dump_json:
                dump_countries.append({
                    "country": cc,
                    "n_signals": len(rows),
                    "cluster_seconds": report.get("cluster_seconds"),
                    "input_dim": report.get("input_dim"),
                    "time_capped": bool(report.get("capped")
                                        or report.get("halved")),
                    "clusters": [{
                        "cluster_id": int(c["cluster_id"]),
                        "label": (dl.get("label") or "")[:120],
                        "raw_size": c.get("raw_size"),
                        "kept_size": c.get("kept_size"),
                        "kept_ratio": c.get("kept_ratio"),
                        "gate_threshold": c.get("gate_threshold"),
                        "cohesion": c.get("cohesion"),
                        "members": [
                            {"signal_id": int(rows[i]["id"]),
                             "headline": rows[i]["headline"]}
                            for i in c.get("kept_idxs", c["all_idxs"])
                        ],
                    } for c, dl in zip(clusters, ds_labels)],
                })

        if args.dump_json:
            payload = {
                "meta": {
                    "snapshot_at": snapshot_at.isoformat(),
                    "hours": args.hours,
                    "whiten_k": args.whiten_k,
                    "pca_dim": args.pca_dim,
                    "as_of": args.as_of or None,
                    "mcs": args.mcs, "ms": args.ms, "min_kept": args.min_kept,
                    "dry_run": args.dry_run,
                    "countries_attempted": len(ccs),
                    "failed": failed,
                    "deferred": len(deferred_ccs),
                    "time_gaps": len(timegap_ccs),
                    "elapsed_s": round(time.time() - t0),
                },
                "countries": dump_countries,
            }
            out = Path(args.dump_json)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            print(f"dump written: {out} ({len(dump_countries)} countries)",
                  file=sys.stderr, flush=True)

        if failed:
            # One persistently-failing country must not freeze the whole
            # substrate (2026-07-13→16: a single dropped connection discarded
            # three consecutive nightly snapshots and the served threads went
            # stale for days). Budget: a handful of ERROR gaps commit WITH a
            # loud ledger — the missing countries' topics age one lifecycle
            # tick and resurrect on the next pass. Widespread ERROR failure
            # still discards — now via a compensating DELETE, because
            # completed countries were committed incrementally. Time-gaps and
            # deferrals are DELIBERATE bounded outcomes and never count here.
            budget = max(2, len(ccs) // 50)
            if failed > budget:
                if not args.dry_run:
                    if conn.is_closed():
                        conn = await asyncpg.connect(db)
                        await conn.execute("SET statement_timeout = '600s'")
                    await conn.execute(
                        "DELETE FROM emergent_clusters WHERE snapshot_at = $1",
                        snapshot_at)
                if checkpoint_path is not None:
                    checkpoint_path.unlink(missing_ok=True)
                raise RuntimeError(
                    f"incomplete country pass: {failed}/{len(ccs)} countries "
                    f"FAILED (error budget {budget}); this snapshot's rows "
                    f"deleted (compensating rollback)"
                )
            print(f"  SNAPSHOT COMMITTED WITH GAPS: {failed}/{len(ccs)} countries "
                  f"missing{' (' + ', '.join(failed_ccs) + ')' if failed_ccs else ''} "
                  f"— within budget {budget}; their topics age one cycle and "
                  f"resurrect next pass", file=sys.stderr, flush=True)
        if timegap_ccs or deferred_ccs:
            dshow = ", ".join(deferred_ccs[:20]) + (", …" if len(deferred_ccs) > 20 else "")
            print(f"  TIME LEDGER: {len(timegap_ccs)} time-gap(s)"
                  f"{' (' + ', '.join(timegap_ccs) + ')' if timegap_ccs else ''} · "
                  f"{len(deferred_ccs)} deferred"
                  f"{' (' + dshow + ')' if deferred_ccs else ''} — committed what "
                  f"completed; these age one cycle, resurrect on the next pass, "
                  f"and take rotation priority", file=sys.stderr, flush=True)
        if processed == 0 and (deferred_ccs or timegap_ccs):
            # An all-deferred pass is BENIGN when a fresh banked snapshot
            # already exists (this run resumed one, or the previous cycle just
            # completed one — e.g. a re-fire immediately after a complete
            # cycle): exit 0 so the runner still projects + SEALS the daily
            # edition from the fresh snapshot. It is a true misconfig ONLY
            # when nothing fresh is banked anywhere — the budget cannot fit
            # ANY country from a cold start (2026-07-17→19: the old
            # unconditional exit 1 skipped every post-step and the sealed
            # edition starved 47h while snapshots were fresh).
            if empty_pass_is_benign(ck, prev_ck,
                                    now=datetime.now(timezone.utc),
                                    max_age_h=args.resume_max_age_h):
                src = ck if ck.done else prev_ck
                print(f"  NOTHING COMPLETED this pass (all deferred/"
                      f"time-gapped) — benign: snapshot {src.snapshot_at} "
                      f"already banked {len(src.done)} countries; exiting 0 "
                      f"so projection and the daily seal run on the fresh "
                      f"snapshot", file=sys.stderr, flush=True)
            else:
                if checkpoint_path is not None:
                    checkpoint_path.unlink(missing_ok=True)
                print("NO countries completed within the time budget and no "
                      "fresh banked snapshot exists — misconfig (budget too "
                      "small to fit ANY country); check the ATLAS_SNAPSHOT_* "
                      "knobs; exiting nonzero so projection is skipped",
                      file=sys.stderr, flush=True)
                sys.exit(1)
        if checkpoint_path is not None and ck.done:
            # Budget-stop or full pass = a FINISHED run (deliberate partial
            # commit) — only crashes leave complete=False for the resume.
            # `ck.done` guard: a pass that banked NOTHING must not clobber
            # the previous cycle's checkpoint — that file is the durable
            # record that a fresh banked snapshot exists (the benign-empty
            # classification above depends on it).
            ck.complete = True
            save_checkpoint(checkpoint_path, ck)
        if rotation_path is not None:
            save_rotation(rotation_path, deferred_ccs + timegap_ccs)
    finally:
        await conn.close()

    print(f"\nR1 DONE: snapshot_at={snapshot_at.isoformat()} · {total_clusters} clusters "
          f"formed, {total_written} written{' (DRY)' if args.dry_run else ''} · "
          f"{failed} failed · {len(timegap_ccs)} time-gap(s) · "
          f"{len(deferred_ccs)} deferred · {round(time.time()-t0)}s")
    if not args.dry_run and total_written:
        print("NEXT: run project_dynamic_topics to fold this snapshot into dynamic_topics "
              "(then it serves). Inspect emergent_clusters for this snapshot_at first.")


if __name__ == "__main__":
    asyncio.run(main())
