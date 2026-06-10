# Research Workflow + Workbench Investigation Spec

**Date:** 2026-06-09  
**Status:** active design target  
**Branch:** `v3-intel-layer`  
**Related:** #213 Research Workflow, #207 Living Narrative Threads, #175 Search,
#177 Signal Stream, #173 Evidence Route, #168 Public Attention Threads,
#172 Silent Risk, Workbench,
`docs/specs/2026-05-25-atlas-narrative-intelligence-framework.md`
**Roadmap:** `docs/roadmap/2026-06-09-research-workflow-roadmap.md`

## Changelog

- **2026-06-10:** Amendments from the implementation review
  (`docs/specs/2026-06-10-research-workflow-spec-review.md`), applied after
  Phases 0.5/1a/1b shipped. Sections below are edited in place (no further
  "correction layer" pattern): ranking-weight seeding (D1), relevance gate +
  guardrail restated (D2), movement-signal provider (D3), walkthrough fixture
  scope (D4), capability G source credibility (P2), pin-event logging in
  Phase 2 (P3), evidence-window contract (B1), public-discussion coverage
  self-description (B2), durability language (B3), #213 exit criterion (S2).
  Kalman promotion to a movement feed approved by Pedro 2026-06-10 — as a
  movement provider only, never as a semantic classifier.
- **2026-06-10 (second pass):** funnel/maturity/positioning analysis folded
  in (`docs/research/2026-06-10-funnel-maturity-and-positioning.md`,
  approved by Pedro): serving-maturity tiers added to capability H; new
  Pipeline Funnel Principle ("gates decide what Atlas volunteers, not what
  it can find when asked") with funnel observability ledger + second-chance
  retrieval folded into Phase 1.5 scope; new Measurement Provenance
  Principle — benchmark/paper numbers are method-dependent estimates, every
  product-gating number gets an alternate-method probe on the route.
  "Why Atlas vs Google" positioning lives in the analysis doc; the
  forcing-case web baselines are the standing Google-comparison control
  group.

## Product Review Correction

Pedro clarified the core product shape on 2026-06-09:

- Atlas should not present this as "search builds a finished dossier."
- The user should investigate naturally inside Atlas, the way they would across
  the open web: search, open a country, open a thread, inspect sources, compare
  frames, follow related branches, and pin useful pieces.
- Workbench is the investigation memory and organizer that emerges from those
  actions. It is not the required starting point and not a magical final answer.
- A dossier/report can be generated later from the pinned route, but it is the
  output of the workflow, not the first response.

Correct product frame:

```text
search -> anchors/options -> open existing Atlas surfaces -> pin useful items
       -> suggested next branches -> Workbench graph/trail -> optional report
```

Wrong product frame:

```text
search -> finished dossier
```

## Scope Corrections (2026-06-09 review)

A build-readiness review tightened scope. These corrections override looser
language elsewhere in this spec; where any section disagrees, this section wins.

### Honest framing of what Phase 1 fixes

The forcing-case `0 signals` result is a **retrieval** failure, not a parsing
failure. `Iran climate water drought` returns nothing because the evidence is
missing the English words or is cross-language (Persian/Arabic/etc). A
deterministic expansion dictionary alone does not bridge that gap.

Therefore:

- Phase 1's real win is **anchor surfacing through the thread / country /
  public-attention lanes** (which already return `flood-landslide-disaster--ir`,
  `armed-conflict-escalation--ir`, etc.), not signal-level recall.
- Signal-level recall for natural queries stays partly broken until the semantic
  (embedding) lane and cross-language/source work land.
- Do not let any acceptance criterion claim Phase 1 solves signal-level recall.

### Embeddings are near-term, not "future"

`e5-base` already runs locally for the emergent-cluster snapshot. Reuse it for
query↔thread and query↔evidence similarity. The semantic lane is **Phase 1.5**,
not an indefinite "future semantic index". It is the actual fix for over/under
recall (Open Problem 1) and the main near-term lever for cross-language matching
(Open Problem 2).

### list/detail reconciliation is a prerequisite bug

`flood-landslide-disaster--ir` shows list `133` / detail `0` today. If a user
opens a suggested anchor and gets `0`, trust dies immediately and the whole
"anchors you can open" promise fails. This is a **pre-existing correctness bug**,
small scope, independent of this feature. Fix it as its own issue **before**
Workbench (Phase 2) relies on counts. Section F still defines the contract; this
correction only changes ordering and ownership.

### Reddit / public-discussion lane is DB-served by default

`ingest_reddit.py` already persists Reddit signals to Postgres. The default
public-discussion lane must read **ingested** Reddit rows, not fetch the public
API at query time. Live fetch (2s/subreddit × many subreddits) blows the
10-20s budget and puts public-API rate limits and reliability in the hot path.
Live/on-demand fetch is allowed only as an explicit, user-triggered deep action.

### Ranking needs weights and normalization

`investigative_score` (below) is not an equal-weight sum. Each component is
normalized to `[0, 1]` and multiplied by a tunable weight from config.

**Amended 2026-06-10 (D1/D2):** weights are NOT seeded from the #154
source-quality audit — source metrics inform at most `source_actor_value` and
`noise_risk` and cannot trade `intent_match` against `evidence_strength`.
Weights are calibrated by the constraint-satisfaction harness
(`backend/scripts/calibrate_research_ranking.py`) against gold ordering
constraints derived from this spec's acceptance criteria plus live
forcing-case constraints; normalization midpoints are calibrated from live
thread distributions. Report:
`docs/research/ranking-calibration/2026-06-10-ranking-calibration.md`.
Additionally, a multiplicative **relevance gate** (`0.5 + 0.5·intent_match`,
exposed per anchor in `ranking_explanations`) prevents large fast-moving
threads with no intent match from burying the actual query match. The
guardrail is therefore restated: `geo_entity_fit` and `movement_signal` must
not dominate `evidence_strength`/`answerability`; `intent_match` may lead
because the gate makes it the load-bearing usefulness axis. Rerun the
calibration when data shifts or when real user relevance judgments (Phase 2
pin-event log) become available.

### Workbench persistence: localStorage first

v1 Workbench is **client-side localStorage**. This ships Phase 2 (pinning,
sidebar/history, route) with zero backend migration. Promote to Postgres
(`investigation_session` / `workbench_pin` tables) only when multi-device or
sharing is needed. The `POST /api/v2/workbench/*` endpoints below are the
forward-compatible target, not a Phase 2 blocker.

### Caching and Phase 1 split

- `POST /api/v2/research/plan` is cached in Redis (~2 min) keyed on
  normalized-query + geo + hours, matching the existing unified-search cache
  convention.
- Phase 1 splits into **1a** (anchors from existing thread/country/
  public-attention surfaces, no ranking ledger — prove the forcing case) and
  **1b** (ranking, weights, reason codes, downranking ledger, gaps).

### Frame comparison is best-effort early

Rule-based frame extraction over multilingual text is noisy. The who-says-what
matrix and frame comparison (Steps 4-5) are **best-effort / manual-assist** in
early phases. Workbench usefulness must not be gated on automatic frame labels;
real frame quality is Phase 4.

### Movement signal source: Kalman state pilot

**Amended 2026-06-10 (D3):** the v1 `movement_signal` provider is
`changed_10h`/`trend` from thread rows — this is what Phase 1b shipped. The
read-only Kalman state pilot
(`backend/scripts/dynamic_topic_state_report.py`, model
`kalman-state-v0-readonly`) produces per-thread `velocity`, `surprise`,
`uncertainty`, and `trend` and is the **approved v2 provider**: Pedro
green-lit (2026-06-10) promoting it from a manual report into a persisted
movement feed (cron writes state estimates; the ranking reads them as the
movement hint). Scope of that promotion is strictly **movement provider** —
it never classifies topics, never promotes/suppresses semantic threads, and
`lifecycle_state` stays separate from `state_estimate`. Tracked as its own
issue; not a Phase 1.5/2 blocker.

### Evidence modality, not a satellite relation type

`reported_by_satellite_imagery` is too specific as a graph relation. Model
evidence modality (`osint`, `imagery`, `actor_claim`, `media_report`) as an
attribute on `evidence_item`, not as a relation type.

### Acceptance is an automated fixture

"Useful anchors" must be measurable. The Iran walkthrough fixture becomes an
automated test: the forcing-case query returns at least N anchors, and at least
one anchor opens to non-empty thread/country detail. Assert in CI, not manual
smoke.

## Terminology Correction: Threads and Dynamic Topics

Pedro also clarified that `dynamic_topic` and `thread` should not be treated as
different product concepts.

Plain-language meanings:

- **Thread:** a thread is a hilo: a connected line of events, sources, claims,
  places, actors, and evidence that can be followed over time.
- **Dynamic topic:** a dynamic topic is a tema dinamico: a topic-like identity
  that changes as new evidence arrives, persists across snapshots, and can grow,
  split, merge, fade, or retire.

For Atlas product purposes, these are the same thing:

```text
dynamic_topic = implementation record for a living Narrative Thread
thread = user-facing product contract for that same living topic
```

The current separation exists for historical/technical reasons:

1. `atlas_topics` began as a static internal anchor taxonomy.
2. `emergent_clusters` then found raw evidence clusters in each snapshot.
3. `dynamic_topics` was added as the persistence/lifecycle layer that links
   clusters across snapshots into stable identities.
4. `/api/v2/threads` was created as the user-facing contract that exposes those
   identities as Narrative Threads.

That means `dynamic_topics` should not appear in product thinking as a separate
kind of thing from threads. Search, Workbench, Country Focus, Brief, and
ThreadFocusPanel should reason over **threads**. Internally, the best current
source for those threads is often the `dynamic_topics` table.

Correct product vocabulary:

- "Open this thread."
- "Pin this thread to Workbench."
- "This thread is active/candidate/fading."
- "This thread is backed by `dynamic_topics`."

Incorrect product vocabulary:

- "Open a dynamic topic" as if it were separate from a thread.
- "Existing threads / dynamic topics" as two peer lanes.
- "Topic" as the visible user-facing taxonomy when the object is actually a
  living thread.

## Objective

Atlas search should let a user type a natural investigation question and begin a
guided research workflow inside Atlas. Search should return useful anchors,
related thread options, pin candidates, and next-step suggestions. As the user
opens and pins those items, Workbench should accumulate a structured
investigation trail that can later become a report.

Target user job:

> "I want to investigate a developing topic, understand who is talking about it,
> what each actor/source is saying, what frames are competing, where the story is
> happening, what else it connects to, and how the story is evolving."

This is not a one-off Iran climate feature. The Iran case is the forcing
example for a general product capability:

- natural-language research intent;
- compound/multi-hop question expansion;
- evidence-backed Narrative Thread anchors;
- "who says what" source/actor matrix;
- frame comparison;
- coverage-gap detection;
- list-vs-detail reconciliation;
- Workbench handoff for pinned investigation memory.

The expected result is that Atlas stops losing the majority of relevant
information because the user's words do not exactly match the current signal
fields or topic slugs.

## Forcing Case

Initial user intent:

> "Noticias relacionadas con el clima en Medio Oriente, específicamente en
> Irán. Quiero saber quién habla de eso, qué dice cada quien, cómo evoluciona la
> historia, qué países están hablando, fuentes, actores, dónde se desarrolla, y
> por qué se está desarrollando ahora."

Expanded compound intent:

> "Además, quiero conectar eso con ataques a bases o infraestructura
> estadounidense/satelital/comunicaciones en Medio Oriente, otros países
> afectados, y cómo esa dimensión se relaciona con clima, agua, energía,
> infraestructura y guerra."

The correct Atlas interpretation is not a single keyword query. It is a
research graph:

```text
Iran climate
├─ water scarcity / drought / reservoirs / dams / Tehran rationing
├─ heatwaves / extreme temperatures / dust / public health
├─ agriculture / self-sufficiency / groundwater / food prices
├─ protests / governance / mismanagement / sanctions
├─ conflict damage to water/electricity infrastructure / WASH / disease risk
├─ regional water-energy-security spillovers
└─ US/allied bases and satellite/communications infrastructure
   ├─ Iran/proxy attacks on bases in Kuwait, Bahrain, Qatar, UAE, Saudi, Iraq
   ├─ radars, radomes, satellite communications, air-defense equipment
   ├─ commercial satellite imagery and evidence restrictions
   ├─ alleged Chinese/Russian targeting-support routes
   └─ links to energy/water infrastructure threats in the Gulf
```

## Web Investigation Baseline

Manual web research on 2026-06-09 found a coherent storyline that Atlas should
eventually reconstruct from its own data plus explicit external enrichment:

1. **Climate/water core.** Iran is under severe long-running drought and water
   stress. UNICEF frames this as climate risk for children and public health:
   hotter temperatures, reduced rainfall, water scarcity, heat waves, dust
   storms, floods, urban heat, energy demand, displacement, and child
   vulnerability.
2. **Tehran and reservoir crisis.** Al Jazeera frames the story through dams,
   rationing, possible evacuation, low precipitation, heatwaves above 50C,
   agriculture consuming most water, poor management, sanctions, and local
   experts.
3. **Security and governance.** WRI frames the same crisis as water bankruptcy:
   climate plus unsustainable water use, groundwater depletion, agriculture,
   dams, subsidence, protests, food security, energy, health, and conflict.
4. **Humanitarian/WASH.** ACAPS frames conflict damage as compounding the chronic
   water crisis: damaged water infrastructure, electricity cuts affecting
   pumping, displaced people in water-stressed areas, waterborne disease risk,
   food inflation, and strained health systems.
5. **Political stability.** The Guardian frames water shortages as a backdrop to
   protest and regime pressure: day-zero risk, pressure cuts, demands for water
   and electricity, and climate breakdown plus mismanagement.
6. **Regional conflict infrastructure.** Recent reporting and OSINT analysis
   connect Iran conflict escalation to attacks on US/allied bases and
   communications/radar/satellite-linked infrastructure in Kuwait, Bahrain,
   Qatar, UAE, Saudi Arabia, Iraq, and Jordan; commercial satellite imagery
   becomes both evidence and contested infrastructure.

## Second Forcing Case: Claim Verification

The first forcing case (Iran climate/water) tests **topic research**. A second,
equally important case tests **claim verification** of a viral narrative. This is
the case a normal user actually hits: they see a striking claim on social media
and want to know if it is true, who is saying it, and why now.

### User intent

> "Vi en redes que en Irán volvió a llover porque atacaron unas bases con
> estaciones de microondas que calentaban la atmósfera y manipulaban el clima.
> ¿Es verdad? ¿Quién dice esto, por qué, y después de qué?"

The user does not know the "correct" query. They might type `manipulación de
clima Irán`, `por qué llovió en Irán`, `rain theft Iran`, `weather weapon Iran
base`, or nothing precise at all. The workflow must turn vague/fringe phrasing
into anchors, not a dead end, and must verify rather than amplify.

### Web investigation baseline (claim verification)

Manual web research on 2026-06-09 characterizes the narrative Atlas should be
able to reconstruct and label:

1. **Observable event (real).** Late-April 2026 brought unusual heavy rain,
   record snowfall, and cooler temperatures across Iran and neighbors, breaking a
   long drought.
2. **The viral claim (unverified).** Iranian social media, amplified by Iran's
   embassy in Kabul (Apr 21, 2026), claimed the weather changed because Iran
   destroyed US radars and Israeli/Emirati "weather-engineering" / cloud-seeding
   infrastructure (THAAD, AN/FPS-132 radar in Qatar, an alleged UAE weather
   center). Low-credibility outlets (Global Research, planet-today, needtoknow)
   echoed it as fact.
3. **The contradiction (authoritative).** Iran's own Meteorological Organization
   rejected the "rain theft" claim. Meteorologists attribute the rainfall to jet
   stream shifts, regional synoptic patterns, and climate variability. NOAA,
   RMIT, and AAP fact-checks establish that HAARP-style ionospheric heaters
   cannot control surface weather: the energy is orders of magnitude too small
   and acts 50-1000 km up, far from where weather forms.
4. **Why now / after what.** The causal claim is post-hoc: it attaches to two
   real events (the drought breaking + strikes on bases/radars) and serves a
   political/morale frame.

### What this case demands of the product

This case is the acceptance test for the harder spec capabilities:

- **Public-discussion lane as origin, not evidence.** The claim lives first on
  social media; Atlas must show it as public attention/narrative spread, clearly
  not as verified fact (Reddit/forum/social guardrail).
- **`contradiction` evidence role.** Iran Met Org and NOAA/RMIT/AAP rebuttals
  must surface as first-class contradicting evidence, not be buried.
- **`unsupported_claim_adjustment`.** The weather-weapon causal claim is
  downranked-with-reason as an unsupported causal relation, never silently
  dropped (the user may be investigating the claim itself).
- **Source credibility labeling.** Low-credibility/conspiracy outlets vs
  national met agency vs scientific fact-checkers must be distinguishable in the
  who-says-what matrix.
- **Frame comparison.** At minimum: conspiracy/political-morale frame vs
  meteorological/climate-variability frame vs fact-check/debunk frame.
- **Movement + temporal "after what".** The claim spike must be locatable in time
  relative to the drought break and the base strikes.

### Product responsibility rule

```text
Atlas verifies and contextualizes claims. Atlas does not endorse or amplify them.
```

For a viral/fringe claim, the honest output is: the observable event, who is
making the claim and from what source family, what authoritative sources say,
the explicit contradiction, the unsupported-causal-link flag, and the
uncertainty. Atlas must never present taxonomy similarity or social virality as
proof the claim is true.

## Current Atlas Result

Production checks on 2026-06-09:

| Query / route | Result | Product meaning |
|---|---|---|
| `/api/v2/search/thread?q=Iran climate water drought&hours=168&country_code=IR` | `0` signals | Exact evidence query misses the research intent. |
| `Iran water shortage`, `Iran drought`, `Tehran water`, `Iran heatwave`, `Iran dams`, `Iran water crisis` | `0` signals | Natural query variants still miss. |
| `/api/v2/search/unified?q=Iran climate water drought&country=IR` | detects `IR`, suggests Climate/Water concepts but no signal matches | Search knows the idea at taxonomy level but cannot bridge it to evidence. |
| `/api/v2/threads?hours=168&country_code=IR` | returns threads such as `flood-landslide-disaster--ir`, `armed-conflict-escalation--ir`, `oil-gas-supply-risk--ir` | Atlas has relevant country activity, but it is not linked to the query intent. |
| `/api/v2/theme/flood-landslide-disaster?hours=168&country_code=IR` | `0` | List/detail contract mismatch. |
| `/api/v2/signals?hours=168&country_code=IR&sort=relevance` | signals returned, but mixed/noisy for the climate/water intent | Stream relevance is not intent-aware enough. |

Conclusion:

Atlas has relevant information, but search does not yet guide the user from a
natural question into the country/thread/source/evidence surfaces where that
information lives. Workbench also does not yet preserve the user's route as a
living investigation object.

## Product Principle

Search is not just retrieval. For Atlas, search must be an investigation
starting point.

The user should be able to start with:

```text
clima en Irán y relación con ataques a infraestructura estadounidense/satelital
en Medio Oriente
```

Atlas should first respond with:

- an interpreted research intent;
- anchor options the user can open;
- related Narrative Threads;
- country, source, actor, and public-attention entry points;
- pin candidates;
- gaps and uncertainty;
- suggested next branches.

Only after the user opens, filters, compares, and pins items should Workbench
show the accumulated graph/trail and optional report view.

The system must make uncertainty visible. It should not pretend it found
evidence when it only found taxonomy similarity or web context.

### Pipeline Funnel Principle (added 2026-06-10)

No Silent Filtering applies to the whole ingest→serve pipeline, not only to
the research plan. Measured 2026-06-10 (live 24h): 194,674 raw signals →
153,538 distinct headlines → 14,343 topic-assigned → 442 latest-snapshot
cluster members. Two different kinds of drop are mixed today and must be
separated:

- **deliberate precision filtering** (gates, noise rates, roundup rules) —
  working as designed, justified by measured precision (Paper 1);
- **capacity/coverage ceilings** (15K snapshot input cap, 7.4% classification
  coverage, 3.5% NLP coverage) — silent recall losses nobody chose
  per-signal. These are fixed by raising capacity (#185, #163/#164/#184,
  stratified snapshot sampling), never by loosening precision gates.

Governing rule:

```text
Gates decide what Atlas volunteers.
Gates must not decide what Atlas can find when asked.
```

Consequences: a funnel observability ledger (stage-by-stage counts with drop
causes — the pipeline-level twin of the research plan's downranking ledger),
and second-chance retrieval — research queries (Phase 1.5 semantic lane,
query-time enrichment #161) retrieve from the **full deduped corpus**, not
only the gated pool, with evidence labels carrying the quality verdict.
Analysis: `docs/research/2026-06-10-funnel-maturity-and-positioning.md`.

### Measurement Provenance Principle (added 2026-06-10)

The measured numbers this spec relies on (Paper 1 precision 41.6%, gate lift
41%→70%, student 78.2%/71.4%, the funnel counts above, the calibration's
21/21 constraints) are **method-dependent estimates, not law**. Each came
from one sampling strategy, one annotator process, one window, one
constraint set; a different method can legitimately produce a different
number. Rules:

- every number cited in this spec carries its method and date; re-measuring
  with the same tooling must be one command;
- before any number gates a product decision (e.g. "keep the precision gate
  at X"), the route includes at least one **alternate-method probe**:
  different sampling (stratified vs latest-N), different window, different
  annotator mix, or an ablation — Paper 1's own missing-evidence list
  (temporal hold-out, BERTopic/lex-only ablations) is exactly this and
  doubles as product validation;
- when an alternate method moves a number materially, the spec text is
  amended in place (changelog), not defended.

This is the same skepticism the ranking calibration already applied to this
spec's own guidance (the #154 weight-seeding claim did not survive contact
with implementation), turned into a standing rule.

## Search Architecture Principle

Atlas should learn from web search platforms without trying to become a general
web search engine.

The useful pattern is:

```text
prepare indexes ahead of time
-> retrieve candidates quickly
-> rank candidates by the user's intent
-> present navigable answers, not raw database rows
```

Atlas should not scan every signal at query time. It should query prepared
structures:

- thread index: `/api/v2/threads`, backed primarily by `dynamic_topics`;
- signal/evidence index: `signals_v2`, snippets, source, language, country,
  timestamp;
- entity index: people, organizations, places, infrastructure;
- source index: publisher, source family, language, geography, source lane;
- public-attention index: Wikipedia/search/social attention;
- historical processed index: longer windows and background volume;
- semantic index (Phase 1.5): `e5-base` embeddings for query/thread/evidence
  similarity. `e5-base` already runs locally for the emergent snapshot, so this
  is reuse, not new infrastructure.

The Research Plan API is the planner/ranker over these indexes. It should return
anchors because anchors are faster, safer, and more useful than pretending the
first query can answer the whole investigation.

## How People Search

Atlas should also learn from how normal users search, not only from how search
engines index data.

Research patterns to support:

1. **Berrypicking / trail following.** Users often do not know the final query
   at the start. They pick one useful result, learn a new term/person/place, and
   reformulate from there. Atlas should preserve that route as an investigation
   trail.
2. **Query reformulation.** Users repeatedly narrow, broaden, translate, add a
   country, add an actor, switch wording, or ask a question after seeing partial
   results. Atlas should treat reformulation as normal workflow, not failure.
3. **Exploratory search.** Research tasks often have uncertainty and no single
   known answer. Atlas should show anchors and next branches instead of forcing
   one final result.
4. **Social asking / public sensemaking.** Users often ask or inspect social
   spaces in addition to search engines. Reddit and similar forums should be
   modeled as public-attention / narrative-discovery lanes, not as verified
   evidence by default.
5. **Suggestion-guided search.** Google-style autocomplete uses real searches,
   language/web patterns, context, trends, and policy filters. Atlas can use a
   smaller version: suggest branches from query logs, current thread movement,
   related entities/countries, public-attention spikes, and Workbench pins.

Product consequence:

```text
search is not one query -> one answer
search is query -> anchors -> inspection -> reformulation -> pins -> route
```

## Investigative Usefulness Ranking

The strongest part of this feature is ranking by **investigative usefulness**.
Atlas should not rank only by text match or volume. It should rank anchors by
whether opening or pinning them helps answer the user's research question.

First-pass ranking model. Each component is normalized to `[0, 1]` and weighted
by a tunable config value `w_*`; adjustments are subtracted after weighting:

```text
investigative_score =
    w_intent      * intent_match
  + w_coherence   * thread_coherence
  + w_evidence    * evidence_strength
  + w_answer      * answerability
  + w_movement    * movement_signal          # from Kalman state pilot
  + w_source      * source_actor_value
  + w_geo         * geo_entity_fit
  + w_novelty     * novelty_or_gap_value
  - w_noise       * noise_risk_adjustment
  - w_unsupported * unsupported_claim_adjustment
  - w_mismatch    * list_detail_mismatch_adjustment
```

Weights live in config so ranking is tunable and reviewable. Do not ship an
equal-weight sum: it lets cheap-to-score components (`geo_entity_fit`,
`intent_match`) dominate the expensive-but-important ones (`evidence_strength`,
`answerability`). Start weights from the source-quality audit (#154) rather than
guessing.

Initial criteria:

| Criterion | Meaning | Current Atlas signal |
|---|---|---|
| `intent_match` | Does this anchor match the query terms, expanded concepts, country, entities, and branch relation? | Search parser, lexical match, concept expansion, future embeddings. |
| `thread_coherence` | Is the thread a coherent hilo rather than a roundup/grab-bag? | `dynamic_topics.noise_rate`, roundup gate, cohesion, representative label, member consistency. |
| `evidence_strength` | Does the anchor have real supporting evidence, not only taxonomy similarity? | signal count, sample evidence, retrieval lane, evidence-role classifier. |
| `answerability` | Which Atlas questions can this anchor answer now? | why-now, what changed, where, subthreads, sources, evidence, related threads. |
| `movement_signal` | Is the story moving recently or changing shape? | changed_10h, velocity, surprise, trend, first/last seen. |
| `source_actor_value` | Does it help answer "who says what"? | source diversity, actor extraction, voice mix, source-family lanes. |
| `geo_entity_fit` | Does it match the requested country/region/entity/infrastructure scope? | country_code, entity mentions, related countries, infrastructure terms. |
| `novelty_or_gap_value` | Does it reveal a drowned-out story, missing lane, or useful uncertainty? | public attention vs media mismatch, coverage gaps, silent-risk detectors. |
| `noise_risk_adjustment` | Is it likely off-topic, generic, syndicated, entertainment/sports, or roundup? | relevance lanes, noise rate, dedupe/syndication, blacklist/roundup rules. |
| `unsupported_claim_adjustment` | Does the anchor claim more than the evidence supports? | weak evidence role, context-only evidence, unsupported causal relation. |
| `list_detail_mismatch_adjustment` | Does list count disagree with detail/evidence count? | `/threads` vs detail vs signal sample reconciliation. |

This ranking should reuse the work already done in Atlas:

- evidence-role validation;
- dynamic-topic lifecycle and noise-rate gates;
- Kalman/state pilot as a movement hint only;
- Signal Stream relevance lanes;
- source-family and voice-mix work;
- public-attention and silent-risk direction;
- Path B/Paper 1 precision gates;
- list/detail reconciliation from the thread contracts.

The ranking output should be inspectable. A user or reviewer should be able to
ask: "Why did Atlas suggest this?" and see the contributing reasons, penalties,
and gaps.

### No Silent Filtering

"Penalty" must not mean hidden censorship or irreversible deletion. In Atlas,
these are **risk adjustments** and should be inspectable.

Default rule:

- Do not silently omit material that matches the user's investigation.
- Downrank or label risky/noisy material.
- Show why an item was downranked.
- Allow the user to open a "filtered / low-confidence / noisy" tray when useful.
- Preserve source provenance and retrieval lane.

Sports, entertainment, celebrity, and lifestyle items are often low-value for
geopolitical investigations, but they must not be blindly excluded. They can be
politically relevant when athletes, artists, influencers, clubs, or fan groups
participate in protest, sanctions, boycotts, national identity disputes,
military propaganda, or public-attention campaigns.

Example transparency payload:

```json
{
  "anchor_id": "signal-123",
  "visibility": "downranked",
  "reason_codes": ["sports_lane", "weak_intent_match"],
  "counter_signals": ["mentions protest", "mentions national team boycott"],
  "final_action": "show_in_low_confidence_tray",
  "user_message": "Downranked because this is sports coverage with weak climate/Iran match, but kept visible because it mentions protest."
}
```

Atlas should maintain an **omission/downranking ledger** for every research plan:

| Field | Purpose |
|---|---|
| `candidate_count` | How many candidate items were considered. |
| `shown_count` | How many were shown as primary anchors. |
| `downranked_count` | How many were moved to low-confidence/noisy trays. |
| `omitted_count` | How many were omitted entirely. |
| `reason_codes` | Why items were downranked/omitted. |
| `appeal_action` | How the user can inspect or restore a class of results. |

This is a product trust requirement. Good filtering is acceptable only when it
is documented, inspectable, and reversible for the investigation.

## Step-by-Step Atlas Investigation Workflow

### 1. Natural Research Query

The user starts with Search, not with a prebuilt dossier:

```text
clima Irán Medio Oriente agua sequía y ataques a bases estadounidenses satélite
```

Atlas creates an interpreted query card and entry-point menu:

```json
{
  "main_intent": "Iran climate-water crisis",
  "geo_scope": ["IR", "Middle East"],
  "time_scope": "recent + historical context",
  "subquestions": [
    "What is happening with drought, water shortages, heat, and reservoirs in Iran?",
    "Who is talking about it and how are they framing it?",
    "How does conflict damage water/electricity infrastructure?",
    "Which other Middle Eastern countries are connected by water, energy, bases, or shipping?",
    "What is the connection to US/allied bases, satellite imagery, communications, and targeting?"
  ],
  "expanded_terms": {
    "climate": ["drought", "heatwave", "water scarcity", "reservoirs", "dams", "WASH"],
    "conflict_infrastructure": ["US bases", "radar", "radome", "satellite communications", "air defense"],
    "regional": ["Kuwait", "Bahrain", "Qatar", "UAE", "Saudi Arabia", "Iraq", "Jordan"]
  },
  "anchor_options": [
    {"type": "country", "label": "Iran", "action": "open_country_focus"},
    {"type": "thread", "label": "Iran water/climate stress", "action": "open_thread"},
    {"type": "thread", "label": "Flood/disaster signals in Iran", "action": "open_thread"},
    {"type": "source_lane", "label": "Humanitarian / UN / NGO framing", "action": "inspect_sources"},
    {"type": "social_lane", "label": "Reddit and forum discussion", "action": "inspect_public_discussion"},
    {"type": "public_attention", "label": "Public attention around Iran + water", "action": "inspect_attention"},
    {"type": "related_branch", "label": "US bases / satellite / communications layer", "action": "add_branch"}
  ],
  "pin_candidates": [
    "country:IR",
    "thread:iran-water-climate-stress",
    "branch:us-bases-satellite-communications"
  ]
}
```

The user can open any anchor, pin it, ignore it, or add another query. Search
should generate threads/options, not force a single answer path.

### 2. Open Existing Atlas Surfaces

If the user opens `Iran`, Atlas should use the existing Country Focus surface. If
the user opens a thread, Atlas should use Narrative Threads / ThreadFocusPanel.
If the user opens a source lane, Atlas should use source and signal panels.
If the user opens a public discussion lane, Atlas should use Reddit/forum
signals as commentary and narrative-discovery evidence, not as verified factual
evidence by default.

The same investigation can begin from several paths:

- `Iran` -> country focus -> active threads -> pin water/climate thread.
- `climate in Iran` -> thread anchors -> open water/flood/heat threads.
- `Iran satellite bases` -> related-branch anchors -> inspect conflict
  infrastructure.
- `UNICEF Iran water` -> source lane -> inspect humanitarian framing.
- `Reddit Iran water` or `r/iran water crisis` -> public discussion lane ->
  inspect what communities are asking, amplifying, doubting, or linking.

Each surface needs the same core actions:

- `Pin to Workbench`;
- `Add as branch`;
- `Compare frames`;
- `Show evidence route`;
- `Show coverage gaps`;
- `Open related thread`.
- `Pin to current investigation`;
- `Save to new investigation`.

### 3. Pin and Build the Workbench Route

Workbench should appear as the user's investigation memory once the user pins or
adds a branch. It stores:

- pinned countries;
- pinned threads;
- pinned evidence rows;
- pinned sources/actors;
- user notes;
- relations between pins;
- coverage gaps;
- ordered trail of how the user got there.

Workbench should support multiple saved investigations, like a chat sidebar:

- one active investigation at a time;
- a sidebar/history of saved investigations;
- `New investigation` starts a clean route without deleting older pins;
- returning the next day should reopen the last active investigation or prompt
  the user to continue vs start fresh;
- pins from different investigations should not silently mix;
- a user can manually move/copy a pin from one investigation to another.

Example emerging Workbench graph:

```text
Iran climate-water crisis
├─ Water scarcity and drought
│  ├─ Tehran reservoirs and rationing
│  ├─ dams / aquifers / groundwater depletion
│  └─ agriculture and self-sufficiency water demand
├─ Humanitarian consequences
│  ├─ WASH and disease risk
│  ├─ food prices and livelihoods
│  └─ displacement / children / health
├─ Governance and protest
│  ├─ mismanagement frame
│  ├─ sanctions/economic capacity frame
│  └─ protest/stability frame
├─ Conflict and infrastructure
│  ├─ damaged water/electricity infrastructure
│  ├─ energy and water security in Gulf states
│  └─ international-law/civilian-harm frame
└─ US bases and satellite/communications layer
   ├─ strikes on bases / radars / communications
   ├─ satellite imagery as evidence
   ├─ targeting-support claims
   └─ regional countries hosting affected infrastructure
```

Each node is created from user action plus Atlas suggestions. A node can be
manually pinned, suggested by Atlas, or promoted from evidence.

Each pinned node has:

- evidence count;
- countries;
- sources;
- frame labels;
- representative evidence;
- confidence/coverage band;
- gaps.

### 4. Who Says What Matrix

For every pinned node or opened thread, Atlas should show:

| Source / actor | Type | What they say | Frame | Evidence role | Confidence |
|---|---|---|---|---|---|
| UNICEF | UN/humanitarian | Climate change worsens water, health, children, displacement. | child-rights / climate adaptation | background/context | high |
| Al Jazeera | media | Dams, rationing, agriculture, sanctions, mismanagement. | water crisis / governance | primary reporting + analysis | medium/high |
| WRI | think tank | Water bankruptcy; conflict can amplify scarcity into security risk. | water-security | analysis | high |
| ACAPS | humanitarian analysis | Conflict damage compounds WASH and disease risks. | humanitarian/WASH | analysis | high |
| Iran officials | state | Conservation, rationing, local management, emergency supply. | governance/response | actor statement | medium |
| OSINT/satellite reporters | investigative media | Damage to bases/radars/comms visible in satellite imagery. | conflict infrastructure | evidence/verification | medium |

This is the core "quién dice qué" object.

### 5. Frame Comparison

Atlas should compare frames instead of collapsing them into one summary:

| Frame | Claim | Supporting sources | Tension |
|---|---|---|---|
| Climate stress | hotter/drier conditions worsen scarcity | UNICEF, WRI, Al Jazeera | long-term driver, not full explanation |
| Mismanagement | dams, wells, agriculture, leakage, poor planning | Al Jazeera, WRI, Guardian | can be politicized |
| Conflict/WASH | strikes/electricity damage worsen water and disease risk | ACAPS, UNICEF, Guardian/WRI | needs event-level evidence |
| Protest/stability | water shortages feed unrest and political pressure | Guardian, WRI, local reporting | causality can be overclaimed |
| Military infrastructure | US/allied bases and communications become targets | AP, WaPo/OSINT, regional media | public imagery may be incomplete/restricted |
| Regional spillover | energy, food, shipping, desalination, Gulf security | ACAPS, WRI | broad but important |

### 6. Suggested Next Branches

Atlas should keep suggesting next research moves based on the current Workbench
state:

- "You pinned Iran water scarcity. Related country branches: Iraq, UAE, Qatar,
  Saudi Arabia."
- "You pinned conflict infrastructure. Related evidence lanes: bases, radar,
  satellite imagery, electricity/water infrastructure."
- "You have public attention but thin media evidence; inspect silent-risk gaps."
- "You have country-level evidence but no actor lane; inspect who is quoted."

The user decides what to add. Atlas should not auto-expand the investigation
until it becomes noisy.

### 7. Optional Report/Dossier View

Only after there is a meaningful pinned route should Atlas offer:

- Markdown/JSON export;
- report view;
- executive summary;
- timeline;
- who-says-what matrix;
- evidence table;
- gaps/uncertainty section.

The report is generated from Workbench state. It is not the first search result.

### 8. Coverage Gaps

Atlas must say what it cannot answer:

- "Atlas found climate/water taxonomy matches but no direct signal evidence for
  `Iran water shortage` in the selected 7-day window."
- "Atlas has Iran conflict and flood/disaster threads, but the theme-detail
  route returns zero for the country-scoped detail; list/detail reconciliation is
  required."
- "Atlas has no source lane for UN/NGO PDF analysis unless those sources are
  ingested or externally enriched."
- "Satellite imagery evidence may appear through media reports, not raw imagery;
  the system should label it as reported OSINT/media evidence."

Coverage gaps are not failures. They are part of the product if presented
honestly with next actions.

## Required Data/Model Capabilities

### A. Query Intent Parser

Input:

- raw query;
- optional selected country/person/source/theme;
- user-added branch/subquestion;
- current Workbench context.

Output:

- `main_intent`;
- `geo_scope`;
- `time_scope`;
- `topic_axes`;
- `entity_axes`;
- `infrastructure_axes`;
- `subquestions`;
- `expanded_terms`;
- `must_include`;
- `nice_to_have`;
- `excluded_noise`.

Implementation v1 can be deterministic + small LLM-free rules:

- country/entity extraction from existing search;
- phrase expansion dictionaries for climate/water/conflict/infrastructure;
- concept map used internally only, not as visible taxonomy;
- query variants per subquestion;
- explicit compound operators:
  - `AND`: climate + Iran;
  - `RELATED`: climate thread related to bases/satellite;
  - `EXPAND`: include water/drought/heat/WASH;
  - `COMPARE`: frames/sources.

### B. Evidence Retrieval Plan

The builder must run several retrieval lanes:

| Lane | Purpose | Sources |
|---|---|---|
| direct lexical | exact headline/theme/person/source match | `signals_v2` |
| semantic expansion | query terms to sibling concepts | internal expansion dictionary; `e5-base` embeddings (Phase 1.5) |
| threads | country/time thread candidates | `/api/v2/threads`, backed primarily by `dynamic_topics` |
| theme/detail | static and dynamic detail packets | `/api/v2/theme/*`, `/api/v2/threads/*` |
| signal stream | recent notable evidence | `/api/v2/signals` with intent-aware filters |
| public attention | wiki/search attention | existing public attention endpoints |
| public discussion | Reddit/forum/community narratives | `ingest_reddit.py`, subreddit search, future forum adapters |
| external context | web/manual enrich, only if enabled | explicit external source adapter |
| historical processed | broader background windows | processed historical tables |

The output must label each evidence item by `retrieval_lane`, so the UI can show
whether it is direct evidence, context, weak support, or external enrichment.

### C. Evidence Role Classifier

Every evidence item needs a role:

- `primary_event`;
- `direct_evidence`;
- `background_context`;
- `actor_statement`;
- `analysis`;
- `reaction`;
- `public_attention`;
- `osint_verification`;
- `weak_support`;
- `contradiction`;
- `noise`.

This should reuse the existing evidence-role validation direction. The research
thread builder should not treat all retrieved rows as equal.

### C2. Reddit and Public Discussion Lane

Reddit should be part of the research workflow because people often discuss,
question, amplify, and route narratives there before those narratives are fully
visible in formal news lanes.

Current Atlas already has `backend/app/services/ingest_reddit.py` for a fixed
set of subreddits, persisting rows to Postgres. The default public-discussion
lane must read those **ingested** rows, not call the Reddit public API at query
time (see Scope Corrections: 2s/subreddit × many subreddits breaks the latency
budget and puts rate limits in the hot path). Live/on-demand fetch is an
explicit deep action only. The scheduled ingest list should be extended to cover
the investigation's countries/topics:

- country subreddits: `r/iran`, `r/colombia`, `r/kuwait`, `r/AskMiddleEast`,
  `r/UnitedStates`, etc.;
- regional/global subreddits: `r/worldnews`, `r/geopolitics`,
  `r/CredibleDefense`, `r/MiddleEast`;
- topic subreddits where relevant: climate, energy, OSINT, defense, public
  health, migration, local politics;
- future forum adapters can follow the same contract if they are public,
  legal, and useful.

Important guardrail:

```text
Reddit/forum discussion = public attention, claims, questions, links, frames
Reddit/forum discussion != verified evidence by default
```

The lane should answer:

- What are people asking?
- What links/sources are being shared?
- Which claims are spreading?
- Which communities/countries are discussing it?
- Does public discussion reveal a branch that formal media is missing?
- Is there formal evidence that supports or contradicts the public narrative?

**Coverage self-description (added 2026-06-10, B2):** lane coverage is a
function of the scheduled ingest list. When an investigation's `geo_scope`
has no ingested subreddits, the lane must emit
`coverage_gap {lane: public_discussion, reason: not_ingested}` (the Phase 1a
gap mechanism already supports this) instead of returning silent emptiness.
Extending the ingest list then becomes a visible, data-driven action.

### D. Frame Extractor

Frame extraction should start rule-based, then graduate to model-assisted only
after a benchmark exists.

Initial frame families:

- `climate_stress`;
- `water_security`;
- `mismanagement_governance`;
- `food_agriculture`;
- `energy_infrastructure`;
- `conflict_damage`;
- `humanitarian_wash`;
- `public_health`;
- `protest_stability`;
- `sanctions_economy`;
- `military_bases`;
- `satellite_osint`;
- `regional_spillover`.

Each evidence item can carry multiple frames with scores.

### E. Workbench Investigation Graph Builder

Objects:

- `investigation_session`;
- `anchor_option`;
- `workbench_pin`;
- `investigation_node`;
- `subquestion`;
- `evidence_item`;
- `actor`;
- `source`;
- `frame`;
- `place`;
- `relation`;
- `coverage_gap`.

Relation types:

- `supports`;
- `context_for`;
- `contradicts`;
- `same_actor_as`;
- `same_place_as`;
- `same_source_lane_as`;
- `frame_contrast_with`;
- `causal_claim`;
- `temporal_precedes`;
- `regional_spillover`;
- `infrastructure_dependency`;

Evidence modality (`osint`, `imagery`, `actor_claim`, `media_report`) is an
attribute on `evidence_item`, not a relation type.

### F. List/Detail Reconciliation

Before presenting a node as answerable, the builder must reconcile:

1. Thread list count.
2. Detail endpoint count.
3. Signal sample count.
4. Country/time filters.
5. Retrieval lane count.

If these disagree, the node should show a gap:

```json
{
  "gap_type": "list_detail_mismatch",
  "thread_id": "flood-landslide-disaster--ir",
  "list_count": 133,
  "detail_count": 0,
  "recommended_action": "route country-scoped thread detail through thread packet or explain unavailable detail"
}
```

No user-facing surface should silently show `133` in one place and `0` in
another.

### G. Source Credibility Tiers (added 2026-06-10, P2)

The claim-verification forcing case requires distinguishing
low-credibility/conspiracy outlets, national agencies, mainstream media, and
scientific fact-checkers in the who-says-what matrix. Without this the matrix
would present Global Research and NOAA as peers, and the case cannot pass
honestly.

This capability is the **product face of Paper 2** ("Cross-source
source-quality scoring for narrative intelligence") and consumes the #154
audit:

- v1 is a small, inspectable tier map: existing `is_state_media` flag +
  `source_family` + a fact-checker/met-agency allowlist + a known-conspiracy
  list seeded from this spec's claim-verification baseline sources;
- tiers are labels with provenance, never silent filters (No Silent Filtering
  applies: a low-credibility source is shown with its tier, not hidden);
- expansion and measurement follow the Paper 2 methodology
  (`atlas-topic-benchmark-v2` statistical conventions);
- ranking consumption: tier feeds `source_actor_value` priors and
  `noise_risk` inputs — it does not get its own additive component until the
  calibration harness shows a constraint that demands one.

### H. Evidence-Window Contract (added 2026-06-10, B1)

`POST /api/v2/research/plan` accepts `hours` up to 720, but evidence depth is
not uniform across that range. The plan must emit the window band as part of
its honesty contract instead of pretending uniform depth:

| Window | Evidence depth | Research-plan behavior |
|---|---|---|
| ≤168h (hot) | full `signals_v2` + evidence samples | all lanes active |
| 168h–~90d (processed) | aggregates only (`theme_country_hourly_v2`, processed historical) | thread/country anchors OK; evidence samples marked unavailable; gap note `evidence detail limited to aggregates beyond the hot window` |
| beyond (archive) | manifests on the external disk, no live query path | not queryable; the plan states it explicitly; an archive bridge is its own future issue, never an implicit promise |

This is the product-facing consequence of the temporal model (Paper 6).

**Serving maturity (added 2026-06-10, extends H backward to fresh data):**
the same honesty applies to the newest data. Measured 2026-06-10: NLP covers
~3.5% of a 24h window, topic classification ~7.4%, so a blanket serving delay
cannot guarantee "processed" — maturity must be labeled, not assumed:

| Maturity tier | Meaning | Guarantee |
|---|---|---|
| `provisional` | ingested < 1h ago | exists, deduped; raw GDELT tone; topic/NLP may be missing |
| `classified` | topic cron passed (≤1h) | dedup + topic assignment stable; counts stop moving |
| `enriched` | NLP done | RoBERTa sentiment, NER done (per-signal badge, never a global promise at current capacity) |

Aggregate surfaces (Brief, threads, country counts) read from **sealed hours
only** (`classified` floor) so counts and rankings stop shifting under the
user; live stream surfaces keep serving `provisional` with an explicit
"unconsolidated" badge. Analysis:
`docs/research/2026-06-10-funnel-maturity-and-positioning.md`.

## Backend Contract Proposal

### `POST /api/v2/research/plan`

This is the Phase 1 search helper. It should not return a finished dossier. It
returns an interpreted intent, candidate anchors, and suggested next actions.

Request:

```json
{
  "query": "clima en Iran y ataques a bases estadounidenses satelitales en Medio Oriente",
  "hours": 168,
  "geo_scope": ["IR", "ME"],
  "mode": "suggest_anchors",
  "context": {
    "selected_country": "IR",
    "workspace_items": []
  }
}
```

Response:

```json
{
  "session_id": "research-session-...",
  "query": "...",
  "interpreted_intent": {},
  "anchor_options": [
    {
      "type": "country|thread|source_lane|actor|public_attention|coverage_gap|related_branch",
      "label": "...",
      "action": "open|pin|add_branch|compare|inspect_gap",
      "target": {}
    }
  ],
  "pin_candidates": [],
  "suggested_next_steps": [],
  "coverage_gaps": [],
  "ranking_explanations": [
    {
      "anchor_id": "...",
      "score_components": {
        "intent_match": 0.8,
        "thread_coherence": 0.7,
        "evidence_strength": 0.5,
        "answerability": 0.6,
        "movement_signal": 0.4,
        "source_actor_value": 0.3,
        "geo_entity_fit": 0.9,
        "novelty_or_gap_value": 0.2,
        "noise_risk_adjustment": -0.1,
        "unsupported_claim_adjustment": 0,
        "list_detail_mismatch_adjustment": -0.2
      },
      "reason_codes": ["strong_geo_fit", "medium_evidence", "list_detail_mismatch"]
    }
  ],
  "downranking_ledger": {
    "candidate_count": 0,
    "shown_count": 0,
    "downranked_count": 0,
    "omitted_count": 0,
    "reason_codes": {}
  },
  "quality_envelope": {
    "band": "thin|medium|high|degraded",
    "answerable_questions": ["where", "sources", "evidence"],
    "missing_questions": ["why_moving"]
  }
}
```

V1 can be stateless/read-only. Persistence is optional later. The endpoint is
cached in Redis (~2 min) keyed on normalized-query + geo + hours, matching the
existing unified-search cache convention.

### Latency and Progressive Loading

Atlas does not need Google-scale millisecond answers for research workflows, but
it must be honest about what is happening.

Target response pattern:

| Stage | Target | User-visible state |
|---|---:|---|
| Fast anchors | 1-3s | "Finding matching countries, threads, and source lanes..." |
| Ranked research plan | 5-12s | "Ranking anchors by evidence, movement, sources, and gaps..." |
| Public discussion / Reddit lane | 10-20s | "Checking public discussion and community signals..." |
| Deep enrichment / external context | 20-60s | "Adding background context and checking unsupported claims..." |

The first useful UI should appear as soon as fast anchors are ready. Deeper
lanes can stream in progressively and update the Workbench route.

Implementation rule:

- Precompute thread/source/entity/public-attention indexes where possible.
- Run slow lanes asynchronously.
- Show partial results with provenance instead of blocking the whole workflow.
- Keep a visible loading explanation for each lane.
- Do not use slow external enrichment to hide the local Atlas result.

### `POST /api/v2/workbench/pins`

Persists or stages an item the user chose to keep.

```json
{
  "session_id": "...",
  "pin": {
    "type": "country|thread|source|actor|evidence|gap|note",
    "target": {},
    "user_note": "why this matters"
  }
}
```

### `POST /api/v2/workbench/investigations`

Creates a clean investigation session so pins do not mix across unrelated
research work.

```json
{
  "title": "Iran climate and regional infrastructure",
  "initial_query": "clima Iran Medio Oriente agua sequia",
  "source": "search|manual|continue_prompt"
}
```

### `GET /api/v2/workbench/investigations`

Returns the sidebar/history list:

```json
{
  "active_investigation_id": "...",
  "investigations": [
    {
      "id": "...",
      "title": "Iran climate and regional infrastructure",
      "updated_at": "...",
      "pin_count": 12,
      "last_query": "US bases satellite communications Middle East"
    }
  ]
}
```

### `POST /api/v2/research/plan/expand`

Suggests anchors for an added branch:

```json
{
  "session_id": "...",
  "branch_query": "relacion con ataques a bases estadounidenses y comunicaciones satelitales",
  "relation": "related_to"
}
```

V1 can simply recompute the anchor plan with current Workbench pins plus the new
branch query.

### `GET /api/v2/workbench/{id}/export`

Future: export the pinned investigation route to Markdown/JSON.

## Frontend / Workbench UX

### Search Entry

Current SearchBar should keep quick direct search, but add a clear action:

- `Start investigation`
- `Add to Workbench`

For broad queries, the primary action should show anchors and next steps, not
force theme detail or a finished answer.

### Workbench Mode

Workbench becomes the investigation memory and editor:

- left: pinned route / trail;
- center: evidence/storyline;
- right: who-says-what + frames + gaps;
- bottom or side rail: next questions / add branch.

User can add:

- another query;
- another country;
- another actor/source;
- another relation.

### Investigation Sidebar

Workbench should include a sidebar/history pattern:

- current active investigation;
- recent investigations;
- `New investigation`;
- `Continue last investigation`;
- `Move/copy pin`;
- clear indication when a pin belongs to a different investigation.

This prevents the product from mixing yesterday's pins with today's unrelated
research. **Durability note (amended 2026-06-10, B3):** v1 storage is
localStorage — per-browser and evictable, NOT a durable archive. Durability in
v1 comes from JSON export, which therefore ships in Phase 2 (not 3). The
Phase 2 pin-event log incidentally provides server-side reconstruction
capability.

Example:

1. User starts: `clima Iran Medio Oriente`.
2. Atlas offers country/thread/source/public-attention anchors.
3. User opens Iran, opens a water/climate thread, and pins it.
4. User adds: `ataques a bases estadounidenses y satelite`.
5. Atlas suggests a sibling branch connected through:
   - conflict infrastructure;
   - satellite imagery;
   - regional bases;
   - energy/water security;
   - Middle East spillover.

### Dossier View

The optional final view should read like a structured report generated from
Workbench pins:

1. Executive summary.
2. Timeline.
3. Narrative tree.
4. Who says what.
5. Frame comparison.
6. Evidence table.
7. Gaps/uncertainty.
8. Related questions.

## Phased Implementation

### Phase 0 — Spec + walkthrough fixture from Iran case

Deliverables:

- this spec;
- a manually curated expected walkthrough for the Iran compound case;
- current Atlas failure snapshot.

No product code.

### Phase 0.5 — Prerequisite: list/detail reconciliation fix

Independent correctness bug, own issue, lands before Workbench relies on counts.

Deliver:

- reconcile thread list count vs detail endpoint count vs signal sample for
  country-scoped threads (e.g. `flood-landslide-disaster--ir`: list `133`,
  detail `0`);
- route country-scoped thread detail through the thread packet or return an
  explicit "detail unavailable" with the same count contract.

Acceptance:

- No surface shows a non-zero list count and a `0` detail for the same thread +
  filters without an explicit gap explanation.

### Phase 1a — Read-only anchors (prove the forcing case)

Deliver:

- deterministic intent parser;
- expansion dictionary for climate/water/conflict/infrastructure;
- multi-lane anchor discovery over **existing** thread/country/public-attention
  surfaces;
- country/thread/source/public-attention/gap anchor options;
- pin candidates and suggested next steps;
- coverage gaps including list/detail mismatch (reusing Phase 0.5).

No ranking ledger yet. No persistence. No LLM dependency.

Acceptance (automated fixture, not manual smoke):

- The Iran forcing-case query returns at least N anchors, and at least one
  anchor opens to non-empty thread/country detail.
- Query can suggest the US bases/satellite branch.
- Output labels each anchor as direct evidence, context, weak support, or gap.
- Output marks gaps instead of hiding them.
- This phase explicitly does **not** claim signal-level recall for natural
  queries; its win is anchor surfacing.

### Phase 1b — Ranking + transparency

Deliver:

- weighted, normalized `investigative_score` (weights in config);
- ranking explanations with `reason_codes`;
- downranking/omission ledger;
- low-confidence / noisy inspection tray.

Acceptance:

- Output explains why anchors were ranked, downranked, or omitted.
- No material that matches the investigation is silently omitted.

### Phase 1.5 — Semantic lane (`e5-base`)

Deliver:

- query↔thread and query↔evidence similarity using the existing local
  `e5-base` embeddings;
- semantic candidates merged into anchor discovery, labeled `retrieval_lane =
  semantic`;
- **(scope clarified 2026-06-10, Pipeline Funnel Principle)** the semantic
  lane retrieves over the **full deduped corpus** (~153K/24h), not only the
  gated/served pool — quality verdicts ride on evidence labels
  (`weak_support`, `below_gate`, `unclassified`), so the 99% funnel drop is
  default-hidden but query-reachable, never unreachable.

Acceptance:

- A natural query with no lexical match (incl. cross-language headlines) can
  still surface related evidence anchors via semantic similarity, labeled as
  semantic rather than direct match.
- Fixtures include at least one cross-language case (Persian/Arabic headline
  ↔ Spanish query) — cross-language recall is the stated reason this lane
  exists.
- A signal below the precision gate is retrievable by a matching semantic
  query and arrives labeled with its gate status.

### Phase 2 — Workbench Pinning + Route UI

Storage: **client-side localStorage** in v1. No backend migration. Promote to
Postgres (`investigation_session` / `workbench_pin`) only when multi-device or
sharing is required; the `POST /api/v2/workbench/*` contracts are the
forward-compatible target, not a v1 blocker.

Deliver:

- investigation sidebar/history;
- `New investigation` and `Continue last investigation`;
- Search results can be pinned to Workbench.
- Existing country/thread/source/evidence panels expose pin actions.
- Workbench renders pinned route, evidence, frames, sources, actors, gaps.
- Allows `Add branch`.
- **Pin-event log (added 2026-06-10, P3):** log
  `(plan_id, anchor_id, rank_shown, opened, pinned, dwell)` from day one —
  a Postgres table or JSONL, no new infra. Anchor impressions → opens → pins
  are graded relevance labels. This is simultaneously the ranking-calibration
  dataset (replacing spec-derived constraints with real judgments), the
  Paper 7 analyst-workflow evidence, and the input for suggestion-guided
  search. Cheap at build time, impossible to retrofit.
- **JSON export** of the pinned investigation (moved up from Phase 3 — it is
  the v1 durability mechanism, see B3).

Acceptance:

- User can reproduce the Iran climate + satellite/bases compound investigation
  without leaving Atlas and without losing the route they took.
- The 8-step walkthrough (Immediate Next Step section) passes as an automated
  E2E fixture for both forcing cases. **This fixture is the exit criterion
  for umbrella #213 (added 2026-06-10, S2/D4):** Phases 1a/1b acceptance was
  the per-layer fixtures that already exist; the walkthrough fixture is
  Phase 2's, and #213 closes when it passes. Tier B/C/D work beyond that is
  ongoing product work, not umbrella scope.

### Phase 3 — Report/Export

Deliver:

- Markdown/JSON export from pinned Workbench route;
- report view generated from pins;
- timeline, who-says-what, frame comparison, evidence table, and gaps.

Acceptance:

- The dossier/report is traceable back to the user's pinned investigation, not
  an opaque generated answer.

### Phase 4 — Evidence/Frame Quality

Deliver:

- benchmark labels for research-thread evidence roles;
- frame extraction validation;
- source/actor normalization;
- duplication/syndication detection;
- confidence bands.

Acceptance:

- At least 85% precision on direct evidence vs context/noise for a small
  reviewed sample.
- Frame labels useful enough for human review, not necessarily fully automatic
  truth.

### Phase 5 — Optional External Context Adapter

Deliver:

- explicit "web context" lane for sources Atlas does not ingest;
- citation list;
- source reliability labels;
- separation from Atlas-ingested evidence.

Acceptance:

- Atlas can say: "Atlas evidence is thin; external context from UNICEF/WRI/ACAPS
  fills background, but current Atlas hot window lacks direct evidence."

## Open Technical Problems

1. Query expansion must avoid over-recall. `climate` should not pull every
   environment article unless tied to Iran/water/heat/drought/infrastructure.
2. Cross-language evidence must work. Persian/Arabic/Hebrew/Russian/Spanish
   headlines need translation or multilingual matching.
3. Actor extraction is currently noisy. Who-says-what needs normalized actor
   identities, not raw repeated strings.
4. Source framing needs source-family and article-type awareness.
5. Historical processed tables may lack enough evidence detail for older
   windows; research builder may need small evidence samples or archive bridge.
6. Thread list/detail paths, including those backed by `dynamic_topics`, must be
   reconciled before Workbench relies on counts.
7. Satellite/OSINT claims should be labeled carefully as reported analysis,
   imagery-derived evidence, or actor claim.

## Product Success Criteria

This feature is successful when:

- a broad natural query produces useful Atlas anchors, not zero results;
- a user can add a related branch without restarting;
- a user can pin useful country/thread/source/evidence items as they research;
- Workbench preserves the investigation route and relationships between pins;
- Atlas shows who says what and how frames differ;
- Atlas clearly separates evidence, context, weak support, and gaps;
- list counts and detail panels do not contradict each other;
- the pinned route can become a report/dossier in Workbench;
- the user can understand the story's evolution and related routes from one
  place;
- for a viral/fringe claim, Atlas surfaces the observable event, who is making
  the claim and from what source family, authoritative contradictions, and an
  explicit unsupported-causal-link flag — without endorsing or amplifying the
  claim.

## Related Issue Map

This spec is not isolated to one new issue. It depends on several existing
threads of work:

| Area | Issues | Product connection |
|---|---|---|
| Search and investigation entry | #213, #175, #152, #178 | Broad queries should become anchor menus and stable routes, not dead ends or layout collisions. |
| Living Narrative Threads | #207, #167, #204, #185 | Search should generate/open threads; `dynamic_topics` is the current implementation source for many threads, not a separate product object. Topic anchors remain internal support, not the user-facing taxonomy. |
| Evidence route and Workbench memory | #173, #140, #134, #133, #141 | The user needs to see how evidence was found, pin it, and later turn the route into reading/report output. |
| Public attention and drowned-out stories | #168, #172, #145, #153 | Atlas should reveal when one story dominates, when attention diverges from media coverage, and where social/public lanes matter. |
| Query-time evidence and story evolution | #161, #159, #156 | Atlas should enrich at query time and show propagation/evolution, not only static hot-store matches. |
| Sources and voice mix | #160, #148, #150, #154, #158, #180, #46 | "Who is talking?" requires source lanes, publisher expansion, non-anglophone coverage, quality/dominance checks, and conflict/event sources. |
| Entity/actor hygiene | #176, #162, #166 | "Who says what?" needs clean actor/person/entity surfaces, not noisy string matches. |
| Layout and provenance | #179, #183 | Investigation surfaces need clear active layers, provenance, counts, and source-of-truth display. |

## Backlog Alignment (2026-06-09 review)

Key finding: the open backlog is not scattered. A large cluster of existing
issues directly feeds this spec. #213 becomes the **umbrella** that finally
sequences that backlog. Each issue is tiered by how it relates to the research
workflow. (No Kalman GitHub issue exists; it is the read-only pilot script and is
the `movement_signal` provider — see Scope Corrections.)

### Tier A — Core spec surfaces (build with / as part of #213)

| Issue | Role in research workflow |
|---|---|
| #207 living Narrative Threads contract | Core dependency. Anchors are threads; this contract underpins them. |
| #173 Evidence Route panel | The `Show evidence route` Workbench action. |
| #168 public-attention threads + semantic links | Public-attention anchor lane + semantic links. |
| #172 silent-risk detector | Feeds `novelty_or_gap_value` and coverage gaps. |
| #160 Voice Mix endpoint | Powers the who-says-what matrix / `source_actor_value`. |
| #176 entity/actor hygiene | Clean actors for who-says-what (Open Problem 3). |
| #178 stable item inspection (pub vs render time) | Stable pinned evidence rows. |

### Tier B — Recall and cross-language enablers (fix the 0-results forcing case)

| Issue | Role |
|---|---|
| #161 GDELT DOC 2.0 query-time enrichment | Cheapest signal-recall fix before embeddings; query-time evidence lane. |
| #185 corpus-mined lexicon | Feeds the intent parser expansion dictionary (was previously unconnected). |
| #150 non-anglophone sources | More multilingual evidence = fewer empty natural queries. |
| #158 newsdata country-primary multilingual buckets | Same cross-language recall lever. |
| #162 multilingual sentiment/NER/framing models | Frames + actors + cross-language for who-says-what. |
| #157 multilingual NLP benchmark | Validates B above before trusting it in ranking. |

### Tier C — Source/evidence quality (feed ranking weights; do before/with Phase 1b)

| Issue | Role |
|---|---|
| #154 source quality/dominance audit | Grounds `noise_risk` inputs and source-tier priors (capability G); weights themselves come from the calibration harness (amended 2026-06-10). |
| #166 analyst confidence calibration | Confidence bands on evidence/frames. |
| #180 reliefweb API/proxy fix | Restores the humanitarian source lane (UNICEF/ACAPS in the Iran matrix). |
| #148 publisher expansion in CountryBrief | Source breadth for `source_actor_value`. |
| #153 evaluate Reddit/NewsAPI/MediaStack/EventRegistry | The public-discussion lane + enrichment source eval. |
| #156 newsapi quota + dynamic crisis queries | Query-time enrichment lane budget. |
| #159 GDELT Event Mentions for propagation | Story-evolution / movement evidence. |
| #46 ACLED access | Conflict-event evidence for the bases/infrastructure branch. |

### Tier D — NLP capacity backbone (unprocessed signals are invisible evidence)

| Issue | Role |
|---|---|
| #164 ADR sampling vs full backfill (~1.8M unprocessed) | Decides how much hidden evidence becomes searchable. |
| #163 split NLP into priority-queue process | Capacity for query-time enrichment. |
| #184 bump worker limit + drain backlog | Same family; reduces evidence blind spots. |

### Tier E — Search entry / front door

| Issue | Role |
|---|---|
| #152 command-bar layout collision | Must hold the new `Start investigation` / `Add to Workbench` actions. |

### Tier F — Superseded or fold by current approach

| Issue | Disposition |
|---|---|
| #167 Atlas topic intelligence beyond GDELT themes | Largely delivered by `dynamic_topics` -> threads. Reframe to "internal anchor support only" or close. |
| #134 / #140 use-case docs + visual manual | The Iran walkthrough becomes the canonical showcase. Defer until the feature ships, then fold. |
| #204 Path C quarterly taxonomy revision | Internal anchor support only; low priority; not user-facing taxonomy. |

### Tier G — Independent (not blocked by, not blocking #213)

`#106` mascot, `#147` map reset, `#151` financial overlay, `#179` map legend,
`#183` sentiment/heat badge, `#196` vessels TLS, `#212` Equal Earth. Keep as a
separate backlog; `#151`/`#179`/`#183` have only weak provenance/frame ties.

### Suggested attack order

1. Phase 0.5 list/detail fix (trust prerequisite). **[done 2026-06-09]**
2. Tier A surfaces + Phase 1a anchors. **[Phase 1a done 2026-06-10: #215]**
3. Phase 1b ranking + ledger, weights via calibration harness.
   **[done 2026-06-10: #216 + calibration]**
4. Tier B recall lane (#161 first, then #185 + multilingual) + Phase 1.5
   `e5-base` semantic lane (fixtures must include one cross-language case).
5. Phase 2 Workbench (localStorage + pin-event log + JSON export) + #152
   search entry. Walkthrough fixture = #213 exit criterion.
6. Tier D NLP capacity as a continuous backbone track in parallel.
7. Kalman movement-feed promotion (approved 2026-06-10, own issue) — parallel,
   not blocking.

## Research References

- Google Search Help, "How Google autocomplete predictions work":
  `https://support.google.com/websearch/answer/7368877`
  autocomplete uses real searches, wording patterns across the web, and
  policy-based removals/exceptions.
- Bates, "The Design of Browsing and Berrypicking Techniques for the Online
  Search Interface":
  `https://pages.gseis.ucla.edu/faculty/bates/articles/berrypicking.pdf` users
  often gather information by following changing trails rather than executing
  one perfect query.
- Jansen, Booth, and Spink, "Patterns of query reformulation during Web
  searching": `https://asistdl.onlinelibrary.wiley.com/doi/abs/10.1002/asi.21071`
  query reformulation is a central web-search behavior.
- Microsoft Research, "To Search or to Ask": users combine search engines with
  social-network asking for some information needs:
  `https://www.microsoft.com/en-us/research/publication/to-search-or-to-ask-the-routing-of-information-needs-between-traditional-search-engines-and-social-networks/`
- Reddit API documentation: `https://www.reddit.com/dev/api/` Reddit remains a
  useful public discussion source, but Atlas should treat it as public
  discussion/commentary unless corroborated.

### Claim-verification baseline sources (Iran "rain theft" / weather weapon)

- Factually fact-check, "Did destroying weather-control tech cause Iran's sudden
  rain": `https://factually.co/fact-checks/science/sudden-rain-iran-weather-modification-technology-claims-explained-2bd0c9`
- Zee News, "Iran's rain theft claim and US radars / Israel weather-engineering":
  `https://zeenews.india.com/world/whats-irans-rain-theft-claim-and-how-its-linked-to-us-radars-israels-weather-engineering-machines-3040508.html`
- Tempo, "Iran's sudden weather shift sparks 'rain theft' theory":
  `https://en.tempo.co/read/2100624/irans-sudden-weather-shift-sparks-rain-theft-theory`
- NOAA, "Fact check: debunking weather modification claims":
  `https://www.noaa.gov/news/fact-check-debunking-weather-modification-claims`
- RMIT FactLab, "Claims US military project is manipulating weather are nonsense":
  `https://www.rmit.edu.au/news/factlab-meta/claims-us-military-project-manipulating-weather-are-nonsense`
- AAP FactCheck, "HAARP weather control conspiracy is off in the clouds":
  `https://www.aap.com.au/factcheck/haarp-weather-control-conspiracy-is-off-in-the-clouds/`

These are used to characterize the narrative for the claim-verification fixture.
Low-credibility amplifiers (e.g. Global Research, planet-today, needtoknow) are
referenced in the baseline only as examples of the claim's spread, not as
evidence.

## Immediate Next Step

Create a concrete walkthrough fixture for the Iran case:

```text
Step 1: Search "Iran".
Step 2: Open Country Focus and inspect active threads.
Step 3: Search "climate in Iran" and inspect anchor options.
Step 4: Pin water/climate/flood/heat signals or gaps.
Step 5: Add branch "US bases satellite communications Middle East".
Step 6: Inspect related conflict-infrastructure anchors.
Step 7: Pin source/actor/evidence items.
Step 8: Workbench shows route, relations, gaps, who-says-what, and optional report.
```

Turn that walkthrough into the automated acceptance fixture — it is the
Phase 2 exit criterion for #213 (amended 2026-06-10, D4: steps 4-8 are
Phase 2 surface, so the full E2E fixture lands with Phase 2; Phases 0.5/1a/1b
were accepted on their per-layer fixtures).

Status as of 2026-06-10:

1. ~~Phase 0.5 list/detail reconciliation~~ — done.
2. ~~Phase 1a read-only anchors~~ — done (#215, deployed).
3. ~~Phase 1b ranking + transparency ledger~~ — done (#216, deployed), weights
   via the calibration harness (not the #154 audit).
4. **Next:** Phase 1.5 `e5-base` semantic lane for cross-language recall
   (include a Persian/Arabic ↔ Spanish fixture case).
5. Then Phase 2 Workbench: localStorage + pin-event log + JSON export +
   walkthrough fixture.
6. Parallel: Kalman movement-feed promotion (approved, own issue);
   capability G source-credibility tiers (own issue, feeds the
   claim-verification case).
