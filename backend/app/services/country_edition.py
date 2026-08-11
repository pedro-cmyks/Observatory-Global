"""L1 country edition — precomputed nightly, live build as the fallback.

Composes country-scoped narrative threads + a country-scoped coverage-gaps
band + cache-first article enrichment for the Brief's country door. Read-only;
never writes engine substrate. Mirrors the daily_publication enrichment pattern
but NEVER blocks — the live path warm-reads the article cache, enqueues the
misses fire-and-forget, and returns immediately; the client polls for the
progressive fill.

WHY THERE IS AN ARTIFACT (council R4 N26, 2026-08-11)
-----------------------------------------------------
The live composition is too slow to be the ONLY path. Measured in production
on quake day, cold: cc=CO -> 503 after 110.8s, cc=JP -> 503 after 21.7s,
cc=US -> 503 after 19.2s. The dominant cost is the scoped-children query
(`_DYNAMIC_TOPICS_COUNTRY_SQL`, measured 12.2-23.1s per country from the M1
against prod); it carries a 15s asyncpg budget, and when the shared Supabase is
loaded the TimeoutError becomes DatabaseBusyError and the door answers 503. The
120s Redis layer cannot rescue that — nothing ever succeeds, so it never fills.
The fast door failed exactly when the country was the story.

So the build moved off the request path, following mig 091 / the universe field:
`scripts/build_country_editions.py` composes the top doors nightly on the M1 and
stores one compact JSONB row each in `country_edition_artifacts` (mig 098). The
handler's order of truth is:

  1. a FRESH artifact (an indexed read, always fast),
  2. else the live build (unchanged — the path below),
  3. else the STALE artifact, labeled stale + degraded — a day-old edition that
     says it is a day old beats "database is busy".

The N17 slot guard runs on BOTH paths: for the artifact it runs at build time
and is stored inside the payload, so a reader still sees exactly which row was
withheld and why. `artifact_row_fields` refuses to store a payload without that
block — a missing check must never be indistinguishable from a passing one.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Iterable, Optional, Sequence

from app import db
from app.services.coverage_gaps import COUNTRY_GAPS_SQL, country_gap_floor
from app.services.subject_geography import (
    label_geography_conflict,
    label_subject_country,
    normalize_subject_country,
)
from app.services.thread_intelligence import fetch_threads
from app.services.thread_ranking import rank_threads

logger = logging.getLogger(__name__)

CONTRACT = "country-edition-v0"
ENRICHMENT_CONTRACT = "country-edition-enrichment-v0"
SLOT_GUARD_CONTRACT = "country-edition-slot-guard-v0"
ARTIFACT_CONTRACT = "country-edition-artifact-v0"

_MAX_THREADS = 24
_RECEIPTS_PER_THREAD = 4
_MAX_RECEIPT_URLS = 48

# How old a stored edition may be before the handler prefers a live rebuild.
# The builder runs once a night inside the scoped-snapshot chain, so 26h is one
# cadence plus slack: anything past it means a night was missed. A stale
# artifact is still SERVED when the live build cannot answer — it is just
# labeled, never passed off as today's edition.
ARTIFACT_MAX_AGE_HOURS = 26.0

# Country selection for the nightly build. MEASURED 2026-08-11 over the 24h
# field (132,286 signals across 228 country codes, `country_hourly_v2`):
#
#   rank 20 -> 68.3% cumulative      rank 50 -> 88.9%      rank 70 -> 93.9%
#   rank 30 -> 79.5%                 rank 60 -> 91.7%      rank 80 -> 95.6%
#
# The curve has no cliff (it is Zipf), it FLATTENS: 40->50 buys +3.6pp,
# 50->60 buys +2.8pp, 60->70 buys +2.2pp, and by rank 50 a country is at
# ~430 signals/day (~18/hour), the band where the scoped clustering yields
# 0-1 threads and the door is honestly short either way. Each additional 10
# countries costs ~3.5 min of nightly build (measured 12-23s per door). 50 is
# where the marginal coverage stops paying for the marginal minutes.
BUILD_TOP_N = 50

# The second lane, and the one N26 is actually about: a country can be THE
# story of the day without being big. Colombia was rank 9 on quake day, but
# Libya (302 today vs a 64.6/day baseline), Yemen, Lebanon, Armenia and Kosovo
# were all outside the volume head while spiking hard against their own
# baselines. `country_heat_v2` already measures that (it is the composite the
# map's heat reads), so the anomaly lane reuses it rather than inventing a
# second definition of "in the news".
#
# Both conditions are required. Ratio alone selects noise (AI: 8 signals vs a
# 2.0 baseline = 4x, and nothing to build an edition from); mass alone selects
# big-and-flat countries the volume lane already has. Measured today: 16 extra
# doors at these thresholds.
BUILD_ANOMALY_MIN_VOLUME = 150
BUILD_ANOMALY_RATIO = 1.5

# Hard ceiling on doors per run, so a pathological night (say, half the world
# spiking after a global event) cannot turn a bounded step into an open-ended
# one. The wall-clock budget in the builder is the other half of that bound.
BUILD_COUNTRY_CAP = 80

# Not a country door: GDELT's unknown-geography bucket. It has no CountryBrief,
# and it is large enough (rank 17 today) to steal a real country's slot.
_NON_COUNTRY_CODES = frozenset({"XX", "ZZ", "OO"})


# ── slot guard (council R4 N17, 2026-08-11) ───────────────────────────────────
# Colombia's edition led with "Japan Earthquake Traps Shoppers" — court
# ENTAILED, subject-geo VERIFIED ['CO'], 95 signals — while every receipt under
# it read "terremoto 7,4 sacude Colombia". The slotter selects threads by the
# COVERAGE country of their signals and never reads the label, so a thread
# whose own receipts contradict its label text can take the #1 slot on the one
# door where that lie is loudest.
#
# The guard is a SLOT decision, not a verdict: an excluded thread is untouched
# everywhere else (global /threads, its own detail, every other edition) — it
# simply is not slotted into THIS country's sections. The exclusion is counted
# and NAMED in the payload (`slot_guard`), never silent.
#
# Precision-first, deliberately narrower than "label country != cc": a label
# naming a foreign country is only excluded when the label ALSO contradicts
# its OWN receipts (`label_geography_conflict` — the same detector the court's
# geography conjunct rides, so the two can never drift apart). A genuine
# Venezuela story carried by Colombian press names Venezuela in its receipts
# too; that is an editorial question, not a defect, and emptying the door of
# real foreign coverage would be the worse error.
#
# KNOWN RESIDUAL, counted not hidden (measured 2026-08-11). The court widens
# its absence pool to 40 receipts before vetoing, because an actor-country
# label ("Ukraine Strikes Wildberries Warehouses" over Russian receipts) reads
# as contradicted on a short window and is honest on a long one. This door has
# only the receipts already in its payload, and it must not grow queries — the
# country edition is the surface that 503s db_busy on cold open (council R4
# N26), so a per-row widening fetch would trade one defect for a worse one.
# So the actor-vs-target class can cost ONE row on ONE door here: measured at
# ~half of the 4.4% of single-country labels that conflict at all, it is named
# in `slot_guard.exclusions` where a reader (or an audit) can see exactly what
# was withheld and why, and `ATLAS_COUNTRY_EDITION_SLOT_GUARD=off` reverts it.
# Follow-up: widen this pool once the door has a warm/cached build.
def slot_guard_enabled() -> bool:
    """Kill-switch, read at call time. Default ON — the guard only ever hides
    a row whose label is measurably contradicted by its own receipts.
    `ATLAS_COUNTRY_EDITION_SLOT_GUARD=off` restores the pre-fix behavior."""
    return os.environ.get("ATLAS_COUNTRY_EDITION_SLOT_GUARD", "on").lower() == "on"


def filter_edition_slots(
    threads: list[dict],
    country_code: str,
    *,
    enabled: bool | None = None,
) -> tuple[list[dict], dict]:
    """(threads to slot, slot-guard block). Pure — no I/O.

    Excludes a thread when its label names exactly ONE country, that country
    is not this edition's, AND the thread's own evidence receipts contradict
    the label's geography claim. Every other case is kept.
    """
    on = slot_guard_enabled() if enabled is None else enabled
    cc = normalize_subject_country(country_code)
    kept: list[dict] = []
    exclusions: list[dict] = []
    for thread in threads or []:
        label = str((thread or {}).get("label") or "")
        named = label_subject_country(label) if on else None
        conflict = (
            label_geography_conflict(label, (thread or {}).get("evidence_samples"))
            if named and named != cc else None
        )
        if not conflict:
            kept.append(thread)
            continue
        exclusions.append({
            "thread_id": (thread or {}).get("thread_id"),
            "label": label,
            "label_country": conflict["label_country"],
            "edition_country": cc,
            "dominant_receipt_country": conflict["dominant_country"],
            "reason_code": "label_country_contradicts_edition_slot",
            "reason": (
                f"{conflict['summary']}; not slotted into the {cc} edition "
                "(excluded from this door only — never demoted globally)"
            ),
        })
    return kept, {
        "contract": SLOT_GUARD_CONTRACT,
        "enabled": on,
        "considered": len(threads or []),
        "excluded": len(exclusions),
        "exclusions": exclusions,
        "note": (
            "a thread whose label names a country its own receipts contradict "
            "is not slotted into this country's edition; it stays served "
            "everywhere else"
        ),
    }


def gather_receipt_urls(
    threads: list[dict],
    *,
    per_thread: int = _RECEIPTS_PER_THREAD,
    cap: int = _MAX_RECEIPT_URLS,
) -> list[str]:
    """Distinct http receipt URLs across the ranked threads (capped per thread
    and per edition), preserving order. Same cap discipline as the seal."""
    urls: list[str] = []
    for thread in threads:
        for ev in (thread.get("evidence_samples") or [])[:per_thread]:
            url = str(ev.get("url") or ev.get("source_url") or "")
            if url.startswith("http"):
                urls.append(url)
    return list(dict.fromkeys(urls))[:cap]


def build_article_enrichment(urls: list[str], states: list[dict]) -> dict:
    """Assemble the enrichment block from a warm article_states read. `pending`
    counts URLs still fetching (None/pending/queued) — the client polls those."""
    by_url = {s["url"]: s for s in states}
    ok_count = sum(1 for s in states if s.get("status") == "ok")
    pending_urls = [
        u for u in urls
        if by_url.get(u, {}).get("status") in (None, "pending", "queued")
    ]
    return {
        "contract": ENRICHMENT_CONTRACT,
        "yield": {
            "ok": ok_count,
            "attempted": len(urls),
            "pending": len(pending_urls),
        },
        "pending_urls": pending_urls,
        "articles": {
            s["url"]: {
                "status": s.get("status"),
                "via": s.get("via"),
                "excerpt": s.get("excerpt"),
                "outlet": s.get("outlet"),
                "fetched_at": s.get("fetched_at"),
            }
            for s in states
        },
        "note": (
            "server-fetched page text per receipt; partial yield is normal "
            "(paywalls/bot walls); pending = still fetching, poll for the fill"
        ),
    }


def build_country_edition_payload(
    *,
    country: str,
    country_name: str,
    ranked_threads: list[dict],
    enrichment: dict,
    coverage_gaps: list[dict],
    generated_at: datetime,
    window_hours: int,
    slot_guard: dict | None = None,
) -> dict:
    """The country-edition-v0 envelope. Pure — no I/O."""
    return {
        "contract": CONTRACT,
        "country": country,
        "country_name": country_name,
        "generated_at": generated_at.isoformat(),
        "window_hours": window_hours,
        "threads": ranked_threads,
        "coverage_gaps": coverage_gaps,
        "article_enrichment": enrichment,
        # always present, even when nothing was excluded — an absent block
        # would read as "the guard did not run" (N17's own lesson: a missing
        # check is indistinguishable from a passing one unless it is counted).
        "slot_guard": slot_guard if slot_guard is not None else {
            "contract": SLOT_GUARD_CONTRACT,
            "enabled": slot_guard_enabled(),
            "considered": len(ranked_threads or []),
            "excluded": 0,
            "exclusions": [],
        },
    }


# ── which doors the nightly build warms ──────────────────────────────────────

def _code_of(row: Any, key: str, index: int) -> str:
    """Country code out of a tuple, an asyncpg Record or a dict."""
    if isinstance(row, dict):
        value = row.get(key)
    else:
        try:
            value = row[key]                       # asyncpg Record
        except (TypeError, KeyError, IndexError):
            value = row[index]                     # plain tuple
    return str(value or "").strip().upper()


def _num_of(row: Any, key: str, index: int) -> float:
    if isinstance(row, dict):
        value = row.get(key)
    else:
        try:
            value = row[key]
        except (TypeError, KeyError, IndexError):
            value = row[index]
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _is_country_door(code: str) -> bool:
    return len(code) == 2 and code.isalpha() and code not in _NON_COUNTRY_CODES


def select_build_countries(
    volume_rows: Sequence[Any],
    heat_rows: Sequence[Any],
    *,
    top_n: int = BUILD_TOP_N,
    explicit: Iterable[str] = (),
    anomaly_min_volume: int = BUILD_ANOMALY_MIN_VOLUME,
    anomaly_ratio: float = BUILD_ANOMALY_RATIO,
    cap: int = BUILD_COUNTRY_CAP,
) -> list[dict]:
    """Which country doors to warm tonight, in build order. Pure — no I/O.

    Three lanes, deduped, head first so a truncated run still warms the doors
    most readers open:
      * `explicit`      — an operator named it on the command line,
      * `volume_rank`   — the top-N of the 24h field (see BUILD_TOP_N),
      * `volume_anomaly`— a country spiking against its OWN baseline with
                          enough mass to compose an edition (the N26 case).
    """
    chosen: list[dict] = []
    seen: set[str] = set()

    def _add(code: str, reason: str) -> None:
        if not _is_country_door(code) or code in seen or len(chosen) >= cap:
            return
        seen.add(code)
        chosen.append({"country_code": code, "selection_reason": reason})

    for code in explicit or ():
        _add(str(code).strip().upper(), "explicit")

    ranked = 0
    for row in volume_rows or ():
        if ranked >= top_n:
            break
        code = _code_of(row, "country_code", 0)
        if not _is_country_door(code):
            continue           # not a door; it does not consume a rank either
        ranked += 1
        _add(code, "volume_rank")

    for row in heat_rows or ():
        volume_now = _num_of(row, "volume_now", 1)
        baseline = _num_of(row, "volume_baseline_daily", 2)
        if volume_now < anomaly_min_volume or baseline <= 0:
            continue
        if volume_now < anomaly_ratio * baseline:
            continue
        _add(_code_of(row, "country_code", 0), "volume_anomaly")

    return chosen


SELECTION_VOLUME_SQL = """
    SELECT country_code, SUM(signal_count)::bigint AS volume
    FROM country_hourly_v2
    WHERE hour > now() - ($1::int || ' hours')::interval
      AND hour <= now()
    GROUP BY country_code
    ORDER BY volume DESC
"""

SELECTION_HEAT_SQL = """
    SELECT country_code, volume_now, volume_baseline_daily
    FROM country_heat_v2
    WHERE hours_window = $1
    ORDER BY atlas_heat DESC NULLS LAST
"""


async def fetch_selection_inputs(*, hours: int = 24) -> tuple[list, list]:
    """(volume rows, heat rows) for `select_build_countries`. Both are cheap
    matview reads (measured 0.6s / 1.0s). The heat lane degrades to [] rather
    than failing the run: losing the anomaly lane costs a few doors, losing the
    build costs all of them."""
    if db.pool is None:
        return [], []
    async with db.pool.acquire() as conn:
        volume = await conn.fetch(SELECTION_VOLUME_SQL, int(hours), timeout=60)
        try:
            heat = await conn.fetch(SELECTION_HEAT_SQL, int(hours), timeout=60)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "country-edition build: heat lane unavailable (%s: %s) — "
                "volume lane only",
                type(exc).__name__, str(exc)[:200],
            )
            heat = []
    return list(volume), list(heat)


# ── artifact: store, read, label ─────────────────────────────────────────────

def artifact_row_fields(payload: dict) -> dict:
    """The denormalized columns for one artifact row.

    Refuses a payload with no `slot_guard` block. The guard runs at BUILD time
    on this path, and an artifact that lost the block would serve a door whose
    exclusions are invisible — indistinguishable from a guard that never ran,
    which is precisely the failure N17 was opened for.
    """
    guard = (payload or {}).get("slot_guard")
    if not isinstance(guard, dict) or "excluded" not in guard:
        raise ValueError(
            "refusing to store a country edition without a slot_guard block "
            "(the guard runs at build time; a missing block is unauditable)"
        )
    return {
        "contract": str(payload.get("contract") or CONTRACT),
        "thread_count": len(payload.get("threads") or []),
        "slot_guard_excluded": int(guard.get("excluded") or 0),
    }


def _age_hours(generated_at: datetime, *, now: Optional[datetime] = None) -> float:
    now = now or datetime.now(timezone.utc)
    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)
    return max(0.0, (now - generated_at).total_seconds() / 3600.0)


def stamp_artifact(
    payload: dict,
    *,
    generated_at: datetime,
    build_seconds: float | None,
    selection_reason: str | None,
    now: Optional[datetime] = None,
    max_age_hours: float = ARTIFACT_MAX_AGE_HOURS,
    window_requested: int | None = None,
    window_served: int | None = None,
    degraded_reason: str | None = None,
) -> dict:
    """Add the `artifact` provenance block. Pure; the edition body is untouched.

    The block is what keeps a precomputed door honest: when it was built, how
    old that makes it, whether that age crossed a missed night, and — when the
    live path failed and this is a fallback — that it is a fallback.
    """
    age = _age_hours(generated_at, now=now)
    block: dict = {
        "contract": ARTIFACT_CONTRACT,
        "source": "precomputed_artifact",
        "generated_at": (
            generated_at.replace(tzinfo=timezone.utc).isoformat()
            if generated_at.tzinfo is None else generated_at.isoformat()
        ),
        "age_hours": round(age, 2),
        "stale": age > max_age_hours,
        "max_age_hours": max_age_hours,
        "build_seconds": (
            round(float(build_seconds), 2) if build_seconds is not None else None
        ),
        "selection_reason": selection_reason,
        "note": (
            "precomputed on the M1 (the live composition measures 12-23s of "
            "scoped queries per country and 503'd db_busy on cold open — "
            "council R4 N26); the slot guard ran at build time and rides in "
            "`slot_guard`"
        ),
    }
    if window_requested is not None and window_served is not None and (
        int(window_requested) != int(window_served)
    ):
        block["window_requested"] = int(window_requested)
        block["window_served"] = int(window_served)
    if degraded_reason:
        block["degraded"] = True
        block["degraded_reason"] = degraded_reason
    return {**payload, "artifact": block}


async def store_country_edition_artifact(
    payload: dict,
    *,
    country_code: str,
    hours: int,
    build_seconds: float,
    selection_reason: str | None = None,
    generated_at: Optional[datetime] = None,
) -> None:
    """Upsert ONE artifact row for this door. Raises on a payload the guard
    never touched (see `artifact_row_fields`)."""
    fields = artifact_row_fields(payload)
    generated_at = generated_at or datetime.now(timezone.utc)
    async with db.pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO country_edition_artifacts
                (country_code, window_hours, generated_at, contract,
                 thread_count, slot_guard_excluded, selection_reason,
                 build_seconds, payload, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, now())
            ON CONFLICT (country_code, window_hours) DO UPDATE SET
                generated_at = EXCLUDED.generated_at,
                contract = EXCLUDED.contract,
                thread_count = EXCLUDED.thread_count,
                slot_guard_excluded = EXCLUDED.slot_guard_excluded,
                selection_reason = EXCLUDED.selection_reason,
                build_seconds = EXCLUDED.build_seconds,
                payload = EXCLUDED.payload,
                updated_at = now()
            """,
            country_code.upper(),
            int(hours),
            generated_at,
            fields["contract"],
            fields["thread_count"],
            fields["slot_guard_excluded"],
            selection_reason,
            float(build_seconds),
            json.dumps(payload, default=str),
        )


def _json_value(value: Any) -> Any:
    return json.loads(value) if isinstance(value, (str, bytes)) else value


async def fetch_stored_country_edition(
    country_code: str, *, hours: int = 24, now: Optional[datetime] = None,
) -> dict | None:
    """The precomputed door, stamped — or None when there is nothing stored.

    Never raises and never builds: this read sits in front of the slow path, so
    a missing table, a cold pool or a timeout must fall THROUGH to the live
    build rather than take the door down with it.

    Exact window first; failing that, the freshest artifact for this country
    with the mismatch NAMED (same rule as the universe field's `days_served`) —
    a 24h edition answering a 6h request is worth serving, but only labeled.
    """
    if db.pool is None:
        return None
    cc = country_code.upper()
    try:
        async with db.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT country_code, window_hours, generated_at, contract,
                       thread_count, slot_guard_excluded, selection_reason,
                       build_seconds, payload
                FROM country_edition_artifacts
                WHERE country_code = $1 AND window_hours = $2
                """,
                cc, int(hours), timeout=5,
            )
            if row is None:
                row = await conn.fetchrow(
                    """
                    SELECT country_code, window_hours, generated_at, contract,
                           thread_count, slot_guard_excluded, selection_reason,
                           build_seconds, payload
                    FROM country_edition_artifacts
                    WHERE country_code = $1
                    ORDER BY generated_at DESC
                    LIMIT 1
                    """,
                    cc, timeout=5,
                )
    except Exception as exc:  # noqa: BLE001 — the artifact read is best-effort
        logger.warning(
            "country-edition artifact read degraded cc=%s: %s: %s",
            cc, type(exc).__name__, str(exc)[:200],
        )
        return None

    if row is None:
        return None
    payload = _json_value(row["payload"])
    if not isinstance(payload, dict):
        return None
    return stamp_artifact(
        payload,
        generated_at=row["generated_at"],
        build_seconds=row["build_seconds"],
        selection_reason=row["selection_reason"],
        now=now,
        window_requested=int(hours),
        window_served=int(row["window_hours"]),
    )


async def fetch_country_edition(
    country_code: str, *, hours: int = 24, enqueue: bool = True,
) -> dict:
    """Compose the live country edition. Never blocks: warm-reads the article
    cache and enqueues the misses fire-and-forget.

    `enqueue=False` for the NIGHTLY BUILD. Measured 2026-08-11: the enqueue's
    known-domain gate (a 48h scan of `signals_v2` union the archive samples)
    hit the statement timeout under load and cost 2-3.5 MINUTES per door —
    more than the composition it was decorating. It is also redundant there:
    the browser posts the payload's `pending_urls` to
    /api/v2/research/articles/fetch itself (BriefNewspaper.tsx), so the reader
    who actually opens a door starts its fetches, instead of the build firing
    ~3,000 speculative ones a night for doors nobody may open. The artifact
    still carries every excerpt already in the cache plus the honest
    `pending_urls` list.
    """
    cc = country_code.upper()
    generated_at = datetime.now(timezone.utc)

    if db.pool is None:
        return build_country_edition_payload(
            country=cc,
            country_name=cc,
            ranked_threads=[],
            enrichment=build_article_enrichment([], []),
            coverage_gaps=[],
            generated_at=generated_at,
            window_hours=hours,
        )

    gap_min = country_gap_floor()
    country_name = cc
    gap_rows: list = []
    try:
        async with db.pool.acquire() as conn:
            rec = await conn.fetchrow(
                "SELECT name FROM countries_v2 WHERE code = $1", cc
            )
            country_name = rec["name"] if rec else cc
            gap_rows = await conn.fetch(COUNTRY_GAPS_SQL, hours, cc, gap_min)
    except Exception as exc:  # gaps/name are secondary — never blank the door
        logger.warning(
            "country-edition gaps skipped cc=%s: %s: %s",
            cc, type(exc).__name__, str(exc)[:200],
        )

    threads = await fetch_threads(
        hours=hours,
        limit=_MAX_THREADS,
        country_codes=[cc],
        attach_evidence=True,
    )
    # N17 slot guard runs BEFORE enrichment so an excluded row's receipt URLs
    # never spend the edition's bounded fetch budget either.
    ranked, slot_guard = filter_edition_slots(rank_threads(threads), cc)

    urls = gather_receipt_urls(ranked)
    states: list[dict] = []
    if urls:
        try:
            from app.services.article_fetch import article_states, enqueue_fetches
            states = await article_states(urls)
            by_url = {s["url"]: s for s in states}
            # 'queued' is already in flight — don't re-enqueue (it still counts
            # as pending in the yield, hence the asymmetry with pending_urls).
            missing = [
                u for u in urls
                if by_url.get(u, {}).get("status") in (None, "pending")
            ] if enqueue else []
            if missing:
                await enqueue_fetches(missing)      # fire-and-forget, NO wait
                # re-read: picks up the newly-inserted pending rows + any
                # concurrent request's fetch that flipped mid-enqueue.
                states = await article_states(urls)
        except Exception as exc:  # enrichment never breaks the edition
            logger.warning(
                "country-edition enrichment skipped: %s: %s",
                type(exc).__name__, str(exc)[:200],
            )

    enrichment = build_article_enrichment(urls, states)
    coverage_gaps = [dict(r) for r in gap_rows]

    logger.info(
        "country-edition cc=%s threads=%d gaps=%d enrich ok=%d/%d pending=%d "
        "slot-guard excluded=%d",
        cc, len(ranked), len(coverage_gaps),
        enrichment["yield"]["ok"], enrichment["yield"]["attempted"],
        enrichment["yield"]["pending"], slot_guard["excluded"],
    )
    for row in slot_guard["exclusions"]:
        logger.info("country-edition slot-guard cc=%s %s: %s",
                    cc, row["thread_id"], row["reason"])
    return build_country_edition_payload(
        country=cc,
        country_name=country_name,
        ranked_threads=ranked,
        enrichment=enrichment,
        coverage_gaps=coverage_gaps,
        generated_at=generated_at,
        window_hours=hours,
        slot_guard=slot_guard,
    )
