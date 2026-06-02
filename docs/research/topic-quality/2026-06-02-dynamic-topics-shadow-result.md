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

## Decision / next increment

Sub-A is done and validated in shadow. Next: wire the **evidence-role
student noise rate** as the real quality gate (replacing label regex), and
add the incremental cron path (hydrate existing dynamic_topics from the DB
and match new snapshots, instead of `--rebuild`). Canonical product cutover
stays last.
