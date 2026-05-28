# Roadmap: pushing Atlas precision from ~51% to 90-95%

Date: 2026-05-28
Status: active plan (the central objective)

## The objective

Atlas v2 full-taxonomy precision under balanced 6-model LLM consensus is
**50.79%** (CI [43.72%, 57.83%], N=189, 30 topics). The goal is
**90-95% precision**. This document is the plan to get there.

## Why rule edits cannot get us there (already proven)

The migration arc 040 -> 044 established the ceiling of lexicon/theme
editing on the reviewed gold:

| Intervention | Precision effect |
|---|---|
| 423 lexicon additions (mig 042) | +0.0pp (recall instrument, not precision) |
| 3 lexicon removals (mig 043) | +6.55pp |
| 2 theme-hint removals (mig 044) | +8.20pp |

Cumulative: +14.75pp from surgical removals, 0pp from additions. After
all rule edits, the reachability decomposition of the remaining false
positives is:

- ~scope mismatches: real topic mentioned as context, not primary event.
  NOT fixable by lexicon/theme edits.
- ~theme-only over-matching: GDELT theme hints too broad.
- ~substring noise: e.g. `lira` inside "aliran" (word-boundary defect).
- long-tail 0% topics (mining-royalty, fuel-subsidy, sanctions,
  humanitarian, telecom, water, forced-displacement) under strict
  annotators.

The dominant residual (scope mismatch) is architectural. Lexicon +
theme substring matching cannot distinguish "this headline IS about
topic X" from "this headline MENTIONS topic X as background". That
distinction is the difference between ~51% and ~90%.

## The proof that 90%+ is reachable

The LLM zero-shot baseline (Sonnet 4.6) scored **95.08% precision**
(Wilson CI [86.51%, 98.31%]) on the human gold, clearing the 90%
target. An LLM reading the headline applies semantic + scope judgement
that lexicon matching cannot. So the target is achievable in principle;
the problem is doing it at production scale and cost.

## The plan — three phases

### Phase A — scope-aware labels at scale (data generation)

We already have the instrument: the multi-vendor LLM annotator panel
produces, per signal, not just correct/incorrect but `scope`
(domain / parent_thread / child_thread / entity_thread / evidence /
context_signal / noise) and `evidence_role` (primary_event / followup /
background / reaction / analysis / ...). These are exactly the fields a
scope-aware classifier needs.

Actions:
1. Scale the LLM-consensus labeling from 256 rows to a large training
   set (target 5k-20k signals), stratified by topic and bucket,
   weighted by production volume. Cost is the only constraint and it is
   small (~$0.003/row/model; a 3-model panel over 10k rows is ~$90).
2. Keep only rows with >=2/3 (or >=4/6) panel agreement as training
   labels; route ties to a small human/adjudication queue.
3. Persist labels with scope + evidence_role, not just topic
   correctness.

Output: a scope-typed, multi-vendor-consensus training corpus.

### Phase B — a learned classifier that approximates the LLM (distillation)

Replace (or gate) the lexicon+theme rule with a learned classifier
trained on the Phase A corpus. Three candidate architectures, cheapest
first:

1. **Embedding + head**: embed the headline (multilingual sentence
   encoder, e.g. LaBSE / multilingual-e5), train a lightweight
   classifier head per topic or a single multi-label head. Near-zero
   inference cost, runs in the existing worker. Target: recover most of
   the LLM's precision.
2. **Cross-encoder re-ranker**: for each (headline, candidate topic)
   pair from the cheap lexicon prefilter, score with a small
   cross-encoder trained on the corpus. Keeps lexicon as a fast
   recall prefilter, adds a precision gate.
3. **Distilled small LLM**: fine-tune a small open model on the
   consensus labels. Higher cost, highest fidelity to the LLM panel.

The scope head is the key addition: predict scope (evidence vs context
vs noise) so the classifier abstains from assigning a topic when the
signal only mentions it as context. This directly attacks the dominant
scope-mismatch error.

Validation: score each candidate against the same balanced 6-model
consensus benchmark + the human reference. Promotion gate: consensus
precision >= 90% with the CI lower bound clearing 85%.

### Phase C — confidence gating and abstention

Even with a learned classifier, the long-tail noisy topics may not
reach 90%. For those:
1. Calibrate a per-topic confidence threshold; assign only above it.
2. Abstain (assign nothing) rather than mis-assign on low-confidence
   signals. This trades recall for precision and is the right tradeoff
   per the project's precision-first rule.
3. Report coverage alongside precision so the recall cost is explicit.

## How this maps to the paper

- Paper 1 (current): documents the rule-based v2 classifier, the
  honest ~51% consensus precision, the reachability decomposition, the
  annotator-reliability methodology, and the LLM baseline that proves
  90%+ is reachable. **It does not need the v3 classifier built** — it
  argues why the architecture must change and what the ceiling of rules
  is. That is a complete, honest contribution.
- The v3 learned classifier (Phases A-C) is the follow-up: "from rules
  to a scope-aware distilled classifier", targeting 90-95%, validated
  on the same benchmark. It can be Paper 1's "future work" section now
  and its own paper later.

## Immediate next actions (next session)

1. Build the Phase A scaling script: extend the LLM annotator panel run
   to a large stratified sample (reuse `llm_annotator.py`,
   `multi_annotator_agreement.py`, consensus builder). Target 5k rows
   first.
2. Persist consensus labels with scope + evidence_role into a training
   table or JSONL corpus.
3. Prototype Phase B option 1 (embedding + head) and score it against
   the 6-model consensus benchmark.
4. Keep every result in `docs/research/atlas-paper/phase-1-validation/`
   with bootstrap CIs and per-vendor Fleiss, same as this phase.

## Budget note

Spend so far this work: Anthropic $4.58 + OpenAI $0.90 = $5.48. Phase A
scaling to 5k-10k rows on a 3-model panel is the next notable cost
(~$45-90). Well within range.
