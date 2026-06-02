# Emergent Topic Identity Resolver — Design (Phase 6, Sub-A')

Date: 2026-06-02
Status: implemented in shadow through Sub-A / quality gate / incremental cron / guarded rebuild dedup
Series: Phase 6 (`dynamic_topics` lifecycle), increment 1 of 6.

## Context

Phase 6 will replace the static `atlas_topics` taxonomy with a
self-curating `dynamic_topics` lifecycle (create / promote / merge /
retire) sourced from the emergent HDBSCAN layer. The core risk for the
whole phase is **topic identity**: are two emergent clusters from
different snapshots the *same topic*? If identity resolution is wrong,
every downstream lifecycle event (birth, persistence, merge, death) is
noise.

This increment builds a **read-only identity resolver** over the
`emergent_clusters` snapshots that already exist (7 snapshots, ~81
clusters). It validates whether cross-snapshot identity is coherent,
how many real topics exist vs the static taxonomy, and which signal
defines identity — *before* committing to a schema. Nothing is written
to the DB; no production surface changes.

## Goals

1. Group the ~81 clusters across snapshots into stable **topic
   identities** using centroid cosine similarity.
2. Validate identity coherence from multiple angles (sequential vs
   global, threshold sweep, signal agreement, intra-identity stability).
3. Produce a report that answers: how many real topics exist, where the
   threshold "knee" is, whether label/member-overlap add discriminative
   value, and what fields a `dynamic_topics` schema must carry.

Non-goals: no schema, no writes, no lifecycle state machine, no product
read-path change. Those are later Phase 6 increments.

## Implementation status (2026-06-02)

This spec's identity-risk investigation led to the Phase 6 shadow lifecycle:

- `048_dynamic_topics.sql` adds `dynamic_topics` and
  `dynamic_topic_members`.
- `049_dynamic_topics_noise_rate.sql` adds topic-level student noise gating.
- `050_emergent_cluster_noise_cache.sql` caches per-cluster noise in
  `emergent_clusters.role_noise_rate`.
- `backend/scripts/project_dynamic_topics.py` now supports full `--rebuild`
  and default incremental mode.
- The existing emergent snapshot cron runs the incremental lifecycle after
  each snapshot from `/Users/pedro/AtlasLocalWorker`.
- Merge/dedup exists only in the rebuild path and requires centroid similarity
  plus compatible labels; roundups are excluded from merge participation.

No product read path has been cut over. `dynamic_topics` remains shadow-only.

## Architecture

Single read-only script `backend/scripts/emergent_topic_identity_resolver.py`,
run on the off-iCloud `mlvenv` (asyncpg + numpy; e5 only for the
label-cosine diagnostic — primary matching uses the stored
`centroid_vec`, so no torch is needed for the core path).

### Components (pure functions, testable without DB)

1. **Loader** — read all `emergent_clusters` rows: `centroid_vec`,
   `label`, `description`, `sample_signal_ids`, `top_country_codes`,
   `snapshot_at`, `cluster_id`, `n_signals`, `cohesion`. Skip + count
   rows with null `centroid_vec`.
2. **Sequential linker** — process snapshots in time order. For each
   snapshot's clusters, greedily one-to-one match to the best existing
   identity with centroid cosine ≥ threshold; unmatched clusters open a
   new identity. Track per identity: member clusters, snapshots spanned,
   first_seen / last_seen.
3. **Global cross-check** — agglomerative clustering of all centroids at
   the same cosine threshold; compare identity count and member
   agreement vs the sequential linker.
4. **Signal diagnostics** — for each accepted match, also compute label
   cosine (e5) and `sample_signal_ids` Jaccard; report whether they agree
   with the centroid decision (data-driven answer to "what signal
   defines identity").
5. **Threshold sweep** — cosine thresholds 0.70–0.95; report
   #identities, #persistent (≥2 snapshots), #singletons, mean lifespan
   to locate the knee.

### Data flow

DB → loader → for each threshold { sequential linker + global cross-check
+ signal diagnostics } → report (JSON + MD).

## Output

`docs/research/topic-quality/2026-06-02-emergent-topic-identity.{json,md}`:

- **Identity timelines** — stable id, representative label,
  first_seen/last_seen, #snapshots, member clusters, aggregate n_signals.
- **Threshold table** — per threshold: #identities, #persistent,
  #singletons, mean lifespan; knee flagged.
- **Signal agreement** — % of matches where label cosine / Jaccard agree
  with the centroid decision; averages.
- **Cross-check** — sequential vs global agreement.
- **Schema implications** — what a `dynamic_topics` row must carry
  (stable id, first/last_seen, member list, representative label).

## Validation (what this increment proves)

1. Cross-snapshot identity is coherent: a threshold exists where most
   identities persist cleanly (not all singletons, not collapsed to one).
2. Real topic count vs static `atlas_topics` (measures the 20/80 worry
   with data).
3. Which signal defines identity (centroid alone vs + label/overlap).
4. Stability: persistent identities have low intra-identity centroid
   variance.

## Error handling

- null `centroid_vec` → skip + count.
- < 2 snapshots available → abort with a clear message (needs history).
- threshold with no matches → identities degrade cleanly to raw clusters.

## Testing

Unit tests of pure functions (synthetic centroids → known identities,
Jaccard, threshold logic, timeline grouping); no DB. Plus a smoke run
over the 81 real clusters.
