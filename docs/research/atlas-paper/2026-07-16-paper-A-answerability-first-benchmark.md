# Paper A — Answerability-First Narrative Intelligence: an evidence-role benchmark and validation methodology

**Status:** skeleton (not a full manuscript) · **Date:** 2026-07-16 · results
integrated through 2026-08-03
**Series role:** backbone. This paper *earns the right to measure*; Papers B and C
cite its benchmark and its LLM-panel-gold disclosure.
**Reframe authority:** `docs/research/atlas-paper/2026-07-16-papers-reorganization-justification-framing.md`
(the papers are a **justification layer** — "everything Atlas shows is valid because
it is backed by measured math, inference, and experiment; nothing is assumed, not
even the non-decisions" — **not** a superiority pitch).

**What changed in the 2026-08-03 integration.** The "answerability-first" frame
finally has an end-to-end answerability *measurement*: a frozen, anti-circular
gold analyst-query set with negative controls, run as a day series on the live
product across two arms (API-served threads vs rendered UI), with day-over-day
answer **persistence** as a first-class metric (§3.7, R8). And the validation
methodology gained its production stress test: the label court — an LLM judge
whose verdict gates what serves — was calibrated by five successive blind
hand-checks and a full promotion census, so "LLM-judge as certificate" is now a
measured quantity (~70% serving precision), not an assumption (§3.8, R9). The
substrate non-decision (§3.6) is extended by the identity-layer STOP and the
embedding bake-off, whose full treatment lives in Paper B Part II.

> **Standing disclosure, repeated in every methods and limitations section.**
> Precision, throughout this paper, means **agreement with a 3-LLM consensus panel**
> (majority vote of `claude-sonnet-4-6`, `gpt-4.1`, `deepseek-chat`). The count of
> rows adjudicated by a **human** is **n_rows_with_human_gold = 0**. Every "precision"
> number is panel-relative. The LLM baselines are a **calibration reference on a
> shared answer key**, never an opponent Atlas is racing.

---

## Title / target venue

**Title:** *Answerability-First Narrative Intelligence: an evidence-role benchmark
and an LLM-panel validation methodology for zero-cost topic classification.*

**Target venue:** a measurement/eval track — e.g. NLP+CSS / *ICWSM* (computational
social science, media monitoring) or a *EMNLP/NAACL* resource-and-evaluation track.
The contribution is a **reproducible benchmark + a validation methodology with an
honest gold-provenance story**, not a leaderboard result.

---

## Abstract (≈170 words)

Narrative-intelligence systems must tell an analyst not merely *what topic* a news
signal touches but *what evidentiary role* it plays — is it primary evidence, context,
a reaction, or noise. We argue this "answerability-first" framing is a design
*decision that must be justified*, and we build the measurement apparatus to justify
it at two levels. At the classification level: on a stratified 3-vendor
LLM-consensus benchmark (N=660 usable; Fleiss κ=0.625), a zero-inference-cost static
classifier reaches 41.6% panel-agreement precision [37.8, 45.5], calibrated against
an LLM reference at 78.6% zero-shot on the same key; errors are semantic (substring
noise 0.6%), GDELT theme-hints are measured net noise (removal +7.4pp, CI [5.2,
9.6]), and an OUT_OF_SCOPE reject class raises annotator agreement 76%→96%. At the
task level: a frozen, anti-circular gold analyst-query set (20 queries + 6
honest-absence controls) run as a day series measures end-to-end answer rate
(7–29%, n=14), an honesty floor, and day-over-day answer **persistence** — whose
initial total churn, and first later hold, localize the system's binding failure to
the identity layer. A production LLM-judge serving certificate is blind-check
calibrated (~70% precise). Gold is LLM-panel consensus; human-adjudicated rows:
zero.

---

## 1. Thesis (in justification form)

Atlas ships an **evidence-role classifier over a curated crisis taxonomy, distilled
into a $0-inference lexicon, with a reject class and a scope gate**. Each of those is
a *choice that could have been arbitrary*. The competitive-superiority question
("does Atlas beat X?") is the wrong question and the one that trips the
LLM-as-gold circularity. The question this paper answers is:

> **Is each classification-design decision non-arbitrary — backed by a measurement
> of the naive alternative — and is the measurement apparatus itself honest about its
> gold?**

The contribution is therefore two-part and defensive:

1. **A benchmark + validation methodology** that can *tell* whether a design decision
   is justified: stratified sampling, an independent 3-LLM consensus panel with a
   reported Fleiss κ, Wilson + stratified-bootstrap intervals, and a written
   gold-provenance disclosure (LLM-panel, zero human rows).
2. **Five justified decisions** measured on that apparatus (§3): the evidence-role
   schema, the LLM-distilled lexicon, the removal of GDELT theme-hints, the
   OUT_OF_SCOPE reject class, and the scope gate — each with the naive alternative
   measured and ruled out, and each with its honest limit stated (including one case,
   the anchoring control, where our own de-biasing turned out to be within noise).

We take the LLM baseline strictly as a **calibration reference**: a static,
zero-cost classifier sitting ~37pp below an expensive model *on the same answer key*
is a legitimate calibration statement about how far a cheap method is from a semantic
reader — not a claim that either "wins."

---

## 2. Related work (honest positioning, no strawman)

- **GDELT / GDELT-GKG themes & EventRegistry.** GDELT-GKG's theme taxonomy is a
  keyword-driven, high-recall event/theme layer; EventRegistry and Media Cloud
  provide large-scale multilingual news aggregation and clustering. We *use* GDELT
  themes as an input and treat them as a hypothesis to test, not a ground truth:
  §3.3 measures that theme-hints are net noise on our key. We do not claim GDELT is
  "wrong"; we claim its theme overlap is a *low-precision candidate generator* for
  crisis assignment, and we measure it.
- **BERTopic + c-TF-IDF and neural topic modeling.** BERTopic (UMAP → HDBSCAN →
  class-based TF-IDF) is the closest external method to Atlas's discovery layer. We
  position our clustering findings against it honestly: a **BERTopic-proper external
  baseline (UMAP + c-TF-IDF) has not been run** (toolchain block, §7); what we *do*
  report is an HDBSCAN-over-e5 sweep that isolates a recall/purity cliff. We do not
  claim to beat BERTopic — we flag it as the missing external comparator that would
  isolate the schema's own contribution.
- **LLM-as-annotator / LLM-as-judge evaluation.** A growing literature uses LLMs as
  annotators and judges; the known hazards are label drift, single-model bias, and
  circularity when the judge and the system share priors. Our methodology *is* an
  instance of this paradigm and inherits its central caveat; we mitigate with a
  **multi-family panel + reported κ + a fixed, declared gold set**, and we foreground
  the caveat rather than bury it (§6). Two of our findings are themselves
  methodological contributions to this literature: an LLM judge scored against
  *production* labels is confounded by label drift (§3.4); and a production LLM
  judge whose verdict *gates serving* can and should be calibrated the way a
  human annotator would be — repeated blind hand-checks against its verdicts,
  failure-mechanism classification per round, and a census-scale precision
  measurement of its PASS stamp (§3.8: the label court arc, GB1→GB5 blind checks
  3/10 → 7/10 plateau; certificate precision 70.5% at census scale, n=244,
  inter-judge 98.4%).
- **Embedding anisotropy — Mu & Viswanath / Arora et al. "all-but-the-top."** The
  observation that contextual/​static embeddings occupy a narrow anisotropic cone,
  curable by mean-removal + top-principal-direction projection, is directly relevant:
  §3.6 reports that e5 signal embeddings have near-perfect pairwise separability
  (AUC 0.985) masked by scale compression, and that all-but-top-k=1 whitening opens
  the same/different gap 4.4×. We credit this line of work and report two
  **bounds** on it: whitening cures pair geometry but does not by itself dissolve
  the cluster-level recall ceiling; and in *multilingual* e5 the removed dominant
  direction carries the **cross-lingual alignment**, so whitened cosine collapses
  same-event pairs across languages (identity-gate measurement,
  `docs/research/recall-229/2026-07-28-whitened-identity-taus.md`) — a setting
  boundary the original monolingual results could not have exposed.
- **HDBSCAN.** Density-based clustering with a variable-density model; we use it as
  the discovery substrate and report its parameter-cliff behavior on short-text news
  embeddings as a measured constraint, not a defect.

---

## 3. Design decisions (each in the 5-part template)

### 3.1 Decision: an evidence-**role** schema, not a single topic label

- **Decision.** Every signal→topic assignment carries a *semantic role*
  (primary_evidence / context / reaction / analysis / entity_reference / noise), not
  only a topic label.
- **Stakes.** The tempting, standard design is one flat label per document. It is
  cheaper, matches most topic-modeling output, and "looks done."
- **Backing.** On the N=660 consensus benchmark, incorrect rows are **dominated by
  `off_topic` and `scope_mismatch`**; pure **substring noise is only 0.6%** of
  incorrect rows (RQ2 error-composition artifact,
  `.../reports/llm-baseline/2026-06-02-rq1-error-composition.json`). The errors a
  flat label makes are *semantic role* errors — a reaction or an entity mention
  charged as evidence — which a single layer cannot express or repair.
- **Alternatives ruled out.** The flat single-label classifier *is* Atlas v2 as
  measured (41.6%); its failure anatomy shows the residual is not regex-fixable
  keyword noise (0.6%) but role/scope confusion — so "edit more keywords" is
  measured to be a dead lever.
- **Honest limit.** The evidence-role *schema value* (RQ3) is only **partially**
  measured: the role student (v1) shows semantic errors binary-correctness hides, but
  a role-level precision/recall on a held-out human set does not exist
  (n_rows_with_human_gold = 0).

### 3.2 Decision: an LLM-**distilled** lexicon at $0 inference

- **Decision.** The production classifier is a static multilingual lexicon +
  taxonomy, *distilled* from LLM labels, run at zero per-signal inference cost.
- **Stakes.** The obvious alternative is to call an LLM per signal (78.6–81.1% on our
  key). At Atlas's ingest volume that is a recurring cost and a latency/availability
  dependency.
- **Backing (calibration, not victory).** The LLM reference sits at **78.6% zero-shot
  [75.3, 81.7]** and **81.1% few-shot [77.7, 84.0]**; the static classifier sits at
  **41.6% [37.8, 45.5]** *on the same gold key* — a calibration gap of ~37pp that
  quantifies exactly how much a cheap static method concedes to a semantic reader.
  The distillation makes the lexicon reproducible from a versioned label set at
  $0 inference.
- **Alternatives ruled out.** Per-signal LLM inference is ruled out on cost/latency
  grounds, not accuracy — we *state* that the reference is more accurate on the key
  and treat the 37pp as the price of $0 inference, a design trade the analyst can see.
- **Honest limit.** The distilled artifact is English-majority (batch-03) and has
  **no temporal hold-out** (§6); "distillation preserves the reference's decisions"
  is unmeasured beyond the training window.

### 3.3 Decision: **remove** the GDELT theme-hints (the cleanest experiment)

- **Decision.** Demote GDELT-GKG theme-overlap from a hard candidate-generator to (at
  most) a weak confidence feature.
- **Stakes.** Theme-hints are the intuitive backbone of a GDELT-based classifier;
  four internal docs treated "hints carry precision" as a 🔒 assumption that must not
  be removed.
- **Backing.** `backend/scripts/gdelt_hint_ablation.py` (read-only, repeatable) on the
  batch-03 consensus gold: **theme-hint-dependent assignments are 20.2% correct
  [14.9, 26.8]** versus a **40.9% baseline**; removing the hints (lexicon-standalone)
  **rises to 48.3%**, a delta of **+7.4pp with bootstrap CI [5.2, 9.6] excluding 0**,
  at a recall cost of ≤13%. The theme-dependent interval [14.9, 26.8] and the baseline
  [37.2, 44.7] do **not overlap** — the theme-only path is significantly worse than
  the engine average, i.e. a *net noise source* (the "KILL"-GKG-theme-fires-on-idiom
  hypothesis, measured).
- **Alternatives ruled out.** "Keep the hints, they must help" is the naive belief;
  it is measured false. The 13% true-loss is 86–100% recoverable by the semantic path
  at a moderate cosine threshold (threshold-sensitive; report the curve, not a point).
- **Honest limit.** One benchmark, English-majority; the *ablated* engine assumes the
  lexicon becomes a standalone candidate-generator (an implementation follow-up); no
  temporal hold-out on the ablation itself. **This is the paper's cleanest,
  fully-backed experiment.**

### 3.4 Decision: an OUT_OF_SCOPE **reject class** as the taxonomy fix

- **Decision.** Add a rigorous OUT_OF_SCOPE reject class + per-category
  include/exclude rules to the crisis taxonomy (candidate-v2), rather than expand into
  an all-news taxonomy or add categories.
- **Stakes.** A 100%-crisis taxonomy with no reject option *forces* every non-crisis
  signal into the nearest crisis bucket; the tempting fix is "add more/better crisis
  categories," which the evidence shows is not the problem.
- **Backing.** A **multi-model × multi-persona ensemble** (DeepSeek `deepseek-chat`,
  GPT-4o, GPT-5.5/Codex, Claude-orchestrator; personas: wire-taxonomist,
  ontology-purist, geopolitics-analyst) diagnosed force-fit and measured the fix:
  - *Phase A (diagnosis):* on 50 gate-kept evidence headlines, **30% ensemble-unanimous
    (46% DeepSeek) are OUT_OF_SCOPE** — force-fit into a crisis bucket (a shopping
    article → "Heat health risk"; a book review → "Armed conflict").
  - *Phase C (fix, agreement):* the same headlines under v1 vs v2 prompts →
    inter-annotator agreement **76% → 96% (+20pp)** driven by both annotators agreeing
    on the reject label.
  - *Reliability:* a growing gold base (732 signals across a broad pass; 75%
    3-model-unanimous) with **artifact-reported Fleiss κ in the "substantial" band**
    (`kappa.py`; the artifact reports κ≈0.74–0.80 across label-space/in-category cuts,
    with the value climbing as the base grew — see §6 note on the pending
    final-numbers pass and the κ inconsistency across doc versions).
- **Alternatives ruled out.** "Rename/add categories" is ruled out: both proposing
  personas **kept the ~30 categories** and located the fix in the reject class +
  boundaries. The category *names barely move*; the value is refusing the non-crisis
  half.
- **Honest limit.** The random 72h sample is non-crisis-heavy, so the +20pp is driven
  mainly by agreement on the reject label for the non-crisis majority — the core fix,
  but it under-stresses *crisis-vs-crisis* separability. Gold is LLM-ensemble, not
  human (n_rows_with_human_gold = 0). The three contested categories
  (housing-cost-pressure, humanitarian-access-conflict, mining-royalty-risk) need
  their own targeted κ pulls.

### 3.5 Decision: a scope **gate** (abstain) rather than lowering thresholds for coverage

- **Decision.** Keep a per-topic scope gate that *abstains* on low-confidence rows
  rather than assign everything.
- **Stakes.** The intuitive move for "more coverage" is to lower thresholds; abstaining
  trades recall for precision and looks like "showing less."
- **Backing.** The M1 scope gate lifts precision from **41% to 70.3% at 37.3%
  coverage** on scored rows — i.e. serving the cleanest ~37% at ~70% precision.
- **Alternatives ruled out.** "Assign everything" is the 41% full-taxonomy operating
  point; the gate is the measured way to buy precision at a stated recall price the
  analyst can see (a precision-at-coverage point on a curve, never conflated with the
  full-taxonomy headline).
- **Honest limit — winner's-curse.** The gate's 70.3%@37.3% is **not yet verified on a
  held-out split**: only the downstream *student* model has shown cross-validation, not
  the gate thresholds themselves, which were tuned per-topic to ≥0.90 target precision.
  Until a held-out confirmation exists, treat 70.3% as an in-sample, possibly optimistic
  operating point. (Deployment note: a live A/B reject arm, `gate_model=v2-gate-e5-lr-1`,
  demoted **43.3% (567/1310)** of gate-kept rows as force-fit over 168h — reversible and
  audit-tagged — consistent with the gold-measured force-fit share; this is an
  operational cross-check, not a held-out precision proof.)

### 3.6 Decision (a *non*-decision, still backed): whitening is a geometry cure + stabilizer, **not** the recall lever

- **Decision.** Apply all-but-top-k whitening *selectively* where it measurably helps
  (pair-similarity consumers), and **do not** claim it as the clustering-recall fix.
- **Stakes.** An early result (a single 0.477-recall sample) tempted the claim
  "whitening crosses the recall/purity cliff." Publishing that would have been a
  measure-once error.
- **Backing (measure-twice).** `cluster_whiten_sweep.py` (3 samples, 2026-07-07):
  signal-pair separability is real and reproducible — same/different cosine
  **0.916 / 0.788**, **AUC 0.985**, gap opening **4.4×** after all-but-top-k=1. But the
  initial recall was **high-variance and non-reproducing (0.477 / 0.062 / 0.109 across
  three samples)**, and the best joint HDBSCAN point is `e5_whiten_k1` **recall 0.109 /
  purity 1.0** vs `e5_raw` **recall 0.756 / purity 0.146** — *each at its own
  best-joint config* (`e5_whiten_k1` at `eom mcs=5 ms=1`; `e5_raw` at
  `eom mcs=8 ms=3`); at a **matched** config (`eom mcs=8 ms=1`) raw e5 recall
  collapses to ~0.09 (see Paper C, Table 3). The cliff *persists*; whitening
  picks the purity end.
- **Alternatives ruled out.** "Whitening is the recall lever" is ruled out *by our own
  re-measurement*. The recall/coverage lever is **scoped partitioning** (§ Paper C /
  R1), not whitening. Two later measurements complete the boundary (full treatment:
  Paper B §4): whitening as an **identity gate** was killed by a pre-registered
  tail rule (anchor-gate whitened gap **−0.5471**; the mechanism is the
  cross-lingual collapse named in §2), and an **encoder swap** was killed by its
  own bake-off (no candidate space fixes argmax dispersion; e5-large ≡ e5-base to
  three decimals; the strongest space on identity statistics, bge-m3, had finished
  *last* in the earlier assignment-gate bake-off —
  `docs/research/recall-229/2026-07-31-embedding-bakeoff-v2.md`). The substrate
  non-decision is therefore three measurements deep: not the recall lever, not a
  gate, and not fixable by a better encoder.
- **Honest limit.** This is included as an exemplar of the paper's method (measure
  twice; walk back a tempting positive). The clustering-recall consequence is owned by
  Paper C; the identity-layer consequences by Paper B; Paper A owns only the
  substrate/geometry claim.

### 3.7 Decision: measure answerability end-to-end — an anti-circular gold query set with honest-absence controls, run as a day series

- **Decision.** The system's primary metric is not a component precision but an
  **end-to-end answer rate**: 20 frozen analyst-natural queries scored 0–3 by a
  temp-0 judge against the *served* product surface, plus 6 negative controls
  whose correct behaviour is an honest absence; the run repeats on consecutive
  days and **day-over-day answer persistence is a first-class metric**.
  Instrument: `docs/research/gold/gold-query-set-v1.json` (sha-pinned across
  every run) + harness `run_gold_query_eval.py` (`gold-query-eval-v1`, frozen
  mid-series by design).
- **Stakes.** Component metrics (41.6% precision, coverage percentages) cannot
  say whether an analyst's question gets answered; and a gold set authored from
  the system's own served output would be circular. The tempting shortcut — score
  one good day — hides the failure mode that turned out to dominate.
- **Backing (construction).** Anti-circularity: queries were authored from **raw
  `signals_v2` headlines** (the ingest stream), not from served threads, so every
  query is answerable in principle without presupposing the pipeline formed the
  right thread. Six negative controls (absent stories, unanswerable
  provenance/forecast/opinion asks) must score ≤1 or the run is void — an
  honest-absence bar that penalizes confident fabrication, and it has caught
  real behaviour (controls 6/6 PASS on every run to date). A five-query
  **external-agenda extension** (EQ-01..05, authored from world knowledge
  *outside* the corpus, with a mandatory web-search ingestion-gap check) exists
  because the raw-headline construction is structurally blind to what was never
  ingested (`docs/research/gold/2026-07-29-gold-external-5.md`).
- **Backing (what the series measured).** Answer rate across four runs:
  **14% → 7% → 21% → 29%** (n=14, one query = ±7pp; both ≥21% readings
  post-date the serving-enforcement flip, §3.8/Paper B §4.6 — attribution is an
  ensemble, stated in the artifact). The single loudest finding is
  **instability**: GQ-02 (Berlin Pride) was answered with a 26-receipt on-topic
  thread on day 1 and served a *football-coach appointment* on day 2 while the
  story remained in-corpus — an answer that exists on day N and vanishes on day
  N+1 (`2026-07-28-rerun-comparison.md`). Persistence therefore became a metric:
  churn across the first three day-pairs was near-total (1/2, 0/1 answers
  retained; on day 3 every scored thread id differed from day 2), and the first
  full hold — **3/3 answers retained + 1 gained, with 4 thread identities
  surviving the night** — arrived only on the first day-pair run entirely under
  the court-gated lifecycle + fetch-side enforcement ensemble
  (`2026-08-03-gold-eval-day4.md`). A same-instrument re-run also **refuted the
  obvious confounder**: restoring the label blackout did not raise the answer
  rate (14%→7%); labels bought *honesty floors*, not answers.
- **Backing (the two-arm result).** The same gold set was run against the
  **rendered UI** under a pixels-only rubric
  (`docs/research/gold/rubric-v2-ui.md`, 2026-07-30 full-20 run): answered
  14.3%, **informed 71.4%**, honesty 0.83, and a navigation-loss defect on
  20/20 queries; the UI arm scored ≥ the API arm on all twenty (UI-BETTER ×14,
  SAME ×6, WORSE ×0). The 5× gap between informed and answered is the paper's
  sharpest decomposition: **retrieval has the material; assembly and navigation
  lose it** — the API arm measures what Atlas *concluded*, the UI arm what Atlas
  *has*. (The interface-side consequences are the tech report's; Paper A owns
  the two-arm instrument design.)
- **Alternatives ruled out.** Scoring the system on its own served labels
  (circular; the §3.4 drift warning), single-day snapshots (blind to the
  dominant failure mode), and a semantic-search recovery of the failures —
  measured NO: 5 of 12 failures had no thread in any lifecycle state and 3
  failed downstream of retrieval, so search-side semantics buys an honesty
  floor (0.17 → ~0.50), never answers
  (`docs/research/gold/2026-07-27-semantic-search-feasibility.md`).
- **Honest limit.** n=14 real queries — one query moves the rate ±7pp; the band
  statement (7–29%) is the honest form. Single judge (DeepSeek temp-0), no κ,
  and judge-application variance is a *measured* term (one query scored 3 then 2
  on identical structural facts). The judge chain's honesty floor is a lower
  bound. Day-4 attribution is confounded across three simultaneous serving
  changes, stated in the artifact. A time-shifted placebo (K3) has not run.

### 3.8 Decision: an LLM-judge *serving certificate*, calibrated like an annotator — the label court arc

- **Decision.** A nightly temp-0 LLM court judges every served label against its
  own receipts (`label_status ∈ {entailed, partial, failed, withheld}`); the
  verdict is not advisory — it **gates serving** (court-failed threads are
  damped/withheld; lifecycle revival promotes only court-`entailed` topics; a
  quote-gate and withhold lane make "attempted, ungrounded" a durable state).
- **Stakes.** An LLM judge in the serving path is exactly the pattern §2's
  literature warns about. Shipping it *unmeasured* would assume the thing this
  series exists to never assume; the alternative — no label vetting — measurably
  serves labels that contradict their own receipts (the sibling-finder
  measurement found whole witness families dissolving on inspection because
  labels lied: a "Halkidiki wildfire" that is a Chania workshop explosion, a
  "Crimea-Congo fever death" that is a Spanish femicide —
  `docs/research/recall-229/2026-07-29-sibling-finder-v2-measurement.md` §4.1).
- **Backing — the calibration protocol.** Five successive **blind hand-check
  rounds** (GB1–GB5): deterministic umbrella draws, judgments written before any
  court verdict is read, ≥8/10 agreement bar, and — from round 4 — every
  disagreement diagnosed against the court's own ledgered reason and classified
  by failure mechanism. Trajectory: **3/10 → 6/10 → 7/10 → 7/10 → 7/10** — each
  round killed a named mechanism (receipt contamination, calibration, scale
  collapse), the bar was never reached, and the flag never flipped on a failed
  gate (`docs/research/label-court/2026-07-29-gb{,2,3,4,5}-blind-check.md`).
  A stratified **blind-spot audit** (62 topics) then located the court's real
  error structure: **zero blind spot at the PASS stamp** (0/30 court-`entailed`
  labels contradicted their receipts) with over-strictness on `partial` (13/15
  read fine to a human) — and, decisively, that the operative gap was
  **enforcement, not judgment**: 66% of active topics were court-FAILED *and
  still serving*, and the biggest served rows carried no verdict at all
  (`2026-07-29-court-blindspot-audit.md`). That finding redirected the work to
  the serving path (fetch-side enforcement, Paper B §4.6 / tech report §serving)
  rather than to more judge tuning.
- **Backing — the certificate's precision, at census scale.** Once the verdict
  gated lifecycle promotion, its PASS stamp was measured as a **census, not a
  sample**: all 244 court-certified revival promotions double-judged
  (inter-judge agreement **98.4%**) — strict-real **70.5%**, vs **37.5%** for
  ungated revival (+33pp), with the deficit attributed by class (certified
  generic-label blobs 11.5%, certified PR-wire junk 6.1%, judge mismatch 11.9%)
  and explicitly *not* to post-certification decay (0/72 failures decayed) —
  `docs/research/recall-229/2026-08-03-tf3b-gate-c-census.md`. The court also
  over-blocks (11.1% of sampled fails were real stories), the other face of the
  same certificate.
- **Alternatives ruled out.** Serving unvetted labels (measured: label↔evidence
  divergence is common enough to dissolve witness families); trusting the judge
  unmeasured (GB1 came back 3/10 — the first blind check alone justified the
  protocol); and treating judge quality as the binding constraint (the audit
  showed enforcement was).
- **Honest limit.** The blind checks are single-human-equivalent judgments, not
  a panel; the ≥8/10 bar is unreached after five rounds, so the court's verdict
  quality is *bounded*, not certified — which is exactly why its serving role is
  a gate on `entailed` (the stamp with measured 0-blind-spot and ~70%
  census precision) rather than trust in the full verdict scale. The court
  judges **entailment, not newsworthiness** — certified PR-wire junk is a
  measured consequence, with its own follow-up. Capacity is finite (~1,700
  judgments/day after withhold-backoff) and the court was fully inert for five
  nights under a provider-credit outage — provider redundancy is a standing
  operational dependency.

---

## 4. Methods

### 4.1 Data & sampling
- **Population:** `signals_v2` news signals; the classifier under test is Atlas v2
  (`theme-hint-lex-v2`), multilingual lexicon + curated GDELT theme-hints, writing
  `signal_topic_assignments` with confidence/gate metadata.
- **Benchmark (canonical regime):** batch-03 — **691 stratified rows** from a 7-day
  window, **660 usable** (31 ties dropped); Atlas-scored subset n=635 (264 correct).
  Stratified across 30 crisis topics × 4 buckets.
- **Taxonomy-ensemble sampling:** two strata, deduped by headline — (1) stratified
  gate-kept evidence (every category represented) and (2) representative full-stream
  random (336h, gate-agnostic) so the OUT_OF_SCOPE decision is measurable on the
  ~91%-out-of-scope real distribution.
- **No temporal hold-out anywhere on the classification benchmark** (§6): batch-03
  rows carry no timestamps and the underlying signals were purged under retention,
  so all generalization language is hedged to in-window.
- **Task-level series (§3.7):** the frozen 20+6 gold set
  (`gold-query-set-v1.json`, sha-pinned) run against live production on
  2026-07-27 / 07-28 / 07-31 / 08-03 with an unmodified harness; the UI arm ran
  once (2026-07-30) under the pixels-only rubric v2 with the API arm's same-set
  run as its baseline. Persistence is computed over adjacent-day pairs on the
  answered set (score ≥2).
- **Court calibration (§3.8):** deterministic blind draws
  (`ORDER BY md5(id || salt)`), judgments recorded before verdict reveal, ledgered
  reasons retrieved per disagreement (rounds 4–5); the promotion census is
  exhaustive over its cohort (n=244, 2 judges + tiebreaker) using the court's own
  receipt scoping (engine_version + quarantine — the GB1 lesson).

### 4.2 Labels & gold provenance (the disclosure, in full)
- **Consensus benchmark gold** = majority vote of a 3-vendor panel:
  `claude-sonnet-4-6`, `gpt-4.1`, `deepseek-chat`. **Fleiss κ = 0.625** (the artifact
  additionally reports a binary correct-vs-not κ = 0.734 on a 684-row 3-annotator
  subset — "substantial," Landis–Koch).
- **Taxonomy-ensemble gold** = majority vote of scriptable annotators (DeepSeek,
  GPT-4o, Codex/GPT-5.5) with Claude-orchestrator adjudication of 3-way disagreements;
  each record carries `n_votes`/`agree_n` provenance and an e5-embedding flag.
- **n_rows_with_human_gold = 0.** Every precision number is agreement with an LLM
  panel; the LLM zero/few-shot baselines are a **calibration reference on the shared
  key**, not opponents.

### 4.3 Metrics & statistical conventions
- **Precision** = panel-agreement (correct / labeled).
- **Intervals:** Wilson score interval for every proportion; **stratified bootstrap**
  (10,000 resamples, seed 20260527) for the headline and for ablation deltas. A delta
  is called significant only when its bootstrap CI excludes 0 (e.g. theme-hint removal
  +7.4pp [5.2, 9.6]).
- **Reliability:** Fleiss' κ for ≥3 annotators; Cohen's κ / pairwise agreement for
  2-annotator cuts; report the κ *and* the label-space size (a 32-way + reject task).
- **Significance tests:** two-proportion z where two independent samples are compared
  (e.g. the anchoring control, §5).

---

## 5. Results (real numbers)

### R1 — Headline benchmark (calibration reference on a shared key)
| Method | Precision | Wilson 95% | Bootstrap 95% | n (labeled) | Gold |
|---|---:|---|---|---:|---|
| Atlas v2 (static, $0 inference) | **41.6%** | [37.8, 45.5] | [38.4, 44.7] | 635 | 3-LLM panel (κ=0.625) |
| LLM zero-shot *(calibration ref)* | 78.6% | [75.3, 81.7] | [75.8, 81.3] | 627 | same key |
| LLM few-shot *(calibration ref)* | 81.1% | [77.7, 84.0] | [78.2, 83.9] | 597 | same key |

*Reading:* a zero-cost static classifier sits ~37pp below the semantic reference on
the same key. This is a calibration statement, not a contest.

### R2 — Error composition (why the residual is not regex-fixable)
| Failure bucket | Share of incorrect rows |
|---|---|
| off_topic | largest |
| scope_mismatch | second |
| substring noise | **0.6%** |

### R3 — Theme-hint ablation (fully backed)
| Engine | Correct / usable | Precision | Wilson 95% |
|---|---:|---:|---|
| baseline (theme-hints on) | 270 / 660 | 40.9% | [37.2, 44.7] |
| theme-hint-dependent path only | 35 / 173 | **20.2%** | [14.9, 26.8] |
| ablated (lexicon-standalone) | 235 / 487 | **48.3%** | [43.8, 52.7] |
| **Δ ablated − baseline** | — | **+7.4pp** | bootstrap [5.2, 9.6] (excludes 0) |

> **Denominator footnote (same classifier, two numbers — not a conflict):** the
> headline **41.6%** is over the n=635 *gate-scored* subset; the ablation
> **40.9%** is over the full n=660 benchmark denominator (270/660). Same static
> classifier, different scoring population — chain neither as if the other.

### R4 — Taxonomy reject class (ensemble)
| Measurement | v1 | v2 (reject class) |
|---|---:|---:|
| inter-annotator agreement (Phase C, 72h sample) | 76% | **96%** |
| Phase A force-fit (OUT_OF_SCOPE, ensemble-unanimous / DeepSeek) | 30% / 46% | — |
| gold base reliability (Fleiss κ, artifact-reported, "substantial" band) | — | κ≈0.74–0.80 (final-numbers pass pending) |

### R5 — Scope gate (winner's-curse caveat attached)
| Operating point | Precision | Coverage |
|---|---:|---:|
| assign-everything (full taxonomy) | 41% | 100% |
| M1 scope gate | **70.3%** | 37.3% |
*Not yet held-out-validated on the gate thresholds themselves — treat as in-sample.*

### R6 — Anchoring control (honesty about our own de-biasing)
| Framing | Crisis-only precision | n | IN-rate |
|---|---:|---:|---:|
| hinted (assigned category shown) | 53.8% | 316 | 47.9% |
| blind (unanchored) | 48.2% | 390 | 59.1% |

*The 5.6pp "anchoring effect" is **within noise**: two-proportion z = 1.48, p ≈ 0.14
(not significant).* Consequently we **do not** present a clean "48–54% de-biased
successor to 41.6%": that band is a point-pair across two samples (not a CI), on a
**changed denominator** (crisis-only, force-fits excluded) versus the 41.6% headline
(all usable assignments). The two numbers are **bridged, not interchangeable**, and
the crisis-only control has **not** been retro-applied to the full N=660 *headline*
(an open, light recompute — §7).

### R7 — Substrate geometry (measure-twice exemplar)
| Space | same p50 | diff p50 | gap | AUC |
|---|---:|---:|---:|---:|
| e5 raw (signal-pair) | 0.916 | 0.788 | +0.13 | **0.985** |
| all-but-top k=1 (signal-pair) | — | — | +0.57 (4.4×) | ≈0.985 |

*Whitening cures pair geometry and stabilizes density clustering; it does **not** by
itself cross the cluster-level recall/purity cliff (recall non-reproducing 0.477 /
0.062 / 0.109 across 3 samples). The recall lever is scoped partitioning — Paper C.
The identity-gate STOP and encoder bake-off (Paper B §4.1/§4.5) complete the
boundary.*

### R8 — The primary metric: answer rate, honesty floor, and persistence (day series, live product)

| run | answer rate (≥2, n=14) | honesty floor | controls | persistence vs prior run |
|---|---:|---:|---|---|
| 2026-07-27 | **14%** (2/14) | 0.17 | 6/6 PASS | — (first) |
| 2026-07-28 (labels restored) | **7%** (1/14) | 0.23 | 6/6 PASS | 1/2 held — **GQ-02 vanished in-corpus** |
| 2026-07-31 (fetch-mult M=2) | **21%** (3/14) | 0.09 | 6/6 PASS | 0/1 held — churn total; every thread id new |
| 2026-08-03 (M=2 + court-gated lifecycle + demotion sweep) | **29%** (4/14) | 0.40 | 6/6 PASS | **3/3 held + 1 gained; 4 identities survived** |

*Band statement: 7–29% at n=14 (±7pp/query). The label-blackout confounder is
refuted (07-28); the day-3 honesty collapse did not reproduce (08-03). Union of
answers across 4 days: 5/14; intersection: ∅ — persistence became a state only
under the final ensemble, and attribution within that ensemble needs day 5.
Sources: `docs/research/gold/2026-07-{27,28}-gold-query-eval.md`,
`2026-07-28-rerun-comparison.md`, `2026-07-31-gold-eval-day3-m2.md`,
`2026-08-03-gold-eval-day4.md`.*

**Two-arm decomposition (2026-07-30 UI run, rubric v2, pixels-only):** answered
**14.3%** · informed **71.4%** · honesty **0.83** · navigation-loss 20/20 ·
UI ≥ API on all 20 queries. The informed-vs-answered gap (5×) is an
assembly-and-navigation gap, not a retrieval gap
(`docs/research/gold/2026-07-30-ui-eval-v2-run.md`).

### R9 — The label court as a measured serving certificate

| measurement | value | source |
|---|---|---|
| blind hand-check agreement, rounds GB1→GB5 | 3/10 → 6/10 → 7/10 → 7/10 → 7/10 (bar ≥8/10 — never flipped on a failed gate) | `label-court/2026-07-29-gb*-blind-check.md` |
| PASS-stamp blind spot (entailed × contradicts) | **0/30** | `2026-07-29-court-blindspot-audit.md` |
| `partial` over-strictness | 13/15 read fine to a human | same |
| enforcement gap at audit time | 66% of active topics court-FAILED yet serving | same |
| certificate precision at census scale (promotions) | **70.5%** strict-real, n=244, inter-judge 98.4%; +33pp vs ungated | `recall-229/2026-08-03-tf3b-gate-c-census.md` |
| over-blocking | 11.1% of sampled fails were real stories | same |
| post-certification decay among failures | 0/72 | same |

---

## 6. Limitations

1. **LLM-panel gold, not human gold (stated first, everywhere).** Every precision
   number is agreement with a 3-LLM consensus panel; **n_rows_with_human_gold = 0**.
   The multi-family panel + reported κ (0.625 benchmark; "substantial" band for the
   ensemble base) mitigate single-model bias but do **not** remove shared LLM priors.
   The LLM zero/few-shot numbers are a calibration reference on the same key, not
   independent ground truth. A human-adjudicated subset is required future work.
   *A methodological corollary, itself a finding:* an LLM judge scored against
   *production* labels is confounded by label drift — so all judging in this paper is
   against a **fixed, declared** gold set, never the production labels.
2. **No temporal hold-out — anywhere.** Batch-03 rows carry no timestamps and the
   source signals were purged under retention. Every generalization claim is hedged to
   **in-window**; "the classifier generalizes to a future week" is untested and needs
   a fresh labeled window.
3. **Per-topic statistical power.** Several categories have n < 15 (e.g.
   forced-displacement n=6, press-freedom n=7, transport-corridor n=6); their per-topic
   Wilson intervals are wide and must not be read as stable per-category precision.
4. **κ inconsistency across doc versions.** The taxonomy-ensemble κ is reported at
   different growing-base snapshots (≈0.74 → ≈0.78 full label space; ≈0.80
   in-category; ≈0.71–0.73 reject); the manuscript must pin **one** final-numbers pass
   and cite that JSON, not the running notes.
5. **Scope-gate winner's-curse.** 70.3%@37.3% is in-sample on gate thresholds tuned to
   the same data; only the student model has shown CV.
6. **English-majority benchmark.** batch-03 is English-heavy; non-English gate recall
   is named as the deeper, unmeasured lever.
7. **Coverage denominators are inconsistent across the corpus of internal docs**
   (0.2% / 2.5% / 5.6% / **25.8% funnel** / **26.72% scoped** / ~38% / 39.7% —
   funnel-coverage and scoped-recall are distinct claim-types, both canonical per
   the reconciliation doc `2026-07-16-coverage-metric-canonicalization.md`); this
   paper reports **only** the classification-precision metrics above and defers all
   coverage claims to Paper C, which must pick one defined denominator per claim.
8. **The task-level series is small-n and single-rater.** n=14 real queries
   (±7pp/query); one temp-0 DeepSeek judge, no κ, with judge-application
   variance measured at ±1 level on identical structural facts; day-4
   attribution is confounded across three simultaneous serving changes (stated
   in the artifact); the time-shifted placebo (K3) has not run. The UI arm is
   one evaluator applying a frozen rubric — a structured instrument, not a
   multi-user study (the tech report's P7 gate remains open).
9. **The court calibration is single-team blind-checking, and the bar is
   unreached.** Five rounds plateaued at 7/10 against a ≥8/10 bar; the census's
   two judges agree at 98.4% but are agents operated by the same team. The
   certificate's 70.5% is a measured ceiling on what `entailed` currently
   guarantees at serving — cite it as such, never as "labels are verified."

---

## 7. What must exist before submission

- **[+EXP, light] Retro-apply the anchoring/blind control to the full N=660 headline.**
  Turn the crisis-only point-pair into a CI on the *headline* denominator so the
  "successor to 41.6%" is a real interval, not a cross-denominator point-pair.
- **[+EXP, blocked] BERTopic-proper external baseline (UMAP + c-TF-IDF).** Currently
  unrun (numba / Python 3.14 toolchain block). This is the missing external comparator
  that would isolate the schema's own contribution; state it as open, do not proxy it
  with the HDBSCAN-over-e5 sweep.
- **[+EXP] Held-out validation of the scope-gate thresholds** (not only the student) to
  remove the winner's-curse caveat on 70.3%@37.3%.
- **[data] A human-adjudicated gold subset** (even a few hundred rows) to convert at
  least one headline from panel-relative to human-anchored, and to bound the
  LLM-panel bias.
- **[data] A fresh, timestamped labeled window** for the first temporal hold-out
  (batch-03's signals are purged), lifting the in-window hedge on at least the
  theme-hint ablation and the reject-class agreement.
- **[housekeeping] Pin one final-numbers κ pass** for the ensemble base; restore/cite
  the exact JSON artifacts (`gold-kappa.json`, `anchoring-control.json`,
  `ablation-cis.json`); stop any "doc track CLOSED" language while the successor
  precision is still range-valued, in-window, and panel-relative.
- **[+EXP] Day-5+ of the gold series under an unchanged ensemble** — the cheap
  test that converts "persistence held once" (R8) into a structural claim, and
  the only way to allocate day-4's improvement among its three confounded causes.
- **[+EXP] The K3 time-shifted placebo and a second judge (κ) for the gold
  harness** — the two pre-registered instrument checks still open.
- **[+EXP] GB6 court-calibration round post-stamp-stabilization**, plus the
  blob-veto and PR-wire junk-gate composition fixes, then the census re-run —
  the enumerated path from a 70.5% certificate toward the 90% promotion bar.

---

### Provenance of every load-bearing number (for the fact-check pass)
- 41.6% / 78.6% / 81.1%, N=660, seed 20260527, 10000 resamples, κ 0.625 —
  `.../reports/llm-baseline/2026-06-02-comparison-atlas-vs-llm-n660.json`.
- theme-hint ablation (20.2% / 40.9% / 48.3% / +7.4pp [5.2,9.6]) —
  `docs/research/embedding-ablation/2026-07-01-gdelt-hint-ablation.md`.
- anchoring control (48.2% n=390 / 53.8% n=316; z=1.48 p≈0.14) —
  `docs/research/embedding-ablation/2026-07-01-crisis-only-precision-and-kappa.md` +
  `2026-07-01-anchoring-control.json`.
- scope gate 41%→70.3%@37.3% — Paper-1 skeleton R3 / M1 gate artifact (held-out CV
  pending).
- taxonomy ensemble (76%→96%, force-fit 30/46%, gold base 732, κ "substantial") —
  `docs/research/taxonomy-revision/2026-06-29-taxonomy-revision-methodology.md`.
- substrate geometry (AUC 0.985, 0.916/0.788, 4.4×; whitening recall 0.477/0.062/0.109)
  — Paper-1 skeleton §"e5 anisotropic compression" + `cluster_whiten_sweep.py` (2026-07-07).
- error composition (substring 0.6%) — `.../reports/llm-baseline/2026-06-02-rq1-error-composition.json`.
- gold series (14/7/21/29%; honesty 0.17/0.23/0.09/0.40; persistence 1/2 · 0/1 · 3/3;
  controls 6/6 ×4) — `docs/research/gold/2026-07-27-gold-query-eval.md`,
  `2026-07-28-gold-query-eval.md`, `2026-07-28-rerun-comparison.md`,
  `2026-07-31-gold-eval-day3-m2.md`, `2026-08-03-gold-eval-day4.md` (+ jsonl siblings).
- UI arm (14.3% / 71.4% / 0.83 / NAV-LOSS 20/20 / UI-BETTER ×14) —
  `docs/research/gold/2026-07-30-ui-eval-v2-run.md` + `rubric-v2-ui.md`.
- semantic-into-search NO (5/12 clustering, 3/12 synthesis, honesty floor 0.17→~0.50) —
  `docs/research/gold/2026-07-27-semantic-search-feasibility.md`.
- court calibration (GB1–GB5 3/10→7/10; blind spot 0/30; enforcement 66%;
  census 70.5% n=244 @98.4%; over-block 11.1%; decay 0/72) —
  `docs/research/label-court/2026-07-29-gb*-blind-check.md`,
  `2026-07-29-court-blindspot-audit.md`,
  `docs/research/recall-229/2026-08-03-tf3b-gate-c-census.md`.
- identity-gate whitening STOP (anchor gap −0.5471; cross-lang split) —
  `docs/research/recall-229/2026-07-28-whitened-identity-taus.md`.
- embedding bake-off v2 (e5large ≡ e5base; bge-m3 strongest on identity stats) —
  `docs/research/recall-229/2026-07-31-embedding-bakeoff-v2.md`.
