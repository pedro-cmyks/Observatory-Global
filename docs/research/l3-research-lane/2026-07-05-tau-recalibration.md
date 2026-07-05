# L3 semantic-lane tau recalibration — wild-junk-quantile (W2a-i)

**Date:** 2026-07-05 · **Script:** `backend/scripts/recalibrate_research_taus.py`
(SQL-only over pgvector; no local model) · **Sample:** 800 random recent signals
(96h) vs active centroids; 800 pseudo-queries vs 3,000-signal disjoint corpus.

## Result

| Basis | Current tau | Junk p50 | Junk p95 | Junk p99 | Suggested (0.5% clearance) |
|---|---|---|---|---|---|
| member_centroid | 0.80 | **0.8646** | 0.9184 | 0.944 | 0.9615 |
| signal_headline | 0.84 | **0.8873** | 0.939 | 0.9808 | 0.9901 |

Pool health at measurement time: **15 active centroids** (collapsed —
post-universe-collapse recovery; healthy ≥80).

## Reading

1. **The current taus are UNDER the junk median.** More than half of a random
   recent corpus clears 0.80 against the centroid pool, and finds a ≥0.84
   headline neighbor. The 2026-06-10/11 calibrations were honest on the ~100K
   corpus; at ~1M+ embeddings the max-similarity junk floor moved up past them
   (more corpus → nearer nearest-neighbors). Same e5-noise-floor story as the
   06-29 ablations and the 07-04 sem-assign calibration failure.

2. **Caveats — why we did NOT blindly bump to 0.96/0.99:**
   - member_centroid was measured against a COLLAPSED pool (15 running-mean
     centroids) — exactly the regime the new substrate guard (W2a) suppresses.
     The measured floor is the floor of the degenerate regime; re-measure when
     the pool recovers ≥80.
   - signal_headline used random HEADLINES as pseudo-queries. Headlines have
     syndicated near-duplicates in-corpus (max = 1.0 = exact dupes survived
     write-dedup across runs), so this over-estimates the junk floor for real
     USER queries (short, often cross-lingual, not headline-shaped). The honest
     signal-lane tau needs real query samples — search telemetry collects them
     (`search_query` events, 13 so far).

3. **What protects the user TODAY:** (a) the substrate guard suppresses the
   member_centroid basis under a thin pool (visible `lane_degraded` gap);
   (b) every semantic evidence item now carries the two-tier gate label
   (verified/extended/assigned/below_gate, W2b) — junk that sneaks past the
   tau still shows as UNVERIFIED, never as coverage.

## Actions

- [x] Substrate guard shipped (`substrate_min_centroids=80`, router-wired).
- [x] Two-tier labels shipped (`gate_tier_for`).
- [ ] Re-run this script when pool ≥80 → set member_centroid tau from the
      healthy-pool floor (expect ~0.86-0.90).
- [ ] Signal-lane tau: accumulate ≥100 real `search_query` texts → embed →
      measure query-vs-corpus junk floor → then set. Until then 0.84 stays,
      protected by the tier labels.
- [ ] Both re-measurements fold into the OpenAI-space cutover decision (D2):
      when hot-corpus OpenAI vectors exist, calibrate THERE instead.
