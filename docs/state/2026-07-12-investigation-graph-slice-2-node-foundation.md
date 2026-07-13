# Investigation Graph — Slice 2 node foundation delivery

Date: 2026-07-12 (production verification completed 2026-07-13 UTC)  
Branch: `v3-intel-layer`  
Grade: **pass_with_caveats**

## Delivered

- `atlas-investigation-v2` typed node contract for story, evidence, subject,
  country, source, event, anomaly, attention, asset, and temporal-slice pins.
- Stable node identity from node type, subtype, and live reference.
- Immutable capture boundary: caller-visible snapshot is deep-copied before
  live enrichment and retained beside `snapshot.live`.
- Validated observation ranges and optional replay cursor.
- Resolution states and receipts: `resolved`, `partial`, `metadata_only`, or
  `unavailable`, with adapter, timestamp, retryability, and caveat.
- Canonical Narrative Thread and signal/article adapters.
- Stateless `POST /api/v2/investigation/resolve-node` with reconciled completion
  counts. No LLM, embedding, persistence, or graph-edge assertion occurs.

## Verification

- TDD observed the route at 404 before implementation and the inverted time
  range being accepted before validation.
- Focused final suite: `10 passed`.
- Full backend suite before the production signal-query correction:
  `1239 passed, 6 skipped, 0 failed`.
- The production smoke then exposed an `UndefinedColumnError` because the first
  signal adapter requested columns not deployed on `signals_v2`. A failing SQL
  shape test was added, the query was reduced to deployed canonical columns,
  and focused tests returned green before redeploy.
- Fresh full backend suite on the final corrected state:
  `1240 passed, 6 skipped, 0 failed` in 23.09s.

## Production

Fly image: `atlas-api-pedro:deployment-01KXCSNV26YBREHB167TS0EZEA`  
Digest: `sha256:dd34a32999ceeaaf8b7052ee8a4e2680f93091d9c65274c6623bb1096eebedbb`  
App machine: `d8d2e46fe07e78`, version `400`, health `1/1 passing`.

Measured post-deploy results:

- country `IR`: HTTP 200 in 0.820s, deterministic metadata-only node with
  frozen voice/thread snapshot and explicit `canonical_enrichment_not_available`;
- thread `dynamic-topic-1594`: HTTP 200, resolved with 66 live signals while
  preserving the frozen analyst summary; cold 11.125s, cached 0.853s;
- signal `12614774`: HTTP 200 in 0.849s, resolved canonical headline/source URL
  while preserving the caller's frozen receipt.

## Judgment and next gate

The node boundary is usable and honest, so the slice passes. It remains
`pass_with_caveats` because only thread and signal have canonical server-side
enrichment; the other eight families deliberately pin as metadata-only until
their adapters land. Thread cold resolution also needs a latency budget/cached
snapshot path before the Workbench invokes it interactively at scale.

Next slice: stateless graph assembly and edge envelopes. It must accept several
resolved nodes, enumerate every requested pair, distinguish measured/inferred/
contextual/analyst edges, attach receipts or an explicit missing-receipt caveat,
and reject the tautological `Iran ↔ Iran` explanation as a narrative relation.
