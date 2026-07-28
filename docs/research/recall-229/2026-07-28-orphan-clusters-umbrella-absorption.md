# Orphan emergent_clusters: the umbrella swallow cycle (2026-07-28)

**Status: root-caused + fixed (one guard in `project_dynamic_topics.hydrate_topics`).**
Follow-up to the used_t simulation finding (44 of the 2026-07-28 snapshot's 2,032
clusters with no `dynamic_topic_members` row, including the 70-signal
"Iran Accuses Ukraine of Caspian Attack" fragment).

## Verdict in one paragraph

The ordering hypothesis (clusters committed after `project_dynamic_topics` ran,
still queued) is **REFUTED**. The projection is retroactive by construction —
`done` = every cluster id present in `dynamic_topic_members`; anything not there
is reprocessed on the next run regardless of snapshot age — and the nightly logs
prove it runs to completion (`members written == n_new_clusters` every night:
3886/3886, 3686/3686, 3599/3599, 2149/2149). The real mechanism: **`hydrate_topics`
loaded umbrella topics into the matching population.** A cluster whose best
centroid match is an umbrella (a big diffuse event aggregate) attaches DIRECTLY
to it — so it never founds its own `dyn-…` identity — and the umbrella's member
rows are *derived* state that `build_umbrella_topics` deletes and rebuilds from
its children every night. The direct attach is deleted at the next umbrella pass,
the cluster falls out of `done`, the next projection re-adopts it, it re-attaches
to an umbrella, forever. **The cluster never serves.**

## Evidence chain (all read-only prod, 2026-07-28)

1. **Orphans persist across later successful projections** (so "still queued" is
   false): per snapshot — 07-25: 6, 07-26: 5, 07-27: 17, 07-28: 44; ≤07-24: 0.
   `centroid_vec` NULL count: 0 (the writer always persists one — not an
   invisibility bug).
2. **None of the 72 ever founded a topic**: expected identity
   `dyn-<snapshot_iso>-<cluster_id>` absent from `dynamic_topics` for 72/72
   (formula validated: the 95 founded 07-28 identities all match it).
3. **Not a crash-mid-persist**: orphaned and member-carrying clusters share the
   same per-country `created_at` (same executemany commit) and orphan cluster_ids
   INTERLEAVE with founded ones inside each country (US: founded 0,12,18…119;
   orphaned 5, 81).
4. **Projection wrote a member row for every processed cluster each night**
   (`written.members == n_new_clusters`, 4 consecutive nights) — the rows
   existed at ~06:00 UTC and were gone by 15:44 UTC. The only step that deletes
   `dynamic_topic_members` inside that window is the umbrella rebuild
   (`build_umbrella_topics.py:516-518`): `DELETE … WHERE dynamic_topic_id IN
   (SELECT id FROM dynamic_topics WHERE is_umbrella = true)`, then re-INSERT as
   the union of the children's rows. A direct attach is in no child's rows → lost.
5. **The smoking gun — 72/72 orphans best-match an umbrella at ≥ 0.88**
   (cosine vs `dynamic_topics.is_umbrella=true` centroids, range 0.899–0.988;
   MATCH_THRESHOLD = 0.88). The Caspian fragment: 0.944 vs "Iran Attack on US
   Bases and Regional Fallout". `used_t` (greedy 1-to-1) caps each umbrella at
   ONE swallow per run, which is why the count (44) sits near the umbrella count
   (67) and why the orphan set is a sparse per-country subset.
6. **Why the DeepSeek-402 era shows unlabeled orphans**: 07-25..27 orphans all
   carry NULL labels (labeler down) — coincidental to the mechanism, which is
   label-independent.
7. **Why snapshots ≤ 07-24 show 0 orphans**: escape happens when, on a later
   re-adoption pass, the umbrella is already `used_t`-taken (or a closer real
   topic appeared) and the cluster attaches to a REAL topic instead. That escape
   is exactly what produced the used_t violations (below) — the two phenomena
   are one disease.

## The 633 used_t violations: writer named

`git grep` finds exactly three writers of `dynamic_topic_members` beyond the
projection: `build_umbrella_topics.py:516-569` (delete + union-copy INSERT) and
`robot_apply_outputs.py:129-137` (fusion member move + leftover delete).

- **Umbrella union copies** account for ALL `is_umbrella = true` duplicate
  (topic, snapshot) pairs — 574 topic-nights, by construction (two children each
  holding a same-night cluster), derived rows, benign.
- **The 633 non-umbrella topic-nights** (252 active / 211 candidate / 170
  retired — matches the simulation's numbers: 77 on 07-27, 0 on 07-28) are
  **NOT robot_apply_outputs**: only 7/633 pairs carry two founding-scored
  (match_score = 1.0) rows — the fusion signature — and `FUSION g` appears 0
  times in the current runner log. **482/633 pairs have `added_at` spreads > 6h
  (7 ≤ 1min): the writer is `project_dynamic_topics` itself, across RUNS.**
  `used_t` is per-run in-memory state; when a straggler cluster of an
  already-processed snapshot is re-adopted on a later run (the umbrella-swallow
  escape path, resume passes, deferred-country stragglers), it attaches to a
  topic that already holds a same-snapshot member. No DB constraint enforces
  the invariant (PK is `(dynamic_topic_id, emergent_cluster_id)`).
- The suspicion that `robot_apply_outputs.py`'s `UPDATE dynamic_topic_members
  SET dynamic_topic_id=…` produced the bulk is **REFUTED** (it explains ≤ 7).
  Not fixed here (out of scope, non-trivial): a real fix is either an exclusion
  constraint per (topic, snapshot) or making the projection consult persisted
  same-snapshot membership before attach. The umbrella fix removes the dominant
  straggler source, so the violation rate should collapse; re-measure after a
  week.

## The fix (minimal, root cause)

`project_dynamic_topics.hydrate_topics` now skips `is_umbrella = true` rows —
umbrellas are never matching targets (and the projection stops life-cycling
them; their lifecycle is owned by `build_umbrella_topics`, which re-asserts
state on every rebuild anyway). `done` still counts every membership row, so
accounting is unchanged. No runner (.sh) edit; no schema change; NEVER
`--rebuild`; nothing truncated. Regression test:
`test_hydrate_topics_excludes_umbrellas_from_matching`.

Healing is automatic and retroactive by the projection's own design: the 72
orphans have no membership row, so the first post-fix nightly re-adopts them
with umbrellas excluded — they found real `dyn-…` identities (or attach to real
topics) and enter the normal lifecycle (`persist_min=2` still applies before
they serve).

**Deploy dependency:** the nightly Step -1 git-archive sync ships
`backend/scripts` from the CANONICAL repo's committed HEAD. The canonical
checkout currently sits on the parallel session's branch (`eclipse-dramatic-
moment`, dirty — not touched). This fix must be merged there (or to whatever
branch that checkout has at 22:00) before the night it is expected to run.

## Verification (run the morning after the first post-fix nightly)

```sql
-- (a) orphans for the NEW snapshot ≈ 0, and the 07-25..28 backlog adopted:
SELECT snapshot_at::date, count(*) FILTER (
  WHERE NOT EXISTS (SELECT 1 FROM dynamic_topic_members m
                    WHERE m.emergent_cluster_id = ec.id)) AS orphans
FROM emergent_clusters ec WHERE snapshot_at > '2026-07-24'
GROUP BY 1 ORDER BY 1;
-- (b) the Caspian fragment finally has an identity/membership:
SELECT t.id, t.identity_key, t.state, t.label
FROM dynamic_topic_members m JOIN dynamic_topics t ON t.id = m.dynamic_topic_id
WHERE m.emergent_cluster_id = (SELECT id FROM emergent_clusters
  WHERE snapshot_at::date='2026-07-28' AND cluster_id=700000);
-- (c) no NEW member rows point at umbrellas outside the umbrella pass:
SELECT count(*) FROM dynamic_topic_members m
JOIN dynamic_topics t ON t.id = m.dynamic_topic_id
WHERE t.is_umbrella AND m.added_at > now() - interval '1 day'
  AND NOT EXISTS (SELECT 1 FROM dynamic_topic_members c
                  WHERE c.emergent_cluster_id = m.emergent_cluster_id
                    AND c.dynamic_topic_id = t.id IS FALSE); -- copies only
```
Expected: (a) new snapshot ~0 and 07-25..28 rows drop to 0 as the backlog is
adopted; (b) returns a non-umbrella topic; (c) umbrella rows are all
child-copies. If (a) still shows fresh orphans, re-check for OTHER derived
topics being matched (same class of bug, different producer).
