# Investigation Graph Slice 2 Node Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize every currently planned L2 pin family into a stable `atlas-investigation-v2` node with an immutable observation snapshot, live reference, quality envelope, and honest resolution status.

**Architecture:** Add a focused investigation-node service with Pydantic contracts and an adapter registry. Thread and signal adapters enrich from canonical backend records; every other declared pin family can immediately preserve its visible client snapshot and live reference as `partial` or `metadata_only`, so unsupported enrichment never blocks the pin. Expose the contract through a stateless `POST /api/v2/investigation/resolve-node` router.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, asyncpg, pytest.

## Global Constraints

- Contract version is `atlas-investigation-v2`.
- Pins preserve a frozen observation and a separate live reference.
- Node types are `story`, `evidence`, `subject`, `country`, `source`, `event`, `anomaly`, `attention`, `asset`, and `temporal_slice`.
- Resolver failure returns a usable metadata-only node with a named caveat; it does not invent enrichment.
- LLMs are not involved in node identity, type, quality, or resolution.
- No database migration or frontend rewrite belongs to this slice.

---

### Task 1: Define and prove the typed node contract

**Files:**
- Create: `backend/app/services/investigation_nodes.py`
- Create: `backend/tests/test_investigation_nodes.py`

**Interfaces:**
- Produces: `ResolveNodeInput`, `InvestigationNode`, `ObservationWindow`, `resolve_investigation_node(...)`.

- [ ] Write failing tests proving all declared node types validate, identical live refs create identical stable node IDs, caller snapshot mutation cannot mutate a resolved node, and missing enrichment yields `metadata_only` with a retryable caveat.
- [ ] Run `cd backend && .venv/bin/pytest tests/test_investigation_nodes.py -q` and observe RED.
- [ ] Implement the minimal Pydantic models, canonical JSON/deep-copy snapshot boundary, deterministic SHA-256 node ID, adapter dispatch, and resolution receipt.
- [ ] Re-run the test file and require PASS.
- [ ] Commit as `feat(graph): add typed investigation node contract`.

### Task 2: Add canonical thread and signal adapters

**Files:**
- Modify: `backend/app/services/investigation_nodes.py`
- Modify: `backend/tests/test_investigation_nodes.py`

**Interfaces:**
- Thread adapter consumes `fetch_thread_detail(thread_id, hours)`.
- Signal adapter consumes an injected `signal_fetcher(signal_id)` returning the canonical signal row.
- Both preserve caller-visible snapshot fields while adding canonical receipts under `snapshot.live`.

- [ ] Add failing tests for resolved thread and signal nodes, including evidence/source URL preservation and an adapter exception that degrades only that node.
- [ ] Observe RED with the focused tests.
- [ ] Implement the two adapters without embedding, classification, or prose generation.
- [ ] Run the complete node test file and require PASS.
- [ ] Commit as `feat(graph): resolve thread and signal nodes`.

### Task 3: Expose and verify `resolve-node`

**Files:**
- Create: `backend/app/routers/investigation.py`
- Modify: `backend/app/main_v2.py`
- Create: `backend/tests/test_investigation_router.py`
- Modify: `docs/state/2026-07-12-investigation-graph-slice-2-node-foundation.md`

**Interfaces:**
- Produces: `POST /api/v2/investigation/resolve-node` -> `{contract, node, completion}`.

- [ ] Add a failing real-app request test for a country snapshot and a signal resolution test with the database fetcher injected/overridden.
- [ ] Observe RED because the route is absent.
- [ ] Implement the router, canonical signal query, router registration, and database-busy propagation.
- [ ] Run node/router tests, then the full backend suite.
- [ ] Deploy through `scripts/deploy-fly-api.sh` and smoke a metadata country pin plus a live signal/thread pin.
- [ ] Record counts, status, caveats, deployment identity, and grade in the state document.
- [ ] Commit and push `v3-intel-layer`.

## Self-Review

- This plan intentionally ends at the node boundary. Edge engines, graph assembly, persistence/migration, L1 selection, Workbench UI, and `PublicationPackage` remain later independently testable slices.
- Every planned node type is accepted now; the response distinguishes canonical enrichment from client-frozen metadata instead of pretending all adapters have equal depth.
- The same input produces stable identity, but `pinned_at` remains an observation timestamp and is not part of identity.
