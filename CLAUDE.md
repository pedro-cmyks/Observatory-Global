# CLAUDE.md - Project Guidelines and Agent Configuration

> **PRODUCT WEDGE (the one user, the one job — master-consolidation T5.2).**
> Atlas serves the **narrative analyst** — journalist, OSINT/conflict researcher,
> newsroom desk, or policy/NGO analyst — whose job is **honest situational
> awareness on a specific event, topic, or country**: the real story, who is
> saying what across countries and languages, press vs. public, and what is
> missing — fast, and with the receipts. (Pedro 2026-06-26 chose "all four"; they
> share this core, so it stays one wedge — *narrative analyst*, not "everyone" —
> and narrows further if telemetry shows one persona dominates.) **Anti-goal:**
> no new surface/capability until telemetry shows users reaching a value moment.

**2026-07-04 (DÍA 2 — SEMANTIC LANE LIVE + identity fix + F4 param, `02a03ad5`,
read FIRST).** Day 2 of the 3-day route executed. (1) **SEMANTIC ASSIGNMENT
LANE SHIPPED + CRON-LIVE** (spec updated to SHIPPED w/ deviations): e5
anchor-cosine FAILED calibration honestly (pos/neg p50 delta 0.024, cross-fire
3169/3186 — same noise floor as the 06-29 ablations; text-rich anchors don't
fix it). Lane = **OpenAI text-embedding-3-small + ARGMAX rule +
WILD-calibrated taus** (gold-corpus taus admitted 29.6% of random corpus =
base-rate transfer failure; wild-junk-quantile taus ≤0.05%/topic → 2.43%
clearance, 24/30 lanes on — `docs/research/semantic-lane/`). Writes
method='embedding'/model_version='sem-assign-v0' (mig-019 CHECK has no
'semantic'); gate grades the lane via `score_assignments_gate.py --lane
semantic` (same OpenAI space; matched_terms=0 mild-OOD caveat logged). Cron:
runner Step 2b every 30min (~$0.001/cycle; ATLAS_SEM_LANE_ENABLED; config in
~/AtlasLocalWorker/config/; runner NOW VERSIONED at `infra/runners/` — it had
drifted out of repo). **Acceptance HIT first cycle: election-legitimacy lex
kept 0/18, semantic added 2 VERIFIED (Peru Sánchez-IACHR 0.997, Armenia
annulment court 0.994) + a literal India-SIR headline entered the candidate
universe.** Ledger = `sem_assign_report.py` (keep-rates: lex .32 / sem .18).
(2) **UNIVERSE-COLLAPSE ROOT CAUSE FIXED**: `hydrate_topics` SKIPPED topics
whose member clusters were wiped from emergent_clusters (`if not mem:
continue`) → identities re-founded instead of resurrecting. Now falls back to
persisted dynamic_topics centroid_vec (running centroid = anchor
approximation, documented); 22 tests pass. (3) **F4 read-path parametrized**:
`ATLAS_TOPIC_MEMBERS_ENGINE_VERSION` (default v1-compat) — cutover/rollback =
one env var. Also: scorer dry-run infinite-loop fix; mega2 corpus (13,663
rows) secured off /tmp (repo gz + /Volumes/Ext/Atlas/Gold/). REMAINING Day-2
residue → Day 3: unified-new-topic labeling+persistence (unified-new-N ids
are ephemeral per rebuild — needs dynamic_topics-row persistence before
DeepSeek labeling), F4 A/B re-run on gold before flip, watch sem-lane
keep-rates a few cycles (forced-displacement tau 0.163 = lowest, watch junk;
energy-grid/fuel-subsidy goldP ≤0.07 rely on gate). Day 3 also: browser-verify
surfaces + handoff playbooks.

**2026-07-05 (MADRUGADA — ROBOT v1 + ARCHIVO EN PROCESO, `ef87f73d`+`b86400a1`).**
Pedro: robot sobre TODA la historia, no el hot; "todos los datos históricos
procesados". (1) **archive_embed_pipeline.py CORRIENDO overnight** (nohup,
`archive-embed-full.log`): archivo completo → dedupe sha1 global + junk
filter → OpenAI 3-small → shards fp16 durables en /Volumes/Ext/Atlas/
Embeddings (resumible; ~$3 total; 130K vectores a las 00:15). (2) **robot_
categories_v1.py**: estructura-primero sobre las 1,406 identidades (TODOS
los estados, may31-jul5), corte MEDIDO por silhouette (0.35), naming único
por grupo, acepta unidades externas (--units-jsonl para el archivo).
HALLAZGO primera corrida: grupos = eventos/duplicados, no categorías → 2
guards medidos (intra≥0.80 = SAME-STORY, 17 grupos = work-list de dedup de
identidades; token dominante ≥60% = EVENT-LEVEL, 39 grupos = material
umbrella; Mundial cross-idioma agrupado, heatwave 'covered'). **0 inserts
espurios — las 30 seeds cubren el espacio categorial de esta ventana**;
categorías nuevas esperadas de las unidades era-mayo (Stage B: clustering
semanal del archivo → próxima sesión). Robot MANUAL hasta eyeball de Pedro
(reporte `robot-v1-2026-07-05.md`); v0 growth loop sigue armado de puente.

**2026-07-05 (MADRUGADA 2 — L3 DEEP REVIEW, spec de trabajo, sesión paralela).**
Pedro pidió revisión exhaustiva de L3 mientras el archivo se embebe en la otra
sesión. Entregable: `docs/specs/2026-07-05-l3-deep-review.md` (review + work
spec W0-W5 + 5 decisiones D1-D5, PENDIENTE del ojo de Pedro). Verificado en
código+prod, no en docs: (1) **L3 = split-brain**: Workbench
(`workbench.ts`, investigations+pins con snapshot #227+dossier, localStorage
`atlas.workbench.v1`) ‖ Workspace (`WorkspaceContext`, PinnedItem+force-graph,
`atlas-workspace`) — dos modelos de pin, el dossier solo lee uno, pins de
ThemeDetail/CountryBrief/Entity/Source nunca llegan al reporte. (2) **Backend
research congelado en el engine del 06-10/11** (grep-verificado 0 hits):
lane semántico en e5 + centroides running-mean (el mismo e5 que medimos en
noise-floor el 06-29/07-04), acoplado a pool-health sin piso (misma
enfermedad del F4 A/B), movement=changed_10h crudo (no Kalman), gate labels
pre-two-tier, cero lente R3; EXCEPCIÓN: thread lane hereda `fetch_threads`
(stories-only fluye gratis). (3) **Uso real ≈ CERO + telemetría ciega**:
`research_pin_events` = 1 pin en la historia (06-11, ship-day), 0 dossiers
jamás; no existen event types workbench/investigation; `research_pin_events`
write-only (#218 nunca consumido). (4) CORRECCIONES al registro: Phase 3
dossier SÍ está construido (`DossierView.tsx`, `2d4d04e3`) y #227 CLOSED —
docs 06-09 stale. Spec: W0 instrumentar (primero, barato) → W1 unificar los
dos sistemas (un store, snapshot en todo pin) → W2 re-sustrato del plan
(taus e5 re-medidos método wild-junk + guard pool≥80; two-tier labels;
Kalman; lente categorías; OpenAI gated en hot-vectors) → W3 dossier v2 =
wedge (who-says-what vía topic_members roles + voice_mix + tiers #217
mínimo + gaps por categoría) → W4 captura (universe/threads/signal pinnable,
puente story-panel→investigation, archive-backed pin open) → W5 Phase 4
sigue paper-gated. Anti-goal respetado: cero superficies nuevas.
**EJECUTADO misma sesión (Pedro aceptó + decidió D1-D5):** W0 `ff6e2b33`
(eventos workbench/investigation/pin + value moment `investigation` +
`research_usage_report.py` — primer READ de #218; funnel real: 24 opened/0
workbench/0 pins). W1 `e0f58aeb` (WorkspaceContext = adaptador sobre
workbench.ts, TODO pin de panel lleva snapshot #227; force-graph RETIRADO
D1 — InteractiveWorkspace/workspaceGraph/ReadingMode borrados; llave
`atlas-workspace` drop D5 — aclarado: pins fueron SIEMPRE localStorage del
usuario, tu server solo guarda eventos anónimos; browser-verified pin→
badge→dossier→reopen). W2 `80b64681` DEPLOYED Fly (contract
research-plan-v1: guard sustrato pool<80 DISPARANDO en prod "15 active...
suppressed"; two-tier verified/extended en evidencia; Kalman en anchors
"surging" source=kalman-topic-movement; lente categorías + category_summary;
`recalibrate_research_taus.py` → **junk p50 0.865 vs tau 0.80 / 0.887 vs
0.84 — taus 06-10 bajo la mediana de junk**, NO subidos a ciegas (pool
colapsado + sesgo pseudo-query), artefacto
`docs/research/l3-research-lane/2026-07-05-tau-recalibration.md`; walkthrough
smoke 2/2 PASS post-deploy). W3 `e4d21759` (dossier v2: who-says-what vía
roles typed — verificado browser "media-led, press 36 · public 1"; voice
self-voice/dominant-outsider/state-media; grupos por categoría; frozen vs
measured-at-generation nunca mezclados; markdown completo). W4 `f830107a`
(primer PIN sin investigation LA CREA del query — la rampa search→story ya
no muere en la captura; filas de NarrativeThreads pineables ◆). 163 vitest +
46 pytest research + builds verdes. PENDIENTE gated: OpenAI-space cutover
(hot vectors), archive-backed pin open, W5 papers, re-medir taus @pool≥80.

**2026-07-04/05 (NOCHE — CATEGORÍAS≠HILOS servido + growth loop + retención
REAL + reclaim 4.1GB, `d40deedf`+`1b6ba3b0`, read FIRST).** Pedro corrigió la
falacia de niveles y destapó la retención. (1) **STORIES-ONLY /threads
DEPLOYED** (Fly): atlas topic = CATEGORÍA (lente R3), NO fila — supersede el
unified-ranking del 06-24; lista global sirve solo historias (dynamic;
emergent fallback; sustrato flaco = lista corta honesta, nunca relleno de
categorías). Prod verificado: 10 filas todas dynamic-topic-*. Vista
país/slug conserva el merge R1 (contrato CountryBrief — follow-up).
Kill-switch ATLAS_THREADS_CATEGORY_ROWS=on. El deploy también subió el F4
read-path param a prod. (2) **CATEGORY GROWTH LOOP armado** (Pedro: "el
corpus no es fijo en piedra"): `grow_atlas_categories.py` — categorías
libres del typer R3.1 recurrentes (≥3 stories/30d) → bar de solape MEDIDO
(p90 sims inter-anchor = 0.426, espacio OpenAI) → draft DeepSeek → INSERT
origin='auto' (mig 068), sin lexicón (nace como lente typing/semántico).
Cap 2/noche, ledger, seeds intocables; Step 5 del scoped-snapshot
(ATLAS_CATEGORY_GROWTH=off). Validado dry-run; dispara cuando el pool
re-engorde. **DISEÑO ACORDADO robot v1 (Pedro)**: estructura-primero —
agglomerative sobre centroides de historias en espacio OpenAI (e5 comprimido
0.94+ a esa granularidad), umbral MEDIDO, un naming por grupo, recursivo
(temas→dominios), lifecycle de retiro; v0 nombre-primero queda de puente.
PRÓXIMA SESIÓN. (3) **RETENCIÓN — culpable real encontrado**: NO el retention
7d documentado; `local_hot_cold_catchup --older-than-hours` DEFAULT 24 sin
override en el runner → hot vivía a 1-2 días (Kalman 7d + persistencia
famélicos). Runner ahora pasa 168h (ATLAS_HOT_RETENTION_HOURS); prune sigue
solo tras archivo verificado. TAMBIÉN: el job fallaba exit 1 en su VACUUM
final (statement_timeout del pooler, mismo bug-class matview) → session
timeout bump. (4) **RECLAIM SUPABASE: 7.16→3.09 GB (−4.1 GB)** — era BLOAT,
no tablas viejas: signals_v2 3,105→356 MB (¡15KB/fila de churn!),
signal_embeddings 1,236→205 MB (152K tuplas muertas vs 54K vivas),
theme_country_hourly 1,406→1,078 MB. Con 7d hot el DB estabiliza ~5-6 GB.
(5) Respuestas asentadas: pool de centroides = dinámico por lifecycle (16
active/737 candidate/619 retired hoy, post-collapse), SIN relación con las
30 categorías; corpus atlas 30 en DB (candidate-v2=32, 2 hazards nunca
insertadas — el typer ya las emite libres, el growth loop las propondrá
solo). NEXT: robot v1 estructura-primero · country-view stories-only ·
A/B F4 re-run @pool≥80 (PB-5) · archivo→identidades (time-as-dimension).

**2026-07-04 (DÍA 2 cont.+DÍA 3 — F4 §6-step-5 + A/B VERDICT + playbooks,
`a5b61131`+`54368a3a`).** (4) **New-topic labeling+persistence SHIPPED**
(`build_unified_topics.py`): residual clusters → real dynamic_topics
candidates (identity_key `u2-*`, DeepSeek label, centroid); `_load_centroids`
includes them → pass-1 matches next run (ephemeral unified-new-N loop
CLOSED). Live catch: number-spelling SPAM cluster ("Digit: 5,250,037 / In
words:…") persisted then deleted → `_looks_junk_cluster` guard added; spam-
source cleanup = open chip (task_9e296e6b). (5) **F4 A/B re-run: NOT YET —
judged an ARTIFACT** (`docs/research/engine-ab/2026-07-04-f4-ab-rerun.md`):
post-collapse pool = 16 active centroids → 15k signals → 18 blob-topics at
assign_t 0.82 (promiscuous end of the measured cliff); the 06-29 PASS ran on
a 100+-topic pool. **REAL FINDING: v2 quality is COUPLED to dynamic_topics
pool health with no floor — v1's lexicon lanes degrade gracefully, v2
doesn't.** Flip criterion now carries a substrate-health precondition (≥80
active centroids) + structural candidate: v2 should anchor on the full R3
spine (atlas + scoped topics), not only dynamic centroids. A/B re-run in 2-3
days = mechanical (PB-5). (6) **DÍA 3 delivered**: `docs/state/
handoff-playbooks.md` (PB-1 cron health · PB-2 sem-lane monitor/recal/
disable · PB-3 gate retrain w/ HARD deploy rule · PB-4 two-tier check ·
PB-5 F4 A/B precondition · PB-6 substrate recovery · PB-7 deploy/reversal
card · PB-8 telemetry read) + `emit_extended_thresholds.py` (the ad-hoc
threshold emission is now a script). Surfaces verified vs retrained engine
at contract level: /threads 10 dyn+atlas ✓; **election-legitimacy fixture
serving 2 VERIFIED India-SIR-class headlines ("Karandlaje seeks ECI probe
into SIR", "INDIA Bloc EVM") + 3 extended (Armenia court, Panamá)** ✓;
universe Kalman trends differentiated (4 surging/7 cooling) ✓ — 16 nodes =
substrate thinness (tracked), not regression. Sem-lane after several cron
cycles: keep-rate stable 0.16 vs lex 0.29, grading every cycle. Runner
canonical copy = `scripts/run-atlas-topic-classifier.sh` (infra/runners dup
dropped; earlier "not versioned" note was cwd error). NOTE:
`thread_intelligence.py` F4 param needs the next Fly deploy to reach prod
(default unchanged, no urgency).

**2026-07-04 (NIGHT — GOLD BLITZ + GATE v3 DEPLOYED + reframes).**
Pedro's question ("¿la información pasada no sirve?") unlocked Day 1 of the
3-day route (`docs/state/2026-07-04-three-day-route.md`): hot DB holds 7 days
but the EXTERNAL ARCHIVE holds May-3+ (10.5M rows scanned). Shipped tonight:
(1) **archive_gold_miner.py** — offline lexicon match over 754 gzip
partitions; election pool 39→21k candidates. Wave-1: 4,160 labeled (2-vendor,
**86% agreement** with the newly-wired candidate-v2 boundaries; the measured
answer to Pedro's 70%-junk intuition: **70/30 incorrect/correct = lexicon
candidate precision ~30%**, a P1 number). Mega corpus **9,274 rows**, hard
topics 95-286 positives. (2) **FROZEN-HOLDOUT eval (85/15)** — the honest
apples-to-apples the cross-benchmark comparisons couldn't give: **v1-prod
precision 0.890 = BELOW its 90% claim on realistic data** (telecom P=0.46; its
0.843 recall was easy-benchmark artifact); **v3-bootstrap holds 0.924**
(sanctions P.95/R.46 = 2× v1 recall at higher precision). (3) **GATE v3-MEGA
DEPLOYED** (cron flipped, 48h re-scored, extended thresholds re-emitted @75%
bootstrap, Fly deployed; election stays hard — extThr~0.98, below-gate
fallback carries it; wave-2 (+4,800 thin-topic labels) cooking + semantic lane
= the recall fixes). `--bootstrap-thresholds` in train_scope_gate = the
variance cure (75th-pct threshold across 300 resamples + recall CI reported).
(4) **REFRAME (Pedro): crisis-as-dynamics**
(`docs/specs/2026-07-04-crisis-as-dynamics-reframe.md`) — crisis is a
POST-classification; `crisis_dynamics` = f(velocity,surprise,changed_10h)
adopted; F4 re-framed as "kill the pre-classification lane"; P1's 41.6%
lineage = historical baseline, documented not defended. First piece SHIPPED:
**universe SURGING chip** (isSurging over the Kalman field, browser-verified
55→27 filter; CRISIS chip tooltip renamed to honest harm-lens). (5) **Time-
as-dimension spec** (`2026-07-04-time-as-dimension.md`, Pedro): data never
windowed by UI tabs; scrubbers per surface (globe joins universe+orbital);
AGE/persistence first-class ("active since June 12"); click-a-past-peak →
that day's evidence (archive-backed). (6) **Self-training flywheel**
(`2026-07-04-self-training-flywheel.md`): L1 nightly accumulator (armed) + L2
weekly archive miner + L3 frozen eval slices + L4 disagreement queue; archive
= training reservoir, labels compound. (7) **Universe collapse INCIDENT**
(6 alive on Pedro's phone): lifecycle transient post-substrate-recovery
(07:30 clustering re-founded identities; promotion gate persist≥2 admitted 6)
— bootstrap-restored 33 retired + 10 candidates → 47 nodes/108 edges prod;
OPEN root-cause: resurrection didn't centroid-match (engine session, folds
into F4). ALSO: #204 boundaries wired into annotators; #239 fully closed
(warm-cache + MapLibre deprecation −1MB + keep-alive shell + hidden-pane poll
damp); telemetry read (value moments 3→42/wk, dev-noise caveat). NEXT (Day
2): wave-2 merge → final retrain → semantic lane → F4 prep → crisis_dynamics
in more surfaces; Day 3: verify + small-model handoff playbooks.

**2026-07-04 (PM — SHIP DAY: search→story · #239 closed end-to-end · MapLibre
DEPRECATED · gold accumulator, read FIRST for product state).** Eight ships,
all browser-verified + prod: (1) **Search → STORY panel** (`c84e6627`): Enter/
"◆ Open the story" on a natural query renders the research-plan anchors as the
cross-thread narrative IN the stream slot (ResearchPlanPanel reused; Build-a-
thread demoted to power tool; Start-investigation stays = the Workbench ramp —
L3 now has a natural entry instead of being the unreachable layer). Race fixed
(searchSeqRef: late search response can't reopen the dropdown). (2) **#239
CLOSED end-to-end**, Pedro's load-time complaint: slice 1 warm-cache fetch shim
(`ab964f0d`, lib/fetchWarmCache.ts — first request per URL after a route change
serves cached + background-revalidates; polls untouched; Brief re-entry 3ms) +
**MapLibre DEPRECATED** (`1c99ded1`, Pedro's call: legacy mercator behind a
settings toggle cost 1MB on EVERY /app load without mounting + carried the
display:none crash class; EE has full parity — ~450 lines out of App.tsx, deps
uninstalled, maplibre chunk GONE from dist) + slice 2 **keep-alive shell**
(`775fe945`, main.tsx AppBriefKeepAlive OUTSIDE Routes: App+Brief mount once,
switches = display toggles, DOM sentinel survives round-trip; deep-links kept
correct — App/Brief now URL-REACTIVE with pathname guards so the hidden pane's
params never cross). Net: first load −1MB, Brief↔App instant with state intact.
(3) **mig 067 hint pruning** (`de0bab98`, applied): junk GDELT theme-hints
pruned per measured keep-rate (<2% @ n≥40) — election-legitimacy rawTotal
2,002→112 (rail now says 18, was the lying 1.4k); PR3-05 REMOVE-OK finally
IMPLEMENTED, surgically (kept signal-bearing hints: ARMEDCONFLICT 15%,
CORRUPTION 77% — naive lex-required would kill 569 verified non-English rows).
(4) **#248 forum hobby damp** (`74488ffe`, deployed): fediverse community name
= the topic signal (crochet@lemmy.ca self-identifies); damp-not-gate, 3 tests.
(5) **Orbital perspective zoom** (`5e2943b3`): radii counter-scaled k^-0.55 →
moons visibly detach (Pedro's "las lunas no se alejan"); verified k=4.83 →
separations 4.83× vs bodies 2.03×. (6) **GOLD-GROWTH round 1 = honest negative**
(`0b327128`): 226 decision-band candidates → 2-vendor labels (80% agree, +70
positives) → retrain → **NOT deployed: per-topic thresholds at 40-60 positives
are HIGH-VARIANCE** (election recall@90 swung .39→.55→.24 across corpus
variants; deploying = statistical self-deception). Pipeline repeatable at
pennies; **com.atlas.goldgrowth cron ARMED** (`e7fd6d92`, 03:30 nightly,
~$0.15/night, samples+labels until 200 pos/topic ≈ 2 weeks) → then ONE retrain
with variance-aware calibration (bootstrap CI-lower). (7) Kalman **backtest**
(`afbddb42`): velocity does NOT lead volume (mean-reverts, h1 −0.477) →
changed_10h stays the ordering source, topic_movement = display-only. DECIDED.
(8) Ops: `atlas-cron-freshness-watchdog` (30-min launchd, kickstarts stale
crons by DB freshness, never two heavy jobs) + substrate #2 closed (crons
re-bootstrapped, embeddings fresh 176K). Alignment doc:
`docs/state/2026-07-04-alignment.md` (+EOD reconciliation §). Eval doc (the
bacano≠eje pass): `docs/research/eval/2026-07-04-atlas-vs-websearch-eval.md` —
**Atlas = EJE for discovery** (tone map pointed at India's election-legitimacy
crisis, web-confirmed, unreachable from a Peru-first search). NEXT: candidate-
v2 wiring (#204), semantic assignment lane, retrain-at-200-pos, hidden-pane
poll pause (mobile), telemetry weekly read.

**2026-07-04 (GATE RECALL ARC — eval→diagnosis→OpenAI cutover→two-tier, read
FIRST for engine).** Full evidence chain in one session: (1) **Atlas-vs-web EVAL
(the "bacano≠eje" pass, `docs/research/eval/2026-07-04-atlas-vs-websearch-eval.md`):
Atlas = EJE for discovery** — its tone map pointed at India (−1.5, 143 sig) on
election-legitimacy and the web CONFIRMED a real crisis (Banerjee/SIR purge/vote-
chor) unreachable from a "Peru election" search; web wins verified depth. Blocker
exposed: gate kept 1/1,269 → all UNVERIFIED. (2) **Diagnosis
(`docs/research/gate-recall/2026-07-04-gate-recall-diagnosis.md`): NOT a bug —
the per-topic ≥90%-precision policy forces thr≈0.99 on hard topics** (74 signals
≥0.5 dropped; the 0.35-0.5 band is real coverage: FBI Georgia, WA mail-in, Peru
JNE). (3) **Bake-off:** no local embedder matches OpenAI (m-e5-large 0.742,
bge-m3 0.745, e5base 0.749 vs OpenAI 0.843 @90%); Pedro funded $30 →
**scope gate CUT OVER to OpenAI** (`score_assignments_gate.py` OpenAI branch,
text format 'headline | label' NO query-prefix; cron gate-id
atlas-scope-gate-v1-openai; reversible ATLAS_GATE_JSON/ATLAS_GATE_ID; 48h
backfilled ~$0.006). Live: agriculture 0→44%, armed-conflict 17%, overall 25%.
(4) **TWO-TIER coverage SHIPPED (Fly `f2c28eca`):** `_atlas_topic_detail` serves
VERIFIED (gate_kept 90%) + EXTENDED (score ≥ per-topic 75%-precision threshold,
`backend/app/data/scope_gate_extended_thresholds.json` — models/ is NOT in the
Docker image, app/data is) + per-signal `tier` + warning `extended_coverage`;
ThemeDetail banner "N verified · +M extended (~75%)". Prod verified:
election-legitimacy total 1→14 (6 verified + 8 extended, extThr 0.954); overall
coverage 25→38%. **HONEST RESIDUE: election-legitimacy stays modest — its real
lever is the LEXICAL ASSIGNMENT (~2,000 loose signals inflate the denominator),
not the gate.** Also this session: Kalman BACKTEST (velocity does NOT lead
volume — mean-reverts, h1 −0.477; changed_10h stays the ordering source,
topic_movement = display-only; `backtest_movement_leading.py` +
`docs/research/movement-backtest/`); substrate #2 closed (crons re-bootstrapped,
embed fresh 176K, `atlas-cron-freshness-watchdog` 30-min launchd — checks DB
freshness, kickstarts stale crons, never two heavy jobs); alignment doc
`docs/state/2026-07-04-alignment.md`; label bug (map key shows dynamic-topic-821
raw id — Legend getThemeLabel only maps GDELT codes) spawned as task. NEXT:
lexical-assignment precision (election-legit denominator), universe orbital
moon-zoom bug (zoom didn't propagate to orbital canvas), #248 noise lanes.

**2026-07-02 (PM — UNIVERSE VIEW MVP SHIPPED, /goal run).** Pedro's vector-
field framing ("todo el universo en un campo vectorial; un tema = una sección")
built literal: **`GET /api/v2/universe`** (universe-v0, `app/routers/universe.py`)
— 348 active story topics (umbrellas excluded), positions = numpy-SVD PCA
blended 55% to category anchors (48 constellations, data-driven attractors),
**edges = top-3 cosine neighbors in FULL 768-dim space** (thresholds rejected:
NN sims p50 0.943 → 0.92 gives 1,534 edges; measured), 30d daily activity
timeline per node, 158KB, 10-min cache. **Honesty split = the design:** PCA
top-2 explains ~17% (measured) → legend says "positions approximate ·
relations exact", meta carries both bases. Frontend: command-bar **UNIVERSE**
button → full-screen overlay (`UniverseView.tsx` + pure `universeLayout.ts`,
5 vitest; zoom/pan, hover→neighbor-subgraph highlight, click→closes+opens
that thread's ORBITAL system — universe→system one visual language). §I time:
scrubber births/decays stories (72h half-life, floor). Browser-verified:
348 bodies/836 edges/24 constellations; scrub Jun 11→27 alive; hover card;
click→STORY SYSTEM. 150/150 vitest + 3 pytest, deployed Fly+pushed. Docs:
spec `2026-07-02-universe-view.md` (+§6 trajectory/"gravity" metrics
assessment — capture rate/drift/convergence, backtestable, #219 Kalman =
seed); P7+P8 grown in master plan. **V2 same day (Pedro: panel + motion,
`7a257ff9`):** UNIVERSE = toggle EN el GLOBE toolbar (mounts OVER the map —
display:none crash lesson; overlay retired, command-bar button = shortcut);
cloud ROTATES — backend serves PCA top-3 (z = honest depth) + nn_sim; drag
= yaw, ambient spin pauses on hover/drag, depth cues near-big/far-dim.
**Orphans** (nn_sim < p10 0.893, dashed): live finding — the 35 orphans are
EXACTLY the isolated lifestyle class (hotel reviews/travel guides); field
detects semantic oddity unsupervised (P8/#248 evidence). Spec §7 = working
section (7.2 moving cloud; trajectories v3 = per-snapshot centroids in
emergent_clusters). **V3 same day (Pedro round 2, `db186ad4`):** UNIVERSE =
dock-style GLOBE|UNIVERSE TABS in the map panel (layer chips + MAP KEY
globe-only; universe has OWN classifiers CRISIS/ORPHANS); thread-open
TRAVELS to its orbit INSIDE the panel (zoom+fade → orbital, ← UNIVERSE
back) — STORY SYSTEM removed from ThemeDetail (one home; legacy graph
render retired). Axis fix ×2: center-of-mass rotation + THE REAL BUG:
mount-only ResizeObserver behind the loading branch → svg 1200px in a
590px panel (why it "rotaba por fuera"); callback-ref fixes universe +
orbital. Umbrellas: excluded from field, story system opens via travel
(children = field bodies). 153/153 vitest. **V4 (Pedro: "llegar desde la
nube", `c769c4c4`):** universe = DISCOVERY entry + FULL focus lens. Root
cause: theme-focus era GDELT-only (`ANY(themes)`) → thread ids matcheaban 0
→ paneles silenciosamente globales (la razón del viejo "thread-open clears
focus by design"). `focus_filters.thread_focus_filter` (dynamic-topic-N /
atlas slug → typed topic_members membership) compartido por /nodes + /focus.
Verified: click en la nube → orbital viaja + ThemeDetail + GLOBE "Filtered:
<thread>" + AnomalyPanel "THREAD → RU" + cuerpo activo ANILLADO en el campo.
**V5 (Pedro: "se clipea + muy redondo", `4c40e62a`):** orbital POLISH —
canvas height-aware (fijo 380px era el clipping), órbitas ELÍPTICAS
(stretch uniforme del campo radial → llena el panel, el ORDEN radial =
distancia semántica se preserva exacto), gradientes por tipo, glow del
centro + core compacto con label DEBAJO, starfield determinístico, colas
de cometa afiladas, línea de conexión en hover con la distancia medida,
labels de banda (closest/edge), texto con halo. Verified 587×859 svg =
panel completo. **V6 (Pedro review 2, `415ed1fd`):** (1) cola RE-CODIFICADA
= drift semántico MEDIDO (late-half vs early-half mean dist; afuera =
alejándose del tema, adentro = convergiendo; floor 4% del span medido);
cometa = anillo punteado; hover muestra el drift. Prod dt-981: netanyahu
+0.0038 receding, rubio −0.0077 converging. (2) **DATA BUG (Pedro's
election-legitimacy screenshot): gate kept 1/1,066 en 24h** → detail
mostraba UNA señal filipina como historia de 1.1k; below-gate fallback
extendido a near-zero keeps (gated<5, raw≥20) → 200 rows/15 países bajo
UNVERIFIED. ⚠ El keep-rate 0.1% del gate en un topic político = problema
de ENGINE (gate recall), pendiente de programa — no de superficie.
PENDIENTES de la review: universe trajectories (posiciones moviéndose con
el scrub — emergent_clusters per-snapshot centroids), pseudo-3D tilt
orbital, discussion-attach noise (Mbappé/LinkedIn en dt-981, semantic
0.90 attach quality → #248 class). NEXT igual + esos.
**2026-07-04 (SUBSTRATE #2 DIAGNOSED + crons revived, ops — read FIRST).**
Root cause of the thin/frozen data (only 101 stories, universe/movement/heating
all noise-thin): NOT fundamentally thin data — the M1 CRONS STOPPED FIRING ~20h
ago (log mtimes: embed 07-03 06:59, clustering 03:24; machine was AWAKE, sleep
prevented — scheduling broke, likely my earlier manual bulk-reindex+restore
cycle left launchd in a bad state). Chain: embed cron stalled → 11h stale
embeddings → the 07-03 clustering ran on INCOMPLETE embeds → formed 186 clusters
(vs 07-02s 1049) → only 101 active stories → everything downstream thin.
Ingest itself is HEALTHY (157K/24h fresh). FIXED: re-bootstrapped scoped-snapshot
+ embed-hot-corpus + emergent-snapshot (scheduling reset; kickstart proved
clustering runs); kicked a mindful embed catchup (clears the backlog). SAFETY:
two heavy ML jobs at once spiked load to 16.3 on the 8-core M1 (the kernel-panic
zone — WindowServer at 35%) → killed the premature clustering kickstart, kept
the foundational embed. DURABLE PLAN (not yet built): (1) CHAIN embed→cluster
(sequence, not independent schedules) so clustering never runs on stale embeds —
the real structural fix; (2) a scoped-snapshot watchdog (like embed-watchdog) to
catch stalls; (3) harden restore-after-bulk-reindex (it likely broke the
schedules). Substrate thickens over the next hours as embed catches up + the
re-bootstrapped clustering fires. This is the honest blocker under universe/
movement/heating — mechanics are correct, data was starved by dead crons.

**2026-07-03 (PM — PERSPECTIVE ZOOM + open-thread highlight, `24757126`).**
(1) Zoom is now PERSPECTIVE (Pedro "como en el espacio": zoom in → your planet
grows, the rest recedes), not uniform scale. Perspective divide on the real
PCA z (exaggerated 2.4× — z is low-variance), strengthens with zoom, k=1 stays
orthographic; focused-body radius unclamped to 3.5×. Verified radii spread
5.4→9.7, focused 31→65px. Weighed perspective-camera (chosen, uses real z) vs
fisheye (warps positions, rejected). (2) Back-to-UNIVERSE frames + highlights
the open thread (green glow + "◆ open story" label, camera k=1.5) → see WHERE
it sits. (3) Click regression fixed (hit-test on tap), ROLL button dropped,
orbital zoom stronger. Consistency Q answered: same brain — movement unified
to topic_movement (whole population); highlight/camera/perspective are pure
frontend VIEW, zero new compute (projection is a view of shared engine facts,
not a parallel truth). NEXT unchanged: backtest, threads-read-topic_movement
(gated), substrate #2.

**2026-07-03 (PM — INTERACTION FIXES + movement covers whole population, `1387e288`).**
(1) Pedro live review: CLICK on a universe body DID NOTHING (free-nav regression —
setPointerCapture ate the <g> onClick) → non-drag tap hit-tests the body (mouse+
touch) → opens its thread. ROLL mode DROPPED (redundant w/ free trackball orbit;
roll still on alt-drag/twist). Orbital thread view now ZOOMS+PANS (wheel/drag/reset)
to get closer to moons/planets. (2) Movement unification step: `compute_topic_movement`
now runs the Kalman over ALL topic_ids in topic_members (unified membership) → 290
dyn + 59 atlas = 349; the shared field spans the WHOLE thread population. NOT flipped:
threads-panel ranking still uses inline changed_10h — reading topic_movement there
changes front-page ORDERING → gated on A/B + Pedro ok. (3) Answered the threads-serving
Q: unified score 0.45·vol(log)+0.35·movement+0.20·coherence, no hierarchy; "generic
names" = atlas CATEGORIES winning on volume (R3 tension + #204 label quality).
NEXT: backtest (does Kalman velocity/surprise LEAD volume? — likely underpowered on
the thin corpus, honest finding either way); threads read topic_movement (gated);
substrate #2.

**2026-07-03 (PM — KALMAN #219 MOVEMENT FIELD POPULATED, `3befea33`, read FIRST).**
Pedro's call executed: Kalman = the movement DESTINATION (smoothed velocity/
surprise over the SAME signals_v2 volume lineage, NOT a competitor to
changed_10h). `topic_movement` existed but was EMPTY; now it's the ONE shared
movement field. mig 066 (Kalman cols) + `compute_topic_movement.py` (runs the
read-only pilot's tiny Kalman over each topic's 3h-bucketed signals_v2 volume/
7d → smoothed_intensity/velocity/uncertainty/surprise/trend, upsert
movement-kalman-v1). Wired into the M1 embed runner AFTER the topic_members ETL
(fresh members→movement); synced to AtlasLocalWorker. Universe reads
topic_movement.velocity (tanh) + trend, relative changed_10h fallback.
Populated 101 topics (feed LIVE for the first time). Verified: universe
velocity now differentiated + carries Kalman trend ("surging"), 8-halo rank.
ARCH: movement defined ONCE → Kalman smooths → every surface reads it (same
principle as topic_members unification, applied to MOVEMENT). PENDING: threads
panel should ALSO read topic_movement (still computes its own changed_10h —
same lineage so consistent, but not yet the shared field); the backtest (does
surprise/velocity LEAD volume?) validates the predictive claim. 161 vitest.

**2026-07-03 (PM — VELOCITY CONSISTENCY FIX, `c136e842`, read FIRST).**
Pedro's recurring split-brain smell = CORRECT. The universe velocity had grown
its OWN source (emergent_clusters snapshot n_signals) — a confounded proxy +
a THIRD movement brain vs the Narrative Threads "▲ Accelerating". FOUNDED
decision (provenance + resolution + consistency): `changed_10h` (direct
signals_v2 delta, the ONE number thread_ranking + the panel already use) beats
the snapshot proxy. Rewired universe velocity → relative changed_10h; snapshot
fn deleted. Rank-based "Fastest rising" top-8 (thin corpus saturates the
absolute — substrate #2, not a metric bug). Emoji→vector spark. **Kalman is
the DESTINATION** (Pedro right): `topic_movement` #219 schema EXISTS but EMPTY
= the smoothed/zscore form of the SAME lineage → populate it next, every
surface reads that one field (raw changed_10h fallback). Backtest validates
the zscore leading-indicator claim, not the raw delta. Principle = the
topic_members unification applied to MOVEMENT: define it ONCE, read everywhere.
161 vitest.

**2026-07-03 (PM — ATTENTION VELOCITY / heating bodies, `6f019213`, read FIRST).**
Trayectorias v2 = capa de gravedad PREDICTIVA. Dos propuestas (propose/counter):
velocity-glyph por cuerpo (A) vs detector de convergencia/merge (B) — elegí A.
`_attention_velocity` = aceleración normalizada (tercio reciente vs tercio
previo de la serie diaria de tamaño desde emergent_clusters snapshots). Halo
cálido ESTÁTICO (sin animación — disciplina térmica) escalado por velocity +
readout "🔥 N heating · top". FRAMING HONESTO: aceleración MEDIDA, no
predicción — el claim de indicador-adelantado es un backtest read-only (P3/P8,
pendiente, el sustrato está recuperándose). **Bonus fix del sustrato:** el
timeline del scrubber había colapsado a 1 bucket/topic (ETL re-estampó
assigned_at); reconstruido timeline + velocity desde la serie durable de
snapshots (median 3/max 18 días de nuevo). Verificado browser: readout+halo
vivos; scrub Jun 10 → 7 de 101. Prod: US-Iran enfriándose -1.15, Canada Bosnia
calentándose +0.54. 161 vitest.

**2026-07-03 (PM — INVERSE-FOCUS GRAVITY WELL, `e108da9f`, read FIRST).**
Focus país/persona en Atlas → ilumina SUS historias en el campo (la otra
mitad de #234). Dos propuestas pesadas (propose/counter): dim pasivo (A) vs
entity-as-gravity-well (B) — elegí B como OVERLAY honesto: sol fantasma en el
baricentro + líneas de gravedad + readout de FOOTPRINT (N historias / M
categorías, concentrado vs transversal) SIN distorsionar las posiciones
semánticas. Backend: top countries+persons por nodo en el payload (cacheado).
Frontend: litNodeIds+entitySpread (puro, vitest); cámara enmarca. Verificado
en browser: country=US → 46 historias / 28 categorías / CROSS-CUTTING + 46
líneas + sol. 160 vitest. Señal investigativa: transversal (figura dominante)
vs concentrado (actor de una sola historia).

**2026-07-03 (PM — FREE 3D ROLL, `c2f85fee`, read FIRST).** Pedro: "roll
disponible 3D, para donde sea". Weighed TWO approaches per his instruction
(judge + counter-propose + weigh, web-grounded arcball/gimbal-lock): Euler
yaw/pitch/roll (clamped, gimbal-limited) vs accumulated 3×3 TRACKBALL MATRIX
— chose the matrix (no gimbal lock, no clamp, any orientation; positions are
approximate PCA anyway so exploration ergonomics win). `Rot3` +
applyRot/mul3/rotX/Y/Z (pure vitest). Modes ORBIT|MOVE|ROLL + reset; roll also
alt-drag / two-finger twist. Ambient spin composes into the matrix, firmly
paused during any drag (draggingRef fix: hover-leave no longer resumes spin
mid-drag). **Physically verified in the BROWSER (Pedro's rule): ~172° roll
flipped the field rigidly (constellation labels bottom→top); orbit/pan/reset
live; console clean.** 158 vitest. Research subagent + web grounded the choice.
Spec §7.4.

**2026-07-03 (AM — FREE NAV + Paper-1 framing, read FIRST).** Pedro's product
thesis LOGGED: **Atlas = Paper 1** (narrative threads + how we classify/relate
information); every other paper (P2-P8) is BACKING for P1. The universe is
becoming the SPATIAL INDEX of Atlas — discovery entry + focus lens + R3 spine +
time, one surface. **Universe FREE NAVIGATION shipped (`7113222a`):**
two-axis free orbit (yaw+pitch via `rotateProject`, pitch clamped ±1.2) + ORBIT|
MOVE mode toggle + pan (drag the whole cloud) + two-finger pan/pinch on mobile +
reset. **Fixed the text-selection bug** (drag turned the panel blue / selected
labels instead of moving): user-select:none + touch-action:none + preventDefault.
Browser-verified (rotate non-uniform dx-spread 244, pan uniform +100px, selection
empty). Spec §7.3. Reindex recovery: HNSW rebuilt, 144K embeddings (FK-violation
stopped it early on retention-deleted rows; catchup relaunched). Orbital + moons
verified live on atlas threads (amy-coney-barrett = moon of trump, measured
co-occurrence). NEXT (Pedro's "qué falta para ser eje"): (1) substrate
reliability = the real blocker — reindex/ETL/gate all had bad nights on the M1;
(2) inverse focus country/person→field; (3) task-time evaluation (bacano≠eje);
(4) trajectories v2 = capture-rate as leading heat indicator (#219 Kalman seed).

**2026-07-03 (madrugada — PANIC POST-MORTEM + RECOVERY + V9, read FIRST).**
(1) **El apagón de Pedro = KERNEL PANIC 00:06:45**: "userspace watchdog
timeout: no successful checkins from WindowServer in 134 seconds".
Contribuyentes: universe auto-spin re-renderizando 348 nodos SVG a 60fps
(MITIGADO `91073ca4`: yaw ~10fps, para con orbital abierto, auto-rest 90s
idle, re-arma con interacción) + **mysqld homebrew crash-loop (99 crash
reports, NO es Atlas — Pedro: `brew services stop mysql` si no lo usas)**.
(2) **EL PANIC MATÓ EL BULK-REINDEX A MITAD**: signal_embeddings quedó en
18K de ~476K, SIN índice HNSW; el relanzamiento post-reboot murió con
ModuleNotFoundError (cwd equivocado). RELANZADO 2026-07-03 ~01:20 (nohup
taskpolicy -b, cwd backend, mlvenv, `embed-bulk-reindex-recovery.log`,
113,591 pendientes ≈2.5h; HNSW al final; restore-watcher re-bootstrapea
fleet+embed-cron al salir). Hasta entonces: semantic lane lexical-only,
orbital sin distancias. (3) **PA-thread attach NOISE (Pasta Grannies al
85% en Irak-anticorrupción): floor adaptativo por-centroide** (`91073ca4`,
mean+2.5σ vs fondo social random; medido: el piso e5 VARÍA 0.875-0.900
por thread → umbral fijo 0.82 siempre servía basura). Prod: dt-800
noise_floor 0.875 → 0 items = vacío honesto; hallazgo: HOY casi ningún
thread tiene discusión de foro genuina (misma conclusión que silent-risk).
(4) **V9 MOONS (`3e8d8d6c`, spec 7b)**: entidad chica con ≥75% de señales
compartidas orbita a su cuerpo padre (co-ocurrencia medida; países nunca
son lunas); hover muestra % compartido. + Member resolution endurecida:
ventana envejecida → últimos 400; topic_members mid-rebuild (el ETL dejó
dynamic en 677 filas/108 topics esta noche — ⚠ pipeline pendiente) →
sample_signal_ids. Moons SIN verificación visual hasta el backfill.
PENDIENTES: verificar reindex al terminar (count ~476K + HNSW) + moons
eyeball; translate-por-texto para PA dock (queries trends, M); focus
inverso país/persona→campo; ETL dynamic projection (por qué 677 filas).

**V8 (sigamos, `95d3a120`): UNIVERSE TRAJECTORIES** — el scrub MUEVE las
posiciones por sus rutas REALES: centroides por-snapshot (emergent_clusters,
87 snapshots/30d) proyectados a la base PCA actual → node.track (348/348
topics); interpolación + ease al centroide actual; hover dibuja la ruta
(polyline). Verified: scrub Jun 13 → cuerpos en SUS posiciones de ese día.
Caveat honesto: topics jóvenes = track de 1 punto; el frame es la base de HOY.
**V7 (Pedro round 3, `547662db`):** (1) rim = TONE en cuerpos orbitales
(fill=tipo, borde=tono medio; escala raw ±10, banda neutra ±1.0 — unifica
el split tone/avg-sentiment de nombres); (2) **R3 SPINE DRILL-DOWN** —
Pedro: "todos son atlas topics dinámicos; los grandes deben dejar ver los
pequeños" = la unificación R3. Slice de superficie shipped: atlas topic =
categoría → sus historias R3.1-tipadas servidas como `memberStories` +
sección STORIES INSIDE THIS TOPIC clickeable (election-legitimacy → 9:
Cepeda CO/Fujimori PE/Atiku NG; verified click→abre). Cutover engine
R3.2/F4 sigue gold-gated — esto es la cara de usuario. (3) Moons+gravity
fields (concepto Pedro) SPEC ONLY en orbital spec §7b — co-ocurrencia →
lunas, body↔body distancia semántica → atracción; sesión propia.

**2026-07-02 (L11 SOLAR SYSTEM — Orbital Thread View SHIPPED + E2 root-caused).**
Design+prototype session (parallel chat; did NOT touch BriefNewspaper/search.py/
thread_ranking). (1) **E2 DIAGNOSED + FIXED (`b3fcfa79`, deployed):** the >24h
processed-history branch ran BEFORE the dynamic-topic resolver and "dynamic-
topic-981" contains "-" → EVERY dynamic thread opened EMPTY (total=0) at hours
>24; plus the old graph silently hides when `graphSignals: []` (`??` gate) and
at 24h renders a 1-signal bucket that reads broken. Guard added; prod-verified
(dt-981@72h: 0→78). (2) **Orbital Thread View** (spec `docs/specs/2026-07-02-
orbital-thread-view.md`): STORY SYSTEM section in ThemeDetail, DEFAULT over the
legacy graph (toggle ◉Orbits/⌗Graph keeps it). Radius = REAL semantic distance
(member embeddings ↔ centroid, `<=>`; atlas = computed avg centroid, labeled);
angle sweeps with cumulative interactions via TIME SCRUBBER (no idle animation);
presence decays exp (§I decay-not-cliff, floor 0.22); comets = span <25% of
window; entrants counter = the acceptance task ("who entered this week?").
Backend `GET /api/v2/theme/{id}/orbital` (orbital-thread-v0, honest empty
reasons; member query windowed on assigned_at — atlas 26s→3.9s), 4 pytest;
pure layout `lib/orbitalLayout.ts`, 6 vitest. Browser-verified BOTH paths
(dt-981 30 bodies + atlas 35; scrub 10%→bodies 10→6; hover "PERSON · COMET";
toggle→legacy canvas). 145/145 vitest, build green, deployed Fly. Paper 7
method note grown in master plan (falsifiable-against-engine + motion-as-
interaction + task-not-aesthetics acceptance). Phase 2 = L3 universe-builder,
SPEC ONLY (§7). NEXT: Pedro eyeball + task-time pass; mobile shape (#236).

**2026-07-01 (PM3 — SEARCH ENGINE P1 + EE DESIGN PASS + review execution).**
Pedro: search = the hard core; EE map = OUR design, prioritize; execute the
review plan; ACLED de-blocked (#46). ALL SHIPPED+DEPLOYED: (1) **Search P1**
(`docs/specs/2026-07-01-search-engine-plan.md`): unified search NEVER queried
dynamic_topics — live threads invisible. `live_threads` segment (token-AND ILIKE
+ partial fallback + country scope + label-dedupe) + "Live Threads" FIRST in
SearchBar → `onThemeSelect('dynamic-topic-<id>')`. Prod: 'Lebanon Israel
agreement' → 3 threads → click opens detail; 'burkina faso' → thread+signals
(P2 finding: match_country lacks small-country aliases). #245 CLOSED. P2=country
-scoped, P3=semantic-on-submit, P4=search telemetry. (2) **Equal Earth design
pass** (`c72baae0`, review doc §5): default/reset now FIT-WORLD (fitHeight
over-zoomed narrow panels onto Africa, scaleExtent min=1 couldn't zoom out;
kFit + letterbox-center + wrap on zoom-in); heat rank^1.6 normalize (the 422
fix fed 250 countries into the old [0.1,1] min-max → rainbow world; heals BOTH
engines); Geist canvas labels. Verified: world-fit + click→CountryBrief+#234
re-scope. HONEST: engine = geoCylindricalEqualArea(30) NOT geoEqualEarth
(rectangular wrap trade; equal-AREA holds; rename label?). Route to default:
Pedro eyeball (desktop+MOBILE) → flip default → fly-to-bounds + marker clicks →
retire MapLibre. (3) **#244 CLOSED** (`dc5d9812`): landing cards deep-link
?theme=&entry=landing + tour DEFERS on intent-carrying entry (browser-verified).
(4) **#246 CLOSED** (+`949d8192`): damp consumes served category (crisis_
relevant=False + lifestyle-family token → 0.45; football/world-cup added);
prod: hotel review AND 'Canadá Clasifica' out of top-10, real news leads.
Next per plan: search P2 (Burkina case full) → design #247 batch A → P3.
**PM4 (goal run):** EE = DEFAULT (Pedro sign-off, `44b7580e`); search P2 shipped
(+129 country aliases — 'burkina faso' now resolves; pure-country query → its
PRIMARY-country threads inline, prod-verified); **#247 batches A/B/D/E SHIPPED**
(`159b6309`→`827ef3b9`): muted→0.55 AA floor + 139 grays tokenized; Brief got
FRAUNCES + Docs re-skinned to Atlas identity (cyan→emerald x60, Fraunces
wordmark); ghost fonts killed (--font-serif now defined); truncation data-tips;
DESIGN.md prose de-contradicted + tailwind surface-* de-leaked (Landing 0.55
opacity KEPT — Pedro approved Landing as-is). REMAINING #247: C1/C2/C3 (panel-
header/badge/EntityPanel-palette consolidations — M-effort, specs in the audit).
Search remaining: P2-focus-chip, P3 semantic-on-submit, P4 telemetry.

**2026-07-02 (OVERNIGHT STATE + MORNING CHECKLIST — read FIRST).** Night close
2026-07-01 ~23:40. Shipped late: EE map = DEFAULT + Pedro's 2 live regressions
fixed same hour (`51793494`: portrait fills height w/ strip world, landscape
world-fits; fly-to-country now works in EE for every entry — verified on
phone, PWA needed the double-refresh SW cycle); L0 CLOSED (landing stats live
from /voice-mix, `5e5f8046`); forum lane source:'forum' (was claiming reddit
for Lemmy); #247 = 5/6 batches DONE (A contrast 139+43 fixes · B Fraunces/Docs
identity · C3 EntityPanel violet · D truncation tips · E canon de-contradicted
— only C1/C2 headers+badges remain, need per-panel eyeball); search P1+P2 LIVE
(live-threads segment + 129 country aliases + pure-country→primary threads;
'burkina faso' resolves). New: **#249** (Brief BY THEME still GDELT → swap to
R3.1 categories; + dup counts 5,774 smell + Antilles/RM country leaks).
**OVERNIGHT COMPUTE (self-managing):** #241 lever-1 bulk-reindex RUNNING
(196K embeds, ~13/s CPU-bound — note: NOT the 228/s theory; MPS contention w/
NER measured, fleet PAUSED for it) → HNSW rebuild at end; ETA ~04:00-05:00.
`restore-after-bulk-reindex.sh` (nohup, ALW) auto-bootstraps nlp-fleet +
fleet-watchdog + embed-cron when the process exits, EVEN IF this session died.
Semantic lane on lexical fallback until rebuild. Scoped-snapshot fires 02:30.
**MORNING CHECKLIST:** (1) reindex done? `psql: SELECT count(*) FROM
signal_embeddings` (~476K) + `SELECT indexname FROM pg_indexes WHERE tablename=
'signal_embeddings'` (idx_signal_embeddings_vec MUST exist) + research/plan
smoke (semantic anchors back); (2) restorer log `~/AtlasLocalWorker/logs/
restore-after-reindex.log` + `launchctl list | grep atlas` (fleet/watchdog/
embed-cron up); (3) scoped-snapshot first fire (launchctl exit 0 + fresh
dynamic_topics snapshot_at ~02:30-03:30, incl. Step 4b disaster binding);
(4) multilingual drain: verified subjects growing (IT had carabinieri/Roma);
(5) NER burst resumes + consider burst=2 (RAM was 42% free w/ 1 worker).
**QUEUE:** #247 C1/C2 → #249 → search P3 (semantic-on-submit) + P4 (telemetry)
→ #248 noise classes → L3 depth track (T1.1 dossier who-says-what). #243 has
the full ops list.

**2026-07-01 (PM2 — L0→L3 DEEP REVIEW, read FIRST for product state; full doc
`docs/specs/2026-07-01-l0-l3-deep-review.md`).** Pedro: fly re-auth (done,
browser flow) + judge the FOUNDATION (data congruence L0→L3, design vs
DESIGN.md, persona walkthroughs) — "que no estemos construyendo sobre algo
malo." **VERDICT: foundation SOUND** — every traced number = real Atlas data,
honesty labels hold, L3 workbench ledger reconciles EXACTLY; problems = seams +
silent breaks + design debt, not rot. **4 defects found live + FIXED + DEPLOYED
same session:** (1) map heat fill 422 on EVERY request (frontend limit=250 vs
endpoint le=200 — the recurring "dark map"; `c9eaffac`); (2) **`country_hourly_
v2` matview DEAD since 08:00 UTC** (refresh outgrew statement_timeout, 2m35s
measured; brief stats//stats/geo/anomaly served 24h missing 13h, handler was a
bare print → session timeout 600s + RESET + logger.error + manual backfill,
raw==agg verified; `abd61cd0`); (3) `changed_10h` dynamic = LIFETIME MAX
velocity (69/101 topics inflated movement → trend arrows + 0.35 rank term; now
latest-snapshot, SUM for umbrellas; same commit); (4) relationship endpoint
pinned discussion/mood to v1-compat (~0 there) → asserted "press-only" falsely
(dt-84 had 10+10 in unified-v2; now engine-agnostic deduped — the v1‖v2 UNION
debt paid at this consumer; verified live 10/10). Also fixed: mobile Brief 71px
overflow (`f8b880a1`). **Persona findings → issues:** #244 landing story-click
drops intent (no deep-link + tour stacks); #245 search never surfaces LIVE
threads (workbench DOES find them — 49 anchors, DIRECT 0.83); #246 lifestyle
damp ignores served category (hotel review #3-4 global; mechanism: thread_
ranking.py keys label keywords only); #247 design program (audit computed **142
WCAG-fail text declarations** — the "letras que se pierden" exact list; Docs
hero = CYAN+other bg vs landing emerald; **Brief uses Georgia, never got
Fraunces — inverted**; EntityPanel alien palette 0 vars; ≥8 label styles/~25
badge families; token PLUMBING correct, adoption is the gap; batches A/B/C
shippable); #248 byline-persons + entertainment-about-crisis noise classes.
#180 REOPENED (reliefweb 2 ngo rows/7d — wired ≠ producing; morning close was
wrong). Pipeline health: NER 2%/24h (5.2d lag — #243 urgency), embeddings 8.7%
of fresh, trends FRESH 0.78h, gate 24.1% kept, 373 active topics 100% typed.
Backend suite 976 passed (3 test files excluded: pre-existing broken
`anthropic` pkg import in .venv). Landing diversity stats hardcoded (~true,
will drift). Full sound-list + remaining minors in the review doc §2a.

**2026-07-01 (PM — CONNECTION REVIEW + HYGIENE PASS, read alongside the
parallel-tracks block).** Pedro asked for a full coherence review (specs ↔ papers ↔
vision ↔ issues) then "work everything actionable." Review verdict: convergence
real (R3 = genuine umbrella; PR3 ledger mechanism works); remaining risks =
MAINTENANCE not design. All actionable items EXECUTED same session:
(1) **Telemetry READ for the first time (T5.1 debt):** 181 app_opens / 14 sessions
since 06-26 but only 3 value moments (none since 06-28) — AND `/brief` (the PWA
consumer front door) fired ZERO events (`app_open` only fires on `/app`). Fixed:
`brief_open` on mount + `brief_thread_open`+`first_value_moment{kind:brief_thread}`
in `openThread` (BriefNewspaper.tsx; distinct event to avoid double-count with the
console's deep-link `thread_open`). Verified end-to-end (preview → 202 → prod rows).
**Read telemetry weekly — the wedge anti-goal is ungoverned without the reading.**
(2) **R3.1 typing cadence contradiction FIXED:** spec §3.1 mandates 30-min typing;
build had it nightly-only. `run-atlas-topic-classifier.sh` Step 4 now runs
`compute_category_typing --deepseek --write --only-untyped` every 30 min (new flag;
incremental crisis_class IS NULL; steady-state 0 API calls; lazy torch import).
Tested live ("no topics to type"), synced byte-identical to ALW.
(3) **nlp-fleet watchdog** (`scripts/nlp-fleet-watchdog.sh` + launchd 15-min,
INSTALLED + verified "up"): the fleet died silently 06-29→07-01 (2nd silent-death
incident after #240) — checks loaded/PID/heartbeat-freshness (45m), kickstarts.
Failure branches untested by design (didn't kill the live fleet).
(4) **PR3-02 CLOSED (agent-authored):** P1 skeleton gained §"Benchmark universe
re-scope (PR3.2)" — Part A crisis-anchor precision (48–54% band, κ, CIs, anchoring
mandatory) + Part B open-set delegated to P8 + the 41.6%→48–54% bridge (question
change, not one measurement). Ledger: 10 resolved / 1 partial (PR3-10 residue);
doc track CLOSED. (5) **R3 spec addenda:** §4.1 gate SATISFIED (PR3-05 REMOVE-OK),
§12 ablation-exists correction, §3.1 cadence-implemented note. (6) **Issues:**
**#243** = follow-ups checklist (multilingual re-check, #241 lever 1 Pedro-gated,
burst=2, uk/bg, role_noise_rate, temporal-holdout window, scoped-snapshot first
fire, theme-hint removal); #184 re-scoped (M1 fleet superseded the ask); #157
updated (82.1%/87.5% measured). (7) vitest 136/136 (fixed the stale #204 label
expectation in exportFormatters.test.ts — was the standing 1-fail). Multilingual
drain measured LIVE: ~2.1K xlm signals/hr, 660 non-EN nlp_persons at check.
Residual named debt (not urgent, tracked): two membership regimes (v1-compat ‖
unified-v2) until F4; consumers must UNION (the relationship-endpoint bug class).

**2026-07-01 (PM cont. — ISSUE-HYGIENE SWEEP, 42→26 open).** Pedro: audit every
open issue (stale vs current), close or advance, in parallel. 3 Explore agents
verified issues vs CODE (not docs); every close carries file:line/commit evidence.
**CLOSED 17:** #240 (watchdogs + false-healthy fix), #228 (§6 items 1-4 verified,
micro-polish noted), #178 (pub-vs-render timestamps exist), #176 (hygiene stack
end-to-end + today's photo-credit guard), #212 (Equal Earth SHIPPED w/ toggle),
#148 (**IMPLEMENTED this session** — Show-all-publishers toggle, `a77a822`,
browser-verified 5→10→5), #145 (serving-layer filters), #134 (Docs use-cases),
#180 (reliefweb path live), #164 (ADR-0004 exists+implemented), #158 (CJK batches),
#153 (superseded→#237), #222 (superseded by R1 — the 15K cap is gone), #219
(E-R3-f: Kalman never a serving provider), #196 (stale — vessels 200 live), #184
(fleet superseded the ask), #157 (benchmark ran: 82.1%/87.5%). **Commented 7:**
#154 (audits ~75%, serving-integration remains, pair w/ #217), #185 (agent misread
CORRECTED — mining unbuilt + deprioritized by PR3-05), #221 (confidence half only),
#140 (screenshots remain), #46 (blocked on Pedro's ACLED registration), #239
(program not started), #243 (new blockers below). **ALSO SHIPPED:** photo-agency
person filter `2264ecf` (`_PHOTO_CREDIT_TOKENS` in utils.py — "jonathan borba
unsplash" /country/IT leak; 72 tests) — **⚠ NOT DEPLOYED: fly token EXPIRED**
('missing third-party discharge'), backend deploy blocked on `fly auth login`
(Pedro, interactive). The expiry also had embed-watchdog reporting FALSE "up"
(fly error → empty list → healthy); fixed `171459b` (logs FLY ERROR now); embed
service itself verified ALIVE (semantic smoke). Remaining open = genuinely-valid
work: #233/#173 (not built), #220/#217/#221 (contracts), #161/#159 (GDELT research),
#156 (quota), #226/#151 (markets), #235/#237/#238/#239 (programs), #166/#106/#46
(blocked/design), #140, #236 (mobile polish), #241/#243 (ops), #204 (living).

**2026-07-01 (PARALLEL-TRACKS SESSION — read FIRST; full handoff
`docs/state/2026-07-01-parallel-tracks-session.md`).** Two explicit parallel tracks
(Pedro: "que no se me pierda el uno o el otro"), ALL shipped + VALIDATED (69 tests,
prod 4/4 200, git clean). **⚠ MULTILINGUAL NLP IS NOW LIVE ON M1** — the biggest state
change: `ATLAS_NLP_MULTILINGUAL=on` in `/Users/pedro/AtlasLocalWorker/.env`. The
2026-06-25 "not worth it" was WRONG (blockers = a missing `protobuf` + only trying the
free spaCy). Now: Davlan xlm-roberta NER (82% precision, non-Latin) + wikineural for ru
(87.5%) + XLM sentiment; `nlp_pipeline.py` routes non-en→Davlan, ru→wikineural, en→spaCy.
**Discovery: the M1 NLP fleet had been DOWN since 06-29** (bootstrapped it — NER was
starved). **Memory guard: burst=1** (supervisor floor `max(2)→max(1)`; 8GB M1, heavier
multilingual workers). Production non-English `nlp_persons` now writing (`NER[xlm-v1]`).
**Surface payoff ACCUMULATES over days** (mindful drain ~169s/cycle) — re-check
`/country/IT` etc. show verified non-English subjects tomorrow. **REVERSIBLE:**
`ATLAS_NLP_MULTILINGUAL=off` + restart `com.atlas.nlp-fleet`. Quality fix from live
monitoring (`980ff1c`, deployed): `subjects.classify_subject` now checks the gazetteer
BEFORE NER (was NER-wins → England/LaLiga→PERSON leaked; gazetteer overrides mistypes).
**Event sources:** disaster ingest LIVE (USGS+GDACS, mig 062 `disaster_events_v2`, 250
events, `ingest_disasters.py` 8th cycle) + geo-temporal binding (`bind_disaster_movement.py`,
runner Step 4b, zero fan-out) — the hazards CAMEO can't represent; relationship endpoint
movement-count bug fixed. F3 event UNION (`compute_event_movement` reads sample ∪ unified-v2,
+57% coverage). **#241 embed:** Lever 2 (recency) shipped in `embed_hot_corpus`; Lever 1
(`--bulk-reindex` drop/rebuild) READY but OFF — Pedro reviews before enabling (drops prod
index ~4min). **Papers: PR3 experiment backlog DONE + WRITTEN** (ledger
`docs/research/atlas-paper/2026-07-01-paper-staleness-ledger.md`): PR3-05 theme-hint
ablation (theme-hints are NET NOISE, 20.2%≪40.9%, removal→48.3%, REMOVE-OK), PR3-09
external baseline (HDBSCAN-global cliffs 0/8, Atlas edge = scoping+lifecycle not raw
coherence), PR3-10 CIs+κ0.734+crisis-only **48–54% = the successor to 41.6%** (anchoring-
controlled), PR3-11 heat ablation (Kendall-τ vs volume −0.198, volume≠importance measured);
folded into P1 skeleton + P3 master-plan. 16 commits `992b445`→`004a101`.

**2026-07-01 — R1 SCOPED CLUSTERING SHIPPED + SERVED (#229, read FIRST for engine).**
The recall lever landed. R1 (`backend/scripts/run_scoped_snapshot.py`) clusters
per-country over the persisted corpus (dissolves the global HDBSCAN purity/recall
cliff): wrote **731 tight topics, 126 countries, cohesion 0.968, no blob, 26
honest-empty**. Serving bootstrap-promoted **68→392 active** (purity held: admitted
topics cohesion 0.969 / noise 0.081, real stories). Prod `/threads` VERIFIED serving
scoped regionals a global pass drowned (Iraq Anti-Corruption, France Heatwave,
Italian "Attentato a Ranucci", Sydney). Key finding: the promotion gate
(`LifecycleConfig`) was calibrated for the OLD global regime (`persist_min=2` +
`volume_min=30`); scoped topics are 8-30 signals → recalibrated to `volume_min=12`
(MEASURED histogram v30=50/v15=205/v10=389, not guessed; 311 revert ids saved).
**Recurring cron** `com.atlas.scoped-snapshot` (02:30, mindful, NEVER `--rebuild`)
REPLACES the global `emergent-snapshot` — armed, first autonomous fire tonight.
**Retention/resurrection = the design (Pedro's ask, already built):** never deletes;
retire = serving-hidden state; a retired topic resurrects on centroid match (same
`identity_key`, history intact). **R2 SHIPPED + SERVED (LIVE on Fly, 2026-07-01)**
(`docs/specs/2026-07-01-atlas-engine-r2-umbrella-hierarchy.md`): umbrella hierarchy
(centroid-of-centroids) — `build_umbrella_topics.py` COMPLETE-linkage @0.98 (single-link
CHAINS; 0.95 leaks — both measured) → **26 umbrellas over 55 children**; migration 058
(`parent_id`/`is_umbrella`). Serving: global `/threads` = top-level (umbrellas +
singletons, dups collapsed — VERIFIED "dup labels NONE", 6 umbrellas in top-40);
recent_n = SUM at latest snapshot (so umbrellas rank); dynamic-fetch timeout 8→15s.
**Country-view FIXED**: `?country_code=CC` now merges R1 scoped children (primary-country,
e.g. "Venezuela Earthquake Casualties" for VE) with atlas — was atlas-generic only.
R2.4 = umbrella build wired into the nightly cron (Step 3). **Deployed to Fly (x4),
pushed** (`66b69e4`→`9293667`). Papers: P8 Interventions 3/4 + retention; P7
evolution-graph-as-engine-truth; P4 R-pointer. Umbrellas are EPHEMERAL (rebuilt each
pass, ids change) — drill by id works within a fetch; stable-umbrella-id is a follow-up.
Perf follow-up: the top-level query is ~7s cold (array subqueries; Redis-cached).

**2026-07-01 (PM) — R2 umbrella SHIPPED + R3 unification spec CLOSED+VALIDATED + R3
build started.** R2 (event level) LIVE on Fly (`build_umbrella_topics.py`, complete-
linkage @0.98, 26 umbrellas; global dedup + country-view serving R1-specifics). **R3 =
the unification** (`docs/specs/2026-07-01-atlas-engine-r3-unification.md`, **CLOSED +
VALIDATED** after a 4-agent deep read of ~20 specs + 9 papers): kills the atlas‖dynamic
split → ONE story population, a SPINE category→event→story + orthogonal LENSES
(entity/geo/source, already built) + a deferred typed-RELATION layer. Pedro's challenge
fixed the taxonomy: **ANCHORED-EMERGENT categories** — the crisis-32 (#204) are SEED
ANCHORS + an editorial lens, NOT a fixed target; the set GROWS (resolves the 40-52%
precision ceiling + open-set consistency). EVENT = TWO axes (geographic umbrella ‖
narrative subthread; decision 3 NOT delivered by the umbrella). **Build STARTED:**
R3.0 schema (mig 059: member-ref cols + `attention` role + `topic_movement` +
category cols); R3.7 retirement (392→348, swept the R1-bootstrap over-promotion,
retention model live); **R3.1 typing** (`compute_category_typing.py` — DeepSeek-
validated: cosine FAILS, DeepSeek typed **348/348 = 182 crisis + 166 non_crisis**
honest-reject). Remaining = engineering w/ resolved decisions (§9): R3.4a movement,
R3.3 umbrella-fold+stable-id, R3.2/F4 cutover (serving-seam carry-forward + gold gate),
roles R3.4b/5/6/8, narrative-subthread axis, PR3 paper track (`docs/research/atlas-
paper/2026-07-01-paper-staleness-ledger.md` — 4 un-reconciled precision numbers,
`gdelt_hint_ablation.py` unbuilt, missing external baseline). **R3 BUILD (implementa-todo
pass):** shipped R3.0/R3.0b (mig 059/060 schema+PK-swap), R3.1 (DeepSeek typing 348/348 +
emergent categories + open non-crisis domains), R3.3 (umbrella stable-id + category
inherit), R3.6-partial (category badge LIVE), R3.7 (retirement 392→348). **Crisis-relevance
as a LENS (Pedro): the crisis/non_crisis binary → `category` (open, every story) + `crisis_
relevant` (flag/filter), mig 061.** Findings: topic centroids diffuse (cosine unreliable →
DeepSeek is the typer); R3.4b event-movement DATA-LIMITED (CAMEO country-level, #232);
cutover R3.2 = low-priority (user-facing unification already delivered via badge; pure
atlas-collapse risks coverage). Typing wired into the nightly cron **+ (2026-07-01)
the 30-min classifier cron Step 4 (`--only-untyped` incremental — spec §3.1/F-C4.2
cadence, fresh stories badge within a cycle)**. Commits 67f4484→2e22cd5.

Last updated: 2026-06-30. **TRACK CONSOLIDATION — COMPLETE (read this FIRST):**
the two parallel chats (engine/taxonomy ‖ frontend/L2) have MERGED into ONE living
track — the engine handoff was absorbed 2026-06-30, so this is now the SINGLE
track owning BOTH engine and frontend (no more "reserved" split). State now owned:
prod serves construction **v1**; **v2 reject gate LIVE** (reversible); pending
off-peak = gold-growth pass + F4 unified-v2 cutover + the attention/anomaly engine
extension. (Un-versioned-runner risk RESOLVED 2026-07-01 — runner versioned +
byte-identical with the executed AtlasLocalWorker copy, now incl. Step 4 typing.)
Original merge rationale —
the L2 audit showed the split-brain is one problem, two ends (the engine's missing
attention+anomaly roles ARE the L2 surfaces). Plan + rationale:
`docs/state/2026-06-30-track-consolidation.md`. The engine chat's **FINAL HANDOFF**
(F3/F4 status, #204 gold base 2,134/κ0.775 + **v2 reject gate SHIPPED** cutting ~43%
force-fit reversibly, `topic_members` schema, M1 crons, mid-flight/un-versioned
runner) = `docs/state/2026-06-30-engine-chat-final-handoff.md` — whoever owns the
engine reads that one. Reversibility: `UPDATE signal_topic_assignments SET
gate_kept=true WHERE gate_model='v2-gate-e5-lr-1'`.

Prior handoff (L2 execution): **read for the frontend track:**
**L2 deep-review execution (`docs/specs/2026-06-26-l2-deep-review.md`)** — the
"analyze before attacking" review (split-brain: alert layer ↔ evidence layer
never reconcile) is being implemented Tier A→B→C, all deployed Fly+Vercel:
- **A1/A2** focus chip + deselect + single-source-of-truth country select; chip
  redesigned COMPACT (was a loud blue gradient → small dark pill, mobile floats
  above the tab bar).
- **B3** thread KEY SUBJECTS use `rank_key_people` (kills single-signal "ocean
  atlantic"-class noise). **B1** dropped the positional "critical" spike (a
  country volume spike no longer falsely marks the first thread critical).
- **B2 (#214) one count semantics**: country thread list now carries
  `gated_signal_count`/`gate_scored_count` (CTE adds the gate-kept count the
  detail already serves); CountryBrief shows the GATED number (raw on hover) and
  splits scored-but-zero-kept threads into an **UNVERIFIED `<details>` tray** —
  prod-verified CO: "Armed conflict" 39raw→12 shown, "Election legitimacy" 36/0
  → tray. List and detail now agree.
- **C1** forum lane surfaced: `GET /api/v2/public-attention[?country=]` (Reddit
  `source_family='social'`, labeled `verified=false`, never evidence) +
  `source_family` added to `/api/v2/signals`. **C2** AnomalyPanel Public
  Attention now = Trends[S]+Wiki[W]+**Forum[F]**, scoped via useFocusRelation
  (fixed a response race: global fetch overwriting the country-scoped one).
  **Mobile**: new 4th tab **Pulse** (◎) mounts the intel dock so phones regain
  Public Attention (the tabbed IA had dropped it).
- **REGRESSION owned + fixed**: the tabbed-IA `display:none` map toggle exposed
  an unguarded `map.getLayer()` in `ensureLayer` → crash-loop → console stuck on
  loader / blank map. Guarded ensureLayer/setLayerVisibility + `map.resize()` on
  Map-tab show. Also: country drill-in from a thread now renders ABOVE the thread
  overlay (z 9100 > 9000) — was opening behind it on mobile.
REMAINING L2: A3 (scope strips), A4 (first-click walkthrough), C3 (per-thread
public attention). Lesson re-logged: VERIFY a panel before assuming; the NLP
backlog still gates verified subjects (gazetteer types honestly meanwhile).

**2026-06-30 — TRACK CONSOLIDATION COMPLETE (Pedro):** the two-chat split is
over; the engine chat closed at the **v2-gate checkpoint** + wrote its final
handoff (`docs/state/2026-06-30-engine-chat-final-handoff.md`, 5 points), this
chat ABSORBED it → now the SINGLE living track owning engine + frontend. No more
"reserved" — but the **heavy-compute discipline stays** (M1 crons ON: classifier
30min + embed 17:30/23:30/05:30 + **emergent-snapshot REVIVED 2026-06-30 mindful
@ 20:30/02:30** — it had frozen the served living topics; re-enabled off-peak in
the embed gaps, Background QoS + nice 10 + `taskpolicy -b`, RunAtLoad off; M1
crashed at load 177 from stacked compute, so any heavy local pass goes off-peak
AROUND the embed cron, efficiency cores). Owned
engine state: construction serves **v1** (unified-v2 built + A/B-wins, NOT
flipped — F4 gated on labeling+gold+read-path); **v2 reject gate LIVE** (567
force-fit demoted, `gate_model='v2-gate-e5-lr-1'`, reversible); `topic_members`
mig 057 (evidence+discussion populated, mood sparse, movement blocked #232).
PENDING off-peak: gold-growth pass (lifts gate balanced 61.5%→~80%), F4 cutover,
and the **attention/anomaly engine extension** (the 5-brains analysis — L2 spec
§"unified-engine connection", fold into `2026-06-29-atlas-unified-engine.md`).
**Un-versioned risk RESOLVED 2026-07-01:** `scripts/run-atlas-topic-classifier.sh`
versioned + synced byte-identical to AtlasLocalWorker (incl. new Step 4 incremental
category typing); still re-sync `apply_v2_reject.py` + `v2_gate.json` +
`compute_category_typing.py` on engine-code changes.

**2026-06-30 (parallel-chat L2 session, frontend-only — A3/A4/C3 closeout):**
Verify-before-assume paid off — the "REMAINING L2" list above was STALE.
Measured against code, not docs: **A3 scope strips ALREADY shipped** in
`6dfa6a0` (NarrativeThreads "Scoped to X ✕" country+person + blank-stream strip
+ sibling reason chips) — verified rendering live. **C3 forum lane ALREADY
shipped** (`public_attention.fetch_forum_thread_attention` + ThemeDetail
"DISCUSSION · UNVERIFIED", data-dependent render). Only genuinely-missing item
built: **A4 first-country-click walkthrough** (`CountryFocusWalkthrough.tsx`,
own `atlas_country_walkthrough_v1` key, fires once on first `handleCountryClick`,
guarded vs stacking on the first-session tour; step 2 highlights the focus-chip
✕ on desktop; position-accurate copy on mobile ("Tap"/"above the tabs"), spec §7
says deselect matters most there). **Mobile fix (Pedro caught it):** the shared
`.onboarding-card--mobile` bottom sheet (`bottom:16px`, `!important`) COLLIDED
with the mobile tab bar + the focus chip that floats above it → action buttons
clipped. Fixed with a dedicated `CountryFocusWalkthrough.css` `cfw-card-mobile`
class = a VERTICALLY-CENTERED card (own !important to beat the base rule) that
clears the top header AND the bottom chrome, leaving the chip visible below for
step 2. Browser-verified desktop (1440) + mobile (375): A3 strip + A4
walkthrough + A1 chip render together, card centered (top 293/bottom 519, tab
bar at 755), console clean, `npm run build` green, 112/113 vitest (the 1
fail = pre-existing `exportFormatters.test.ts` "Protest"→"Protests & Unrest",
a #204 taxonomy LABEL rename — reserved track, NOT touched). **C3(b) semantic
trends/wiki DEFERRED** (Pedro's call): per-thread trends/wiki still lexical
(`/trends/match`+`/wiki/match`, GDELT-theme-code → ~dead for dynamic threads);
deferred because trends/wiki data is thin/stale (#104 rate-limit, low ROI) and
the live path embeds ~100 candidates per ThemeDetail-open on the shared Fly
embed box (cheap pre-embed path touches the reserved AtlasLocalWorker tree).
Impl note in spec §"Execution status". **#234 finding:** the two remaining
items (thread-as-full-focus-lens + dock-PA-for-open-thread) both trace to ONE
root — thread-open clears focus BY DESIGN, deliberately kept by prior sessions;
needs an explicit greenlight (regression risk), not a quiet win. Files: new
`CountryFocusWalkthrough.tsx`, `App.tsx` (wire+trigger), `FocusIndicator.tsx`
(`data-tour="focus-clear"`). Uncommitted (commit on request).

Prior handoff: `docs/state/2026-06-25-consumer-mvp-pwa-session.md` — Consumer MVP shipped:
Atlas is now an installable PWA (vite-plugin-pwa, offline-last-Brief) with a
mobile single-column Brief feed + full-screen mobile thread read + honest
"Covered from" chips + offline banner (Tasks 1-5,7 of 8 deployed to Vercel).
Built via product-gap assessment → brainstorm (consumer read front door) →
spec → plan. Remaining: share-card (Task 6) + final Lighthouse/papers (Task 8).
Phase 2 (accounts/alerts/dossier) and #238 (subject-geography behind honest
chips) are the next tracks. Prior handoff:
`docs/state/2026-06-25-brief-dataquality-session.md` — live re-eval of the
surfaces moved the bottleneck from surface STRUCTURE to the DATA feeding them.
Shipped + deployed: Brief lead-story regression fix, geo mistag (title-only +
71-row backfill), count semantics #214, conservative same-event dedup,
thread-detail UX (readable headlines + source→coverage expand + hide-empty
drift), translatable coverage headlines. New umbrella **#238** (subject
geography — chips/dedup/cross-language all need subject-country, not coverage
volume). Prior handoff: `docs/state/2026-06-25-session-handoff.md` (adaptive
NLP fleet #184, #234 relations, papers). The dated blocks below are the
running registry.

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

**2026-06-24 — #234 thread-focus cross-panel (sibling threads, `8f544d4`):**
Verified thread-open clears focus by design (opens ThemeDetail + flies to top
country), so panels can't re-scope via the focus lens. Low-risk path instead:
NarrativeThreads surfaces a thread's SIBLINGS — threads sharing one of its TOP-2
(primary-geography) countries — and dims the rest, reusing the activeThreadId
prop, no focus-model change. Top-2 not all-5 (sharing US is too broad).
Browser-verified: open "Ukraine War Updates" (RU/KP) → "Oil and gas supply risk"
+ "News from Buryatia" surface, 17 dim. #234 now re-scopes for ALL focus kinds:
country (slice 1), person (map+threads precise+anomaly+sources), thread
(siblings). Precise future upgrades: rarity-weighted/entity-overlap thread
relation; thread-as-focus-lens if the open flow is ever made a lens. Map VISUAL
still needs Pedro's Vercel eyeball.

**2026-06-24 — #234 map VISUAL CONFIRMED on Vercel (Pedro):** the heat re-scope
+ camera fly verified good in prod. #234 fully closed for country/person/thread
focus — every main surface re-scopes, all verified end-to-end (the dev-preview
dark-map was a local source race only). Remaining are precise UPGRADES, not gaps:
rarity-weighted/entity-overlap thread-sibling relation; thread-as-full-focus-lens;
public-attention focus panels. #234 core = DONE.

**2026-06-25 — #184 NLP throughput: DIAGNOSED + reverted (incident logged):**
Goal = fill nlp_persons (flip typed subjects unverified→verified). Measured via
Supabase: nlp_sentiment 100% (fast-lane) but nlp_persons only 3.9% / ~680/hr vs
~7,000/hr ingest → 24h lag. Root cause: `nlp_worker.py` phase runners
LOAD-RUN-UNLOAD each model per cycle (to fit 4GB), and `NLP_WORKER_LIMIT` is a
Fly secret = 25 (not the 500 in the stale fly.toml comment). **INCIDENT:** the
throughput-bump redeploy applied `NLP_MULTILINGUAL_MODE=on` → heavy xlm-roberta
models load 140s/cycle on the shared-cpu-2x/4GB box, which ALSO hosts the embed
service (daemon thread, same process) → embed starved → `/api/v2/research/plan`
(semantic lane) timed out. FIX: `fly secrets set NLP_MULTILINGUAL_MODE=off
NLP_WORKER_LIMIT=25 NLP_WORKER_INTERVAL_SECONDS=120` → EN-only light models
(~11s cycles) → embed restored (plan 200/0.4s, was timeout). **STRUCTURAL
FINDING:** NER throughput CANNOT be bumped by config — the worker (per-cycle
heavy model load) and the embed service share one machine + Python process (GIL
contention). #184 is blocked on INFRA: (a) move the embed service to its own
machine, or (b) scale the worker box, or (c) decouple NER from the embed
process. Until then NER stays EN-only at baseline; typed subjects stay
gazetteer-typed (unverified). Multilingual NER (#162) has the same infra
dependency. Lesson: changing the NLP worker risks the co-hosted embed — verify
embed health on any worker deploy.

**2026-06-25 — #184 NLP worker MOVED to M1 (mindful daemon, embed freed):**
Pedro's fix: server = ingestion only; NLP/NER on the M1 (capable, no embed to
starve). Shipped a continuous **mindful** launchd daemon
(`com.atlas.nlp-worker.plist` KeepAlive + ProcessType=Background + Nice;
`scripts/run-nlp-worker-local.sh` wraps python in `taskpolicy -b` → EFFICIENCY
cores + nice 20, so it yields to foreground work). Runs from
`/Users/pedro/AtlasLocalWorker` (macOS TCC blocks launchd from the Desktop/iCloud
path — had to sync `enrichment/` there + install spaCy+en_core_web_sm into
`mlvenv`, which already had torch/transformers). New `EMBED_SERVICE_ENABLED`
flag (default true) — set false on M1 so the worker does NER only; the embed
service STAYS on Fly. VERIFIED LIVE: daemon checkpoints as `worker_id=m1-local`,
"NER[en-v1]: 300 signals", Cycle 1 done 306s (efficiency cores), embed restored
on Fly (research/plan 200/0.4s). Throughput ~3,500/hr (5x the Fly 680/hr) —
mindful efficiency-core rate, below the ~7k/hr ingest but hot-lane prioritises
recent so served signals get NER'd first. NOTE: the runner/plist are VERSIONED
here but EXECUTED from AtlasLocalWorker — re-sync enrichment/ on worker code
changes. Fly worker left at light EN/limit-25 (minor row-race with M1, idempotent
UPDATE). MORE THROUGHPUT (future): parallel mindful workers need SELECT … FOR
UPDATE SKIP LOCKED (no row lock today); or allow performance cores when idle; or
flip `ATLAS_NLP_MULTILINGUAL=on` once stable (M1 handles it → non-English
subjects verified, the #162 win that the Fly box could never do).

**2026-06-25 — MACHINE AUDIT + RESTRUCTURE (Pedro): one purpose per box.**
Final layout, each machine single-purpose, no NER↔embed contention:
- **Fly `app` (1GB shared-1):** API + ingestion (`start.sh`). Unchanged.
- **Fly `nlp_worker` (4GB shared-2x):** the EMBED service (e5, serves the
  research semantic lane — must live next to the API; M1 NAT can't serve it) +
  the light sentiment fast-lane. NER made RARE here via `NLP_WORKER_INTERVAL_
  SECONDS=600` + `NLP_WORKER_LIMIT=10` so the per-cycle model-load no longer
  starves the embed thread → research/plan back to a steady ~0.45s.
- **M1 `com.atlas.nlp-worker` daemon:** the bulk NER, MINDFUL (taskpolicy -b →
  efficiency cores + nice) — verified yielding: cycle 306s when idle → 606s when
  Pedro is active on the machine (exactly the "don't bother me" behaviour).
  Plus the existing M1 crons (topic-classifier, emergent-snapshot, embed-corpus).
NER_ENABLED flag (`deee88b`) is committed for a future clean nlp_worker deploy
(the process-group deploy kept failing to apply staged secrets / build a new
image — version stuck at 252; the interval=600 secret achieved the same goal
reliably). When that deploy lands, set NLP_WORKER_NER_ENABLED=false for true
NER-off on Fly. Throughput now ~1.5–3.5k/hr (M1, mindful) vs 7k/hr ingest —
hot-lane prioritises recent so served signals NER first; drains faster at night.
NEXT LEVERS: flip ATLAS_NLP_MULTILINGUAL=on on the M1 (capable → non-English
subjects verified, #162); parallel mindful M1 workers need SELECT…FOR UPDATE
SKIP LOCKED. Re-sync enrichment/ + the runner to AtlasLocalWorker on worker code
changes (they're versioned in repo, executed from the non-iCloud tree).

**2026-06-25 — Multilingual NER on M1: investigated, NOT enabled (finding).**
Tried to flip ATLAS_NLP_MULTILINGUAL=on on the M1 to verify non-English typed
subjects (#162). Verified instead of assumed — two blockers make it not worth it:
(1) `xx_ent_wiki_sm` (the multilingual spaCy NER) extracts Latin-script fine
(es: Gustavo Petro/PER + Bogotá/LOC; fr: Macron/Scholz/Paris) but returns
NOTHING for Persian/Arabic/CJK — exactly the diversity gap. The Problema-A
gazetteer already types those honestly, so xx adds no non-Latin value.
(2) The xlm sentiment model is broken in `mlvenv` (transformers 5.8 / Python
3.14 routes xlm-roberta's SentencePiece tokenizer to tiktoken → ValueError),
and there's no NLP_SKIP_SENTIMENT flag (only SKIP_FRAMING) — so multilingual mode
would crash the M1 worker's sentiment phase. Left M1 on EN-only (working). Installed
xx_ent_wiki_sm + tiktoken + sentencepiece into mlvenv (harmless). REAL non-Latin
NER win needs a proper multilingual token-classification MODEL (not xx_ent_wiki_sm)
+ a transformers env that loads xlm-roberta — a scoped task, not a config flip.
Meanwhile non-English subjects stay gazetteer-typed (honest, unverified).

**2026-06-25 — #229 coverage DIAGNOSED + #234 rarity-weighted sibling shipped.**
(While the M1 NLP drains.) #229 measured the funnel end-to-end (verify-before-
assume killed two wrong fixes): 174K signals/24h → 71K persisted corpus → only
**23 clusters/snapshot, mostly small**. Bottleneck is NOT promotion — the gate
works (0 candidates qualify-but-stuck); 150/181 candidates are 1-snapshot-new,
114 are <30 signals. Fast-tracking high-volume 1-snapshot candidates would help
**0** topics (no big stuck candidates; biggest clean 1-snapshot is <60 sig). So
coverage (50 active threads) ≈ the clustering's stable-large-cluster yield; the
signal mass stays HDBSCAN noise. REAL #229 lever = clustering RECALL
(`min_cluster_size` granularity + scoped regional passes, #229 lever 2) — a
data-layer task that runs on the M1 cron and needs offline quality testing, not
a quick code change. Logged for the next data-layer session.
#234 sibling upgrade (`NarrativeThreads.tsx`): added rarity-weighted entity
overlap to the thread-sibling relation. NAIVE entity overlap was HARMFUL —
verified on live data that one common GDELT entity ("donald trump", DF=14/30)
linked every unrelated thread (Pauline Hanson ↔ Venezuela Earthquake). Fixed by
counting only DISTINCTIVE entities (document-freq ≤ min(3, 25% of list)): trump
excluded, spurious matches gone, genuine geography-independent siblings still
surface (Humanitarian-access ↔ Flood-disaster via a shared rare actor). This is
the "rarity-weighted/entity-overlap" item from the #234 remaining list. Build
green, 74/74 vitest, 0 console errors, live-data verified. Remaining #234:
thread-as-full-focus-lens; public-attention focus panels.

**2026-06-25 — #234 sibling-relation LEGIBILITY + papers grown in-place.**
(a) Rarity-weighted entity-overlap thread siblings shipped (prev note). (b)
SIBLING REASON CHIPS (`2342ea3`): a surfaced sibling now shows WHY it relates —
"↔ <shared distinctive entity>" or "↔ <shared primary country>" — never a silent
dim (satisfies the no-silent-filtering / reason-codes guardrail). Browser-
verified: open "Ukraine War Updates" → 2 siblings chipped "↔ Russia", 17 dimmed,
0 console errors, 74/74 vitest. (c) PAPERS GROWN (Pedro's instruction — cross-
refs must be WRITTEN INTO the paper methodology, not just mentioned): Paper 7
(viz/workflow) gained the focus-propagation relation model + the rarity-weighted
finding ("donald trump" DF 14/30 launders relation → distinctive-only, same
volume≠importance principle as Paper 3 heat) + a relation-quality ablation to
collect; Paper 8 (open-set discovery) gained the #229 recall-ceiling measurement
(0.2% coverage, bottleneck = clustering recall not promotion, regional-pass
lever) as product evidence. Master plan: `docs/research/atlas-paper/2026-05-27-
atlas-papers-master-plan.md`. Remaining #234: thread-as-full-focus-lens;
public-attention focus panels.

**2026-06-25 — #184 ADAPTIVE NLP FLEET (parallel workers, throughput attack).**
Goal (Pedro): NER true-output → 100% (output==input) + drain the backlog.
MEASURED backlog: 208,238 signals un-NER'd (95%); 11,232 done (5% — Pedro's
estimate exact); ingest ~6.4k/hr. Shipped a sharded parallel fleet:
- **Sharding** (`nlp_pipeline._priority_select_sql`): `NLP_WORKER_SHARD_COUNT/INDEX`
  → each worker restricted to `id % N = K`. Verified EVEN + DISJOINT on the live
  backlog (N=4 → 52043/52080/52000/52115, sum = backlog). No row locks / no held
  transactions (the NER batch is slow — SKIP LOCKED would pin a txn open
  minutes×N; modulo sharding is the right tool for slow batches).
- **Adaptive supervisor** (`scripts/nlp_fleet_supervisor.py`): probes HID idle
  (`ioreg HIDIdleTime`) + AC power (`pmset`) every 30s. **GENTLE** (Pedro active /
  on battery) = 1 mindful worker (`taskpolicy -b`, efficiency cores, SHARD_COUNT=1,
  covers everything) — identical to the old single worker. **BURST** (idle>180s on
  AC) = N sharded workers at normal priority (performance cores). Drops back to
  gentle within 30s of Pedro touching the machine.
- **launchd** `com.atlas.nlp-fleet` (NO ProcessType=Background — that QoS clamp
  would propagate and pin the burst children to efficiency cores). Supersedes
  `com.atlas.nlp-worker` (booted out).
- **M1 is 8GB** (verified, not 16) + runs heavy ML crons → **BURST_WORKERS=2**
  (each worker peaks ~1.5GB; 2 perf workers ≈ 8-10k/hr > ingest, drains without
  OOM/swap; bump via ATLAS_NLP_BURST_WORKERS only if RAM proves comfortable).
HONEST throughput model: during ACTIVE hours NER stays gentle (~3k/hr < 6.4k/hr
ingest) so the backlog grows slightly — the mindful constraint trades instant
100% for never freezing the machine. During IDLE hours burst (~8-10k/hr) exceeds
ingest and drains + makes up the deficit. So "output==input" is reachable as a
DAILY AVERAGE given enough idle time, not instantaneously while Pedro works; the
208K backlog clears over ~days of idle bursting, then steady-state keeps up.
Faster levers if wanted: burst=3 (RAM permitting) or a dedicated always-on box
(not the 8GB M1). VERIFIED: gentle worker completed a cycle ("NER[en-v1]: 300
signals"); burst env validated (2 disjoint shards). Burst auto-triggers on the
next real idle window — watch `logs/nlp-fleet.out.log` for "switching gentle ->
burst". Re-sync enrichment/ + both scripts to AtlasLocalWorker on code changes.

**2026-06-29 — ENGINE REVIEW: GDELT decoupling + syndication + embedding/recall
investigation (spec `docs/specs/2026-06-29-atlas-engine-gdelt-decoupling-syndication.md`,
status REVIEW).** Pedro's "attack the Atlas engine directly" session. Diagnosis
(verified in code): the classifier is **split-brain** — a GDELT-theme lexicon
path (`atlas_topics`, `theme-hint-lex-v2`: `gdelt_theme_hints` set-membership OR
headline lexicon) ‖ an **embedding path** (`dynamic_topics`, e5 over
`passage: {headline}` — HEADLINE TEXT ONLY, no GDELT) — they never reconcile.
Root cause of nonsensical conflict threads CONFIRMED: GDELT `KILL` GKG theme is
wired as a hard hint into `armed-conflict-escalation` + `gender-violence-rights`
(`migrations/019:149,169`) and fires on idioms ("killing it"). **SHIPPED:**
SignalDetail "Where this fits" — renders backend `connected_threads`
(member/semantic/keyword basis badges) that was computed but thrown away; honest
empty state when nothing connects; GDELT taxonomy collapsed into `<details>`
(= truncated-spec T1.4; `SignalDetailPanel.tsx`+`.css`, build green). **Live
finding:** `dynamic-topic-262` "Las Vegas Travel Guide" ranked #0 @24h = ONE
travel article × ~25 Australian Community Media `.com.au` papers (135
serving-count). Syndication is a RANKING-COUNT problem (clustering already
headline-dedupes), fix = `headline_diversity` ranking INPUT + publisher-family
map (§4, the surviving shippable win). **TWO recall hypotheses DISPROVED on prod
(mapped, do NOT re-investigate — spec §8 + papers):** (1) enriching the e5 input
(`+entities`/`+country`) buys ~1pp; `+country` over-clusters by geography. (2)
HDBSCAN param tuning is a CLIFF — `leaf` purity 1.0 but shatters (Gaza recall
0.04, ~70% noise); `eom`/big mcs recall 0.97 but mega-blob (896/1074 rows, 0.49
purity = #224 black-hole). No high-recall+high-purity config → recall ceiling is
intrinsic to headline-only short text; real lever = scoped regional passes
(#229). Artifacts: `scripts/embedding_input_ablation.py`,
`scripts/cluster_recall_sweep.py`, `docs/research/embedding-ablation/` (run on M1
mlvenv, free compute). Papers updated: master plan P1 (KILL→theme-only ablation),
P4 (headline_diversity 4th ranking term + Vegas), P8 (recall negative result
mapped). Decisions (Pedro agreed): conservative diversity weight; defer coarse
bucket (honest gap stays); theme-hints STAY until §3.2 ablation proves semantic
parity (🔒 gate — removing them breaks Paper 1's 41.6% number); park article
bodies (worsens #184). NEXT BUILD = §4 syndication (`syndication_audit.py`
first). NOTE: Pedro running EqualEarthMap work in PARALLEL — this engine session
did NOT touch the map.

**2026-06-29 (PM) — UNIFIED ENGINE spec + F0 started; Vegas fix DEPLOYED;
silent-risk investigated+parked.** Continuation of the engine session, all
shipped to prod (Fly). (1) **Editorial-lane damp DEPLOYED + verified live**
(`3d5fe1e`): `classify_stream_lane` gained a `lifestyle` lane; `rank_threads`
damps lifestyle/sport/entertainment by label (damp, not gate). PROD: "Las Vegas
Travel Guide" #0→#7, "World Cup" #5→#10, real news leads. (2) **#172 silent-risk
investigated + VALIDATED + PARKED** (`docs/methodology/silent-risk-detection.md`,
issue #172): built the scaffold (`/api/v2/attention/silent-risks`,
`app/services/silent_risk.py`, `app/routers/attention_threads.py`), measure-first
DISPROVED the data source across iterations — wiki top-pageviews is
sports/celebrity (classified by Wikipedia category, not dropped — Pedro's
no-silent-filtering correction), velocity uncomputable (wiki_pageviews_v2 is
top-N only), and the **forum pivot does NOT clearly improve** (Reddit news subs
track mainstream coverage → not silent; the silent-risk phenomenon is RARE in
both sources). Real path = attention/coverage RATIO or local sources; parked.
Forum-research agent mapped open sources (Bluesky/Lemmy/Mastodon/Telegram/HN —
see the unified-engine spec §7). (3) **UNIFIED ENGINE — the big one.** Pedro's
thesis (validated): kill the split-brain (atlas-lexical ‖ dynamic-embedding ‖
discussion-attach = 3 parallel pipelines, different outputs, never reconcile);
ONE engine — any signal → embedding substrate → ONE typed `topic_members` table
(role: evidence/discussion/mood/movement); **unify construction, separate at
SERVING.** GDELT themes demoted to an optional confidence feature (kills the
RSS/forum asymmetry; full removal still gated on P1 ablation). HYBRID cutover:
serving unifies now (v1-compat ETL), construction rewritten behind
`ATLAS_UNIFIED_ENGINE` flag, A/B-measured, flip only when v2≥v1. Spec
**APPROVED**: `docs/specs/2026-06-29-atlas-unified-engine.md` (brainstorming →
spec-driven; phases F0-F4; plans to CLOSE #242/#168/#172/#237/#232; paper-track
impact mapped P1/P4/P5/P7/P8/P2 — the A/B IS Paper 1's split-brain-vs-unified
experiment; causal cross-vocab linking deferred). **F0 SHIPPED** (`413b391`):
F0.1 migration `057_topic_members` applied to prod; F0.2 `scripts/etl_topic_
members.py` v1-compat ETL — atlas-evidence parity EXACT (6734=6734, windowed by
`assigned_at` to match serving), dynamic projected by sample (constraint §10:
dynamic has only `emergent_clusters.sample_signal_ids`; full membership arrives
with unified-v2 F3). Then F1 (Bluesky+Lemmy ingest), F2 (source_family
clustering guard), F3 (unified-v2 + A/B), F4 (cutover). §17 decisions: dual
topic_id in F0; mood=nlp_sentiment in F1; F1=Bluesky+Lemmy first.

**2026-06-29 (PM cont.) — F0.3 + F0.4 SHIPPED + DEPLOYED (`2f87459`).**
**F0.3 unified read-flag:** `/threads` atlas-evidence path reads typed
`topic_members` (role='evidence') via `THREADS_SQL_TOPIC_MEMBERS` (mirrors
`THREADS_SQL` exactly: basis↔lex/theme, gate_kept/confidence carried, related
co-occ via `tm2`), behind `ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS` (default
**OFF** — prod serving unchanged). **A/B gate `scripts/engine_serving_parity.py`:
CRITICAL PARITY ALL PASS** (set/order/signal_count/gated/source/country/entities
EXACT across global+US+CO+topic) — only 2 documented cosmetic deltas
(related-chip top-5 reshuffle: current=all-time co-occ, unified=window-scoped =
MORE correct; avg_confidence ±1e-3 REAL-vs-double). **ETL BUG FOUND+FIXED:**
F0.2 stamped `topic_members.assigned_at = now()` (insert-time) → serving-window
would have served aged-out rows (7449 vs correct 6734); now carries SOURCE
`assigned_at`, re-seeded (windowed 6734=6734 exact). **Flip is Pedro's** (1 env
var) after eyeballing the chip change — do NOT flip blind. `/theme/{id}`
read-swap deferred to F3 (detail gate path separate; LIST parity is F0 accept).
**F0.4 relationship endpoint:** `GET /api/v2/topic/{id}/relationship` — 5 #168
types (media/public/social-led, silent-risk, uncoupled) from `topic_members`
role-count ratios (`app/services/topic_relationship.py:classify_relationship`,
pure, 14 tests; accepts raw topic_id or `slug--cc`). DEPLOYED+SMOKED (prod:
armed-conflict→media-led 1412). **HONEST current state:** ALL atlas topics =
`media-led` — discussion/mood lanes are 0 (`semantic-discussion-v1` has **0
source rows**, not just cron-fresh); public/social-led/silent-risk fire only when
F1 forum ingest populates discussion+mood. **Issues:** #168/#172 commented
(serving half delivered; full close at F1 when the 5 types differentiate on real
data). **Papers:** P4 spec (`2026-05-24-living-narrative-threads.md`) + master-
plan cross-ref row updated (typed membership + 5 types = P4; A/B = P1; serving =
P7). **NEXT = F1**: Bluesky Jetstream + Lemmy ingest workers → `signals_v2`
social (instance/lang=country), embedded, attached as discussion members —
THEN the relationship types light up.

**2026-06-29 (PM cont.2) — CLASSIFIER CRON FIXED + F1.2 Lemmy + discussion chain
made recurring.** (1) **Classifier cron was dead since the power outage**
(`exit 1` × 8, silent since 06-27 12:04 → why 24h threads were starved + topic_
members had no fresh evidence). Root cause: launchd's minimal env has no
`DATABASE_URL`; the runner fell to a `fly ssh` fetch that fails under launchd,
and `set -euo pipefail` aborted the script before python (no logs). FIX
(`/Users/pedro/AtlasLocalWorker/run-atlas-topic-classifier.sh`, NOT in repo —
un-versioned): source `.env` first + made fly-ssh fallback non-aborting.
Verified end-to-end under launchd (exit 0, 425 assignments, fires every 30min);
`/threads?hours=24` serves atlas again. (`local-hot-cold-catchup` also exit-1
from the outage — archive job, left.) (2) **DISCUSSION-ATTACH BUG (the real
reason 0 `semantic-discussion-v1` rows for weeks):** `assign_discussion_topics.py`
INSERT `$3` was used as both `confidence` real AND a jsonb anyelement →
`AmbiguousParameterError` on EVERY real run (dry-run hid it). It was ALSO never
cron'd. Fixed `$3::real` (`f9af200`); proven: 24 embedded social → 2 attach at
0.90 precision-first → `topic_members` discussion role → prod relationship
endpoint reads real `discussion_count` (armed-conflict 1, migration-border 1;
both stay media-led — evidence ≫ discussion, correct). (3) **F1.2 Lemmy ingest**
(`9e5e917`, DEPLOYED): `app/services/ingest_lemmy.py` — 9 live instances,
`type_=Local`, instance→`source_origin_country` (WAVE-N voice model for forums),
wired into `ingest_loop` every 4th cycle, 7 tests. LIVE: 125 social signals,
country-tagged (feddit.dk DK/DK; lemmy.ca→US-subject/CA-origin). (4) **Recurring
discussion chain** (`33e71e0`): the M1 embed cron (3x/day) now does embed →
attach → `etl_topic_members` project (all pure-SQL post-embedding), so discussion
members + topic_members stay current with no manual runs. Synced runner + the 2
scripts to AtlasLocalWorker (were missing). When the F0.3 read-flag flips on,
move the ETL projection to the 30-min classifier runner (fresher evidence).

**2026-06-29 (PM cont.3) — F1.1 Bluesky + F2 clustering guard SHIPPED+DEPLOYED.**
**F1.1** (`97e1556`): `app/services/ingest_bluesky.py` — Jetstream JSON-over-WS
firehose (no creds / no atproto lib / aiohttp WS), bounded ~25s drain of
substantive top-level posts → social. Bluesky = one global network (no instance
home) → country via NER geocode, `source_lang` from BCP-47 `langs` reduced to
2-letter. Wired `ingest_loop` 4th cycle; 12 tests. LIVE: 185 signals/drain, **13
languages**. Bug fixed: BCP-47 (`pt-BR`/`zh-Hans`) overflow CHAR(2) source_lang.
**F2** (`711d3f4`): `snapshot_emergent_topics._social_seed_pred()` keeps
`source_family='social'` OUT of the HDBSCAN seeding pulls (social still embeds +
attaches as discussion; just never SEEDS) — env knob
`ATLAS_CLUSTER_ALLOW_SOCIAL_SEED` for the measured exception. Verified prod: 24
social excluded / 44,171 press kept; lands BEFORE the F1 volume embeds (spec §8).
Synced to M1 emergent-snapshot tree. **F0/F1/F2 now done.** **NEXT = F3**: unified
construction v2 behind `ATLAS_UNIFIED_ENGINE` (embed-all → assign → typed
`topic_members(unified-v2)`) + `scripts/engine_ab_report.py` (v1-compat vs
unified-v2 on coherence/recall/black-hole/evidence-purity/cross-source-binding,
spec §11) — the A/B IS Paper 1's split-brain-vs-unified experiment. Then F4
measured cutover. Forum volume now flows; lanes differentiate as Bluesky/Lemmy
embed + attach over the next M1 embed cycles.

**2026-06-29 (PM cont.4) — F3 UNIFIED CONSTRUCTION + A/B: split-brain→unified
PROVEN (PASS effective).** `build_unified_topics.py` (F3.1, `80ac5b0`): ONE numpy
assignment over the e5 substrate — every embedded signal → nearest active
`dynamic_topics` centroid (≥0.88; threshold is a measured CLIFF 0.82→98.6% /
0.86→70% / 0.88→37%) + role by `source_family` + §6 HDBSCAN-leaf new-topic
formation on the residual (recovers ~12%, the companion-spec cliff) → writes
`topic_members(engine_version='unified-v2')`, isolated from v1 serving.
`engine_ab_report.py` (F3.2, §11) RESULT over 168h: **v2 wins coherence
0.930>0.908, purity 100%>98.1%, black-hole 12.1%<19.0%, topics≥3 103>66**; members
6710<7874 BUT the surplus-quality test settles member-recall WITHOUT human gold —
v1's 2910 surplus members cohere **0.899 vs v1-shared 0.940** = v1
OVER-ASSIGNMENT, not lost signal. **VERDICT: PASS (effective) — unified-v2 is the
better engine** (Paper 1's experiment, measured; written into the P1 result
skeleton). v2 build is now RECURRING on the M1 embed cron (`ba7460d`: embed→attach
→ETL-v1→build-v2) so the A/B stays live. **F4 cutover NOT forced** — gated on
recurring build (done) + new-topic labeling (§6 step 5) + gold confirmation +
parametrizing the read path to serve unified-v2. **F3.3 movement** (#232): events
live in separate tables (`acled_conflicts_v2` ≠ `signals_v2`), so the movement
role needs a `topic_members` event-ref schema extension first — scoped, commented
on #232. #242 closed (subsumed); #237 progress-commented (forum ingest delivered).
**Engine arc F0→F3.2 COMPLETE + measured.**

**2026-06-29 (PM cont.5) — F3.2b LLM-judge: CONFOUND → taxonomy is the real lever.**
Tried to confirm the recall verdict with an independent modality
(`engine_recall_judge.py`, DeepSeek judges on-topic vs each engine's label). Result
negative-but-pivotal: `shared` members (assigned by BOTH engines) score **40–52%**
on-topic (legal filing→"Gang control", FEMA satire→"Constitutional crisis"). The
judge measures LABEL/TAXONOMY precision, not engine recall (broad atlas vs
specific/stale dynamic labels = not comparable). **So: architecture settled in
v2's favour on label-INDEPENDENT structural metrics, but topical precision vs the
current taxonomy is ~40–52% for BOTH engines → the dominant remaining lever is
TAXONOMY/LABELS (#204) + the gate, NOT the engine.** v2 cutover buys cleaner/
tighter topics, not topical precision. Verdict auto-flags the confound (shared<65%).
Commented #204 with the measured baseline (elevates it from "quarterly" to primary
lever); written into Paper 1 + spec §16 F3.2b. Also found (measure-first): the
NARRATIVE event sources are DEAD — `acled_conflicts_v2`=0 rows; only `events_v2`
(4.8M GDELT CAMEO, co-occurrence-bindable not embeddable). So F3.3 movement needs
event-ingestion revival OR a co-occurrence+schema build (commented #232), not a
quick increment. **NEXT priorities (re-ordered by evidence):** (1) #204 taxonomy/
label revision — the measured ~40–52% topical-precision ceiling; (2) a FIXED
precise gold label set so the recall judge is unconfounded + F4 has a real gate;
(3) F4 read-path + new-topic labeling; (4) forum-volume ramp differentiates lanes;
(5) F3.3 movement (event source revival + schema).

**2026-06-29 (PM cont.6) — #204 TAXONOMY REWRITE via multi-model/multi-persona
ensemble (Pedro greenlit). Candidate v2 BUILT + VALIDATED.** Foundation:
`backend/scripts/ensemble/model_clients.py` — provider-neutral async client over
DeepSeek + OpenAI(gpt-4o) + Gemini(CLI) + Claude(subagent path; **Anthropic API
credits dry** so Claude annotates via the orchestrator, not the API), 429/5xx
retry. **Phase A** (`phase_a_diagnose.py`): ensemble classified gate-kept EVIDENCE
vs the 30 crisis categories with an OUT_OF_SCOPE option → **30% unanimous / 46%
DeepSeek is OUT_OF_SCOPE** (force-fit; "Amazon buy that saved my marriage in the
heatwave"→Heat-health, book review→Armed-conflict). Precision ceiling is
STRUCTURAL: 100%-crisis taxonomy, no reject class. **Phase B**
(`phase_b_propose.py`+`build_candidate_v2.py`): model×persona (DeepSeek=wire-
taxonomist, GPT-4o=ontology-purist, Claude=geopolitics-analyst; Gemini quota-fails
long prompts). CONVERGENT: both KEEP the ~30 categories, fix via a rigorous
OUT_OF_SCOPE policy + per-category includes/excludes. **Candidate v2**
(`docs/research/taxonomy-revision/candidate-v2.json`): 27 all-consensus + 3
contested (housing/humanitarian-access/mining) + 2 flagged natural-hazard adds
(earthquake-volcano, wildfire-storm) + the reject policy. **Phase C**
(`phase_c_agreement.py`): inter-annotator agreement **v1 76% → v2 96% (+20pp)** —
validated. HONEST caveat: random sample is non-crisis-heavy so the gain is driven
by the reject class on the non-crisis majority (the core fix); in-category crisis
separability + the 3 contested need a **crisis-only gold κ phase**. Method+results
in `docs/research/taxonomy-revision/2026-06-29-taxonomy-revision-methodology.md`
(paper-grade: ensemble annotation + κ = the unconfounded benchmark the
production-label judge couldn't give). #204 commented. **NEXT: Pedro's interactive
round + the gold κ phase, then wire OUT_OF_SCOPE+excludes into the gate/assignment
prompts + add the 2 categories to `atlas_topics`.** Category NAMES barely move —
the value is the reject class + sharp boundaries.
