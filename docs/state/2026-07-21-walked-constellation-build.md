# The walked constellation — v1 BUILD (2026-07-21)

Spec (contract): `docs/superpowers/specs/2026-07-21-multi-hop-transitive-chains.md`
(authored in a parallel design-session worktree; the Phase-0b probes
`walk_probe*.py` measured + LOCKED the numbers). Journey-map §1 (inert bridge
stars) is the UX gap this closes. **Not deployed — awaiting Pedro's ok.**

## What shipped (spec §5 build order)

**Backend — `app/services/constellation_walk.py` (PURE, numpy-only, 21 unit tests):**
- `build_knn_graph` — top-k=6 whitened-cosine neighbor graph. Commits to the ONE
  global whitening (`services/whitening.py`), **not** the raw universe kNN
  (`universe.py:132`) and **not** the dossier per-request refit (spec §2.2).
- `max_product_walk` — from-pins, multi-source, max-product walk. Brake =
  **REL_FLOOR 0.35 + HOP_CAP 3** (both load-bearing; LOCKED Phase-0b). Per-origin-
  seed relative floor; blob penalty on hops OUT of a flagged connector.
- Kinship: **hermano** (a direct measured edge to a seed — §2.5 promotion) vs
  **primo Nº** (transitive-only); degree = hop-count of the **max-product** path
  (B1, stated explicitly).
- `blob_connector_flags` — 2-hop category-**entropy** (≥1.5) AND in-degree (≥3).
  Cosine coherence was measured to FAIL; entropy separates blob (2.0–2.9) from
  genuine event-hub (0.0–0.6). Flagged UP FRONT, before dedup (§2.4 order).
- `dedup_reached` — greedy same-event fold at **DEDUP_TAU 0.85**.
- `match_destination` — WORD-BOUNDARY term / category match (rejects the probe's
  "turm**oil**" substring FP, §2.7).
- `norm_rarity` / `actor_edge_weight` — the #234 LOCKED formula
  `0.30 + 0.68·norm_rarity` (trump df=29 → 0.300; rare df=2 → 0.628; gate ≈ df 3).
- `walk_constellation` orchestrator (build → flag → walk → dedup).

**Backend — `POST /api/v2/dossier/walk`** (contract `constellation-walk-v0`, 5
tests): resolves pins → fetches active-topic centroids → global whitening → walk →
payload of `kin` (id, label, category, degree, kinship, acc_weight, per-hop
`via` receipt, `is_blob`, folded fragments, typed `destination`). 120s cache
keyed on (sorted pins, rel_floor). Honest empty reasons
(`no_topic_centroids` / `no_db` / `no_measured_kin`). `rel_floor` is the
"¿hasta dónde caminar?" slider (0.10–0.90); HOP_CAP fixed.

**Backend — #234 fix (`dossier.py`):** softened the hard-exclude (604-608) to a
thin CONTINUOUS link + applied the locked formula (629-633). A ubiquitous-only
pair is now a thin weak link (not a false "isolated" verdict — the N=2 erdogan
artifact), while the DISTINCTIVE subset still drives the confirmed tier.

**Frontend — `lib/constellationWalk.ts` (+13 vitest):** types, `fetchWalk`, and
PURE honesty-grammar + **RADIAL** layout helpers (pin center, kin outward by
degree; solid=hermano / dashed=primo with widening gaps; thickness=acc_weight;
size+opacity recede with degree; degree labels; glass-box receipt line). A
left-to-right chain layout is FORBIDDEN + tested against. v1 UNDIRECTED — no
causal arrow.

**Frontend — surface:**
- `WalkConstellation.tsx` (+`.css`) — the radial walked view: seeds at center, kin
  outward, "¿ver primos Nº?" reveals ONE degree at a time, rel-floor slider, honest
  orphan state, hover receipt with the "association, not cause" note. Every walked
  node is **clickable (open) + pinnable (◆)** — pinning grows the investigation.
- `InvestigativeUniverse` (DossierConnections.tsx) — bridge/neighbor/pin stars are
  no longer inert: optional `onNodeClick` / `onNodePin` props wire open + ◆ capture
  (journey-map §1 flagship fix).
- `WorkbenchConstellation` mounts `WalkConstellation` + wires the universe nodes;
  `WorkbenchPanel` passes `onOpenThread` + `rerender`.

## Verification
- Backend: `test_constellation_walk.py` 21 · `test_dossier_walk.py` 5 · affected
  dossier/overmerge/whitening suites 136 — all green.
- Frontend: `npm run build` clean · full vitest **823 passed** (incl. 13 new).
- **Browser-verify PENDING** — the live walk needs the backend endpoint serving
  real centroids (no local DB here; no deploy without Pedro's ok). Pure render +
  layout + grammar are unit-tested; the honest-absence path degrades safely.

## §9 B-list tracking
- **B1** degree = max-product hop-count — DONE (documented + tested).
- **B2** DEDUP_TAU — LOCKED 0.85 (Phase-0b), used as-is.
- **B3** honest empty/orphan + negative acceptance — DONE (endpoint reason +
  `WalkConstellation` orphan + tests).
- **B4** frontier cache keyed on seed-set + floor — DONE (120s cache key); cap =
  MAX_PINS 64; **promotion-when-pinned** works by construction (pinning a primo
  adds it to the pin set → next walk seeds from it).
- **B5** cross-language hops — satisfied by design: the walk is semantic-only
  (whitened cosine, language-agnostic); no token-mention receipts on hops.
- **B6** true complexity O(N²) kNN build + O(reached) walk (cached); HOP_CAP +
  REL_FLOOR bound the frontier. Re-time + add an explicit frontier cap if the
  active-topic universe grows well beyond ~1.6k.
- **B7** receipt is the raw whitened cosine + the topic's own label — never an LLM
  label. No LLM anywhere on the walk.

## Deferred (spec §7 / §2.8 — NOT in v1)
- Time-axis / versioned-relationship edge-snapshot store (§2.8 (a)) — separate
  track.
- L4 markets as a bidirectional lens (§7) — separate chip (`task_23a4591b`).
- Temporal `▸` precedence glyph — dropped from v1 (§1.1); returns only as a gated
  measured basis (#219).
- Full DossierView **report** node click/pin + walk mount — `InvestigativeUniverse`
  already accepts the handlers; wiring the read-mostly report is a small follow-on
  (journey-map §3). v1 delivers the walk on the WORKBENCH build surface.

## Reversibility
`ATLAS_WALK_*` env knobs (rel_floor, hop_cap, k, blob_penalty/entropy/indeg,
dedup_tau). The #234 formula is the only edit to existing serving math; the walk
endpoint is additive; the frontend props are optional/back-compatible.
