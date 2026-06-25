# CLAUDE.md - Project Guidelines and Agent Configuration

Last updated: 2026-06-10 (Research Workflow Phases 1a/1b shipped + spec review).

This file provides Claude Code with essential context about the Observatorio Global project, including agent configurations, tooling guidelines, and development workflows.

## Project Overview

Observatorio Global is a narrative intelligence system that tracks, analyzes, and visualizes how topics and narratives propagate across global media sources. The system aggregates signals from GDELT 2.0, Google Trends, and Wikipedia, normalizes them into a unified schema, and provides insights on geographic drift, sentiment analysis, and narrative mutations.

## Current Session Context (2026-06-10, Research Workflow Phases 1a/1b shipped)

Branch `v3-intel-layer`, aligned with origin. All of the following is deployed
to Fly (`atlas-api-pedro`) and verified by production smoke:

- **Phase 1a (#215, closed):** deterministic intent parser
  (`backend/app/services/research_plan.py`) + multi-lane anchor discovery
  (`research_anchor_discovery.py`) + `POST /api/v2/research/plan` (120s Redis
  cache, contract `research-plan-v0`). Lanes: country, threads (country-scoped
  + global), public attention (trends_v2), related branches, coverage gaps.
  Every anchor labeled direct_evidence/context/weak_support/gap; degraded
  lanes emit gap notes, never 500s. Geo alias tokens excluded from topical
  matching.
- **Phase 1b (#216, closed):** `investigative_score` per anchor
  (`research_ranking.py`), ranking_explanations with reason_codes,
  downranking_ledger (candidate/shown/downranked/omitted reconciles exactly),
  low_confidence_tray, noise lanes (sports/entertainment/roundup → tray, never
  excluded), relevance gate `0.5 + 0.5*intent_match` exposed per anchor.
- **Ranking calibration:** weights + normalization midpoints calibrated by
  `backend/scripts/calibrate_research_ranking.py` — constraint harness over
  spec-derived gold orderings + live forcing cases (21/21 vs baseline 20/21).
  Report: `docs/research/ranking-calibration/2026-06-10-ranking-calibration.md`.
  NOT seeded from #154 (that dependency was removed; see issue comment).
- **Spec review + amendments:** judgment of the spec lives in
  `docs/specs/2026-06-10-research-workflow-spec-review.md`; all amendments
  applied in place to the spec (changelog section at top). Key decisions:
  capability G source-credibility tiers added (#217, product face of Paper 2);
  pin-event log is a Phase 2 day-one deliverable (#218 — the future
  relevance-judgment dataset); evidence-window contract (hot ≤168h / processed
  aggregates / archive not queryable) is spec capability H; #213 closes when
  the Phase 2 walkthrough E2E fixture passes.
- **Kalman promotion APPROVED (Pedro, 2026-06-10), scoped:** #219 — promote
  the read-only state pilot to a persisted movement feed (velocity/surprise/
  uncertainty per thread, written after the emergent-snapshot cron) consumed
  by `movement_signal` v2 with `changed_10h` fallback. Strictly a movement
  provider — still NEVER a semantic classifier; `lifecycle_state` stays
  separate from `state_estimate`.

**Phase 1.5a shipped 2026-06-10** (`45834e8`, deployed):
`research_semantic.py` — semantic lane with two bases, both
`retrieval_lane=semantic` + `match_basis`: `member_centroid`
(query↔`dynamic_topics.centroid_vec`, pooling replicates the snapshot
pipeline exactly) and `topic_description` (query↔embedded atlas_topics
label+description, cached per process, relative top-margin cut 0.012 —
taxonomy similarity never presented as evidence). Cross-language verified
real-model (Spanish↔Persian/English); pure-semantic case "crisis hídrica en
Teherán" → water-stress anchor sim 0.7967. Fly api-runtime has no torch, so
production shows the designed `lane_unavailable` gap ("recall is
lexical-only") until #223.

**Phase 2 slice 1 shipped 2026-06-10** (`ff38990`, Fly + Vercel deployed,
prod E2E verified): Workbench overlay (command-bar WORKBENCH button) —
investigation sidebar + pins + trail + JSON export over localStorage
(`lib/workbench.ts`); `ResearchPlanPanel` (anchors, gaps, tray, ledger, PIN);
pin-event log #218 CLOSED (migration 053 `research_pin_events` applied,
`POST /api/v2/research/events`, plans carry `plan_id`, frontend emits
impressions/opens/pins — verified rows in prod). Thread anchors open via the
theme-detail contract (slug--cc parsed); country anchors via CountryBrief.

**#213 umbrella CLOSED 2026-06-10** (`c020de7`, deployed): walkthrough E2E
fixture passes at three layers — service
(`backend/tests/test_research_walkthrough_fixture.py`), client route
(`frontend-v2/src/lib/walkthrough.test.ts`), live production smoke
(`backend/scripts/research_walkthrough_smoke.py`, repeatable, both forcing
cases PASS). SearchBar gained the 'Start investigation' entry (creates
investigation + opens Workbench + loads the plan). Browser click-through of
the overlay still worth a manual pass from Pedro.

**Phase 1.5b deliverable 1 shipped 2026-06-10/11** (`a129cc9`, deployed):
semantic lane LIVE in production. `enrichment/embed_service.py` = internal
e5 embed service on nlp_worker (4096MB machines, ~3.3GB headroom — the
985MB note was stale), private 6PN only, daemon thread, snapshot-identical
pooling. API box reaches it via `EMBED_SERVICE_URL` (fly.toml), 10s timeout,
degrades to visible lane gap. Two prod bugs fixed: e5 had to be pre-baked
into nlp-runtime (TRANSFORMERS_OFFLINE=1 blocks runtime download), and the
service must bind `::` (Fly 6PN is IPv6-only — 0.0.0.0 = connection
refused). Verified: semantic anchors in prod, weak matches correctly
trayed, walkthrough smoke PASS both cases.

**Phase 1.5b deliverable 2 shipped 2026-06-11** (`207feda`+`6128416`,
deployed E2E): migration 054 `signal_embeddings` (pgvector halfvec/768,
HNSW); writer `scripts/embed_hot_corpus.py` + launchd cron
`com.atlas.embed-hot-corpus` (6h, installed on M1); query path
`fetch_semantic_signal_matches` → `plan.semantic_evidence` items with
`gate_status` labels (`match_basis=signal_headline`). Bugs fixed: headlines
HTML-entity-encoded (unescape before embed), executemany WAN bottleneck
(unnest batch INSERT ~45/s), cold model load burning timeouts (warmup thread
+ 30s remote timeout). Prod verified: 12 below_gate evidence items for a
pure-semantic Spanish query. Backfill ~200K running; #223 stays open for:
threshold re-measure on full corpus, query-side headline dedup, UI render of
semantic_evidence (pairs with #178).

**Issue audit 2026-06-11:** closed #207 (threads contract delivered), #163
(nlp_worker split delivered), #167 (superseded by dynamic topics). Backlog
close-map: biggest clusters close at (1) who-says-what surface polish
(#160/#168/#172/#173/#176/#178 + #217) and (2) the #154/Paper 2 audit moment
(7-8 issues). 10 issues are spec-independent UX/maintenance.

**Thread-quality diagnosis 2026-06-11 (Pedro's fresh-eyes review, confirmed
with data):** dynamic-topic identities are black holes — running-mean
centroid drift + MATCH_THRESHOLD=0.85 (below the e5 centroid↔centroid noise
floor) makes 11-day-old topics absorb unrelated clusters at 0.87-0.93
(evidence in #224: 'PSG Victory Riots' recent members are Orwell/Modi/
earthquakes/car launches). Plus: roundup detection misses non-English labels
('Noticias Regionales Variadas' active, unflagged); /threads ranks by
lifetime agg_n_signals so stale topics dominate by construction. Fix design
in #224 (anchor-centroid guard, threshold re-measure, event aging,
entropy-based roundup detection, window-scoped serving counts, identity
rebuild). #225 = editorial surface-hierarchy review (Brief L1 → App L2 →
Workbench L3 → dossier L3.5), blocked on #224.

**2026-06-12:** #224 CLOSED (anchor 0.93 after same-domain conflation found;
rebuild → 116 identities, actives = Russia-Ukraine/US-Iran/Mundial 2026;
prod /threads verified fresh). Embed cron rescheduled 17:30/23:30/05:30 —
heavy local compute NEVER during Pedro's working hours (daytime backfill
froze his machine; backfill reached 39.6K/200K, cron chips the rest
nightly). Atlas L4 markets layer documented
(docs/research/2026-06-12-atlas-markets-layer-l4.md, M0 event study =
#226): personal app in future private repo, evidence-gated, no employer IP.

**2026-06-12 (app review, Pedro):** global threads list was starved (4
threads vs 188K signals) — fetch_threads returned dynamic EXCLUSIVELY;
atlas threads now fill remaining slots (`8cf9dbc`, deployed, prod=10).
Below-gate evidence fallback shipped for the #214 contradiction: theme
detail with gated=0/raw>0 serves raw signals labeled below_gate_evidence +
UNVERIFIED banner (prod verified: CO election-legitimacy 0/44 — real
relevant headlines the gate hid). #214 stays open for list count
semantics. Markets L4: lives in `markets/` folder IN this repo (Pedro);
relational thesis recorded (co-movement, Atlas-as-API end state).

**2026-06-11/12 late session:** #223 CLOSED (`a56dd6b`): threshold 0.84
(re-measured on ~100K corpus), is_junk_headline filter write+query side
('Doc *.Shtml' scraped garbage was matching everything), query-side
headline dedup, SEMANTIC EVIDENCE UI section in ResearchPlanPanel
(UNVERIFIED/ASSIGNED badges). Prod verified clean. Embed cron converging
(99.6K embeddings; throughput > inflow).

**#225 review DELIVERED 2026-06-11** (`a6a7f79`):
`docs/specs/2026-06-11-surfaces-editorial-review.md`. Verdict: L1 Brief
inverted — leads with stats/choropleth/template "Editor's Analysis", buries
threads, editorial body still six GDELT theme articles (guardrail
violation). Key finding: briefing payload's `top_threads` (window-scoped
counts, trend, changed_10h, countries, hourly timeline w/ sentiment) +
`heat_countries` already contain the front page; Brief renders none of it —
frontend rendering decision, not backend gap. Only backend gaps: evidence
headlines per thread in payload + #214 count semantics. Proposed L1: lead
story from top thread + watchlist rows w/ movement + honest standfirst +
heating strip + reserved gap box + demoted map. Graphic slots per level
(§3). UX fold (§6): #152/#179/#147 = L2 legibility batch; #183 splits
(panel L2 / strip L1); #212 folds into Brief rebuild; #145 prerequisite
for gap box; #106 backlog; #151 → markets L4; #196/#204 excluded.
Execution order (§7): Brief rebuild first. Issue open pending Pedro's read.

**Brief rebuild (L1) SHIPPED 2026-06-12** (`3369e29`, Vercel prod
verified, #225 CLOSED): Pedro accepted the judgment; L1 implemented per
review §4. Lead story from `top_threads` (evidence headlines, why_now,
trend chip, sparkline), watchlist rows w/ movement + country chips,
honest standfirst (Math.random template essays deleted), Heating Up
strip from `heat_countries` (dominant story component named;
geo_confidence/duplication never surfaced), map demoted half-width
geoEqualEarth (#212 partial — L2 MapLibre still open), GDELT themes →
"By Theme" back-matter index, country view = country-scoped threads
(same contract as CountryBrief). No backend change needed — dynamic
threads already carried evidence_samples in the briefing payload.
Verified: 56/56 tests, local preview global+CO, prod bundle markers.
New issue #227: workbench pin evidence-snapshot + per-pin note (Phase 3
prerequisite). Gap box deferred to #172 (after #145).

**L2 legibility batch SHIPPED 2026-06-12** (`d15799c`, #152/#179/#147
CLOSED): command bar — compact time-range dropdown <1380px, '···'
overflow menu (TOUR+Settings; SettingsPanel now supports controlled
open/onClose), icon-only labels <1200px. Real cause of hidden horizontal
scroll: SignalStream headline flex children (min-width:auto) — fixed
min-width:0+ellipsis. Legend — follows effective render state (flows
section when filter activates arcs, not just toggle), 'Baseline spikes'
section for the always-on anomaly rings (the unexplained marker in
Pedro's recording), chokepoint ring documented. Map reset — two-stage ↺:
tilted → flat north-up first, flat → fly to hotspot. Verified
1440/1280/375 maxScrollX=0, menus exercised, 56/56 tests. Branding note:
#106 updated — Pedro wants leviathan/kraken mascot direction, dedicated
design session (colors/typography/message), first use = Brief loading
animation.

**2026-06-12 (Pedro's L2 review, live):** routing bug FIXED (`0b9ab4a`,
deployed): theme detail never parsed 'slug--cc' thread ids → atlas lookup
missed → GDELT path → 0 signals while list showed 48. Hit on Peru's live
vote-count dispute (Fujimori/Sánchez recount; 92 election headlines in
raw PE feed). Prod now: rawTotal 43 + below_gate_evidence + UNVERIFIED
banner. Diagnostic: gate kept 0/43 relevant Spanish headlines → gate
recall problem on non-English (→ #162, noted in #214). New umbrella
**#228**: L2/L3 deep review (connection map, click-path audit) with
Pedro's observations — person panel weakest ('El Niño' as person,
'bafana bafana' as people; fold #176), SignalDetail shows GDELT themes
not Atlas threads + irrelevant related signals (fold #178), yellow dots
no hover, PLANE dead/SHIPS sparse (movement→narratives, #159/#226),
widescreen 16:9 crushes AnomalyAlert/SourceIntegrity panels.

**#228 review DELIVERED 2026-06-12** (`cc041e5`):
`docs/specs/2026-06-12-l2-l3-deep-review.md`. Verdict: L2 skeleton right,
edges rotten — every path off the threads spine lands on raw GDELT
presented as product. Key findings: gate recall 0/43 Spanish ("language
gate in quality-gate costume" → measure keep-rate by language, likely
re-prioritizes #162); SignalDetail most-clicked + most dishonest leaf
(GDELT chips as story model, related-by-GDELT-overlap, dead onClick) —
rebuild with thread chips + semantic neighbors (embeddings exist);
person panel garbage-in (#176 folded, priority raised); DiscoveryPanel +
AtlasHeatList dead components (latter = half of #183 built, unmounted);
16:9 bottom row ~132px for 3 interactive sections → tabbed dock
proposal. L3 fine, only needs #227. Execution order §6: 1) SignalDetail
rebuild (folds #178), 2) dock tabs + mount AtlasHeatList (#183),
3) person hygiene cheap wins, 4) gate-recall SQL report, 5) map hovers +
PLANE degraded state, 6) keyword-match labels. Open pending Pedro's read.

**#229 created 2026-06-12** (Pedro's note while reading #228): threads
coverage scaling program. Measured funnel: 185K signals/24h → 15K cap →
8 clusters/373 signals → ~5 living threads = **0.2% coverage**. Levers in
order: (1) cluster over persisted signal_embeddings corpus (~100K,
dissolves the 15K-cap constraint that #223 already paid for), (2) scoped
regional passes (Peru recount had 92+ signals, never clustered —
global HDBSCAN drowns regional stories), (3) #222 stratified sampling,
(4) #219 lifecycle, (5) label refresh policy (labels frozen at creation),
(6) #162 multilingual, (7) #220 ledger as instrumentation prerequisite.
Facts verified: Reddit IS ingested (ingest_loop, source_family='social')
but invisible — no surface exposes it; 14 ingest services need a
utilization audit. Surface item folded into #228 impl: two-tier display
honesty in NarrativeThreads (living/curated vs atlas-aggregate fill).

**2026-06-12 (post power-outage resume):** #228 §6 items 1-2 shipped
(see below). #183 CLOSED (`28df5c7`+`7dc8955`): heat panel = AtlasHeatList
mounted as HEAT tab of new tabbed bottom dock (anomaly|heat|sources —
fixes the 16:9 ~132px crush); sentiment provenance badges (NLP nn% vs
GDELT) on Brief sentiment rows. **#230 created** (Pedro's China note,
judged not assumed): China is #5 by subject-country (6,235/24h) but that's
Western-lens — Chinese VOICE near-absent (2 outlets in 500-signal sample,
all English; CGTN/Xinhua RSS dead; ZERO zh ingestion — NewsData's 8 lang
batches skip zh/ja/ko entirely). Levers: east-asia NewsData batch, revive
dead state feeds, hard-dep on #162 multilingual NLP, document Great
Firewall ceiling. Folds into #229 source audit.

**2026-06-12 (Pedro's dock review — corrections):** the HEAT tab from
§6 item-2 was MISPLACED. Verified bug: map `country-heat-fill` uses
`/nodes` `.heat` which is volume-rank (US 1.0, GB 0.40, CN 0.26 —
monotonic w/ signalCount), NOT the `/heat/countries` baseline composite
(GZ 0.74/vol49, LB 0.65/vol3, US not top-5). US-always-red = the
volume≠importance distortion we explicitly rejected; same as the China
Western-lens gap (#230). → **#231 SHIPPED**: map fill = /heat/countries
atlas_heat composite (not /nodes volume-rank); US no longer reddest;
HEAT dock tab removed (heat = map property); volume → glow width only;
legend/tooltip reworded; absent-from-composite reads not-hot. Dock now
anomaly|sources. **#232**: vessels/aircraft/
conflict/anomalies are viz-only, verified they do NOT feed threads —
must become narrative inputs (paper-adjacent, #159/#226). **#233**:
reorderable panels regressed (RGL ^2.2.3 still in deps, commit e6fbecf
added draggable grid, now fixed CSS grid) — documented for revival.

**#228 §6 item 1 SHIPPED 2026-06-12** (`c6470cf`+`2b462fd`+`d3bae7a`,
Fly+Vercel deployed): GET /api/v2/signal/{id}/context (thread
memberships w/ gate status + semantic neighbors from signal_embeddings;
HNSW gotcha: ORDER BY joined vector column = seq scan timeout — bind
the vector as a constant). SignalDetailPanel: NARRATIVE THREADS chips
primary, GDELT demoted to taxonomy row, SEMANTIC NEIGHBORS w/
similarity+gate badges+working links replace the theme-overlap heuristic.
Prod proof: lluvias signal → Trujillo deslizamientos 0.94. Two-tier
badges in NarrativeThreads: LIVING vs AGGREGATE. Fresh signals show
'not embedded yet' (nightly cron lag — #229 lever).

**2026-06-13 (Pedro's HEAT review):** #231 follow-ups shipped — heat
gradient was too narrow (fetched top-80 only + raw band 0.36–0.72 → flat
orange, world dark). Fixed: fetch all (limit 250) + min-max normalize the
real band onto [0.1,1.0] + full blue→cyan→amber→red ramp (weather-radar
spread). Renamed GLOW→HEAT everywhere (button/help/docs/legend) — same
thing that drifted apart; Atlas = news weather-radar, HEAT fits the
composite. NEW issues: **#234** (focus propagation — focusing a
country/thread/person must repaint ALL surfaces to its RELATIONS; map
stays global today, flow-relation view regressed; the #228 connection-map
thesis made interactive — high-value spine item). **#230** confirmed
ja/ko also absent (only es/pt/ar/fr/sw/SE-Asia/hi batches; CJK press
entirely missing from news-text ingest, though wiki attention + GDELT
domain-map do cover JP/KR/CN).

**2026-06-13 (#234 slice 1 shipped):** country focus now re-scopes the
map heat to the focused country + flow-strength-weighted co-occurrence
partners (reuses visibleFlows), unrelated dims — map and flows agree.
Client-only. #234 stays open for thread/person/PA focus + the dock
surfaces re-scoping. Noted: spurious flow partners (Colombia→Trinidad)
are co-occurrence/flow quality, separate from propagation.

**2026-06-22 (Diversify Atlas + prove it — `f52c83b`):** Goal = make "global"
a measured claim. Shipped **Voice Mix audit** (`backend/scripts/voice_mix_audit.py`,
read-only, repeatable, `diversity_score` 0-100 = mean of english_balance /
language_entropy / cjk_coverage). **Baseline (prod, 168h, 146K signals):
English = 96.9% of language-known, CJK zh/ja/ko = 0, entropy 0.0686,
diversity_score 3.3/100** — the monoculture is now a number (artifact
`docs/research/voice-mix/2026-06-22-baseline.json`). Lever: **8th NewsData
batch zh,jp,ko / cn,tw,hk,jp,kr** (192 req/day < 200 free cap; NewsData
non-ISO "jp"→ISO "ja"). e5 semantic layer gives CJK presence + thread
membership immediately; NLP gate still English-only (`nlp_*_xlm` columns
exist but 0-populated → #162 is the next dep). Mechanism proven:
`tests/test_ingest_newsdata_cjk.py` 4/4 (CJK article → normalized source_lang
end-to-end, no live key needed). **Open loop: live corpus delta needs
`./scripts/deploy-fly-api.sh` + 1 ingest cycle, then re-run audit `--hours 24`;
success = CJK 0→N, score rises.** Empirical unknown: Japanese code jp vs ja
settles on first run. Method doc: `docs/research/voice-mix/2026-06-22-diversify-atlas.md`.
Follow-ups: #162 (multilingual NLP), #230 (revive CGTN/Xinhua zh feeds),
#160 (Voice Mix product surface).

**2026-06-22 WAVE 2 (full multilingual voice — `e216360`/`d927b8d`,
deployed):** Went past the single CJK batch to attack the monoculture at
volume. (1) **28 native-language RSS feeds** (`ingest_rss.py` WAVE 5,
zh/ja/ko/ru/fr/pt/de/ar/fa/hi — all verified live); English feed-share
78%→49%. RSS is UNCAPPED = the real lever vs NewsData 200/day. (2) **RSS
cadence 4th→2nd cycle** (`ingest_loop.py`) — durably raises non-English
share. (3) **Voice Mix endpoint** `GET /api/v2/voice-mix?hours=&country=`
(#160), formula shared with the audit via `app/services/voice_mix.py`
(single source of truth). (4) **#162 IS ALREADY LIVE** —
`NLP_MULTILINGUAL_MODE=on`, `xlm-v1` (twitter-xlm-roberta); prod confirms
new CJK/RU/FA signals labeled ~100% in-window. The "nlp_*_xlm=0" note was a
MISREAD: on-mode writes production `nlp_*`, not shadow. Remaining #162 =
throughput (#184), not the model — **correct the old handoff.** Live result:
one RSS trigger landed **12 languages, 78% non-English** (ru/fa/ko/zh/de/ar/
fr/ja vs en 77). diversity_score **3.3→4.5 (168h) / 12.1 (fresh cycle)**, CJK
**0→83**, langs 15→21. Honest limiter: english_share_of_known still ~96%
(GDELT English firehose ~52K/168h); score climbs via cjk_coverage+entropy and
lifts english-balance only as the 30-min cron accumulates non-English over
days. 13 tests green (`test_voice_mix.py` 5, `test_ingest_newsdata_cjk.py` 4 +
existing). Doc: `docs/research/voice-mix/2026-06-22-diversify-atlas.md`.
Remaining diversity levers: non-English VOLUME vs GDELT (#229), non-Latin
geo-tagging (#150 — non-Latin headlines fall back to outlet home country),
NLP throughput (#184), folha_pt feed utf-8 decode bug.

**2026-06-22 WAVE 2 follow-ups (two RSS fixes in `ingest_rss.py`):**
(1) **Feed encoding bug FIXED** — `fetch_feed` did `await resp.text()`
(assumes utf-8) → `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xed`
on latin-1/iso-8859-1 feeds. Now `await resp.read()` (bytes); feedparser
detects charset from XML decl/HTTP header. Live verify (7-day window):
**folha_pt 0→100 signals, antaranews_en 50, no decode error.** (2) **#150
first cut — non-Latin geo-tagging.** Latin `\b` `_COUNTRY_PATTERNS` match no
CJK/Cyrillic/Arabic/Devanagari → headlines fell back to outlet country
(DW-Chinese Syria story → DE, not SY). Added `_NATIVE_COUNTRY_PATTERNS` (16
high-volume subject countries × native scripts: CN/JP/KR/KP/TW/RU/UA/IR/IN/
US/IL/GZ/SY/DE), checked after Latin in `extract_country`. CJK = substring
(no word boundaries); Cyrillic/Arabic/Devanagari use Unicode-aware `re \b/\w`.
High-precision/low-recall: only lifts voice when the **headline names the
country in native script** — a zh story naming no place still falls back to
outlet country. Real recall lift = e5/NLP geo path (the clean #150 end
state, still open). 9 tests green (CJK ingest + voice-mix).

**2026-06-22 WAVE 3 (voice RELATION + Islamic world — `3064dd5`, deployed):**
Pedro's ask: separate WHO speaks from WHO is spoken about, finish the mix,
justify it. Plan+justification: `docs/specs/2026-06-22-voice-relation-plan.md`.
Measured Islamic world: covered as subject, ~0 voice — Iran 5,932@1% Persian,
Turkey 4,060@0% Turkish, Pakistan 0% Urdu. (1) **RSS WAVE 6** (9 feeds): Al
Jazeera Arabic + Sky News Arabia (pan-Arab, were absent), BBC Türkçe/Anadolu/
Cumhuriyet (tr), BBC Urdu, Antara (id), BBC Bangla/Prothom Alo (bn). Now 87
feeds / **16 languages** / 49 non-English. (2) **source→subject relation** in
`voice_mix.py` + `/api/v2/voice-mix?country=CC`: `PRIMARY_LANG` map,
`voices_by_origin`, `self_voice_ratio`/`foreign_voice_ratio`/
`dominant_outsider` (endogenous = origin==subject OR lang in subject's primary
langs). LIVE PROOF: Iran self_voice **0.014** (98.6% foreign, dom GB), China
0.316, Turkey 0.240 (was ~0). Subject-vs-voice conflation now a number on a
contract surface. **Caveat:** self-voice is a FLOOR until Problem A (non-Latin
geo-tagging — fa/ar/zh headlines fall back to outlet country, see spawned
task) ships; next build. 13 voice tests green. Justification = §2 of the plan
doc (volume maps launder perspective; diversity unprovable without the
relation; matches the mission; holds our own GDELT English bias accountable).

**2026-06-22 WAVE 4 (self-coverage = OWNERSHIP, source-research project —
`cced104`/`781fbbe`, deployed):** Pedro's correction: BBC Persian covering
Iran is British eyes in Persian, NOT Iranian voice — self-coverage must be by
outlet OWNERSHIP, not language. (1) RSS now persists `source_origin_country`
(was discarded; existing rows backfilled, 93%). (2) `voice_mix.relation`
redefined: `self_voice = origin == subject`; new `soft_power_local_language`
bucket (foreign outlet in local language) tracked SEPARATELY, never counted as
self; ratios over attributable origin, `unattributed` (GDELT, no origin)
reported honestly. LIVE: Iran self_voice **10.4%** domestic, soft_power ~0
(Iran is covered in English-by-foreigners, not even Persian-by-foreigners).
(3) **Verification** (`backend/scripts/self_coverage_report.py`, 14d): most
countries ~0% domestic — CH/BE/GR/BY/CZ/SY/PA/HU/CD at 0%, Iran 10%, US 10%;
strong DE 91%, CO 52%. (4) **WAVE 7** 10 domestic feeds for 9 zero-coverage
countries (ANSA/Repubblica IT, SVT se, Der Standard AT, NOS nl, NRK no, RTE ie,
Expats cz, Granma cu, SANA sy). 97 feeds / 20 languages / 56 non-English. (5)
**Project #235** = "every country a domestic voice" (iterate WAVE N: one
verified domestic outlet per zero-coverage country; normalize GDELT FIPS subject
codes RP/LS/OS/CG; surface self_voice_ratio in CountryBrief). 14 voice tests
green. Caveat: WAVE 7 feeds new = no history, gaps close as cron accumulates.

**2026-06-23 DIVERSITY PROGRAM CONSOLIDATION (`c6e802c`…`fdcbc9d`, deployed):**
Full session arc, end to end. `diversity_score` 3.3→**23.9/100**;
**`voice_entropy` (origin diversity, Pedro's objective metric) = 0.71, ABOVE
the 0.65-0.70 target** over 89 countries. Ingest **50→219 feeds / 126 countries
/ 31 languages / 105 non-English** (waves 5-16; bg-agent assist for last 31
countries; only KW/BH uncovered = bot-block ceiling). Stack: Voice Mix audit +
`/api/v2/voice-mix` (voice_entropy headline); self_voice = OWNERSHIP +
soft_power bucket + CountryBrief surface; Instagram translation (translated by
default + "See original"); **#229** persisted-corpus stratified clustering
(`--from-persisted` cron LIVE every 6h → non-English threads serve, 11→25/run);
**#224** content-entropy roundup classifier (no-shared-subject AND single-outlet
guard spares broad real threads — Ukraine/market crash; `subj<0.30 AND
src>=0.35`); FIPS RP→PH; #162 xlm-v1 confirmed live. **Served threads refresh
every 6h** (clustering cadence), ingest every 30min. Ceiling ~65-70 (English is
real lingua franca; GDELT firehose). Self-maintaining now. Doc:
`docs/research/voice-mix/2026-06-23-diversity-program-consolidation.md`. Tests:
`pytest tests/test_voice_mix.py tests/test_project_dynamic_topics.py tests/test_ingest_newsdata_cjk.py`.

**2026-06-22 WAVE 6 (translations + WAVE 9 — `673b86c`/`6620529`, deployed
Fly+Vercel, browser-verified, #235):** Instagram-style headline translation,
INVERSE affordance (Pedro): non-viewer-language headlines show **translated by
default** + a **"See original"/"Ver original"** toggle. `/api/v2/signals` now
returns `source_lang`; `TranslatableHeadline` lazily hits `/api/v2/translate`
(DeepSeek, cached in signal_translations, client-memoized); en/xx render plain
(no call). Target lang = `navigator.language` → a Spanish-locale viewer gets
English news in Spanish by default. Wired into SignalStream + **CountryBrief
top_stories** (now render headlines + **own-voice sort**: a country's brief
leads with ITS OWN-language press, not only GDELT English about it). KEY
context: GDELT English firehose + snippet-richness ordering bury non-English
RSS everywhere; the CountryBrief own-voice sort is the fix where it matters.
Browser-verified VE: 6 Spanish headlines shown in English, toggle flips to
original Spanish and back, 0 console errors. WAVE 9: New Zealand (RNZ, Stuff) —
last 0% gap; live seed 11 domestic. **109 feeds.** Remaining: more native
volume surfacing (#229), domestic feeds as cron accumulates.

**2026-06-22 WAVE 5 (FIPS normalization + WAVE 8 domestic feeds + CountryBrief
surface — `9b67b22`/`aab072e`, deployed Fly+Vercel, #235):** All 3 parts of
the self-coverage goal. (1) **FIPS:** added `RP→PH` to FIPS_TO_ISO (Philippines
leaked unconverted = false 0% domestic), backfilled 1419 RP→PH/CG→CD rows;
**PH self-coverage 0%→36%** verified. LS/OS/MG = GDELT geocode noise, left.
(2) **WAVE 8** domestic feeds for CH (Le News), BE (VRT), GR (Greek City Times/
Reporter), HU (Telex/Daily News), CD (Actualité.cd/Radio Okapi), BY (Belta
state), PA (TVN) — 107 feeds/21 langs/61 non-English; live seed landed domestic
signals (HU 9, PA 7, BY 6, CD 2). (3) **CountryBrief Voice Mix panel** —
"X% covered by its own press" (color bar, domestic/foreign, dominant outsider,
soft-power note); browser-verified PH 36%. The self_voice = OWNERSHIP metric is
now end-to-end: ingest stores origin → relation by origin → surfaced. Remaining
(#235): next feed waves for any country still at 0% after cron catches up;
normalize remaining FIPS edge codes; full Arabic/tr/ur/bn SUBJECT lexicon for
Problem A.

**Next work, in order:**

0. Problem A — **lexical cut DONE (2026-06-24)**: full Arabic/Turkish/Urdu/
   Bengali SUBJECT lexicon shipped in `ingest_rss.extract_country`
   (`_NATIVE_COUNTRY_PATTERNS` 41→83; `_native_arabic`/`_native_bengali`
   boundary helpers). Now covers ~30 subject countries per script incl. the
   full Arab world + nisba DEMONYMS (المصري→EG, الإيراني→IR, چینی→CN).
   Proven by `tests/test_geo_tagging_native.py` (95/95: recall noun+demonym
   100%, precision 100% — مصرف/عراقيل/قطرة/سوريالي/بھروسا never false-fire;
   held-out generalization confirmed). Boundary regime per script documented
   in code. REMAINING: e5/NLP geo path (recall ceiling for headlines that
   name a place only obliquely; list-order priority + non-Latin subject
   geocoding live there). Continue #235 domestic-feed waves until no Atlas
   country sits at 0% self-coverage.
1. #228 §6 remainder (items 1-2 + #183 + **3 (#176) + 4 gate-recall** done):
   — 3) person hygiene **DONE 2026-06-24** (`96fef18`+`2ae494d`): hardened
     `_is_valid_person` gate (article/repeated-token/multilingual-geo rejects;
     kills "El Niño"/"bafana bafana"/"dar una patada"/"america latina") +
     `rank_key_people` syndication-resistant ranking (DISTINCT headlines/outlets
     + corroboration floor + low-coverage fallback) wired into themes/geo
     person aggregation. Tests `test_person_hygiene.py` (34) +
     `test_person_ranking.py` (6). DEPLOYED + SMOKED (geo 24h=10, focus=8).
   — 3b) **REFRAME person→SUBJECT (Pedro, 2026-06-24)**: panel asked "is this a
     person?" and discarded the rest; correct frame is typed SUBJECTS (person
     is one type). `app/services/subjects.py` (`cb52730`): `classify_subject`
     (NER spaCy label → person/org/group/place/event; untyped GDELT inferred
     via typed gazetteer — geo→place, El Niño→event, teams→org — EXACT match,
     not substring) + `build_key_subjects` (types, syndication-rank, flags
     GDELT-sourced `unverified`). `test_subjects.py` (27). Served as
     `key_subjects`/`keySubjects` in focus+country (`cb52730`/serving commit),
     DEPLOYED + SMOKED LIVE: "america latin"/"republica dominicana" now
     `type=place` (no longer fake people), real people `type=person`, all
     `unverified` (GDELT). **MODEL COMPLETE (backend+CountryBrief), 2026-06-24:**
     (a) NER-typed source wired — focus+country query `nlp_persons`/`_xlm` JSONB
     (`jsonb_array_elements` + `jsonb_typeof` guard) and `merge_entity_rows`
     (NER wins per name, GDELT fills untyped); EVENT added to NER kept-types
     (`nlp_pipeline.py:144`, `bd9swmfoq` deploy). (b) FRONTEND CountryBrief
     ships "Key Subjects" typed (`countryBriefSubjects.ts` mirrors backend;
     type badges; only person chips clickable) — browser-verified, replaced the
     hardcoded `countryBriefPeople.ts` blocklist (`c47c523`). DEPLOYED+SMOKED:
     US los angeles/las vegas→place, IR abu dhabi→place + netanyahu→person, CO
     america latin→place. **FINDING:** all subjects still come back
     `unverified=true` — NER query returns 0 rows because `nlp_persons` is
     near-empty in served windows (NLP throughput, **#184**), so the gazetteer
     carries typing honestly; the verified layer lights up only as NLP coverage
     grows. REMAINING: EntityPanel/ThemeDetail still render the old "People"
     list (other surfaces); CountryBrief uses a hand-mirrored TS gazetteer (the
     server `key_subjects` is the eventual single source of truth).
     CONVERGES WITH #234: every subject (person/place/event/thread/country) on
     click should re-scope all surfaces (map centers on where its info
     concentrates) — #234 slice 1 (country) shipped, thread/person pending.
   — 4) gate-recall SQL report = `scripts/gate_recall_by_language.py` (already
     shipped, `4911051`, 7 tests).
   REMAINING: 5) map hovers + PLANE degraded state, 6) keyword-match labels
   (both frontend, need preview verification). Plus #230 China/East-Asia voice
   gap (acquisition + #162 dep).
2. #229 funnel scaling program (data layer; lever 1 = corpus clustering).
2. #183 panel remainder (sentiment_source badge + heat_countries panel
   in L2; the L1 strip already shipped with the Brief rebuild).
3. Workbench pin-snapshot + per-pin note (#227, Phase 3 prerequisite).
4. Parallel, non-blocking: #219 Kalman movement feed; #217 credibility
   tiers; #220 funnel ledger; #221 maturity contract; #222 stratified
   snapshot sampling.
5. Later phases: Phase 3 report view from pinned state (dossier defined in
   review §5); Phase 4 evidence/frame quality bound to Paper 1 benchmarks.
6. Mobile visualization (#236, roadmap, NOT scheduled): phone-native
   presentation, not a shrunk desktop — strip down + re-shape per surface.
   L0 Landing + L1 Brief = near-term polish (already responsive); L2 console
   mobile IA + L3 Workspace = larger project, coordinate with #228.

Tests: research suites = `pytest tests/test_research_*.py` (22 tests).
Deploy: `./scripts/deploy-fly-api.sh`. Prod smoke:
`curl -s -X POST https://atlas-api-pedro.fly.dev/api/v2/research/plan -H 'Content-Type: application/json' -d '{"query":"Iran climate water drought","hours":168}'`.

## Prior Session Context (2026-06-09, Research Workflow + Workbench target)

Current branch is `v3-intel-layer` and is aligned with `origin/v3-intel-layer`.
Commit `ca2130b` shipped the search query-thread builder (#175), Signal Stream
relevance lanes (#177 slice 1), source-available license migration, and
CountryBrief thread-count alignment (#174/#207). Fly API was deployed with
`scripts/deploy-fly-api.sh`; Vercel is serving the matching frontend bundle.

The latest local work adds a read-only Kalman/state report:
`backend/scripts/dynamic_topic_state_report.py`, tested by
`backend/tests/test_dynamic_topic_state_report.py`, with artifacts under
`docs/research/topic-quality/2026-06-09-dynamic-topic-state-pilot.*`.

Pedro then promoted the Iran climate/water search experiment into the next major
product target: natural compound search should become a guided Atlas research
workflow where search produces anchors/options, the user opens and pins useful
items, and Workbench becomes the investigation memory. The detailed spec is
`docs/specs/2026-06-09-research-thread-builder-workbench.md`.

Important current guardrails:

- The visible product model is Narrative Threads. Do not present fixed GDELT
  themes or curated concept-map suggestions as the user-facing topic model.
- `dynamic_topics` and Narrative Threads are not separate product concepts.
  Treat `dynamic_topics` as the implementation/lifecycle backing record for
  user-facing threads.
- CountryBrief must not count a forced `topCounts(themeCounts, 12)` slice as
  visible "themes". It now fetches
  `/api/v2/threads?hours=<window>&limit=24&country_code=<country>` and uses that
  country-scoped thread response for the visible `threads` metric and Narrative
  Threads list.
- If a country has signals but no coherent thread clears the quality gate, show
  `0 threads` / an explanatory empty state; do not fall back to GDELT theme
  volume.
- Secret rotation was intentionally deferred and remains a separate maintenance
  pass before the next credential-bearing deploy cycle.
- Do not reopen #175/#177 unless a new regression appears; create narrower
  follow-ups for additional stream taxonomy or search-demand tracking.
- Kalman filtering, if explored next, belongs in a read-only dynamic-topic state
  tracking pilot (smoothed intensity, velocity, uncertainty, surprise), not as a
  semantic classifier replacement.
- The pilot now exists and must remain read-only unless Pedro explicitly asks to
  promote it into persistence/cron. It keeps `lifecycle_state` separate from
  `state_estimate` and flags explicit roundups as `do_not_promote_roundup`.
- Research Workflow + Workbench is the next target. It should solve broad
  searches like "climate/water in Iran" plus related branches like "attacks on
  US/allied bases, satellite imagery, communications/radar infrastructure, and
  regional water/energy security" by producing anchors/options, who-says-what,
  frame comparison, coverage gaps, pin candidates, and a Workbench route.
- Research search ranking should optimize investigative usefulness: intent fit,
  thread coherence, evidence strength, answerability, movement, source/actor
  value, geo/entity fit, novelty/gap value, and penalties for noise,
  unsupported claims, or list/detail mismatch.
- Do not implement ranking as silent filtering. The Research Workflow spec now
  requires reason codes, ranking explanations, a downranking/omission ledger,
  and inspectable low-confidence/noisy trays.
- Reddit/forum discussion belongs in a public-attention / narrative-discovery
  lane. It can suggest branches and show claims/questions/links, but it is not
  verified evidence by default.
- Workbench should support multiple saved investigations in a sidebar/history;
  pins from unrelated sessions should not silently mix.
- Do not frame the first search response as a finished dossier. The report is an
  optional later output generated from pinned Workbench state.
- Do not treat this as an Iran-only feature. The Iran case is the fixture and
  acceptance test for a general natural research-search capability.

Verification from 2026-06-08:

- Backend focused suite for query-thread + stream lanes: `28 passed`.
- Frontend focused suite for country/thread/search/empty-state helpers: `4 files
  passed / 8 tests`.
- `frontend-v2` production build passed.
- Production smoke after deploy passed: `/api/v2/search/thread` returned `200`,
  `/app?country=CO` showed `10 THREADS` with no `Top Themes`, and clicking
  "Build a thread" opened `CUSTOM THREAD` without `HTTP 404`.
- Dynamic-topic state pilot verification:
  `cd backend && .venv/bin/python -m pytest tests/test_dynamic_topic_state_report.py tests/test_project_dynamic_topics.py -q`
  -> `18 passed`; live read-only report generated JSON/Markdown artifacts.

See `docs/research/topic-quality/2026-06-09-dynamic-topic-state-pilot.md` for
the current pilot output.
See `docs/specs/2026-06-09-research-thread-builder-workbench.md` for the next
implementation target.

## Prior Session Context (2026-06-02, dynamic topics backend cutover)

### Phase 6 dynamic topics read path

- `dynamic_topics` is no longer shadow-only for local backend reads.
  `/api/v2/threads` now prefers active `dynamic_topics` when available;
  atlas-topic and raw emergent-cluster rows remain fallbacks.
- `/api/v2/briefing.top_atlas_topics` now prefers `dynamic_topics` and exposes
  `source_table="dynamic_topics"`, `model_version="dynamic-topics-v1"`, and
  `noise_rate`. Raw `emergent_clusters` and static atlas assignments remain
  fallback sources.
- `/api/v2/theme/dynamic-topic-<id>` resolves Watchlist clicks through member
  `emergent_clusters.sample_signal_ids`, preserving the existing
  `ThemeDetail` contract without re-running clustering or calling paid APIs.
- Local smoke on 2026-06-02 through `/Users/pedro/AtlasLocalWorker/.env`:
  `/api/v2/threads?hours=24&limit=5` returned top `dynamic-topic-*` rows;
  `/api/v2/briefing?hours=24` returned
  `top_atlas_topics_source=dynamic_topics`; `/api/v2/theme/dynamic-topic-10`
  returned "Russia Warns on Baltic and Zaporizhzhia",
  `source=dynamic_topics`, `total=287`, `signalSample=141`.
- Remaining before calling it fully shipped: deploy backend and browser-smoke
  `/brief`, Watchlist clicks, Narrative Threads, and ThreadFocusPanel. The
  observed degraded briefing segment `theme_country` is separate from this
  cutover.

## Prior Session Context (2026-06-01, external storage + emergent layer Phase 3 cron LIVE)

### Local storage relocation

- Atlas raw archive storage has moved to the 2TB external disk:
  `/Volumes/Ext/Atlas/Archive`.
- `/Users/pedro/AtlasArchive` is intentionally a symlink to that external
  archive path so existing scripts and docs continue to work.
- `scripts/run-local-hot-cold-catchup.sh` now defaults to:
  - archive root: `/Volumes/Ext/Atlas/Archive`
  - processed historical output: `/Volumes/Ext/Atlas/Processed`
- The runner exits with status `2` if the configured archive root is under
  `/Volumes/*` and the external volume is not mounted.
- The installed worker copy at
  `/Users/pedro/AtlasLocalWorker/run-local-hot-cold-catchup.sh` was synced from
  the repo runner.
- Verification on 2026-06-01: all `59` archive manifest directories under the
  symlink verified successfully, covering `272` manifest records and
  `3,947,759` represented rows.

The emergent topic discovery layer is wired end-to-end and shipped to
production. Full handoff lives at
`docs/state/2026-05-30-phase-2-emergent-wiring-handoff.md`; this block
is the pointer.

### What is now live

- **Migration 046** (`backend/migrations/046_emergent_clusters.sql`)
  applied to Supabase. `emergent_clusters` table with RLS + 3
  secondary indexes.
- **`/api/v2/briefing.top_atlas_topics`** now sources from the latest
  `emergent_clusters` snapshot when available, falling back to the
  static `signal_topic_assignments` ranking when no snapshot is fresh.
  Field-mapped to the existing frontend contract so the brief
  Watchlist surface renders unchanged.
- **`GET /api/v2/theme/cluster-<id>`** new branch in `themes.py` →
  `_emergent_cluster_detail` resolves cluster rows by id, joins
  `signals_v2` against the persisted `sample_signal_ids`, returns the
  same theme-detail shape so `ThemeDetail` panel renders without
  changes.
- **`GET /api/v2/emergent`** dedicated inspector endpoint.
- **`backend/scripts/snapshot_emergent_topics.py`** writes one row per
  surviving cluster, computes velocity vs the most recent prior
  snapshot, translates HDBSCAN local indices → `signals_v2.id` before
  persisting.
- First production snapshot written at `2026-05-31T03:35:13Z`: 16
  surviving clusters from 11,539 dedup'd signals.
- **Phase 3 cron is installed and verified.**
  `scripts/run-emergent-snapshot.sh`,
  `scripts/install-emergent-snapshot-launchd.sh`, and
  `infra/launchd/com.atlas.emergent-snapshot.plist` are now versioned.
  The installed runner lives at
  `/Users/pedro/AtlasLocalWorker/run-emergent-snapshot.sh` and reads
  credentials from `/Users/pedro/AtlasLocalWorker/.env` (mode `600`),
  not from the Desktop repo `.env`.
- Verification run on 2026-06-01:
  `com.atlas.emergent-snapshot` pulled 15,000 hot signals, deduped to
  13,031 headlines, embedded with e5-base, found 12 raw HDBSCAN
  clusters, kept 9 after the precision gate, labeled via DeepSeek, and
  wrote 9 `emergent_clusters` rows. `launchctl list
  com.atlas.emergent-snapshot` reported `LastExitStatus = 0`.

### Atlas-topic cron is healthy

Earlier handoffs noted "stopped since 2026-05-27". Verified
2026-05-30 22:05: launchd runs `com.atlas.atlas-topic-classifier`
every 30 min including the gate-scoring step. Confirmed via
`launchctl list | grep atlas` + tailing
`~/AtlasLocalWorker/logs/atlas-topic-classifier.{err,out}.log`.

### Threads wiring (2026-05-31) — closed

Pedro caught the Phase 2 surface miss via mobile screenshot
(2026-05-30). `/api/v2/threads` was the unwired panel. Resolved this
session:

- `backend/app/services/thread_intelligence.py` now ships
  `assemble_emergent_thread` + `_fetch_emergent_threads_with_conn`.
  `fetch_threads` merges atlas + emergent (sorted by `signal_count`
  DESC) and the `emergent-cluster-<id>` `thread_id` prefix routes
  `fetch_thread_detail` through `_fetch_emergent_thread_detail`.
- Production verified at `https://atlas-api-pedro.fly.dev/api/v2/threads?hours=24`
  returns merged threads (atlas + 1 emergent at signal_count 74 with
  the current snapshot), `contract=living-narrative-threads-v0`. Detail
  dispatch returns 200 for both prefixes (`emergent-cluster-17` and an
  atlas thread).
- `backend/tests/test_threads_emergent_augment_shape.py` freezes the
  contract (6 shape guardrails; 28/28 tests across threads + emergent
  + briefing).

Known follow-up: evidence headlines come through HTML-entity-encoded
(`&#xNNNN;`) in `_serialize_evidence`. Pre-existing issue affecting
both atlas and emergent paths; `html.unescape` on the headline is the
small fix.

### Current state and next-session priorities

See `docs/state/2026-05-30-context-gap-inventory-proposal.md` for the
diagnosis and proposal.

1. **Phase 6 status:** `dynamic_topics` hydrates incrementally after the
   emergent snapshot cron, uses local e5 + evidence-role student noise gating
   (`$0` API), caches per-cluster noise in
   `emergent_clusters.role_noise_rate`, has guarded rebuild-only merge/dedup,
   and is now the preferred local backend source for `/api/v2/threads` and
   `/api/v2/briefing.top_atlas_topics`.
2. **Next major block:** deploy the backend cutover and browser-smoke `/brief`,
   Watchlist clicks, Narrative Threads, and ThreadFocusPanel before declaring
   full product shipment.
3. **Validation guardrail:** local Ollama on Pedro's M1 is deprecated for Atlas
   judging/teacher labels after the 2026-06-02 `llama3.2:1b` pilot scored 25%
   decision accuracy on 20 reviewed batch 02 rows. Keep outputs in `ollama_*`
   fields only.
4. Polish: `html.unescape` on `_serialize_evidence` headlines; bump
   `sample_signal_ids` cap from 8 to ~24 in the snapshot script; add
   frontend rendering of `velocity` to brief Watchlist row markup.
5. Translation follow-up: Phase 5 is implemented (`signal_translations`,
   `/api/v2/translate`, `/api/v2/translate/batch`, bilingual
   `ThreadFocusPanel`); only tune UX/caching if live review shows friction.

### Quick orientation commands

```bash
# Verify cron health
launchctl list | grep atlas

# Verify local/backend brief source after dynamic-topic cutover
curl -s 'https://atlas-api-pedro.fly.dev/api/v2/briefing?hours=24' \
  | jq '.top_atlas_topics[0].source_table'
# expected after deploy: "dynamic_topics"

# Inspect latest snapshot
psql "$DATABASE_URL" -c "
  SELECT label, n_signals, raw_signal_count, velocity, top_country_codes
  FROM emergent_clusters
  WHERE snapshot_at = (SELECT MAX(snapshot_at) FROM emergent_clusters)
  ORDER BY velocity DESC NULLS LAST, n_signals DESC LIMIT 10;"
```

## Archived chronological session blocks

Older session-context blocks (2026-05-21 → 2026-05-29) moved to
`docs/state/archive/CLAUDE-history-2026-05.md` so this file stays scannable.
Run `python scripts/project_inventory.py` for the machine-verified current
map of endpoints / frontend ↔ API / DB tables / cron / recent commits.


## Specialized Agents

The project uses a multi-agent architecture where each agent has specific expertise. The **Orchestrator** coordinates these agents based on task requirements.

### Agent Summary

| Agent | Purpose | When to Call |
|-------|---------|--------------|
| orchestrator | Coordinates multi-agent workstreams | Starting sessions, planning iterations, QA reviews, managing blockers |
| backend-flow-engineer | Implements API endpoints and backend logic | Flows API, health endpoints, trends endpoints, caching, migrations |
| data-geointel-analyst | Handles geointelligence data sources | GDELT/Trends/Wikipedia clients, topic normalization, scoring algorithms |
| data-signal-architect | Designs signal processing systems | Schema design, Redis caching, signal validation, mobile optimization |
| narrative-geopolitics-analyst | Analyzes narrative propagation | Drift detection, mutation patterns, source analysis, visualization design |
| frontend-map-engineer | Implements map visualizations | Mapbox components, geospatial displays, real-time updates |

---

## Agent Details

### Orchestrator

**Purpose**: Senior technical orchestrator for multi-agent coordination, work prioritization, and incremental delivery.

**When to Call**:
- Starting a new session and need to pick up where work left off
- Planning the next iteration after receiving outputs from multiple agents
- Multiple PRs need QA coordination
- Blocking issues affect multiple workstreams
- Breaking down high-level goals into trackable issues

**Key Responsibilities**:
- Convert iteration goals into small, focused GitHub issues
- Manage handoffs between agents with complete context
- Enforce PR hygiene standards
- Produce daily planning artifacts
- Track and label risks by category

**Interaction with Backend Tasks**:
- Creates issues for backend agents with clear acceptance criteria
- Sequences backend work to minimize idle time
- Coordinates data pipeline outputs with API endpoint implementations
- Ensures database migrations are properly sequenced

---

### Data Signal Architect

**Purpose**: Expert in large-scale signal processing, time-series data architectures, anomaly detection, and cross-source data normalization. Specializes in PostgreSQL schema design and Redis caching strategies for lightweight, mobile-ready systems.

**When to Call**:
- Designing signals schemas for multi-source narrative tracking
- Implementing time-bucketing strategies (15-min vs 1-hour)
- Reviewing or optimizing Redis caching implementations
- Validating incoming signals and detecting synthetic data
- Integrating new data sources into existing pipelines
- Optimizing queries for mobile deployment

**Core Expertise**:
- **Signals Schema Design**: Temporal, geographic, and topic dimensions with proper constraints and indexes
- **Time-Bucketing Strategy**: 15-minute buckets for real-time, 1-hour for trend analysis
- **PostgreSQL Optimization**: Efficient data types, index strategies, constraint definitions
- **Redis Caching**: Key patterns, expiration policies, memory budgets (500MB max)
- **Signal Validation**: Source verification, volume sanity, sentiment bounds, URL validation
- **Mobile Optimization**: <100ms queries, <50KB responses, gzip compression

**Interaction with Backend Tasks**:
- Provides schema DDL for database migrations
- Defines caching key patterns for backend services
- Validates signal processing logic against data quality requirements
- Recommends index strategies for API endpoint queries
- Reviews backend implementations for performance and efficiency

**Execution Guidelines**:
- Always include complete DDL with constraints and indexes
- Provide storage and performance estimates
- Include example queries demonstrating index usage
- Document edge cases and error handling
- Target 100ms query latency and 1000 signals/minute throughput

---

### Narrative Geopolitics Analyst

**Purpose**: Expert in global information ecosystems, disinformation analysis, narrative framing, and comparative media analysis. Provides domain insight on how narratives propagate, mutate, and polarize across regions and platforms.

**When to Call**:
- Analyzing how topics are framed differently across countries
- Defining narrative mutation patterns (framing shifts, emphasis changes, attribution flips)
- Implementing drift detection algorithms (geographic, temporal, cross-platform)
- Specifying API schemas for narrative intelligence endpoints
- Interpreting signals from different source families
- Designing visualizations for narrative data
- Adding geopolitical context flags to the system

**Core Expertise**:
- **Narrative Mutation Types**: Framing shifts, emphasis mutations, omissions, amplifications, minimizations, attribution flips
- **Drift Detection**: Geographic drift scores, temporal sentiment trajectories, cross-platform divergence
- **Source Family Analysis**: GDELT, Google Trends, and Wikipedia coverage patterns, biases, and reliability
- **Geopolitical Context**: State media flags, echo chamber detection, information deserts, polarization thresholds
- **Visualization Design**: Geographic heatmaps, cluster views, temporal timelines, narrative flow diagrams

**Interaction with Backend Tasks**:
- Defines API response schemas with required metadata fields
- Provides Python implementations for drift detection algorithms
- Specifies validation rules for narrative signals
- Recommends data structures for stance and cluster tracking
- Defines confidence scoring methodologies

**Execution Guidelines**:
- Provide at least 3 concrete examples for each concept
- Include quantitative metrics with specific formulas and thresholds
- Supply Python code with type hints when algorithms are requested
- Include complete JSON schemas for API responses
- Provide user-facing plain language explanations
- Document testing recommendations and success criteria

**Collaboration**:
- Works with **DataGeoIntel** to ensure source normalization aligns with narrative needs
- Validates with **DataSignalArchitect** that signals schema includes stance and cluster fields
- Coordinates with **BackendFlow** for efficient narrative query endpoints
- Provides UX guidance to **FrontendMap** for visualization implementations

---

### Backend Flow Engineer

**Purpose**: Implements and modifies the flows API, health endpoints, trends endpoints, and intelligence enrichment endpoints in the Python/FastAPI backend.

**When to Call**:
- Implementing API endpoints (all under `/api/v2/...`; crisis endpoints under `/api/v3/...`)
- Implementing caching strategies with Redis
- Writing database migrations for PostgreSQL (raw `.sql` files in `backend/migrations/`)
- Calculating heat formulas and similarity scores
- Writing tests for backend functionality
- Adding new data source integrations (ACLED, OpenSky, AISStream)

**Interaction with Backend Tasks**:
- Implements endpoints following Pydantic model patterns in `app/models/`
- Creates database migrations run via Supabase SQL editor (NOT alembic)
- Implements caching with key patterns from DataSignalArchitect
- Writes unit and integration tests in `backend/tests/`

---

### Data GeoIntel Analyst

**Purpose**: Works on geointelligence data analysis tasks involving GDELT, Google Trends, and Wikipedia data sources.

**When to Call**:
- Validating or implementing data source clients
- Creating topic normalization logic for cross-country comparisons
- Implementing intensity scoring algorithms
- Writing ADRs for time windows or decay formulas
- Creating dataset snapshots with manifests
- Documenting API quotas and error recovery strategies

**Interaction with Backend Tasks**:
- Provides client implementations for data sources
- Defines normalization pipelines for topic extraction
- Implements scoring formulas (heat, intensity, similarity)

---

### Frontend Map Engineer

**Purpose**: Implements interactive map visualizations using React, MapLibre GL, and DeckGL v9.

**When to Call**:
- Adding circle markers/hotspots to maps (ScatterplotLayer)
- Creating animated flow lines between countries (ArcLayer)
- Building map-related UI components (filters, sidebars, chokepoint panels)
- Handling real-time data updates with auto-refresh (aircraft 15s poll, vessels 30s poll)
- Implementing custom DeckGL layers (e.g. TerminatorLayer)

**Critical Rules for Frontend:**
- Use **Vanilla CSS** for all dashboard components. CSS custom properties come from `ThemeContext`.
- **Tailwind CSS** is installed but used **exclusively for `Landing.tsx`** (the public marketing page). Do NOT add Tailwind classes to dashboard components.
- Use `data-tip="text"` for tooltips on any element — NEVER use native `title=` attributes.
- Components live in `frontend-v2/src/components/`. Current count: **36 .tsx components**.
- Always run `npm run build` (not just `tsc --noEmit`) before pushing — Vite's `tsc -b` is stricter.
- `InteractiveWorkspace.tsx` (the force-graph canvas) is lazy-loaded via `React.lazy()` inside `InvestigationWorkspace.tsx` — do NOT import it directly or it will blow the main bundle.
- Theme labels: always call `getThemeLabel(theme_code)` from `lib/themeLabels.tsx`. Do NOT trust the `label` field returned by the API — the API field may be raw GDELT codes.

---

## AI Model Coordination: Claude, Gemini, and Codex

This project uses three AI models in coordination, each with distinct strengths. Understanding when to use each model maximizes efficiency and output quality.

### Claude's Role: Orchestration and Reasoning

Claude serves as the **orchestrator and system-level reasoning engine**.

**Primary Responsibilities:**

- High-level design, architecture, and planning
- Multi-agent coordination and task sequencing
- Narrative analysis and data interpretation
- Schema design and technical decisions
- Complex reasoning requiring deep context
- Documentation and specification writing
- **Automatic delegation** to Gemini and Codex when appropriate

**When to Use Claude:**

- Starting a session and planning work
- Designing database schemas or API architectures
- Analyzing narrative patterns or drift detection algorithms
- Making technical decisions with tradeoffs
- Coordinating multiple workstreams
- Writing ADRs or architectural documents

**Automatic Delegation Rules:**

Claude should automatically:

1. **Delegate to Gemini** when large multi-file context is needed
2. **Delegate to Codex** when code generation or execution is required
3. **Keep reasoning centralized** within Claude
4. **Combine outputs** from Gemini + Codex into coherent plans

**Orchestration Workflow:**

```text
1. Claude analyzes the goal
2. If large multi-file context needed → Claude triggers Gemini CLI
3. Claude receives Gemini's output and reasons about it
4. If code generation/execution needed → Claude triggers Codex CLI
5. Claude merges all results and produces high-level reasoning
```

**Example Commands:**

```bash
# Claude Code CLI for orchestration
claude "Review the handoff document and create today's plan"
claude "Design the PostgreSQL schema for GDELT signals"
claude "Analyze how drift detection should work across geographic regions"
```

---

## Using Gemini CLI for Large Codebase Analysis

Gemini CLI leverages Google Gemini's massive context window for analyzing large codebases or multiple files that would exceed Claude's context limits.

### Gemini Purpose

Use Gemini CLI when:

- Analyzing large codebases or multiple files that exceed context limits
- Reviewing or comparing full directories
- Scanning for patterns across many files
- Verifying complex implementations scattered across the codebase
- Loading hundreds of files at once
- Performing static read-only analysis requiring massive context

### Gemini Syntax

Use `gemini -p` for non-interactive mode with prompts:

```bash
gemini -p "<prompt here>"
```

### File and Directory Inclusion

Use the `@` syntax to include files and directories. Paths are relative to your current working directory:

#### Basic Examples

**Single file analysis:**

```bash
gemini -p "@src/main.py Explain this file's purpose and structure"
```

**Multiple files:**

```bash
gemini -p "@package.json @src/index.js Analyze the dependencies used in the code"
```

**Entire directory:**

```bash
gemini -p "@src/ Summarize the architecture of this codebase"
```

**Multiple directories:**

```bash
gemini -p "@src/ @tests/ Analyze test coverage for the source code"
```

**Current directory and subdirectories:**

```bash
gemini -p "@./ Give me an overview of this entire project"
```

**All files automatically:**

```bash
gemini --all_files -p "Analyze the project structure and dependencies"
```

### Implementation Verification Examples

**Check if a feature is implemented:**

```bash
gemini -p "@src/ @lib/ Has dark mode been implemented in this codebase? Show me the relevant files and functions"
```

**Verify authentication implementation:**

```bash
gemini -p "@src/ @middleware/ Is JWT authentication implemented? List all auth-related endpoints and middleware"
```

**Check for specific patterns:**

```bash
gemini -p "@src/ Are there any React hooks that handle WebSocket connections? List them with file paths"
```

**Verify error handling:**

```bash
gemini -p "@src/ @api/ Is proper error handling implemented for all API endpoints? Show examples of try-catch blocks"
```

**Check for rate limiting:**

```bash
gemini -p "@backend/ @middleware/ Is rate limiting implemented for the API? Show the implementation details"
```

**Verify caching strategy:**

```bash
gemini -p "@src/ @lib/ @services/ Is Redis caching implemented? List all cache-related functions and their usage"
```

**Check for specific security measures:**

```bash
gemini -p "@src/ @api/ Are SQL injection protections implemented? Show how user inputs are sanitized"
```

**Verify test coverage for features:**

```bash
gemini -p "@src/payment/ @tests/ Is the payment processing module fully tested? List all test cases"
```

### When to Use Gemini

- Analyzing entire codebases or large directories
- Comparing multiple large files
- Understanding project-wide patterns or architecture
- Context window is insufficient for the task
- Working with files totaling more than 100KB
- Verifying if specific features, patterns, or security measures are implemented
- Checking for coding patterns across the entire codebase

### When NOT to Use Gemini

- **Generating new code** (use Codex instead)
- **Executing commands** (use Codex instead)
- **Small context tasks** that fit in Claude's window
- **Code refactoring or implementation** (use Codex instead)

### Important Notes

- Paths in `@` syntax are relative to your current working directory when invoking gemini
- The CLI will include file contents directly in the context
- No need for --yolo flag for read-only analysis
- Gemini's context window can handle entire codebases that would overflow Claude's context
- When checking implementations, be specific about what you're looking for to get accurate results

---

## Using Codex CLI for Code Generation and Execution

Codex CLI is optimized for heavy code generation, refactoring, and execution tasks. It specializes in writing and modifying code with high quality output.

### Codex Purpose

Use Codex CLI when:

- Generating large code modules or full files
- Performing refactors across many files
- Generating test suites or documentation
- Scaffolding entire features or microservices
- Executing code or commands
- Running project automation tasks (formatters, linters, migrations)
- Transforming files requiring "write access"

### Codex Syntax

Use `codex -p` for prompting:

```bash
codex -p "<prompt here>"
```

Codex also supports the `@file` and `@directory/` syntax for including context.

### Code Generation Examples

**Implement an endpoint:**

```bash
codex "Implement GET /api/v2/narratives/topic endpoint in backend/app/main_v2.py following the existing endpoint patterns"
```

**Write tests:**

```bash
codex "Write unit tests for the gdelt_parser.py parse_v2_tone function"
```

**Create TypeScript types:**

```bash
codex "Create TypeScript interfaces in frontend/src/lib/types.ts matching the GDELTSignal Pydantic model"
```

**Refactor for performance:**

```bash
codex "Refactor the flow_detector.py to use numpy vectorization instead of nested loops"
```

**Fix a specific bug:**

```bash
codex "Fix the heatmap rendering issue in HexagonHeatmapLayer.tsx where hexagons are not appearing"
```

### File Context Examples

**Generate tests with context:**

```bash
codex -p "@backend/ Generate a complete test suite for all services"
```

**Refactor with file context:**

```bash
codex -p "@src/ Refactor all API handlers to use dependency injection"
```

**Create new module:**

```bash
codex -p "@app/ Create a new logging module and integrate it"
```

**Full CRUD generation:**

```bash
codex -p "@./ Build a full CRUD module for the User entity"
```

### Execution Examples

Run commands directly through Codex:

```bash
codex run tests
codex run "npm install"
codex run "pytest -q"
codex -p "@scripts/ Execute the migration scripts and show output"
```

### When to Use Codex

- Implementing new API endpoints
- Writing tests for services
- Creating React components
- Refactoring modules for performance
- Generating Pydantic models or TypeScript interfaces
- Fixing bugs in specific files
- Running project commands

### When NOT to Use Codex

- **Analyzing very large contexts** (use Gemini instead)
- **Deep reasoning or cross-file orchestration** (Claude handles this)
- **Verifying architecture or patterns** (use Gemini instead)
- **Planning and decision-making** (use Claude instead)

---

## Combined Workflow

The three models work together in a coordinated pipeline:

```
┌─────────────────────────────────────────────────────┐
│                    WORKFLOW                          │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. CLAUDE THINKS                                   │
│     ├─ Review context and plan                      │
│     ├─ Design architecture                          │
│     └─ Coordinate agents                            │
│                    ↓                                │
│  2. GEMINI INSPECTS                                 │
│     ├─ Analyze codebase                             │
│     ├─ Verify implementations                       │
│     └─ Check patterns                               │
│                    ↓                                │
│  3. CODEX IMPLEMENTS                                │
│     ├─ Write code                                   │
│     ├─ Create tests                                 │
│     └─ Apply fixes                                  │
│                                                     │
│  ═══════════════════════════════════════════════   │
│  All models can run in PARALLEL for independent    │
│  tasks to maximize efficiency                       │
└─────────────────────────────────────────────────────┘
```

**Example Combined Workflow:**

```bash
# Step 1: Claude plans the work
claude "Design the schema for storing narrative clusters with drift scores"

# Step 2: Gemini checks existing patterns
gemini -p "@backend/app/models/ @backend/app/db/ Analyze existing database patterns and constraints"

# Step 3: Codex implements
codex "Create the narrative_clusters table migration following the patterns identified"

# Parallel execution for independent tasks
claude "Design visualization spec" &
gemini -p "@frontend/ Check component structure" &
codex "Implement the tooltip component" &
wait
```

---

## Quick Reference: When to Pick Each Model

| Task Type | Model | Reason |
|-----------|-------|--------|
| Planning and coordination | **Claude** | Complex reasoning, context management |
| Architecture design | **Claude** | Tradeoff analysis, system thinking |
| Codebase-wide analysis | **Gemini** | Large context window |
| "Does X exist in the code?" | **Gemini** | Full repo search |
| Security/pattern audit | **Gemini** | Cross-file analysis |
| Implement endpoint | **Codex** | Code generation |
| Write tests | **Codex** | Implementation |
| Refactor module | **Codex** | Code transformation |
| Fix specific bug | **Codex** | Targeted edits |
| Schema design | **Claude** | Domain expertise |
| TypeScript types | **Codex** | Type generation |
| Execute commands | **Codex** | Command execution |

---

## Concrete Examples by Task

**Task: Add a new API endpoint for narrative topics**

```bash
# 1. Claude designs the API schema
claude "Design the /api/v2/narratives/topic endpoint with request/response schemas"

# 2. Gemini checks existing endpoint patterns
gemini -p "@backend/app/main_v2.py Show me the pattern used for existing endpoints including error handling"

# 3. Codex implements the endpoint
codex "Implement /api/v2/narratives/topic in backend/app/main_v2.py using the designed schema and existing patterns"
```

**Task: Optimize database queries**

```bash
# 1. Gemini identifies slow queries
gemini -p "@backend/app/services/ @backend/app/api/ Find all database queries and identify which ones might be slow"

# 2. Claude designs optimization strategy
claude "Design index strategy for the identified slow queries"

# 3. Codex implements the indexes
codex "Add the recommended indexes to the migration file"
```

**Task: Debug a rendering issue**

```bash
# 1. Gemini finds related code
gemini -p "@frontend/src/components/map/ Show all code related to hexagon rendering"

# 2. Claude analyzes the issue
claude "Analyze why hexagons might not be rendering based on the code"

# 3. Codex fixes the bug
codex "Fix the hexagon rendering issue in HexagonHeatmapLayer.tsx"
```

**Task: Add test coverage**

```bash
# 1. Gemini identifies untested code
gemini -p "@backend/app/services/ @backend/tests/ Which services have less than 80% test coverage?"

# 2. Codex writes the tests
codex "Write comprehensive tests for gdelt_parser.py covering all edge cases"
```

---

## Development Workflow

### Starting a Session

1. Call the **Orchestrator** to review handoff documentation
2. Assess current blockers and prioritize work for the window
3. Create daily plan with agent assignments

### Working on Tasks

1. Use the appropriate specialized agent for each task type
2. Maintain small, focused PRs (<300 lines)
3. Update todos as work progresses
4. Document decisions in ADRs when ambiguity appears

### Ending a Session

1. Complete handoff documentation
2. Update state documents
3. Tag any unresolved blockers
4. Push changes to GitHub

---

## Quality Standards

### PR Hygiene

- Small, focused diffs
- All tests passing
- Structured, useful logs
- Updated .env.example for new environment variables
- Clear commit messages following conventional commits

### Definition of Done

- [ ] Compiles successfully with no errors
- [ ] All tests pass
- [ ] Logs are structured and useful
- [ ] Environment variables documented
- [ ] ADR exists for non-trivial decisions
- [ ] Documentation updated
- [ ] Handoff notes complete

---

## Current Technical State (as of session 13 — 2026-05-17)

### Session 13 Additions (P0 productization pass — PR #144)

**Briefing prefetch (#136)**
- `frontend-v2/src/lib/briefingPrefetch.ts` — sessionStorage cache with 4-min TTL for briefing + insight API responses.
- `Landing.tsx` prefetches on mount. `BriefNewspaper.tsx` reads cache before fetch — no spinner when entering `/brief` from Landing.

**Editor's Analysis restored (#137)**
- `BriefNewspaper.tsx`: `buildGlobalFallback(d)` — 4 rotating variants (theme-lead, geography-lead, sentiment-lead, volume-first).
- `buildCountryFallback(detail)` — 3 country variants.
- `Math.random()` per render for angle rotation — intentional, not seeded.
- Removed all `themeSignals[theme][0]` headline anchors — signals misclassification risk.
- All country names via `resolveCountryName(code, name)` — never raw `c.name`.

**Investigation context preservation (#138)**
- `App.tsx`: `prevStreamCtx` union extended with `country` type.
- Back from source → CountryBrief; Back from country → thread if theme was active.

**Public Attention scoped to active country (#142)**
- `AnomalyPanel.tsx`: re-fetches Wiki on `activeCountry` change; Trends + Wiki merged into single PUBLIC ATTENTION section.
- `[S]` (green) badge for searches, `[W]` (indigo) badge for wiki articles.
- Staleness indicator: `trendsStaleHours` state, shows badge when >25h old.
- Deduplication: `Array.from(new Map(raw.map(a => [a.title, a])).values())`.
- `CountryBrief`: `onAttentionItemClick?: (query: string) => void` prop; `App.tsx` wires it.
- API field fix: `d?.trending ?? []` (was `d?.trends`).

**Google Trends stale data mitigation (#104)**
- `backend/app/services/ingest_trends.py`: shuffle country list each run (`import random`), batch size 5→3, delay 1s→2s, retry pass for failed countries.
- `frontend-v2/src/lib/publicAttention.ts`: `getTrendingSearchesUrl` uses `Math.max(hours, 72)` floor.
- AnomalyPanel shows "searches from Nh ago" badge when stale.

**Narrative Threads timeout cap (#139)**
- `backend/app/routers/narratives.py`: `detail_hours = min(hours, 48)` for Phase 2 (signals_v2 unnest scan); Phase 1 (theme_hourly_v2) still uses full `hours`.
- `effective_hours: detail_hours` added to result dict.
- `NarrativeThreads.tsx`: stores `effectiveHours` state; shows notice "Thread details show last Xh · counts reflect full Yh window" when capped.

**Trail / Pinned graph separation (#128)**
- `InteractiveWorkspace.tsx`: replaced single `graphRef`/`filteredGraph`/physics effect with separate `trailGraphRef` + `pinnedGraphRef`, `trailGraph` + `pinnedGraph` memos, two physics effects.
- Both ForceGraph2D instances always mounted; CSS `visibility: hidden` keeps simulation alive when inactive.
- Trail: linear-spread physics (charge -320/-420, distance 150); Pinned: dense-web physics (charge -380/-560/-760, distance 125-160).
- `InvestigationWorkspace.css`: `.workspace-graph-slot { position: absolute; inset: 0 }` + `.workspace-graph-slot.hidden { visibility: hidden; pointer-events: none }`.

**Backend deployment**
- Fly.io `atlas-api-pedro` deployed with `ingest_trends.py` + `narratives.py` changes (machine version 113, region iad, 1 passing health check as of 2026-05-17T13:57:17Z).

---

## Current Technical State (as of session 9 — 2026-05-11)

### Session 9 Additions

**Geo-validation (Wave 4 Phase 4)**
- `signals_v2.source_origin_country CHAR(2)` — outlet home country (≠ story subject country). Migration 012 applied, 12,944 US signals backfilled.
- `_extract_source_country(url)` in `ingest_v2.py` — 70+ known domains + ccTLD fallback.
- `foreignSourcePct` in country endpoint — null when <50 known-origin signals; shown as warning badge in `CountryBrief` when >60%.

**Source framing split (EntityPanel)**
- Replaces linear source list with Positive/Negative columns + narrative spread bar when sources span both extremes (threshold: `|avg_sentiment| > 0.2`, require ≥2 split sources).

**NER geo-filter**
- `_is_valid_person()` + `_GEO_NAME_BLOCKLIST` (40 entries) + `_GEO_FIRST_WORDS` in `main_v2.py` — filters GDELT-misclassified place names from People Mentioned.

**ESLint clean (#62)**
- `npm run lint` exits 0. `react-hooks/set-state-in-effect` and `purity` off; `no-explicit-any` downgraded to warning; before-declaration ordering fixed in `App.tsx`.

**Tolerant search (#51 closed)**
- `concept_suggestions` chip row added to `SearchBar.tsx`. All acceptance criteria met.

**Onboarding (session 9)**
- Removed redundant `welcome-card` and `map-hint` overlays from `App.tsx`. `OnboardingCoachmark` is the sole onboarding (localStorage, 3-step).

**Command bar stale-while-revalidate**
- `FocusDataContext` preserves nodes/meta during refetch when API returns empty. `App.tsx` command bar fades to 50% opacity during `isRefetching`.

**BRIEF Global Focus (session 9)**
- `Briefing.tsx` — theme→country pill rows showing signal counts per country per topic. Backend already had `theme_country_rows` query + Redis cache.

**Source blocklist expansion**
- 50+ domains added to `backend/app/config/source_blocklist.py`: consumer tech, sports leagues, entertainment, local US TV.

**Investigative concept vocabulary**
- 6 new `CONCEPT_MAP` entries: `blood-diamonds`, `electoral-fraud`, `narcotrafficking`, `forced-displacement`, `water-crisis`, `land-grabbing`.

## Current Technical State (as of session 8 — 2026-05-10)

### Critical Build Rule

Always run `npm run build` (not just `tsc --noEmit`) before pushing frontend changes. Vite uses `tsc -b` (project references), which is stricter. A passing `tsc --noEmit` does NOT guarantee a passing Vercel build.

### No Pending Fly.io Deploys

All backend changes are live. Fly.io app: `atlas-api-pedro`. Migrations 007–011 applied.

### Frontend Component Count

68 .tsx components in `frontend-v2/src/components/` as of 2026-05-10. Do not add Tailwind to any of them.
Session 7 additions: `OnboardingCoachmark`, `PublicAttentionPanel`, `TemporalNarrativeGraph`.

### NLP Pipeline (session 8, live on Fly.io)

- `backend/enrichment/nlp_pipeline.py` — three-phase pipeline: sentiment (RoBERTa), NER (spaCy), framing (NLI distilroberta).
- `ingest_loop.py` fires `asyncio.create_task(_nlp_background(limit=100))` after each GDELT cycle. Non-blocking. Skip if previous task still running.
- Dockerfile: `ENV HF_HOME=/app/hf_cache` and `ENV TRANSFORMERS_CACHE=/app/hf_cache` BEFORE pre-bake RUN. `ENV TRANSFORMERS_OFFLINE=1` AFTER pre-bake RUN. This is the OOM fix — do not reorder.
- NLP rate on Fly: ~200 signals/hour. Peak memory: ~720–738MB on 985MB machine.
- API: `COALESCE(nlp_sentiment, sentiment)` — RoBERTa replaces GDELT tone when available.

### Data Hygiene (session 8)

- Deleted 1,116,136 signals from Apr 27 – May 3 (no NLP, freed ~1GB).
- Retention policy: unprocessed signals deleted after 90 days, NLP-processed kept indefinitely.
- Automated cleanup in `ingest_loop.py` every 672nd cycle (~7 days).
- DB state: ~1.23M total signals, ~34K NLP-processed (2.8%), range May 3 – present.

### Data Coverage Badge (session 8)

- `App.tsx` fetches `oldest_signal` from `/api/v2/stats` on mount.
- Displays `FROM [DATE]` pill next to LIVE DATA in command bar.
- CSS class `.data-since-pill` in `App.css`.

### Branch Status

- `v3-intel-layer` IS production — Vercel and Fly.io both deploy from it.
- `main` is stale/abandoned. Do not merge into it.

### Investigation Workspace (session 6, still current)

- `InteractiveWorkspace.tsx` — react-force-graph-2d canvas. Lazy-loaded (chunk: ~187KB). Use react-force-graph-2d ONLY — the 3D version (react-force-graph) pulls AFRAME and crashes the app.
- `InvestigationWorkspace.tsx` + `InvestigationWorkspace.css` — shell. Wraps `InteractiveWorkspace` via `React.lazy()` + `Suspense` + `PanelErrorBoundary`. Rendered by App.tsx.
- `workspaceGraph.ts` — two-pass graph builder. Pinned nodes always succeed; edges per-item try/catch.

### Error Isolation Architecture (established session 6)

Three-layer error boundary hierarchy:
1. `RootErrorBoundary` in `main.tsx`
2. `PanelErrorBoundary` in `App.tsx` — wraps `InvestigationWorkspace` and other panels
3. `MapErrorBoundary` — wraps DeckGL map layer

### Theme Label Rule (session 6, still current)

All components rendering GDELT theme names must call `getThemeLabel(theme_code)` from `lib/themeLabels.tsx`. Do NOT use the API `label` field — it can return raw GDELT codes.

### Stream Panel Behavior (session 5, still current)

Default stream slot is `DiscoveryPanel` (blank state). State machine: `isPerson → isCompound → isCountry → isTheme → isChokepoint → DiscoveryPanel`.

### Sentiment Scale (unified session 7)

All endpoints return sentiment ÷10 (frontend expects ±1 range, ±0.1 thresholds). GDELT V2Tone raw is ~-20 to +20. Exception: ThemeDetail uses `getSentimentBarWidth()` which normalizes -10 to +10 internally. Do not change ThemeDetail.

### Coverage Confidence Badges (session 7)

Applied in CountryBrief, NarrativeThreads, ChokepointPanel: n<10 → `thin` (orange), 10≤n<50 → `limited` (yellow). CSS classes: `coverage-badge--thin`, `coverage-badge--limited` in respective CSS files.

### Concept Endpoint Fast Path (session 7)

`GET /api/v2/concept/{slug}?hours=N`: for `hours > 24` queries `theme_country_hourly_v2` (pre-agg, PK: hour+theme+country). For `hours ≤ 24` queries `signals_v2` directly. `effective_hours` always equals requested `hours`.

### Source Ingestion Stack (session 7)

- `ingest_rss.py` — Wave 1 general feeds + Wave 3 state media (RT/Sputnik/Global Times/IRNA) + non-English (France24 AR/BBC Arabic/El País/DW). `is_state_media=True` for state sources.
- `ingest_reliefweb.py` — Wave 2: 19 crisis country feeds via ReliefWeb OCHA. `geo_confidence=0.92`, `source_family='ngo'`. Direct URL pattern: `/updates/rss.xml?legacy-river=country/{iso3}` (not country path — that redirects and gets blocked).

### API Endpoints

- `GET /api/v2/search/unified?q=&hours=` — preferred search. Merges taxonomy, concepts, regions, DB. Cached 2 min.
- All v2 and v3 endpoints live. No pending deploys.

### FocusContext

- `GlobalFilter` includes `concept: ConceptFilter | null` and `region: RegionFilter | null`
- `setConcept()` expands to multiple GDELT themes; `setRegion()` expands to multiple countries

### Backend: gdelt_taxonomy.py

- `REGION_MAP` — 6 regions with ISO codes and multilingual aliases (EN/ES/FR/PT/DE/AR)
- `match_region()` — fuzzy region matching

### GitHub Issues Status

Open as of 2026-05-11 (6 issues): #46, #61, #70, #79, #80, #82, #83.
Closed session 7: #63, #73, #78, #81, #84–#93.
Closed session 8: #92 (Wave 4 NLP ADR).
Closed session 9: #51 (tolerant search), #62 (ESLint debt), #77 (source framing viz), #92 (NLP ADR), #99 (geo validation Wave 4 Phase 4), #100 (NER geo-filter).
Next priority: #83 (Signal Intelligence Panel), #61 (comparative engine UI), #70 (theme clustering), mac backfill completion.

**2026-06-24 — UNIFIED THREAD RANKING (Pedro's call):** Killed the
living/aggregate distinction — it was a source label dressed as quality
(dynamic_topics always first, atlas filling below by volume). Pedro: a
persistent atlas topic that keeps growing IS a live thread; don't demote by
origin. `app/services/thread_ranking.py` `rank_threads` (pure, 6 tests):
0.45·log-volume + 0.35·relative-movement(changed_10h) + 0.20·coherence
(avg_confidence), min-max normalised, NO source bias; volume log-damped so a
3K-signal category can't bury a 50-signal story, coherence is the guardrail
vs loose bins. `fetch_threads` merge replaced (dynamic+atlas one population,
deduped by label). Frontend NarrativeThreads LIVING/AGGREGATE badge removed
(trend arrow carries movement). DEPLOYED + SMOKED: prod /threads interleaves
DYN+ATLAS by score — Russia-Ukraine (ch10=147) leads on movement, growing
atlas categories (1000/945 sig, surging) rank top, emergent Sydney Airport
drops 1→7. Browser-verified badge gone. Weights are calibratable v1.
Follow-ups: atlas label quality awkward ("Disease outbreak in France and UG"
— #204 taxonomy); NER persons still throughput-starved (#184, nlp_persons
~empty → subjects show unverified=true via gazetteer).

**2026-06-24 — #234 slice 2 (person/thread focus → map re-scope + center):**
`a018267`. The /nodes fetch already scopes to focus (focus_type/value), so a
person/thread focus returns the countries where the entity concentrates
(prod-verified: person=trump → US 2585/IR 1043/IL 289, 70 countries). App.tsx
heat effect gained an `entityFocus` branch (light focus-scoped nodes by volume,
dim the rest; composite-fill guarded with !entityFocus) + a ref-guarded effect
that flies the camera to the dominant focus country. Build green, 64/64 vitest,
app stable under person focus. CAVEAT: the map-heat VISUAL is UNVERIFIED — the
`country-heat` layer does not render in the local dev preview (source fails to
load; global heat dark too, pre-existing), so the re-scope colors + camera fly
need an eyeball on the Vercel build. Country-focus slice 1 unchanged; thread
focus shares the same path (focus.type==='theme'). Pushed → Vercel redeploying.
Remaining #234: public-attention focus; the dock surfaces (anomaly/sources)
re-scoping; spurious flow partners are a co-occurrence data-quality issue.

**2026-06-24 — typed subjects ACROSS ALL surfaces (`982be23`):** EntityPanel
(person/theme focus) now consumes the server `key_subjects` from /api/v2/focus
directly (NER-typed, single source of truth; falls back to client-typing
key_people); ThemeDetail client-types its topPersons via buildKeySubjects (the
/theme endpoint doesn't serve key_subjects). Both render "Key Subjects" with
type badges, person-only clickable. Browser-verified (person→EntityPanel all
person-typed; thread→ThemeDetail badges). 64/64 vitest, build green. The
typed-subject reframe is now consistent across CountryBrief + EntityPanel +
ThemeDetail. Remaining #176: NER throughput (#184) to flip subjects from
unverified→verified; deeper GDELT name noise ("google mapsreeder mesa"). Old
`countryBriefPeople.ts` (selectVisibleKeyPersons) now unused — safe to delete.

**2026-06-24 — #234 focus propagation, cross-panel + papers cross-ref:**
(`66c2d23` fly fix, `029845b` thread re-scope). Pedro Vercel review: map heat
DID render (the dark map was a dev-preview-only source race), person focus
re-scoped heat but the CAMERA didn't center. Fixed: the fly fired on STALE
nodes (refetch in flight) → split into record-nodes-at-focus-change + fly-once-
nodes-change-reference; verified in a fresh dev session (person=trump → fly US
sc2497, camera centers N.America, US lit). Cross-panel slice 1: NarrativeThreads
now surfaces threads mentioning a focused person (top_entities match, guarded so
nothing-matches keeps the global list); browser-verified. **Cross-reference
DONE** (Pedro's ask to cross the work lines): the unified-ranking decision +
#234 recorded in the Paper 4 thread-model spec `2026-05-24-living-narrative-
threads.md` (2026-06-24 section) — it operationalises the 2026-06-23 decision #2
("volume-as-quality is wrong for serving; weighted distribution lives in Atlas
heat / Paper 3"). Papers map: thread ranking = Paper 4, focus/subjects/viz =
Paper 7, heat = Paper 3. REMAINING #234: dock (anomaly/sources) + public-
attention re-scope for non-country focus; backend `threads?person=` for precise
(non-top_entities-capped) person→thread relation. Evaluation note: the
person→thread match is honest but capped by top_entities (~6); the backend
filter is the precise upgrade (Paper 4 ablation territory).

**2026-06-24 — #234 shared focus-relation context (Paper 7 method):**
(`b4e8d4d`+`a0f52ff`). The DRY architecture Pedro approved: `lib/focusRelation.ts`
`computeFocusRelation` (pure, 5 vitest) → `{kind, value, dominantCountry,
relationCountries (volume-normalised), relationActive}`; `hooks/useFocusRelation`
wraps it over FocusContext+FocusDataContext. Honest by construction:
relationActive=false → panels stay global, never fabricate/blank. Panels
SELF-SUBSCRIBE (no prop-drilling): AnomalyPanel is the first consumer —
`scopeCountry = filter.country ?? relation.dominantCountry`, so a focused person
re-scopes its public-attention (wiki/trends) + ACLED conflicts to the person's
dominant country, label "PUBLIC ATTENTION · UNITED STATES", badge "TRUMP → US"
(browser-verified). **Papers framing (Pedro):** product ↔ paper are one line —
product = evidence/backing, paper = the lab that frames the RQ and tries methods.
This context IS the Paper 7 (analyst-workflow) method answering "how should every
surface re-scope to a focused entity's relations, honestly?". Remaining #234:
SourceIntegrity + the detail-PublicAttentionPanel add one useFocusRelation()
call each; map-heat + threads re-scope can migrate to the hook to collapse the
bespoke logic; precise person→thread = backend `threads?person=` (Paper 4).

**2026-06-24 — #234 "both done well" (precise person→thread + DRY):**
(B `4edc87c`…, A `4edc87c`). (B, Paper 4) PRECISE person→thread: `/api/v2/threads
?person=` filters to threads the person appears in via the FULL signal `persons`
array — `thread_matches_person` (pure, 6 tests): atlas threads match by topic
slug from a separate lightweight `_PERSON_TOPIC_SLUGS_SQL` (never touches the
THREADS_SQL spine), dynamic/emergent fall back to top_entities; router searches a
40-pool when person-filtering. Prod smoke: person=trump → 24/39 matched (caught
"Disease outbreak" that top_entities missed). (A) NarrativeThreads highlight now
consumes that precise set (replaces the capped heuristic): browser-verified 17/20
match vs 10 before. DRY: AnomalyPanel already self-subscribes to
`useFocusRelation`; SourceIntegrity NOT re-scoped (its data is the GLOBAL
briefing — no country param; needs a country-scoped source-health fetch, noted).
CRITICAL DECISION (logged): did NOT migrate the working map-heat/fly to the hook
— marginal DRY gain vs regression risk on a carefully stale-guarded, verified
surface; the hook is the go-forward source for NEW consumers, not a forced
refactor. Remaining #234: SourceIntegrity country-scoped fetch; detail
PublicAttentionPanel one-liner.

**2026-06-24 — #234 cross-panel ESSENTIALLY COMPLETE (correction, verified):**
Earlier note said SourceIntegrity needs a country-scoped fetch — WRONG. Verified
in-browser: SourceIntegrityPanel already re-scopes for ANY focus (incl. person)
via its `summary` path (useFocusData = /api/v2/focus, entity-scoped) — person
focus shows "SOURCE HEALTH: trump" + "Scoped to active person". Only the
unfiltered case falls to the global briefing. So for a focused person every main
surface now re-scopes: Map heat+camera (relation), NarrativeThreads (precise
?person= highlight), AnomalyPanel (wiki/trends/conflicts → dominant country via
useFocusRelation, country-scoped sources have no entity variant), SourceIntegrity
(entity-precise via summary). Lesson logged: VERIFY before assuming a panel needs
work. Genuinely remaining: detail PublicAttentionPanel is already item-scoped (no
#234 needed); map-heat/threads hook migration deliberately skipped (regression
risk); the map VISUAL still needs Pedro's Vercel eyeball.
