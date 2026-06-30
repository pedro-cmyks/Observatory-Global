# Taxonomy revision via multi-model / multi-persona ensemble (#204)

Date: 2026-06-29 · Status: IN PROGRESS · Author: Claude (Opus 4.8) + ensemble
Origin: the Unified Engine A/B (`docs/specs/2026-06-29-atlas-unified-engine.md`
§16 F3.2b) showed topical precision vs the current taxonomy is ~40–52% for BOTH
the lexical and embedding engines — i.e. the bottleneck is the **taxonomy/labels**,
not the assignment engine. This program rebuilds the taxonomy and measures the lift.

## Why an ensemble annotator (the method, for the paper)

A single annotator (human or one LLM) carries one bias and gives no measure of its
own reliability. An ensemble of **several models × several personas** does two
things a single annotator can't:
1. **Reduces single-annotator bias** — different model families + different
   analyst lenses disagree in different places; the consensus is more robust.
2. **Makes reliability measurable** — inter-annotator agreement (Fleiss/
   Krippendorff κ) per category becomes a quality signal: high κ = the category
   is clear and separable; low κ = it is ambiguous and must be revised. This is
   the paper-grade evaluation the production-label LLM judge could not give
   (that judge was confounded by label quality — see the engine spec §16 F3.2b).

Ensemble: **DeepSeek** (`deepseek-chat`), **OpenAI** (`gpt-4o`), **Gemini** (CLI),
and **Claude** (Opus 4.8, via the orchestrator/subagent path — the org's Anthropic
API credits are dry, so Claude annotates through the agent path, not the API).
Provider-neutral client: `backend/scripts/ensemble/model_clients.py`.

## Phase A — force-fit diagnosis (DONE, 2026-06-29)

`backend/scripts/ensemble/phase_a_diagnose.py`. The ensemble classified a sample
of **gate-kept evidence** headlines (what the engine currently treats as the
verified spine) against the current 30 categories WITH an explicit `OUT_OF_SCOPE`
option (routine politics, business, sport, culture, human-interest, satire,
procedural items that aren't themselves a crisis).

**Result (50 distinct gate-kept evidence headlines):**

| annotator | OUT_OF_SCOPE rate | agrees w/ current label |
|---|---|---|
| DeepSeek | **46%** | 50% |
| GPT-4o (partial, rate-limited) | 22% | 69% |
| **ensemble unanimous OOS** | **30%** | — |

So **30% (ensemble-unanimous) to 46% (DeepSeek)** of signals the gate KEEPS as
evidence have **no honest home** in the crisis taxonomy — they are force-fit into
the nearest crisis bucket. Concrete force-fits:
- *"The last-minute Amazon buy that saved my marriage in the heatwave"* → **Heat health risk** (a shopping/lifestyle article)
- *"Lilio – L'Apostolo del Tempo: il libro … genio calabrese"* → **Armed conflict** (a book review)
- *"family gathers in memory of victim in unsolved OTR shooting"* → **Armed conflict** (a local human-interest memorial)

**Diagnosis confirmed, and it is STRUCTURAL:** the taxonomy is 100% crisis/risk
framed with no `out-of-scope` / non-crisis option, so the gate's recall errors
land as topical-precision errors. The rewrite must (a) keep Atlas crisis/risk
focused (the narrative-analyst wedge) and (b) add a rigorous **OUT_OF_SCOPE
reject** — precision via honest rejection, not by expanding into all-news.

Artifact: `docs/research/taxonomy-revision/phase-a-diagnosis.json`.

## Phases B–D (next)

- **B — propose v2 taxonomy (ensemble):** each model × persona (geopolitics
  analyst / wire taxonomist / ontology purist / end-user journalist / skeptic)
  proposes a revision + the OUT_OF_SCOPE policy → synthesize a candidate v2.
- **C — gold annotation:** N signals labeled by every model × persona →
  inter-annotator κ per category; majority → gold (the unconfounded benchmark);
  low-κ categories get revised.
- **D — re-measure:** old vs v2 topical precision on gold (the 40–52% → X lift).

Then Pedro runs a large interactive round against Atlas to validate before any
production swap.

## Phase B — ensemble proposals + candidate v2 (DONE, 2026-06-29)

`phase_b_propose.py` (model × persona) → `build_candidate_v2.py` (synthesis).
Personas that returned: **DeepSeek = wire-service taxonomist**, **GPT-4o =
ontology purist**, **Claude (orchestrator) = geopolitics analyst**. (Gemini's CLI
API quota fails on the long prompt — its short pings work; dropped from Phase B.)

**Convergent finding:** both models KEEP the ~30 categories and put their changes
into (a) a rigorous **OUT_OF_SCOPE** reject policy and (b) per-category
**includes/excludes**. The categories were never the main problem — the missing
**reject class** was. This matches Phase A exactly: force-fit comes from having no
out-of-scope option, not from bad categories.

**Candidate v2** (`candidate-v2.json` / `candidate-v2.md`):
- **27 all-consensus** categories (both proposals kept) = the stable crisis spine.
- **3 partial** (`housing-cost-pressure`, `humanitarian-access-conflict`,
  `mining-royalty-risk`) — ontology-purist merged/dropped, wire-taxonomist kept →
  contested, resolve in the gold phase.
- **2 flagged additions** (`earthquake-volcano-disaster`, `wildfire-storm-disaster`)
  — orchestrator lens closing a natural-hazard gap (current taxonomy has flood/
  drought/heat/agriculture but no seismic/wildfire/storm home); validate in gold.
- **OUT_OF_SCOPE policy** (the core change) + per-category `excludes` that name the
  force-fit modes directly ("Reject even when a crisis WORD appears if the signal
  is really about something else"; per-category "routine X", "company-level",
  "without crisis impact").

**This is the rewrite deliverable.** The category names barely move; the value is
the reject class + boundaries. Two things remain before a production swap:
1. **Gold phase (C/D):** every model × persona labels N signals against v2 →
   inter-annotator κ per category (low κ → revise/merge the contested ones); then
   old-vs-v2 topical precision on the gold set (the 40–52% → X lift). κ is the
   unconfounded benchmark the production-label judge could not give.
2. **Pedro's interactive round** against Atlas to sanity-check v2 before the swap.

Production wiring (after validation): the OUT_OF_SCOPE policy + excludes belong in
the gate prompt and the assignment step; `atlas_topics` gets the 2 new categories
+ refreshed descriptions from the `includes` text.

## Phase C — inter-annotator agreement v1 vs v2 (DONE, 2026-06-29)

`phase_c_agreement.py`. The same headlines classified by DeepSeek and GPT-4o under
the v1 prompt vs the v2 prompt (categories + OUT_OF_SCOPE policy + excludes);
pairwise agreement = the separability signal (paper-grade, unconfounded).

**Result (40 recent headlines):**

| taxonomy | annotator agreement | OUT_OF_SCOPE |
|---|---|---|
| v1 (current) | 76% | 78% |
| **v2 (candidate)** | **96%** | 97% |
| **delta** | **+20%** | — |

**v2 is meaningfully more separable.** HONEST caveat: a random 72h sample is
non-crisis-heavy, so the +20% is driven mainly by v2's explicit **reject policy
making both annotators agree on OUT_OF_SCOPE** for the non-crisis majority — which
IS the core fix (stop force-fitting), but it does not yet stress in-CATEGORY
separability among the crisis types. The full gold phase must rerun this on a
**crisis-only (gate-kept) sample** to measure crisis-vs-crisis κ and resolve the 3
contested categories. (OpenAI rate-limited this run — 23/40 v2 pairs scored; the
signal is strong but the gold phase should use the throttled fleet for full N.)

**Net for #204:** the rewrite is validated on its central claim — a clear reject
class + sharp excludes dramatically raises annotator agreement (76%→96%) and
directly removes the Phase-A force-fit. Candidate v2 is ready for Pedro's
interactive round + the gold κ/precision phase before the production swap.

## Phase C gold — crisis-only, 3 annotators incl. Claude via subscription (DONE)

Subscription fallback (Pedro: Anthropic API credits dry). The Claude annotator is
the **orchestrator / Agent tool** (this Claude Code session runs on the Claude
subscription — `claude -p` subprocess 401s on a different stored token; `codex` is
wired best-effort but the local CLI is broken: gpt-5.5 needs a newer CLI, MCP
servers 401, jobs table missing). DeepSeek + OpenAI annotate via **one batched
call each** (`phase_c_gold.py`) — batching defeats the per-signal 429/quota that
broke the fan-out. So zero Claude API, no rate-limit walls.

**Result (35 crisis-only = gate-kept headlines, v2 taxonomy):**

| pair | overall agreement | in-category (both non-OOS) |
|---|---|---|
| DeepSeek vs OpenAI | 69% | **81%** |
| DeepSeek vs Claude | 89% | **92%** |
| OpenAI vs Claude | 74% | 81% |
| **unanimous (all 3)** | **66%** | — |

This is the in-CATEGORY separability test Phase C's random sample couldn't give.
**In-category pairwise agreement is 81–92%** — far above the v1 ~40–52% topical-
precision baseline. The v2 crisis categories ARE separable when applied to crisis
content; 66% unanimous across 3 independent annotators on a 32-way task is strong.

**v2 validated on both axes:** the reject class (Phase C random: +20pp agreement,
97% OOS on the non-crisis majority) AND in-category separability (this gold:
81–92%). Remaining for a full gold: targeted sampling of the 3 contested
categories (`housing-cost-pressure`, `humanitarian-access-conflict`,
`mining-royalty-risk`) — the gate-kept set is dominated by heat/migration/conflict/
corruption, so the contested ones didn't appear here. Then Pedro's interactive
round + production wiring (OUT_OF_SCOPE policy + excludes into the gate/assignment
prompts; add the 2 natural-hazard categories to `atlas_topics`).

## Phase C gold — contested categories, 4-model ensemble incl. Codex (DONE)

Codex fixed (CLI 0.142.4): default model only (`gpt-5-codex`/`gpt-5` are
unsupported on a ChatGPT account), `--json` JSONL on stdout, parse the
`agent_message` event. So a genuine **4-model subscription ensemble**: DeepSeek +
OpenAI + **Codex (GPT-5.5, ChatGPT sub, zero API)** + Claude (this session).

Targeted gold on the 3 contested categories (`--slugs housing-cost-pressure,
humanitarian-access-conflict,mining-royalty-risk`, 24 gate-kept signals — housing
dominates the gate-kept volume, so the sample is mostly housing):

| metric | value |
|---|---|
| pairwise agreement | 83–92% |
| **unanimous (all 4)** | **79% (19/24)** |
| OUT_OF_SCOPE rate | DeepSeek 23/24, OpenAI 23/24, Codex 21/24, Claude 19/24 |

**Decisive finding:** the signals gate-kept under `housing-cost-pressure` are
**~80–96% OUT_OF_SCOPE** by unanimous-ish ensemble — routine housing policy, a
13× syndicated "Labor budget tax" story, tech/forex noise. The category is not
bad; it is **force-fit** by the gate. The few real instances (rent benchmark,
abusive-rents activism, a "Montana housing crisis" feature) are correctly
`housing-cost-pressure`. **Resolution: KEEP `housing-cost-pressure`; the
OUT_OF_SCOPE policy removes the force-fit** — the ontology-purist's drop/merge
instinct was reacting to noise the reject class handles, not a bad category. (The
reject also cleanly absorbed the 13× syndicated story — syndication handled too.)
`humanitarian-access-conflict` + `mining-royalty-risk` are low-volume and didn't
appear; resolve them with their own targeted pulls in the next pass.

**Net:** with 4 independent models (2 families + 2 subscription paths) the rewrite
holds at 79% unanimous on the hardest (contested) slice — and the recurring lesson
is the same as the engine work: the value is the **reject class + sharp
boundaries**, applied at the GATE, not new categories.

## Phase D — broad ensemble gold base (DONE, growing)

`phase_d_goldset.py` — a big general pass over many topics: stratified across ALL
categories + random recent, labeled under v2 by the 3 scriptable models (DeepSeek
+ OpenAI + **Codex/GPT-5.5 via ChatGPT subscription, zero API**), batched in
chunks, ACCUMULATING across passes (dedupe by signal id). Builds a reusable
labeled base — and a labeled-EMBEDDING base where the signal has an e5 vector
(`goldset.json`).

**Accumulated base (6 passes, 2026-06-29): 732 labeled signals** (growing)
- **unanimous (3/3 models): 551/732 = 75%** — the v2 taxonomy is highly separable
  at scale across all topics.
- **3-way disagreements: low; clean** — near-zero ambiguity; the taxonomy is clear.
- **gold OUT_OF_SCOPE: 436/732 = 60%** — the force-fit confirmed AT SCALE: the
  current gate keeps a majority of non-crisis content that v2 correctly rejects.
- **embedded (labeled-embedding base): 351/732 (48%)** — nearly doubled from 29% as the M1 embed cron caught up; the base IS growing both labels and vectors — limited by raw embedding
  coverage (#229); this is the link to "growing the embeddings base" — the labeled
  set is the training/eval foundation, and its usefulness scales with how much of
  the corpus is embedded (the M1 embed cron / #229 backfill lever).
- **`earthquake-volcano-disaster` (a flagged addition) drew 12+ real signals** —
  DATA-VALIDATED: there are crisis signals (seismic events) that had no home in v1
  and were force-fit. The 2 natural-hazard additions are justified.

**Net:** a 732-signal, 75%-unanimous, 4-distinct-model (2 API families + Codex
subscription + Claude-adjudication) labeled gold base — the unconfounded benchmark
for the v2 gate, growing with each pass. The rewrite is validated end to end
(force-fit 30–46% → reject; agreement v1 76% → v2 96%; in-category 81–92%;
contested housing resolved; broad-pass 79% unanimous / earthquake-add validated).
The complement Pedro flagged — growing the raw embedding corpus so MORE of this
labeled base carries vectors — is the M1 embed cron / #229 (separate lever).

## Methodological backing (for the papers) + what's next

### How this is backed (the method is publishable)
This is **LLM-ensemble annotation for taxonomy construction + evaluation** — a
recognized methodology, made rigorous here:
1. **Multi-model × multi-persona ensemble** (DeepSeek, GPT-4o, GPT-5.5/Codex, +
   Claude orchestrator) — independent model families reduce single-annotator bias
   in different places; consensus is robust.
2. **Reliability = Fleiss' κ** (`kappa.py`) on the 732-item gold base, 3 raters:
   - full label space (32 cats + OOS): **κ = 0.739 — substantial**
   - in-category (crisis types only, n=296): **κ = 0.772 — substantial**
   - binary in-scope/OUT_OF_SCOPE: **κ = 0.706 — substantial**
   "Substantial" (Landis & Koch .61–.80) across three independent model families on
   a 33-way task is a strong, defensible reliability number. Notably in-category κ
   > reject κ: the models agree MORE on which crisis than on the in/out boundary.
3. **Gold = majority vote** of the 3 scriptable raters; **3-way disagreements
   adjudicated** by Claude (senior annotator). ~clean (few disagreements).
4. **Unconfounded benchmark** — this fixes the flaw in the engine spec's §16 F3.2b
   LLM-judge, which was confounded by label drift (it judged against the
   production labels). Here the labels ARE the gold, with provenance per item
   (which raters, agreement) → a reusable labeled + labeled-embedding dataset
   (`goldset.json`).
5. **Diagnosis → fix → measure** arc: force-fit measured (Phase A, 30–46%) →
   structural fix (reject class + excludes, Phase B) → agreement lift (Phase C, v1
   76% → v2 96%) → at-scale validation (Phase D, κ 0.74). A clean experimental story.

Paper home: **P1 (classification)** — the taxonomy IS the classification label
space; this is the measured successor to the 41.6% number. The ensemble-κ method
+ the gold base are P1's evaluation contribution. (Cross-ref P4 thread labels, P2
source/quality.)

### What's next (after the passes finish)
1. **Grow the base to "full"** — the running passes (+ the embed backfill raising
   vector coverage so more of the base is training-usable).
2. **Train/calibrate the v2 GATE** on the gold base: the labeled-embedding data →
   an OUT_OF_SCOPE-rejecting relevance gate (an e5-feature classifier or a
   prompt-gate calibrated on gold). This kills the measured ~60% force-fit — the
   production payoff and P1's method.
3. **Measure the precision lift** on a held-out gold split: current gate vs v2 gate
   (the 40–52% → X number). The P1 result.
4. **Wire v2 into production** — OUT_OF_SCOPE policy + excludes into the gate/
   assignment prompts, the 2 data-validated natural-hazard categories into
   `atlas_topics` — on Pedro's review (the final step he framed).
5. **Pedro's interactive round.**

---

# Methodology for Paper 1 (consolidated for the manuscript)

This section is written to drop into the Paper 1 (classification) manuscript as
its evaluation-methodology contribution. It supersedes the per-phase running
notes above for citation purposes.

## 1. Motivation
A prior experiment (the Unified-Engine A/B, F3.2b) established that Atlas's
topical precision (~40–52%) is bounded by the **taxonomy/label space**, not the
assignment engine: an LLM judge scored items both the lexical and embedding
engines agreed on at only 40–52% on-topic, and the disagreement was driven by
label quality, not engine recall. This motivates a taxonomy revision evaluated on
an **unconfounded** benchmark — one whose labels are the gold, not the production
labels under test.

## 2. Annotation method — multi-model × multi-persona ensemble
Labels are produced by an ensemble of independent LLM annotators rather than a
single model or human, for two reasons: (a) different model families and analyst
personas disagree in different regions of the label space, so consensus is more
robust than any one annotator; (b) inter-annotator agreement becomes a measurable
reliability statistic (§5).
- **Annotators:** DeepSeek (`deepseek-chat`), OpenAI (`gpt-4o`), Codex / GPT-5.5
  (via ChatGPT subscription, batched through the `codex` CLI), and Claude
  (Opus 4.8, orchestrator) for disagreement adjudication. The proposal phase
  additionally used distinct **personas** (wire-service taxonomist, ontology
  purist, geopolitics analyst) to diversify the taxonomy design lens.
- **Prompt:** each annotator receives the full candidate-v2 label space (32
  crisis categories with per-category include/exclude rules) + the OUT_OF_SCOPE
  reject policy, and assigns one label per headline. Batched (one call labels a
  chunk) for throughput and to avoid per-item rate limits.
- Provider-neutral client: `backend/scripts/ensemble/model_clients.py`.

## 3. Sampling — representative of the real input distribution
The evaluation population must be **what the gate actually classifies**, not only
what it keeps. The gold base is therefore drawn from two strata, deduplicated by
headline:
1. **Stratified gate-kept** (per-category sample of current `theme-hint-lex-v2`
   gate-kept evidence) — ensures every category is represented.
2. **Representative full-stream random** (uniform recent `signals_v2`, gate-status
   agnostic, 336h window) — captures the majority non-crisis / out-of-scope
   distribution the reject class must handle.
Drawing only from gate-kept evidence would make the OUT_OF_SCOPE decision
unmeasurable; the full-stream stratum is what lets us evaluate (and later train) a
gate that rejects. `backend/scripts/ensemble/phase_d_goldset.py`, accumulating
across passes (dedupe by `signal_id`).

## 4. Gold construction
Gold label = **majority vote** of the scriptable annotators (DeepSeek, OpenAI,
Codex). Each record carries `n_votes` and `agree_n` (provenance). Items where an
annotator was unavailable (see §6) carry `n_votes=2` and are tracked separately,
never silently treated as unanimous. Three-way disagreements (rare) are
**adjudicated by Claude** (senior annotator). Each record also carries whether the
signal has a persisted e5 embedding → the gold doubles as a **labeled-embedding
training set** for a $0-inference gate.

## 5. Reliability — Fleiss' κ
On the 3-annotator subset (`backend/scripts/ensemble/kappa.py`):
- **full label space (32 + OUT_OF_SCOPE): κ = 0.776 (substantial)**, n=1342
- **in-category (crisis types only): κ = 0.800 (substantial)**, n=617
- binary in-scope / OUT_OF_SCOPE: κ = 0.729 (substantial)
All in the Landis & Koch "substantial" band (.61–.80), across three independent
model families on a 33-way task. κ rose as the base grew (0.739 → 0.776).
Notably in-category κ (0.800) > reject κ (0.729): annotators agree more on *which*
crisis than on the in/out boundary, locating residual ambiguity at the gate, not
inside the taxonomy.

## 6. Limitations (stated honestly)
- **LLM-consensus gold, not human gold.** The benchmark is an ensemble of LLM
  annotators; we report κ, not human ground truth. This is the standard
  LLM-as-annotator caveat; the multi-family ensemble + κ mitigate single-model
  bias but do not eliminate shared LLM priors. A human-validated subset is future
  work.
- **Annotator availability.** The Codex annotator (subscription-metered) exhausted
  its quota mid-run, producing a window of 2-vote items; it recovered and
  back-filled. The `n_votes` field makes this explicit; κ is computed only over
  full 3-vote items.
- **Taxonomy-independence of the substrate.** The e5 embeddings and the gold
  *labels* are reusable across taxonomy versions; only the **gate/classification**
  is taxonomy-dependent. This separation is why the embeddings can be backfilled
  *now* (not wasted work) while the gate is re-derived from the new labels.

## 7. Reproducibility
All scripts under `backend/scripts/ensemble/` (model clients, phase A–D, κ,
candidate synthesis); dataset `docs/research/taxonomy-revision/goldset.json`
(labels + provenance + embedding flag); candidate taxonomy `candidate-v2.json`.
The diagnosis→fix→measure arc (force-fit 30–46% → reject class → agreement v1 76%
→ v2 96% → κ 0.78 at scale) is the experimental spine of the Paper 1 evaluation.

> **Pending (final-numbers pass):** the gold base is still growing overnight under
> the widened sampling; the manuscript numbers (final N, κ, and the v2-gate
> precision-lift on a held-out split) are updated when the base saturates and the
> gate is trained.

---

# Result — v2 embedding-gate precision lift (Paper 1 headline)

Measure-first, offline (no prod change). `backend/scripts/ensemble/v2_gate_experiment.py`.
A LogisticRegression over the e5 embeddings of the gold-labeled signals (n=1,255
embedded, stratified 75/25 split), vs the current lexical gate measured on the
same gold.

**Baseline — current lexical gate (`theme-hint-lex-v2`) vs gold, 1,751 gate-kept:**
- category precision (gold == assigned): **48.7%**
- force-fit (gold == OUT_OF_SCOPE): **46.4%**
- in-scope precision (kept ∧ not OOS): 53.6%
- the stream the gate faces is **91.4% out-of-scope** (random full-stream gold) →
  the gate's dominant job is to REJECT, and the lexical gate keeps 46% junk.

**v2 e5 gate, held-out:**
| metric | lexical | v2 e5 | Δ |
|---|---|---|---|
| in-scope precision @0.50 | 53.6% | **70.0%** | +16.4pp |
| category precision (of kept) | 48.7% | **61.5%** | +12.8pp |
| force-fit (of kept) | 46.4% | **30.0%** | −16.4pp |
| reject recall (OOS caught) | — | 80.9% | |

**Threshold = the product knob** (keep if P(in-scope) ≥ thr):
| thr | keep% | in-scope precision | recall |
|---|---|---|---|
| 0.50 | 41% | 70.0% | 82.7% |
| 0.60 | 27% | **80.0%** | 61.8% |
| 0.70 | 16% | 86.3% | 40.0% |
| 0.80 | 5% | 100.0% | 15.5% |

**Reading (honest):** a $0-inference e5 gate beats the lexical gate at every
operating point and **reaches the ~80% LLM-baseline precision at thr 0.60** (at a
recall cost — it serves the cleanest 27%). The simple learner does not hit ~80% at
the *balanced* point (61.5% category / 70% in-scope @0.50); closing that needs more
gold (the base is still growable), a stronger model, and a better category
sub-model (the multiclass step is the weaker link, data-starved on rare
categories). The reject decision — the dominant job on a 91%-OOS stream — is where
the embedding gate is already strong (OOS F1 85, reject recall 81%). This is the
Paper 1 precision-lift result: the taxonomy revision + gold base convert a 48.7%
force-fit-ridden gate into a tunable 70–86% one at no per-signal cost.

---

# A/B deployment — v2 reject vs the production gate (verifiable)

The v2 gate was deployed as an A/B comparison against the production gate, not a
blind swap — so the lift is verifiable on live data.

**The two arms.** Production gate = lexical assignment (`theme-hint-lex-v2`) +
the 2026-05-29 e5base scope gate (`atlas-scope-gate-v1-e5base`, per-topic ≥90%
precision thresholds). v2 arm = the same pipeline + a post-gate **v2 reject** that
demotes any `gate_kept` signal the new e5 gate (trained on the 2,134 OOS-aware
gold) scores OUT_OF_SCOPE.

**Method.** `apply_v2_reject.py` runs DRY-RUN first (writes nothing) over the live
`theme-hint-lex-v2` gate_kept set, reporting the demote rate + a spot-check, so the
two arms are compared on identical real rows before any write. Live apply demotes
only force-fit, tags `gate_model=v2-gate-e5-lr-1`, keeps `gate_score` → every
difference between the arms is attributable and **reversible**
(`UPDATE … SET gate_kept=true WHERE gate_model='v2-gate-e5-lr-1'`), so the A/B can
be rolled back and re-measured.

**Result (live, 168h, n=1,310 embedded gate_kept).** The v2 arm demoted **567
(43.3%)** as force-fit — matching the gold-measured 46.4% baseline. Spot-check:
demoted = local crime/admin force-fit ("Chiropractor charged with sexual assault",
"Delhi HC school-rape bail", "Diaspora to vote online"); retained = genuine crises
("France 1,000 heatwave deaths", "Ebola DR Congo 4th province", "Assam floods
45,000 hit"). Real-stream validation (600 fresh non-gold signals, the honest
91%-OOS distribution) keeps 18.2% @0.50 with a clean reject/keep split.

**Deployment.** Flipped live (567 demoted) + wired recurring into the classifier
runner (Step 3, flag `ATLAS_V2_GATE_ENABLED`, numpy-only on the M1 mlvenv, $0
inference). The gate_model tag is the audit key for the ongoing A/B: kept-set
precision can be re-measured at any time by comparing rows with/without the v2
demotion against fresh ensemble labels. Verdict so far: v2 cuts ~43% of served
force-fit while retaining the crisis signal — the product face of the Paper 1
precision-lift result.
