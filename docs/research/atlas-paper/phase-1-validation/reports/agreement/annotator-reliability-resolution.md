# Annotator reliability resolution

Date: 2026-05-28
Status: methodology decision (active)

## The question

Pedro raised the right concern: a single untrained human annotator is a
noisy, biased gold source. He preferred the LLM labels and asked whether
his own labels should count as ground truth at all.

We resolved this empirically by running three frontier models as
independent annotators (same prompt, model-level variation only) over
the stratified sample and measuring inter-annotator agreement.

## Annotators

| Annotator | Model | Rows labeled |
|---|---|---:|
| pedro | human (single, initial) | 61 (6 topics) |
| sonnet46 | claude-sonnet-4-6 | 243 (30 topics) |
| opus47 | claude-opus-4-7 | 244 (30 topics) |
| haiku45 | claude-haiku-4-5 | 225 (30 topics) |

## Result 1 — LLMs agree with each other more than with the human

Pairwise Cohen's kappa:

| Pair | kappa | band |
|---|---:|---|
| pedro vs sonnet46 | 0.549 | moderate |
| pedro vs opus47 | 0.574 | moderate |
| pedro vs haiku45 | 0.544 | moderate |
| sonnet46 vs opus47 | 0.624 | substantial |
| sonnet46 vs haiku45 | 0.693 | substantial |
| opus47 vs haiku45 | 0.704 | substantial |

Every LLM-LLM pair (0.62-0.70) agrees more than every human-LLM pair
(0.54-0.57). Fleiss' kappa confirms it:

- LLM-only (3 models): **0.670 (substantial)**
- All four (incl. human): **0.592 (moderate)**

Adding the human annotator *lowers* group agreement. The human is the
outlier, not the reference.

## Result 2 — the human's methodology is coarser

Strictness profile (decision distribution):

| Annotator | correct | incorrect | partial |
|---|---:|---:|---:|
| pedro | 36 | 25 | **0** |
| sonnet46 | 84 | 105 | 54 |
| opus47 | 86 | 120 | 38 |
| haiku45 | 95 | 85 | 45 |

Pedro never used the `partial` category. The three LLMs all used it
substantially. A binary correct/incorrect split collapses borderline
cases into `correct`, which is part of why the human precision estimate
runs high.

## Result 3 — the LLMs form a usable consensus

The three LLMs produced a clear majority on the stratified sample:
- 212 rows where >=2 of 3 agreed.
- Only 7 three-way ties out of 219 jointly-labeled rows (96.8% had a
  majority).

This consensus is a defensible benchmark reference: three independent
frontier models, not circular on any single one.

## Result 4 — Atlas precision under each reference

Same post-044 Atlas v2 classifier, three references:

| Reference | N | Topics | Precision | Wilson 95% CI |
|---|---:|---:|---:|---|
| pedro (human) | 61 | 6 | 73.77% | [61.56%, 83.16%] |
| sonnet46 alone | 243 | 30 | 38.68% | [32.78%, 44.94%] |
| LLM majority (>=2/3) | 212 | 30 | **42.45%** | **[35.99%, 49.18%]** |

The LLM-consensus precision (42.45%) is the headline benchmark number:
full-taxonomy coverage, multi-model consensus, tight CI, no single-human
bias. The human's 73.77% is a coverage-biased, methodology-coarse
overestimate on the six cleanest topics.

## Decision

1. **Adopt LLM-majority-vote as the primary benchmark gold standard.**
   Three-model majority (Sonnet 4.6 + Opus 4.7 + Haiku 4.5) on each
   sampled row. Report Fleiss kappa alongside any precision number.
2. **Demote single-human labels to audit/spot-check.** Pedro's labels
   remain useful as an independent human reference point and for
   detecting systematic LLM bias, but are not the gold standard.
3. **Report the consensus precision with its CI and the inter-annotator
   kappa** in Paper 1. The honest headline: Atlas v2 full-taxonomy
   precision is ~42% under three-model consensus (CI [36%, 49%]), with
   per-topic precision ranging from 0% (mining-royalty, fuel-subsidy,
   sanctions) to ~90-100% (gender-violence, disease-outbreak,
   corruption).
4. **For future labeling, prefer LLM panels over solo human labeling.**
   Add human adjudication only where the LLM panel ties or where
   systematic bias is suspected.

## Why this strengthens Paper 1

This is a methodology contribution in its own right: it demonstrates,
with kappa evidence, that for this narrative-classification task a panel
of frontier LLMs is a more reliable and far more scalable annotation
instrument than a single untrained human. That justifies the
LLM-as-annotator design used for the rest of the Atlas paper series and
removes the human-throughput bottleneck without sacrificing rigor.

## Caveats

- Three Claude-family models are not fully independent — they share
  training lineage. A truly independent panel would add a non-Claude
  model (e.g. GPT-4-class or Llama-class). Stated as a limitation; the
  substantial inter-model kappa (0.67) is still meaningful because the
  models differ in size and tuning.
- LLM consensus can share a systematic blind spot. The 0% topics
  (mining-royalty etc.) should still get a human adjudication pass to
  confirm the LLMs are right and Atlas is wrong, not the reverse.
