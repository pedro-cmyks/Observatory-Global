# Atlas Mascot — Octopus / Kraken Design Spec

Date: 2026-06-26
Status: Character base LOCKED (v16); spec pending Pedro's review → then implementation plan
Issue: #106 (octopus mascot + brand identity) — this spec REFRAMES and unblocks it
Related: DESIGN.md (tokens), `docs/superpowers/specs/2026-06-24-level0-redesign-design.md`
(level-0 register gradient), #225 (surface hierarchy), the Brief L1 rebuild.

Asset source of truth (in repo): `docs/design/mascot/`
- `octopus_portrait.py` — parametric generator (Python; deps: `shapely`, `numpy`)
- `octopus-portrait-v16.svg` — rendered base asset (static SVG, ~251 KB)
- `octopus-portrait-v16.png` / `-head.png` — previews

## 1. Why this exists

#106 sat blocked for months on "needs a human designer's sketch-quality SVG; a
CSS-only approximation will look worse than the current spinner." That premise is
no longer true: the mascot can be **generated as a real, detailed vector
illustration** from code, rasterized and visually critiqued in a tight loop
(Python → SVG → resvg → look → fix). This session ran ~16 such iterations to a
character base Pedro accepts. The issue is therefore reframed from "waiting on
assets" to "design + generate + integrate."

The mascot also has to fit the **current** brand, not the 2024 one: the
2026-06-24 level-0 redesign retired the generic AI type stack and established a
**register gradient** (editorial Fraunces → console Geist/Mono) and an
emerald-on-navy "intelligence dark mode." The mascot is an identity piece inside
that system, not a decorative sticker.

## 2. The concept

An **octopus / kraken** is the literal form of what Atlas does: one creature with
many arms reaching across the world, holding a thousand threads at once
(countries, sources, languages, the people who speak and are spoken about),
*reading* where a narrative is travelling. The "mastermind in the deep" /
"here be monsters" on an old map. It is a single **ente** that lives across the
product and travels between surfaces.

Name (working): *Octopoda cartographica*.

## 3. The character (LOCKED — v16)

- **Treatment:** original **vector engraving**, filled body (NOT line-art — see
  §10), duotone Atlas palette. Reads as a vintage naturalist zoological plate, in
  the Atlas world.
- **Biological reference:** *Octopus vulgaris* (common octopus). Applied real
  anatomy: bulbous teardrop mantle; eyes set on raised shoulder bumps with a
  **horizontal slit pupil**, deep socket, hooded lid (ancestral, calm — never
  cute); **4 erectile papillae in a dorsal diamond** + supraocular papillae
  ("horns"); an **embossed papillae skin field** (small lit-top/shadow-below
  bumps = fake normals) rather than flat mottle; eight arms with **two rows of
  suckers** graded denser at the base and fading to the curling tips; a webbed
  crown so arms emerge from under the mantle with **no seam**.
- **Cohesion rule:** the silhouette is a **boolean union** (shapely) of head +
  web + arms → one continuous body and one outline. Shading is **contour-following
  hatching** (arcs wrapping the dome, cross-strokes ringing each arm tube), tone
  driven by a rim+light field — so it reads as ONE engraving, never as stacked
  shapes. This was the hard-won fix; preserve it.
- **Palette (duotone, from DESIGN.md `tokens.colors.brand`):** navy ground
  `#070d17`; body emerald ramp (`#1a8560` lit → `#0f4836` → `#061f15` rim);
  ink/contour `#04160d`; highlight `#62cca1`/`#86f8c9`; eye iris muted gold
  `#a89a64`; plate label cream `#e7ddbe`. No new hues; stays inside the brand.
- **Voice:** calm, ancient, intelligent. Honors DESIGN.md "geometric and
  confident, never playful." The original #106 costume idea (military hat /
  medical cross) is **dropped** — context is carried by surface, not by props.

## 4. Two modes of the same creature

1. **Portrait** — the centered engraving (v16). Use: loading animation, brand
   lockup, favicon/app icon, share-card, about/landing hero accent.
2. **Editorial companion** — the same creature rendered lighter/**ghosted and
   woven among editorial type**, with one long tentacle sweeping across the
   text (the "pull the thread" gesture). Use: Brief L1, landing sections, the
   L3 report/dossier. **Approved prototype = the FILLED creature ghosted among
   text** (the version Pedro called "bacano"). The later "Watcher in the Deep"
   line-art mock is REJECTED (see §10); companion mode reuses the v16 filled
   body at lower opacity, not line-art.

Both modes are produced from the **same generator** so the identity stays
consistent across sizes and surfaces.

## 5. Fit with the design system (DESIGN.md + level-0)

- Colors/typography come from DESIGN.md tokens; the plate label uses **Fraunces**
  (editorial register). The companion mode literally enacts the **register
  gradient**: it lives in the editorial (Fraunces, warm) layer, the same place
  the Brief masthead lives.
- The mascot is treated as a **design-system asset** (per the installed
  `design-system` skill checklist): tokenized colors, a defined set of
  states/sizes, accessibility, and documentation — see §8.

## 6. Placements (first use → later)

| Surface | Mode | Trigger | Size |
|---|---|---|---|
| Brief L1 initial load | Portrait, animated | full-brief load | ~120 px |
| /app panels (stream, anomaly, …) | Portrait, small | data loading | 28–32 px |
| Brief AI/analysis block | Companion or portrait | generation wait | ~96 px |
| Brief page body / landing sections | Companion (woven) | ambient | full-width band |
| L3 report / dossier | Companion (woven) | report generation/read | full-width |
| Favicon / app icon / share-card | Portrait, simplified | static | 16–512 px |

**First concrete deliverable** (from #106): the Brief loading animation
(`.brief-loading` slot in the Brief). Everything else follows.

## 7. Motion system (implies live processing, never decorative bounce)

- **Idle/breathe:** slow mantle scale ±1–2% (~3 s), the `pulse`/`radar` durations
  in DESIGN.md `motion`.
- **Reading (loading):** arms undulate (phase-offset sine on arm curl), suckers
  and the eye **glint emerald** in sequence — "scanning the threads."
- **Companion sweep:** the long tentacle draws/sweeps across the type on entry.
- **Reduced motion:** honor `prefers-reduced-motion` → static resolved pose, no
  animation (mandatory, per level-0 spec convention).
- Animation is layered on the generated SVG (CSS/SMIL/requestAnimationFrame at
  small scale). It must NOT import `InteractiveWorkspace`/force-graph
  (bundle rule, CLAUDE.md).

## 8. Production pipeline

1. **Generate:** `octopus_portrait.py` builds the static SVG (parametric:
   pose, size, treatment, state). Deps: a venv with `shapely` + `numpy`.
2. **Render/verify:** `resvg` (installed, 0.47) rasterizes to PNG for visual
   QA — the same loop used to design it. (qlmanage works as a fallback.)
3. **Optimize:** run the output through **SVGO** (the `svg-specialist` skill
   covers this) for a production-sized asset.
4. **Integrate:** ship as a React component (e.g. `OctopusLoader` /
   `MascotCompanion`) consuming props `mode`, `state`, `size`; colors from the
   ThemeContext CSS variables, not hardcoded. Vanilla CSS for animation
   (dashboard rule); Landing may use its own styling.

## 9. Design-system asset checklist (from the skill)

- [ ] Tokenized colors (map the duotone ramp to DESIGN.md tokens / CSS vars)
- [ ] Defined states: `idle`, `loading`; modes: `portrait`, `companion`
- [ ] Size set: 16 / 32 / 96 / 120 / 512 (+ favicon)
- [ ] Accessibility: `role="img"` + `<title>`/`<desc>`; decorative instances
      `aria-hidden`; respects reduced motion
- [ ] SVGO-optimized production asset; bundle-size budget noted
- [ ] Docs: this spec + usage notes in `docs/design/mascot/`

## 10. Rejected directions (do not revisit without reason)

- **Typed-node-tips / data-viz octopus** (tentacle tips = country/source/actor
  nodes): rejected — the mascot must not duplicate the hero or depict the data;
  it embodies connection by being a many-armed creature, nothing more.
- **Cute simplified mascot** (Claude-terminal-pet style): rejected as childish vs
  the brand's "never playful."
- **Ink line-art / pen-engraving with spiral tentacles** (v18/v5): tried after
  the Kraken book-cover refs; **rejected as a regression** — the filled
  biological engraving (v16) read better. Refs inform style direction but do not
  justify discarding a working result. (Lesson logged.)
- **Thematic costumes** (military/medical/pilot from original #106): dropped;
  context comes from the surface, not props.

## 11. Scope

**In scope (this track):** the character (done), this spec, the generator as
source of truth, and the implementation plan for mode/state/size assets +
the Brief loading animation as first use.

**Out of scope (here):** backend changes (none); the level-1/2/3 surface
rebuilds themselves; a painterly raster illustration (would need an external
image model — not pursued, vector is the chosen method).

**Acceptance:**
- Generator reproduces the v16 base deterministically.
- Portrait + companion modes render from one generator, on-brand palette.
- Brief loading animation replaces the generic spinner, respects reduced motion,
  no bundle regression, no console errors, verified in preview.

## 12. Open questions

- Companion-mode body opacity / how much it ghosts behind text (tune in preview).
- Exact first animation (breathe vs reading-glint) for the Brief loader.
- Favicon: simplified portrait — how much detail survives at 16 px (needs a
  reduced-detail generator pass).

## 13. Status / next

Character base LOCKED (v16). Pending Pedro's review of this spec → then
`writing-plans` for the implementation (generator hardening → mode/state/size
exports → SVGO → React component → Brief loader as first use, verified in
preview). Mascot can keep evolving, but the identity is settled.
