import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query
from app import db
from app.utils import _resolve_persons, extract_domain

router = APIRouter()

_LEX_STOP = {
    "the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "is", "are",
    "was", "were", "who", "what", "when", "where", "why", "how", "this", "that",
    "with", "from", "by", "as", "at", "it", "its", "his", "her", "their", "they",
    "you", "your", "our", "not", "but", "can", "will", "has", "have", "had",
    "been", "about", "into", "over", "after", "before", "than", "then", "exposed",
    "breaking", "news", "update", "updates", "video", "photo", "report",
}


def _lex_tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", (text or "").lower())
            if w not in _LEX_STOP}


def _stem(w: str) -> str:
    """Crude suffix stripper so 'elections' ~ 'election', 'refineries' ~ 'refiner'."""
    for suf in ("ations", "ation", "ings", "ing", "ies", "ied", "es", "ed", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


# ---------------------------------------------------------------------------
# topic= filter (Eclipse/Shadow signal-stream tabs, eclipse spec §6.4)
# ---------------------------------------------------------------------------
# A signal carries no topic linkage in its own row, so scoping the stream to a
# thread means a semi-join through topic_members. Three constants bound it.

# Cap on how many topic ids one request may name. The Shadow tab passes the
# eclipse `selected[]` set, which the endpoint itself caps at limit<=30; 12 is
# comfortably above the display default (8) and keeps the ANY() array small.
_TOPIC_FILTER_MAX = 12

# Hard ceiling on the member set pulled per request. MEASURED (prod EXPLAIN):
# the cost of this filter is one PK probe into signals_v2 per member row, at
# ~0.6-1.7ms each on the shared instance, so an unbounded member set is an
# unbounded query. A black-hole topic can hold thousands of members; this caps
# the probe count deterministically (most-recently-assigned members win).
_TOPIC_MEMBER_POOL = 5000

# Slack on the member window. topic_members.assigned_at tracks the classifier
# run, not the signal timestamp: MEASURED on prod the lag is p50 +0.43h, and
# assignment can PRECEDE the signal timestamp by up to -2.45h (ingest/clock
# ordering). Widening the member window by 6h past the requested `hours` is
# >2x that measured worst case, so no signal inside the timestamp window can
# fall out of the member set. Rows on the other tail (an old signal assigned
# recently) are dropped by the timestamp filter, as they should be.
_TOPIC_ASSIGNED_SLACK_H = 6

# topic ids are atlas slugs ('gang-control-urban-security') or dynamic ids
# ('dynamic-topic-8072'). Anything else is rejected rather than passed to the
# query — the parameter is bound, not interpolated, so this is shape hygiene
# (and an honesty gate: garbage must not silently widen the stream).
_TOPIC_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def parse_topic_filter(raw: str | None, *, max_ids: int = _TOPIC_FILTER_MAX) -> list[str] | None:
    """Parse a comma-separated topic_id list into validated ids.

    Returns None when no filter was requested (serve the stream unchanged), or
    a list — possibly EMPTY — when one was. An empty list is meaningful: the
    caller asked to scope the stream and nothing valid survived, so the honest
    answer is no signals, never the unfiltered firehose relabelled.
    """
    if raw is None:
        return None
    out: list[str] = []
    for part in raw.split(","):
        tid = part.strip()
        if not tid or not _TOPIC_ID_RE.match(tid) or tid in out:
            continue
        out.append(tid)
        if len(out) >= max_ids:
            break
    return out


def _lexical_connections(headline: str, topic_rows: Any, *, limit: int = 3) -> list[dict]:
    """Keyword-overlap connections between a headline and the living thread
    labels/slugs — the fallback when nothing connects semantically."""
    h = {_stem(w) for w in _lex_tokens(headline)}
    if not h:
        return []
    scored = []
    for r in topic_rows:
        label = r["label"] or ""
        lt = {_stem(w) for w in _lex_tokens(label)}
        lt |= {_stem(w) for w in (r["slug"] or "").split("-") if len(w) >= 4}
        overlap = h & lt
        if overlap:
            scored.append((len(overlap), int(r["n"]), r["slug"], label, sorted(overlap)))
    scored.sort(reverse=True)
    return [
        {"thread_id": slug, "label": label, "basis": "keyword",
         "strength": None, "shared": words[:3]}
        for _, _, slug, label, words in scored[:limit]
    ]

@router.get("/api/v2/signals")
async def get_signals(
    country_code: str = Query(None),
    countries: Optional[str] = Query(None, description="Comma-separated country codes (e.g. IR,AE,OM)"),
    theme: str = Query(None),
    person: str = Query(None),
    hours: int = Query(24, ge=1, le=8760),
    since: Optional[datetime] = Query(None, description="Fetch signals since this timestamp"),
    limit: int = Query(50, ge=1, le=500),
    lane: Optional[str] = Query(None, description="Filter to a stream lane: analyst|sports|entertainment|general"),
    source: Optional[str] = Query(None, description="Filter to one publisher (exact source_name — the CountryBrief publisher expand, D8)"),
    topic: Optional[str] = Query(None, description=(
        "Comma-separated topic_ids (e.g. 'dynamic-topic-8072,armed-conflict-escalation'). "
        f"Restricts the stream to those threads' evidence members; max {_TOPIC_FILTER_MAX} ids. "
        "Feeds the Eclipse/Shadow stream tabs.")),
    sort: str = Query("recent", description="recent | relevance (analyst-grade ranking)"),
    own_voice_mix: bool = Query(True, description="Interleave recent non-English native-voice signals into the global stream so GDELT's English firehose doesn't bury them"),
):
    """Get raw signals with filters and velocity calculation.

    Each signal carries a ``lane`` (analyst|sports|entertainment|general) and a
    0..1 ``relevanceScore`` so the Signal Stream can promote analyst-grade items
    and separate sports/entertainment noise (#177). ``lane`` filters the result;
    ``sort=relevance`` ranks by relevance score then recency.
    """
    from app.services.stream_relevance import score_stream_signal
    topic_ids = parse_topic_filter(topic)
    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 10000")
        has_nlp_columns = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name = 'signals_v2'
                  AND column_name = 'nlp_sentiment'
            )
        """)
        sentiment_expr = "COALESCE(nlp_sentiment, sentiment)" if has_nlp_columns else "sentiment"
        nlp_persons_expr = "nlp_persons" if has_nlp_columns else "NULL::jsonb AS nlp_persons"
        nlp_framing_expr = "nlp_framing" if has_nlp_columns else "NULL::text AS nlp_framing"
        conditions = ["timestamp > NOW() - INTERVAL '%s hours'" % hours]
        params = []
        param_count = 0

        if since:
            param_count += 1
            conditions.append(f"timestamp > ${param_count}")
            params.append(since)

        if country_code:
            param_count += 1
            conditions.append(f"country_code = ${param_count}")
            params.append(country_code.upper())

        if countries and not country_code:
            codes = [c.strip().upper() for c in countries.split(',') if c.strip()]
            if codes:
                param_count += 1
                conditions.append(f"country_code = ANY(${param_count})")
                params.append(codes)

        if theme:
            param_count += 1
            conditions.append(f"${param_count} = ANY(themes)")
            params.append(theme.upper())

        if person:
            param_count += 1
            conditions.append(f"EXISTS (SELECT 1 FROM unnest(persons) p WHERE LOWER(p) LIKE LOWER(${param_count}))")
            params.append(f"%{person}%")

        if source:
            param_count += 1
            conditions.append(f"source_name = ${param_count}")
            params.append(source)

        # Topic scope (Eclipse/Shadow tabs). MEASURED plan choice (prod EXPLAIN
        # ANALYZE, 2 topics / 24h): driving from topic_members via
        # idx_topic_members_topic (topic_id, role, engine_version) → bounded
        # member set → signals_v2_pkey probes touches ~10K buffers / 1.6s warm.
        # The naive `EXISTS (... member_ref = signals_v2.id::text)` shape makes
        # the planner drive from the timestamp index instead and probe
        # topic_members 142K times: 528K buffers / 8s. Same answer, 50x the IO —
        # so the member set is materialised FIRST, on purpose.
        #
        # role/engine_version/quarantined scoping is copied verbatim from
        # routers/attention_eclipse.py: an unscoped topic_members read spans
        # both membership regimes (v1-compat ‖ unified-v2) and the quarantined
        # black-hole rows, which double-counts (the 2026-07-27 class of bug).
        if topic_ids is not None:
            if topic_ids:
                param_count += 1
                p_topics = param_count
                param_count += 1
                p_window = param_count
                conditions.append(
                    "id IN (SELECT tm.signal_id FROM topic_members tm "
                    f"WHERE tm.topic_id = ANY(${p_topics}) "
                    "AND tm.role = 'evidence' "
                    "AND tm.engine_version = 'v1-compat' "
                    "AND tm.quarantined IS NOT TRUE "
                    f"AND tm.assigned_at > NOW() - (${p_window}::int * INTERVAL '1 hour') "
                    f"ORDER BY tm.assigned_at DESC LIMIT {_TOPIC_MEMBER_POOL})"
                )
                params.append(topic_ids)
                params.append(hours + _TOPIC_ASSIGNED_SLACK_H)
            else:
                # A scope was requested and nothing valid survived parsing.
                # Honest empty beats serving the global stream under a label
                # the caller chose ("Eclipse"/"Shadow") — see parse_topic_filter.
                conditions.append("FALSE")

        where_clause = " AND ".join(conditions)

        # When ranking or filtering by lane, classification happens in Python
        # after the fetch, so pull a wider window to give the lane material.
        fetch_limit = max(limit, 200) if (lane or sort == "relevance") else limit

        # Richness ordering must stay bounded: sorting the FULL window by the
        # richness expression forces Postgres to read (and detoast) every row
        # in the window (~100K at 24h) before returning anything — measured
        # 18.5s vs the 8s timeout, the 2026-07-11 stream 500 outage. So: pull
        # a bounded pool of the most recent rows via the timestamp index (ms),
        # then richness-sort within that pool.
        pool_limit = max(fetch_limit * 4, 2000)

        rows = await conn.fetch(f"""
            SELECT * FROM (
                SELECT
                    id,
                    timestamp,
                    country_code,
                    source_name,
                    source_family,
                    source_url,
                    headline,
                    snippet,
                    source_lang,
                    {sentiment_expr} AS sentiment,
                    themes,
                    persons,
                    {nlp_persons_expr},
                    {nlp_framing_expr}
                FROM signals_v2
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT {pool_limit}
            ) recent_pool
            -- Prefer information-rich signals in the stream (has body snippet,
            -- named people, themes) over bare ones, then most recent first.
            -- Display ordering only — does not affect any counts/heat/metrics.
            ORDER BY (
                (snippet IS NOT NULL AND snippet <> '')::int
                + (array_length(persons, 1) IS NOT NULL)::int
                + (array_length(themes, 1) IS NOT NULL)::int
            ) DESC, timestamp DESC
            LIMIT {fetch_limit}
        """, *params, timeout=8.0)

        # Calculate velocity
        vel_last = await conn.fetchval(f"""
            SELECT COUNT(*) FROM signals_v2
            WHERE {where_clause} AND timestamp > NOW() - INTERVAL '1 minute'
        """, *params, timeout=5.0)

        vel_prev = await conn.fetchval(f"""
            SELECT COUNT(*) FROM signals_v2
            WHERE {where_clause} AND timestamp > NOW() - INTERVAL '2 minutes' AND timestamp <= NOW() - INTERVAL '1 minute'
        """, *params, timeout=5.0)
        
        velocity = vel_last or 0
        velocity_delta = (vel_last or 0) - (vel_prev or 0)
        velocity_pct = ((vel_last or 0) - (vel_prev or 0)) / (vel_prev or 1) * 100
        
        def _row_to_signal(r):
            themes = r['themes'] or []
            relevance = score_stream_signal(themes, r['headline'])
            return {
                "id": r['id'],
                "timestamp": r['timestamp'].isoformat(),
                "country": r['country_code'],
                "source": r['source_name'],
                "source_family": r['source_family'],
                "url": r['source_url'],
                "headline": r['headline'],
                "snippet": r['snippet'],
                "source_lang": (r['source_lang'] or '').strip() or None,
                "sentiment": float(r['sentiment'] or 0),
                "themes": themes,
                "persons": _resolve_persons(r['nlp_persons'], r['persons']),
                "framing": r['nlp_framing'],
                "lane": relevance["lane"],
                "relevanceScore": relevance["relevanceScore"],
            }

        signals = [_row_to_signal(r) for r in rows]

        if lane:
            signals = [s for s in signals if s["lane"] == lane.lower()]

        if sort == "relevance":
            signals.sort(key=lambda s: (s["relevanceScore"], s["timestamp"]), reverse=True)

        # Global stream surfacing: GDELT's English firehose + the snippet-richness
        # ordering bury non-English native voice. On the unfiltered global stream,
        # interleave recent own-voice (non en/xx) signals — ~1 in every 3 slots —
        # so the world's own press is visible, not only English coverage of it.
        # A topic-scoped stream is not the global stream: interleaving unrelated
        # own-voice signals into it would break the scope the caller asked for.
        is_global = not (country_code or countries or theme or person or lane
                         or topic_ids is not None)
        if own_voice_mix and is_global:
            seen_ids = {s["id"] for s in signals}
            own_rows = await conn.fetch(f"""
                SELECT id, timestamp, country_code, source_name, source_family, source_url,
                       headline, snippet, source_lang, {sentiment_expr} AS sentiment, themes,
                       persons, {nlp_persons_expr}, {nlp_framing_expr}
                FROM signals_v2
                WHERE {where_clause}
                  AND source_lang IS NOT NULL
                  AND source_lang NOT IN ('en', 'xx', 'un', 'und')
                  AND TRIM(source_lang) <> ''
                  AND headline IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT {limit}
            """, *params, timeout=8.0)
            own = [_row_to_signal(r) for r in own_rows if r["id"] not in seen_ids]
            if own:
                merged, oi, mi = [], 0, 0
                while (mi < len(signals) or oi < len(own)) and len(merged) < limit:
                    # 2 main : 1 own-voice
                    if mi < len(signals):
                        merged.append(signals[mi]); mi += 1
                    if mi < len(signals):
                        merged.append(signals[mi]); mi += 1
                    if oi < len(own):
                        merged.append(own[oi]); oi += 1
                signals = merged

        signals = signals[:limit]

        payload = {
            "count": len(signals),
            "velocity": {
                "signals_per_minute": velocity,
                "delta": velocity_delta,
                "percentage_change": round(velocity_pct, 1)
            },
            "signals": signals
        }
        # Echo the APPLIED scope so the caller can see what actually ran (an id
        # it named may have been rejected or truncated at the cap). Additive:
        # the key is absent entirely when no topic filter was requested, so the
        # unfiltered contract is byte-identical.
        if topic_ids is not None:
            payload["topic_filter"] = topic_ids
        return payload

@router.get("/api/v3/crisis/signals")
async def get_crisis_signals(
    hours: int = Query(24, ge=1, le=8760),
    country: str = Query(None),
    severity: str = Query(None),
    event_type: str = Query(None),
    limit: int = Query(100, ge=1, le=500)
):
    """Get crisis-related signals only with filtering options."""
    async with db.pool.acquire() as conn:
        conditions = [
            "is_crisis = TRUE",
            f"timestamp > NOW() - INTERVAL '{hours} hours'"
        ]
        params = []
        
        if country:
            params.append(country.upper())
            conditions.append(f"country_code = ${len(params)}")
        
        if severity:
            params.append(severity.lower())
            conditions.append(f"severity = ${len(params)}")
        
        if event_type:
            params.append(event_type.lower())
            conditions.append(f"event_type = ${len(params)}")
        
        where_clause = " AND ".join(conditions)
        
        rows = await conn.fetch(f"""
            SELECT 
                id, timestamp, country_code, sentiment,
                source_name, source_url, crisis_themes,
                severity, event_type, crisis_score
            FROM signals_v2
            WHERE {where_clause}
            ORDER BY 
                CASE severity 
                    WHEN 'critical' THEN 1 
                    WHEN 'high' THEN 2 
                    WHEN 'medium' THEN 3 
                    ELSE 4 
                END,
                timestamp DESC
            LIMIT {limit}
        """, *params)
        
        return {
            "signals": [
                {
                    **dict(r),
                    "timestamp": r['timestamp'].isoformat(),
                }
                for r in rows
            ],
            "count": len(rows),
            "filters": {
                "hours": hours, 
                "country": country, 
                "severity": severity,
                "event_type": event_type
            }
        }

@router.get("/api/v3/crisis/summary")
async def get_crisis_summary(hours: int = Query(24, ge=1, le=8760)):
    """Get summary statistics for crisis signals."""
    async with db.pool.acquire() as conn:
        # Overall stats
        stats = await conn.fetchrow(f"""
            SELECT 
                COUNT(*) as total_signals,
                COUNT(*) FILTER (WHERE is_crisis) as crisis_signals,
                COUNT(DISTINCT country_code) FILTER (WHERE is_crisis) as countries_affected,
                COUNT(DISTINCT source_name) FILTER (WHERE is_crisis) as sources_reporting,
                AVG(crisis_score) FILTER (WHERE is_crisis) as avg_crisis_score
            FROM signals_v2
            WHERE timestamp > NOW() - INTERVAL '{hours} hours'
        """)
        
        # By severity
        by_severity = await conn.fetch(f"""
            SELECT severity, COUNT(*) as count, AVG(sentiment) as avg_sentiment
            FROM signals_v2
            WHERE is_crisis = TRUE AND timestamp > NOW() - INTERVAL '{hours} hours'
            GROUP BY severity
            ORDER BY 
                CASE severity 
                    WHEN 'critical' THEN 1 
                    WHEN 'high' THEN 2 
                    WHEN 'medium' THEN 3 
                    ELSE 4 
                END
        """)
        
        # By event type
        by_type = await conn.fetch(f"""
            SELECT event_type, COUNT(*) as count, AVG(sentiment) as avg_sentiment
            FROM signals_v2
            WHERE is_crisis = TRUE AND timestamp > NOW() - INTERVAL '{hours} hours'
            GROUP BY event_type
            ORDER BY count DESC
        """)
        
        # Top countries with crises
        top_countries = await conn.fetch(f"""
            SELECT 
                country_code, 
                COUNT(*) as count, 
                AVG(crisis_score) as avg_score,
                AVG(sentiment) as avg_sentiment
            FROM signals_v2
            WHERE is_crisis = TRUE AND timestamp > NOW() - INTERVAL '{hours} hours'
            GROUP BY country_code
            ORDER BY count DESC
            LIMIT 10
        """)
        
        return {
            "period_hours": hours,
            "totals": dict(stats),
            "by_severity": [
                {
                    **dict(r), 
                    "avg_sentiment": float(r['avg_sentiment'] or 0)
                } 
                for r in by_severity
            ],
            "by_event_type": [
                {
                    **dict(r),
                    "avg_sentiment": float(r['avg_sentiment'] or 0)
                }
                for r in by_type
            ],
            "top_countries": [
                {
                    **dict(r), 
                    "avg_score": float(r['avg_score'] or 0),
                    "avg_sentiment": float(r['avg_sentiment'] or 0)
                }
                for r in top_countries
            ]
        }



@router.get("/api/v2/signal/{signal_id}/context")
async def get_signal_context(
    signal_id: int,
    hours: int = Query(168, ge=1, le=8760),
    neighbors: int = Query(4, ge=1, le=10),
):
    """Per-signal narrative context (#228 §2.3 SignalDetail rebuild).

    Returns the Narrative Threads this signal is assigned to (the product
    story model — primary) and semantically-nearest signals from the
    persisted embedding corpus (labeled, gate-status-tagged — replaces the
    old 'related by any shared GDELT theme' heuristic that connected a
    Pakistan mosque blast to an Illinois tornado via 'Disaster Fire').

    Uses the signal's OWN stored embedding (mig 054), so no embed-service
    round trip: signals not yet embedded return neighbors=[] with a note.
    """
    from app.services.research_semantic import is_junk_headline
    import html as _html

    if db.pool is None:
        return {"signal_id": signal_id, "threads": [], "semantic_neighbors": [],
                "notes": ["database unavailable"]}

    async with db.pool.acquire() as conn:
        await conn.execute("SET statement_timeout = 8000")

        threads = await conn.fetch(
            """
            SELECT t.slug, t.label, a.gate_kept, a.gate_score, a.model_version,
                   a.confidence
            FROM signal_topic_assignments a
            JOIN atlas_topics t ON t.id = a.topic_id
            WHERE a.signal_id = $1
              AND a.model_version IN ('theme-hint-lex-v2', 'semantic-discussion-v1')
            ORDER BY a.gate_score DESC NULLS LAST
            LIMIT 5
            """,
            signal_id,
        )

        notes: list[str] = []
        neighbor_rows: list = []

        own_headline = await conn.fetchval(
            "SELECT headline FROM signals_v2 WHERE id = $1", signal_id,
        )

        # Stored embedding (nightly M1 corpus). Pass it back as a constant so the
        # HNSW index serves `vec <=> $const` (a joined column forces a seq scan).
        own_vec = await conn.fetchval(
            "SELECT vec::text FROM signal_embeddings WHERE signal_id = $1",
            signal_id,
        )
        # On-demand embed: if the item isn't in the nightly corpus yet (cron lag)
        # but the embed service is up, embed its headline NOW — same 'passage:'
        # prefix as the stored corpus — so it connects SEMANTICALLY instead of
        # falling to the keyword lane. Runs off the event loop; degrades silently.
        embedded_on_demand = False
        if not own_vec and own_headline:
            try:
                import asyncio as _asyncio
                from app.services.research_semantic import embed_texts
                _hl = _html.unescape(own_headline)
                vecs = await _asyncio.to_thread(embed_texts, [f"passage: {_hl}"])
                if vecs and vecs[0]:
                    own_vec = "[" + ",".join(f"{x:.6f}" for x in vecs[0]) + "]"
                    embedded_on_demand = True
            except Exception:
                pass

        if own_vec:
            neighbor_rows = await conn.fetch(
                f"""
                SELECT s.id, s.headline, s.country_code, s.source_name,
                       s.source_url, s.timestamp,
                       1 - (e.vec <=> $2::halfvec) AS similarity,
                       nt.slug  AS thread_slug,
                       nt.label AS thread_label
                FROM signal_embeddings e
                JOIN signals_v2 s ON s.id = e.signal_id
                LEFT JOIN LATERAL (
                    -- the neighbor's top thread: how a no-topic item (forum)
                    -- connects to the living threads, via who it sits next to.
                    SELECT t.slug, t.label
                    FROM signal_topic_assignments sta
                    JOIN atlas_topics t ON t.id = sta.topic_id
                    WHERE sta.signal_id = s.id
                    ORDER BY sta.gate_score DESC NULLS LAST
                    LIMIT 1
                ) nt ON true
                WHERE e.signal_id <> $1
                  AND s.timestamp > NOW() - INTERVAL '{int(hours)} hours'
                ORDER BY e.vec <=> $2::halfvec
                LIMIT {int(neighbors * 4)}
                """,
                signal_id,
                own_vec,
            )
            if embedded_on_demand:
                notes.append("embedded on-demand (not in the nightly corpus yet)")
        else:
            notes.append("signal not embedded yet; semantic neighbors unavailable")

    own_key = _html.unescape(own_headline or "").strip().lower()
    seen = {own_key} if own_key else set()
    semantic_neighbors = []
    # Truncated-thread connections (#168/#234): the threads this item connects to
    # via the threads its semantic neighbours belong to. slug -> best similarity.
    neighbor_threads: dict[str, dict] = {}
    for r in neighbor_rows:
        sim = float(r["similarity"])
        if sim < 0.60:  # context view: looser than evidence retrieval (0.84),
            continue    # but everything below carries its similarity visibly
        headline = _html.unescape(r["headline"] or "")
        if is_junk_headline(headline):
            continue
        key = headline.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        slug = r["thread_slug"]
        if slug:
            prev = neighbor_threads.get(slug)
            if prev is None or sim > prev["sim"]:
                neighbor_threads[slug] = {"label": r["thread_label"], "sim": sim}
        if len(semantic_neighbors) < neighbors:
            semantic_neighbors.append({
                "signal_id": int(r["id"]),
                "headline": headline,
                "country_code": r["country_code"],
                "source": r["source_name"],
                "url": r["source_url"],
                "timestamp": r["timestamp"].isoformat() if r["timestamp"] else None,
                "similarity": round(sim, 4),
                "gate_status": "assigned" if slug else "below_gate",
            })
        # keep scanning to accumulate neighbor_threads beyond the display cap

    own_slugs = {t["slug"] for t in threads}
    connected_threads = []
    for t in threads:
        is_disc = t["model_version"] == "semantic-discussion-v1"
        connected_threads.append({
            "thread_id": t["slug"],
            "label": t["label"],
            "basis": "member",
            # A forum post that was semantically attached is a DISCUSSION member,
            # never evidence: strength is its match similarity, gate_kept false.
            "discussion": is_disc,
            "strength": (float(t["confidence"]) if is_disc and t["confidence"] is not None
                         else (float(t["gate_score"]) if t["gate_score"] is not None else None)),
            "gate_kept": False if is_disc else (
                bool(t["gate_kept"]) if t["gate_kept"] is not None else None),
        })
    for slug, info in sorted(
        neighbor_threads.items(), key=lambda kv: kv[1]["sim"], reverse=True
    ):
        if slug in own_slugs:
            continue
        connected_threads.append({
            "thread_id": slug,
            "label": info["label"],
            "basis": "semantic",
            "strength": round(info["sim"], 4),
        })

    # LEXICAL fallback (the embed service can be down and fresh items aren't
    # embedded yet): if nothing connected semantically, match the headline's
    # keywords against the labels of the LIVING threads so the item still lands
    # somewhere true ("africa elections" -> "Election legitimacy dispute").
    if not connected_threads and own_headline:
        try:
            async with db.pool.acquire() as lex_conn:
                await lex_conn.execute("SET statement_timeout = 5000")
                topic_rows = await lex_conn.fetch(
                    """
                    SELECT at.slug, at.label, COUNT(*)::int AS n
                    FROM signal_topic_assignments a
                    JOIN atlas_topics at ON at.id = a.topic_id
                    JOIN signals_v2 s ON s.id = a.signal_id
                    WHERE a.model_version = 'theme-hint-lex-v2' AND a.gate_kept = true
                      AND s.timestamp > NOW() - INTERVAL '168 hours'
                    GROUP BY at.slug, at.label
                    """
                )
            connected_threads = _lexical_connections(own_headline, topic_rows)
            if connected_threads:
                notes.append("connected by keyword (no embedding yet)")
        except Exception:
            pass

    return {
        "signal_id": signal_id,
        "threads": [
            {
                "slug": t["slug"],
                "label": t["label"],
                "gate_kept": bool(t["gate_kept"]) if t["gate_kept"] is not None else None,
                "gate_score": float(t["gate_score"]) if t["gate_score"] is not None else None,
                "discussion": t["model_version"] == "semantic-discussion-v1",
            }
            for t in threads
        ],
        # Truncated-thread "Where this fits": connected threads (member first,
        # then semantic), each basis-badged. Honest empty when nothing connects.
        "connected_threads": connected_threads,
        "semantic_neighbors": semantic_neighbors,
        "match_basis": "signal_embedding",
        "notes": notes,
    }
