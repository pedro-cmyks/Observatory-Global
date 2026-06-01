# Coverage Root-Cause: Lexicon Recall, Not Gate Abstention

**Date:** 2026-06-01
**Status:** Diagnosis (read-only). No gate or schema changes were made.

## Question

The 24h scope-gate coverage report showed a `17.77%` kept rate (`2,999`
kept of `16,878` scored assignments). The open question was whether the
learned scope gate is over-abstaining and suppressing recoverable
coverage, and whether its `0.878` global threshold should be lowered.

## Method

Two read-only views:

1. **Gate score distribution (24h).** Bucketed live
   `signal_topic_assignments.gate_score` into deciles and counted
   kept vs scored per decile.
2. **Gold cross-check.** The 2026-06-01 three-vendor evidence-role gold
   set (`605` consensus rows, `93.7%` agreement) is ground truth on
   whether a signal is real cluster evidence. Joined each gold row by
   `signal_id` to its lexicon assignment (if any) to see how the gate
   treats true `primary_evidence` vs `noise`.

## Findings

### 1. Most abstention is genuine low-confidence noise, not the gate

| gate_score decile | assignments | avg score | kept |
|-------------------|------------:|----------:|-----:|
| 1 (0.0–0.1)       | 12,680      | 0.013     | 41   |
| 2 (0.1–0.2)       | 1,249       | 0.141     | 30   |
| 3–9 (gray zone)   | ~3,165      | —         | ~894 |
| 10 (0.9–1.0)      | 2,253       | 0.982     | 2,096|

Decile 1 alone is ~75% of the scored volume at an average gate_score of
`0.013`. These are near-zero-confidence lexicon matches; abstaining them
is correct. The `17.77%` headline rate is inflated by this upstream
noise sitting in the denominator. On signals with any plausible score
(`gate_score > 0.3`), the kept rate is roughly `58%`.

### 2. The real gap is candidate recall, not the gate

Cross-checking the `605`-row evidence-role gold set against lexicon
assignments:

- `551 / 605` gold rows (`91.1%`) have **no lexicon assignment at all**.
- `269 / 288` true `primary_evidence` rows (`93.4%`) have **no lexicon
  assignment at all**.

So for ~93% of genuine primary evidence, the gate never gets a chance to
keep or abstain — the lexicon candidate generator never produced a
candidate. The gate is doing its job on what it receives; the bottleneck
is upstream recall.

## Conclusion

The lexicon candidate generator is simultaneously:

1. **Low precision** — ~75% of the assignments it does produce are
   near-zero-confidence noise (decile 1).
2. **Low recall** — it misses ~91% of real cluster evidence entirely.

Lowering the gate threshold would only recover items from the noisy
gray zone; it cannot recover the 91% of real evidence that never entered
the pipeline. Coverage cannot be fixed at the gate.

## Implication for product direction

Coverage and the evidence-role pilot are the same problem. The path to
real coverage is to change the candidate generator from lexicon matching
to embedding-based cluster membership (the emergent layer already
produces these clusters via HDBSCAN over `multilingual-e5-base`
embeddings). The evidence-role student — which classifies role over
cluster membership rather than over lexicon matches — is the coverage
mechanism, not a separate paper-validation track.

## Recommended next steps

- Do **not** lower the scope-gate threshold to chase coverage.
- Treat the emergent-cluster + evidence-role path as the coverage engine.
- When the gold set reaches a balanced ~1,000–1,500 rows, train the
  local evidence-role student and measure visible-coverage tiers
  (`verified` / `candidate` / `context_rich` / `suppressed`) against the
  `>=90%` verified-precision target.
- Optionally, quantify the lexicon recall gap as a standing metric so the
  candidate-generator migration has a baseline to beat.
