# Investigation Graph — Slice 1 reliability delivery

Date: 2026-07-12 (production verification completed 2026-07-13 UTC)  
Branch: `v3-intel-layer`  
Grade: **pass_with_caveats**

## Outcome

The shared investigation substrate used by L1, L2, and L3 no longer performs
the legacy atlas-category aggregation on the default stories-only Narrative
Threads path. Database-owned thread timeouts now surface as an honest
`503 db_busy`, and the semantic research lane preserves every healthy
subcomponent when another one fails.

This is the reliability precondition for the approved typed Investigation
Graph. It does not claim that graph persistence, heterogeneous node resolution,
Workbench composition, or the shared L1/L3 `PublicationPackage` are implemented.

## Delivered commits

- `e70673a9` — skip the discarded atlas query on stories-only thread lists;
  preserve the explicit category-row rollback switches.
- `3b010e74` — translate only timeouts inside the thread database boundary to
  `DatabaseBusyError`, mapped to `503 db_busy` with `Retry-After: 10`.
- `bdce07fb` — isolate `story_centroid`, `topic_description`, and
  `signal_headline` semantic failures and expose component-specific gaps.
- `a5995fa5` — remove two stale test assumptions: invalid optional annotator
  scopes intentionally abstain to `None`, and Theme Insight credentials are
  owned by the central Anthropic-to-DeepSeek provider chain.

## Automated verification

Fresh full backend run:

```text
1230 passed, 6 skipped, 0 failed, 22 warnings in 25.05s
```

The six skips are the suite's declared conditional integration/model tests.
The implementation-specific red/green cycles covered:

- stories-only thread query budget;
- category-row kill-switch preservation;
- database-command timeout translation without relabeling generic timeouts;
- real FastAPI `503 db_busy` response and headers;
- independent failure of all three semantic retrieval components;
- no false "thin centroid pool" diagnosis after a centroid timeout.

## Production deployment

Deployment command: `scripts/deploy-fly-api.sh`  
Fly image: `atlas-api-pedro:deployment-01KXCRYT1K1VN352NZC04K5Q77`  
Image digest: `sha256:de2411422f717cc5dae0eacac2eabb6c61f7bc12f527e8e3eb7ce89ed181c5b6`  
App machine: `d8d2e46fe07e78`, version `398`, region `iad`  
Health: `1/1 passing`

The deploy completed successfully. Fly emitted a metrics-token warning after
deployment; it did not affect the machine update, DNS check, or health check.

## Production smoke evidence

All values below were measured after deployment against
`https://atlas-api-pedro.fly.dev`.

| Flow | HTTP | Time | Evidence |
| --- | ---: | ---: | --- |
| Threads, 24h, limit 10 | 200 | 1.638s | 10 rows; first `dynamic-topic-2036` |
| Threads, 168h, limit 24 | 200 | 2.023s | 24 rows; first `dynamic-topic-1594` |
| Research: `NATO summit Ankara`, 24h | 200 | 7.771s | 1 thread anchor, 1 pin candidate, no gaps or generic thread timeout |
| Research: `Israel plot to kill Iran negotiations`, 168h | 200 | 5.374s | 13 thread anchors, 6 pin candidates, no gaps or generic thread timeout |
| Iran selected thread detail | 200 | 1.087s | 66 signals, 23 evidence receipts |

Fly logs after deploy show the app startup completed and the observed thread
requests returned `200`. The same shared database still produced handled
timeouts in unrelated anomaly/correlation queries while the app remained live;
that is evidence that P1.2 serving/batch isolation remains real infrastructure
work, not a reason to weaken the honest-degradation contract.

## Caveats and judgment

The slice passes its data/API acceptance criteria. It is graded
`pass_with_caveats`, rather than `pass`, for two reasons:

1. The integrated browser controller could not attach a newly created Atlas tab
   during the post-deploy visual smoke. No frontend files changed in this slice,
   and the exact UI-facing APIs passed end-to-end, but a fresh visual walkthrough
   was not falsely recorded as complete.
2. Database contention exists beyond Narrative Threads. The durable correction
   remains the planned serving/batch separation/read replica; this slice removes
   wasted thread work and makes failure truthful, but does not cure the shared-DB
   architecture.

## Next executable slice

Build the typed Investigation Graph foundation:

- canonical node identity and `resolve-node` adapters for thread, signal,
  country, entity/person, source, anomaly, structured event, hazard, and asset
  observation;
- immutable snapshot plus live reference for every pin;
- measured/inferred/contextual/analyst edge envelopes with receipts;
- graph assembly from one saved investigation without changing the current
  Workbench UI yet.

That slice should end with an API-level forcing case that pins two Iran-related
threads plus a conflict event, a country, and a person, and returns a reconciled
typed graph with no tautological `Iran ↔ Iran` edge.
