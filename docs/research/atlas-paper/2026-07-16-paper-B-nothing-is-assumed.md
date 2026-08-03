# Paper B — Nothing is assumed: measured refutations of intuitive narrative-signal proxies

**Status:** skeleton (2026-07-16; results integrated through 2026-08-03). Part of
the Atlas justification series
(reorg: `2026-07-16-papers-reorganization-justification-framing.md`). This paper
is a *justification layer*, not a superiority pitch: each section shows that an
intuitive shortcut, taken as obvious by practitioners, is measurably misleading,
and that the shipped design is therefore non-arbitrary. The "alternatives ruled
out" ARE the result.

**What changed in the 2026-08-03 integration.** The paper was drafted around four
refutations of ranking/enrichment proxies. Between 2026-07-22 and 2026-08-03 the
same discipline was applied to the **identity layer** (the machinery that decides
whether two clusters are the same story) under a stricter protocol — a
**pre-registered kill rule frozen before every run** — and produced five further
refutations plus one serving-layer refutation, each killed by its own gate. The
paper now has two result families: Part I (the ranking-proxy refutations, §3) and
Part II (the identity arc, §4). The methodological through-line — *the false side
is measured in the same pass as the recall side, and the kill threshold is written
down before the experiment runs* — is now the paper's largest single contribution
(§5).

**Target venue.** A measurement / methods venue rather than a systems-superiority
one: ICWSM (dataset & methods track), the *Journal of Computational Social
Science*, or a workshop on computational journalism / news measurement (e.g.
Computation + Journalism). The contribution is a set of falsifications of common
news-ranking and news-identity heuristics on a live global-media corpus, with
reproducible scripts — not a claim that Atlas outranks a named competitor.

---

## Abstract (target ~150 words; draft below is ~150)

News-intelligence systems lean on proxies that feel obviously correct: story
volume, syndication breadth, short-horizon acceleration, pre-computed theme
codes — and, at the identity layer, embedding cosine as a story-equality test.
We report ten read-only measurements on a live multilingual corpus (GDELT plus
~219 RSS feeds), each run under a pre-registered kill rule frozen before
execution. The ranking proxies fail as assumed: heat and volume are
rank-disjoint (Kendall-tau −0.198); syndication breadth cannot separate hard
news from filler; smoothed velocity anti-predicts future volume (Spearman
−0.477); GDELT theme-hints are net noise (removal +7.4pp, CI [5.2, 9.6]). The
identity measurements refute five successive remedies — whitening, evidence
overlap, LLM adjudication at volume, cap removal, pre-projection consolidation
— and name the real disease: fragments of one event do not share a nearest
topic (argmax dispersion). Percolation, not pairwise precision, binds merge
rules. Every negative justifies a shipped design or non-decision.

---

## 1. Thesis, in justification form

The organizing claim of Atlas's paper series is that everything the system shows
an analyst is *valid because it is backed by measured math, inference, and
experiment — and nothing is assumed, not even the choices not to act.* This paper
is the literal embodiment of that thesis.

For each heuristic we run the template:

- **Decision** — the concrete thing Atlas ships (or deliberately declines to
  ship).
- **Stakes** — why the obvious alternative is tempting and why picking wrong is
  not free.
- **Backing** — the measurement that makes the choice non-arbitrary (N, CI,
  script).
- **Alternative ruled out** — the naive proxy we measured and rejected. Here the
  rejection *is* the finding.
- **Honest limit** — what is not yet backed (window-only, no temporal hold-out,
  LLM-panel gold, single snapshot).

Part II adds a rule the first four refutations did not yet enforce and the
identity arc made mandatory: **the kill threshold is pre-registered** — written
into the plan or spec before the harness runs — so that when the number comes
back at 0.714 against a bar of 0.7, there is no room to move the goalposts
(first enforced on the attention-coverage-divergence kill,
`docs/research/silent-risk/2026-07-22-domain-placebo.md`; §4 preamble).

None of these results is a standalone paper. Individually each is "we measured
the obvious thing and it failed." Assembled, they are a citable statement about
news-signal measurement: the intuitive proxies practitioners reach for do not
track the quantity they are assumed to track, and measuring that — with the
false side in the same pass as the recall side — is the contribution. Good
science includes measuring the obvious thing and showing exactly why it fails.

A note carried into every methods and limitations section: **where a precision
number is cited, it means agreement with a 3-LLM consensus panel (Claude Sonnet
4.6 + GPT-4.1 + DeepSeek); n_rows_with_human_gold = 0.** The identity-arc
measurements are predominantly **label-free and mechanical** (graph components,
cosine distributions, country spans) and do not inherit that caveat; where they
use hand judgment (§4.3's witness families, §4.6's composition samples) the
judge is the operating author/agent, disclosed per-measurement.

---

## 2. Related work positioning

Engage the real literature; no strawmen.

- **GDELT / GDELT-GKG themes and Event Registry.** GDELT-GKG attaches a large
  controlled vocabulary of themes to each article; systems built on it (and on
  Event Registry's concept tagging) commonly use theme/concept overlap as a
  cheap candidate-generator for topic assignment. We do not dispute that theme
  codes carry signal on average; we measure the precision of the *theme-only*
  assignment path specifically, where idiomatic firing (e.g. the `KILL` theme on
  "killing it") is plausible, and report it against a lexicon-standalone
  ablation. Position: complementary measurement, not a rejection of GDELT.

- **BERTopic + c-TF-IDF and neural topic modeling.** BERTopic (embeddings ->
  UMAP -> HDBSCAN -> c-TF-IDF) is the natural external baseline for the discovery
  and labeling work this paper's engine sits on. We flag honestly that a
  BERTopic-proper baseline is **not yet run** (toolchain block: numba on Python
  3.14) — so we make no comparative claim against it; it is named as the missing
  external anchor.

- **Media Cloud** and computational-journalism measurement traditions frame
  "attention" as counts of stories/outlets. Our heat and syndication results are
  in direct dialogue with that framing: we test whether count-based attention
  tracks a composite anomaly signal, and whether syndication breadth is
  separable from filler.

- **LLM-as-annotator / LLM-as-judge evaluation.** A growing body treats a strong
  LLM (or a panel) as a scalable annotator, with active debate on circularity and
  bias. We adopt a 3-vendor consensus panel where labels are needed *and
  foreground its circularity as a first-class limitation* (§7). §4.2 adds an
  operational bound the literature rarely quantifies: an LLM judge that is
  accurate per-pair can still be **unaffordable at graph volume** — the
  adjudication band a merge gate generates was measured at 2.4×–1117× a realistic
  nightly call budget.

- **Entity resolution / record linkage and percolation.** §4.2's central lesson
  — that a merge rule applied to a fixpoint is a *graph*, whose binding
  constraint is connected-component growth rather than per-pair precision — is
  the transitive-closure hazard known in record-linkage literature, here
  measured live: a 1.4% pairwise false-admit rate produced a connected component
  spanning 96.2% of the snapshot.

- **Embedding anisotropy** (Mu & Viswanath, "all-but-the-top", 2018; Gao et al.
  on representation degeneration) motivates the whitening our sister paper (Paper
  C) uses on pairwise geometry. §4.1 contributes a *bound* on that line of work:
  in multilingual-e5, the top principal direction whitening removes carries the
  **cross-lingual alignment**, so mean/top-PC removal that cures monolingual
  scale compression destroys same-event similarity across languages.

- **HDBSCAN** (Campello, Moulavi, Sander) is the density clustering under the
  discovery engine; its noise-vs-purity behavior is the backdrop for why volume
  and velocity are the tempting shortcuts we test.

---

## 3. Part I — the ranking-proxy refutations

### 3.1 Heat is a composite, because volume is not a proxy for importance

- **Decision.** Country "heat" on the map is a 7-component composite
  (`z_velocity`, `surprise_kl`, `source_diversity`, `local_voice_ratio`,
  `polyphony`, `geo_confidence_mean`, `duplication_index`) — deliberately NOT
  story volume.
- **Stakes.** Volume rank is free, monotonic, and intuitive ("more stories =
  more important"). Shipping it produced the US-always-reddest artifact the
  composite was built to remove. If volume actually tracked the composite, the
  extra machinery would be unjustified.
- **Backing.** Over N=200 countries (24h, `/api/v2/heat/countries?limit=200`):
  **Kendall-tau(composite rank, volume rank) = -0.198** — not merely
  uncorrelated but mildly negative. Top-8-by-composite and top-8-by-volume
  overlap **0/8**. Per-component analysis identifies the mechanism:
  `surprise_kl` correlates +0.401 with the composite but **-0.558 with volume**
  (it rewards distributionally anomalous, disproportionately low-volume
  countries), and `source_diversity` (+0.486 with composite, +0.061 with volume)
  is the strongest volume-neutral driver.
- **Alternative ruled out.** Volume-rank heat. It shares none of its top-8 with
  the composite and is mildly anti-correlated; it is measurably not a proxy.
- **Honest limit.** One 24h snapshot; `polyphony` was constant (0.5) in-window so
  its correlation is undefined (harmless). Weights are v1, not learned — this
  measures the *served* blend's behavior, not an optimal one. No temporal
  hold-out (a multi-day tau would tighten it). The design only needs "not a
  volume proxy," which is shown; correctness-against-an-analyst is explicitly out
  of scope. Script currently a single live pull (`/heat/countries`), not a saved
  harness — wrap it if it stays load-bearing.

### 3.2 No syndication penalty, because reprint breadth cannot separate news from filler

- **Decision.** Thread ranking is `0.45·log-volume + 0.35·movement +
  0.20·coherence` and deliberately carries **no** `headline_diversity` /
  syndication penalty term.
- **Stakes.** It is tempting to demote heavily-syndicated items ("100 identical
  reprints = one wire story, not 100 stories"). A `headline_diversity =
  distinct_normalized_headlines / sample_signals` penalty is the obvious knob.
  The non-decision — choosing NOT to add the knob — must itself be backed, or it
  is an assumption.
- **Backing.** Syndication audit over 13/13 served threads (24h): "Iran attacks
  Bahrain"-class hard news scores diversity 1.0 (45 serving / 24 domains for
  Las Vegas Travel Guide; multiple hard-news threads at 1.0) and a genuinely
  syndicated wire story would score LOW on the same axis. The audit's own
  false-demote check makes the structural point: a high-reprint / high-domain
  hard-news dispatch is indistinguishable, on the diversity axis, from a
  high-reprint recipe. Illustrative pair carried in the reorg canon: "Iran
  attacks Bahrain" (116 reprints / 115 domains) vs a sausage-rolls recipe (92 /
  92) — structurally identical breadth. A diversity penalty would false-demote
  real news.
- **Alternative ruled out.** A `headline_diversity` ranking penalty. If it must
  exist at all, it must DAMP (input) rather than EXCLUDE (gate) — but the audit
  shows it does not cleanly separate the classes it is meant to, so it is not
  wired as a ranking term.
- **Honest limit.** 13-thread, 24h, single-snapshot audit over the served
  evidence sample; `headline_diversity` estimated on that sample, not the full
  member set. 0/13 threads flagged (diversity < 0.35) in-window means the
  pathology is rare here, not absent in general. The clean statement is "reprint
  breadth is not separable from value on this sample," not "syndication never
  matters."
- **A downstream postscript (2026-07-30).** The syndication *dedup* that does
  exist was itself measured broken for non-Latin scripts: `_norm_headline`
  deleted non-Latin characters before comparison, reducing a Cyrillic headline
  to its digits, so ru/uk/ar/fa syndication counting was silently poisoned
  (fixed `924174b2`; part of the script-blind bug family Paper C owns, cited
  here because it bounds what this section's diversity estimates could have
  seen in non-Latin coverage).

### 3.3 changed_10h stays the ordering source, because velocity does not lead volume

- **Decision.** Front-page thread ordering uses contemporaneous `changed_10h`.
  The smoothed Kalman `topic_movement` (velocity/surprise/trend) is a
  **display-only** chip, never a ranking input.
- **Stakes.** Wiring a smoothed velocity into ranking is attractive: it *looks*
  like a leading indicator and would let the front page "predict" rising stories.
  If it does not lead, ranking on it would over-rank topics about to cool.
- **Backing.** Read-only replay backtest over the durable `emergent_clusters`
  snapshot series (99 snapshots / 33.2 days, ~8h cadence; per-topic sliding point,
  Kalman estimated from PAST snapshots only, target = future log-volume growth;
  n = 786-879 points across 36-52 topics). Forward Spearman:

  | horizon | velocity -> future | surprise -> future | changed_10h -> future |
  |---|---|---|---|
  | 1 (~8h)  | **-0.477** [-0.53, -0.42] | +0.005 (ns) | -0.390 |
  | 2 (~16h) | -0.347 [-0.41, -0.29] | -0.038 (ns) | +0.025 (ns) |
  | 3 (~24h) | -0.224 [-0.29, -0.15] | -0.089 | +0.038 (ns) |

  Velocity is significantly *negatively* correlated with future growth at every
  horizon (mean reversion: spikes exhaust themselves); surprise is ~0; velocity
  is significantly worse than naive `changed_10h` at forward prediction. A
  definitional-artifact check rules out construction as the sole cause:
  `changed_10h` is built from the same trailing window yet comes out ~0 at
  h2/h3, while velocity stays -0.35/-0.22, so velocity's anti-prediction is a
  real property.
- **Alternative ruled out.** Ranking on Kalman velocity/surprise. It is not a
  leading indicator on this corpus; wiring it would degrade ordering. This is a
  clean falsification that *prevented a bad ranking change* before it shipped.
- **Honest limit.** 33 days of ~8h snapshots is a modest window; re-run as the
  series lengthens. A cleaner target (future vs a fixed per-topic baseline, not
  the trailing window) would sharpen magnitude, but the sign / no-lead
  conclusion is robust. The result is corpus- and cadence-specific: attention
  series are mean-reverting *at this snapshot cadence*; a genuine leading
  indicator would need a different observable (cross-source attention ratio,
  early-forum velocity), not smoothing of volume.

### 3.4 GDELT theme-hints removed, because the theme-only path is net noise

- **Decision.** Demote GDELT theme-hints from a hard candidate-generator to (at
  most) a weak confidence feature; assignment leans on the LLM-distilled lexicon
  + semantic recovery.
- **Stakes.** Theme-hints are assumed to *add* precision (four internal docs
  named an ablation as the gate before removal was allowed). Removing a
  precision contributor to simplify the engine would be reckless; keeping a noise
  source would be worse. Only a measurement decides.
- **Backing.** Threshold-independent gold decomposition on the canonical N=660
  3-vendor consensus benchmark (`gdelt_hint_ablation.py`, batch-03 gold):

  | engine | correct / usable | precision | Wilson 95% |
  |---|---|---|---|
  | baseline (with theme-hints) | 270 / 660 | **40.9%** | [37.2, 44.7] |
  | ablated (lexicon-standalone) | 235 / 487 | **48.3%** | [43.8, 52.7] |
  | theme-hint-dependent path | 35 / 173 | **20.2%** | [14.9, 26.8] |

  > *The static classifier's 40.9% (n=660 ablation denominator) and the 41.6%
  > headline (n=635 gate-scored subset) in Paper A are the same classifier over
  > different scoring populations — not a discrepancy.*

  The theme-only path is 20.2% correct — roughly half the baseline — and its
  Wilson interval [14.9, 26.8] does not overlap the baseline [37.2, 44.7].
  Removal delta **+7.4pp, bootstrap 95% CI [5.2, 9.6] excludes 0**. Recall cost =
  35 correct assignments (13.0% of corrects); a Stage-2 semantic recovery curve
  recovers 86-100% of those 35 at a moderate cosine cut (0.72-0.75) and little at
  a strict cut (0.80+). This is the cleanest experiment in Part I.
- **Alternative ruled out.** Keeping theme-hint overlap as a hard
  candidate-generator. It is a net noise source on the canonical benchmark, not a
  precision contributor.
- **Honest limit.** One benchmark, English-majority (batch-03 N=660); a
  non-English theme-hint ablation is a separate, unrun row. The ablated engine
  assumes the lexicon becomes a standalone candidate-generator (an implementation
  follow-up the semantic path already approximates). Stage-2 recovery is
  threshold-sensitive — quote the curve, not a single number. No temporal
  hold-out on the ablation itself. And, as everywhere: precision = 3-LLM-panel
  agreement, zero human gold.

---

## 4. Part II — the identity arc: five pre-registered refutations, one named disease

**Context, and why this belongs in this paper.** Atlas's task-level eval (the
gold analyst-query set, Paper A §"the primary metric") measured an answer rate of
7–14% with a loud failure signature: stories present in the corpus were served as
the wrong thread, and an answer that existed on day N vanished on day N+1 while
the story stayed in-corpus (`docs/research/gold/2026-07-28-rerun-comparison.md`).
The diagnosis (`docs/research/recall-229/2026-07-28-identity-layer-raw-cosine.md`)
located the mechanism at the identity layer: topic identity is decided by raw-e5
cosine gates (`MATCH 0.88`, `ANCHOR 0.93`, `MERGE 0.90`) that sit **inside the
overlap band** of same-story and different-story distributions — one event
shatters into 8–33 clusters that never reconverge, while stale identities absorb
unrelated stories (a New Zealand sexual-assault anchor absorbed a Bolivian
military-recruitment cluster at cosine 0.938, above the 0.93 gate).

Five successive remedies were then proposed — each intuitive, each with prior
support — and each was measured under a **pre-registered kill rule frozen before
the run**. All five died by their own gates. What survived is a *named disease*,
an instrument suite, and a set of non-decisions that are now backed rather than
assumed.

### 4.1 Whitening at the identity layer — killed by its own tail audit

- **Proposed remedy.** All-but-top-k whitening rescued pairwise geometry
  elsewhere (Paper C); re-fit the three identity gates in whitened space.
- **Pre-registered kill.** For each gate, STOP if `p5(true) ≤ p95(false)` in
  whitened space (frozen before the run; no threshold tuned after any downstream
  outcome).
- **Result: STOP** (`docs/research/recall-229/2026-07-28-whitened-identity-taus.md`).
  The `anchor` gate's whitened gap is **−0.5471** and `merge`'s **−0.1173**; only
  `match` reads PROCEED, and that is an artifact (its TRUE pairs are
  engine-selected). Whitening's *ranking* separation is strong (AUC 0.9995 /
  0.7264 / 0.9628 across the gates, better than raw everywhere) — **but a gate is
  a hard cut, and at the tails the populations are interleaved**: 22 same-day,
  same-country clusters of ONE event (the Berlin Pride attack) read whitened
  median 0.390, min −0.060, while unambiguously different stories read 0.89–0.92.
- **The bound on Mu & Viswanath.** The language-split analysis (§6 of the
  artifact) shows why: whitened cosine penalizes cross-language same-event pairs
  far below same-language ones (anchor gate, true pairs: same-lang p50 0.677 vs
  cross-lang p50 0.437) — the dominant direction whitening removes carries
  **cross-lingual alignment** in multilingual-e5. Removing it separates pairs the
  engine never confused and destroys exactly the same-event-across-languages
  similarity a global monitor needs. The measured penalty is a lower bound (the
  artifact's own limitation note).
- **Design consequence.** Whitening stays a *consumer-by-consumer* lever
  (pairwise displays, dossier edges) and is **not** the identity substrate. The
  non-decision is now backed at the identity layer specifically, extending Paper
  A §3.6 / Paper C's cluster-level walk-back with a third boundary condition.

### 4.2 Evidence-overlap merging — killed by graph density, not pairwise precision

- **Proposed remedy.** Same-event fragments should share surface evidence (rare
  entities, URLs, headlines); merge on `cosine AND shared-evidence` instead of
  the label-dependent shipping rule (which a five-night label blackout had just
  disabled entirely).
- **Pre-registered kill.** K2: the largest connected component of the
  whole-snapshot merge graph must stay ≤ **2%** of the snapshot, AND ≥2 of 3 core
  witness families must reconverge to ≤3 components. A three-rung lane-escalation
  ladder (entities → URL/locators → headlines) was frozen in the spec with an
  explicit closure sentence if all rungs fail.
- **Result: NO-GO — 0 of 140 grid points satisfy both sides; all three lanes fail**
  (`docs/research/recall-229/2026-07-29-witness-reconvergence.md`). The spec's own
  seed candidate (`cos ≥ 0.86 AND ent ≥ 1`, supported by a 406-pair sample at
  2.7% false) reproduced its pairwise numbers **and produced a connected
  component of 96.2% of the snapshot — missing the K2 bar by 48×.**
- **The lesson that renames the problem.** `merge_duplicates` runs to a fixpoint,
  so a merge rule is not a set of decisions — it is a **graph**, and the binding
  constraint is percolation. A 1.4% false-pair rate over 2.06M candidate pairs is
  tens of thousands of edges. **Pairwise precision is the wrong instrument for a
  transitive rule**; the spec's pre-measurement scored 406 pairs and never built
  the graph, which is exactly why the kill rule required both in one table.
- **The rehabilitation in the same pass.** The SHIPPING rule
  (`cos ≥ 0.90 AND label ≥ 0.80`) — the rule the design set out to replace —
  satisfies K2 at **1.13%**, admits **0/1200** mechanically-false pairs, and
  halves witness fragmentation where labels exist. Its catastrophe was the
  **label blackout** (`emergent_clusters.label` 100% NULL 07-23→07-27 under a
  provider-credit outage), not its discrimination. The refutation therefore
  *re-attributed* the incident: the fix is provider redundancy and blackout
  alerting, not a new merge rule.
- **The judge corollary (refutation 2b).** The fallback idea — adjudicate the
  borderline band with an LLM "one story or two?" judge — was costed in the same
  artifact (§M6): the band is **2.4×–1117× the 150-call/night budget** depending
  on the operating point. Per-pair-accurate and unaffordable at graph volume:
  **dead at volume**, without needing an accuracy measurement at all.

### 4.3 Removing the one-absorption-per-night cap — killed 3 orders of magnitude over its bar, and the disease gets its name

- **Proposed remedy.** `process_snapshot`'s `used_t` set caps a topic at one
  absorbed cluster per night; the diagnosis proposed dropping it so an event's
  N fragments can consolidate onto one topic.
- **Pre-registered kill.** Zero tolerance on a "false absorption" signature
  (one topic absorbing ≥2 clusters/night spanning ≥3 countries or with
  incompatible labels) — baseline produces 0 by construction.
- **Result: NO-GO by three orders of magnitude**
  (`docs/research/recall-229/2026-07-30-used-t-simulation.md`, 12-night replay,
  single-night fidelity vs prod 93.8%). The variant produced **2,247** flagged
  false absorptions (1,513 on fully-labelled nights); its worst single night had
  *Valencia Building Collapse* absorb **41 clusters across 12 countries**. It
  deleted 55.8% of the active serving population to buy a 35% fragmentation
  reduction on one witness family, and never approached the recall bar.
- **The decisive negative finding — argmax dispersion, named.** For 43 of 54
  Berlin-Pride fragments, the family's own consolidation target is **not among
  the fragment's twelve nearest topics at all.** The fragments of one event do
  not compete for the same topic — each independently picks a *different* stale
  identity. `used_t` was never the binding constraint; **the binding constraint
  is that raw-e5 cosine does not put a family's fragments near the same topic.**
  This is the disease every subsequent measurement is scored against, and it
  comes with an instrument: *top-12 agreement per family* (11/54 for Berlin
  Pride at measurement time).
- **Three secondary refutations from the same run**, each a control that future
  work must not reuse naively: (a) the 0.93 anchor guard is ~strictly a
  sub-condition of the 0.88 match gate (317 counter-examples in 18.6M pairs) —
  the two gates are not independent controls; (b) the over-merge detector **goes
  blind exactly where damage concentrates** (at 10+ absorbed clusters its
  gap_ratio median falls to 0.818 < its own KEEP threshold — a 41-cluster blob
  is a smear, not bimodal), so its demote count must never be the purity control
  for a fusion-increasing change; (c) the `used_t` invariant was already violated
  633× in production by a different writer — the invariant was a property of the
  projection, not of the table.

### 4.4 Cluster-level consolidation — succeeds at recall, killed by identity ("coverage measures concentration, not correctness")

- **Proposed remedy.** Sidestep argmax dispersion: unify fragments with each
  other *inside* the snapshot using the one K2-safe rule (§4.2's shipping rule),
  so a super-cluster makes ONE pick against the topic pool.
- **Pre-registered kills.** K2 on the cluster graph (>2% component) and a
  zero-tolerance multi-country/incompatible-label fusion signature.
- **Result: NO-GO — both kills fired, and a third, unanticipated finding decides
  it** (`docs/research/recall-229/2026-07-30-cluster-consolidation.md`, 15
  labelled snapshots). The recall side works spectacularly: Berlin Pride 23
  fragments → 3, Paris knife attack 9 → 1, story coverage 0.109 → 0.931 and
  0.174 → 1.000, at a serving-population cost of 3.1% (vs `used_t`-removal's
  55.8%). **But in 4 of 6 witness families the single topic the event
  concentrates onto is the wrong identity** — Kyiv-being-struck lands 75.5% onto
  "Drone Attacks on Moscow"; the Paris knife attack lands 100% onto a Monaco
  explosion topic. Consolidation does not create the mis-attachment; **it makes
  it total.** A perfectly-formed question still gets the wrong answer from a
  raw-e5 argmax. Coverage and correctness had to be separated before the run
  could be read at all — the identity-landing column is now a mandatory metric
  for any consolidation proposal.
- **The fusion kill is a labeller artifact, not geometry.** The one true fusion
  (Ukraine + Iran + Yemen wars in one component) was bridged by the label
  template `"<X> Conflict Escalation"` — SequenceMatcher scores the *template*
  (0.852), not the story. The intuitive repair (require a shared distinctive
  token) was measured and **refuted**: a large same-event family inflates its own
  tokens' document frequency, so the cut kills Berlin Pride along with the
  three-war fusion. The counter-intuitive repair (require a shared country) was
  measured and works (fusion count → 0, K2 → 14/15, five of six families
  untouched) — recorded as a **lead for its own pre-registered run, not a GO**,
  because it was constructed after seeing the failure, and it structurally
  cannot merge genuinely bilateral stories (the Caspian family degrades 4 → 5).

### 4.5 A better embedding space — NO-GO: e5 is not the bottleneck, and task-dependence is total

- **Proposed remedy.** If raw-e5 geometry is the disease, swap the encoder:
  e5-large, bge-m3, OpenAI text-embedding-3-{small,large}, scored on the three
  instruments the arc had produced (pair-separation per gate; argmax dispersion;
  a K2-safe cos-only operating point), with win margins frozen before scoring.
- **Result: NO-GO**
  (`docs/research/recall-229/2026-07-31-embedding-bakeoff-v2.md`; 43,138
  archive-recovered headlines re-embedded per space, identical estimator per
  space). Three findings with different signs, reported separately rather than
  averaged:
  1. **Pair separation IS fixable by a better space** — the un-separable `merge`
     gate (e5-base gap −0.0336) becomes separable in bge-m3 (+0.0636) and both
     OpenAI spaces (best +0.1149); the engine-independent anchor slice likewise
     (−0.0524 → +0.2171, oai-large).
  2. **No space fixes argmax dispersion** — the frozen top-12 metric moves 0.0714
     → at best 0.0857 (1.2×) against a 2× bar. Fragments of one event still do
     not share a nearest topic in any space measured. (The target-free
     concentration statistic moves more — 0.140 → 0.287 on bge-m3 — reported as
     the honest residual, not a pass.)
  3. **No space makes cos-only merging safe** (no K2-safe cos-only point
     anywhere), so the label conjunct stays load-bearing and merging stays
     blackout-exposed regardless of encoder.
- **The task-dependence result worth citing on its own.** Scaling the same
  family buys nothing — e5-large ≡ e5-base to three decimals on every
  instrument. Changing the family does: **bge-m3, the model that finished LAST
  in the 2026-07-04 assignment-gate bake-off, is the strongest space on the
  identity-disease statistics** — while OpenAI-large, the assignment-gate
  winner, wins pair separation. Encoder rankings do not transfer across tasks
  even inside one product's pipeline; every consumer must run its own bake-off.
- **Design consequence.** The identity layer, not the embedding space, remains
  the lever. OpenAI spaces are a *gates* lever (pair separation at $0.09–0.57
  /day), never an identity substrate.

### 4.6 Serving-side corollary — reviving retired topics without re-vetting, killed by composition

- **Proposed remedy.** The lifecycle-clock diagnosis
  (`docs/research/recall-229/2026-07-29-threading-floor-diagnosis.md`; Paper C
  §serving-coverage owns the full result) showed 1,353 retired topics passing
  every quality bar, killed by an operational aging defect. The intuitive fix —
  correct the clock and revive `retired→active` directly — passed its mechanical
  gate cleanly (TF-1: 0 invariant violations on 6,649 topics) and lit up dark
  country doors live.
- **Pre-registered kill.** Composition: ≥90% of a random 40-topic sample of the
  newly-active must be real stories, or KILL.
- **Result: KILL — 37.5% strict (67.5% under the most charitable reading), both
  far below 90%**
  (`docs/research/recall-229/2026-07-30-tickv2-tf1-tf2-verdict.md`). The clock
  was right and the *exit gate* was wrong: mass-reviving a field that carries
  two known diseases (labels frozen at creation + argmax-dispersion blobs)
  serves those diseases in mass. The flag was reverted and all 1,026 state
  changes surgically restored to baseline the same day.
- **The gated successor, measured to census depth.** TF-3b (revive to
  *candidate*; promotion requires the label court's `entailed` certificate)
  shipped next day and was measured as a **full census of all 244
  court-certified promotions with two independent judges per topic (inter-judge
  agreement 98.4%)**: strict-real composition **70.5%** — a **+33pp** improvement
  over ungated revival that still fails the 90% bar, with the deficit fully
  attributed to the certificate's own precision (certified blobs, certified
  PR-wire junk, judge mismatch), not to post-promotion decay (0/72 failures
  decayed after certification)
  (`docs/research/recall-229/2026-08-03-tf3b-gate-c-census.md`). The refutation
  chain thus ends in a *quantified* design: coverage recovery is court-gated,
  the certificate's serving-precision is a measured ~70%, and the remaining
  levers are enumerated per failure class.

### 4.7 A sixth refutation from the same season, briefly: attention-coverage divergence dies by placebo

For completeness of the "nothing is assumed" record: the silent-risk /
attention-coverage-divergence program (does public attention diverge from press
coverage in a way that flags under-covered stories?) was killed on 2026-07-22 by
its own pre-registered threshold — divergence computed against *week-old*
coverage correlates ρ=0.714 with divergence against real coverage (kill bar 0.7,
written before the run), and a placebo scoring of trend keywords against press
from before they trended produced 42.7–59.4% "silent" rates
(`docs/research/silent-risk/2026-07-22-domain-placebo.md`,
`…-silent-risk-source-measurement.md`). The lexical `coverage_count` is a
match-rate, not a coverage measurement. This kill predates the identity arc and
established the pre-registration discipline the arc then enforced throughout.

---

## 5. The method is the largest result

Across Parts I and II the same protocol was applied ten times, and its rules are
now backed by cases where each one was load-bearing:

1. **Pre-register the kill threshold before the run.** First enforced on the
   silent-risk placebo (ρ bar 0.7, measured 0.714 — no room to move goalposts);
   held through all five identity kills. Two kills (§4.4's K2 firings on small
   snapshots) were honored even where post-hoc inspection suggested the metric's
   units, not a real fusion, had tripped them — the observation is recorded, the
   verdict stands.
2. **Measure the false side in the same pass as the recall side.** §4.2's single
   table (witness reconvergence × graph density × false admission) is the
   template; the seed candidate died only because both sides were in one table.
3. **Graph density ≠ pairwise precision.** A transitive rule must be evaluated
   as a graph (percolation), never by sampling pairs.
4. **Detectors go blind exactly where damage concentrates — pick controls that
   stay sighted.** The over-merge detector's 2-means gap collapses on 10+
   fusions (§4.3); the country-span signature stayed sighted and became the
   standing control.
5. **Coverage measures concentration, not correctness.** §4.4: recall metrics
   must be paired with an identity-landing metric or they reward black holes.
6. **Measure twice; walk back the tempting positive.** The whitening story
   (Paper A §3.6, Paper C Table 3, §4.1 here) is now a three-stage walk-back —
   pair cure real, cluster-recall crossing not reproducible, identity gates
   STOP — each stage its own measurement.
7. **A stats-view zero is not proof** (the 2026-07-27 index-audit lesson,
   recorded in the reliability sweep): observational instruments carry their own
   blind spots and must be checked against the real query before acting.

---

## 6. Methods

- **Data.** Live global-media corpus: GDELT plus ~219 RSS feeds across 126
  countries and 31 languages (English 96.9% of language-known at baseline). Heat:
  200-country 24h snapshot. Syndication: 13 served threads, 24h. Movement:
  `emergent_clusters` snapshot series, 99 snapshots / 33.2 days. Theme-hint
  ablation: N=660 consensus-gold benchmark (batch-03). Identity arc: the live
  `emergent_clusters` / `dynamic_topics` field — 21-day pair collections (§4.1:
  31,636 clusters), whole-snapshot merge graphs (§4.2: 2,032 clusters / 2.06M
  pairs), 12-night lifecycle replays validated at 93.8% single-night fidelity
  against production assignments (§4.3, §4.4), and a 43,138-headline
  archive-recovered re-embedding corpus (§4.5).
- **Ground truth in Part II is predominantly mechanical and label-free**:
  same-event witness families constructed by frozen rules (same-snapshot
  near-identical labels; every membership verified against its own receipt
  headlines after the label↔evidence divergence finding), mechanically-false
  pairs (disjoint countries AND dissimilar same-script labels — conservative by
  construction: errors raise the false side and can only hurt a GO), graph
  components, country spans. Where hand judgment enters (TF-2's 40-topic sample;
  the gate-(c) census's 244×2 judgments, inter-judge 98.4%), the judges are the
  operating author/agents and are disclosed as such — **no independent human
  panel exists anywhere in this paper.**
- **Labels / gold (Part I).** Precision = **agreement with a 3-LLM consensus
  panel** (Claude Sonnet 4.6, GPT-4.1, DeepSeek). **n_rows_with_human_gold = 0.**
  Panel inter-annotator agreement Fleiss kappa = 0.625. The panel is a
  calibration reference; the zero-shot / few-shot LLM figures (78.6% / 81.1% on
  the same key, static Atlas classifier 41.6%) are reported as calibration
  points, not as a contest.
- **Statistics conventions.**
  - Binomial precision intervals: **Wilson score** 95%.
  - Deltas and rank statistics: **stratified bootstrap** (seed 20260527, 10000
    resamples for the N=660 benchmark; 5000 for the ablation slice; fixed
    bootstrap seeds for the movement backtest). The benchmark recomputes to the
    decimal under this seed.
  - Rank association: **Kendall-tau** (heat vs volume) and **Spearman**
    (movement, paired bootstrap CI).
  - Panel agreement: **Fleiss kappa** (3 raters); pairwise **Cohen kappa** where
    a 2-way comparison is needed; percent agreement for 2-judge census work
    (98.4%, §4.6).
  - Identity-arc gates: percentile-gap rules (`p5(true) − p95(false)`),
    connected-component shares (K2 ≤ 2%), and zero-tolerance signature counts —
    each frozen in a spec or plan before its run.
  - "ns" marks CIs that include 0.
- **Reproducibility.** Part I scripts: `gdelt_hint_ablation.py` (+ JSON),
  `backtest_movement_leading.py` (+ `2026-07-04-h{1,2,3}.json`), the syndication
  audit (spec §4), the heat pull (`/api/v2/heat/countries`, flagged for
  harness-wrapping). Part II harnesses (all read-only,
  `SET default_transaction_read_only = on`):
  `measure_identity_whitening.py`, `measure_evidence_fingerprint.py`,
  `simulate_used_t_removal.py`, `measure_cluster_consolidation.py`,
  `measure_embedding_bakeoff.py`, each with a machine-readable JSON beside its
  markdown artifact in `docs/research/recall-229/`.

---

## 7. Results (real-numbers summary)

| # | Intuitive proxy / remedy | Verdict | Key statistic | N / scope | Design consequence |
|---|---|---|---|---|---|
| 1 | volume == importance | **No** | Kendall-tau -0.198; top-8 overlap 0/8 | 200 countries, 24h | heat is a 7-component composite |
| 2 | syndication breadth == filler | **Not separable** | hard news 1.0 vs filler 1.0 diversity; 0/13 flagged | 13 threads, 24h | no `headline_diversity` penalty |
| 3 | velocity leads volume | **No (leads negatively)** | forward Spearman -0.477 [-0.53,-0.42] @h1 | 786-879 pts, 33.2d | `changed_10h` orders; Kalman display-only |
| 4 | theme-hints add precision | **No (net noise)** | 20.2% [14.9,26.8] vs 40.9%; removal +7.4pp [5.2,9.6] | 660 gold | theme-hints demoted/removed |
| 5 | whiten the identity gates | **STOP** | anchor gap −0.5471 whitened; cross-lang true pairs p50 0.437 vs same-lang 0.677 | 21d, 31,636 clusters | whitening never a gate; per-consumer only |
| 6 | merge on shared evidence | **NO-GO (percolation)** | 1.4% pairwise false ⇒ 96.2% component; K2 bar 2% missed 48×; 0/140 points pass | 2,032 clusters / 2.06M pairs | shipping `cos∧label` rule kept; blackout re-attributed to provider redundancy |
| 6b | LLM judge adjudicates the merge band | **Dead at volume** | band = 2.4×–1117× the 150-call/night cap | same graph | no judge-in-the-merge-loop |
| 7 | drop the `used_t` absorption cap | **NO-GO (×1000 over bar)** | 2,247 false absorptions vs 0; −55.8% actives; **43/54 fragments lack the target in top-12** | 12-night replay, 93.8% fidelity | argmax dispersion named; top-12/family instrument |
| 8 | consolidate clusters pre-projection | **NO-GO (identity)** | recall 0.109→0.931 but wrong identity 4/6 families; template fusion via label sim 0.852 | 15 snapshots | identity-landing metric mandatory; shared-country conjunct = pre-registered lead |
| 9 | a better embedding space | **NO-GO** | top-12 rate 0.0714→0.0857 (bar 2×); e5-large ≡ e5-base; gate-bake-off loser bge-m3 strongest here | 43,138 headlines, 5 spaces | identity layer, not encoder, is the lever; per-task bake-offs |
| 10 | revive retired topics directly | **KILL (composition)** | 37.5% real vs 90% bar; gated successor 70.5% (+33pp), census n=244, inter-judge 98.4% | live prod, reverted same day | revival→candidate + court certificate; certificate precision now a measured quantity |

Calibration reference (shared key, same benchmark, Part I): static Atlas
classifier 41.6% [37.8, 45.5]; LLM zero-shot 78.6% [75.3, 81.7]; few-shot 81.1%
[77.7, 84.0]; panel Fleiss kappa 0.625; n_rows_with_human_gold = 0.

---

## 8. Limitations

1. **LLM-panel gold, not human gold (Part I, stated first).** Precision is
   agreement with a 3-LLM consensus panel; **zero rows are human-adjudicated.**
   This is a known circularity in LLM-as-annotator evaluation: the classifier and
   the panel may share blind spots, and the panel's own agreement is moderate
   (Fleiss kappa 0.625). The refutations that do NOT depend on this gold — heat
   (rank correlation of two engine outputs), movement (forward correlation of
   observed volume), and the entire identity arc (mechanical constructions) —
   are the most robust; the theme-hint result inherits the gold caveat directly
   and the syndication result inherits it through thread labels.
2. **Hand judgment in Part II is single-team.** Witness-family membership, TF-2
   composition, and the gate-(c) census verdicts were judged by the operating
   author/agents (census: two independent agent judges, 98.4% agreement, plus a
   tiebreaker) — disclosed, but not an external panel. The mechanical FALSE
   constructions are deliberately conservative (they can only shrink evidence
   for a GO, never manufacture it — each artifact carries the direction-of-error
   note).
3. **No temporal hold-out in Part I; short windows in Part II.** Part I is
   in-window (single-snapshot heat/syndication; 33-day movement replay; one
   benchmark vintage). Part II's identity measurements span 12–21 days with one
   structural gap: a five-night label blackout (07-23→07-27) sits inside every
   replay window, is handled explicitly per-artifact (blackout nights are
   faithful for label-free questions, void for label-dependent ones), and is
   itself a finding (§4.2's re-attribution). The §4.6 census covers one weekend
   cohort.
4. **Witness-family sample sizes are small** (3 eligible gate families in the
   sibling-finder measurement; 6–7 families in the replays; 50 hand-judged
   neighbor rows). They are the pre-registered sizes, and the margins (43/54;
   2,247 vs 0; 48×) dwarf them — but per-family conclusions are not
   generalizable point estimates.
5. **Missing external baseline.** No BERTopic-proper (UMAP + c-TF-IDF) run exists
   (numba / Python 3.14 toolchain block), so none of these refutations is
   positioned against a standard external topic model. This is the named open gap
   that would isolate the schema's own contribution.
6. **Coverage denominators are not chained.** Where coverage is mentioned, one
   defined metric is named per claim (per
   `2026-07-16-coverage-metric-canonicalization.md`); the paper does not multiply
   inconsistently-defined coverage figures, and does not use the "54x more
   narratives" framing.

---

## 9. What must exist before submission

- **Wrap the heat pull in a reproducible harness** (currently one live
  `/heat/countries` snapshot) and re-run tau across multiple days to report a
  multi-day interval instead of a single-snapshot point.
- **Persist the syndication audit as a saved artifact** with a fixed sample and
  its false-demote check, over more than 13 threads / more than one snapshot, so
  the "not separable" claim rests on a distribution, not one window.
- **Lengthen the movement backtest** as the snapshot series grows, and add the
  fixed-per-topic-baseline target variant to sharpen magnitudes (sign already
  robust).
- **Add a non-English theme-hint ablation row** (batch-03 is English-majority),
  the deeper lever named in the source doc.
- **Run the BERTopic-proper external baseline** once the numba/py3.14 toolchain
  unblocks, to anchor the results against a standard topic model.
- **Run the shared-country consolidation conjunct as its own pre-registered
  experiment** (§4.4's lead) — the one identity remedy the arc left alive, and
  the cleanest test of whether the method's leads convert.
- **Re-run the §4.5 bake-off instruments after any identity-layer change** — the
  argmax-dispersion instrument (top-12 agreement per family) is the disease
  tracker; a healed identity layer should move it before anything else does.
- **Keep the LLM-panel-gold disclosure and the "calibration reference, not
  opponent" framing in every methods and results caption** — this is the framing
  that makes the series defensible.
- **Confirm every number against its live artifact at submission time**; mark any
  figure without a backing JSON/script as `[PLACEHOLDER]` until it has one.
