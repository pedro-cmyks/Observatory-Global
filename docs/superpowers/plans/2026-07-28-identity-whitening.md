# Identity layer → whitened space — implementation plan

**Date:** 2026-07-28
**Diagnosis:** `docs/research/recall-229/2026-07-28-identity-layer-raw-cosine.md` (read it first).
**One sentence:** the identity gates (`MATCH 0.88 / ANCHOR 0.93 / MERGE 0.90` in
`scripts/project_dynamic_topics.py:40,53,455`) compare centroids in raw e5 cosine, whose
same-story vs different-story distributions overlap — shredding events into 8–33 fragments
AND letting stale identities absorb unrelated stories. The whitened space that separates
them (0.975 true vs 0.39–0.45 false) already ships (`app/data/e5_whitening.npz`).

## Pre-registered success metrics (from the diagnosis — frozen BEFORE any run)

| Metric | Baseline | Target |
|---|---|---|
| GQ-05 story coverage in ONE topic | 38/598 = **6.4%** | **≥50%** |
| Fragments per event (GQ-05 / GQ-12) | 33 / 9 | **≤3** |
| New false absorptions (≥3 unrelated countries under a failed label) | topics 784, 52 | **0 new** |
| `detect_overmerge` nightly demotes | 187 | must NOT spike (the falsifier) |
| NULL-label rate in the measurement snapshot | — | **0%** or the run is VOID |

## Tasks

### T1 — Measure the whitened thresholds (offline, read-only) — GATES EVERYTHING
Harness `backend/scripts/measure_identity_whitening.py`: sample recent
cluster↔topic pairs (same-story pairs from `dynamic_topic_members` lineage where the label
court PASSED; different-story pairs from cross-country/cross-category picks), compute raw
and whitened cosine for each, report the two distributions + candidate taus for
MATCH_w / ANCHOR_w / MERGE_w (p5 of true-match vs p95 of false-match, with the gap stated).
Artifact → `docs/research/recall-229/2026-07-28-whitened-identity-taus.{md,json}`.
KILL RULE: if the whitened gap is not clean (p5_true ≤ p95_false), STOP — report and do not
proceed to T2.

### T2 — Whitened identity path behind a kill-switch
`project_dynamic_topics.py`: all three comparisons (match, anchor guard, merge) computed on
`apply_whitening(centroid)` when `ATLAS_IDENTITY_WHITEN=on` (default **off**), using the
T1-measured taus (module constants `MATCH_THRESHOLD_W` etc., commented with provenance).
Raw path byte-identical when off. Whiten ONCE per centroid per run (cache), not per pair.
Tests: env off ⇒ identical decisions on a fixture; env on ⇒ the diagnosis's witness case
(NZ anchor vs CO cluster, raw 0.938 / whitened 0.45) is REJECTED while the true match
(0.975) attaches.

### T3 — Unlabelled snapshot must not silently disable merging
`labels_compatible(None, None)` returns False ⇒ a 402 night disables ALL merging (the
eval-week confounder). Fix in two halves:
(a) `merge_duplicates`: when BOTH labels are None/empty, fall through to the vector+
whitened test instead of refusing (a missing label is absence of evidence, not evidence of
difference) — but ONLY when `ATLAS_IDENTITY_WHITEN=on` (raw cosine alone must not gain
merge power).
(b) `snapshot_emergent_topics.py`: when the labeling step failed wholesale (100% NULL),
write the snapshot but emit `SNAPSHOT_UNLABELLED` to the reliability ledger (the alert
helper from `e658dddf`) so a labelless night is visible the same day.

### T4 — Offline replay + verdict (no prod flip inside this plan)
Re-run the diagnosis probes (scratchpad `story_funnel.py` / `co_funnel_probe.py`,
re-created if evicted) with `ATLAS_IDENTITY_WHITEN=on` over the same corpus. Score the
pre-registered metrics. Verdict PASS ⇒ separate go-live step (flip env in both runners +
ALW sync + watch one nightly). Verdict FAIL ⇒ artifact says why; thresholds do not move
post-hoc.

## Boundaries
- `used_t` removal (greedy 1-to-1) and the entity-overlap merge gate are the NEXT plan —
  explicitly out of scope here (diagnosis: unsafe before whitening lands).
- No serving-path changes; this is all M1 nightly-pipeline code.
- Runners re-sync to `~/AtlasLocalWorker/` only at go-live.
