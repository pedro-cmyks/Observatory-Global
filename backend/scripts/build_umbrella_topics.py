"""R2 — umbrella hierarchy: cluster topic centroids into parent umbrellas (#229).

Pedro's embedding-of-embeddings. Groups same-EVENT cross-country children (France
heatwave DE/FR/GB) under one umbrella via union-find over the ACTIVE topic centroids
at a cosine threshold. An umbrella is a `dynamic_topics` row (`is_umbrella=true`);
children point up via `parent_id`. Cheap (~hundreds of centroids, seconds) — the
hourly/on-read layer of the 3-speed cadence.

Honesty invariants (spec §7):
  - same-EVENT only: the threshold cut (default 0.95) is tight enough that same-THEME
    topics (all "election ...") do NOT merge — that is the taxonomy axis (#204).
  - umbrella-of-one: a topic with no cross-sibling stays flat (parent_id NULL), served
    unchanged — no fabricated grouping.
  - never deletes a CHILD (a real topic w/ history). Only the derived umbrella rows are
    rebuilt each pass. Reversible: `UPDATE dynamic_topics SET parent_id=NULL, is_umbrella
    =false` flattens to R1.

Run (repo root, DATABASE_URL set):
  python -m backend.scripts.build_umbrella_topics --dry-run              # measure
  python -m backend.scripts.build_umbrella_topics --threshold 0.95       # write
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

import asyncpg
import httpx
import json
import numpy as np

try:  # dual run-context: ROOT_DIR (backend.scripts.*) vs backend/ (scripts.*)
    from app.services.event_umbrella import (
        SAME_EVENT_SYSTEM, parse_same_event_response, plan_event_umbrellas,
        plans_to_index_groups, same_event_user, semantic_chunk_order,
    )
    from app.services.label_fold import label_fold_groups, merge_index_groups
    from scripts.ensemble.model_clients import call_llm
except ImportError:  # pragma: no cover
    from backend.app.services.event_umbrella import (
        SAME_EVENT_SYSTEM, parse_same_event_response, plan_event_umbrellas,
        plans_to_index_groups, same_event_user, semantic_chunk_order,
    )
    from backend.app.services.label_fold import (
        label_fold_groups, merge_index_groups,
    )
    from backend.scripts.ensemble.model_clients import call_llm

# Children pool = the served set. Only active, non-umbrella topics with a centroid.
_LOAD = """
    SELECT id, identity_key, label, agg_n_signals,
           COALESCE(mean_cohesion, 0.0) AS mean_cohesion, centroid_vec,
           crisis_class, category, crisis_relevant
    FROM dynamic_topics
    WHERE state = 'active' AND is_umbrella = false AND centroid_vec IS NOT NULL
    ORDER BY id
"""

# Per-topic actors (NER persons over the topic's current members) — the shared
# distinctive actor is what reconnects event fragments the semantic cut misses.
_ACTORS = """
    SELECT tm.topic_id, s.persons
    FROM topic_members tm
    JOIN signals_v2 s ON s.id = tm.signal_id
    WHERE tm.topic_id = ANY($1::text[])
      AND s.timestamp > now() - INTERVAL '48 hours'
      AND s.persons IS NOT NULL
"""


def _complete_linkage(sims: "np.ndarray", threshold: float) -> dict[int, list[int]]:
    """Greedy COMPLETE-linkage over a similarity matrix.

    Merge two groups only if ALL cross-pairs are >= threshold. Single-link/union-find
    chains transitively (A~B, B~C => A,C together even if A,C are unrelated) — that
    dragged World-Cup matches + heatwaves + unrelated topics into garbage megagroups.
    Complete-linkage forms a group only when it is genuinely mutually-tight, i.e. the
    SAME event across countries, never merely the same theme.
    """
    n = sims.shape[0]
    edges = np.argwhere(np.triu(sims >= threshold, k=1))
    order = sorted(((float(sims[i, j]), int(i), int(j)) for i, j in edges), reverse=True)
    cluster_of = list(range(n))
    members: dict[int, list[int]] = {i: [i] for i in range(n)}
    for _s, i, j in order:
        ci, cj = cluster_of[i], cluster_of[j]
        if ci == cj:
            continue
        mi, mj = members[ci], members[cj]
        if float(sims[np.ix_(mi, mj)].min()) >= threshold:  # complete linkage
            for p in mj:
                cluster_of[p] = ci
            mi.extend(mj)
            del members[cj]
    return {root: idxs for root, idxs in members.items() if len(idxs) >= 2}


def _union_find_groups(n: int, edges: list[tuple[int, int]]) -> dict[int, list[int]]:
    """Union-find over precise edges → groups of >=2. Safe here (unlike the
    single-link-on-similarity that made garbage megagroups) because the edges are
    shared-DISTINCTIVE-actor links, which do not chain unrelated topics."""
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j in edges:
        parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return {root: idxs for root, idxs in groups.items() if len(idxs) >= 2}


def _shared_actor_edges(
    topic_actors: list[set],
    sims: "np.ndarray",
    *,
    max_actor_df: int = 2,
    centroid_floor: float = 0.88,
    min_shared: int = 1,
) -> list[tuple[int, int]]:
    """Edges between topics that share a DISTINCTIVE actor — one appearing in at
    most ``max_actor_df`` topics, so ubiquitous names (Trump) never connect — and
    whose centroids clear a floor, so a coincidental shared rare name cannot merge
    two semantically unrelated topics. This reconnects the event fragments (US
    strikes / Hormuz blockade / drone attack) that share Araghchi/Khamenei/Hormuz
    into one umbrella, which the semantic complete-linkage at 0.95 keeps missing.
    """
    from collections import Counter
    df: Counter = Counter()
    for actors in topic_actors:
        for a in actors:
            df[a] += 1
    distinctive = {a for a, c in df.items() if c <= max_actor_df}
    edges: list[tuple[int, int]] = []
    n = len(topic_actors)
    for i in range(n):
        for j in range(i + 1, n):
            shared = topic_actors[i] & topic_actors[j] & distinctive
            if len(shared) >= min_shared and float(sims[i][j]) >= centroid_floor:
                edges.append((i, j))
    return edges


class UmbrellaGroupingUnavailable(RuntimeError):
    """llm-event grouping failed AND the degraded fallback is disabled —
    the caller must abort before the destructive parent_id rewrite."""


def _env_flag(name: str, *, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in ("off", "0", "false", "no")


async def _resolve_event_groups(judge, sims: "np.ndarray", threshold: float,
                                *, degraded_ok: bool):
    """Resolve the llm-event grouping with an honest degradation ladder.

    2026-07-19 fix: the degraded path used to be gated on non-empty label-fold
    groups — after THE RELABEL removed near-duplicate labels, a judge outage
    hit the abort branch and left the umbrella layer stale ("aborting before
    the destructive rebuild", scoped-snapshot.err.log:2152) even though the
    deterministic semantic complete-linkage was available all along. The
    degrade decision is now independent of label-fold state:

      judge ok + non-empty  → (groups, "llm-same-event-v1")
      judge fails/empty     → degraded_ok: (complete-linkage groups,
                              "semantic-complete-linkage (llm-degraded)")
                              else: raise UmbrellaGroupingUnavailable → the
                              caller aborts BEFORE the parent_id wipe.

    An EMPTY-but-parseable verdict counts as degraded (adversarial review
    2026-07-14: hallucinated ids / all-below-confidence must never read as a
    genuine "flatten everything").
    """
    try:
        multi = await judge()
        if not multi:
            raise RuntimeError("judge grounded 0 umbrella groups")
        return multi, "llm-same-event-v1"
    except Exception as exc:
        if not degraded_ok:
            raise UmbrellaGroupingUnavailable(repr(exc)) from exc
        print(f"llm-event grouping FAILED ({exc!r}) — DEGRADED to the "
              f"deterministic semantic complete-linkage (no abort; set "
              f"ATLAS_UMBRELLA_DEGRADED_FALLBACK=off to restore the abort)",
              file=sys.stderr)
        return (_complete_linkage(sims, threshold),
                "semantic-complete-linkage (llm-degraded)")


async def _llm_event_multi(rows, sims: "np.ndarray", *, min_confidence: float,
                           threshold: float,
                           chunk_size: int = 120) -> dict[int, list[int]]:
    """Gap-2: group active topics into SAME-EVENT umbrellas via the LLM judge —
    reconnecting the fragments the semantic cut misses (US strikes / Hormuz /
    drone attack) WITHOUT chaining unrelated topics (the shared-actor negative
    result). Returns the same {root_idx: [member_idx]} shape as _complete_linkage
    so the entire write path is reused.

    #261 slice 1 (2026-07-19): the judge is CHUNKED. 830 labels in ONE prompt
    truncated the 4k-token response → unparseable → the 07-18/19 nights lost
    EVERY LLM verdict to the degraded fallback. Now: semantic ordering
    co-locates likely same-event topics, contiguous chunks of ``chunk_size``
    are judged independently, and failure is per-chunk:

      chunk parses      → its events join the shared plan pass
      chunk fails       → ITS OWN sub-block complete-linkage (deterministic,
                          never cross-chunk chained) emitted as synthetic
                          full-confidence events — the pairs are recovered,
                          honestly, without the judge
      ALL chunks fail   → raise (the caller's degradation ladder decides)

    Cross-chunk merges the judge can no longer see are the accepted cost of
    parseability; the label-fold pre-pass + semantic ordering mitigate."""
    topics = [
        {"id": int(r["id"]), "label": r["label"], "category": r["category"],
         "crisis_relevant": r["crisis_relevant"], "is_umbrella": False}
        for r in rows
    ]
    n_topics = len(topics)
    if n_topics <= chunk_size:
        chunks = [list(range(n_topics))]
    else:
        order = semantic_chunk_order(sims)
        chunks = [order[k:k + chunk_size] for k in range(0, n_topics, chunk_size)]

    all_events: list[dict] = []
    failed_chunks: list[list[int]] = []
    async with httpx.AsyncClient(timeout=90.0) as client:
        for idxs in chunks:
            sub = [topics[i] for i in idxs]
            try:
                raw = await call_llm(
                    "deepseek", system=SAME_EVENT_SYSTEM, user=same_event_user(sub),
                    client=client, max_tokens=4000, temperature=0.0, json_mode=True,
                )
                events = parse_same_event_response(raw)
            except Exception as exc:  # LLM/transport failure = this chunk failed
                print(f"same-event judge chunk failed ({exc!r})", file=sys.stderr)
                events = None
            if events is None:
                failed_chunks.append(idxs)
            else:
                all_events.extend(events)

    if len(failed_chunks) == len(chunks):
        raise RuntimeError(
            f"same-event judge response was unparseable on ALL {len(chunks)} chunk(s)")

    for idxs in failed_chunks:
        sub_sims = sims[np.ix_(idxs, idxs)]
        for members in _complete_linkage(sub_sims, threshold).values():
            all_events.append({
                "name": "Semantic near-duplicate group (judge-degraded chunk)",
                "topic_ids": [topics[idxs[m]]["id"] for m in members],
                "confidence": 1.0,
            })
    if failed_chunks:
        print(f"same-event judge: {len(failed_chunks)}/{len(chunks)} chunk(s) "
              f"unparseable — degraded those chunks to sub-block "
              f"complete-linkage @{threshold}", file=sys.stderr)

    plans = plan_event_umbrellas(topics, all_events, min_confidence=min_confidence)
    return plans_to_index_groups([int(r["id"]) for r in rows], plans)


async def main() -> None:
    ap = argparse.ArgumentParser(description="R2: build umbrella topics over active centroids.")
    ap.add_argument("--linkage", choices=["complete", "llm-event"], default="complete",
                    help="grouping strategy: complete=semantic centroid cut (default); "
                         "llm-event=LLM same-event judge (gap-2, reconnects fragments)")
    ap.add_argument("--min-event-confidence", type=float, default=0.7,
                    help="llm-event: minimum judge confidence to form an umbrella")
    ap.add_argument("--judge-chunk-size", type=int, default=120,
                    help="llm-event: topics per judge prompt (#261 — one 830-label "
                         "prompt truncates the response; chunks are judged "
                         "independently over a semantic co-location ordering)")
    ap.add_argument("--threshold", type=float, default=0.95,
                    help="cosine similarity to merge two topics into one umbrella (same-event cut)")
    ap.add_argument("--max-actor-df", type=int, default=2,
                    help="an actor in >this many topics is not distinctive (won't connect)")
    ap.add_argument("--centroid-floor", type=float, default=0.88,
                    help="shared-actor edges also require this centroid similarity (anti-chain guard)")
    ap.add_argument("--min-shared-actors", type=int, default=1,
                    help="require at least this many shared distinctive actors per edge")
    ap.add_argument("--dry-run", action="store_true", help="measure only, no write")
    args = ap.parse_args()

    db = os.environ.get("DATABASE_URL")
    if not db:
        print("DATABASE_URL required", file=sys.stderr)
        sys.exit(2)

    conn = await asyncpg.connect(db)
    try:
        rows = await conn.fetch(_LOAD)
        n = len(rows)
        if n < 2:
            print(f"only {n} active topic(s) — nothing to umbrella")
            return

        # normalize centroids → cosine = dot product
        V = np.array([list(r["centroid_vec"]) for r in rows], dtype=np.float32)
        V /= (np.linalg.norm(V, axis=1, keepdims=True) + 1e-9)
        sims = V @ V.T

        # NOTE (2026-07-14): shared-distinctive-actor linkage (the fragmentation
        # fix for reconnecting US-strikes / Hormuz-blockade / drone-attack into one
        # US-Iran-war umbrella) is IMPLEMENTED and unit-tested below as
        # `_shared_actor_edges` + `_union_find_groups`, but NOT wired in: on live
        # data raw NER persons chain garbage (US-Iran fell under "Côte d'Ivoire"),
        # and verified subjects come back empty / garbage ("cross ormuz") /
        # ubiquitous ("donald trump"). The distinctive actors that would connect
        # the fragments are not cleanly extracted — the umbrella-by-actor is
        # blocked on NER/entity data quality (#184), the same root as the L2
        # sport mis-typing and the "who" lane. Serving stays on the semantic cut
        # until #184 lands; the mechanism is ready to wire then.
        # Lane B (2026-07-18) — LABEL-FOLD PRE-PASS. Fragments of one event often
        # carry the literal identical label ("Venezuela Earthquake Death Toll" x9):
        # a LABEL-string cluster before it is a centroid cluster, which the LLM
        # judge misses at scale (830 labels in one prompt truncate the response).
        # Deterministic, cheap, conservative (Jaccard >= 0.8 complete-linkage on
        # normalized label tokens). Reversible: ATLAS_UMBRELLA_LABEL_FOLD=off.
        fold_on = os.environ.get("ATLAS_UMBRELLA_LABEL_FOLD", "on").lower() \
            not in ("off", "0", "false")
        fold_groups = label_fold_groups([r["label"] for r in rows]) if fold_on else {}
        if fold_on:
            print(f"label-fold pre-pass: {len(fold_groups)} groups over "
                  f"{sum(len(v) for v in fold_groups.values())} near-duplicate labels")

        if args.linkage == "llm-event":
            # Degrade-by-default (2026-07-19): a judge outage falls back to the
            # deterministic semantic cut INDEPENDENTLY of label-fold state —
            # the 07-18/19 nights aborted here because the old degraded path
            # required non-empty fold_groups, which THE RELABEL had emptied.
            degraded_ok = _env_flag("ATLAS_UMBRELLA_DEGRADED_FALLBACK",
                                    default=True)
            try:
                multi, basis = await _resolve_event_groups(
                    lambda: _llm_event_multi(
                        rows, sims, min_confidence=args.min_event_confidence,
                        threshold=args.threshold,
                        chunk_size=args.judge_chunk_size),
                    sims, args.threshold, degraded_ok=degraded_ok)
            except UmbrellaGroupingUnavailable as exc:
                # Fallback explicitly disabled — NEVER wipe umbrellas on an
                # LLM outage; existing parent_id/umbrellas stay untouched.
                print(f"llm-event grouping FAILED ({exc}) — aborting before the "
                      f"destructive rebuild; existing parent_id/umbrellas "
                      f"untouched (ATLAS_UMBRELLA_DEGRADED_FALLBACK=off)",
                      file=sys.stderr)
                sys.exit(3)
        else:
            multi = _complete_linkage(sims, args.threshold)
            basis = "semantic-complete-linkage"
        if fold_on and fold_groups:
            multi = merge_index_groups(n, fold_groups, multi)
            basis = f"{basis}+label-fold-v1"
        n_children = sum(len(v) for v in multi.values())

        print(f"active_topics={n} · threshold={args.threshold} · umbrellas={len(multi)} · "
              f"children_collapsed={n_children} · singletons={n - n_children} · "
              f"top-level_after={len(multi) + (n - n_children)}")
        # sample the biggest umbrellas — eyeball same-EVENT (good) vs same-THEME (bad)
        for root, idxs in sorted(multi.items(),
                                 key=lambda kv: -sum(rows[i]["agg_n_signals"] for i in kv[1]))[:15]:
            order = sorted(idxs, key=lambda i: -rows[i]["agg_n_signals"])
            head = (rows[order[0]]["label"] or "?")[:32]
            kids = ", ".join((rows[i]["label"] or "?")[:20] for i in order[:5])
            print(f"  [{head}] <- {len(idxs)} kids: {kids}")

        if args.dry_run:
            print("DRY — no write")
            return

        written = 0
        async with conn.transaction():
            # R3.3: STABLE umbrella identity (`umbrella:<min_child_id>`) — UPSERT instead
            # of delete-all+recreate, so ids survive nightly rebuilds (drill/pin links
            # don't churn). Children never deleted — only re-parented; umbrella MEMBERS
            # (union of children's) are derived → cleared + rebuilt each pass.
            await conn.execute("UPDATE dynamic_topics SET parent_id = NULL WHERE parent_id IS NOT NULL")
            await conn.execute(
                "DELETE FROM dynamic_topic_members WHERE dynamic_topic_id IN "
                "(SELECT id FROM dynamic_topics WHERE is_umbrella = true)")
            new_keys: list[str] = []
            for root, idxs in multi.items():
                order = sorted(idxs, key=lambda i: -rows[i]["agg_n_signals"])
                head = rows[order[0]]
                cen = V[idxs].mean(axis=0)
                cen = cen / (np.linalg.norm(cen) + 1e-9)
                agg = int(sum(rows[i]["agg_n_signals"] for i in idxs))
                coh = float(np.mean([rows[i]["mean_cohesion"] for i in idxs]))
                child_ids = [int(rows[i]["id"]) for i in idxs]
                ident = f"umbrella:{min(child_ids)}"
                new_keys.append(ident)
                # R3.3 category inheritance: dominant child crisis_class (the badge);
                # a real multi-category event still reads its distribution via children.
                # inherit the dominant child CATEGORY (crisis seed OR emergent) + the
                # crisis-relevance lens by majority — so non-crisis umbrellas (World Cup)
                # carry their emergent category too, not NULL.
                child_cats = [rows[i]["category"] for i in idxs if rows[i]["category"]]
                dom_category = max(set(child_cats), key=child_cats.count) if child_cats else None
                dom_relevant = sum(1 for i in idxs if rows[i]["crisis_relevant"]) * 2 >= len(idxs)
                child_crisis = [rows[i]["crisis_class"] for i in idxs
                                if rows[i]["crisis_class"] and rows[i]["crisis_class"] != "non_crisis"]
                dom_crisis = max(set(child_crisis), key=child_crisis.count) if child_crisis else "non_crisis"
                uid = await conn.fetchval(
                    "INSERT INTO dynamic_topics "
                    "(identity_key, label, state, is_umbrella, centroid_vec, agg_n_signals, "
                    " mean_cohesion, crisis_class, category, crisis_relevant, umbrella_basis, "
                    " n_snapshots, snapshots_since_seen, is_roundup, first_seen, last_seen) "
                    "VALUES ($1,$2,'active',true,$3,$4,$5,$6,$8,$9,$10,1,0,false,"
                    " (SELECT MIN(first_seen) FROM dynamic_topics WHERE id = ANY($7::bigint[])),"
                    " (SELECT MAX(last_seen) FROM dynamic_topics WHERE id = ANY($7::bigint[]))) "
                    "ON CONFLICT (identity_key) DO UPDATE SET label=EXCLUDED.label, "
                    " centroid_vec=EXCLUDED.centroid_vec, agg_n_signals=EXCLUDED.agg_n_signals, "
                    " mean_cohesion=EXCLUDED.mean_cohesion, crisis_class=EXCLUDED.crisis_class, "
                    " category=EXCLUDED.category, crisis_relevant=EXCLUDED.crisis_relevant, "
                    " umbrella_basis=EXCLUDED.umbrella_basis, "
                    " last_seen=EXCLUDED.last_seen, updated_at=now() "
                    "RETURNING id",
                    ident, head["label"], [float(x) for x in cen], agg, coh, dom_crisis, child_ids,
                    dom_category, dom_relevant, basis)
                await conn.execute(
                    "UPDATE dynamic_topics SET parent_id = $1 WHERE id = ANY($2::bigint[])",
                    uid, child_ids)
                # umbrella members = union of the children's members (so the umbrella
                # aggregates counts/countries/evidence via the existing serving query)
                await conn.execute(
                    "INSERT INTO dynamic_topic_members "
                    "(dynamic_topic_id, emergent_cluster_id, snapshot_at, match_score, added_at) "
                    "SELECT $1, emergent_cluster_id, snapshot_at, match_score, now() "
                    "FROM dynamic_topic_members WHERE dynamic_topic_id = ANY($2::bigint[]) "
                    "ON CONFLICT DO NOTHING",
                    uid, child_ids)
                written += 1
            # stable-id cleanup: remove only umbrellas whose component vanished this pass
            await conn.execute(
                "DELETE FROM dynamic_topics WHERE is_umbrella = true "
                "AND identity_key <> ALL($1::text[])", new_keys or [""])
        print(f"WROTE {written} umbrellas over {n_children} children "
              f"(top-level serving set = {written + (n - n_children)})")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
