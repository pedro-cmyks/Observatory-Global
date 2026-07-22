# Constellation 3D — distance-preserving layout (MDS) — Design

**Date:** 2026-07-22
**Status:** Design (approved §1–§4; awaiting spec review before planning)
**Author:** Pedro + Claude

## Problem

Atlas has four "cloud of related things" surfaces and they have drifted into four
different visual languages with four different meanings:

| Surface | Today |
|---|---|
| **Orbital thread view** (`OrbitalThreadView`) | 2D elliptical orbits; radius = cosine distance to the story centroid |
| **Constellation thread view** (`ConstellationThreadView`) | 2D; shows *the same information* as the orbital |
| **Workbench / Dossier constellation** (`InvestigativeUniverse`, `WorkbenchConstellation`) | measured 6-basis edges between pinned topics; **positions arbitrary** |
| **Universe** (`UniverseView`) | 348 nodes, PCA top-3 + trackball, honest "positions approximate · relations exact" |

Two concrete problems:

1. **Orbits and Constellation are redundant** — the same story, the same members,
   the same measured distance, two renderers. (Pedro, live: *"la constelación y la
   órbita son la misma cosa, muestran exactamente lo mismo"*.)
2. **Positions carry no measured meaning** except the orbital's radius. In the
   Workbench the *edges* are measured but *where a node sits* is arbitrary — so the
   analyst cannot read "are my pins one story or three?" off the picture.

Meanwhile the universe proves the interaction that works: **rotate the cloud and the
structure reveals itself.** The per-story and per-investigation surfaces don't have it.

## Goal

One **distance-preserving 3D constellation**: the spatial distance between any two
nodes ≈ their **real measured distance**, rotatable with the universe's trackball.
Applied to the two surfaces where it is honest and useful (per-story, and the
Workbench/Dossier pin cloud), via **one shared module**.

## Decisions (settled in brainstorm)

1. **Deprecate Orbits.** The constellation — now 3D — is the single per-story view.
   `OrbitalThreadView` is retired, and the ◉Orbits/◉Constellation toggle goes away.
2. **The constellation stays its own view** (not folded into the universe): the
   universe answers "where does this story sit among all stories"; the constellation
   answers "what is this story made of". Different questions, different scales.
3. **Layout = 3D metric MDS**, not concentric shells and not raw PCA. Pedro's
   framing: *"una mezcla del PCA 3D donde la distancia es la distancia entre nodos"*.
   The distance you see between two nodes **is** their measured distance.
   - Rejected: **radius-shell** layout (radius = distance-to-core, angle arbitrary) —
     the arbitrary angle is exactly the dishonesty we're removing.
   - Rejected: **raw PCA** — preserves variance, not pairwise distance.
   - The story centroid enters as a node, so "distance to the core" is preserved for
     free as that node's distances, without forcing rings.
4. **Distance target = cosine** (not Manhattan/L1). Screen distance ≈ semantic distance.
5. **Share the mechanism, not blindly the metric** (see §2). Each surface feeds its
   own distance definition into one shared MDS.
6. **Universe and WalkConstellation are NOT changed** — for different reasons (§ Non-goals).

---

## §1 — Architecture + data flow

**MDS runs on the BACKEND.** Each endpoint gains 3D coordinates per node plus a
measured distortion (`stress`). The frontend only renders and rotates — no heavy JS,
no per-frame math beyond the rotation already proven in the universe.

**Why backend:** the pairwise distance matrix already lives there (embeddings /
edge weights), numpy is present, and the node counts are small (≈2–35), so the
solve is microseconds. Keeping it server-side also means the *measurement* is
computed once, in one place, testable — consistent with how rarity and movement are
handled ("define it once, read it everywhere").

**Flow:** open a story (or a Workbench investigation) → the existing endpoint returns
its usual payload **plus** `pos3` per node and an `mds` block → the shared 3D
renderer draws it and the trackball rotates it.

Payload additions are **additive**: existing 2D fields remain during the transition
so nothing regresses if the 3D path is disabled.

---

## §2 — Backend: one shared MDS, two consumers

### The shared module — `backend/app/services/mds.py` (pure)

```
mds_3d(dist_matrix: list[list[float]]) -> (coords: list[[x,y,z]], stress: float)
```

Classical (Torgerson) metric MDS, **numpy only, no scikit-learn**:
double-centre the squared-distance matrix, eigendecompose, take the top-3
eigenvectors scaled by √eigenvalue.

- **Stress** = Kruskal stress-1: `√( Σ(d₃ᴅ − d_target)² / Σ d_target² )` — the honest,
  measured distortion of squeezing high-dimensional distance into 3D.
- Cosine distance is not perfectly Euclidean, so **negative eigenvalues are clipped
  to 0**; the resulting error shows up in `stress` rather than being hidden.
- Deterministic (no random init) — the same input always yields the same picture.
- `n < 3` → degenerate; returns `None` and the caller falls back (see §4).

### Consumer A — per-story (`GET /api/v2/theme/{id}/orbital`)

Build the pairwise **cosine** distance matrix over the story's bodies **plus the story
centroid as node 0**, run `mds_3d`, and emit per body:

```json
"pos3": [x, y, z],
"mds": { "stress": 0.14, "basis": "cosine", "n": 27 }
```

Existing fields (`dist`, angle, tone, type, moons, timeline) are untouched.

### Consumer B — Workbench / Dossier (`POST /api/v2/dossier/connections`)

This endpoint already measures **6-basis edges** between pinned topics (semantic
centroid cosine, shared country, rarity-weighted shared person, headline
text-mention, article body-mention, …). MDS needs one scalar per pair, so:

```
d(i, j) = clamp(1 − combined_edge_weight(i, j), 0, 1)
```

A pair with **no measured relation** gets the maximum distance (1.0) — honest absence,
never a fabricated closeness. Emits the same `pos3` + `mds` block with
`"basis": "edge-weight-6basis"`.

**Critically: the per-edge basis chips and receipts are unchanged.** Position encodes
*how related overall*; the edge still carries *why* (shared person X, shared country Y).
That split is the whole reason this is honest — collapsing six bases into one number
would otherwise destroy the glass box.

---

## §3 — Frontend: 3D renderer + shared trackball

### New shared pieces

- **`lib/mds3d.ts`** (pure): projects `pos3` → screen using the universe's existing
  rotation math (`Rot3` / `applyRot` / `mul3` / `rotX|Y|Z` from `universeLayout.ts`,
  reused verbatim — already pure and unit-tested), plus a perspective divide and
  depth cues (near = larger/brighter, far = smaller/dimmer).
- **`hooks/useTrackball.ts`**: extract the universe's gesture layer — drag to rotate,
  alt-drag / two-finger twist to roll, wheel/pinch to zoom, pan, reset, and
  pause-ambient-spin-while-interacting. It is currently inline in `UniverseView`;
  extracting it makes it reusable **and de-duplicates** the one working implementation.

### Consumers

- **`ConstellationThreadView`** → renders the 3D MDS cloud. Keeps everything that
  already earns its place: co-occurrence edges, tone rim, entity types, moons, the
  time scrubber, hover receipts. **Removes** the Orbits toggle; `OrbitalThreadView`
  is retired.
- **`WorkbenchConstellation`** and the Dossier's **`InvestigativeUniverse`** → the
  same renderer fed by the dossier `pos3`. The compact Workbench variant keeps its
  letterbox and its "re-measure only when the pin set changes" behaviour.

### Honesty labels (driven by the payload, per surface)

| Surface | Label |
|---|---|
| Story | `distance ≈ semantic similarity · 3D distortion N%` |
| Workbench | `distance ≈ measured relation (6 bases) · the why is on each edge · distortion N%` |

When `stress > 0.20` the label says so plainly (*"high distortion — rotate to see the
real geometry"*) rather than presenting a warped picture as exact. Small pin sets
(2–10 nodes) will typically land near-zero stress, which is precisely where the
geometry is most trustworthy — and the label should be allowed to say that too.

---

## §4 — Honesty, edge cases, testing

### Honesty rails

- **Positions become a measured claim.** Today the universe says "positions
  approximate · relations exact"; here positions ARE the relation, so the honest
  companion is the stress number — always shown, never rounded away.
- **No fabricated proximity.** Unmeasured pairs sit at maximum distance.
- **The why stays on the edge** (Workbench), never inferred from position alone.
- **Absence stays absence** — no embeddings / no edges → the existing honest-empty
  states, not a decorative cloud.

### Edge cases

| Case | Behaviour |
|---|---|
| `n < 3` nodes | MDS degenerate → fall back to the current 2D layout with an honest note (2 pins = a line, trivially exact) |
| Cosine non-Euclidean | negative eigenvalues clipped; error surfaces in `stress` |
| Missing vectors for a body | that node is dropped from the matrix and rendered as an honest "unplaced" chip, never at a made-up coordinate |
| Endpoint fails | existing honest-empty / degraded states (unchanged) |

### Testing

- **Backend pytest** (`mds_3d`): known geometry (regular tetrahedron → stress ≈ 0),
  degenerate `n<3`, negative-eigenvalue clipping, determinism (same input → same output).
- **Frontend vitest**: the pure projection in `mds3d.ts`; the extracted trackball math
  (partly covered already by `universeLayout` tests — extend, don't duplicate).
- **Browser verify**: rotation, depth cues and labels on **both** surfaces; confirm the
  story path and the Workbench path each render and rotate with real data.

---

## Non-goals (deliberate)

- **The universe (348 nodes) stays PCA.** MDS at that scale is expensive and would
  carry high stress; its existing "positions approximate · relations exact" label is
  already the honest treatment. Not broken — not touched.
- **`WalkConstellation` (multi-hop chains) stays radial.** Its geometry encodes
  **hops** (hermano / primo), not distance, and its spec explicitly forbids layouts
  that imply causation. Applying MDS there would smuggle back the exact claim that
  design removed.
- No new data, no engine writes, no change to how any relation is *measured* — this
  is a layout/legibility change over relations Atlas already computes.

## Open items for the plan (not design blockers)

1. **Confirm the per-story bodies expose vectors** for pairwise cosine (the same
   vectors behind today's `dist` to centroid). If the orbital endpoint only carries
   the scalar `dist`, the plan must fetch the member embeddings.
1b. **Confirm the dossier exposes ONE combined edge weight** per pair. `d = 1 − weight`
   assumes a single scalar; if the 6 bases are carried as separate per-basis weights
   with no collapsed scalar, the plan must define the collapse explicitly (and that
   choice is itself a measurement decision worth stating in the payload's `basis`).
2. **Confirm the exact Orbits/Constellation toggle wiring** in `ThemeDetail` before
   removing it, so retiring `OrbitalThreadView` doesn't strand a code path.
3. **Pick the stress threshold** for the "high distortion" wording (0.20 is a
   starting proposal; check it against real stories and real pin sets).
4. Decide whether the time scrubber stays on the 3D story view or is re-thought once
   rotation exists (both are "explore the structure" gestures and may compete).
