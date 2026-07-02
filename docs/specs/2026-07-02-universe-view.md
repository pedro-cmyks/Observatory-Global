# Universe View — the whole living story population as one navigable field

Status: MVP SHIPPED (2026-07-02, /goal session). Command-bar UNIVERSE button → full-screen overlay.
Origin: Pedro's vector-field framing (2026-07-02 voice note): "que sí exista todo el universo en un campo vectorial 3D, y cuando uno vaya a ver un tema específico, simplemente es una sección de ese campo… que en algún lugar sí se vea esa nube de puntos, de cosas que orbitan entre sí, se jalan los unos a los otros."
Companions: `2026-07-02-orbital-thread-view.md` (the "section of the field" — one thread's system) + L11 capture (galaxy metaphor) + §I time model.
Paper track: P7 (visualization method), P8 (open-set field), P3 (volume≠importance), P4 (lifecycle).

## 1. The claim

The universe EXISTS already — it is not a metaphor to build but a dataset to render: 476K signals live in e5's 768-dim space; 348 active story topics are dense regions with real centroids; categories are attractor neighborhoods. The Universe View renders that field directly. The orbital view (E2/L11) is a SECTION of this field around one attractor; the Universe View is the field itself. Zoom hierarchy shipped: **universe → click a body → its story system** (ThemeDetail orbital), one visual language.

## 2. Honesty architecture (the load-bearing decisions)

- **Positions are approximate BY DESIGN and labeled so.** PCA top-2 explains only ~17% of variance (measured 2026-07-02 on the live 348×768 matrix). So positions are a *map*, not the territory. The payload meta carries `position_basis`; the legend says "positions approximate · relations exact".
- **Relations are EXACT.** Edges = top-3 cosine neighbors per node computed in the FULL 768-dim space, never from the projection. Measured basis: e5 centroid NN sims run high (p10/p50/p90 = 0.893/0.943/0.986), so thresholding explodes (0.92 → 1,534 edges); top-k is the honest cut. 836 deduped edges.
- **Categories as constellations, data-driven.** Layout = global PCA blended 55% toward the topic's category-mean anchor — Pedro's "attractors" made literal, but from real geometry (category anchor = mean of member centroids projected), not hand placement.
- **Time is inside, not a filter (§I).** No window guillotine: all active topics serve with `first_seen`/`last_seen` + a 30-day daily activity timeline (19,386 member assignments bucketed). The scrubber makes stories BE BORN, burn, and decay (72h half-life opacity, floor 0.14 — never a cliff). Verified live: scrub to Jun 11 → 27 alive of 348; NOW → 348 alive, 212 born-this-week.
- **Volume ≠ importance** (P3 discipline): node radius is log-damped so a 3K-signal category-story cannot bury a 50-signal real story (frozen in `universeLayout.test.ts`).
- **No fabricated bodies:** umbrellas (ephemeral roll-ups, rebuilt nightly) are excluded; only story-level topics render. Crisis-relevant = red ring (R3.1 flag as a lens, not a filter).

## 3. Contract — `GET /api/v2/universe` (universe-v0)

- `nodes[348]`: id, label, category, crisis_relevant, n, x/y ∈ [0,1], first_seen, last_seen, timeline `[{day, n}]` (30d)
- `edges[836]`: a, b, sim (full-space cosine, top-3/node, deduped undirected)
- `anchors[48]`: category constellation positions + member counts
- `meta`: topic_count, edge_basis, position_basis, timeline_days — the honesty labels travel WITH the data
- In-process cache 10 min; ~158KB; 1.9s cold / instant warm. numpy SVD only (no sklearn — not in the API image).
- Backend `app/routers/universe.py`; pure projection+edge fns tested (`tests/test_universe.py`, 3: category-pull, full-space-not-projection edges, undirected dedupe).

## 4. Frontend

`UniverseView.tsx` + `universeLayout.ts` (pure, 5 vitest) mounted as a full-screen overlay from the command bar (UNIVERSE button, next to WORKBENCH). SVG; wheel-zoom around cursor + drag-pan; hover → neighbor subgraph highlights, rest dims to 0.12 (relation legible at a glance); hover card = category/label/volume/crisis/presence window/CTA; click → `handleThemeSelect(id)` closes the overlay and opens the thread's orbital system. Labels: top-14 visible by volume + hovered. Constellation labels for categories with ≥4 stories. Desktop surface.

## 5. Verified (browser, 2026-07-02)

348 bodies · 836 edges · 24 constellation labels; scrub Jun 11 → 27 alive/10 born-this-week, NOW → 348/212; hover "ARMED CONFLICT ESCALATION / Trump Cancels Iran Strikes / 386 signals · crisis-relevant / Jun 1 → Jun 19"; neighbor-dim 340 bodies; click → universe closes, STORY SYSTEM (orbital) opens. 150/150 vitest, build green, prod endpoint smoked.

## 6. What the field enables next (assessment 2026-07-02, not built)

Trajectories + "gravity" over this same data — all backtestable because snapshots persist:
- **capture rate** (new signals falling into a topic's basin per hour) as a LEADING heat indicator vs lagging volume;
- **centroid drift** = measured narrative mutation (the #224 black-hole, instrumented);
- **convergence** of two centroids = merge forecast (dynamic version of R2 umbrellas);
- **orbit decay** (members drifting out, cohesion falling) = retirement/split prediction;
- entity migration between attractors. #219 Kalman (approved) is the trajectory-tracking seed.
First step stays the read-only historical script over `emergent_clusters` snapshots (validate capture-rate lead on VE earthquake / Lebanon-Israel).

## 7. Known limits (v1)

Position projection lies locally (mitigated by exact edges + the labels); no drift trails yet (needs per-snapshot centroid JOIN — data exists in `emergent_clusters`); no umbrella hulls; desktop only; scrubber granularity = daily buckets; 3D nube-de-puntos deliberately NOT built (projection honesty + analyst task-time rule — a 3D fly-through is demo-ware until it beats a task).
