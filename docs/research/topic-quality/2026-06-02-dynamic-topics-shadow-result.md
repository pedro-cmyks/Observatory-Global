# dynamic_topics Shadow Lifecycle — Result (Phase 6, Sub-A)

**Date:** 2026-06-02
**Status:** built + validated in shadow (no product read path).
**Migration:** `048_dynamic_topics.sql` (applied). Writer:
`backend/scripts/project_dynamic_topics.py` (`--rebuild`).

## What was built

A `dynamic_topics` + `dynamic_topic_members` schema and an incremental,
idempotent projection writer that collapses emergent_clusters across
snapshots into stable topic identities (centroid cosine ≥ 0.85, sequential
greedy 1-to-1 linking, running-mean centroid) and runs a quality-gated
state machine each snapshot tick:

- `candidate → active`: persists ≥2 snapshots AND mean cohesion ≥ 0.50 AND
  aggregate signals ≥ 30 AND not a roundup.
- roundup topics are never promoted (demoted to `candidate` if seen).
- `active → deprecated` after 2 unseen ticks; `deprecated → retired` after
  4 more; `deprecated → active` on qualifying reappearance.

State transitions are pure functions (9 unit tests). The writer runs on the
off-iCloud `atlasvenv`; centroids are stored, so matching is numpy-only.

## Shadow rebuild result (89 clusters, 8 snapshots)

| state | count | roundup |
|---|---:|---:|
| active | 5 | 0 |
| candidate | 11 | 5 |
| deprecated | 5 | 0 |

Active (the data-driven taxonomy): "Economic and Social Trends",
"Russia Warns on Baltic and Zaporizhzhia", "Local News and Politics",
"Infrastructure and Public Services", "Agostina Vega Found Dead".

## Validation findings (multi-angle, honest)

1. **The lifecycle mechanism works.** Stable identities, idempotent
   upsert, correct create/match/persist, and quality-gated promotion. 5
   roundups were correctly held out of `active`.
2. **Label-regex roundup detection is a weak v1 gate.** It catches explicit
   grab-bags ("Brazil/Turkey/Romanian News Roundup", "Mixed News
   Headlines", "Daily News Roundup" — 5 found) but broad-but-generic topics
   ("Economic and Social Trends") slip through. Two iterations were needed:
   member-vote was too noisy (labels are unstable across snapshots), so the
   representative (mode) label is the identity signal; and an active topic
   that later turns roundup must be demoted (state-machine fix).
3. **Cohesion does not separate quality** — all clusters score ~0.95, so
   cohesion is a poor roundup discriminator. The robust quality gate is the
   evidence-role student noise rate (M2): a grab-bag has high noise-role
   membership. This is the documented hook for the next increment.
4. **The emergent labeler produces many geographic grab-bags.** Of the
   persistent identities, ~half are "X News Roundup" artifacts — the source
   of the junk topics flagged earlier. Either the HDBSCAN granularity or the
   DeepSeek labeling needs work, or (better) the student noise gate filters
   them downstream.

## Quality gate v2 — evidence-role student noise rate (2026-06-02)

Wired the student noise rate as the principled quality gate
(`--student-model`, migration 049 adds `dynamic_topics.noise_rate`). For
each topic, every member cluster's sample headlines are scored by the local
student (e5 + logistic); `noise_rate` = mean fraction predicted `noise`.
Promotion to `active` now also requires `noise_rate < 0.50`, and an active
topic that turns high-noise is demoted.

Rebuild with the gate: **4 active** / 12 candidate / 5 deprecated.

| topic | n | noise | gate |
|---|---:|---:|---|
| Russia Warns on Baltic and Zaporizhzhia | 224 | 0.03 | active |
| Local News and Politics | 163 | 0.24 | active |
| Infrastructure and Public Services | 152 | 0.19 | active |
| Agostina Vega Found Dead | 135 | 0.39 | active |
| **Economic and Social Trends** | 770 | **0.82** | suppressed (NOISE) |
| Brazil / Turkey / Romanian News Roundup, Mixed, Daily | — | 0.08–0.48 | suppressed (RU) |

**The two gates are complementary, validated:** the regex catches
explicitly-labeled roundups even when their student-noise is low (e.g.
"Mixed News Headlines" noise 0.08), while the student catches *unlabeled*
grab-bags the regex misses — most notably "Economic and Social Trends"
(n=770, noise 0.82), the single largest cluster, which no label rule would
have flagged. Together they leave 4 genuinely coherent, low-noise active
topics. Noise distribution is bimodal (8 topics ~0, a tail to 0.82), so the
0.50 threshold cleanly isolates the egregious grab-bag without demoting real
specific topics like "Agostina Vega Found Dead" (0.39).

## Incremental cron path (2026-06-02)

The writer now defaults to incremental mode. It hydrates existing
`dynamic_topics` from the DB by replaying persisted
`dynamic_topic_members`, then processes only emergent clusters that do not
already have a member row. `--rebuild` remains the full shadow rebuild path.

The existing `com.atlas.emergent-snapshot` cron is the trigger: the guarded
tail step in `scripts/run-emergent-snapshot.sh` runs
`project_dynamic_topics.py` after each snapshot. No new cron was added. The
step runs from `/Users/pedro/AtlasLocalWorker` with the local `mlvenv`.

Cost guardrail: lifecycle scoring is **$0 API**. The evidence-role student and
e5 embedder are local. Migration 050 caches
`emergent_clusters.role_noise_rate`, so each cluster's sample headlines are
scored once and later incremental runs skip cached clusters. Verified no-op
incremental run after rebuild: `n_new_clusters=0`, `inserted=0`, `updated=0`,
`members=0`.

## Merge/dedup refinement (2026-06-02)

Merge/dedup is now wired into the `--rebuild` consolidation path, not the live
incremental cron. The first naive idea — centroid single-linkage at 0.90 —
was rejected by dry-run evidence: Atlas centroids are dense enough that
unrelated topics such as bus crashes, portfolios, politics, and roundups sit
above 0.90 and chain-collapse into grab-bags.

The implemented merge is conservative:

- centroid cosine must pass the merge threshold,
- labels must be compatible (`SequenceMatcher` ratio >= 0.80 after
  normalization, or exact normalized match),
- any topic whose current representative label is a roundup is excluded from
  merge participation.

Latest verified rebuild after the guard (101 clusters, 9 snapshots): **21
topics**, `n_merged_topics=0`, 6 active / 12 candidate / 3 deprecated, 5
roundups, 1 high-noise topic. This is the desired behavior for the current
data: dedup exists, but it refuses unsafe merges when there are no real
duplicates.

## Decision / next increment

Phase 6 shadow lifecycle is now self-curating in live cron, cost-bounded, and
protected against unsafe centroid-only dedup. Canonical product cutover remains
last and should be a dedicated session: product surfaces can read
`dynamic_topics` only after a final contract/smoke pass confirms that visible
threads improve over the current atlas/emergent hybrid.
