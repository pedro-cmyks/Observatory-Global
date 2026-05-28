# Phase B feasibility probe: a learned "is-evidence" scope gate

Date: 2026-05-28
Status: cheap-first feasibility probe (zero API cost). Informs the go/no-go
on the Phase A 5k-row annotation spend.

## Question

The dominant residual error of the rule-based Atlas v2 classifier is
**scope mismatch**: the topic is really mentioned, but only as context /
background, not as the primary event the headline is about. Lexicon +
theme substring matching cannot tell "this headline IS about topic X" from
"this headline MENTIONS topic X". The roadmap
(`2026-05-28-precision-to-90-roadmap.md`) bets a learned classifier can.

Before spending ~$45-90 to scale the annotation panel from 256 to 5k rows,
this probe asks the cheap version of the question on the data we already
have: **can a learned gate, reading the headline + candidate topic,
separate evidence from context on the 7-LLM consensus corpus?**

## Setup

- Corpus: `labels/consensus/2026-05-28-7llm-consensus-corpus.jsonl`
  (built by `build_consensus_corpus.py` from the 7-model × 247-signal
  annotation panel).
- Target: `is_evidence` — consensus decision `correct` -> 1,
  `incorrect` -> 0, ambiguous (`partial` / no-majority) dropped.
- **N = 207 binary rows** (93 evidence, 114 not-evidence).
- Positive class = evidence = "the gate KEEPS this assignment".
- Model: numpy logistic regression (L2, class-balanced), pooled
  stratified 5-fold out-of-fold probabilities, seed 0.
- Metrics: ROC-AUC, PR-AUC, and the precision-first metric
  **max recall while keep-precision >= 0.90 / 0.85**, with 2000-sample
  bootstrap CIs. Metric implementations are self-tested against known
  sklearn reference values (`--selftest`).
- Tool: `backend/scripts/phase_b_scope_gate_probe.py`
  (numpy-only — see Environment note).

Baseline: the no-op "keep all" gate has precision = base rate =
**44.93%** (= current Atlas precision on this binary-decided subset).

## Results

| feature set | ROC-AUC (CI95) | PR-AUC (CI95) | keep@0.90 recall | keep@0.85 recall |
|---|---|---|---|---|
| atlas_conf | 0.739 [0.664, 0.805] | 0.669 [0.553, 0.771] | **1.1%** | 1.1% |
| charngram | 0.778 [0.711, 0.839] | 0.765 [0.680, 0.841] | **31.2%** | 31.2% |
| charngram+conf | 0.818 [0.754, 0.874] | 0.766 [0.663, 0.854] | 16.1% | 28.0% |

- `atlas_conf` = Atlas v2's own assignment confidence + matched-term count.
- `charngram` = hashed char 3-5 grams over "headline | topic_label".
- `charngram+conf` = char n-grams stacked with the atlas_conf features.

## Reading

1. **Atlas's own confidence is not a scope gate.** AUC 0.739 looks
   non-trivial, but at the high-precision end it is useless: it can hold
   90% precision on only ~1% of the evidence. Confidence reflects lexical
   match strength, not whether the topic is the primary event. This is the
   quantitative confirmation that the current pipeline has no scope signal
   to exploit.

2. **A learned gate finds scope signal that confidence does not.** Even a
   zero-cost char-ngram logistic model carves out a keep-set that is 90%
   precise and covers ~31% of true evidence — a 30x improvement over
   confidence at the same precision. Lexical features alone already
   separate evidence from context better than anything in the production
   pipeline. The architecture bet is **directionally supported**.

3. **It is not yet at target, and it cannot be from this probe.**
   Char-ngrams are still lexical; they reach 90% precision only on a third
   of evidence, not at high recall. The roadmap's actual bet is on
   *semantic* embeddings (a model that reads scope the way the LLM panel
   does). That arm is **untested here** — see Environment note. So this
   probe is a **lower bound**: the cheapest possible features already beat
   confidence; semantic embeddings should do strictly better.

4. **N=207 is the binding limitation.** ~18 positives per fold. CIs are
   wide (charngram AUC [0.71, 0.84]) and `keep@precision` is defined by a
   handful of top-ranked points, hence the non-monotone
   charngram-vs-charngram+conf flip at 0.90 (higher overall AUC, noisier
   high-precision tail). This is precisely the noise the 5k-row scale-up is
   meant to remove — the probe confirms plausibility, not a production
   number.

## Recommendation (go / no-go on the 5k spend)

**Conditional go, but run one more cheap test first.** The probe shows a
learned gate does what rules and confidence cannot, which is the load-
bearing assumption of the whole v3 plan. But the decisive question — does a
*semantic* encoder lift the 90%-precision keep-set well above char-ngram's
31% recall — is still open and is testable cheaply on the existing 207
rows without the 5k spend:

- **Next cheap step:** embed the 207 "headline | topic" strings with a
  multilingual embedding model and re-run the identical numpy LR + metrics.
  A hosted embedding API (e.g. OpenAI `text-embedding-3-small`,
  multilingual, ~$0.00002/1k tokens -> << $0.01 for 207 short rows)
  sidesteps the local environment problem entirely.
  - If semantic embeddings jump keep@0.90 recall substantially above 31%
    -> strong evidence the full architecture reaches target -> **commit the
    5k annotation spend** to build the production training corpus.
  - If semantic embeddings are only marginally better than char-ngrams ->
    the cheap embedding+head arm may not be enough; reconsider the
    cross-encoder / distilled-LLM arms before scaling labels.

## Environment note (recurring gotcha)

The project lives under `~/Desktop`, which is iCloud-Drive-synced, and the
disk is ~90% full, so iCloud has **evicted** large venv files to dataless
placeholders (`pandas/core/generic.py` is flagged
`hidden,compressed,dataless`). Importing sklearn (which eagerly imports
pandas) blocks at 0% CPU on the on-demand iCloud download of an evicted
file — diagnosed via `faulthandler.dump_traceback_later`. numpy/scipy core
are materialized and import fine.

Consequences:
- The probe was rewritten **numpy-only** (matching the rest of the research
  toolkit, which is stdlib/numpy-only — this is why the issue never
  surfaced before). Metrics are hand-rolled and self-tested.
- The semantic-embedding arm needs torch/transformers (also dataless) or a
  hosted API. Use the hosted API or run from the non-synced worker path
  (`/Users/pedro/AtlasLocalWorker`) rather than fighting iCloud
  materialization on a near-full disk.

## Artifacts

- Corpus builder: `backend/scripts/build_consensus_corpus.py`
- Corpus: `labels/consensus/2026-05-28-7llm-consensus-corpus.jsonl`
  (+ `.summary.json`)
- Probe: `backend/scripts/phase_b_scope_gate_probe.py`
- Report: `reports/phase-b/2026-05-28-scope-gate-probe.json`
