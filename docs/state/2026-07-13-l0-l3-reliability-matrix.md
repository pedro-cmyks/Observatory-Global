# Atlas L0-L3 reliability matrix — publication program baseline

**Measured:** 2026-07-12/13
**Purpose:** distinguish “surface loads”, “contract is honest”, and “artifact is
publishable”. A green render is not a green editorial system.

## Executive verdict

| Layer | Availability | Truth contract | Standalone value | Publication readiness |
|---|---|---|---|---|
| L0 Landing | green | green | green for expectation-setting | not a publication surface |
| L1 Brief | green after paint-budget repair | amber | amber | **red** — shared package is wired but current artifact is degraded |
| L2 Console | green | amber | amber/green for live exploration | not applicable; capture receipts incomplete |
| L3 Workbench | green overlay/empty-state | amber | amber when populated | **amber/red** — v2 synthesis exists, heterogeneous package not proven |
| Engine/ops | amber | amber | supports current product | blocks an honest daily auto-edition when snapshots are stale |

## Current production observations

### L0

- public route loads and communicates Atlas's information-sphere frame;
- CTA/prefetch bridges exist;
- no current browser/console error was observed.

**Gate:** keep. L0 is not where current product risk sits.

### L1

- `/brief` loads and the fixed-24h newspaper structure exists. A production
  regression measured about 19.2 seconds and exceeded the client's 12-second
  budget because two optional legacy queries waited sequentially; independent
  1.5-second optional budgets restored a warm response to 6.47 seconds;
- production can return Narrative Threads and provider-backed Editor's Analysis,
  but the result varies with cache/job timing;
- L1 consumes the shared Daily Investigation package only when it is `ready`,
  contract-compatible, complete-universe and non-truncated. The present
  `degraded` artifact activates a visible live fallback rather than silently
  masquerading as the edition;
- current ranking can surface generic/sports duplicate-like rows and still
  inherits legacy volume/editorial-lane logic;
- the current visual audit exposed direct thread-label/evidence mismatches,
  including a Ukraine label paired with Iran/NATO evidence and multiple
  unrelated entertainment/sports rows in the watchlist;
- the current prose is a short aggregate insight, not a cited connected article;
- L1 does not yet consume the dossier's citation, corroboration, graph, readiness,
  method, or reproducibility contracts.

**Gate:** availability passes; editorial quality fails. Do not market the
current L1 as Atlas's publishable daily investigation. It remains a useful
context front door and honest fallback while memberships are refreshed and
label/evidence fit is measured.

### L2

- `/app` loaded with Globe, Universe, time controls, threads, signal stream,
  attention, conflict, hazard and anomaly surfaces; no browser console error was
  observed in the current audit;
- focus propagation, hover cards, pins, replay and Deep History exist;
- event counts and related-thread rows still do not uniformly open exact member
  receipts or distinguish binding tiers in one contract;
- `FocusLens` time behavior is not yet shared by every focus-dependent panel;
- event-binding freshness passed its autonomous gate and #256 is closed;
  structured marker receipts remain #255.

**Gate:** L2 is already the strongest standalone product. The next work is
contract depth and coordinated time, not another surface.

### L3

- Workbench is an overlay inside `/app`, not a `/workbench` route. The overlay
  loads cleanly with separate-investigation empty state and the three-region
  model;
- unified pins, frozen snapshots, incremental thread constellation, dossier
  synthesis v2, numbered citations and corroboration already exist;
- the current connection provider remains thread-only and can exceed the serving
  query budget on a cold call;
- no current production run has demonstrated story + actor + signal + country +
  event/anomaly pins connected, time-remeasured, inspected and exported as one
  portable package.
- a production-shaped Iran plan now evaluates the complete current thread
  universe: 581 candidates with real embeddings, 18 primary, 563 expandable
  low-confidence and zero omitted. Weak support cannot reach primary through
  volume/movement, and coverage geography is not promoted as subject truth;

**Gate:** the NATO dossier proves the publication primitives, not the full L3
composition goal. Preserve the existing dossier as fallback while the shared
package adapter reaches parity.

## Daily Investigation foundation — live read-only measurement

The provisional backend was exercised directly against the live database; it
was not connected to production UI.

| Measurement | Result |
|---|---:|
| active top-level rows scanned | 458 |
| cursor exhausted | yes |
| semantic topic-count ceiling | none |
| candidate traversal alone | 0.845 s measured |
| edition cutoff | 2026-07-12 07:30:10 UTC |
| data lag at final run | 21.374 h |
| visual slots | 12 distinct labels |
| current-window snapshot receipts | 17 |
| receipt candidates inspected | 32 |
| package end-to-end | 12.935 s measured |
| 5W+H | what/when/how ready; where/why partial; who missing |
| dossier relation provider | degraded on serving timeout |

The recovered complete snapshot changed the current daily measurement to 546
candidates, 12 layout stories, 71 receipts and 5.4 hours lag. An edition-scoped
current label receipt removes stale lifecycle labels from L1 without rewriting
thread identity. A provisional embedding evidence-fit pass measured 150
eligible single-cluster topics and downranked seven bivariate q10 low-tail
outliers. The package remains `degraded` because `where` is coverage-only,
`why` is not causally measured and no final grounded article has been generated.

Important interpretation:

- the cursor contract works and no longer mistakes an empty batch for universe
  exhaustion;
- the expensive raw `topic_members × signals_v2` traversal was rejected after a
  live timeout and replaced with precomputed movement/snapshot metadata;
- the fixed edition now ends at the latest completed top-level topic snapshot,
  not wall-clock “now”; a 21-hour lag is disclosed rather than presenting stale
  data as current;
- only candidates with at least one receipt from the sealed 24-hour window may
  occupy the visual spine; checked candidates without a current sample stay in
  the ledger with `no_current_receipt_sample`;
- exact duplicate labels share one visual slot but both ledger rows remain;
- current receipt sampling is suitable for selection availability, not a claim
  of exhaustive per-story evidence;
- the result is **not publishable yet**: the actor/subject lane is not verified,
  relation enrichment is cold-path slow, and 17 receipts across 12 stories is
  too thin for a connected world article.

### Precomputed serving cutover

The expensive build is no longer an HTTP-path proposal. Migration
`075_atlas_daily_editions.sql` stores one sealed JSONB artifact per edition and
the scoped M1 runner builds it after the event binders, while it still owns the
heavy-job mutex. `/api/v2/investigation/daily-publication` performs one indexed
row read and never rebuilds an edition on demand.

| Measurement | Result |
|---|---:|
| stored edition row | 122.4 KiB |
| PostgreSQL buffers | 2 shared hits |
| PostgreSQL execution | 0.032 ms |
| warm end-to-end backend read + JSON decode | 232 ms |
| candidate traversal | 458 / 458, cursor exhausted |
| stored status | `degraded` |

The degraded status is intentional: the measured cutoff was 21.5 hours old,
`who` was missing, `where` and `why` were partial, and the explicit-window
relation provider was unavailable. Storage/latency is therefore solved; content
readiness is not.

## Engine and operations

| Contract | State | Consequence |
|---|---|---|
| heavy-job mutex + `503 db_busy` | shipped | serving fails honestly instead of false empty/500 |
| snapshot/data cutoff freshness | amber | the measured edition was 21h behind wall clock |
| `topic_movement` | green as current-state measure | usable for movement/surprise; no forecasting language |
| full evidence receipt lookup | red for request path | random reads over `signals_v2` can exceed 12s on cold cache |
| `dossier-connections-v1` | correct but cold-path slow | must cache/precompute or degrade independently for L1 |
| subject geography | Stage 1.1 complete-universe: 169/1,488 inferred; 1,319 explicit abstentions | frozen daily headlines now verify every selected story independently, but C7 remains read-only pending broader validation |
| actors/NER | amber | headline-visible person hygiene and typed subject-place actors repair daily `who`; upstream entity throughput still needs an autonomous SLA trend |
| public discussion | thin | who-says-what remains press-heavy; never call it public consensus |

## 2026-07-13 follow-up — deterministic readiness replay

The measurements above remain the historical baseline for the currently stored
edition. Replaying that edition through the corrected publication code changes
the readiness verdict without rewriting or backdating the sealed artifact:

- all 12 selected story nodes have independently corroborated subject
  geography; multi-country stories stay multi-country;
- headline-visible person hygiene removes byline/place leakage, and verified
  subject places satisfy the documented broad-actor definition without turning
  country overlap into a measured relationship;
- `who`, `what`, `when`, `where` and `how` are now ready; `why` remains partial
  because Atlas does not yet measure causality;
- the real scheduled event binders wrote 1,151 movement and 81 disaster
  bindings, then produced a 12-story/44-receipt daily artifact at 3.363 hours
  lag; #256 is therefore closed;
- batched multilingual NER reduced a controlled 300-row phase from about 874
  seconds to 67.90 seconds. The first autonomous batch-eight cycle wrote 1,200
  rows but took 1,183.8 seconds end-to-end, so it did not satisfy the SLA. A
  representative batch-16 run then processed 1,200 rows (996 transformer
  routes) in 160.82 seconds at 1.07 GB max RSS and zero swaps. #253 stays open
  for trend/residue follow-up: the restarted autonomous worker subsequently
  completed 1,200 NER rows in 131.20 seconds and the whole cycle in 266.4
  seconds, while the direct 24h pending count fell from 86,307 to 85,455.

The shared-package browser comparison now passes for availability and contract
honesty. The deployed API and Vercel proxy return 546/546 candidates, 12 story
nodes and 71 receipts; the five required promotion dimensions
(`who/what/when/where/how`) are ready, while causal `why` remains explicitly
partial. The evidence-fit lane was repaired after production exposed an
undeclared OpenAI SDK import: the HTTP implementation measured all 150 eligible
single-cluster stories and downranked seven low-tail outliers without hiding any
candidate.

The publication verdict is still not green because the stored edition ends at
07:33 UTC and exceeded the six-hour freshness gate before the corrected rebuild.
L1 therefore shows its visible live fallback. Browser smokes found no console
errors in `/brief`, `/app` or the populated Workbench, but the fallback still
contains low-value rows and at least one visible label/evidence mismatch. A
fresh autonomous complete snapshot, followed by editorial inspection of the
resulting article/package, remains the promotion gate.

### 2026-07-13 follow-up — visible subject geography contract

The first measured #257 slice is deployed on Fly image
`deployment-01KXE51C99XEY7TAQPPCXP5G1D`, app machine version 413:

- dynamic-thread list/detail evidence is scoped to the latest topic snapshot;
- `subject_countries` is inferred from frozen current receipts and is distinct
  from coverage-oriented `top_countries`;
- L2 prefers verified subject geography and explicitly labels coverage only
  when subject geography abstains;
- the production Senegal forcing case displays `Verified subject: Senegal`
  (`SN`), historical accented Sénégal receipts serialize as `SN`, and RDC
  receipts remain `CD` rather than being double-converted through FIPS;
- the production browser has no console errors, and the backend suite remains
  `1334 passed, 6 skipped`; frontend verification is `310 passed` plus a green
  production build.

This does not close #257. The same topic still contains Senegal and RDC material,
so its label is supported by some receipts but its umbrella is not coherent.
The next gate is complete-universe label/evidence-fit measurement and a visible,
reason-coded grab-bag/downranking ledger. Nothing was silently omitted, capped,
or deleted to make the forcing case pass.

### Embedding writer incident found during freshness verification

The 2026-07-12 17:30 embed run held the mutex for more than 397 minutes. Live
inspection showed four HNSW inserts in `DataFileRead`, with individual query
ages of 2–45 minutes. `signal_embeddings` was 484 MB and its HNSW index 596 MB
(1.09 GB total) on the shared 1 GB instance. This was not useful M1 compute; it
was database index thrash and would have prevented the 02:30 scoped snapshot.

The transactional embed child was stopped, orphaned inserts were cancelled,
and downstream ETL was allowed to continue. The writer now sweeps expired hot
rows before optional index maintenance and owns HNSW restoration from an outer
`finally`, so a bulk-write error cannot strand serving without its ANN index.
The index strategy still needs a measured maintenance run before the recurring
cron is changed; no signal or historical information was deleted to hide the
capacity problem.

### Controlled maintenance and ANN recovery (2026-07-13)

The guarded `--bulk-reindex` trial over 4,822 pending non-junk headlines proved
that dropping HNSW removes PostgreSQL insert waits, but exposed two independent
constraints:

- after 2,304 embeddings, the M1 stopped progressing in
  `MPSStream::copy_and_sync` / `MTLCommandBuffer waitUntilCompleted` while all
  PostgreSQL writer connections were idle;
- cooperative interruption correctly entered the outer `finally` and rebuilt
  HNSW, but rebuilding the 310K-row index saturated the shared database enough
  for `/api/v2/threads?hours=24&limit=3` to time out at 15 seconds while health
  still reported `db_ok=true` with degraded status.

The local embedder now releases the MPS cache after each successfully copied
batch. HNSW itself was then tested at `m=16`, `m=8`, and `m=4`: all variants
spilled or stopped progressing on the shared 1 GB instance, and the `m=16`
backend ultimately required a project restart.

Atlas cut the hot corpus to an IVFFlat cosine index (`327` lists for 326,762
build-time rows). It built in about 105 seconds. A 20-query exact-vs-ANN
benchmark measured recall@10 of `0.915`, `0.955`, and `1.000` at probes 5, 10,
and 20; probes 20 averaged 130.97 ms and is now set explicitly in both serving
semantic lanes. A rolled-back 256-row insert completed in 172.429 ms, versus
the prior HNSW path exceeding 120 seconds. The API was deployed and its health,
Research Plan, and stored Daily Publication contracts passed. Full evidence is
in `docs/state/2026-07-13-ann-index-recovery.md`.

This resolves the measured index mechanism, not the shared serving/batch
architecture. #241 remains open until a recurring writer cycle proves the
complete embeddings -> memberships -> movement -> publication chain.

## Required next gates

1. **Daily data maturity:** edition lag is visibly labeled; autonomous snapshots
   prove a fresh sealed cutoff before L1 switches to the new package.
2. **Receipt density:** every load-bearing daily node has dated receipts and a
   source-independence status; thin nodes move to anomaly/gap context.
3. **Relation latency:** cached/precomputed dossier relations or independent
   degradation keeps the daily endpoint inside the serving budget.
4. **L1 parity:** the new package renders behind a compatibility flag and the old
   Brief remains available until browser/editor comparison passes.
5. **L2 receipts:** Iran event/thread counts open exact/contextual member lists
   and all focus-dependent panels agree on the time lens.
6. **L3 composition:** heterogeneous pins, incremental edges, inspector, time
   lens and export pass the Iran forcing case.
7. **Publication:** daily, Iran and NATO packages pass the same citation and
   cold-editor rubric; only then publish a public/LinkedIn artifact.
