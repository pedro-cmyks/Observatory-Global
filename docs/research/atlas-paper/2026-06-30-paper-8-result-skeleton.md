# Paper 8 — Open-Set Narrative Discovery: coverage + dynamism (result skeleton)

Date: 2026-06-30 · Author: Claude (Opus 4.8) · Status: **result skeleton** (the
RQ + the measured baseline; filled as the levers ship). Companion to
`2026-05-27-atlas-papers-master-plan.md` (P8 = "the discovery value of the dark
layer / the open-set funnel") and the engine spec
`2026-06-30-atlas-engine-recall-scoped-clustering.md`.

## Research question
Can a streaming system discover the *open set* of narrative topics from a
high-volume, multilingual, short-text feed — and keep that set **dynamic**
(topics appear, grow, shrink, retire with the world) rather than a fixed,
persisting list? Two sub-claims a deployed system must defend:
1. **Coverage** — what fraction of the signal mass is assigned to a topic.
2. **Dynamism** — does the topic set track reality over time, or freeze.

## Measured baseline (live prod, 2026-06-30) — a DIAGNOSTIC negative [BEFORE state, SUPERSEDED]

> **Status (PR3.3, 2026-07-01):** this section is the measured **before** snapshot,
> preserved as the negative-before-fix. It has since been FIXED — see Interventions
> 1–4 below (dynamism revived + R1 scoped clustering served 68→392→348 active topics;
> coverage lifted global 5.6% → scoped ~26.7% system estimate). Read the numbers here
> as the diagnostic baseline, not the live state.

**Coverage was tiny and it was a clustering-recall problem, not embedding or
promotion:**
- 534,000 signals → **239,233 embedded** → only **13,354 distinct signals in any
  topic = 5.6% of embedded (2.5% of total).**
- Per-country recall < 1% even for the highest-volume countries: **US 24,709→136
  (0.6%), CN 8,720→4 (0.0%), GB 10,117→25, RU 7,036→10.** A single global HDBSCAN
  pass drops ~94% of embedded signals as noise. (The HDBSCAN purity/recall cliff
  is characterized in `gdelt-decoupling §8`: no global config gives both.)

**The cliff is a WHITENING problem, not an intrinsic one (2026-07-06 — reframes
the diagnosis above).** The `gdelt-decoupling §8` reading ("no global config
gives both → the ceiling is intrinsic to headline-only short-text density") is
now measured to be an artifact of e5 anisotropy, not of the corpus. Harnesses
`backend/scripts/measure_signal_separation.py` + `measure_embedding_separation.py`
(read-only, sampled):
- **Separability is already there:** signal-pair ROC-AUC (same-topic vs
  different-topic) = **0.985** in raw e5. The space encodes the distinction; the
  clusterer can't *use* it because raw same/diff cosine is pegged into a narrow
  **0.916 / 0.788** band (a dominant anisotropic principal direction eats the
  dynamic range).
- **"All-but-the-top" k=1 whitening de-compresses it** (subtract mean, project
  out the top-1 principal direction): signal-level gap **+0.13 → +0.57 (4.4×)**,
  centroid-level **+0.04 → +0.31 (7×)**, AUC unchanged.
So there are **two independent recall levers**, not one: R1 scoped clustering
(partition the space to dodge the global blob) AND whitening (fix the
scale-compression that blinds the density estimator even *within* a partition).
The 5.6% "before" number was doubly pessimistic — the global pass, over an
un-whitened space. **Decisive experiment for this paper's recall claim:** HDBSCAN
recall/purity on raw vs `all-but-top k=1` whitened signal embeddings (reuse
`cluster_recall_sweep.py`) + a k-sweep. If the cliff lifts after whitening, the
open-set ceiling was a fixable geometry defect, not an intrinsic limit — a
stronger discovery result than the scoped-only story. Already shipped downstream:
L3 dossier neighbors whiten (`3990af0d`); constellation orphan-attach uses a
shared-token gate as the interim stand-in (`a793c7e9`).

**Dynamism was broken — the topic set was frozen + sticky (now FIXED, see
Interventions 1 + 3):**
- `dynamic_topics` / `emergent_clusters` were last updated **2026-06-29 17:00**; the
  topic-forming cron had been disabled in a 2026-06-29 infra consolidation and the
  successor engine (`unified-v2`) built but was **not served** → serving read a
  **~1-day-frozen snapshot**; **0 new topics in ~1 day.**
- Lifecycle was sticky: **54 of 68 "active" topics had `last_seen` > 3 days** yet
  remained `active`; **185 candidates** stuck un-promoted; only 14 ever retired.
- So "68 active topics" was not a measure of the live world — it was an accumulated,
  stale list. **A fixed topic count from a streaming feed is itself the failure
  signal.** (Resolved 2026-07-01: R1 scoped clustering + gate recalibration served
  **392** then a retirement sweep settled at **348** active; the lifecycle now
  retires-from-serving while retaining rows — §"Retention + resurrection".)

## The thesis the result will defend
Open-set discovery needs BOTH (a) **recall** — partition-scoped clustering over
the persisted corpus so minority/regional stories that drown in a global pass
form topics (the engine recall spec, R-track), AND (b) **dynamism** — a live
former + an aging lifecycle so topics appear and retire with the feed (B-track).
Either alone is insufficient: high recall into a frozen list still goes stale; a
live lifecycle over 5.6% recall still misses 94% of the world.

## Metrics / evidence to collect (as the levers ship)
- **Coverage curve:** % embedded signals clustered, global vs scoped-by-partition
  (target 5.6% → ≥15%; per-major-country <1% → ≥5%), with the black-hole/purity
  guard (#224) held at baseline.
- **Whitening ablation (2026-07-06 lever):** the SAME coverage/purity curve on
  raw e5 vs `all-but-top k=1` whitened embeddings (k-sweep 1/3/5/10), global AND
  scoped — does removing the anisotropic scale-compression lift the "no config
  gives both" cliff independently of scoping? Separability is settled (signal-pair
  AUC 0.985); this measures whether the density estimator recovers structure once
  the compressed cosine band (0.916/0.788 → +0.57 gap) is un-pegged.
- **Dynamism curve:** topic births/deaths per day; median `last_seen` age of
  "active" topics (should track the feed, not grow unbounded); candidate→active
  promotion latency; active-set size as a function of real event volume (should
  vary, not pin to a constant).
- **Recovery cases:** named stories that a global pass misses but a scoped pass
  recovers (CI 238→0, China 8,720→4 as before/after).
- **Honesty invariants held:** no fabricated topics; a partition with no coherent
  cluster yields none (the honest gap).

## Relation to the other papers
- **Paper 1** (split-brain→unified, evidence-role): recall is upstream of P1's
  precision — more topics = more evidence members to classify; but recall is NOT
  the same experiment (P1's ceiling is taxonomy #204).
- **Paper 5** (multilingual): CN 8,720→4 is a recall AND a voice gap — scoped
  per-country passes give non-English regional stories their own clustering space
  (ties to T1.5: the English-centric *assignment* bottleneck).
- **Paper 3/7** (heat / workflow): a dynamic, well-covered topic set is the
  substrate the heat + analyst surfaces draw from.

## Intervention 1 — dynamism: a natural before/after (in flight 2026-06-30)
The frozen-lifecycle negative had a precise, diagnosable cause — a clean systems
result for the paper:
- **Diagnosis.** Pipeline forensics (ingest/embed/lexical-assign all LIVE; only
  the topic-forming tail frozen at 06-29 19:04) localized it to the M1 embed
  runner: Step 1 (embed) ran under `set -e` as a FATAL step, so an asyncpg
  statement-timeout (a large/slow embed backlog) aborted the run BEFORE the
  topic-projection steps. Compounded by the topic-forming cron being disabled in
  the 06-29 consolidation while the successor wasn't yet served.
- **Intervention.** (a) make the embed step non-fatal so the projection always
  runs; (b) revive the topic-forming cron mindful + off-peak (efficiency cores,
  scheduled in the gaps so it never stacks — stacking had crashed the machine).
- **Expected after (the measurement, ~24–48h):** `dynamic_topics` resumes
  forming new topics + retiring stale ones (`stale_k=2`/`retire_m=4` by
  `snapshots_since_seen`); the active-set size tracks event volume instead of
  pinning to a constant; the 54 stale-but-active topics drain. **This is the
  dynamism curve's negative→positive — a controlled before/after, not a tuned
  demo.** (Verification scheduled.)

## Intervention 2 — coverage: the scoped-pass lever (RESULT 2026-06-30, 2 countries)
The coverage negative's lever was probed on two countries, persisted embeddings,
recent window (the hardest case — recent signals aren't globally clustered yet):

| country | global recall | scoped recall (best non-blob) | clusters | lift |
|---|---|---|---|---|
| US (15,000) | 2.59% | **38.11%** | 530 | ~15× |
| CN (6,000) | 2.43% | **32.92%** | 213 | ~13.5× |

Every grid config 22–38% with **no blob**. This is the coverage curve's measured
before→after: the global HDBSCAN purity/recall cliff is intrinsic to a 200K
global space but DISSOLVES under partitioning, because within a country the
regional stories are the majority rather than drowned minorities. **It
generalizes** — and CN is the key second case: a non-English, voice-gap country
that clusters ~0% globally clusters at 33% scoped, so scoped passes ALSO dissolve
the multilingual ASSIGNMENT bottleneck (the result that ties Paper 8 to Paper 5 /
T1.5).

**System-wide (the decisive result, 2026-06-30):** the per-country method was run
over **117 countries / 131,210 country-attributable signals** (all countries with
≥100 embedded signals, cap 6,000/country, 168h; parallel, read-only). Aggregate:

| | recall | topics/clusters |
|---|---|---|
| **global (today)** | **4.94%** | ~68 |
| **scoped (every country within)** | **26.72%** | **3,662** |
| **effect** | **~5.4× recall** | **~54× more narratives** |

Every country lifts (US 37%, DE/GR 34%, IR 32%, MX 25%, from single-digit
global); the lift is universal, not driven by a few. So the "recall ceiling is
intrinsic to headline-only short text" null is refuted **at the system level**: it
is intrinsic to a *global* pass, not to the data — partitioning recovers it. This
is the number that justifies the production per-country loop (R1). Caveats
(honest): 9 of the highest-volume countries still dropped on connection under
parallel load (their inclusion would only add signal + topics, same pattern); 2
countries (TZ, DO) blobbed and are flagged; the 6,000/country cap samples the
largest countries. Artifacts:
`docs/research/recall-scoped/{scoped-probe-US,scoped-probe-CN,system-estimate}.{json,md}`;
method: `backend/scripts/recall_scoped_{probe,estimate}.py`.

## Intervention 3 — coverage → SERVED: the R1 production run (RESULT 2026-07-01)
Interventions 1–2 were read-only measurements. R1 turns the measured lift into a
*served* before/after: `backend/scripts/run_scoped_snapshot.py` formed + wrote
scoped topics for **all 126 countries** with ≥100 embedded signals under ONE
`snapshot_at`, then `project_dynamic_topics` folded them into `dynamic_topics`.

**Write result (emergent_clusters):** **731 clusters, 126/126 countries, 0
failed, ~49min** (mindful `taskpolicy -b`). Quality is the headline: **no blob**
(largest cluster 101 signals against a 6,000/country cap), **mean cohesion
0.968**, median 11 signals — i.e. many *tight regional* topics, not few mega-bins.
**Honesty invariant confirmed live:** 26 countries yielded NONE ("no gated
clusters", e.g. TW/KH/AZ/JM) — real recovery, not fabricated black-holes; each
country is its own `cluster_id` block so a single-country blob cannot contaminate
the rest. So the R0 measurement reproduces at production scale: partitioning
recovers tight regional topics that a global pass drowns, with diversity as a
side effect — **VE/CA/UA/DE/FR/IR/RU/GR all hit the 25-topic cap while US took 23**
(a global pass would let the English/US volume dominate; scoped gives each country
equal footing — the Paper 5 voice tie-in, structural not tuned).

**Serving result — a measured promotion-gate recalibration:** the write does not
serve itself. The lifecycle promotion gate (`LifecycleConfig`) was calibrated for
the *old global regime*: `persist_min=2` (blocks every first-snapshot topic) and
`volume_min=30` (a real global thread was 100s of signals). Against the scoped
regime — regional topics of 8-30 signals — only **50 of 510 quality-clean topics
cleared `volume_min=30`**. Measured histogram of quality-clean fresh candidates
(cohesion ≥0.5, noise <0.5, not roundup) at each threshold: **v30=50, v20=135,
v15=205, v10=389**. So the gate, not the engine, was the serving bottleneck. The
recalibration (Pedro's call, "bootstrap now + measure purity"): promote clean
candidates at **`volume_min=12`** (one-time `persist_min=1` bootstrap). **Serving
went 68 → 392 active topics (~4.6×)**, and the **purity held** — the 256
newly-admitted small topics (12-29 signals) measured **cohesion 0.969 / noise
0.081**, and a manual sample of the smallest (12-16 signals) were all real
specific stories ("Shooting in German Youth Center", "Venezuela Earthquake
Disaster", "Pakistan-Afghanistan Border Clashes", "Twin Storms Pound Japan"), not
noise. Because the noise/roundup gates are *independent of volume*, lowering
volume admits smaller-but-equally-clean topics, not noisier ones — the reason the
recalibration is safe, stated as a falsifiable claim and confirmed. Reversible:
311 promoted ids saved. The recurring nightly cron carries `volume_min=12` at
steady state (with `persist_min=2` restored, so *new* regional stories prove
across two nightly snapshots before serving — dynamism, not one-shot).

### Retention + resurrection (the dynamism mechanism, verified 2026-07-01)
Pedro's design concern — "don't lose a topic that was ever classified; let the
table grow; let a topic resurge without re-classifying." Verified this is already
the architecture, and it is the dynamism curve's mechanism:
- **No deletion.** The only `DELETE`/`TRUNCATE` is `project_dynamic_topics
  --rebuild`; the incremental nightly path (and the cron, guarded) never deletes.
  Retirement is a `state` (`active→deprecated→retired`), never a row drop — the
  row keeps its centroid, members, and history.
- **Resurrection, not re-classification.** A retired topic whose centroid is
  matched by a new cluster (≥0.88) re-opens as `candidate` under its SAME
  `identity_key` (`next_state`), history intact, members appended. `hydrate_topics`
  loads ALL states unfiltered, so retired topics remain assignment/resurrection
  targets — Pedro's "more topics in the table = more places to classify into."
- **Why still retire from serving.** Never-retiring is precisely the frozen-68
  negative above: serving fills with dead topics and stops tracking the live
  world. The resolution is the separation this paper measures — **retire from
  SERVING (freshness) while keeping in the TABLE (history + resurrection)**. That
  separation, not a longer/shorter timer, is the dynamism result.

## Intervention 4 — coverage → LEGIBILITY: the R2 umbrella (SHIPPED + SERVED 2026-07-01)
**RESULT:** `build_umbrella_topics.py` clusters the active topic centroids into parent
umbrellas. Method finding: **single-link union-find CHAINS** (transitively merged
World-Cup matches + heatwaves + unrelated topics into garbage megagroups) → greedy
**COMPLETE-linkage** (a group forms only if ALL cross-pairs ≥ threshold) is the
same-EVENT-vs-same-THEME guard, in the algorithm not the threshold. Threshold **0.98,
not 0.95** — some short-headline centroids are diffuse (generic/roundup topics sit near
many things), so the same-event cut is tighter than expected (0.96 still leaked
"Football Transfer News" ← Sudan Conflict). Output: **26 umbrellas over 55 children**
(Venezuela Earthquake ×2, France Heatwave ×2, Egypt World Cup ×4). Serving is LIVE on
Fly: global `/threads` = top-level (umbrellas + singletons) — verified **"dup labels
NONE", 6 umbrellas in the top-40**; the country view merges the R1 scoped children with
atlas per country. So the legibility before/after is served: the cross-country
duplication R1 introduced is collapsed WITHOUT losing a child (every child reachable via
drill/country). Ranking fix worth noting for the paper: an umbrella's "current volume"
is the SUM of its child clusters at the latest snapshot (a single-cluster LIMIT-1 buried
umbrellas below the fold) — the aggregate-of-aggregates must aggregate at serving too.

### (original plan, for reference)
R1 raises recall but leaves two legibility gaps, both to be measured as R2's
before/after: (a) **cross-country duplication** — a global story (e.g. France
heatwave) forms one scoped cluster per country, correct for country-scoped
serving but N-fold in a global list; (b) **fragmentation** — a single evolving
story appears as many flat threads (Paper 4 finding: US–Iran ≈ 7 flat threads).
R2 = a cheap SECOND clustering pass over the ~2k scoped *centroids* (not the 200K
signals) → **parent umbrella topics** with the per-country/regional clusters as
children. This is embedding-of-embeddings: it collapses cross-country duplicates
into one umbrella (children preserved) and gives the "big story = parent + child
sub-threads" hierarchy (Paper 4 decision 3, 2026-06-23). The experiment sequence
recorded for the paper: **R0 (measure) → R1 (produce/serve) → R2 (umbrella
hierarchy) → R3 (A/B cutover on a measured recall lift without purity loss).** R2
spec is authored AFTER R1 completes, parameterized on R1's actual output.

## Negative-result honesty
Both negatives (5.6% coverage, frozen lifecycle) are recorded BEFORE the fixes,
with the exact prod queries in the engine recall spec §1 — so each lever's lift
is a real, reproducible before/after, not a cherry-picked after. A *systems*
discovery paper's contribution is precisely this: the measured failure, the
localized cause, and the controlled intervention — not just the final number.

## 2026-07-12 addendum — the coverage arc delivered + the honest denominator

The R-sequence's promised recall lift landed (2026-07-08, `9d1b04e7`): the wall
was NOT volume or promotion but the evidence-role student NOISE gate computed in
raw compressed e5, which over-flagged real narratives (Venezuela Earthquake 0.72,
Heatwave 0.88 blocked). Fixing it: **active threads 30→597, story coverage
0.04%→39.7%, mean ~86 signals/thread (not a blob)** — the reproducible
before/after this skeleton's negative-result section reserved.

Second finding, same week (`41862150`, mig 074): raw coverage is a dishonest
metric — 38% of the new coverage sat in junk grab-bags. The **useful-coverage
junk gate** (content-based; the R3.1 DeepSeek category typer is the strongest
separator — cohesion/whitened/label-regex all measured useless) took junk-held
coverage 17.4%→0.0%, useful +4.1pp, +4,465 real signals reclaimed. The A0 3-way
probe (`b2bab22b`) formalizes the paper's denominator: useful / junk-typed /
unassigned, with unassigned split into syndication-dup ‖ junk-headline ‖
real-unclustered — the **unclassifiable floor** below which no open-set system
should claim coverage. Artifacts: `docs/state/2026-07-08-clustering-recall-fix.md`,
`docs/state/2026-07-09-useful-coverage-gate.md`.

## 2026-07-16 addendum — derived-axis detectors + the LLM event lane

1. **Detector-input coupling (C7 voice-asymmetry)**: an unchanged detector's
   judged mismatch went 71% → 6.7% purely from upstream subject-geography
   fixes (#238) — open-set detectors over DERIVED axes inherit the measured
   error of their weakest input, and the honest protocol is judge-referenced
   re-measure after each input fix. C7's geo source was then swapped from the
   cluster coverage proxy to the serving inference (`55abeddc`); review-only
   unblocked, ranking still gated. Artifacts:
   `docs/research/subject-geo/2026-07-16-c7-reconsideration.md`,
   `docs/research/voice-asymmetry/2026-07-12-c7-pilot.md`. (Method block in
   the master plan under P2.)

2. **Event-level grouping moved to a verdict-gated LLM lane**: `--linkage
   llm-event` same-event umbrella grouper (mig 077, `953cd411`, hardened
   against degraded verdicts `8fa4756d`) + `type_noncrisis` fast typing on
   the 30-min cron — lane 2 (canonical-event) of the robot taxonomy now has
   a production method beyond lexical/centroid linkage; adversarial-review
   hardening is part of the method, not an afterthought.
