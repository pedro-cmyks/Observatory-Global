"""`POST /api/v3/query` — the Atlas Query Protocol (slice 1).

Spec: `docs/superpowers/specs/2026-08-14-atlas-query-protocol-design.md`.
Verbs, caps, budgets and the honesty envelope live in
`app.services.query_verbs`; this module is the transport and the bounded
execution.

    { "ask": [ { "identities_covering": { "terms": ["earthquake","terremoto"],
                                          "country": "CO",
                                          "window_days": 7 } } ] }

FOUR VERBS, each mapping to a measurement Atlas already makes:

  identities_covering  which identities cover this event (two bases: member
                       signals and topic label, tagged per identity)
  receipt_geography    the country / language / outlet-origin distribution of
                       one topic's evidence members
  unclustered_signals  what was ingested and never became a story, plus where
                       the assigned ones landed
  voice_mix            reuses `services/voice_mix` (country) and
                       `services/thread_voice` (topic) verbatim

WHY A SEPARATE RATE-LIMIT BUCKET. The instruction was to ride W4's `read`
bucket unless a verb measures heavier than `read`'s justification. It does, so
it gets its own — and here is the arithmetic, in the same form `rate_limit.py`
states its own.

`read` is justified at 90 requests / 300s against a measured ~1.0s per call:
90 x 1.0s = 90 connection-seconds per window, ~0.3 of one connection from a
pool of 10. A query request is a different animal: it can carry up to
MAX_VERBS_PER_REQUEST (4) verbs, each running up to three bounded lanes, under
a 15s global deadline. Measured warm on prod 2026-08-14 a single verb lands at
0.3-1.5s, but the binding number for a bucket is the worst case it permits,
and that is the 15s deadline — 15x the per-call cost `read` was sized around.

At 20 requests / 300s: worst case 20 x 15s = 300 connection-seconds per
window (1.0 sustained connection, 10% of the pool from one IP); typical
20 x ~2s = 40 connection-seconds, comfortably under `read`'s 90. Twenty
queries per five minutes is also generous against the actual workload: the
investigation that motivated this protocol answered the whole Colombia
question in about six.

Note this bucket is sized by CONNECTION-SECONDS, not by spend — no verb calls
an LLM or an external service. It happens to share `paid`'s numbers for an
entirely different reason.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app import db
from app.services import query_verbs as qv
from app.services import thread_voice
from app.services.focus_lanes import POOL_ACQUIRE_TIMEOUT_S, LaneRunner

router = APIRouter(tags=["query"])
logger = logging.getLogger(__name__)


@router.post("/api/v3/query")
async def post_query(payload: dict = Body(...)):
    started = time.monotonic()
    try:
        ask = qv.validate_ask((payload or {}).get("ask"))
    except qv.VerbError as exc:
        return _error(exc)

    if db.pool is None:
        return JSONResponse(
            _envelope([
                qv.degraded_result(verb, "no_pool") for verb, _ in ask
            ], degraded=True),
            status_code=200,
        )

    # `voice_mix {country}` reuses the served `/api/v2/voice-mix` function,
    # which acquires its OWN pool connection. Running it while this handler
    # holds one is self-inflicted contention: measured locally 2026-08-14, the
    # country lane degraded (db_busy) inside the protocol while the same call
    # direct to the endpoint succeeded in 2.1s against its own 2.5s budget.
    # So those verbs are deferred until after the connection is released, and
    # results are reassembled in the order they were asked.
    results: list[Optional[dict]] = [None] * len(ask)
    deferred: list[int] = []
    oldest: Optional[datetime] = None

    try:
        async with _acquire() as conn:
            runner = LaneRunner(
                conn,
                deadline_ms=qv.QUERY_DEADLINE_MS,
                started_at=started,
                budgets=qv.LANE_BUDGETS_MS,
            )
            # One retention probe per request, shared by every verb's window
            # block. Cheap (MIN over an indexed column) and it is what turns a
            # window from a claim into a measurement.
            oldest = await _hot_retention(runner)

            for i, (verb, args) in enumerate(ask):
                if _defers_to_own_connection(verb, args):
                    deferred.append(i)
                    continue
                results[i] = await _guarded(verb, args, runner, conn, oldest)
    except TimeoutError:
        logger.warning("query protocol could not acquire a connection in %.1fs",
                       POOL_ACQUIRE_TIMEOUT_S)
        return JSONResponse(
            _envelope([qv.degraded_result(v, "db_busy") for v, _ in ask], degraded=True),
            status_code=200,
        )

    # The connection is released here; the deferred verbs acquire their own.
    for i in deferred:
        verb, args = ask[i]
        results[i] = await _guarded(verb, args, None, None, oldest)

    return _envelope([r for r in results if r is not None],
                     elapsed_ms=(time.monotonic() - started) * 1000.0)


def _defers_to_own_connection(verb: str, args: dict) -> bool:
    """True for verbs that reuse a served endpoint function (own connection)."""
    return verb == "voice_mix" and bool(str(args.get("country") or "").strip())


async def _guarded(verb: str, args: dict, runner: Optional[LaneRunner],
                   conn: Any, oldest: Optional[datetime]) -> dict:
    try:
        return await _run_verb(verb, args, runner, conn, oldest)
    except qv.VerbError as exc:
        return {
            "contract": qv.VERB_CONTRACT, "verb": verb,
            "status": qv.STATUS_DEGRADED, "reason": exc.reason,
            "detail": exc.detail,
        }


# ------------------------------------------------------------------ verbs

async def _run_verb(verb: str, args: dict, runner: Optional[LaneRunner],
                    conn: Any, oldest: Optional[datetime]) -> dict:
    if verb == "identities_covering":
        return await _identities_covering(args, runner, oldest)
    if verb == "receipt_geography":
        return await _receipt_geography(args, runner, oldest)
    if verb == "unclustered_signals":
        return await _unclustered_signals(args, runner, oldest)
    if verb == "voice_mix":
        return await _voice_mix(args, runner, conn, oldest)
    raise qv.VerbError("unknown_verb", f"unknown verb '{verb}'")  # pragma: no cover


async def _identities_covering(args: dict, runner: LaneRunner,
                               oldest: Optional[datetime]) -> dict:
    terms = args.get("terms") or args.get("event_terms") or []
    needles, rejected = qv.normalize_terms(terms, require_one=True)
    country = qv.validate_country(args.get("country"))
    states = qv.validate_states(args.get("states"))
    hours = _window_hours(args, default_days=7)

    could_not: list[dict] = []

    member_sql, member_params = qv.identities_covering_member_sql(
        needles, country=country, hours=hours)
    member_rows = await runner.run("identities_members", member_sql, *member_params)

    label_sql, label_params = qv.identities_covering_label_sql(
        needles, country=country, states=states)
    label_rows = await runner.run("identities_labels", label_sql, *label_params)

    if not runner.is_live("identities_members"):
        could_not.append({
            "what": "identities whose member signals match the terms",
            "reason": runner.reasons.get("identities_members", "db_error"),
        })
    if not runner.is_live("identities_labels"):
        could_not.append({
            "what": "identities whose label matches the terms",
            "reason": runner.reasons.get("identities_labels", "db_error"),
        })
    if country:
        could_not.append({
            "what": f"country scope on the label basis (country={country})",
            "reason": "no_country_dimension",
            "detail": "dynamic_topics carries no country column, so the label "
                      "basis is global; only the member basis is country-scoped",
        })
    # Member matching can only see signals still in hot retention, but an
    # identity outlives its receipts. Saying so is the difference between
    # "this topic has no matching members" and "its receipts aged out".
    could_not.append({
        "what": "member matches for signals older than hot retention",
        "reason": "hot_retention_only",
        "detail": "the member basis scans signals_v2, which holds roughly the "
                  "last week; identities older than that can still appear via "
                  "the label basis but with matched_members understated",
    })

    merged = qv.summarize_identities(
        [dict(r) for r in member_rows], [dict(r) for r in label_rows])

    out = qv.result_envelope(
        verb="identities_covering",
        window=qv.window_block(requested_hours=hours, oldest_available=oldest),
        population=qv.population_block(
            member_basis={"table": "topic_members", "role": "evidence",
                          "engine_version": qv._engine_version(),
                          "quarantined_excluded": True},
            label_basis={"table": "dynamic_topics", "states": states},
        ),
        could_not_measure=could_not,
        rejected_terms=rejected,
    )
    out["lane_status"] = runner.statuses
    out["truncation"] = {
        "members": qv.truncation_block(returned=len(member_rows), cap=qv.IDENTITY_CAP),
        "labels": qv.truncation_block(returned=len(label_rows), cap=qv.IDENTITY_CAP),
        "signal_scan_cap": qv.SCAN_CAP,
    }
    out["data"] = merged
    if not runner.is_live("identities_members") and not runner.is_live("identities_labels"):
        out["status"] = qv.STATUS_DEGRADED
        out["reason"] = runner.reasons.get("identities_members", "db_error")
    return out


async def _receipt_geography(args: dict, runner: LaneRunner,
                             oldest: Optional[datetime]) -> dict:
    topic_key, _dt_id = qv.parse_topic_ref(args.get("topic_id"))

    geo_sql, geo_params = qv.receipt_geography_sql(topic_key)
    geo_rows = await runner.run("receipt_geography", geo_sql, *geo_params)

    res_sql, res_params = qv.receipt_resolvability_sql(topic_key)
    res_rows = await runner.run("receipt_resolvability", res_sql, *res_params)

    window = qv.window_block(requested_hours=24 * 7, oldest_available=oldest)
    population = qv.population_block(
        table="topic_members", role="evidence",
        engine_version=qv._engine_version(), quarantined_excluded=True,
        topic_id=topic_key,
        scope="all recorded evidence members of this topic, not a time window",
    )

    if not runner.is_live("receipt_geography"):
        return qv.degraded_result(
            "receipt_geography", runner.reasons.get("receipt_geography", "db_error"),
            window=window, population=population)

    could_not: list[dict] = []
    data = qv.summarize_geography([dict(r) for r in geo_rows])

    if runner.is_live("receipt_resolvability") and res_rows:
        row = dict(res_rows[0])
        members = int(row.get("members") or 0)
        resolvable = int(row.get("resolvable") or 0)
        data["members_recorded"] = members
        data["members_resolvable"] = resolvable
        # The true distinct-source count, over the FULL member set — the
        # counterpart to the served "20 Sources" display slice.
        data["distinct_sources"] = int(row.get("distinct_sources") or 0)
        pruned = max(members - resolvable, 0)
        data["members_pruned"] = pruned
        if pruned:
            # The starvation class made measurable: the identity still counts
            # these members, but their receipts are gone from the hot corpus,
            # so no geography can be computed for them.
            could_not.append({
                "what": f"{pruned} of {members} evidence members",
                "reason": "receipts_pruned",
                "detail": "these members' signal rows are no longer in the hot "
                          "corpus (retention), so they contribute to the "
                          "identity's counts but not to this distribution",
            })
    else:
        could_not.append({
            "what": "how many members still have a resolvable receipt",
            "reason": runner.reasons.get("receipt_resolvability", "db_error"),
        })

    out = qv.result_envelope(
        verb="receipt_geography", window=window, population=population,
        could_not_measure=could_not)
    out["lane_status"] = runner.statuses
    out["truncation"] = qv.truncation_block(returned=len(geo_rows), cap=qv.GEO_GROUP_CAP)
    out["data"] = data
    return out


async def _unclustered_signals(args: dict, runner: LaneRunner,
                               oldest: Optional[datetime]) -> dict:
    needles, rejected = qv.normalize_terms(args.get("terms") or [], require_one=True)
    country = qv.validate_country(args.get("country"))
    hours = _window_hours(args, default_days=1)
    window = qv.window_block(requested_hours=hours, oldest_available=oldest)
    population = qv.population_block(
        matched_over={"table": "signals_v2", "predicate": qv.HEADLINE_MATCH_EXPR},
        assignment_over={"table": "topic_members", "role": "evidence",
                         "engine_version": qv._engine_version(),
                         "quarantined_excluded": True},
    )

    counts_sql, counts_params = qv.unclustered_counts_sql(
        needles, hours=hours, country=country)
    counts_rows = await runner.run("unclustered_counts", counts_sql, *counts_params)

    if not runner.is_live("unclustered_counts"):
        return qv.degraded_result(
            "unclustered_signals", runner.reasons.get("unclustered_counts", "db_error"),
            window=window, population=population)

    landing_sql, landing_params = qv.unclustered_landing_sql(
        needles, hours=hours, country=country)
    landing_rows = await runner.run("unclustered_detail", landing_sql, *landing_params)

    sample_sql, sample_params = qv.unassigned_sample_sql(
        needles, hours=hours, country=country)
    sample_rows = await runner.run("unclustered_detail", sample_sql, *sample_params)

    could_not: list[dict] = []
    if not landing_rows and not runner.is_live("unclustered_detail"):
        could_not.append({
            "what": "which topics the assigned signals landed in",
            "reason": runner.reasons.get("unclustered_detail", "db_error"),
        })

    counts = dict(counts_rows[0]) if counts_rows else {"matched": 0, "unassigned": 0}
    data = qv.summarize_unclustered(
        counts, [dict(r) for r in landing_rows], [dict(r) for r in sample_rows])

    if int(counts.get("matched") or 0) >= qv.SCAN_CAP:
        could_not.append({
            "what": "signals beyond the scan cap",
            "reason": "scan_cap_reached",
            "detail": f"the term scan stops at {qv.SCAN_CAP} matching signals, so "
                      "the counts are a floor, not a total — narrow the window "
                      "or the terms",
        })

    out = qv.result_envelope(
        verb="unclustered_signals", window=window, population=population,
        could_not_measure=could_not, rejected_terms=rejected)
    out["lane_status"] = runner.statuses
    out["truncation"] = {
        "landed_in": qv.truncation_block(returned=len(landing_rows), cap=qv.LANDING_CAP),
        "unassigned_sample": qv.truncation_block(
            returned=len(sample_rows), cap=qv.UNASSIGNED_SAMPLE_CAP),
        "signal_scan_cap": qv.SCAN_CAP,
        "landing_detail_cap": qv.DETAIL_CAP,
    }
    out["data"] = data
    return out


async def _voice_mix(args: dict, runner: Optional[LaneRunner], conn: Any,
                     oldest: Optional[datetime]) -> dict:
    scope, value = qv.validate_voice_mix_scope(args)
    hours = _window_hours(args, default_days=7)
    window = qv.window_block(requested_hours=hours, oldest_available=oldest)

    if scope == "country":
        # Reuse the country Voice Mix endpoint function verbatim. Not a
        # reimplementation: calling the served surface is what makes the
        # protocol and the product incapable of disagreeing here.
        from app.routers.voice_mix import get_voice_mix
        report = await get_voice_mix(hours=hours, country=value)
        population = qv.population_block(
            table="signals_v2", scope=f"country_code = {value}",
            served_by="/api/v2/voice-mix (same function, same formula)")
        if report.get("degraded"):
            return qv.degraded_result(
                "voice_mix", report.get("reason", "db_busy"),
                window=window, population=population)
        out = qv.result_envelope(verb="voice_mix", window=window,
                                 population=population)
        out["data"] = report
        return out

    topic_key, _ = qv.parse_topic_ref(value)
    if runner is None:  # pragma: no cover - only the country scope is deferred
        return qv.degraded_result("voice_mix", "no_pool", window=window)
    population = qv.population_block(
        table="topic_members", role="evidence",
        engine_version=qv._engine_version(), quarantined_excluded=True,
        topic_id=topic_key,
        served_by="/api/v2/topic/{id}/voice (same aggregation function)")

    rows = await runner.run(
        "voice_members", thread_voice.THREAD_VOICE_SQL,
        topic_key, qv._engine_version(), hours)
    if not runner.is_live("voice_members"):
        return qv.degraded_result(
            "voice_mix", runner.reasons.get("voice_members", "db_error"),
            window=window, population=population)

    # Pure aggregation reused verbatim from the served thread-voice surface.
    data = thread_voice.aggregate_thread_voice([dict(r) for r in rows])
    could_not: list[dict] = []
    if not data.get("available"):
        could_not.append({
            "what": "this topic's voice mix",
            "reason": "no_members_in_window",
            "detail": data.get("reason"),
        })
    out = qv.result_envelope(verb="voice_mix", window=window,
                             population=population, could_not_measure=could_not)
    out["lane_status"] = runner.statuses
    out["data"] = data
    return out


# ------------------------------------------------------------------ shared

def _window_hours(args: dict, *, default_days: int) -> int:
    if args.get("window_hours") is not None:
        return qv.clamp_hours(args.get("window_hours"), default=default_days * 24)
    if args.get("window_days") is not None:
        return qv.clamp_hours(
            qv.clamp_hours(args.get("window_days"), default=default_days) * 24,
            default=default_days * 24)
    return default_days * 24


async def _hot_retention(runner: LaneRunner) -> Optional[datetime]:
    rows = await runner.run("retention", qv.hot_retention_sql())
    if rows:
        return dict(rows[0]).get("oldest")
    return None


def _acquire():
    return db.pool.acquire(timeout=POOL_ACQUIRE_TIMEOUT_S)


def _envelope(results: list[dict], *, degraded: bool = False,
              elapsed_ms: Optional[float] = None) -> dict:
    out: dict[str, Any] = {
        "contract": qv.REQUEST_CONTRACT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "asked": len(results),
        "results": results,
        "composition": {
            "supported": False,
            "note": "verb composition ($1 chaining) is the next slice; verbs in "
                    "one request are independent and share only the deadline",
        },
    }
    if degraded:
        out["degraded"] = True
    if elapsed_ms is not None:
        out["elapsed_ms"] = round(elapsed_ms, 1)
    return out


def _error(exc: qv.VerbError) -> JSONResponse:
    return JSONResponse(
        {"contract": qv.REQUEST_CONTRACT, "error": exc.reason, "detail": exc.detail},
        status_code=exc.status_code,
    )
