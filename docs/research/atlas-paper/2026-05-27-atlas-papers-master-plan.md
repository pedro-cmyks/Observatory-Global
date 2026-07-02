# Atlas Papers — Master Plan

Date: 2026-05-27
Status: canon (active)
Scope: full methodological backbone for Atlas as a narrative intelligence
system. Each entry below is a stand-alone paper. The series together
constitutes the academic justification for every major design decision
in Atlas.

## Why a series, not a mega-paper

Atlas spans data ingestion, source quality, NLP, sentiment fusion,
topic classification, heat composition, thread aggregation, evidence
sampling, temporal model, visualization, and analyst workflow. A
single paper covering all of this would be 50+ pages, hard to peer
review, hard to cite, and slow to publish. A coordinated series:

- Ships incremental contributions on a tighter cadence.
- Lets each paper choose its best-fit venue.
- Lets a reader cite the exact methodological piece they need.
- Lets reviewers focus on one decision class.
- Keeps the schema (`atlas-topic-benchmark-v2` and successors) as the
  shared substrate across papers.

## Shared substrate across all papers

All papers in the series share:

- Production system reference: `atlas-api-pedro` on Fly + Supabase Postgres.
- Code repository: this repo (`v3-intel-layer` branch).
- Benchmark schema family: `atlas-topic-benchmark-v2` and evolutions.
- Reproducible audit + benchmark tooling under `backend/scripts/`.
- LLM-as-annotator and LLM-as-baseline (Sonnet 4.6) as common
  evaluation infrastructure.
- Statistical conventions: Wilson per-topic CI, stratified bootstrap
  overall CI, Cohen's kappa for inter-annotator agreement,
  Landis & Koch bands.
- Single-reviewer initial annotation honesty: labels are referred to
  as `pedro_initial` / `sonnet46_initial`; never "gold" without
  qualifier.

## Series index

### Paper 1 — Evidence-role topic classification + distillation methodology

**Status:** active; RQ1 measured at scale, manuscript still open. Outline doc:
`docs/research/atlas-paper/2026-05-27-methodology-paper-outline.md`.

**Core claim:** A single-layer topic classifier collapses semantic
roles; an evidence-role schema plus an LLM-distilled lexicon
refinement loop lifts precision toward LLM baselines while keeping
production inference at zero per-call cost.

**Evidence already collected:**
- Reviewed gold N=61 (batches 01+02).
- 3-vendor consensus-gold benchmark: 660 usable rows / 31 ties,
  Fleiss kappa `0.625`.
- Atlas v2 precision `41.6%` [37.8, 45.5].
- LLM zero-shot precision `78.6%` [75.3, 81.7].
- LLM few-shot precision `81.1%` [77.7, 84.0].
- Error anatomy: `off_topic` and `scope_mismatch` dominate; substring noise is
  only `0.6%` of incorrect rows.
- Scope gate lift measured: `41%` -> `70%` precision on scored rows.
- Evidence-role student v1 measured: `78.2%` primary_evidence precision,
  `71.4%` noise recall, no LLM at inference.
- Distillation candidates surfaced per topic (reasoning mining).

**Product evidence accrued (2026-06-25):** the evidence-role / distillation
pipeline is now the production backing record, with several decisions the paper
can cite as deployed-at-scale rather than offline-only. (1) **`dynamic_topics`
is the backing record** for user-facing threads, hydrated after the emergent
snapshot cron using local e5 + the evidence-role student noise gate, caching
per-cluster `role_noise_rate` on `emergent_clusters` at `$0` API
(`thread_intelligence.evidence_role`, CLAUDE.md 2026-06-02 / 2026-06-09). (2)
The **precision gate** survives in production (`snapshot_emergent_topics.py`
keeps 9 of 12 raw HDBSCAN clusters; CLAUDE.md 2026-06-01). (3) **DeepSeek**, not
the deprecated local Ollama, does the cluster labeling (`deepseek_narrative.py`;
the 2026-06-02 note records Ollama `llama3.2:1b` at 25% decision accuracy on 20
rows — keep that as the negative-control disclosure). (4) A separate but
adjacent distillation-style **ranking calibration harness** is shipped:
`backend/scripts/calibrate_research_ranking.py` calibrates weights +
normalization midpoints over spec-derived gold orderings + live forcing cases,
`21/21` vs a `20/21` baseline (report
`docs/research/ranking-calibration/2026-06-10-ranking-calibration.md`; CLAUDE.md
2026-06-10) — a constraint-harness calibration the methodology section can cite.
(5) The semantic retrieval threshold was **re-measured on the real ~100K corpus
to 0.84** (`research_semantic.SIGNAL_MIN_SIMILARITY = 0.84`; below the 0.84 band
admits same-language affinity junk), shipped with an **`is_junk_headline`
filter** on both write and query side (`is_junk_headline`, CLAUDE.md
2026-06-11/12 #223) — a corpus-grounded threshold + noise filter, not a fixed
constant.

**Evidence still missing for submission:**
- Result-bearing draft skeleton with current tables and figures.
- Temporal generalization hold-out week.
- BERTopic / lex-only / theme-only ablation baselines.
  - **2026-06-29 motivation** (spec `docs/specs/2026-06-29-atlas-engine-gdelt-decoupling-syndication.md` §2.2/§3): the
    theme-only ablation now has a concrete defect to measure against —
    `gdelt_theme_hints` wire polysemous GKG codes into topics (`KILL` ∈ BOTH
    `armed-conflict-escalation` and `gender-violence-rights`, `migrations/019:149,169`);
    `KILL` fires on idioms ("killing it"), injecting false conflict assignments.
    The ablation is the BLOCKING gate before removing theme-hints in prod (measure
    recall delta + semantic recovery). The 41.6% precision number came from the
    lex+theme system, so removal must be measured, not declared.
- Anchoring effect measurement if the paper keeps the assistant-hint workflow as
  a central claim.
- Limitations language separating reviewed diagnostic labels, consensus gold,
  and local Ollama negative evidence.
- Threshold-sweep curve around the re-measured `0.84` semantic floor (precision/
  recall vs cut) on the full persisted corpus, not just the band rationale.
- `role_noise_rate` calibration check: does the cached per-cluster noise rate
  predict reviewed precision on a held-out thread sample?

**Target venues:** EMNLP industry, ACL Findings, NLP4PI workshop.

---

### Paper 2 — Cross-source source-quality scoring for narrative intelligence

**Status:** seed. No paper outline yet.

**Core claim:** A composite source-quality vector (`source_family`,
`geo_confidence`, `attribution_method`, `is_state_media`, source
diversity, aggregator down-weighting) is more predictive of analyst-
useful narrative evidence than any single signal alone.

**Evidence available:**
- 9 ingest sources (GDELT, RSS, NewsData, MediaStack, NewsAPI,
  Reddit, ReliefWeb, ACLED, AISStream, OpenSky).
- Per-source defaults documented in CLAUDE.md.
- Source blocklist (50+ domains).
- Atlas heat formula component `voice` already weights source
  diversity.

**Product evidence accrued (2026-06-25):** the source-quality axis grew a
measured, surfaced metric the paper can anchor on — **who speaks vs who is
spoken about**. (1) A repeatable **Voice Mix audit**
(`backend/scripts/voice_mix_audit.py`, read-only) computes a `diversity_score`
(0-100, mean of english_balance / language_entropy / cjk_coverage) and the
origin-diversity headline `voice_entropy`; baseline was a measured monoculture
(English `96.9%` of language-known, CJK `0`, `diversity_score` 3.3/100, artifact
`docs/research/voice-mix/2026-06-22-baseline.json`), and after the multilingual
ingest waves `diversity_score` reached `23.9/100` with **`voice_entropy = 0.71`
over 89 countries, above the 0.65-0.70 target** (CLAUDE.md 2026-06-22 /
2026-06-23). (2) The same formula is exposed as a product contract:
`GET /api/v2/voice-mix?hours=&country=` via `app/services/voice_mix.py` (single
source of truth shared with the audit; #160). (3) **`source_origin_country` is
persisted at ingest** (`ingest_rss.py`) — outlet home country, distinct from
story subject country, backfilled ~93% of rows. (4) **Self-coverage is defined
by OWNERSHIP, not language**: `self_voice = origin == subject`, with a separate
`soft_power_local_language` bucket for a foreign outlet writing in the local
language (BBC Persian on Iran counts as soft-power, never as self), ratios taken
over attributable origin and `unattributed` GDELT reported honestly
(`voice_mix.relation`; live: Iran `10.4%` domestic, US `10%`, DE `91%`, CO
`52%`; verification script `backend/scripts/self_coverage_report.py`; CLAUDE.md
2026-06-22 WAVE 4). (5) **#217 source-credibility tiers** are scoped as the
product face of this paper (CLAUDE.md 2026-06-10 spec review) — design exists,
not yet measured.

**Evidence to collect:**
- Cross-source coverage matrix (which sources cover which crises).
- Per-source false-positive rate on stratified sample.
- Aggregator-share metric per thread; correlation with analyst
  usefulness.
- State-media leakage rate by topic.
- Correlation of `voice_entropy` / `self_voice_ratio` with analyst-judged
  perspective diversity on a stratified thread sample (does the ownership
  metric track "did we hear the local voice?").
- #217 credibility-tier ablation: does the tier weight change analyst-useful
  ranking beyond `source_family` + `is_state_media` alone.

**Target venues:** ICWSM, JCDL, ACL Findings.

---

### Paper 3 — Atlas heat: composite heat detection for multi-source signals

**Status:** seed. Heat formula doc:
`docs/methodology/atlas-heat.md`. Mig 026 + `country_heat_v2`.

**Core claim:** A multi-component heat score (velocity + surprise +
diversity + voice + polyphony + geo_confidence + duplication) detects
narrative-grade heat with fewer volumetric false positives than raw
signal counts. Per-component ablation shows which signals contribute
the most to analyst-relevant ranking.

**Evidence available:**
- `country_heat_v2` matview with 7 components live.
- `heat_countries` API exposes the ranking.
- `heat_voluminous_countries` lens for volume comparison.

**Result — ablation RUN (2026-07-01, PR3-11):** the core claim is now MEASURED, not asserted.
`external_baseline_comparison`-style pull of `/heat/countries` (N=200): **Kendall-τ(composite rank
vs volume rank) = −0.198** (mildly NEGATIVE — not a volume proxy); top-8-by-composite vs
top-8-by-volume overlap **0/8** (GT/CR/CI/HN small-country anomalies vs GB/CN/IN/RU firehoses).
Per-component: `surprise_kl` (+0.401 composite / −0.558 volume) + `source_diversity` (+0.486) drive
the divergence; `local_voice_ratio` (+0.413) is the one volume-leaning term, damped. Artifact:
`docs/research/embedding-ablation/2026-07-01-heat-ablation.md`. (Kendall-τ + per-component ablation
= the two deliverables the P3 seed named.)

**Product evidence accrued (2026-06-25):** the volume≠importance thesis was put
on the map and verified in production (#231). The map `country-heat-fill` had
regressed to `/nodes` `.heat`, which is **volume-rank** (US 1.0, GB 0.40, CN
0.26 — monotonic with signal count), i.e. exactly the distortion this paper
argues against (US always reddest). It now fills from the **`atlas_heat`
composite** via `/api/v2/heat/countries` (`App.tsx` fetches
`heat/countries?limit=250` and keys on `it.atlas_heat`, CLAUDE.md 2026-06-12
#231) — so a low-volume but composite-hot country (e.g. GZ 0.74/vol49, LB
0.65/vol3) outranks high-volume US, and US is no longer reddest. **Volume was
demoted to glow-width only**; absent-from-composite reads as not-hot. A
follow-up (CLAUDE.md 2026-06-13) widened the visible band: fetch all (limit 250)
then **min-max normalize the real composite band onto [0.1, 1.0]** across the
full blue→cyan→amber→red ramp (the raw 0.36-0.72 band rendered flat-orange).
This is the live, eyeballed (Vercel-confirmed) demonstration that the composite
re-orders the world away from raw counts — the qualitative half of the paper's
per-component ablation claim, on the production surface.

**Evidence to collect:**
- Per-component ablation: drop each component, measure ranking shift.
- Analyst preference study: heat-ranked vs volume-ranked panels (the live
  composite-vs-volume-rank swap is the deployable A/B substrate).
- Time-correlation study: do heat spikes lead or lag external news?
- Quantify the composite-vs-volume re-ranking (Kendall-tau / top-k overlap
  between `/nodes` volume order and `/heat/countries` composite order).

**Target venues:** ICWSM, JCDL, KDD Applied Data Science track.

---

### Paper 4 — Thread aggregation and evidence sampling for real-time narrative tracking

**Status:** seed. Implementation in
`backend/app/services/thread_intelligence.py`. Spec:
`docs/specs/2026-05-24-living-narrative-threads.md`.

**Core claim:** Treating narrative threads as the first-class user
unit (instead of topic buckets) requires evidence-deduplication,
syndication detection, source diversity weighting, and a confidence
band. The resulting thread contract supports the seven Atlas questions
better than per-topic aggregation alone.

**Evidence available:**
- `THREAD_EVIDENCE_SQL` with `DISTINCT ON (LOWER(headline))` and
  `evidence_role` classification.
- `confidence_band()` classifier.
- Living thread contract `living-narrative-threads-v0`.
- Quality audit document
  (`docs/research/2026-05-24-thread-quality-audit.md`).

**Product evidence accrued (2026-06-25):** the thread serving model was
re-grounded on a quality-not-source decision the paper can defend. (1)
**UNIFIED thread ranking** (`app/services/thread_ranking.py`, pure, 6 tests):
`score = 0.45·log-volume + 0.35·relative-movement(changed_10h) +
0.20·coherence(avg_confidence)`, min-max normalised across the candidate set,
**NO source bias** — volume is log-damped so a 3K-signal category can't bury a
50-signal story and coherence is the guardrail against loose bins. This
explicitly **killed the living/aggregate distinction** (Pedro: a persistent
atlas topic that keeps growing IS a live thread; demoting by origin was a source
label dressed as quality); `fetch_threads` now merges dynamic + atlas as one
deduped population ranked by score (prod-verified: Russia-Ukraine leads on
movement `ch10=147`, a surging 1000-signal atlas category ranks top, an emergent
thread drops 1→7; CLAUDE.md 2026-06-24). (2) **Evidence sampling is honest under
the gate**: `evidence_samples` ride in the briefing/thread payload, and when the
quality gate clears 0 but raw signals exist the theme detail serves
`below_gate_evidence` raw headlines behind an **UNVERIFIED banner** rather than a
false empty (`themes.py` warning `below_gate_evidence`; prod case CO
election-legitimacy 0/44; CLAUDE.md 2026-06-12). (3) **Precise person→thread
relation**: `GET /api/v2/threads?person=` filters to threads a person appears in
via the full signal `persons` array — `thread_matches_person`
(`thread_intelligence.py:1140`, 6 tests): atlas threads match by a lightweight
person→topic-slug SQL that never touches the main THREADS spine, dynamic/emergent
fall back to `top_entities`; prod smoke person=trump → 24/39 matched, catching a
"Disease outbreak" thread the capped `top_entities` heuristic missed (CLAUDE.md
2026-06-24, Paper 4 ablation territory).

**Product evidence accrued (2026-06-26, L2 deep review — alert↔evidence
reconciliation):** the L2 console review
(`docs/specs/2026-06-26-l2-deep-review.md`) traced end-to-end on Côte d'Ivoire
(CI) the precise failure this paper's evidence-sampling thesis must defend, and
the product shipped the honesty fix. **The split-brain (RQ touched: does the
thread contract sample evidence honestly under the gate?):** the alert layer
(country volume anomaly: CI 238 signals at 26.4× a 9-signal baseline) and the
evidence layer (`/threads?country_code=CI` returning 4 rows of 1–2 raw
assignments) are computed by unrelated pipelines and never reconcile, so the
console routed a real volume spike into a single-source, gate-failed, positive,
irrelevant "Flood and landslide disaster" thread (`total:0 / rawTotal:1`, served
below-gate as one Spanish beach-tourism article, sentiment +0.385) and presented
it as the lead "critical" story — four correct-in-isolation components wired so
their disagreements surfaced as product. The shipped fixes are the measurable
honesty results: **(1) #214 one-count semantics** — the country thread list CTE
now carries `gated_signal_count` / `gate_scored_count` (the gate-kept count the
detail already served), CountryBrief shows the GATED number with raw on hover,
and scored-but-zero-kept threads split into a labeled **UNVERIFIED `<details>`
tray** (prod-verified CO "Armed conflict" 39 raw → 12 shown; "Election
legitimacy" 36/0 → tray) so list and detail finally agree (CLAUDE.md 2026-06-26
B2, `60dce84`). **(2) Positional "critical" killed (B1)** — spike bars no longer
paint on `i===0` (the first raw-count row), so a country volume spike no longer
falsely marks an arbitrary thread critical (`8395b63`); "elevated" must come from
the thread's OWN movement/coherence, not the country's volume. **(3) Thread KEY
SUBJECTS now use `rank_key_people`** (syndication-resistant, corroboration floor)
instead of bare `_is_valid_person`, killing single-signal "ocean atlantic"-class
noise (GDELT NER mangling "Atlantic Ocean" into a PERSON) from the thread packet
(`04d8f0a`, B3). This is the paper's evidence-sampling claim made honest on the
production surface: the below-gate fallback (which serves raw signals labeled
UNVERIFIED when the gate clears 0 but raw>0, the 2026-06-12 `below_gate_evidence`
mechanism) is now demoted out of the lead/critical slot into an explicitly-marked
tray rather than masquerading as the country's verified narrative. Note: the deep
review re-confirms the leak is downstream of P1's gate-recall-on-non-English
problem (CI's spike is French/`xx` local press the English-biased lexical gate
can't score) — a Paper-1↔Paper-4 dependency the discussion section should state.

**Evidence to collect:**
- Thread-level benchmark (sample 30 threads; LLM annotator scores
  each against the 7 questions; compare to analyst judgement).
- Evidence-role accuracy per thread.
- Syndication detection precision.
  - **2026-06-29 live failure + proposed metric** (spec
    `docs/specs/2026-06-29-...-syndication.md` §4): `dynamic-topic-262`
    "Las Vegas Travel Guide" ranked **#0** at 24h — ONE travel article reprinted
    across ~25 Australian Community Media `.com.au` papers (135 serving-count
    signals). The 3-term ranking has no diversity term; log-damping is
    volume-blind to copy-vs-original. Proposed:
    `headline_diversity = distinct_normalized_headlines / total_signals`.
    **2026-06-29 UPDATE — this metric was DISPROVEN by measure-first** (audit
    `scripts/syndication_audit.py` + raw-corpus SQL; artifacts
    `docs/research/syndication/`): of 506 high-reprint headline groups in 24h, 95%
    are clean independent wire, and real news ("Iran attacks Bahrain", 116
    reprints/115 domains) is structurally IDENTICAL to filler ("sausage rolls
    healthier", 92/92) — diversity/domain-count cannot separate importance, and
    owner-network fronts (Las Vegas ×25 `.com.au`, one owner) post once per domain
    so they look like legit wire. A diversity penalty would false-demote real
    news. **The negative result is itself a paper finding** (syndication structure
    ≠ news value). Replaced by: (a) single-domain-boilerplate demote (high reprints
    from 1 domain = template junk, ~4%); (b) editorial-lane demote — the real
    "Las Vegas Travel Guide ranks #1" cause is LIFESTYLE/SPORT low news value, not
    syndication, fixed by applying the #177 stream-lane classifier to thread
    ranking.
- Confidence-band calibration.
- Ranking-weight ablation: vary the 0.45/0.35/0.20 split and the log-damping,
  measure analyst-judged top-k thread quality (weights are explicitly v1 /
  calibratable). **2026-06-29: the proposed 4th `headline_diversity` term is
  withdrawn (disproved above); the editorial-lane term (#177) is the candidate
  4th input instead.**
- person→thread recall/precision of `?person=` (full-array match) vs the
  `top_entities`-capped heuristic on a labeled set.
- Alert↔evidence reconciliation (#214): on a sample of anomalous countries,
  measure how often the volume-anomaly lead thread is below-gate / single-source
  vs gate-passing, before and after the gated-count + UNVERIFIED-tray fix —
  i.e. the rate at which "critical" was a sampling artifact. Pair with a
  list↔detail count-agreement check (gated vs raw across the two surfaces).

**Target venues:** ICWSM main, EMNLP industry, CSCW.

---

### Paper 5 — Sentiment fusion and multilingual NLP calibration

**Status:** seed. Implementation in
`backend/app/services/sentiment_fusion.py`. Pre-agg coverage in
mig 025, 026, 033.

**Core claim:** Confidence-weighted fusion of GDELT V2Tone and an
XLM multilingual transformer is more faithful to human sentiment
judgement than either source alone. The calibration constant
`NLP_SENTIMENT_SCALE = 2.37` is empirically derived from per-source
stddev measurements and is the right baseline for downstream UI
thresholds.

**Evidence available:**
- 70.8% sign agreement between transformer and GDELT V2Tone.
- 29.2% disagreement, with lexicon weaker than transformer.
- Per-bucket `nlp_signal_count`, `avg_nlp_sentiment`,
  `nlp_sentiment_weight_sum`, `nlp_confidence_sum`.
- Three sentiment sources exposed: `gdelt`, `nlp`, `nlp_weighted`.

**Product evidence accrued (2026-06-25):** the multilingual-NLP claim now has a
deployed configuration AND an honest, measured infra limitation the paper should
state as a finding. (1) **Sentiment runs as a fast lane** and reaches ~100%
coverage on served signals (`nlp_sentiment` 100% in measured windows), while
**NER lags far behind** — measured `3.9%` `nlp_persons` coverage, ~680/hr on the
Fly box vs ~7,000/hr ingest (24h lag). Root cause is structural: the
`nlp_worker` LOADs-RUNs-UNLOADs each heavy model per cycle to fit a 4GB box, and
that box co-hosts the e5 embed service in the same Python process — bumping NER
throughput starved the semantic lane (logged incident, CLAUDE.md 2026-06-25
#184). (2) Multilingual mode exists (`NLP_MULTILINGUAL_MODE`,
`cardiffnlp/twitter-xlm-roberta-base-sentiment`, `enrichment/nlp_pipeline.py`;
confirmed labeling new CJK/RU/FA signals when on). (3) NER was **moved to the M1
as a mindful launchd daemon** (`taskpolicy -b` → efficiency cores + nice, yields
to foreground work), lifting throughput to ~1.5-3.5k/hr while freeing the Fly box
for embed; hot-lane prioritises recent so served signals get NER'd first
(CLAUDE.md 2026-06-25). (4) **Key honest finding for the per-language section:**
multilingual NER was investigated and NOT enabled — `xx_ent_wiki_sm` extracts
Latin scripts fine but returns **nothing for Persian/Arabic/CJK** (exactly the
diversity gap), and the xlm sentiment tokenizer is broken in the M1 env
(transformers 5.8 / Python 3.14 mis-routes the SentencePiece tokenizer). So
non-English subjects stay **gazetteer-typed (honest, `unverified=true`)** until a
proper multilingual token-classification model + a working xlm env land. The
NER↔embed co-hosting and the non-Latin NER gap are real, reproducible system
constraints — not aspirational.

**Evidence to collect:**
- Human sentiment labels on a stratified sample (e.g., 100 headlines).
- Per-language accuracy breakdown (and per-language NER coverage, given the
  measured non-Latin NER gap — likely the headline limitation result).
- HTML entity decode impact ablation.
- `nlp_weighted` vs flat-AVG ablation on analyst-facing rankings.
- Throughput/coverage characterization: NER lag vs ingest rate, and the
  sentiment-fast-lane vs NER split as a cost/coverage trade.

**Target venues:** NAACL, EMNLP, *SEM (sentiment / semantics workshop).

---

### Paper 6 — Temporal model: hot vs cold storage, processed historical, time-bucketing

**Status:** seed. Specs:
`docs/superpowers/specs/2026-05-21-processed-historical-sync-design.md`
plus ADR-0004 NLP stratified sampling and `data-operating-roadmap`.

**Core claim:** A two-tier temporal architecture (hot 24h on
Supabase + cold archive locally + compact processed historical on
Supabase) preserves long-window analytical surfaces under strict cost
budgets, while keeping 15-minute bucket SLAs on the hot path. Bucket
granularity choices are justified per use case.

**Evidence available:**
- Hot/cold cutover: 2,128,070 rows archived, 18 days, $0 lost.
- `historical_topic_country_daily`, `historical_source_daily`
  compact tables.
- Live coverage reports.

**Product evidence accrued (2026-06-25):** the two-tier temporal contract was
made explicit and its serving consequences measured. (1) The **evidence-window
contract** is now a named spec capability (H): **hot ≤168h queryable / processed
aggregates / archive NOT queryable** (CLAUDE.md 2026-06-10 spec review) — the
boundary this paper argues for, written as a product guarantee. (2) The **hot
lane prioritises recent signals first**, so under throughput pressure (e.g. NER
behind ingest, #184) the most-served recent window is enriched first — a
deliberate freshness-over-completeness scheduling choice the paper can cite. (3)
The **cold archive was relocated to external disk** (`/Volumes/Ext/Atlas/Archive`,
`/Users/pedro/AtlasArchive` symlinked; runner exits if the volume is unmounted;
59 manifest dirs / 272 records / 3,947,759 rows verified, CLAUDE.md 2026-06-01) —
concrete tiering operations under cost budget. (4) The strongest new datum is the
**raw-vs-served coverage gap (#229)** — re-measured precisely 2026-06-30 (live
prod), which SHARPENS the old `~0.2%` funnel and adds a second dimension:
- **Coverage:** `534K` signals → `239K` embedded → only **`13,354` distinct
  signals in any topic = `5.6%` of embedded (`2.5%` of total)**. Per-country
  recall is **`<1%` even for the highest-volume countries** (US `24,709→136`/0.6%,
  CN `8,720→4`/0.0%, RU `7,036→10`). Bottleneck = **clustering ASSIGNMENT**
  (global HDBSCAN drops ~94% as noise), NOT embedding (239K done) or the promotion
  gate. The HDBSCAN purity/recall cliff is characterized (no global config gives
  both); the lever is **scoped passes** (spec
  `2026-06-30-atlas-engine-recall-scoped-clustering.md`, R0 probe written).
- **Dynamism — a measured before→after (FIXED; not a live negative — PR3.3).**
  *Before (2026-06-30):* the served topic set was **FROZEN** — `dynamic_topics`
  last updated 06-29 17:00 (the topic-forming cron was disabled in a 06-29 infra
  consolidation; the successor `unified-v2` built but was not served), and 54/68
  "active" topics had `last_seen` > 3 days (the lifecycle wasn't retiring). **A
  fixed topic count from a streaming feed is itself a failure signal.** Root cause:
  the M1 embed runner's fatal embed-step aborted the projection chain before topic
  formation. *After (shipped 2026-06-30 → 2026-07-01):* the emergent-snapshot former
  was revived mindful/off-peak and the embed step made non-fatal (P8 Intervention 1);
  R1 scoped clustering then WROTE **731 clusters over 126/126 countries** and, via a
  measured promotion-gate recalibration (`volume_min` 30→12, purity held: cohesion
  0.969 / noise 0.081 on the newly-admitted small topics), **served 68 → 392 active
  topics (~4.6×)**; a subsequent R3.7 retirement sweep dropped 44 wrongly-re-activated
  stale bootstrap topics to `deprecated`, settling serving at **348** (P8 Intervention 3,
  §"Retention + resurrection"). So "68 active topics" was the *frozen* count, not a
  live measure; the lifecycle now retires-from-serving while retaining rows for
  resurrection (Pedro's retention model). The coverage number likewise moved from
  the frozen-global 5.6% baseline toward the scoped ~26.7% system estimate (R1).
Both are **Paper 8's** result (`2026-06-30-paper-8-result-skeleton.md`: open-set
discovery = coverage + dynamism, published as a measured negative-before-fix — the
before AND the after now recorded).
This is also the temporal-tier analogue of what the hot window surfaces vs what is
retained — directly relevant to bucket/retention justification.

**Evidence to collect:**
- Query latency per bucket granularity.
- Cost per row across hot/cold tiers.
- Reproducibility of compact aggregates from cold archive.
- Hot-window recency-scheduling impact: enrichment coverage of the served window
  vs the full 168h hot window under throughput pressure.

**Target venues:** VLDB systems, CIDR, ICDE industry track, KDD ADS.

---

### Paper 7 — Visualization and analyst workflow for narrative intelligence

**Status:** seed. ADR-0005 Equal Earth pending. Workspace audit:
`docs/research/workspace-expert-audit.md`. UX iteration notes
under `docs/research/ux-video-evaluation/`.

**Core claim:** Specific visualization decisions (Equal Earth
projection, coverage badges, sentiment scaling, narrative-thread-first
panel layout, force-graph workspace) make Atlas measurably better at
the seven analyst questions than commodity dashboards.

**Evidence available:**
- Panel-by-panel audit
  (`docs/research/2026-05-24-app-panel-thread-audit.md`).
- Workspace expert audit.
- **Focus-propagation relation model (product, #234, 2026-06-13→25):** a focused
  entity (country / person / thread) re-scopes EVERY surface to its relations —
  map heat + camera fly, narrative-thread siblings, public-attention (wiki/
  trends/conflict), source-health — via a shared `computeFocusRelation`
  (`lib/focusRelation.ts`, `useFocusRelation`). Two measured method findings the
  paper can use: (1) **honest-by-construction** — when nothing relates,
  `relationActive=false` and surfaces stay global rather than fabricate or blank
  a relation. (2) **Rarity-weighted relation (2026-06-25):** naive entity-overlap
  for thread siblings LAUNDERS common actors — live measurement found one entity
  ("donald trump") in 14 of 30 concurrent threads, which linked every unrelated
  narrative (Pauline Hanson ↔ Venezuela Earthquake). The shipped relation counts
  only DISTINCTIVE entities (document-freq ≤ min(3, 25% of the list)) ORed with
  primary geography. This is the same volume≠importance principle as Paper 3's
  heat composite, transferred from intensity to relation — a citable
  cross-method result within the Atlas series. (`NarrativeThreads.tsx`; CLAUDE.md
  2026-06-24/25.)
- **Combined-honest Public Attention lane (product, L2 deep review, 2026-06-26):**
  the analyst-workflow "people-side proxy" surface was rebuilt to corroborate or
  contradict the press-side narrative honestly. Public Attention is now
  **Trends[S] + Wiki[W] + Forum[F]**, where the forum lane surfaces the
  `source_family='social'` (Reddit) signals Atlas already ingested but never
  exposed — `GET /api/v2/public-attention[?country=]` returns them labeled
  `verified=false` (never folded into gated evidence), and `source_family` was
  added to `/api/v2/signals` (CLAUDE.md 2026-06-26 C1/C2, `34e941d`/`e73fcc0`;
  mobile reachability via a 4th Pulse tab, `7ac10c6`). **Method finding the paper
  can use:** the lane is *interleaved with kind badges and a corroboration flag*,
  NOT a blended score — the kinds are not commensurable (a `de`-edition wiki
  spike is a German-audience signal, not local attention), so the analyst value
  is the *agreement across surfaces* ("searched + discussed + reported"), made
  explicit rather than averaged away. This is the same honesty discipline as the
  L1 reserved-gap-box / no-silent-blank thesis, transferred to a multi-source
  attention panel. Cross-ref: the forum/voice diversity it exposes is Paper 2
  source-quality substrate; the discovery value of the dark social layer is
  Paper 8.
- **Truncated narrative thread (product concept, spec in flight 2026-06-26):**
  the evolution of focus-propagation (#234) + signal-context. Entering from a
  SPECIFIC item (forum post / topic / person / event) should build an ad-hoc,
  scoped "truncated" narrative thread that shows which EXISTING living threads
  that item CONNECTS to — via semantic neighbors (signal_embeddings) + shared
  distinctive entities — rather than only aggregating a fresh bucket. RQ touched:
  *"how should a specific entity be related to the living thread set, honestly?"*
  The honesty constraints carry over from the rarity-weighted relation above
  (distinctive-entity overlap, not common-actor laundering) and the relation is
  presented as a typed, reason-chipped connection set, never a fabricated thread.
  This is the analyst-workflow method that turns the focus lens from "re-scope
  every surface" into "show me where this one item sits in the narrative graph."
- **Evolution graph as ENGINE-TRUTH view (Pedro's direction, 2026-06-30 — noted,
  build after R2):** the thread evolution graph should be fed by *the same
  substrate the engine/classifier eats* — the embedded signals entering the
  vector space + their typed `topic_members` membership — so it visualizes WHICH
  signals classified into this thread, in what ROLE (evidence / discussion / mood
  / movement), and HOW they relate in embedding space to *form* the narrative; as
  signals enter and fade the graph evolves over time buckets, and a larger thread
  is an **umbrella** (R2) whose children/sub-themes appear and drop across the
  window. **Honest correction of the current state:** today's
  `TemporalNarrativeGraph.tsx` is fed by signal *metadata* — country/person/source
  co-occurrence + related-GDELT-`theme` links (`temporalNarrativeGraph.ts:176`)
  from one theme's signals — NOT the embedding substrate or `topic_members`. So
  this is a **reframe/upgrade, not a description of what ships**: make the graph an
  engine-truth view (semantic-neighbor edges from `signal_embeddings`, typed
  membership nodes, `splitting`/`merged`/`fading` lifecycle states, umbrella→child
  hierarchy) instead of a parallel metadata proxy that can *disagree* with the
  engine. **Method value the paper can claim:** a visualization fed by the
  classifier's own substrate is *falsifiable against the engine* — the analyst
  sees the actual basis of the thread (what is evidence vs discussion, which
  cross-country children sit under the umbrella, what entered/left this window),
  not a proxy. Ties to R2 (centroid-of-centroids umbrella), `topic_members` roles
  (Paper 4), and on-demand any-window construction (Paper 4 decision 5,
  2026-06-23). Constraint: the current force-graph is desktop-only
  (`ThemeDetail.tsx:744` `!isMobile` — off by design, a canvas doesn't rank on a
  phone); the engine-truth reframe needs a mobile-native shape (#236).
- **Orbital Thread View — the engine-truth reframe SHIPPED as a solar system
  (L11/E2, prototype 2026-07-02; spec `docs/specs/2026-07-02-orbital-thread-view.md`):**
  the evolution graph was replaced by a 2D radial "story system" where every
  visual degree of freedom maps to a MEASURED engine quantity — **orbit radius =
  semantic distance** (member `signal_embeddings` ↔ `dynamic_topics.centroid_vec`
  cosine, min-max normalized per thread; computed mean-of-members centroid for
  atlas topics, labeled), **angular velocity = interaction intensity** (a body's
  angle advances with its cumulative member signals up to the scrubbed time),
  **entry/exit = the time dimension** (invisible before `first_seen`; opacity
  DECAYS exponentially after last activity — the §I criticality-decay model,
  never a window cliff), **comets = transient participants** (presence span
  < 25% of the thread window — a visual class no list surface can show), size =
  volume, color = typed subject (person/org/place/event/country). **Method
  claims the paper can make:** (1) unlike the metadata-proxy force graph it
  replaces, the view is *falsifiable against the engine* — radius IS the
  classifier's own distance measure, so a body that looks misplaced is an engine
  finding, not a layout artifact; (2) motion is INTERACTION, not animation — all
  dynamics are driven by a time scrubber (deterministic layout per (bodies,
  scrub-t), pure functions in `lib/orbitalLayout.ts`, vitest-frozen), preserving
  the analyst's reading posture; (3) the acceptance metric is a TASK, not
  aesthetics — "who entered this story this week?" must be answered faster than
  from the signal list (the view carries an explicit entrants counter to make
  the comparison measurable). Evaluation pending (Pedro task-time pass on live
  threads); a Paper 7 contribution IF evaluated. Phase-2 concept captured in
  spec §7: the L3 Workbench as *universe builder* (investigation question at
  center, pinned items as captured bodies — same visual language, second
  consumer). E2 diagnosis fixed en route: the >24h processed-history branch
  swallowed `dynamic-topic-*` ids (dispatch-order bug, `b3fcfa79`) — every
  dynamic thread opened EMPTY at long windows; the old graph also silently
  hid on `graphSignals: []` payloads (`?? ` gate).

**Evidence to collect:**
- Analyst task-completion study (10-15 analysts, structured tasks).
- Public Attention corroboration study: when an item appears across ≥2 kinds
  (search + forum + press), do analysts rate the cross-surface-agreement signal
  as more useful than any single kind alone? Measure forum-lane coverage gain
  (how many CI-class countries with empty search/wiki get *some* people-side
  signal once `source_family='social'` is surfaced).
- Truncated-thread relation quality: do the item→existing-thread connections
  (semantic neighbor + distinctive-entity overlap) match analyst-judged "this
  item belongs to / relates to these narratives"? Ablate the DF threshold and
  the semantic vs lexical match basis (the current `LIKE '%word%'` trends/wiki
  join is language-blind — replacing it with embed-service similarity is the
  comparison).
- Relation-quality study: do rarity-weighted siblings match analyst-judged
  "related narratives" better than geography-only or naive-entity baselines?
  (The DF-threshold is a tunable the study can ablate.)
- Comparative dashboard (Atlas vs Google Trends + GDELT raw).
- Eye-tracking or click-stream where feasible.

**Target venues:** CHI, CSCW, IEEE VIS, InfoVis.

---

### Paper 8 — Open-set topic discovery and taxonomy evolution

**Status:** parking. Tied to BERTopic / dynamic topic modeling work
NOT yet started. This paper addresses Pedro's question about "new
buckets that could appear" — making the Atlas taxonomy adaptive
rather than manually curated.

**Core claim:** A semi-automated taxonomy evolution loop, combining
BERTopic clusters of unclassified signals with LLM-assisted naming
and human approval, expands the Atlas taxonomy without losing the
schema rigor of v2.

**Product evidence accrued (#229, 2026-06-25):** the open-set discovery funnel
is now instrumented end-to-end and the recall ceiling is measured. Prod, 24h:
174K ingested signals → 71K persisted embedding corpus → HDBSCAN over the corpus
yields only ~23 clusters/snapshot → ~50 stable served threads ≈ **0.2% of the
signal mass** *(denominator = served-thread signals ÷ ingested signals — the
coarsest funnel figure; the 2026-06-30 re-measure below reports **5.6% of
embedded / 2.5% of ingested**, a different and sharper denominator pair, PR3-08.
Both are "before" numbers, since superseded by the scoped-clustering lift — see
the SHARPENED block and the P8 result skeleton's Interventions 2–3)*; the
remainder stays HDBSCAN noise. Key result for this paper: the
bottleneck is **RECALL of the discovery step, not the promotion/approval gate** —
measured 0 candidates qualify-but-stuck, 150/181 candidates single-snapshot, 114
<30 signals; fast-tracking high-volume candidates would promote 0 topics. So the
open-set question is precisely "how many real narratives does clustering surface
from the unlabeled mass," and the levers are clustering-side: `min_cluster_size`
granularity, **scoped regional passes** (global HDBSCAN drowns regional stories —
documented case: the Peru vote-recount, 92 signals, never clustered), stratified
sampling. The persisted-corpus clustering (which dissolved the 15K hot-window
cap) is already shipped (`--from-persisted` cron); recall measurement on the full
corpus is the next experiment. (CLAUDE.md 2026-06-12 #229 / 2026-06-25.)

**Product evidence SHARPENED + a second dimension (2026-06-30) — see the result
skeleton `2026-06-30-paper-8-result-skeleton.md`:** re-measured on live prod with
exact queries. (1) **Coverage, sharper:** 534K signals → 239K embedded → only
**13,354 in any topic = 5.6% of embedded**; per-country **<1%** even at high
volume (US 24,709→136/0.6%, CN 8,720→4/0.0%). Confirms the bottleneck is
clustering ASSIGNMENT, not embedding/gate. Lever specced + R0 probe written
(`2026-06-30-atlas-engine-recall-scoped-clustering.md`); **since produced+served
by R1 — global 5.6% → scoped ~26.7% system estimate, 731 clusters/126 countries**
(P8 Intervention 2–3). (2) **dynamism — before→after, FIXED (PR3.3):** *before* the
served topic set was FROZEN (`dynamic_topics` last updated 06-29 17:00; the forming
cron disabled in the consolidation; 54/68 "active" topics >3d stale, the lifecycle
not retiring). **A fixed topic count from a streaming feed is itself a failure
signal** — open-set discovery is not just coverage but *dynamism* (topics
appear/retire with the world). Root cause (a fatal embed-step aborted the projection
chain). *After (2026-06-30 → 07-01):* the former was revived mindful/off-peak and
the embed step made non-fatal; the lifecycle now retires-from-serving while retaining
rows for resurrection; **serving went 68 → 392 → 348 active** (R1 gate recalibration
`volume_min` 30→12 with purity held, then the R3.7 retirement sweep). So Paper 8 now
has TWO measured negatives-before-fix (coverage + dynamism) with localized causes
and controlled interventions **whose after-state is now recorded, not just
scheduled** — the systems-paper contribution.

**Product evidence accrued (2026-06-26, L2 deep review — forums structurally
excluded from discovery):** the open-set funnel was found to throw away an entire
ingested source class, and the diagnosis pinpoints the mechanism. **Measured in
the DB: 0 of 71 forum (Reddit, `source_family='social'`) signals have any topic
assignment.** Root cause is structural, not a deliberate filter: the atlas-topic
classifier (`classify_topics.py`) matches on GDELT GKG themes
(`WHERE themes IS NOT NULL … JOIN ON s.themes && t.gdelt_theme_hints`), and forum
posts carry no GDELT themes, so they are excluded by construction from the
theme-hint discovery path. **~28 of the 71 forum signals DO have embeddings**,
which means the inclusion path already exists in the corpus: **semantic
membership** (embedding → nearest topic centroid over the persisted
`signal_embeddings` corpus), keeping forum posts labeled discussion / `verified=
false` and NEVER counted as gated evidence. This is squarely this paper's
question — open-set discovery over an unlabeled mass — extended to a second
*modality* (social/forum) that the lexical-theme path can never reach. It also
reframes the #229 recall ceiling: part of the "0.2% of signal mass surfaced"
loss is not just clustering granularity but whole source families that the
theme-join cannot see, recoverable only by the embedding path. (CLAUDE.md
2026-06-26 / `docs/specs/2026-06-26-l2-deep-review.md` §4.)

**Evidence to collect:** taxonomy-evolution loop itself (BERTopic + LLM naming +
human approval); recall vs `min_cluster_size` curve **(2026-06-29: partly
measured — see negative result below)**; regional-pass yield delta;

- **2026-06-29 NEGATIVE result (investigated, mapped — do not re-investigate):**
  spec `docs/specs/2026-06-29-atlas-engine-gdelt-decoupling-syndication.md`
  §4B.3/§4B.4, artifacts `docs/research/embedding-ablation/`,
  `scripts/embedding_input_ablation.py` + `scripts/cluster_recall_sweep.py`. Two
  cheap recall hypotheses DISPROVED on prod data: (1) enriching the e5 input
  beyond the headline (`+entities`, `+country`) buys ~1pp recall and `+country`
  over-clusters by geography (geo_purity ↑); (2) tuning HDBSCAN params is a
  cliff — `leaf` keeps purity 1.0 but shatters diverse coverage (Gaza
  best-cluster recall 0.04, ~70% to noise), `eom`/larger `min_cluster_size`
  hits recall 0.97 but as a **mega-blob** (modal Gaza cluster = 896/1074 rows at
  0.49 purity = the #224 black-hole). NO config has high recall AND high purity.
  → the recall ceiling is intrinsic to headline-only short-text density; the
  remaining lever is **scoped regional/topical clustering passes** (cluster
  within a coherent pre-filtered subset), the regional-pass yield-delta
  experiment above. Caveat: smoke sample was Gaza-heavy (~42%); a representative
  8000-row run should confirm the cliff (structure unlikely to change).
**semantic-membership recall for the forum/social modality** — how many of the
~28 embedded forum signals (and of newly embedded ones) attach to an existing
topic centroid above threshold, vs how many seed genuinely new discussion-only
clusters that the theme-hint path could never surface (the discovery-from-
unreachable-modality result).

**Target venues:** EMNLP, NAACL, ACL Findings, ICWSM.

---

## Recommended publication order

1. **Paper 1** (topic classification + distillation) — *the 2026-05-27 "closes
   4–8 weeks with current data + mig-042" estimate is superseded (PR3-07).* The
   mig-042 lexicon + 30-topic benchmark were overtaken by the unified engine and
   candidate-v2; Paper 1's two largest sections are now the **v1-vs-unified A/B**
   (the split-brain experiment, PASS-effective) and the **ensemble-κ 0.739 gold
   benchmark**. Close-criteria absorb the canonical regime (PR3.1), the A/B, the
   κ base, and the R3.1 crisis-only precision lift; the remaining gates are the
   still-UNBUILT experiments (`gdelt_hint_ablation.py`, crisis-only κ split,
   temporal hold-out, ≥1 external baseline — PR3.4 / ledger PR3-05/09/10).
2. **Paper 5** (sentiment fusion) — uses LLM-as-annotator extension
   to provide gold; can land 8-12 weeks after Paper 1.
3. **Paper 4** (thread aggregation) — depends on Papers 1 + 5 to
   anchor the thread-level metrics on validated underlying components.
4. **Paper 3** (atlas heat) — requires per-component analyst study;
   can be done in parallel with Paper 4.
5. **Paper 2** (source quality) — broader infrastructure piece; can
   start anytime once cross-source coverage matrix is automated.
6. **Paper 6** (temporal model) — most "systems" feeling paper;
   targets a different audience.
7. **Paper 7** (visualization) — needs real analyst recruitment.
8. **Paper 8** (open-set discovery) — most ambitious; could become
   a thesis-level project.

## Master criteria

For any paper in the series to ship:

- Reproducible benchmark with stratified sampling.
- Statistical CIs (Wilson per-bucket, stratified bootstrap overall).
- Inter-annotator agreement (Cohen's kappa).
- Single-reviewer disclosure.
- Anchoring-effect measurement when LLM hints are used.
- Public artifacts in repo: scripts, schemas, labels, reports.
- Methodology section that another team could replicate.

## Open questions for the series

- Do we publish the full LLM-annotator dataset (256 rows) as a
  citable resource? Yes — recommend release on Zenodo with DOI.
- Do we open the Atlas Review browser tool as a public-domain
  labeling instrument? Pedro flagged this as future product
  interest; potential Paper 8 demo / system paper.
- How do we credit Sonnet 4.6 in author / acknowledgement sections?
  Standard practice: "model assistance" disclosure in methodology
  section, no co-authorship.

## Cross-reference index (product ↔ paper)

Updated **2026-07-01** (PR3.3 — appended the unified-engine F0–F4, the A/B result,
candidate-v2/κ-0.739, R0–R3, and the crisis-relevance lens; the index had lagged to
2026-06-26, which is itself a staleness-ledger trigger, PR3-06). Prior refresh
2026-06-26 with the L2 deep-review findings
(`docs/specs/2026-06-26-l2-deep-review.md`, which carries the full per-surface
paper-alignment table in its §5). Newest mappings on top:

| Product finding / surface | Paper(s) | Where folded |
|---|---|---|
| **R3 unification (2026-07-01, spec `2026-07-01-atlas-engine-r3-unification.md`):** one served population, `atlas_topics` collapsed to a `category` attribute; SPINE (stories) + orthogonal LENSES (entity/geo/source) + deferred typed-relation layer; anchored-emergent category level (crisis-32 = seed anchors, emergent super-clusters extend the set) | **P4** (hierarchy: category/event/story levels + typed membership) + **P1** (the anchored-emergent taxonomy is the successor to the fixed-32 benchmark) + **P7** (one topic view, all lenses re-scope) | R3 spec §1/§3; P4 spec `2026-05-24-living-narrative-threads.md`; P1 "Canonical benchmark regime" + "Taxonomy revision" |
| **R3.1 category typing (2026-07-01):** DeepSeek-primary typer (cosine seed-prototype FAILS — diffuse centroids, proven); 348/348 stories typed (182 crisis-anchored + 166 non-crisis honest-labeled, not suppressed); Path B local encoder = future $0 distillation | **P1** (typing precision = the crisis-only successor to 41.6%; the DeepSeek→local distillation loop) | R3 spec §3.1/§12; P1 "Reject GATE ≠ category TYPING" note |
| **Crisis-relevance as a LENS (2026-07-01, Pedro's correction):** `category` is the OPEN category for EVERY story (badge); `crisis_relevant` is a FLAG the analyst filters on, NOT a taxonomy divide — a World Cup is a narrative, not a "reject" | **P1** (open-set category space, not a closed crisis gate) + **P7** (relevance as an analyst lens) + **P8** (open-set principle) | R3 spec §12 "Crisis-relevance as a LENS"; P1 "Canonical benchmark regime" (open-set framing) |
| **R1 scoped clustering (2026-06-30→07-01):** per-country partitioned HDBSCAN dissolves the global recall cliff — global 4.94% → scoped 26.72% (~5.4×), 731 clusters/126 countries, no blob (cohesion 0.968); promotion-gate recalibration `volume_min` 30→12 served 68→392→348 active, purity held | **P8** (coverage lever — the measured before→after; ties to P5 voice: CN 0%→33% scoped) | P8 result skeleton Interventions 2–3; master-plan P6/P8 (past-tensed, PR3.3) |
| **R2 umbrella (2026-07-01):** complete-linkage @0.98 over active-topic centroids collapses cross-country duplication into geographic-event umbrellas (26 umbrellas / 55 children); single-link CHAINS → complete-linkage is the same-EVENT-not-same-THEME guard (in the algorithm, not the threshold) | **P8** (legibility before→after) + **P4** (event-parent hierarchy, the geographic axis of decision 3) | P8 Intervention 4; P4 spec (event levels) |
| **R3.7 retirement / lifecycle (2026-07-01):** `snapshots_since_seen` aging → active→deprecated→retired (retire from SERVING, keep the row for resurrection); fixes the frozen-68 negative (Pedro's retention model) | **P8** (dynamism sub-claim — the mechanism, not a timer) | P8 "Retention + resurrection"; master-plan P6/P8 (past-tensed) |
| **Unified Engine F3 A/B (2026-06-29):** v1-compat (split-brain) vs unified-v2 over the e5 substrate — v2 wins coherence 0.930>0.908, evidence-purity 100%>98.1%, black-hole 12.1%<19.0%, topics≥3 103>66; member-recall settled without human gold (v1's surplus = over-assignment); LLM-judge cross-check found shared-member on-topic only 40–52% → the dominant lever is TAXONOMY (#204), not the engine | **P1** (THE split-brain-vs-unified experiment; the label-drift confound in the judge) | P1 result skeleton "Split-brain → unified: the A/B result" + "LLM-judge cross-check" |
| **Unified Engine F0–F2 (2026-06-29):** typed `topic_members` (mig 057, roles evidence/discussion/mood + F0.3 read-flag + LIST parity gate); F1 Bluesky+Lemmy forum ingest (social, `verified=false`); F2 social-seed clustering guard | **P4** (typed membership + relationship types) + **P8** (forum modality enters discovery via the embedding path) | P1 §"A/B"; P4 spec; P8 "forum modality" |
| **Canonical benchmark regime (2026-07-01, PR3.1):** ONE headline = 3-vendor N660 (Atlas 41.6% / LLM 78.6%); 50.79%/59.02%/scope-gate footnoted as N/panel/coverage variants; 78.6 vs 95.08 LLM split resolved as different gold sets (the label-drift confound) | **P1** (headline reconciliation) | P1 result skeleton "Canonical benchmark regime (PR3.1)"; staleness ledger PR3-01/PR3-07 |
| Taxonomy revision (#204): ensemble LLM annotation builds a 732-item gold base, Fleiss κ 0.739 (substantial); force-fit 30–46% → OUT_OF_SCOPE reject class; the taxonomy is the classification label space | **P1** (eval method + unconfounded benchmark + the precision-lift successor to 41.6%) | P1 result skeleton "Taxonomy revision — ensemble-κ gold benchmark" + the taxonomy methodology doc |
| Unified Engine F0 (2026-06-29): typed `topic_members` membership replaces the split-brain; 5 relationship types (`media/public/social-led, silent-risk, uncoupled`) from role-count ratios; read-flag + A/B parity gate before serving swap | **P4** (typed membership + relationship method) + **P1** (the v1-vs-unified A/B IS the split-brain experiment; silent-risk-as-ratio) + **P7** (press-vs-public in one topic view) | P4 spec `2026-05-24-living-narrative-threads.md` "Typed membership + relationship types (2026-06-29)"; P1 = the §11 A/B; serving = P7 |
| #214 one-count semantics (gated vs raw) + UNVERIFIED tray; killed positional "critical"; thread KEY SUBJECTS via `rank_key_people` | **P4** (primary), with P1 (gate is P1's result) + P3 (volume-as-importance leak) | P4 "Product evidence accrued (2026-06-26)" + new ablation in P4 "Evidence to collect" |
| Forums (`source_family='social'`) NOT in thread inference — GKG-theme join structurally excludes them; ~28/71 have embeddings → semantic-membership inclusion path | **P8** open-set discovery (new modality) | P8 "Product evidence accrued (2026-06-26)" + semantic-membership recall in "Evidence to collect" |
| Forums-as-discovery-lane surfaced (`/api/v2/public-attention`, Trends+Wiki+Forum, `verified=false`, interleaved + corroboration flag) | **P7** (analyst workflow), cross-ref P2 (voice/source diversity), P8 (dark social weight) | P7 "Evidence available" + corroboration study in "Evidence to collect" |
| Truncated narrative thread (item → ad-hoc scoped connections to existing threads; evolution of #234 + signal-context) | **P7** (analyst-workflow method) | P7 "Evidence available" + truncated-thread relation-quality study in "Evidence to collect" |
| Alert↔evidence split-brain (volume anomaly never reconciled with thread gate) — the cross-cutting CI failure | spans **P1/P3/P4/P5** (the "verified, gated, importance-ranked ≠ GDELT volume" thesis) | recorded in P4 split-brain note; the leak is downstream of P1 gate-recall-on-non-English |

**Unassigned findings (no clean paper home yet):** none from this session — all
four 2026-06-26 findings mapped cleanly (forum-modality → P8, Public Attention +
truncated thread → P7, count semantics → P4). The L2 legibility items (deselect
chip, single-source-of-truth country select, scope strips) are UX hardening, not
a paper claim; they touch P7's legibility surface only and are tracked in the L2
spec, not promoted to the paper track.

## Next action

Update `2026-05-27-methodology-paper-outline.md` so that it is
explicitly labeled "Paper 1 of the Atlas methodology series" and
references this master plan as the framing document.
