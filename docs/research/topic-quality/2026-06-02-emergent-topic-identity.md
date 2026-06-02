# Emergent Topic Identity — Resolver Result (Phase 6, Sub-A')

**Date:** 2026-06-02
**Status:** validated (read-only). No schema, no writes.
**Inputs:** 81 `emergent_clusters` rows across 7 snapshots (2026-05-31 → 2026-06-02).
**Artifact:** `2026-06-02-emergent-topic-identity.json`.

## Question

Are two emergent clusters from different snapshots the *same topic*? If
cross-snapshot identity is not coherent, the whole `dynamic_topics`
lifecycle (create/merge/retire) is built on sand. This resolver tests it
read-only before any schema is committed.

## Method

Centroid cosine similarity over the stored `centroid_vec`. Sequential
time-ordered greedy 1-to-1 linking into identities, cross-checked against
global single-linkage agglomerative, swept over thresholds 0.70–0.95,
with label-cosine and `sample_signal_ids` Jaccard as diagnostic signals.

## Threshold sweep

| thr | identities | persistent (≥2 snap) | singletons | global groups | intra spread | jaccard≠0 | label cos |
|----:|----:|----:|----:|----:|----:|----:|----:|
| 0.70 | 16 | 15 | 1 | 1 | 0.080 | 0.0 | 0.823 |
| 0.75 | 16 | 15 | 1 | 1 | 0.080 | 0.0 | 0.823 |
| 0.80 | 16 | 15 | 1 | 1 | 0.080 | 0.0 | 0.823 |
| **0.85** | **21** | **15** | **6** | 2 | 0.065 | 0.0 | 0.823 |
| 0.90 | 31 | 15 | 16 | 11 | 0.037 | 0.0 | 0.841 |
| 0.95 | 43 | 12 | 31 | 42 | 0.012 | 0.0 | 0.849 |

## Findings (multi-angle validation)

1. **Cross-snapshot identity IS coherent.** The recurring core —
   `n_persistent = 15` — is stable across the entire 0.70–0.90 threshold
   band. The count of real recurring topics does not depend on a tuned
   threshold, which is the strongest possible evidence that identity is a
   real signal and not an artifact.

2. **Member overlap is dead as an identity signal.** `sample_signal_ids`
   Jaccard between linked clusters is **0.0 at every threshold** —
   snapshots use different time windows, so they share no member signals.
   Confirms the prior hypothesis with data: drop member overlap.

3. **Label confirms centroid.** Linked clusters have label-cosine
   ~0.82–0.85. The centroid decision and the LLM label agree, so label is
   a valid confirmatory signal but is not needed as the primary one.
   **Answer to "what defines identity": centroid primary, label
   confirmatory, member-overlap discarded.**

4. **Global single-linkage is a poor cross-check.** It collapses
   everything into 1 group at thr ≤ 0.80 (transitive chaining) and only
   converges with the sequential linker at 0.95. The **sequential linker
   is the trustworthy method**; global single-linkage is not a reliable
   arbiter here.

5. **Operating threshold = 0.85** (the knee). Below it, one-offs hide
   (singletons=1); at 0.90+ singletons explode (16, then 31) as the same
   topic fragments. 0.85 keeps the 15-topic core with coherent identities
   (intra spread 0.065) and only 6 singletons.

6. **20/80 coverage worry, quantified.** 15 recurring emergent topics vs
   **30 active `atlas_topics`**. The static taxonomy carries ~2× the
   topics that actually recur in live data. Combined with M3 (static
   topics like `mining-royalty-risk` and `fuel-subsidy-unrest` score 0%
   precision), the static taxonomy is bloated with non-recurring / dead
   topics. The emergent layer surfaces a tighter, data-driven set.

7. **Some persistent identities are generic roundup artifacts** —
   "Mixed News Headlines", "Daily News Roundup" persist across snapshots
   alongside real topics ("Iran Nuclear Talks Stance" 6 snaps, "Public
   Safety and Crime" 7 snaps, "Russian and Ukrainian Drone Strikes" 3).
   So persistence alone is not topic quality; the lifecycle must still
   suppress roundup identities (ties to the evidence-role noise tier).

## Decision

- **Identity resolution works.** Proceed with the `dynamic_topics`
  lifecycle on this foundation.
- **Identity signal:** centroid cosine, sequential linking, threshold
  **0.85**. Label as a confirmatory tiebreak; member overlap discarded.
- **A `dynamic_topics` row must carry:** stable identity id, `first_seen`
  / `last_seen`, `n_snapshots` (persistence), member cluster list,
  representative label, aggregate `n_signals`, and a quality flag to
  suppress roundup identities.
- **Persistence ≥ 2 snapshots** is the natural birth criterion for a
  candidate topic; singletons stay provisional.

## Next increment

Sub-A (schema + state machine), now informed by this result: the table
keys on a stable identity id, tracks persistence, and carries a
roundup/noise suppression flag. Then the create/retire loop in shadow.
