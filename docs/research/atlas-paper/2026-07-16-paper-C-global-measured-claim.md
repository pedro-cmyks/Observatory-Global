# Paper C — Making "global" a measured claim: voice ownership and open-set coverage

**Status:** skeleton (justification-framing pass, 2026-07-16; results integrated
through 2026-08-03)
**Series role:** Paper C of the 3-paper justified core (A = evidence-role
benchmark + methodology; B = measured refutations of intuitive proxies; **C =
this**). Reorg rationale: `2026-07-16-papers-reorganization-justification-framing.md`.
**Absorbs:** old P2 (voice / ownership honesty instrument) + old P8-reframed
(scoped-per-country discovery + the whitening walk-back).

**What changed in the 2026-08-03 integration.** "Global is a measured claim" now
cuts *inward* as well as outward, and the paper gains two decisions and one
sequel. (Decision 3) The instrument's own **country axis was audited and found
corrupted since inception** — a FIPS→ISO translation defect that filed whole
countries under other countries (Lebanon served as Lesotho) — measured, healed
in hot and historical stores, and converted into a versioned correction layer;
every per-country claim in this paper now carries that provenance boundary.
(Decision 4) A **script-blind bug family** in the text heuristics (word-count
title validation, flat character floors, Latin-only normalization) was measured
to structurally exclude CJK and non-Latin coverage at capture, clustering and
dedup time — the monoculture was not only in the feed, it was in the code's
assumptions. And the discovery sequel: scoped partitioning recovered *formation*
coverage, but **serving-level** global coverage was then measured at 30 of 168
clustered countries — a floor set by the lifecycle clock, not by data volume —
and the fix is itself a justified, gated design (per-country clock;
revive-to-candidate with a court certificate).

> **Framing contract (read before editing).** This paper does not argue Atlas is
> "more diverse" or "better at discovery" than any named system. It argues two
> *justified design decisions*: (1) score voice by **ownership**, not language;
> (2) discover topics by **scoped-per-country partitioning**, not a single global
> pass. Each is justified because *we measured the intuitive shortcut everyone
> assumes and found it false or curable*. The negatives are the contribution.

---

## Title / target venue

**Working title:** *"Making 'global' a measured claim: an ownership-based voice
instrument and a scoped-partition remedy for open-set narrative discovery."*

**Target venue (candidates, honest fit):**
- **ICWSM** or **The Web Conference (WWW) — Journalism/News track**: the voice
  instrument (who-speaks vs who-is-spoken-about, ownership-scored) is a media-
  ecosystem measurement contribution that fits ICWSM's computational-journalism
  scope.
- **Secondary:** a computational-social-science / measurement venue for the
  diversity-instrument half; the discovery/clustering half is a systems-measurement
  contribution suited to the same venue's methods track.
- **Not** a VIS/CHI submission — no analyst user study is in scope here (that is
  the deferred P7 report).

---

## Abstract (≤150 words)

"Global media coverage" is usually asserted from outlet or volume counts. We
argue it must be *measured* — including against the measuring instrument itself.
Voice diversity scored by *language* miscounts foreign coverage as a country's
own voice; our instrument separates who-speaks from who-is-spoken-about and
scores self-voice by outlet **ownership** (English 96.9% of language-known; Iran
self-voice 1.4%; origin voice-entropy 0.71 over 89 countries). Open-set
discovery under one global clustering pass assigns 4.94% of signals;
**scoped-per-country partitioning lifts it to 26.72%** — a global-pass artifact,
not a short-text ceiling. We then turn the audit inward: the country axis itself
was corrupted since inception (a FIPS→ISO defect served Lebanon as Lesotho;
healed, with a 22,472-row historical remap), script-blind text heuristics
silently discarded CJK coverage (~33k headlines/week recovered at the parser),
and served coverage reached only 30 of 168 clustered countries — a lifecycle
artifact, measured and fixed under a pre-registered composition gate. We also
report the whitening self-retraction. "Global" holds only as far as each
instrument has been audited.

---

## 1. Thesis (in justification form)

Two claims that Atlas surfaces to an analyst are load-bearing and could be
arbitrary:

- **"This country is / is not covered in its own voice."**
- **"These are the narratives present in the feed"** (the topic set the analyst
  browses).

Both are only meaningful if the underlying instrument is not measuring an
artifact. This paper justifies each by measuring the tempting alternative and
showing it misleads:

1. **Voice.** The obvious diversity metric — language mix, or raw outlet count —
   launders perspective: it counts English-language foreign coverage of Iran as
   diversity and cannot tell foreign coverage from domestic. We therefore score
   voice by **ownership** (origin country of the outlet), separated from the
   subject country. This turns "global" from an assertion into a reproducible
   number, and exposes the monoculture rather than hiding it. This is an
   **honesty instrument**, not a predictiveness claim (predictive usefulness of
   the composite is explicit future work, §6).

2. **Open-set discovery.** The obvious reading of a low topic-assignment rate is
   "short-text news has an intrinsic recall ceiling." We measured that this is a
   property of the *global* clustering pass, not of the data: partitioning the
   space per country dissolves the ceiling (4.94% → 26.72%). And — the
   measure-twice self-retraction that is the paper's methodological centerpiece —
   we tested a second candidate remedy (embedding whitening) that a single early
   sample made look decisive, ran it three times, and found it does **not** cross
   the cluster-level cliff. We report the walk-back in full because a
   justification paper must show what it ruled out, including its own earlier
   over-read.

Since the 07-16 draft, a third claim-family joined the thesis: **the instrument
is only as global as its own inputs, and those inputs must be audited, not
assumed.** Three audits (Decisions 3–5) each found the "global" claim silently
bounded by an internal defect — a country-code translation layer, a family of
English-normative text heuristics, and a lifecycle clock that structurally
excluded small countries from serving. Each was measured first, fixed second,
and each fix carries its own verification. A diversity instrument that does not
audit its own pipeline measures its pipeline's biases and calls them the world.

Nothing here is pitched as beating a competitor. Where an external baseline is
run (§3.2, BERTopic's HDBSCAN core), it is reported faithfully, including where
a flat baseline matches Atlas on a metric.

---

## 2. Related work positioning (engage the real literature, no strawman)

- **GDELT / GDELT-GKG themes, EventRegistry, Media Cloud.** These are the
  standard global-news event/coverage infrastructures. GDELT provides an English-
  dominated firehose with a fixed GKG theme taxonomy; Media Cloud and
  EventRegistry aggregate multilingual outlets. Our contribution is *not* a new
  aggregator. It is a **measurement layer on top of aggregation**: whose voice is
  actually present, scored by ownership. We position against the implicit
  assumption in coverage dashboards that outlet/volume presence equals voice
  diversity — an assumption we make falsifiable and show to be false at baseline
  (English 96.9% of language-known). GDELT is *our own* upstream, so this
  critique holds us accountable, not only others.
- **BERTopic + c-TF-IDF topic modeling (Grootendorst 2022).** The de-facto
  modern topic-modeling pipeline: UMAP → HDBSCAN → class-based TF-IDF labels. Its
  topic-forming core is HDBSCAN over embeddings. We engage it directly as the
  external baseline (§3.2): its HDBSCAN core, run on our held-constant e5
  representation, exhibits the density cliff. We are explicit that **BERTopic-
  proper (with UMAP and c-TF-IDF) is not run** (toolchain block, §6) — a genuine
  open comparison, not a dodge.
- **HDBSCAN (Campello et al. 2013; McInnes et al.).** Density-based clustering
  with a noise class. We use it and characterize its failure mode on short-text
  news embeddings (mega-blob vs shatter — no single global operating point). Our
  claim is narrow and about *this corpus geometry*, not a general criticism of
  HDBSCAN.
- **Embedding anisotropy / all-but-the-top (Mu & Viswanath 2018; Arora et al.).**
  The finding that contextual/word embeddings share a dominant direction that
  compresses cosine dynamic range, and that subtracting the mean + top principal
  components restores it. We apply all-but-top-k whitening to e5 sentence
  embeddings and **confirm the pairwise-geometry cure** (AUC 0.985; same/diff
  cosine 0.916/0.788 de-compressed 4.4× at k=1) — then report the honest negative
  that this pairwise cure does not propagate to the cluster level. This both uses
  and bounds the Mu & Viswanath result in a new setting (density clustering, not
  similarity retrieval).
- **LLM-as-annotator evaluation (Gilardi et al. 2023; Ziems et al.).** Where this
  paper cites a precision number from the companion benchmark (Paper A), that
  number is *agreement with a 3-LLM consensus panel*, not human gold — treated as
  a **calibration reference**, never an adjudicator. Paper C's own core metrics
  (voice entropy, ownership ratios, clustering coverage/purity) are **definitional
  or label-free**, so they do not inherit the LLM-gold circularity — but they
  inherit a different limit (no human validation that discovered topics are the
  "right" set; §6).

---

## 3. Design decisions (each in the 5-part template)

### Decision 1 — Voice scored by ownership, not language; who-speaks separated from who-is-spoken-about

**Decision.** For each subject country, Atlas reports a `self_voice` ratio =
share of coverage produced by outlets *owned in* that country, with a separate
`soft_power_local_language` bucket (foreign outlet publishing in the local
language) that is **never** counted as self-voice. Diversity is summarized by two
numbers: `diversity_score` (language mix) and `voice_entropy` (origin-country
entropy of who is speaking).

**Stakes (why it could be arbitrary).** The tempting shortcut is to score
diversity by the *language* of coverage, or by raw outlet count. Both are
available for free and both are wrong in a specific, measurable way: a language
metric counts BBC Persian's coverage of Iran as Iranian voice; a raw-outlet-count
metric is inflated by GDELT's ~11K predominantly Western domains. If we shipped
either, "covered in its own voice" would be an artifact of the counting rule.

**Backing (math + inference + experiment).**
- Baseline audit (`voice_mix_audit.py`, N = 146,121 signals, 168h, prod
  2026-06-22, artifact `2026-06-22-baseline.json`): **English = 96.9% of
  language-known signals**; CJK (zh/ja/ko) = 0; `diversity_score` = **3.3 / 100**.
  The monoculture is a number, not an impression.
- Ownership relation (`voice_mix.py`, `/api/v2/voice-mix?country=`): **Iran
  self_voice = 1.4%** (98.6% foreign coverage; dominant outsider tracked). This
  is the decision's justifying datum — a language metric would have scored Iran
  as substantially "self-covered" via Persian-language foreign outlets; the
  ownership metric shows it is 98.6% foreign.
- Program instrument, post-diversification (`2026-06-23-consolidation.json`,
  prod 168h): `diversity_score` **3.3 → 23.9 / 100**; **voice_entropy = 0.71**
  over **89 origin countries**; corpus **219 feeds / 126 countries / 31
  languages**. The instrument moved with a deliberate intervention (feed waves),
  which is the evidence it measures the thing it claims to.
- Definition is versioned and shared between the offline audit and the live
  endpoint (one formula, one source of truth) → reproducible.

**Alternatives ruled out (the measured negatives).**
- **Language-share as the diversity metric:** ruled out because it scores foreign
  local-language coverage as self-voice — the Iran 1.4%-vs-language-inflated gap
  is the direct measurement of the error.
- **Raw outlet count as diversity:** ruled out because GDELT's Western-domain
  firehose inflates it; `voice_entropy` over *origin countries* was adopted
  specifically because it weights "different ones speaking from different places"
  rather than outlet volume.

**Honest limit.**
- This is an **honesty/measurement instrument, not a predictiveness claim.** We do
  not claim self-voice predicts analyst-useful evidence or story accuracy — that
  is explicit future work.
- **Attributable-origin coverage is partial:** roughly one-third of signals carry
  an attributable outlet origin; the rest are GDELT rows with no origin and are
  reported as `unattributed`, not imputed. `voice_entropy = 0.71` is computed over
  the attributable slice.
- **In-window only, no temporal hold-out.** New feed waves need days of cron
  accumulation before their countries clear 0% self-coverage; the 0.71 is a
  snapshot, not a stationary property. Any generalization ("this stays diverse")
  is unhedged and not claimed.
- Two countries (KW, BH) remain uncovered (bot-blocked / no RSS) — a documented
  ceiling, not a silent gap.
- Language-count figures are mildly inconsistent across artifacts (31 vs 32
  distinct known languages depending on window); we report the verified 31 and
  flag the discrepancy rather than average it.

---

### Decision 2 — Open-set discovery via scoped-per-country partitioning (with the whitening walk-back)

**Decision.** Atlas forms topics by clustering **within each country's signal
partition** and folding the results into a lifecycle, rather than running one
global HDBSCAN pass over the whole embedded corpus. Embedding whitening is
shipped as a **reversible, default-off** lever, *not* as the recall remedy.

**Stakes (why it could be arbitrary).** A single global clustering pass is the
obvious, standard choice (it is BERTopic's default shape). It assigns only a
small fraction of signals to any topic. The tempting conclusion — and the one the
literature invites for short-text news — is that this low coverage is an
**intrinsic recall ceiling** of headline-length text. If that were true, scoping
would be pointless complexity, and the honest move would be to accept ~5%
coverage. The decision to partition is only justified if the ceiling is shown to
be an artifact of the global pass.

**Backing (math + inference + experiment).**
- **Global pass is the diagnostic negative.** System-wide, a global HDBSCAN pass
  assigns **4.94%** of country-attributable signals to a topic (~68 topics
  system-wide; `recall_scoped_estimate.py`, `system-estimate.md`, 117 countries /
  131,210 signals, 168h).
- **Scoped partitioning dissolves the cliff.** Clustering *within* each country
  raises assignment to **26.72%** across the same 117 countries, forming **3,662**
  scoped clusters (which collapse to **549 canonical served narratives** after
  umbrella-folding + retirement, per the reconciliation doc — cite 549, never the
  raw 3,662 or a cross-country "54×", as the served-narrative magnitude); the lift
  is universal, not driven by a few countries (US
  13.37% → 37.4%, DE 4.42% → 34.55%, IR 7.06% → 31.84%, MX 4.05% → 24.79%). The
  mechanism is stated and falsifiable: within a country, regional stories are the
  *majority* rather than drowned minorities, so density estimation recovers them.
- **External baseline (BERTopic's determining core).** Holding the e5
  representation constant (`external_baseline_comparison.py`, N = 8,000), the
  standard density method (HDBSCAN-global = BERTopic's topic-forming step)
  produces **3 topics, 59.1% coverage, 58.2% blob** — a mega-blob at small
  `min_cluster_size` and total shatter/collapse at large `mcs`, with **no
  operating point in between** (mcs 10 → 43.6% blob; mcs 25 → 4.6% coverage;
  mcs 75 → 0 topics). This is the measured justification for scoping.
- **Whitening — the pairwise geometry IS cured (confirming Mu & Viswanath in this
  setting).** Signal-pair separability is already high in raw e5 (ROC-AUC
  **0.985**) but cosine is scale-compressed into a narrow band (same/diff medians
  **0.916 / 0.788**); all-but-top-k=1 whitening de-compresses the signal-level gap
  **4.4×** (centroid-level 7×) with AUC unchanged
  (`measure_signal_separation.py`).

**Alternatives ruled out (the measured negatives — including our own over-read).**
- **"Accept the intrinsic recall ceiling":** ruled out by the 4.94% → 26.72%
  scoped result. The ceiling is a global-pass artifact.
- **Whitening as the recall remedy — the self-retraction (methodological
  centerpiece).** A *single* early sample showed `e5_whiten_k1` at recall 0.477 /
  purity 0.96 vs raw's ~0.09 — a clean-looking cliff crossing. It **did not
  reproduce.** Across three independent 168h samples the same config gave recall
  **{0.477, 0.062, 0.109}** — high-variance, the 0.477 a knife-edge tail. The best
  *joint* whitened config (`e5_whiten_k1`, recall 0.109 / purity 1.0) sits at the
  purity end; raw e5 at its high-recall config (recall 0.756 / purity 0.146) sits
  at the blob end — the recall/purity **cliff persists after whitening**
  (`cluster_whiten_sweep.py`, 2026-07-07). What whitening *does* reproduce is
  clustering **stabilization**: blob-resistance (held purity ≥ ~0.93 where raw e5
  and OpenAI collapse to a mega-blob) and ~6–12pp lower noise at held purity.
  **Honest frame:** whitening cures the signal-*pair* geometry and stabilizes
  density clustering, but the **cluster-level recall win is the scoped-partition
  lever, not whitening.** We foreground this walk-back as a measure-twice
  exemplar.
- **Flat clustering (KMeans / Agglomerative) as the engine:** on the held-constant
  representation these reach coherence parity in-sample (0.883 / 0.866 vs Atlas
  0.849) — reported faithfully — but are ruled out as the *engine* because they
  force 100% assignment (no noise rejection), are fit-and-scored in-sample (no
  transfer), and have no topic identity / lifecycle. The paper's claim is
  therefore about scoping + lifecycle + noise rejection, **not** "Atlas clusters
  tighter."

**Honest limit.**
- **Truncated / capped sample.** The 26.72% system estimate caps each country at
  6,000 signals (dropping the highest-volume tail) and lost 9 of the highest-
  volume countries to connection errors under parallel load; two countries
  (TZ, DO) blobbed and are flagged. The estimate is therefore a system *estimate*,
  not a census. Their inclusion would add signal and topics on the same pattern,
  but this is stated as expectation, not measurement.
- **BERTopic-proper (UMAP + c-TF-IDF) is not run** (numba has no py3.14 wheel).
  The HDBSCAN-global row is its determining core; a py3.12 BERTopic-proper run is
  the clean, still-**open** external follow-up that would isolate the schema's own
  contribution. We do not claim to have compared against BERTopic-proper.
- **Coverage denominators are not chained.** Different documents report
  0.2% / 2.5% / 5.6% / **25.8% (funnel)** / **26.72% (scoped)** / ~38% / 39.7% under
  different definitions (of-total vs of-embedded vs of-country-attributable, global
  vs scoped, pre- vs post-useful-coverage-gate); funnel-coverage (25.8%) and
  scoped-recall (26.72%) are distinct canonical claim-types per
  `2026-07-16-coverage-metric-canonicalization.md`. This paper fixes **one**
  denominator per claim —
  the scoped result is *of country-attributable embedded signals* — and states it
  inline. The earlier "54× more narratives" figure is **dropped**: it double-
  counts the cross-country duplicates that the umbrella pass (R2) exists to
  collapse.
- **In-window only, no temporal hold-out** anywhere in the discovery result. All
  "the lift generalizes" language is hedged to "reproduces across the sampled
  countries in this window."
- Clustering purity/recall are measured against a single-story probe (Gaza) that
  spans many legitimate sub-stories, so *low* single-cluster recall can be
  *correct* fragmentation — which is exactly why purity + blob-resistance + noise
  (which reproduce), not the recall headline (which does not), carry the
  conclusion.
- **The formation lift is not yet an identity lift.** Scoped partitioning forms
  the clusters; the identity layer that should keep one event as one story was
  subsequently measured to shred it (one event held as 22 same-day clusters;
  fragments of one event do not share a nearest topic — "argmax dispersion",
  Paper B §4). Coverage numbers in this section count *assignment*, not
  *coherent served stories*; Decision 5 owns the serving half.

---

### Decision 3 — The country axis is audited, not assumed: the FIPS→ISO corruption and its heal

**Decision.** Every country-keyed claim (voice mix, self-coverage, per-country
discovery, country doors) rides on one translation layer
(`country_codes.py`, GDELT FIPS/GEC → ISO). That layer is now **audited against
row content, corrected, and versioned**, with a machine-readable correction
layer (`country-code-corrections-v1.json`) that every archive reader and
historical ETL must apply; the immutable external archive is never mutated.

**Stakes.** The voice instrument's unit of analysis is the country. If the
translation layer is wrong, "Iran self-voice 1.4%" is a claim about a bucket,
not a country — and the error class is invisible from inside the system,
because the wrong codes are *plausible* ISO codes.

**Backing (the audit).** Provoked by the UI gold eval's control arm (a Lesotho
query whose arrival brief rendered Lebanon — **316 Lebanese signals under
`LS`**, `docs/research/gold/2026-07-30-ui-eval-v2-run.md` defect D2), the full
audit found the map had **5 mis-translated FIPS entries and ~89 missing
divergent codes since inception** (2025-12-04): FIPS `LE` (Lebanon) → `LS`
(Lesotho), Paraguay filed under `PA` (Panama), Serbia under raw GEC `RB`,
Kosovo under `KV`, Georgia-the-country under `GG` … —
`docs/research/country-code-remap/2026-07-28-country-code-remap.md`. Two
long-standing "known oddities" dissolved under the audit: the old "LS/OS/MG =
geocode noise" note was **this bug misdiagnosed**, and `OS` was identified as
GDELT's "Oceans" pseudo-code (correctly left unmapped, with a product follow-up
to exclude it from country surfaces).

**Backing (the heal, verified before writing).** The remap was executed
verification-first: 20-headline samples per bucket; lane-split discovered
(only the GDELT lane is wrong — RSS rows under `MN` are genuine Mongolia, so a
whole-bucket remap would have shredded them); outlet-origin override rows
(`geo_confidence = 0.35`) excluded as genuine; the LS bucket split
Lebanon/Liechtenstein by keyword with the residual risk quantified (~375:1) and
accepted in writing. Hot-window rows were remapped with reversible ledgers;
the **historical store was healed in a 22,472-row remap** (PK collisions
merged, idempotence proven: re-run = 0 ops), and the corrections layer was
wired into the three archive writers that had zero consumers at audit time
(fix `b7ab7def`; heal `f73c2ef6`; ledgers under
`docs/research/country-code-remap/ledgers/`).

**Alternatives ruled out.** Trusting the vendor's code space (the map was wrong
for eight months); mutating the immutable archive (a re-ETL would resurrect the
wrong codes — the correction layer at read time is the design); and remapping
whole buckets without lane/confidence splits (measured to destroy genuine
rows).

**Honest limit.** The remap restores **GDELT's stated country, not per-row
geographic truth** — upstream gazetteer noise (Bathurst NSW → Gambia,
Montserrat-the-mountain → Montserrat-the-island) rides along unchanged, and is
a different, disclosed error class. Rows contaminated in *derived* GDELT-side
aggregations need re-derivation rather than remapping. And the boundary is
temporal: per-country claims for the ~40 affected buckets dated before
2026-07-28 must be read against the correction layer. This paper's Table 1
voice numbers key on RSS-lane outlet ownership and subject countries whose
buckets were sampled clean; the exposure is stated rather than assumed away.

### Decision 4 — Script-aware text heuristics, because the monoculture was also in the code

**Decision.** Every text-gating heuristic in the pipeline is audited for script
blindness; three were measured excluding non-Latin coverage and fixed
(character-composition rules keyed to the text, never to `source_lang`):
1. **Capture:** GDELT translingual `<PAGE_TITLE>` validation required ≥4
   whitespace-separated words — CJK titles have few or none, so complete
   Japanese/Chinese headlines were discarded at ingest and stored as NULL.
2. **Clustering eligibility:** a flat `length(headline) >= 20` floor.
3. **Syndication dedup:** `_norm_headline` deleted non-Latin characters before
   comparison (a Cyrillic headline reduced to its digits).

**Stakes.** These are exactly the "surely harmless" validations every news
pipeline carries. Each one silently deleted the non-English world from a
different stage — capture, discovery, dedup — while every dashboard stayed
green, and while this very paper claimed measured diversity.

**Backing.**
- The NULL-headline hole
  (`docs/research/recall-229/2026-07-30-gdelt-null-headline-diagnosis.md`):
  the translingual lane carried **53.3% NULL headlines for CN, 45.5% TW, 38.5%
  JP** (English lane ~0.3%) — ~33k lost headlines/week — and the country
  ordering is the mechanism's fingerprint (Korean uses spaces → KR only 10.8%).
  Replayed on a live GDELT file: the title was present in 99.8% of rows; the
  validator rejected 160 CJK-dominant complete headlines, and the
  script-aware rule rescued **160/160** while every ASCII junk placeholder
  stayed rejected by construction. Post-deploy, fresh-row NULL rates fell **JP
  23.2% → 0.0%, CN 41.4% → 1.5%**.
- The length floor
  (`docs/research/recall-229/2026-07-30-cjk-length-floor-measurement.md`): the
  headline "27.3% of Japanese signals" number was itself audited and found to
  conflate NULL headlines with genuinely-short ones; the pure script-blind
  effect is **JP 2.6% / KR 2.2% / TW 3.8% / CN 15.0%** vs US 0.95% — real,
  CJK-shaped, and fixed behind a reversible flag (`ATLAS_CJK_LEN_FLOOR`) at the
  two live clustering-pull sites, with a full census of every other
  `length(headline)` site and its live/dormant status.
- The dedup normalizer: fixed `924174b2`; the syndication-count inputs for
  ru/uk/ar/fa were poisoned until then (bounds Paper B §3.2's diversity
  estimates on non-Latin coverage, cross-referenced there).

**Alternatives ruled out.** Keying rescues on `source_lang` metadata (measured
unreliable — the translingual lane is `xx`); lowering floors globally (junk
placeholders are ASCII and short for unrelated reasons; the script-aware rule
keeps them out *by construction*).

**Honest limit.** Historical NULL rows are not backfilled (mechanically
recoverable from the archive; the hot store self-heals in a week). Short
non-CJK titles (uk/lt/ne one-to-three-worders, ~0.6% incidence) still drop —
the word-count validation remains script-blind for them, at low incidence,
needing its own measurement. This family was found defect-by-defect, not by a
systematic audit of every text heuristic; the enumeration in the length-floor
artifact is the start of that audit, not its completion.

### Decision 5 — A per-country lifecycle clock, because the serving floor was operational, not statistical

**Decision.** Serving-level coverage — *can a country's door show a thread at
all* — is now a measured, first-class number, and the lifecycle that produces
it is being re-designed under pre-registered gates: one clock tick per snapshot
pass; aging only when the topic's country was actually clustered; revival lands
in `candidate` and must earn promotion through the label court's `entailed`
certificate.

**Stakes.** The intuitive readings of "small country serves nothing" are data
poverty ("not enough signals") or threshold strictness ("lower the quality
bars"). Acting on either would have been wrong in *both* directions — junk
promotion without coverage gain.

**Backing (the diagnosis, every intuitive cause refuted).**
`docs/research/recall-229/2026-07-29-threading-floor-diagnosis.md`, triggered
by the external-agenda gold queries (4/5 failures had the material in-corpus
and still served zero threads). Measured: only **30 of 168 clustered countries
could serve a thread**. Not volume — Bolivia and Mali form clusters the same
size as the United States (tier-invariant mean 12.2 vs 12.7 members). Not
eligibility — no witness country fell below the embedded floor. Not identity
re-match — tail countries re-match at ~100%, better than the US. The binding
mechanism is **the clock**: the staleness counter advanced 2–4× per night
(straggler snapshot groups re-ticking the world) while a tail country is
clustered only on weekend-budget nights, so one missed pass aged a topic
through deprecation *and* retirement — measured directly as 1,007 topics at
`snapshots_since_seen = 4` after exactly one elapsed snapshot, and **1,353
retired topics that pass every quality bar**. The only survivors of that
regime in tail countries were their wire/lottery feeds — junk the detectors
rightly block, so the doors stayed dark honestly.

**Backing (the fix, gated — and the gate fired).** The clock arithmetic fix
passed its mechanical gate (0 invariant violations on 6,649 topics) and lit
dark doors live (Colombia 8 threads, Japan 6) — and was **killed the same day
by its pre-registered composition gate** (37.5% of revived-to-active topics
were real stories vs a 90% bar) and surgically reverted: coverage bought with
junk is a failure, not a partial win
(`docs/research/recall-229/2026-07-30-tickv2-tf1-tf2-verdict.md`). The gated
successor (revive-to-candidate + court certificate) improved composition
**+33pp to 70.5%** at census scale and remains ON but not done — the residual
is the certificate's own precision, with per-class levers enumerated
(`2026-08-03-tf3b-gate-c-census.md`; full refutation chain: Paper B §4.6). The
per-country clock itself is armed behind the completion of that verdict.

**Alternatives ruled out.** Lowering `volume_min` / `cohesion_min` /
`min_kept` (the bars are not what binds — the one country where a bar does
bind, Myanmar, needs a longer window, not a lower bar); per-country adaptive
thresholds (cluster sizes are tier-invariant, so there is nothing to adapt
to); ungated revival (measured at 37.5% real).

**Honest limit.** The serving-coverage claim (30/168) is one day's census under
one budget configuration; the tail's weekday deferral is a scheduling artifact
that the tail-reserve change addresses separately. The 70.5% composition is a
census of one weekend cohort. The #238 subject-geography arm removes a third of
a healthy door's candidates — if subject verification is systematically easier
for foreign-subject stories, it is a second attrition lane pointed at the same
countries; named, unmeasured.

---

## 4. Methods

**Data.** Production Atlas corpus, `signals_v2` + `signal_embeddings` (e5
sentence embeddings over headlines). Voice audit: N = 146,121 (baseline) and the
219-feed program corpus, 168h windows. Discovery: 117 countries / 131,210
country-attributable signals (cap 6,000/country); external-baseline sample
N = 8,000; whitening sweep 3 × ~3.3K-row 168h samples with a 390–512-row Gaza
probe each. All read-only, sampled, on M1 `mlvenv`.

**Labels / gold — foregrounded disclosure.**
- **No human-adjudicated gold exists anywhere in this paper: `n_rows_with_human_gold = 0`.**
- Paper C's core metrics are **definitional or label-free**: voice_entropy and
  self_voice are functions of outlet-ownership metadata; clustering coverage is
  the fraction of signals assigned; purity/recall are computed against a
  single-story probe; coherence is intra-topic mean cosine (embedding-based, not
  c_v / UMass), comparable across methods only because the representation is held
  constant.
- Where a precision number is cited from the companion benchmark (Paper A), it is
  **agreement with a 3-LLM consensus panel** (sonnet-4.6 + gpt-4.1 + deepseek,
  Fleiss κ 0.625), used as a **calibration reference**, never as ground truth.

**Metrics.** `diversity_score` (100 · mean of english_balance, language_entropy,
cjk_coverage); `voice_entropy` (normalized entropy over origin countries);
`self_voice` / `soft_power_local_language` (ownership-based shares); clustering
**coverage** (% assigned), **purity** (majority-probe-label fraction per
cluster), **recall** (single-story probe), **noise** (HDBSCAN unassigned share),
**blob%** (largest-cluster share), **coherence** (intra-topic mean cosine).

**Statistical conventions.**
- **Wilson score intervals** for binomial proportions (coverage, agreement rates).
- **Stratified bootstrap** (≥10,000 resamples, fixed seed; seed 20260527 for the
  shared benchmark) for CIs on precision/agreement where cited.
- **Fleiss / Cohen κ** for inter-annotator (inter-LLM) agreement on any cited
  panel label.
- **Two-proportion z-test** for difference claims; we report the statistic and
  p-value and **do not** call within-noise differences "improvements" (this
  convention is what forces the whitening walk-back and the anchoring-control
  hedge to be reported honestly).
- Multi-sample results (whitening) are reported as the **distribution across
  samples**, never a single favorable draw.

---

## 5. Results (real-numbers table)

**Table 1 — Voice instrument (production, 168h).**

| metric | value | source |
|---|---|---|
| English share of language-known (baseline) | 96.9% | `2026-06-22-baseline.json` |
| CJK (zh/ja/ko) at baseline | 0 | baseline audit |
| diversity_score (baseline → program) | 3.3 → 23.9 / 100 | baseline / consolidation |
| voice_entropy (origin), # countries | 0.71 · 89 | `2026-06-23-consolidation.json` |
| Iran self_voice (ownership) | 1.4% (98.6% foreign) | `/api/v2/voice-mix?country=IR` |
| corpus reach | 219 feeds / 126 countries / 31 languages | consolidation |

**Table 2 — Open-set discovery (label-free, held-constant e5).**

| method / config | coverage | purity / blob | topics | source |
|---|---|---|---|---|
| Global HDBSCAN (system) | 4.94% | — | ~68 | `system-estimate.md` |
| **Scoped per-country (system)** | **26.72%** | no blob (2 flagged) | 3,662 | `system-estimate.md` |
| HDBSCAN-global (BERTopic core, N=8K) | 59.1% | **58.2% blob** | 3 | `external_baseline_comparison.py` |
| KMeans flat (N=8K, in-sample) | 100% | coherence 0.883 | 251 | external baseline |
| Atlas scoped+gated (N=8K, transfer) | 89.7% | coherence 0.849, 6.5% blob | 251 | external baseline |

**Table 3 — Whitening ablation (the walk-back; `eom mcs=8 ms=1`, 3 samples).**

| space | run A | run B | run C | note |
|---|---|---|---|---|
| e5_raw recall / purity | 0.09 / 0.878 | 0.067 / 1.0 | 0.068 / 1.0 | shatters |
| e5_whiten_k1 recall / purity | 0.477 / 0.96 | 0.062 / 1.0 | 0.109 / 1.0 | **high-variance recall — no stable crossing** |
| signal-pair AUC (raw e5) | 0.985 | — | — | separability already present |
| same/diff cosine (raw → whiten_k1 gap) | 0.916 / 0.788 → 4.4× | — | — | pairwise geometry cured |

Reading: the pairwise geometry cure is real and reproducible (AUC 0.985, 4.4×
de-compression); the **cluster-level recall crossing is not** (0.477/0.062/0.109).
Whitening's reproducible value is stabilization (blob-resistance, ~6–12pp lower
noise at held purity), and it is shipped default-off. The recall lift belongs to
scoping (Table 2).

**Table 4 — Instrument-integrity audits (Decisions 3–5).**

| audit | headline number | after the fix | source |
|---|---|---|---|
| country-axis corruption (FIPS→ISO) | 5 wrong + ~89 missing codes since 2025-12-04; Lebanon served as Lesotho (316 signals) | hot remap ledgered; **22,472-row historical heal**, idempotent; corrections-v1 wired into 3 archive writers | `country-code-remap/2026-07-28-country-code-remap.md` |
| CJK capture hole (title validation) | CN 53.3% / TW 45.5% / JP 38.5% NULL headlines in the translingual lane (~33k/week) | live replay: 160/160 CJK failures rescued, junk excluded by construction; fresh rows JP 0.0% / CN 1.5% NULL | `recall-229/2026-07-30-gdelt-null-headline-diagnosis.md` |
| CJK clustering floor | JP 2.6 / KR 2.2 / TW 3.8 / CN 15.0% of non-NULL headlines under the flat 20-char floor (US 0.95%) | script-aware floor, env-gated default-off | `recall-229/2026-07-30-cjk-length-floor-measurement.md` |
| non-Latin dedup normalizer | Cyrillic headline reduced to digits; ru/uk/ar/fa syndication dedup poisoned | fixed `924174b2` | same family, cited in the null-headline diagnosis |
| serving-level country coverage | **30 / 168** clustered countries servable; 1,353 retired topics passing every quality bar; 1,007 topics aged 4 ticks in one snapshot | clock fix gated: ungated revival 37.5% real (KILLED); court-gated revival 70.5% (census n=244) | `recall-229/2026-07-29-threading-floor-diagnosis.md`, `2026-07-30-tickv2-tf1-tf2-verdict.md`, `2026-08-03-tf3b-gate-c-census.md` |

---

## 6. Limitations (LLM-panel gold first, then temporal, then power)

1. **LLM-panel gold / no human gold (foregrounded).** `n_rows_with_human_gold = 0`
   across the paper. Paper C's own metrics are definitional or label-free, which
   removes the LLM-gold circularity but introduces a **construct-validity limit**:
   no human has adjudicated that the discovered topics are the *right* topics, or
   that ownership-scored self-voice is the *right* notion of "own voice." The
   voice metrics are internally consistent and reproducible, not externally
   validated. Any cited precision number (from Paper A) is agreement with a 3-LLM
   consensus panel used as a **calibration reference**, not ground truth.
2. **No temporal hold-out anywhere.** Every result is a single-window snapshot
   (voice 168h; discovery 168h). We do not claim the diversity level or the scoped
   coverage lift is stationary. New feed waves need days to accumulate; the topic
   set is dynamic by design. All generalization language is hedged to "reproduces
   across the sampled units in this window."
3. **Truncated / capped discovery sample.** 6,000/country cap drops the high-volume
   tail; 9 top-volume countries lost to parallel-load connection errors; 2 blob
   countries (TZ, DO) flagged. The 26.72% is a system *estimate*.
4. **Per-topic / per-country statistical power.** Many countries contribute a few
   hundred signals; per-country scoped percentages have wide intervals and are
   reported as a distribution, not per-country point claims.
5. **Anisotropy result is bounded.** Whitening confirms Mu & Viswanath's pairwise
   cure but the cluster-level negative shows the cure does not propagate — a
   scoped, honest extension, not a general "whitening fixes clustering" claim.
6. **Attributable-origin partiality.** ~⅔ of signals lack outlet origin
   (`unattributed`); voice_entropy is over the attributable slice.
7. **BERTopic-proper unrun** (§3.2) — the external comparison is against its
   HDBSCAN core only; the full UMAP + c-TF-IDF pipeline is toolchain-blocked and
   open.
8. **Coverage-denominator discipline.** One defined denominator per claim; the
   "54×" cross-country figure is dropped as a double-count. A new claim-type
   joined the canonicalization doc with Decision 5: **serving-level country
   coverage** (countries with ≥1 servable thread) is distinct from funnel
   coverage and scoped recall, and must never be chained with either.
9. **Pre-heal per-country provenance.** Country-keyed measurements dated before
   2026-07-28 must be read against `country-code-corrections-v1.json` for the
   ~40 affected GDELT-lane buckets (Decision 3). The headline voice numbers'
   exposure is bounded (ownership metrics key on the RSS lane, which was
   clean), but any per-country GDELT-volume figure from before the heal
   inherits the defect.
10. **Formation ≠ identity ≠ serving.** Table 2 measures assignment; the
    identity layer's fragmentation (Paper B §4) and the lifecycle's serving
    floor (Decision 5) each sit between "assigned" and "an analyst sees one
    coherent story." The three layers now have three separate measured numbers;
    conflating them was the original sin of the coverage-denominator mess.

---

## 7. What must exist before submission

**Blocking (needed for the claims as written):**
- [ ] **Wrap the voice audit and the scoped-estimate in reproducible harnesses
      with fixed seeds and versioned artifacts** already exist
      (`voice_mix_audit.py`, `recall_scoped_estimate.py`,
      `cluster_whiten_sweep.py`, `external_baseline_comparison.py`) — confirm each
      re-runs to the reported figures and pin the exact artifact hashes in the
      paper.
- [ ] **Fix one coverage denominator** in prose and re-derive every coverage
      number from it; delete the "54×" figure everywhere it is cited.
- [ ] **Voice CIs.** Add Wilson intervals to the self_voice / diversity headline
      numbers (currently point estimates); report voice_entropy with a bootstrap
      CI over the attributable slice.
- [ ] **State the whitening walk-back as a titled subsection**, not a footnote —
      it is the methodological contribution.

**Strengthening (turns hedges into results; currently open):**
- [ ] **BERTopic-proper (UMAP + c-TF-IDF) on a py3.12 env** — the clean external
      baseline that isolates the schema's contribution (toolchain-blocked today).
- [ ] **A temporal hold-out** for at least the scoped-coverage lift (two
      non-overlapping windows) — would lift the strongest generalization hedge.
- [ ] **Uncapped / higher-cap scoped run** including the 9 dropped high-volume
      countries — converts the "system estimate" into a census-grade number.
- [ ] **A small human-adjudicated validation** of (a) a sample of discovered
      scoped topics (are they real, distinct stories?) and (b) ownership labels on
      a sample of outlets — would give the paper its first non-LLM, non-definitional
      ground truth and directly address Limitation 1.
- [ ] **Re-measure the voice and per-country tables post-heal** (Decision 3) and
      post-CJK-capture-fix (Decision 4) — the East-Asia coverage numbers in
      particular were structurally capped by the capture hole and should move.
- [ ] **The serving-coverage census re-run** once the per-country clock lands:
      the pre-registered target is countries-served 30 → ≥60 with composition
      held (the TF-gate ladder in the threading-floor artifact §5).
- [ ] **A systematic script-blindness audit** of every remaining text heuristic
      (the length-floor artifact's site census is the worklist), converting
      Decision 4 from defect-driven to audit-driven.

**Explicitly out of scope (do not add / do not claim):**
- Any "more diverse than [system]" or "better discovery than [system]" comparison.
- Predictive-usefulness claims for the voice composite (future work).
- An analyst user study (that is the deferred P7 report, not this paper).
