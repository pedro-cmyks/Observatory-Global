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

**Evidence to collect:**
- Thread-level benchmark (sample 30 threads; LLM annotator scores
  each against the 7 questions; compare to analyst judgement).
- Evidence-role accuracy per thread.
- Syndication detection precision.
- Confidence-band calibration.
- Ranking-weight ablation: vary the 0.45/0.35/0.20 split and the log-damping,
  measure analyst-judged top-k thread quality (weights are explicitly v1 /
  calibratable).
- person→thread recall/precision of `?person=` (full-array match) vs the
  `top_entities`-capped heuristic on a labeled set.

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
**raw-vs-served coverage gap (#229)**: a measured funnel of `174K` ingested
signals/24h → `71K` persisted embedding corpus → ~23 clusters/snapshot → ~50
served threads ≈ **0.2% of the signal mass**, with the bottleneck identified as
clustering RECALL (not the promotion gate); the persisted-corpus clustering that
dissolved the 15K hot-window cap is shipped (`--from-persisted` cron every 6h;
CLAUDE.md 2026-06-12 / 2026-06-25). This is the temporal-tier analogue of what
the hot window can surface vs what is retained — directly relevant to bucket and
retention justification (shared substrate with Paper 8's open-set funnel).

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

**Evidence to collect:**
- Analyst task-completion study (10-15 analysts, structured tasks).
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
signal mass**; the remainder stays HDBSCAN noise. Key result for this paper: the
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

**Evidence to collect:** taxonomy-evolution loop itself (BERTopic + LLM naming +
human approval); recall vs `min_cluster_size` curve; regional-pass yield delta.

**Target venues:** EMNLP, NAACL, ACL Findings, ICWSM.

---

## Recommended publication order

1. **Paper 1** (topic classification + distillation) — closes 4-8
   weeks from today with current data and migration 042.
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

## Next action

Update `2026-05-27-methodology-paper-outline.md` so that it is
explicitly labeled "Paper 1 of the Atlas methodology series" and
references this master plan as the framing document.
