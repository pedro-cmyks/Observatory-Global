# Annotator vendor camps (6-model panel)

Date: 2026-05-28
Status: major Paper 1 finding

## Setup

Balanced annotator panel: 3 Claude + 3 OpenAI + the human, all on the
same stratified sample with the same prompt.

| Annotator | Vendor | correct | incorrect | partial | errors |
|---|---|---:|---:|---:|---:|
| pedro | human | 36 | 25 | 0 | - |
| sonnet46 | Anthropic | 84 | 105 | 54 | - |
| opus47 | Anthropic | 86 | 120 | 38 | 2 |
| haiku45 | Anthropic | 95 | 85 | 45 | - |
| gpt41 | OpenAI | 126 | 102 | 25 | 3 |
| gpt4o | OpenAI | 112 | 122 | 14 | 8 |
| gpt4omini | OpenAI | 93 | 119 | 0 | 44 |

## Finding 1 — agreement has vendor structure

Fleiss kappa:
- Claude-only (3): **0.670** (substantial)
- OpenAI-only (3): **0.681** (substantial)
- All 6 LLMs: **0.635** (substantial, lower)
- All 7 incl. human: 0.630

Within-vendor agreement (~0.67-0.68) is higher than the mixed-vendor
agreement (0.635). Models cluster by vendor: a Claude annotator agrees
more with another Claude than with a GPT, and vice versa. Annotation
style is partly a vendor artifact, not a universal ground truth.

## Finding 2 — the human sits in the OpenAI camp

Human pairwise Cohen kappa:

| Pair | kappa | band |
|---|---:|---|
| pedro vs gpt4o | **0.769** | substantial |
| pedro vs gpt4omini | 0.736 | substantial |
| pedro vs gpt41 | 0.638 | substantial |
| pedro vs opus47 | 0.574 | moderate |
| pedro vs sonnet46 | 0.549 | moderate |
| pedro vs haiku45 | 0.544 | moderate |

Pedro agrees with all three OpenAI models (0.64-0.77) markedly more
than with any Claude model (0.54-0.57). The human is not a random
outlier — he lands squarely in the OpenAI/lenient camp. His earlier
self-doubt ("my labels aren't good, I prefer the model's") is half
right: his labels are not noise, they are a consistent lenient style
that happens to match GPT calibration.

## Finding 3 — precision depends on which camp you trust

Atlas v2 post-044 precision by reference:

| Reference | N | Precision | Wilson 95% CI |
|---|---:|---:|---|
| pedro (human, lenient, 6 topics) | 61 | 73.77% | [61.56%, 83.16%] |
| sonnet46 alone (strict) | 243 | 38.68% | [32.78%, 44.94%] |
| 3-Claude consensus (strict) | 212 | 42.45% | [35.99%, 49.18%] |
| 4-model consensus | 180 | 48.33% | [41.14%, 55.59%] |
| 6-model balanced consensus (>=4/6) | 189 | **50.79%** | **[43.72%, 57.83%]** |

As lenient OpenAI models enter the panel, the consensus precision
rises monotonically: 42% (Claude-only) -> 48% (4-model) -> 51%
(balanced 6-model). The number is a function of panel composition on
the strictness axis.

43 of 232 jointly-labeled rows (18.5%) had no >=4/6 majority — these
are the rows where the vendor camps split. Cross-vendor disagreement
is concentrated, not random.

## Implications for Paper 1

1. **There is no single "LLM gold".** Annotation has vendor-correlated
   style. A precision benchmark anchored on one vendor's models inherits
   that vendor's strictness.
2. **Report a balanced cross-vendor panel and the spread**, not a
   single number. The defensible statement is: Atlas v2 full-taxonomy
   precision is ~42-51% under LLM consensus depending on panel
   strictness (balanced 6-model point estimate 50.79%, CI
   [43.72%, 57.83%]), versus ~74% on the cleanest six topics under a
   lenient human.
3. **The strictness axis is a publishable confound.** Annotator leniency
   correlates with vendor; the human aligns with the lenient (OpenAI)
   camp. This is direct evidence that single-annotator precision claims
   in narrative classification are unreliable and that benchmark design
   must control for annotator strictness.
4. **gpt-4o-mini is a weak annotator** (44/256 parse errors, never used
   `partial`). Keep it in the panel for completeness but down-weight; a
   capable model is required for reliable structured annotation.

## Decision (final for this phase)

- Primary benchmark gold = balanced multi-vendor LLM consensus
  (>=4 of 6 agree across Anthropic + OpenAI families).
- Always report: panel composition, per-vendor Fleiss, all-LLM Fleiss,
  and the no-majority rate.
- Human labels = an independent lenient-camp reference, not gold.
- Headline Atlas number for Paper 1: **50.79% precision, CI
  [43.72%, 57.83%]**, balanced 6-model consensus, full 30-topic
  taxonomy, with the strictness-axis caveat stated explicitly.

---

## Update: third vendor (DeepSeek, 2026-05-28)

Pedro added a DeepSeek key — a third, genuinely independent training
lineage (Chinese lab, no shared lineage with Anthropic or OpenAI).
`deepseek-chat` ran as a seventh annotator via the OpenAI-compatible
endpoint (`llm_annotator.py` gained `_is_deepseek_model` +
`base_url=https://api.deepseek.com`).

deepseek-chat profile: 90 correct / 166 incorrect / 0 partial / 0
errors. Strict (low correct rate) but binary (never used `partial`).

Notable pairwise Cohen kappa:
- deepseek vs gpt4omini: 0.809 (almost perfect) — both strict + binary
- deepseek vs gpt4o: 0.711
- deepseek vs pedro: 0.621
- deepseek vs opus47: 0.596
- deepseek vs gpt41: 0.520
- deepseek vs sonnet46: 0.512
- deepseek vs haiku45: 0.502

Two axes are now visible, not one:
1. Vendor lineage (Anthropic / OpenAI / DeepSeek).
2. Partial usage (some annotators use the `partial` category, others
   are binary correct/incorrect). DeepSeek + gpt4o-mini + Pedro are
   binary; the Claude models + gpt-4.1 use partial. The binary group
   agrees strongly with each other (deepseek/gpt4omini 0.809)
   regardless of vendor. So annotation style is driven by both vendor
   and a binary-vs-graded methodology axis.

Three-vendor agreement holds:
- Fleiss all-8 (incl. human): 0.614
- Fleiss LLM-only (7 models, 3 vendors): 0.626 (substantial)

Adding a third independent vendor keeps the LLM consensus substantial.
LLM annotator reliability is not a single-vendor or shared-lineage
artifact — it survives across Anthropic, OpenAI, and DeepSeek.

### Most robust Atlas precision estimate (3-vendor, 7-model)

| Reference | N | Precision | Wilson 95% CI |
|---|---:|---:|---|
| pedro (lenient, 6 topics) | 61 | 73.77% | [61.56%, 83.16%] |
| 3-Claude consensus | 212 | 42.45% | [35.99%, 49.18%] |
| 6-model consensus (2 vendors) | 189 | 50.79% | [43.72%, 57.83%] |
| **7-model consensus (3 vendors, >=4/7)** | **216** | **47.69%** | **[41.12%, 54.33%]** |

The 7-model, 3-vendor consensus (47.69%, 216 rows, 88% decisive,
CI [41.12%, 54.33%]) is the most defensible single estimate: broadest
and most independent panel, full 30-topic taxonomy. Atlas v2
full-taxonomy precision sits in the **~42-51% band**, point estimate
~48% under the most independent panel. The headline for Paper 1 stands:
the rule-based classifier is far below the 90-95% target, and the gap
is reachable only by moving to a semantic/scope-aware classifier (LLM
zero-shot proved 95% on the human gold).
