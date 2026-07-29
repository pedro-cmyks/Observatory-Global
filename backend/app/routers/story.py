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
from app.services.constellation_walk import (
    WalkParams,
    blob_basis_for_ui,
    blob_connector_flags,
    build_knn_graph,
    confirm_blob_candidates,
)
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

# Blob CONFIRMER (Lever C2, plan docs/superpowers/plans/2026-07-29-identity-
# three-levers.md; measured docs/research/recall-229/2026-07-29-blob-flagger-
# calibration.md). The cached `blobs` set (built once per _TOPICS_CACHE
# refresh, above) is the CHEAP entropy first-pass only — measured AUC 0.564 at
# the topic level (near coin-flip), blind to within-category fusions BY
# CONSTRUCTION. The measured discriminator is MEMBERSHIP MULTIMODALITY
# (`confirm_blob_candidates`, the same confirmer `/dossier/walk` already
# uses) — bounded to ONLY the topics THIS response actually shows (never the
# whole cached candidate field): the returned siblings, plus the umbrella
# stand-in child when the anchor resolved through one. Mirrors dossier.py's
# `_WALK_BLOB_MEMBERS_SQL` pattern exactly (engine_version v1-compat serving
# default, evidence role only, quarantined rows excluded, capped per-topic via
# ROW_NUMBER).
BLOB_CONFIRM_MEMBERS_CAP = 200
_BLOB_MEMBERS_SQL = """
    WITH ranked AS (
        SELECT (split_part(tm.topic_id, '-', 3))::int AS tid,
               se.vec::text AS vec,
               ROW_NUMBER() OVER (
                   PARTITION BY tm.topic_id ORDER BY tm.signal_id
               ) AS rn
        FROM topic_members tm
        JOIN signal_embeddings se ON se.signal_id = tm.signal_id
        WHERE tm.topic_id = ANY($1::text[])
          AND tm.role = 'evidence'
          AND tm.engine_version = 'v1-compat'
          AND tm.quarantined IS NOT TRUE
    )
    SELECT tid, vec FROM ranked WHERE rn <= $2
"""


async def _confirm_ui_blob_flags(
    candidate_keys: dict[str, int],
) -> dict[str, tuple[bool, str | None]]:
    """Membership-multimodality confirmation for the reader-facing `is_blob`
    chip (Lever C2). `candidate_keys` maps topic_key -> its node index, for
    every entropy CANDIDATE that is actually about to be shown to the caller
    (never the whole cached field — mindful, matches the dossier walk's own
    bound). Returns (is_blob, blob_basis) per topic_key via
    `blob_basis_for_ui` — GC kill rule: a candidate that can't be confirmed
    (no DB, an old topic whose embeddings were pruned, too few embedded
    members) DEGRADES to 'candidate_unconfirmed', never silently reads as
    cleaner (dropped) or as a real confirmed fusion.

    Bounded: at most `len(candidate_keys)` topics (≤12 siblings + 1 umbrella
    stand-in child = ≤13 by construction) × BLOB_CONFIRM_MEMBERS_CAP member
    rows each. A DB failure here degrades every requested candidate to
    'candidate_unconfirmed' (via confirm_blob_candidates' own entropy_only
    fallback over an empty member_vecs) rather than raising — this helper is
    never allowed to turn a degraded fetch into a 500.
    """
    pool = db.pool
    if not candidate_keys or pool is None:
        return {}
    member_vecs: dict[int, np.ndarray] = {}
    try:
        async with pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 8000")
            rows = await conn.fetch(
                _BLOB_MEMBERS_SQL, list(candidate_keys.keys()), BLOB_CONFIRM_MEMBERS_CAP,
            )
        idx_by_tid: dict[int, int] = {}
        for topic_key, idx in candidate_keys.items():
            try:
                idx_by_tid[int(topic_key[len("dynamic-topic-"):])] = idx
            except ValueError:
                continue
        by_idx: dict[int, list] = {}
        for r in rows:
            node_i = idx_by_tid.get(int(r["tid"]))
            if node_i is None:
                continue
            try:
                vec = np.asarray(json.loads(r["vec"]), dtype=np.float32)
            except Exception:
                continue
            by_idx.setdefault(node_i, []).append(vec)
        member_vecs = {i: np.vstack(v) for i, v in by_idx.items() if v}
    except Exception as exc:  # noqa: BLE001
        logger.warning("story siblings blob-confirm member fetch failed "
                       "(degrades to candidate_unconfirmed): %s", exc, exc_info=True)
        member_vecs = {}

    confirmations = confirm_blob_candidates(set(candidate_keys.values()), member_vecs)
    return {
        topic_key: blob_basis_for_ui(confirmations.get(idx))
        for topic_key, idx in candidate_keys.items()
    }


# Umbrella fallback (T10 follow-up, 2026-07-29): /threads serves R2 UMBRELLAS
# at the top level (build_umbrella_topics.py, mig 058 `parent_id`/`is_umbrella`
# — same `dynamic-topic-<id>` prefix as a story-level topic), and the lens
# auto-enter fires on whatever id the front page shows. An umbrella row has no
# centroid_vec of its own and is deliberately excluded from `_TOPICS_SQL`, so
# without this fallback exactly the BIGGEST stories (the ones an umbrella
# collapses) would 100% miss into "seed_not_found_or_no_centroid". Resolve to
# the umbrella's largest ACTIVE child that carries a centroid (state='active'
# is a WHERE clause, not a tiebreak — a retired-but-largest child must never
# win LIMIT 1 and then hard-fail seed_not_found while a smaller active child
# was walkable), walk from there, but keep the ANCHOR identity (id/label/
# label_status) as the umbrella's own — the child is a stand-in for the walk,
# never the story the user asked about.
_UMBRELLA_SQL = """
    SELECT label, label_status
    FROM dynamic_topics
    WHERE id = $1 AND is_umbrella AND state = 'active'
"""

_UMBRELLA_CHILD_SQL = """
    SELECT id
    FROM dynamic_topics
    WHERE parent_id = $1 AND NOT is_umbrella AND centroid_vec IS NOT NULL
      AND state = 'active'
    ORDER BY agg_n_signals DESC NULLS LAST
    LIMIT 1
"""


async def _resolve_umbrella_anchor(
    topic_key: str,
) -> tuple[str, str | None, str | None] | None:
    """If `topic_key` names an active R2 umbrella, resolve it to its largest
    child that carries a centroid (i.e. is walkable). Returns
    (child_topic_key, umbrella_label, umbrella_label_status), or None when
    `topic_key` is not an umbrella, or is one with no resolvable child (a
    childless/all-blind-child umbrella — honest miss, not an error).

    Tiny lookups (PK + the `idx_dynamic_topics_parent` index) — run on a
    short-timeout acquire of their own, deliberately OUTSIDE the topics-cache
    branch: unlike the topics matrix, this result is per-anchor, not shared
    across every request in the TTL window. Only ever called after the
    handler's own pool-availability guard has already passed, so no repeat
    guard here — an unexpected missing pool would surface as an
    AttributeError, caught by the broad except below same as any other
    connection fault.
    """
    try:
        tid = int(topic_key[len("dynamic-topic-"):])
    except ValueError:
        return None
    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 8000")
            umbrella_row = await conn.fetchrow(_UMBRELLA_SQL, tid)
            if umbrella_row is None:
                return None
            child_row = await conn.fetchrow(_UMBRELLA_CHILD_SQL, tid)
    except Exception as exc:  # noqa: BLE001
        logger.warning("story siblings umbrella resolve failed: %s", exc, exc_info=True)
        return None
    if child_row is None:
        return None
    return (
        f"dynamic-topic-{int(child_row['id'])}",
        umbrella_row["label"],
        umbrella_row["label_status"],
    )


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

    # (a) Topics matrix + its derived graph: cache hit skips the DB AND the
    # O(N^2) compute entirely (this is the fix — apply_whitening/build_knn_
    # graph (1600x1600)/blob_connector_flags all depend ONLY on this matrix,
    # never on the requested seed, so every anchor within the TTL window
    # reuses them — the lens auto-enters on EVERY thread open, so recomputing
    # a 1600x1600 similarity matrix per request would block other requests on
    # this worker's event loop). On a miss, acquire ONLY for the fetch, then
    # release — mirrors dossier.py's /walk (dossier.py:1027-1085), which
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
        whitened_arr: np.ndarray = cached_topics["whitened"]
        graph = cached_topics["graph"]
        blobs: set[int] = cached_topics["blobs"]
        walk_params: WalkParams = cached_topics["params"]
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

        if not keys:
            # A transient/degenerate empty scan must NEVER be frozen into the
            # cache — that would turn one bad fetch into 2 minutes of a false
            # "seed not found" for every anchor on this worker (mirrors the
            # Redis never-cache-a-degraded-payload rail at the bottom of this
            # handler). Fall straight through to the honest empty WITHOUT
            # caching; the next request re-tries the DB fresh rather than
            # waiting out the TTL.
            return _empty("seed_not_found_or_no_centroid")

        vecs_arr = np.asarray(vecs, dtype=np.float32)
        walk_params = WalkParams.from_env()
        whitened_arr = apply_whitening(vecs_arr, whitening)
        graph = build_knn_graph(whitened_arr, k=walk_params.k)
        blobs = blob_connector_flags(graph, cats, walk_params)

        _TOPICS_CACHE.clear()
        _TOPICS_CACHE.update(
            at=now, keys=keys, labels=labels, cats=cats, statuses=statuses,
            vecs=vecs_arr, whitened=whitened_arr, graph=graph, blobs=blobs,
            params=walk_params,
        )

    # (b) Compute OUTSIDE any held connection: seed lookup + the walk itself.
    # `rank_siblings` raises ValueError loudly on a contract violation
    # (misaligned/non-unit-norm arrays — Task 1's deliberate design: a silent
    # [] there would read as "this story stands alone," a dishonest empty).
    # That is a CALLER programming error, never a database fault, so it — and
    # any other compute failure — must never be mislabeled "db_error". With
    # `graph`/`blob_flags` supplied from the cache above, `rank_siblings`
    # skips its own O(N^2) graph build and does only the walk + dedup per
    # request (M5).
    # Umbrella stand-in state: set only when topic_key itself isn't a walkable
    # story (see _resolve_umbrella_anchor above). anchor_label/anchor_status
    # carry the UMBRELLA's own identity so the payload's `anchor` never
    # reports the child's label as if it were the requested story's.
    child_key: str | None = None
    anchor_label: str | None = None
    anchor_status: str | None = None
    try:
        if topic_key not in keys:
            resolved = await _resolve_umbrella_anchor(topic_key)
            if resolved is None:
                return _empty("seed_not_found_or_no_centroid")
            child_key, anchor_label, anchor_status = resolved
            if child_key not in keys:
                return _empty("seed_not_found_or_no_centroid")
            seed = keys.index(child_key)
        else:
            seed = keys.index(topic_key)

        siblings = rank_siblings(
            seed, whitened_arr, keys, labels, cats, walk_params, cap=DEFAULT_CAP,
            graph=graph, blob_flags=blobs,
        )
        if child_key is not None:
            # The child is the anchor's stand-in for the walk, not a sibling
            # of itself — it must never appear in the returned neighborhood.
            siblings = [s for s in siblings if s.topic_key != child_key]
    except ValueError as exc:
        logger.error("story siblings contract violation: %s", exc, exc_info=True)
        return _empty("internal_error")
    except Exception as exc:  # noqa: BLE001
        logger.error("story siblings compute failed: %s", exc, exc_info=True)
        return _empty("internal_error")

    # (b2) Blob CONFIRMER (Lever C2): `blobs` is the cheap entropy first-pass
    # over the WHOLE cached field — confirm ONLY the topics this response is
    # about to show (the ≤DEFAULT_CAP returned siblings, plus the umbrella
    # stand-in child when the anchor resolved through one), never the whole
    # candidate set. A sibling not in `blobs` at all was never flagged and
    # needs no confirmation call — `_confirm_ui_blob_flags` degrades any
    # DB/compute failure to 'candidate_unconfirmed' rather than raising, so
    # this step can never turn into a 500.
    key_to_idx = {k: i for i, k in enumerate(keys)}
    candidate_keys: dict[str, int] = {}
    for s in siblings:
        idx = key_to_idx.get(s.topic_key)
        if idx is not None and idx in blobs:
            candidate_keys[s.topic_key] = idx
    if child_key is not None:
        child_idx = key_to_idx.get(child_key)
        if child_idx is not None and child_idx in blobs:
            candidate_keys[child_key] = child_idx
    blob_ui = await _confirm_ui_blob_flags(candidate_keys)
    anchor_is_blob, anchor_blob_basis = (
        blob_ui.get(child_key, (False, None)) if child_key is not None else (False, None)
    )

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
        # C2: `is_blob` now reads CONFIRMED-only (membership multimodality),
        # never the raw entropy candidate flag — `blob_ui` degrades honestly
        # to 'candidate_unconfirmed' rather than silently reading as cleaner.
        confirmed_is_blob, confirmed_blob_basis = blob_ui.get(s.topic_key, (False, None))
        sib_payload.append(
            {
                "id": s.topic_key,
                "label": s.label,
                "weight": round(s.weight, 4),
                "degree": s.degree,
                "kinship": s.kinship,
                "through_blob": s.through_blob,
                "is_blob": confirmed_is_blob,
                "blob_basis": confirmed_blob_basis,
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
    if child_key is not None:
        notes.append("umbrella_resolved_via_child")

    payload = {
        "contract": "story-siblings-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anchor": {
            "id": topic_key,
            "label": anchor_label if child_key is not None else labels[seed],
            "label_status": anchor_status if child_key is not None else statuses[seed],
            "countries": anchor_countries,
            # Confirmed only for the umbrella stand-in-child case (the walk's
            # actual seed) — the plain non-umbrella anchor is never itself a
            # RETURNED node in `siblings`, so it carries no confirmable trail
            # penalty here; False/None honestly means "not evaluated", not
            # "cleared". C2, same confirmer as the siblings above.
            "is_blob": anchor_is_blob,
            "blob_basis": anchor_blob_basis,
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
