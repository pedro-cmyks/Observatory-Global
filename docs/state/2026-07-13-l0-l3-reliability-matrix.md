# Atlas L0-L3 reliability matrix — publication program baseline

**Measured:** 2026-07-12/13
**Purpose:** distinguish “surface loads”, “contract is honest”, and “artifact is
publishable”. A green render is not a green editorial system.

## Executive verdict

| Layer | Availability | Truth contract | Standalone value | Publication readiness |
|---|---|---|---|---|
| L0 Landing | green | green | green for expectation-setting | not a publication surface |
| L1 Brief | green with freshness caveat | amber | amber | **red** — current edition is not the shared publication package |
| L2 Console | green | amber | amber/green for live exploration | not applicable; capture receipts incomplete |
| L3 Workbench | green empty-state | amber | amber when populated | **amber/red** — v2 synthesis exists, heterogeneous package not proven |
| Engine/ops | amber | amber | supports current product | blocks an honest daily auto-edition when snapshots are stale |

## Current production observations

### L0

- public route loads and communicates Atlas's information-sphere frame;
- CTA/prefetch bridges exist;
- no current browser/console error was observed.

**Gate:** keep. L0 is not where current product risk sits.

### L1

- `/brief` loads cleanly and the fixed-24h newspaper structure exists;
- production can return Narrative Threads and provider-backed Editor's Analysis,
  but the result varies with cache/job timing;
- current ranking can surface generic/sports duplicate-like rows and still
  inherits legacy volume/editorial-lane logic;
- the current prose is a short aggregate insight, not a cited connected article;
- L1 does not yet consume the dossier's citation, corroboration, graph, readiness,
  method, or reproducibility contracts.

**Gate:** do not market the current L1 as Atlas's publishable daily
investigation. It remains a useful context front door and honest fallback.

### L2

- `/app` loaded with Globe, Universe, time controls, threads, signal stream,
  attention, conflict, hazard and anomaly surfaces; no browser console error was
  observed in the current audit;
- focus propagation, hover cards, pins, replay and Deep History exist;
- event counts and related-thread rows still do not uniformly open exact member
  receipts or distinguish binding tiers in one contract;
- `FocusLens` time behavior is not yet shared by every focus-dependent panel;
- event-binding freshness and structured marker receipts remain #256/#255.

**Gate:** L2 is already the strongest standalone product. The next work is
contract depth and coordinated time, not another surface.

### L3

- `/workbench` loads cleanly with separate-investigation empty state and the
  three-region model;
- unified pins, frozen snapshots, incremental thread constellation, dossier
  synthesis v2, numbered citations and corroboration already exist;
- the current connection provider remains thread-only and can exceed the serving
  query budget on a cold call;
- no current production run has demonstrated story + actor + signal + country +
  event/anomaly pins connected, time-remeasured, inspected and exported as one
  portable package.

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
| subject geography | Stage 1 only, 9.7% inference | where/C7 cannot claim reliable subject truth |
| actors/NER | amber/red | who and shared-actor edges remain the main quality bottleneck |
| public discussion | thin | who-says-what remains press-heavy; never call it public consensus |

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

### Controlled maintenance result (2026-07-13)

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
batch. This is a stability mitigation, not evidence that the full run is safe.
GitHub #241 was reopened. Drop/bulk/rebuild remains recovery-only; it must not
become the recurring cron strategy on a database that also serves production.

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
