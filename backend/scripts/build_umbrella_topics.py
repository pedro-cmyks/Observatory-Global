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
import numpy as np

# Children pool = the served set. Only active, non-umbrella topics with a centroid.
_LOAD = """
    SELECT id, identity_key, label, agg_n_signals,
           COALESCE(mean_cohesion, 0.0) AS mean_cohesion, centroid_vec,
           crisis_class, category, crisis_relevant
    FROM dynamic_topics
    WHERE state = 'active' AND is_umbrella = false AND centroid_vec IS NOT NULL
    ORDER BY id
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


async def main() -> None:
    ap = argparse.ArgumentParser(description="R2: build umbrella topics over active centroids.")
    ap.add_argument("--threshold", type=float, default=0.95,
                    help="cosine similarity to merge two topics into one umbrella (same-event cut)")
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

        multi = _complete_linkage(sims, args.threshold)
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
                    " mean_cohesion, crisis_class, category, crisis_relevant, n_snapshots, "
                    " snapshots_since_seen, is_roundup, first_seen, last_seen) "
                    "VALUES ($1,$2,'active',true,$3,$4,$5,$6,$8,$9,1,0,false,"
                    " (SELECT MIN(first_seen) FROM dynamic_topics WHERE id = ANY($7::bigint[])),"
                    " (SELECT MAX(last_seen) FROM dynamic_topics WHERE id = ANY($7::bigint[]))) "
                    "ON CONFLICT (identity_key) DO UPDATE SET label=EXCLUDED.label, "
                    " centroid_vec=EXCLUDED.centroid_vec, agg_n_signals=EXCLUDED.agg_n_signals, "
                    " mean_cohesion=EXCLUDED.mean_cohesion, crisis_class=EXCLUDED.crisis_class, "
                    " category=EXCLUDED.category, crisis_relevant=EXCLUDED.crisis_relevant, "
                    " last_seen=EXCLUDED.last_seen, updated_at=now() "
                    "RETURNING id",
                    ident, head["label"], [float(x) for x in cen], agg, coh, dom_crisis, child_ids,
                    dom_category, dom_relevant)
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
