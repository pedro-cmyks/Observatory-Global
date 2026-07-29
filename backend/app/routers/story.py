"""Story Lens — the measured neighborhood of one thread.

GET /api/v2/story/{thread_id}/siblings

Read-only, ranking-with-receipts (spec docs/superpowers/specs/2026-07-28-
story-lens-design.md §6; the ranker itself is app/services/story_siblings.py
— pure, no DB, deliberately NEVER a merge gate; the transitive-collapse
failure that killed evidence-overlap as a merge rule (recall-229 record)
cannot recur here because nothing is written and no closure is taken).

Every sibling carries the measured WHY (whitened cosine + kinship degree,
plus a shared-country receipt when one exists) — never a silent rank.

Connection discipline mirrors routers/dossier.py's `/walk` (dossier.py:
1027-1085): the pool connection is held only for each bounded fetch, never
across the whitening + graph-walk compute (O(n^2) in the active-topic count
— holding a connection through it needlessly pins a pool slot on Fly, where
the pool caps at 10).
"""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import datetime, timezone

import numpy as np
from fastapi import APIRouter

from app import db
from app.services.constellation_walk import WalkParams
from app.services.story_siblings import DEFAULT_CAP, rank_siblings
from app.services.whitening import apply_whitening, load_whitening

logger = logging.getLogger(__name__)
router = APIRouter()

_CACHE_TTL_S = 300

# In-process topics-matrix cache — ANCHOR-INDEPENDENT: the same dynamic_topics
# scan (~1.6k active rows x 768-float centroids) serves every anchor's walk, so
# paying for it once per TTL instead of once per request is the fix for the
# prod 15s-statement-timeout failure (Fly logs, 2026-07-28: "canceling
# statement due to statement timeout" at the old bare `conn.fetch(_TOPICS_SQL)`
# over the pooler). 120s TTL is generous against a nightly-churn corpus (this
# project's CLAUDE.md: topics churn nightly, not intra-minute) and matches the
# dossier walk's own `_WALK_CACHE_TTL_S` precedent (dossier.py:952). Mutated
# in place (`.clear()` + `.update()`) rather than rebound, so no `global` is
# needed. Redis payload cache (300s per anchor, `_CACHE_TTL_S` above) sits
# above this and is unchanged — this cache is the shared substrate underneath
# a Redis miss, not a replacement for it.
_TOPICS_CACHE_TTL_S = 120
_TOPICS_CACHE: dict = {}

# Shape gate: a malformed id must short-circuit BEFORE any Redis/DB work — a
# thread_id is untrusted path input, never assumed pre-validated by the
# caller. Allows the `slug--cc` country-scope suffix (hyphens included) so a
# legitimate scoped id still passes; garbage (1000-char strings, injection
# attempts, embedded whitespace) is rejected here, cheaply, up front.
_TOPIC_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

# Mirrors routers/dossier.py `_WALK_TOPICS_SQL` EXACTLY (state/is_umbrella/
# centroid filters are the walk's serving-universe contract — story-level,
# not umbrella, active only) + label_status (Label Court verdict) added to
# the select so the sibling payload can carry it as a receipt.
_TOPICS_SQL = """
    SELECT id, label, category, label_status, centroid_vec
    FROM dynamic_topics
    WHERE state = 'active' AND NOT is_umbrella AND centroid_vec IS NOT NULL
"""

# Country footprints for the anchor + returned siblings only (one bounded
# query, ANY($1) over a short list) — the shared-country reason on top of the
# ranker's whitened-cosine receipt. Scoping mirrors the walk's blob-member
# fetch (dossier.py `_WALK_BLOB_MEMBERS_SQL`): evidence role, v1-compat
# engine, quarantined rows excluded — the 2026-07-27 SNAPSHOT_UNLABELLED bug
# class this project's CLAUDE.md logs was exactly this scoping done wrong.
_COUNTRIES_SQL = """
    SELECT tm.topic_id, s.country_code, COUNT(*) AS n
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = ANY($1::text[])
      AND tm.role = 'evidence'
      AND tm.engine_version = 'v1-compat'
      AND tm.quarantined IS NOT TRUE
      AND tm.assigned_at > NOW() - INTERVAL '7 days'
      AND s.country_code IS NOT NULL
    GROUP BY tm.topic_id, s.country_code
"""


def _redis_client():
    # Deferred (call-time) import — the house pattern (attention_eclipse.py,
    # delight.py, research.py): main_v2.py imports this router module while
    # ITSELF still mid-import (`app.include_router(...)` at module scope), so
    # a top-level `from app.main_v2 import app` back-reference would make
    # `python -c "import app.routers.story"` fail with a circular-import
    # AttributeError. By request-serving time app.main_v2 is always already
    # fully loaded, so a call-time import is free.
    from app.main_v2 import app

    return getattr(app.state, "redis", None)


def _normalize_thread_id(raw: str) -> str | None:
    """Validate shape, then strip an optional `--cc` country-scope suffix
    (mirrors dossier.py's `_base_topic_id`): topic_members/dynamic_topics key
    on the bare id. Returns None on a malformed id — the caller must reject
    it before any Redis/DB work, not merely treat it as "not found".

    This does NOT decide whether the resulting key is a SUPPORTED anchor
    type (see the handler's `dynamic-topic-` prefix check) — a bare atlas
    slug normalizes cleanly here and is rejected one step later, on purpose,
    so the two failure modes (malformed vs unsupported) stay distinguishable
    reason codes rather than collapsing into one."""
    if not raw or not _TOPIC_ID_RE.match(raw):
        return None
    if raw.startswith("dynamic-topic-"):
        return raw
    return raw.split("--")[0]


def _empty(reason: str) -> dict:
    return {
        "contract": "story-siblings-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anchor": None,
        "siblings": [],
        "notes": [reason],
    }


@router.get("/api/v2/story/{thread_id}/siblings")
async def get_story_siblings(thread_id: str) -> dict:
    """The measured neighborhood of one thread — hermanos (direct edge) and
    primos (walked), each with a receipt. Never merges, never asserts a
    relation without a measured basis; an honest empty (invalid id,
    unsupported anchor type, no DB, no whitening, seed not found, no kin) is
    a first-class response, not an error."""
    topic_key = _normalize_thread_id(thread_id)
    if not topic_key:
        return _empty("invalid_thread_id")

    # v1 lens anchors are DYNAMIC TOPICS ONLY. A `thread_id` may also name an
    # ATLAS topic ('some-slug' bare, or 'some-slug--cc' country-scoped) or an
    # emergent-cluster snapshot ('emergent-cluster-N', 'cluster-N') — neither
    # has a `dynamic_topics.centroid_vec`, so neither can EVER resolve here
    # (mirrors the walk endpoint's scope, dossier.py `_WALK_TOPICS_SQL` +
    # `_base_topic_id`'s seed-filter: only `dynamic-topic-<id>` bases walk).
    # This is a STRUCTURAL v1 limitation, not a transient failure — its own
    # reason code, checked BEFORE any Redis/DB work, rather than folding into
    # "seed not found" (which reads as "try again later," and never will).
    if not topic_key.startswith("dynamic-topic-"):
        return _empty("unsupported_anchor_type")

    cache_key = f"story_sib:v1:{topic_key}"
    redis = _redis_client()
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as exc:  # noqa: BLE001
            logger.warning("story siblings cache read failed: %s", exc, exc_info=True)

    if db.pool is None:
        return _empty("db_unavailable")

    try:
        whitening = load_whitening()
    except Exception as exc:  # noqa: BLE001
        logger.warning("story siblings whitening unavailable: %s", exc, exc_info=True)
        return _empty("whitening_unavailable")

    # (a) Topics matrix: cache hit skips the DB entirely (this is the fix —
    # the scan is ANCHOR-INDEPENDENT, so every anchor within the TTL window
    # reuses the same parsed arrays). On a miss, acquire ONLY for the fetch,
    # then release — mirrors dossier.py's /walk (dossier.py:1027-1085), which
    # never holds a connection across the O(n^2) whitening/graph-walk compute
    # below. Bumped 15000->30000ms: this is the one connection that pays for
    # the full ~1.6k-row centroid scan; the countries connection below stays
    # at its original 8000ms (bounded ANY($1) fetch, unaffected).
    now = time.monotonic()
    cached_topics = _TOPICS_CACHE
    if cached_topics and (now - cached_topics["at"]) < _TOPICS_CACHE_TTL_S:
        keys: list[str] = cached_topics["keys"]
        labels: list[str] = cached_topics["labels"]
        cats: list[str | None] = cached_topics["cats"]
        statuses: list[str | None] = cached_topics["statuses"]
        vecs_arr: np.ndarray = cached_topics["vecs"]
    else:
        try:
            async with db.pool.acquire() as conn:
                await conn.execute("SET statement_timeout = 30000")
                rows = await conn.fetch(_TOPICS_SQL)
        except Exception as exc:  # noqa: BLE001
            logger.warning("story siblings topic fetch failed: %s", exc, exc_info=True)
            return _empty("db_error")

        keys = []
        labels = []
        cats = []
        statuses = []
        vecs: list[list[float]] = []
        for r in rows:
            v = r["centroid_vec"]
            if v is None or len(v) != 768:
                continue
            tid = int(r["id"])
            keys.append(f"dynamic-topic-{tid}")
            labels.append(r["label"] or f"dynamic-topic-{tid}")
            cats.append(r["category"])
            statuses.append(r["label_status"])
            vecs.append([float(x) for x in v])
        vecs_arr = np.asarray(vecs, dtype=np.float32)

        _TOPICS_CACHE.clear()
        _TOPICS_CACHE.update(
            at=now, keys=keys, labels=labels, cats=cats, statuses=statuses, vecs=vecs_arr,
        )

    # (b) Compute OUTSIDE any held connection: seed lookup, whitening, the
    # graph walk. `rank_siblings` raises ValueError loudly on a contract
    # violation (misaligned/non-unit-norm arrays — Task 1's deliberate
    # design: a silent [] there would read as "this story stands alone," a
    # dishonest empty). That is a CALLER programming error, never a database
    # fault, so it — and any other compute failure (e.g. an OOM building the
    # similarity matrix) — must never be mislabeled "db_error".
    try:
        if topic_key not in keys:
            return _empty("seed_not_found_or_no_centroid")

        seed = keys.index(topic_key)
        whitened = apply_whitening(vecs_arr, whitening)
        siblings = rank_siblings(
            seed, whitened, keys, labels, cats, WalkParams.from_env(), cap=DEFAULT_CAP,
        )
    except ValueError as exc:
        logger.error("story siblings contract violation: %s", exc, exc_info=True)
        return _empty("internal_error")
    except Exception as exc:  # noqa: BLE001
        logger.error("story siblings compute failed: %s", exc, exc_info=True)
        return _empty("internal_error")

    # (c) Re-acquire ONLY for the bounded country-receipt fetch. A failure
    # here degrades gracefully (empty footprints, never a 500) but must be
    # surfaced honestly, not silently — and a degraded payload must never be
    # frozen into the cache (the rail this project's CLAUDE.md logs
    # repeatedly: attention_eclipse.py's degraded branch also never setex's,
    # attention_eclipse.py:262-265).
    want = [topic_key] + [s.topic_key for s in siblings]
    foot: dict[str, list[tuple[str, int]]] = {}
    country_receipts_degraded = False
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 8000")
            crows = await conn.fetch(_COUNTRIES_SQL, want)
        for cr in crows:
            foot.setdefault(cr["topic_id"], []).append(
                (cr["country_code"], int(cr["n"]))
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("story siblings country footprint failed: %s", exc, exc_info=True)
        country_receipts_degraded = True

    def _countries(tk: str) -> list[str]:
        return [cc for cc, _n in sorted(foot.get(tk, []), key=lambda t: -t[1])[:3]]

    anchor_countries = _countries(topic_key)
    status_by_key = dict(zip(keys, statuses))

    sib_payload = []
    for s in siblings:
        reasons = [dict(r) for r in s.reasons]
        shared = sorted(set(_countries(s.topic_key)) & set(anchor_countries))
        if shared:
            reasons.append({"basis": "shared_country", "value": ",".join(shared)})
        sib_payload.append(
            {
                "id": s.topic_key,
                "label": s.label,
                "weight": round(s.weight, 4),
                "degree": s.degree,
                "kinship": s.kinship,
                "through_blob": s.through_blob,
                "is_blob": s.is_blob,
                "via_parent": s.via_parent_label,
                "folded": list(s.folded),
                "label_status": status_by_key.get(s.topic_key),
                "countries": _countries(s.topic_key),
                "reasons": reasons,
            }
        )

    notes: list[str] = []
    if country_receipts_degraded:
        notes.append("country_receipts_degraded")
    if not siblings:
        notes.append("no_measured_kin")

    payload = {
        "contract": "story-siblings-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anchor": {
            "id": topic_key,
            "label": labels[seed],
            "label_status": statuses[seed],
            "countries": anchor_countries,
        },
        "siblings": sib_payload,
        "notes": notes,
    }

    if redis is not None and not country_receipts_degraded:
        try:
            await redis.setex(cache_key, _CACHE_TTL_S, json.dumps(payload))
        except Exception as exc:  # noqa: BLE001
            logger.warning("story siblings cache write failed: %s", exc, exc_info=True)
    return payload
