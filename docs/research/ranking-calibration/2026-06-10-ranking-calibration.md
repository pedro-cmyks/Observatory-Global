# Research ranking calibration — 2026-06-10

Window: 168h · thread population: 95 · seed 42 · 3000 samples

## Normalization midpoints (live medians → 0.5)

| Normalizer | Current | Recommended |
|---|---|---|
| evidence_signals | 40.0 | 10.0 |
| source_count | 5.0 | 4.0 |
| movement_changed_10h | 10.0 | 3.0 |

## Weights

Baseline satisfies 20/21 constraints (min margin 0.0349).
Best satisfies 21/21 (min margin 0.065); gold 9/9, live 12/12.

| Component | Current | Recommended |
|---|---|---|
| intent_match | 0.15 | 0.2321 |
| thread_coherence | 0.12 | 0.1232 |
| evidence_strength | 0.2 | 0.1462 |
| answerability | 0.16 | 0.1518 |
| movement_signal | 0.08 | 0.07 |
| source_actor_value | 0.08 | 0.068 |
| geo_entity_fit | 0.1 | 0.1051 |
| novelty_or_gap_value | 0.11 | 0.1036 |
| noise_risk_adjustment | 0.1 | 0.1152 |
| unsupported_claim_adjustment | 0.08 | 0.1356 |
| list_detail_mismatch_adjustment | 0.07 | 0.1378 |

## Method

Weights are fit against pairwise ordering constraints derived from the
spec's acceptance criteria (gold) plus live forcing-case anchors, not
from the source-quality audit: source metrics inform at most
`source_actor_value`/`noise_risk` and cannot trade `intent_match`
against `evidence_strength`. Midpoints are live medians. Rerun this
script when the data distribution shifts or when real user relevance
judgments become available.
