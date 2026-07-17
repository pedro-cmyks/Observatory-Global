# Constellation Thread View — orbital → constellation re-code

**Date:** 2026-07-17
**Status:** SPEC (implementation behind a `◉ Constellation / ◉ Orbits` toggle;
orbital renderer is NOT deleted until Pedro's eyeball)
**Supersedes-in-part:** the solar-system framing of
`docs/specs/2026-07-02-orbital-thread-view.md` (the ENGINE MATH is unchanged and
reused verbatim; only the visual grammar changes).

## Why

Pedro retired the octopus/kraken mascot. **The constellation is now Atlas's
identity** — it is already the visual language the final dossier prints
(`InvestigativeUniverse` in `DossierConnections.tsx`, consumed compact by
`WorkbenchConstellation.tsx`), the loading identity (`LoadingMoment.tsx`,
procedural star-graph), and the discovery field (`UniverseView.tsx`, nodes +
edges + starfield). The one story surface still speaking "solar system" is the
**Orbital Thread View** (`OrbitalThreadView.tsx`, mounted inside the map panel's
UNIVERSE tab via `UniverseView.tsx:393`). Re-cast it as a **constellation** so a
thread's internal structure reads in the same grammar the report will print.

## Hard rule (from Pedro)

Do not lose any MEASURED quantity the orbit encodes today. Every encoding is
either **conserved** (same engine number, same visual channel) or **explicitly
re-coded** (same engine number, new visual channel — documented below). No
encoding is dropped, none is decorative-in-disguise.

The backend contract (`GET /api/v2/theme/{id}/orbital`, `orbital-thread-v0`) and
the pure math (`lib/orbitalLayout.ts`) are UNCHANGED and shared by both views.
`OrbitalBody` is the shared payload type.

## The mapping (documented before code — Pedro's process gate)

Constellation = a **star-graph**: one bright ANCHOR STAR (the thread) and member
STARS connected by EDGES, on a starfield. Placement stays **polar** (identical to
the orbit) so the semantic-distance ordering is preserved exactly; only the
grammar of what is drawn changes (edges + fixed shape instead of rings + sweep).

| # | Orbital encoding (measured source) | Fate | Constellation form |
|---|---|---|---|
| 1 | **radius** = semantic distance member↔centroid (embeddings `<=>`) | **CONSERVED + made comparable** | Star is placed at radial distance = the **ABSOLUTE cosine distance on a FIXED domain** (`radiusFraction`, `RADIUS_DOMAIN_MAX=0.20` ≈ the semantic-assignment boundary), not per-thread min-max. This **fixes the eval's U3**: the same distance maps to the same radius in every story, so a tight thread reads tight and a diffuse one reads diffuse — comparable across threads. An **EDGE** (spoke) is drawn anchor→star; the spoke **LENGTH** carries the distance. Its width/opacity are **UNIFORM** — a closer star is nearer the core, never a "stronger" link (dossier canon §5.3: *cosine never thickens*). |
| 2 | **angle** = `seedAngle(id)` + cumulative-interaction sweep (velocity IS intensity; the shape ROTATES as you scrub) | **SPLIT**: seed CONSERVED, sweep **RE-CODED** | Angle = `seedAngle(id)` ONLY → the constellation is a **fixed, stable shape** (a constellation does not spin — this is the identity point). The cumulative-interaction measurement the sweep carried is re-coded to **ignition glow**: `ignitionGlow = interactionsUpTo(scrubT) / total` scales a star's inner luminosity, so a star that is rapidly filling in at the scrubbed moment burns brighter. **This is the one channel change** (angular velocity → luminosity); the number is identical. |
| 3 | **presence alpha** = decay from last activity, floor `0.22`, hidden before `first_seen` (`presenceAlpha`) | **CONSERVED** | Star opacity = `presenceAlpha(body, scrubT)`. The scrubber lights stars ON/OFF exactly as `UniverseView`'s `universeAlpha` does — "tiempo → scrubber enciende/apaga estrellas" (Pedro). |
| 4 | **drift tail** = late-half − early-half mean centroid distance; outward=receding, inward=converging (`driftTailLength`) | **CONSERVED + bug-fixed** | A directional streak on the star along the semantic radial (same px from `driftTailLength(drift, distSpan)`), **outward = receding, inward = converging**. The eval found the ORBIT's render was inverted vs its own legend/hover (`OTV:328-331` drew receding inward while the legend said outward); the constellation render is **corrected** so render + legend + hover all agree. |
| 5 | **comet** = presence span < 25% of window (`isComet`, dashed ring) | **CONSERVED** | Brief-visitor star renders as a **shooting star**: dashed/streaked stroke + faint trailing tick. `isComet` unchanged. |
| 6 | **moon** = small entity ≥75% inside a parent's signals (`moon_of`/`moon_overlap`, fake sub-orbit) | **RE-CODED → UPGRADED to a real edge** | The moon is placed by its **OWN semantic distance** like any member (its distance is no longer discarded — the eval flagged the orbit's sub-orbit as fake geometry), and a **SOLID co-occurrence EDGE** is drawn to its parent whose **width ∝ the measured `moon_overlap`**. This is the one link whose weight is honest to thicken (a real shared-signal co-occurrence = the confirmed tier), per the eval §5 P0-3. |
| 7 | **rim** = mean tone, neutral band ±1.0 (`toneStroke`) | **CONSERVED → RELOCATED (P1-5, 2026-07-17)** | Originally the star halo = `toneStroke(body.tone)`. Superseded by eval P1-5: rim is now a neutral outline and tone moved to the coverage-weighted **"tone of coverage" Distributions strip** (still measured, one variable per channel — dossier canon). |
| 8 | **dot radius** = signal volume `n` (`bodyRadius`) | **CONSERVED** | Star core radius = `bodyRadius(n)`. |
| 9 | **center** = the thread (glow + core + label + category) | **CONSERVED** | The **anchor star** — brightest, central, the constellation's origin star; same glow/core/label/category. Every member edge originates here (moon edges at their parent). |
| 10 | **type color** person/org/place/event/country (`TYPE_COLORS`) | **CONSERVED** | Star fill gradient by type (same palette). |
| 11 | **scrubber**, **entrants counter** ("N entered this week"), **hover card**, **legend**, **zoom/pan**, **labels** (top-8 by volume + hover + zoom) | **CONSERVED** | Reuse the same controls/classes; hover card and legend updated to the constellation wording (edge = distance, ignition = activity). |

### Net visual result

A fixed constellation of typed stars around a bright thread-anchor star, wired by
proximity edges (bright = same story, faint = edge of the story), with satellite
moons branching off their parents, tone-colored halos, shooting-star comets,
drift streaks along the edges, and **time driven purely by the scrubber**
(stars ignite / dim / brighten as you scrub) — the exact grammar the dossier
`InvestigativeUniverse` and the `LoadingMoment` identity already print.

### The single explicit trade (call it out for the eyeball)

Orbital motion (the sweep) is gone. In the orbit, a high-velocity body visibly
raced around its ring; in the constellation the shape is still and that same
velocity is read as **ignition brightness** + the scrubber. This is deliberate:
a constellation that spins is not a constellation. If Pedro wants motion back, an
alternative (kept OUT of v1) is an angular drift of the seed with `scrubT` — noted
here, not built.

## Reconciliation with the tri-surface evaluation

The sister evaluation (`docs/research/dataviz/2026-07-17-tri-surface-evaluation.md`,
§5) independently judged this exact conversion and **recommends it as a net
honesty gain**, landing on **Option A — the EGO constellation (hub story-core
node + member stars + edges)**, which is what this view is. Its refinements are
adopted here:

- **U3 fix (adopted):** radius uses a **fixed absolute-cosine domain**, not
  per-thread min-max → cross-thread comparable (mapping row 1).
- **"Cosine never thickens" (adopted):** hub spokes carry distance as **length
  only**; width/opacity uniform (row 1).
- **Moons → real weighted co-occurrence edges (adopted):** row 6.
- **Drift-tail direction bug (adopted/fixed):** row 4.
- **`log2` size canon (noted, not adopted):** the eval wants volume→size unified
  on the universe/dossier `log2` formula; this view keeps `bodyRadius`
  (`sqrt`-based, shared with the orbit) so the toggle is an honest A/B of the
  **same** measured bodies. Unifying `bodyRadius` is a cross-surface change
  (touches the orbit too) — left for the P1 vocabulary pass the eval scopes.

**Surfaced conflict — RESOLVED 2026-07-17 (Pedro endorsed the doc):** the eval
§5.1 recommends moving **tone OFF the nodes** into a Distributions panel; Pedro's
first brief listed `rim = tono` to conserve. On 2026-07-17 Pedro said he agrees
with the doc → **implemented tone-off-nodes**: the star rim is now a neutral
outline, and tone renders as a coverage-weighted **Distributions strip** ("tone
of coverage") below the field. Tone is still MEASURED and shown (Pedro's original
"don't lose it" holds) — just relocated to one-variable-per-channel, matching the
dossier canon.

## Additional tri-surface-eval items implemented (2026-07-17)

Pedro consolidated ownership of the map/universe/orbital surfaces here and asked
to implement the rest of the eval. After the parallel **UX-council** batch (`6a410c21`,
already committed: map G1–G4, `/universe` retry+honest-fail, count/sentiment/jargon
honesty), the remaining **dataviz** items were implemented on current code:

| item | change | files |
|---|---|---|
| **P1-4** | signpost the fill encoding flip: universe legend now names **"fill = category"**; the story-view orbit-bar shows **"colors = subject type"** on travel | `UniverseView.tsx/.css` |
| **P1-5** | tone off the star rim → neutral rim + **"tone of coverage" Distributions strip** (coverage-weighted, ±1.0 bands) | `ConstellationThreadView.tsx/.css` |
| **P1-6** | constellation node size unified to the **`log2` canon** (`universeRadius`), not the orbit's `sqrt` | `ConstellationThreadView.tsx` |
| **P1-7** | constellation presence decay unified to the **field's 72h / 0.14 floor** (`presenceAlphaField`), not the orbit's 36h / 0.22 | `constellationLayout.ts` (+test) |
| **P1-8** | movement readout copy aligned to the **real mixed basis** (Kalman velocity first, `changed_10h` fallback) — no longer falsely claims "same as threads panel". Backend per-node `velocity_basis` tag = deploy-gated follow-up | `UniverseView.tsx`, `universeLayout.ts` |
| **P2-9** | map-key discloses the projection is **Behrmann equal-area** (areas true, shapes stretch), not the rounded Equal Earth | `Legend.tsx` |
| **P2-10** | heat legend discloses color = **rank vs other countries today** (busiest always brightest), not an absolute level | `Legend.tsx` |

Legacy `OrbitalThreadView` (the `Orbits` toggle state) is left on `sqrt`/36h/`toneStroke`
intentionally — it retires with the toggle; the go-forward constellation carries the
canon. **P2-11** (LoadingMoment separable) was already satisfied. Data evaluated:
pipeline healthy (170K signals/24h, 583K embeddings), substrate thin (32 active
topics = #229 engine ceiling, not dataviz); `/universe` intermittent error = DB
statement-timeout under load (phase0 already added retry + honest-fail).

**Deferred to the eval's cross-surface P1 (out of scope for this toggle):**
`fill` type-vs-category reconciliation, presence half-life 36h↔72h, one movement
encoding — all touch shared/other surfaces and are the vocabulary pass, not this
per-story recode.

## Implementation

Additive and reversible — the orbital renderer is untouched.

1. **`lib/constellationLayout.ts`** (pure, vitest — mirrors `orbitalLayout.test.ts`
   style). Reuses `orbitalLayout` math (`orbitRadius`, `seedAngle`,
   `presenceAlpha`, `isComet`, `interactionsUpTo`; the component also reuses
   `bodyRadius`, `toneStroke`, `driftTailLength`, `entrantsBetween`). Adds:
   - `RADIUS_DOMAIN_MAX = 0.20` + `radiusFraction(dist)` — clamp `dist/0.20` to
     `[0,1]`; the FIXED cosine domain that makes positions comparable across
     threads (U3 fix).
   - `ignitionGlow(body, t): number` — `interactionsUpTo(t)/timestamps.length`,
     clamped `[0,1]` (0 with no timestamps).
   - `placeConstellation(bodies, scrubT, geom, window)` — returns placed stars
     (`{body, x, y, alpha, ignition, comet, moon, distFraction, moonParentId}`).
     Angle = `seedAngle` only (fixed shape), radius = `orbitRadius(radiusFraction(dist))`
     (absolute domain). Every member — moons included — is placed by its own
     distance; `moonParentId` lets the component draw the co-occurrence edge.
2. **`components/ConstellationThreadView.tsx`** (+`.css`) — parallel to
   `OrbitalThreadView.tsx`, same props (`theme`, `themeLabel`, `hours`,
   `onCountrySelect`, `onPersonSelect`), same fetch, same empty/loading states,
   same scrubber / entrants / hover / legend / zoom-pan. Renders the star-graph.
   Reuses shared CSS classes where possible (scrubber, legend, hover, canvas,
   empty); constellation-specific classes (edges, anchor, ignition) are new.
3. **Toggle INSIDE `OrbitalThreadView.tsx`** (collision-safe — see below). The
   file's original render is renamed to an inner `OrbitalSolarView`; the exported
   `OrbitalThreadView` becomes a thin wrapper that holds a
   `storyViewMode: 'constellation' | 'orbits'` state (persisted `localStorage`
   `atlas.story-view.v1`, **default `constellation`** — the new identity; Orbits
   stays one click away for the eyeball), renders a segmented
   `◉ Constellation / ◉ Orbits` control, and mounts the chosen child (only the
   active child mounts → only it fetches). Same export name + props, so
   `UniverseView`'s mount (`<OrbitalThreadView .../>`) is **unchanged**. The
   legacy solar-system is fully preserved as the `Orbits` state.

### Collision safety (Pedro's "que no se cruce con otro trabajo")

The parallel Phase-0 session is actively editing `UniverseView.tsx`,
`UniverseView.css`, and `DossierConnections.tsx` (uncommitted in the main
worktree). This change therefore touches **only the two orbital files**
(`OrbitalThreadView.tsx` + `.css`) — verified untouched in every worktree and
branch — plus **new** files (`ConstellationThreadView.tsx`/`.css`,
`constellationLayout.ts`/`.test.ts`, this spec). It does **not** edit
`UniverseView`, `DossierConnections`, the globe, or the universe field: the
constellation grammar is reused by importing shared helpers (`orbitalLayout`),
never by editing the dossier/globe/universe source. Zero merge collision with the
parallel work.

## Acceptance / verification (dev only — NO prod deploy without Pedro asking)

- `npm run build` + `vitest` green (new `constellationLayout.test.ts`).
- Browser-verify BOTH story-view modes on BOTH thread kinds:
  - a **dynamic** topic (`dynamic-topic-N`) and an **atlas** thread (`slug--cc`),
  - scrubber live (stars ignite/dim/brighten; entrants counter moves),
  - hover cards, edges (proximity weighting visible), moons on parents, comets,
    drift streaks, tone halos, zoom/pan,
  - toggle flips Constellation↔Orbits with the open thread intact.
- No console errors; the coverage/honesty empty states still render honestly.
