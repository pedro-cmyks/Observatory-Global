# Octopus Mascot — Implementation Spec

Design rationale + locked decisions: `docs/superpowers/specs/2026-06-26-octopus-mascot-design.md`.
This file is the implementation source of truth (contract + TODO) per
spec-driven-development. Frontend-only; no backend.

## Source of truth for the art

The creature is **generated**, not hand-drawn. Generator:
`docs/design/mascot/octopus_portrait.py` (Python; venv deps `shapely`, `numpy`).
Base = v16 (locked). Renderer for QA = `resvg` (installed); SVGO for production.

## Generator contract

`octopus_portrait.py` exposes a CLI / `render(mode, size, out)`:

| Param | Values | Meaning |
|---|---|---|
| `--mode` | `portrait` \| `companion` | portrait = centered full creature; companion = lighter body (lower opacity) + one long sweeping tentacle, transparent background (the app supplies the text it weaves through) |
| `--size` | int px (width) | viewBox stays 520×600 (portrait) / wider for companion; width attr scales |
| `--out` | path | output `.svg` |

- Colors are **duotone Atlas tokens** (no new hues). The static SVG carries the
  art; **state animation lives in React/CSS**, not in the SVG.
- `portrait` background is transparent (no navy rect) so the component controls
  the ground; the design preview keeps a navy rect only for QA.

## Asset outputs (generated → SVGO → committed)

| File | Mode |
|---|---|
| `frontend-v2/src/assets/mascot/octopus-portrait.svg` | portrait |
| `frontend-v2/src/assets/mascot/octopus-companion.svg` | companion |

## React component contract

`frontend-v2/src/components/Mascot/OctopusMascot.tsx`

```ts
type OctopusMode = 'portrait' | 'companion'
type OctopusState = 'idle' | 'loading'
interface OctopusMascotProps {
  mode?: OctopusMode      // default 'portrait'
  state?: OctopusState    // default 'idle'
  size?: number           // px width; default 96
  'aria-label'?: string   // if absent → aria-hidden="true" (decorative)
}
```

- Imports the generated SVG inline (so CSS can animate sub-parts) or as `<img>`
  for the simple case; animation via **vanilla CSS** (dashboard rule), keyed off
  `data-state`.
- Colors from **ThemeContext CSS variables**, not hardcoded.
- **`prefers-reduced-motion`**: no animation, static pose.
- MUST NOT import `InteractiveWorkspace` / force-graph.

### Motion (CSS)
- `idle`: mantle breathe, slow (≈3s), ±1.5% scale.
- `loading`: breathe + arms undulate + eye/sucker emerald glint sweep.
- `companion`: long tentacle sweep-in on mount.

## Token mapping (duotone → CSS vars)

| Art role | Hardcoded (v16) | CSS var (ThemeContext) |
|---|---|---|
| ground | `#070d17` | `--bg-primary` |
| body lit | `#1a8560` | `--brand-emerald-deep`-ish |
| body rim | `#061f15` | (derive) |
| contour ink | `#04160d` | (derive) |
| highlight | `#86f8c9` | `--brand-emerald-bright` |
| eye iris | `#a89a64` | `--brand-amber`-muted |

(Exact var names verified against ThemeContext during Task 3.)

## First concrete use

Brief L1 loading slot → replace the generic spinner with `<OctopusMascot
mode="portrait" state="loading" size={120} />`. Locate the Brief loading
component during Task 4 (Brief was rebuilt 2026-06-12; confirm current file).

## Implementation TODO

- [x] **T1 — Harden generator**: added `--mode/--size/--out/--preview` (argparse);
      portrait export is transparent-bg + role/title + no label; `--preview` adds
      navy ground + latin label for QA. v16 art unchanged at defaults (verts=369,
      bytes≈251k identical). Verified: transparent portrait renders correctly
      composited on navy; preview matches v16.
- [x] **T2 — Companion mode**: `--mode companion` ghosts the body (opacity 0.5) +
      adds one long filled sweeping tentacle (procedural curvature, suckered, NOT
      line-art), extended viewBox `-170 -150 720 770`, transparent bg. Verified
      via resvg.
- [x] **T3 — Export + SVGO**: both SVGs in `frontend-v2/src/assets/mascot/`
      (`octopus-portrait.svg`, `octopus-companion.svg`), SVGO multipass (-11%,
      ~220 KB each — heavy due to stipple/sucker density; acceptable for
      loader/hero, can thin later). Verified rendering intact post-SVGO (clipPath/
      gradient ids preserved). NOTE: ~220 KB is large — consider a low-detail
      variant for the 16–32 px panel/favicon sizes in T4.
- [ ] **T4 — React component**: `OctopusMascot.tsx` + `.css`, props above,
      ThemeContext vars, reduced-motion, a11y. Build green (`npm run build`).
- [ ] **T5 — Brief loader**: wire into the Brief loading slot as first use;
      verify in preview (loads, animates, reduced-motion fallback, no console
      errors, no bundle regression).
- [ ] **T6 — Docs + #106**: update `docs/design/mascot/` usage notes; comment
      on #106 with the reframed outcome.

## Acceptance

- Generator reproduces v16 at defaults; portrait + companion both export on-brand.
- Component renders both modes, honors reduced-motion, a11y labels correct.
- Brief loader replaces the spinner, verified in preview, build green.
