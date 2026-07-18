"""Narrative lineage — a thread's BIOGRAPHY over the archive story layer.

Serves GET /api/v2/theme/{id}/lineage (contract theme-lineage-v0, frozen by
the surface lane in frontend-v2/src/lib/lineage.ts): weekly era nodes built
from narrative_lineage edges (mig 084, loaded from the census emission) +
archive_story_units, capped by the live topic's hot week.

Honesty rules (mirrors the census):
- drift = MEASURED cosine of adjacent era centroids (n_signals-weighted mean
  of unit vectors, OpenAI space), null for the first era — never a vibe;
- era gaps inside the archive span are EXPLICIT ({week, gap:true}) — the
  consumer renders spanned distance, we never fabricate a point;
- tiers are explicit: 'archive' (weekly story-unit clusters) vs 'hot' (the
  live topic itself); the Stage-B unit hole between them is crossed only by
  the labeled stitch;
- candidate stitches (near/below the measured threshold, or thresholds from
  the non-bimodal fallback) are flagged, never asserted;
- absence is honest: no stitch -> empty weeks + empty_reason, never filler.
"""
from __future__ import annotations

import html
import json
import logging
import re
from collections import Counter
from datetime import date, timedelta
from typing import Any

logger = logging.getLogger(__name__)

CONTRACT = "theme-lineage-v0"
SPACE = "openai/text-embedding-3-small"
MAX_COMPONENT_UNITS = 600   # runaway-component guard (census keeps these small)
MAX_BFS_ROUNDS = 40


def _empty(topic_id: str, reason: str) -> dict:
    return {"contract": CONTRACT, "topic_id": topic_id, "lineage_id": None,
            "weeks": [], "stitch": None, "empty_reason": reason}


def monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def parse_method_thetas(method: str | None) -> tuple[float | None, float | None]:
    """Loader method strings carry the measured taus: '... tu=0.62 uu=0.55'."""
    if not method:
        return None, None
    tu = re.search(r"\btu=([0-9.]+)", method)
    uu = re.search(r"\buu=([0-9.]+)", method)
    return (float(tu.group(1)) if tu else None,
            float(uu.group(1)) if uu else None)


def _era_centroid(vecs: list[list[float]], weights: list[float]):
    import numpy as np
    v = np.asarray(vecs, dtype=np.float32)
    w = np.asarray(weights, dtype=np.float32)[:, None]
    c = (v * w).sum(axis=0)
    n = float(np.linalg.norm(c))
    return c / n if n > 0 else None


def _receipts_from_samples(samples: Any, day: str | None) -> list[dict]:
    if isinstance(samples, str):
        try:
            samples = json.loads(samples)
        except ValueError:
            return []
    out = []
    for s in samples or []:
        if isinstance(s, str):
            out.append({"headline": html.unescape(s), "day": day})
        elif isinstance(s, dict) and s.get("headline"):
            out.append({"headline": html.unescape(s["headline"]),
                        "url": s.get("url"), "source": s.get("source"),
                        "source_lang": s.get("source_lang"),
                        "day": s.get("day") or day})
        if len(out) >= 3:
            break
    return out


def build_lineage_payload(topic_id: str, tu_edges: list[dict],
                          uu_edges: list[dict], units: list[dict],
                          hot: dict | None) -> dict:
    """Pure assembly (testable without DB).

    tu_edges: [{unit_id, sim, candidate, method}]  — this topic's stitch
    uu_edges: [{src_unit_id, unit_id, sim, edge_kind, candidate}] — component
    units:    [{id, day 'YYYY-MM-DD', label, samples, n_signals, top_cc, vec}]
    hot:      {week 'YYYY-MM-DD', label, n_signals, countries, receipts}
    """
    if not tu_edges or not units:
        return _empty(topic_id, "no_lineage")

    best = max(tu_edges, key=lambda e: e["sim"])
    theta_tu, theta_uu = parse_method_thetas(best.get("method"))

    by_id = {int(u["id"]): u for u in units}
    weeks_of_unit = {int(u["id"]): monday(date.fromisoformat(u["day"]))
                     for u in units}
    week_units: dict[date, list[int]] = {}
    for uid, wk in weeks_of_unit.items():
        week_units.setdefault(wk, []).append(uid)
    wk_sorted = sorted(week_units)

    # per-week joining edge: best incoming (src in an EARLIER week) — the
    # census builds edges src-earlier by construction (intra/adjacent/bridge)
    incoming: dict[date, dict] = {}
    for e in uu_edges:
        src, dst = int(e["src_unit_id"]), int(e["unit_id"])
        if src not in weeks_of_unit or dst not in weeks_of_unit:
            continue
        ws, wd = weeks_of_unit[src], weeks_of_unit[dst]
        if ws >= wd:
            continue  # intra edges don't join eras
        cur = incoming.get(wd)
        if cur is None or e["sim"] > cur["sim"]:
            incoming[wd] = e

    weeks_out: list[dict] = []
    prev_centroid = None
    prev_week: date | None = None
    for wk in wk_sorted:
        if prev_week is not None:
            g = prev_week + timedelta(weeks=1)
            while g < wk:  # explicit era gaps, never fabricated points
                weeks_out.append({"week": g.isoformat(), "gap": True})
                g += timedelta(weeks=1)
        uids = week_units[wk]
        rows = [by_id[u] for u in uids]
        vec_rows = [r for r in rows if r.get("vec")]
        centroid = (_era_centroid([r["vec"] for r in vec_rows],
                                  [max(int(r["n_signals"]), 1)
                                   for r in vec_rows])
                    if vec_rows else None)
        drift = None
        if prev_centroid is not None and centroid is not None:
            drift = round(float(prev_centroid @ centroid), 4)
        big = max(rows, key=lambda r: int(r["n_signals"]))
        ccs: Counter = Counter()
        for r in rows:
            for rank, cc in enumerate(r.get("top_cc") or []):
                ccs[cc] += int(r["n_signals"]) / (rank + 1)
        join = incoming.get(wk)
        weeks_out.append({
            "week": wk.isoformat(),
            "tier": "archive",
            "label": html.unescape(big["label"])[:160],
            "n_signals": sum(int(r["n_signals"]) for r in rows),
            "n_units": len(rows),
            "countries": [c for c, _ in ccs.most_common(4)],
            "drift_cos_prev": drift,
            "candidate": bool(join["candidate"]) if join else False,
            "receipts": _receipts_from_samples(big.get("samples"), big["day"]),
        })
        if centroid is not None:
            prev_centroid = centroid
        prev_week = wk

    if hot:
        # The hot node's drift is the STITCH cosine (topic centroid vs its
        # best-matched archive unit) — a measured number in the same space,
        # labeled by the stitch block; era-centroid drift is not computable
        # across the Stage-B unit hole, so we never fake one.
        weeks_out.append({
            "week": hot["week"],
            "tier": "hot",
            "label": (hot.get("label") or "")[:160] or None,
            "n_signals": int(hot.get("n_signals") or 0),
            "n_units": 1,
            "countries": list(hot.get("countries") or []),
            "drift_cos_prev": round(float(best["sim"]), 4),
            "candidate": bool(best["candidate"]),
            "receipts": list(hot.get("receipts") or []),
        })

    present = [w for w in weeks_out if not w.get("gap")]
    span = len({w["week"] for w in weeks_out})
    return {
        "contract": CONTRACT,
        "topic_id": topic_id,
        "lineage_id": f"lin-{min(by_id)}",
        "weeks": weeks_out,
        "stitch": {
            "space": SPACE,
            "theta_topic_unit": theta_tu,
            "theta_unit_unit": theta_uu,
            "topic_sim": round(float(best["sim"]), 4),
            "member_coverage": None,  # per-topic shard coverage lives in the
                                      # census artifact, not the DB — honest null
            "candidate": bool(best["candidate"]),
            "method": best.get("method"),
        },
        "meta": {
            "method": best.get("method"),
            "weeks_spanned": span,
            "weeks_present": len(present),
            "coverage_pct": round(100.0 * len(present) / span, 1) if span else 0.0,
            "n_units": len(units),
            "n_unit_edges": len(uu_edges),
        },
        "empty_reason": None,
    }


async def _expand_component(conn: Any, seed_units: list[int]) -> tuple[list[int], list[dict]]:
    """BFS over unit_unit edges from the stitched seed units."""
    seen: set[int] = set(seed_units)
    frontier = list(seed_units)
    edges: dict[tuple[int, int], dict] = {}
    for _ in range(MAX_BFS_ROUNDS):
        if not frontier or len(seen) > MAX_COMPONENT_UNITS:
            break
        rows = await conn.fetch(
            """SELECT src_unit_id, unit_id, sim, edge_kind, candidate
               FROM narrative_lineage
               WHERE kind = 'unit_unit'
                 AND (src_unit_id = ANY($1::bigint[])
                      OR unit_id = ANY($1::bigint[]))""", frontier)
        frontier = []
        for r in rows:
            key = (int(r["src_unit_id"]), int(r["unit_id"]))
            if key not in edges:
                edges[key] = {"src_unit_id": key[0], "unit_id": key[1],
                              "sim": float(r["sim"]),
                              "edge_kind": r["edge_kind"],
                              "candidate": bool(r["candidate"])}
            for uid in key:
                if uid not in seen:
                    seen.add(uid)
                    frontier.append(uid)
    return sorted(seen), list(edges.values())


async def topic_lineage(conn: Any, theme_code: str) -> dict:
    if not theme_code.startswith("dynamic-topic-"):
        return _empty(theme_code, "lineage_dynamic_topics_only")
    try:
        tid = int(theme_code.removeprefix("dynamic-topic-"))
    except ValueError:
        return _empty(theme_code, "topic_not_found")

    topic = await conn.fetchrow(
        "SELECT id, label, last_seen FROM dynamic_topics WHERE id = $1", tid)
    if not topic:
        return _empty(theme_code, "topic_not_found")

    tu_rows = await conn.fetch(
        """SELECT unit_id, sim, candidate, method
           FROM narrative_lineage
           WHERE kind = 'topic_unit' AND topic_id = $1""", tid)
    if not tu_rows:
        return _empty(theme_code, "no_lineage")
    tu_edges = [{"unit_id": int(r["unit_id"]), "sim": float(r["sim"]),
                 "candidate": bool(r["candidate"]), "method": r["method"]}
                for r in tu_rows]

    unit_ids, uu_edges = await _expand_component(
        conn, [e["unit_id"] for e in tu_edges])
    unit_rows = await conn.fetch(
        """SELECT id, day::text AS day, label, samples, n_signals, top_cc,
                  vec::text AS vec
           FROM archive_story_units WHERE id = ANY($1::bigint[])""", unit_ids)
    units = []
    for r in unit_rows:
        vec = None
        try:
            vec = json.loads(r["vec"]) if r["vec"] else None
        except ValueError:
            pass
        units.append({"id": int(r["id"]), "day": r["day"],
                      "label": r["label"], "samples": r["samples"],
                      "n_signals": int(r["n_signals"]),
                      "top_cc": list(r["top_cc"] or []), "vec": vec})

    # hot tier: the live topic itself (evidence-membership window)
    hot: dict | None = None
    try:
        ev = await conn.fetch(
            """SELECT s.id AS signal_id, s.headline, s.source_name,
                      s.source_url, s.country_code, s.source_lang,
                      s.timestamp::date::text AS day
               FROM topic_members tm
               JOIN signals_v2 s ON s.id = tm.signal_id
               WHERE tm.topic_id = $1 AND tm.role = 'evidence'
               ORDER BY s.timestamp DESC
               LIMIT 120""", theme_code)
        ccs = Counter(r["country_code"] for r in ev if r["country_code"])
        hot = {
            "week": monday(topic["last_seen"].date()).isoformat(),
            "label": topic["label"],
            "n_signals": len(ev),
            "countries": [c for c, _ in ccs.most_common(4)],
            "receipts": [
                {"headline": r["headline"], "url": r["source_url"],
                 "source": r["source_name"], "source_lang": r["source_lang"],
                 "signal_id": int(r["signal_id"]), "day": r["day"]}
                for r in ev[:3]],
        }
    except Exception as exc:  # noqa: BLE001 — hot tier is best-effort
        logger.warning("lineage hot tier failed: %s", exc)
        hot = {"week": monday(topic["last_seen"].date()).isoformat(),
               "label": topic["label"], "n_signals": 0,
               "countries": [], "receipts": []}

    return build_lineage_payload(theme_code, tu_edges, uu_edges, units, hot)
