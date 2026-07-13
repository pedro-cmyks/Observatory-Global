# Publication evidence-fit gate — operational validation

**Measured:** 2026-07-13  
**Status:** operational abstention gate; not paper-grade model validation

## Question

Can Atlas detect a current thread whose label and frozen receipts do not form a
coherent publishable story, without asking an LLM to classify the story or
deleting the thread from exploration?

## Method

- universe: every receipt-eligible, single-current-cluster candidate in the
  sealed daily edition; no semantic top-N ceiling;
- model: `text-embedding-3-small` used only as a vector measurement;
- per topic: median pairwise receipt cosine and median label-to-receipt cosine;
- abstention: downrank only when both measures fall below the complete-universe
  q10 thresholds;
- compound/too-thin topics abstain from this measurement explicitly;
- every candidate, score and reason code remains in the edition ledger and in
  L2. The gate changes publication eligibility only.

## Live result

| Measure | Result |
|---|---:|
| measured universe | 150 topics |
| tail quantile | 0.10 |
| pair-median threshold | 0.324990 |
| label-median threshold | 0.228343 |
| downranked | 7 |
| omission ledger | complete |
| semantic ceiling | none |

The seven abstentions were the mixed Lindsey Graham cluster, Algeria roundup,
EU-sanctions subset mismatch, healthcare/regional mixture, China
disasters/tensions mixture, broad Sudan update mixture, and a generic headlines
cluster. The Lindsey Graham candidate measured pair median `0.214877` and label
median `0.193665`; it no longer occupies an L1 story slot.

## Interpretation and limits

This result supports an operational claim only: bivariate embedding dispersion
can identify obvious label/evidence mixtures before publication. It does not
establish calibrated precision, recall or a universal q10 threshold. The sample
was not independently labeled, and the cut was inspected on the same live
universe on which it was selected. It must not be cited as paper-grade evidence.

Next validation requires a frozen stratified sample, independent coherence
labels, threshold selection on train/calibration only, and reporting on held-out
topics. Until then the gate should remain conservative, complete-ledger and
publication-only.
