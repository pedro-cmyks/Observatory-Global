"""Deep history — thread-level time-as-dimension over the FULL archive.

The last surface of the time-as-dimension cycle (spec 2026-07-04): the
country-day receipts shipped (DayEvidencePanel); this closes the THREAD
level — a story's history back to May-03 (archive_story_units, mig 069) as
a clickable series, and any past day's receipts for THAT story.

Matching: the topic label is embedded (OpenAI, the units' space) and
matched against unit centroids by cosine. Match threshold is a LABEL→
CONTENT similarity — same family as the semantic lane's wild-calibrated
taus (0.25-0.35 operating band); default 0.32, always reported in the
payload so the consumer sees the knob. Tiers are honest:
  hot      real signals of THIS topic that day (assignment-backed)
  archive  story-cluster samples matched by centroid (approximate by
           construction — labeled, never passed off as assignments)
Degradation: no OPENAI key / API failure → available:false with reason.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

MATCH_TAU = 0.32
_label_vec_cache: dict[str, tuple[float, list[float]]] = {}
_CACHE_TTL = 3600.0


def _embed_label(label: str) -> list[float] | None:
    now = time.time()
    hit = _label_vec_cache.get(label)
    if hit and now - hit[0] < _CACHE_TTL:
        return hit[1]
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    # REST via urllib — the API image has no `openai` package (kept lean);
    # the embed service (EMBED_SERVICE_URL) is e5, wrong space for the
    # OpenAI-embedded archive units, so call OpenAI directly.
    try:
        import json as _json
        import urllib.request
        req = urllib.request.Request(
            "https://api.openai.com/v1/embeddings",
            data=_json.dumps({"model": "text-embedding-3-small",
                              "input": label[:500]}).encode(),
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = _json.loads(r.read())
        v = resp["data"][0]["embedding"]
        # Cost ledger — OpenAI embeddings have input tokens only.
        try:
            from app.services.ai_cost import log_ai_cost
            toks = (resp.get("usage") or {}).get("total_tokens", 0) or 0
            log_ai_cost("dossier-embed", "openai", "text-embedding-3-small", toks, 0)
        except Exception:
            pass
        _label_vec_cache[label] = (now, v)
        return v
    except Exception as exc:  # noqa: BLE001
        logger.warning("deep-history label embed failed: %s", exc)
        return None


async def _resolve_label(conn: Any, theme_code: str) -> str | None:
    if theme_code.startswith("dynamic-topic-"):
        try:
            tid = int(theme_code.removeprefix("dynamic-topic-"))
        except ValueError:
            return None
        row = await conn.fetchrow(
            "SELECT label FROM dynamic_topics WHERE id=$1", tid)
        return row["label"] if row else None
    slug = theme_code.split("--")[0].lower()
    row = await conn.fetchrow(
        "SELECT label, description FROM atlas_topics WHERE slug=$1", slug)
    if not row:
        return None
    return f"{row['label']}. {(row['description'] or '')[:200]}"


async def _archive_horizon(conn: Any) -> dict | None:
    """The queryable archive window (May-04..last-compacted day). Bounds the
    honesty label so the UI never implies reach past what exists."""
    row = await conn.fetchrow(
        "SELECT MIN(day)::text AS min_day, MAX(day)::text AS max_day, "
        "COUNT(DISTINCT day) AS days FROM archive_story_units")
    if not row or not row["min_day"]:
        return None
    return {"min_day": row["min_day"], "max_day": row["max_day"],
            "days": int(row["days"])}


async def _match_units(conn: Any, vtxt: str) -> list:
    """Story-cluster units whose centroid cosine-matches the query/label vec."""
    return await conn.fetch(
        """SELECT day::text AS day, label, samples, n_signals, top_cc,
                  1 - (vec <=> $1::halfvec) AS sim
           FROM archive_story_units
           WHERE 1 - (vec <=> $1::halfvec) >= $2
           ORDER BY day""", vtxt, MATCH_TAU)


def _build_series(rows: list) -> list[dict]:
    """Daily activity for the query.

    `units`/`signals` count everything above the (permissive) match floor —
    at that floor the count tracks TOTAL archive volume, not topic presence,
    so it is NOT the spike signal. `peak_sim` (the day's strongest cluster
    match) IS: it self-scales per query, so the consumer bars height on
    (peak_sim - tau) and genuine spikes stand out from the flat background.
    """
    series: dict[str, dict[str, float]] = {}
    for r in rows:
        s = series.setdefault(r["day"], {"units": 0, "signals": 0, "peak_sim": 0.0})
        s["units"] += 1
        s["signals"] += int(r["n_signals"])
        s["peak_sim"] = max(s["peak_sim"], round(float(r["sim"]), 3))
    return [
        {"day": d, "units": int(v["units"]), "signals": int(v["signals"]),
         "peak_sim": round(v["peak_sim"], 3)}
        for d, v in sorted(series.items())
    ]


def _archive_day_items(rows: list, day: str) -> list[dict]:
    import json as _json
    items = []
    for r in rows:
        if r["day"] != day:
            continue
        samples = r["samples"]
        if isinstance(samples, str):
            samples = _json.loads(samples)
        items.append({
            "tier": "archive",
            "cluster_label": r["label"][:160],
            "headlines": samples,
            "n_signals": int(r["n_signals"]),
            "sim": round(float(r["sim"]), 3),
            "top_cc": list(r["top_cc"] or []),
        })
    return items


async def topic_deep_history(conn: Any, theme_code: str,
                             day: str | None = None) -> dict:
    label = await _resolve_label(conn, theme_code)
    if not label:
        return {"contract": "deep-history-v0", "available": False,
                "reason": "topic label not resolvable"}
    vec = _embed_label(label)
    if vec is None:
        return {"contract": "deep-history-v0", "available": False,
                "reason": "embedding lane unavailable (no key or API error)"}
    vtxt = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

    rows = await _match_units(conn, vtxt)

    out: dict[str, Any] = {
        "contract": "deep-history-v0",
        "available": True,
        "label": label,
        "match_tau": MATCH_TAU,
        "matched_units": len(rows),
        "horizon": await _archive_horizon(conn),
        "series": _build_series(rows),
    }

    if day:
        items = _archive_day_items(rows, day)
        # hot tier: real assigned signals of this topic that day (if retained)
        try:
            hot = await conn.fetch(
                """SELECT s.headline, s.source_name, s.source_url,
                          s.country_code, s.source_lang
                   FROM topic_members tm
                   JOIN signals_v2 s ON s.id = tm.signal_id
                   WHERE tm.topic_id = $1 AND tm.role = 'evidence'
                     AND s.timestamp::date = $2::date
                   LIMIT 8""", theme_code, day)
            for h in hot:
                items.insert(0, {
                    "tier": "hot",
                    "headline": h["headline"],
                    "source": h["source_name"], "url": h["source_url"],
                    "country": h["country_code"], "lang": h["source_lang"],
                })
        except Exception as exc:  # noqa: BLE001
            logger.warning("deep-history hot tier failed: %s", exc)
        out["day"] = {"date": day, "items": items,
                      "empty_reason": None if items else
                      "no matched archive units and no retained signals "
                      "for this day"}
    return out


async def query_deep_history(conn: Any, query_text: str,
                             day: str | None = None) -> dict:
    """Free-text time-as-dimension over the archive (the STORY-panel widen).

    A research-plan query returning 0 hot anchors ("Maduro" today) still has a
    real past — this embeds the QUERY directly (same OpenAI/archive space as
    topic_deep_history) and returns the topic's daily activity across the full
    archive so the user can see WHEN it spiked and jump to that day's receipts.

    Archive-only by construction: a free-text query has no topic_id to join, so
    there is no hot tier here — day receipts are the matched story-cluster
    samples (labeled archive, never passed off as assignments). Bounded to the
    archive horizon; older is not queryable.
    """
    query_text = (query_text or "").strip()
    if len(query_text) < 2:
        return {"contract": "deep-history-v0", "available": False,
                "reason": "query too short"}
    vec = _embed_label(query_text)
    if vec is None:
        return {"contract": "deep-history-v0", "available": False,
                "reason": "embedding lane unavailable (no key or API error)"}
    vtxt = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

    rows = await _match_units(conn, vtxt)
    out: dict[str, Any] = {
        "contract": "deep-history-v0",
        "available": True,
        "basis": "query",
        "label": query_text,
        "match_tau": MATCH_TAU,
        "matched_units": len(rows),
        "horizon": await _archive_horizon(conn),
        "series": _build_series(rows),
    }
    if day:
        items = _archive_day_items(rows, day)
        out["day"] = {"date": day, "items": items,
                      "empty_reason": None if items else
                      "no matched archive story units for this day"}
    return out
