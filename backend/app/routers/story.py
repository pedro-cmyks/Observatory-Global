"""Story Lens — the measured neighborhood of one thread.

GET /api/v2/story/{thread_id}/siblings

Read-only, ranking-with-receipts (spec docs/superpowers/specs/2026-07-28-
story-lens-design.md §6; the ranker itself is app/services/story_siblings.py
— pure, no DB, deliberately NEVER a merge gate; the transitive-collapse
failure that killed evidence-overlap as a merge rule (recall-229 record)
cannot recur here because nothing is written and no closure is taken).

Every sibling carries the measured WHY (whitened cosine + kinship degree,
plus a shared-country receipt when one exists) — never a silent rank.
"""
from __future__ import annotations

import json
import logging
import re
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
    it before any Redis/DB work, not merely treat it as "not found"."""
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
    relation without a measured basis; an honest empty (no DB / no whitening
    / seed not found) is a first-class response, not an error."""
    topic_key = _normalize_thread_id(thread_id)
    if not topic_key:
        return _empty("invalid_thread_id")

    cache_key = f"story_sib:v1:{topic_key}"
    redis = _redis_client()
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as exc:  # noqa: BLE001
            logger.warning("story siblings cache read failed: %s", exc)

    if db.pool is None:
        return _empty("database unavailable")

    try:
        whitening = load_whitening()
    except Exception as exc:  # noqa: BLE001
        logger.warning("story siblings whitening unavailable: %s", exc)
        return _empty("whitening_unavailable")

    try:
        async with db.pool.acquire() as conn:
            await conn.execute("SET statement_timeout = 15000")
            rows = await conn.fetch(_TOPICS_SQL)

            keys: list[str] = []
            labels: list[str] = []
            cats: list[str | None] = []
            statuses: list[str | None] = []
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

            if topic_key not in keys:
                return _empty("seed_not_found_or_no_centroid")

            seed = keys.index(topic_key)
            whitened = apply_whitening(np.asarray(vecs, dtype=np.float32), whitening)
            siblings = rank_siblings(
                seed, whitened, keys, labels, cats, WalkParams.from_env(), cap=DEFAULT_CAP,
            )

            # Country receipts for the anchor + returned siblings only — one
            # bounded query over a short ANY() list, never the whole graph.
            want = [topic_key] + [s.topic_key for s in siblings]
            foot: dict[str, list[tuple[str, int]]] = {}
            try:
                crows = await conn.fetch(_COUNTRIES_SQL, want)
                for cr in crows:
                    foot.setdefault(cr["topic_id"], []).append(
                        (cr["country_code"], int(cr["n"]))
                    )
            except Exception as exc:  # noqa: BLE001
                logger.warning("story siblings country footprint failed: %s", exc)
    except ValueError as exc:
        # rank_siblings raises loudly on misaligned/non-unit-norm inputs — a
        # CALLER programming error (Task 1's deliberate design: a silent []
        # there would read as "this story stands alone," a dishonest empty).
        # That is NOT a database fault; mislabeling it "db_error" would hide
        # a real contract violation behind a transient-looking reason code.
        logger.error("story siblings contract violation: %s", exc)
        return _empty("internal_error")
    except Exception as exc:  # noqa: BLE001
        logger.warning("story siblings query failed: %s", str(exc)[:200])
        return _empty("db_error")

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
        "notes": [],
    }

    if redis is not None:
        try:
            await redis.setex(cache_key, _CACHE_TTL_S, json.dumps(payload, default=str))
        except Exception as exc:  # noqa: BLE001
            logger.warning("story siblings cache write failed: %s", exc)
    return payload
