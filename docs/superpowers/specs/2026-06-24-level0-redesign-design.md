# Atlas Level-0 Redesign — Narrative + Aesthetic

Date: 2026-06-24
Status: Approved (brainstorm), pending spec review
Surface scope: Level 0 only — the public Landing page and the Docs page (all
text/marketing/explanatory surfaces). Levels 1–3 (Brief, App console,
Workspace) are NOT touched.

## 1. Problem

The public-facing level-0 surfaces froze around an earlier version of Atlas and
read as generic "AI-made" product pages:

1. **Narrative is dated and abstract.** The Landing leads with "public narrative
   intelligence for seeing what the world is paying attention to" — abstract,
   fails a 5-second comprehension test, and doesn't reflect what Atlas became
   (research workflow, semantic layer, voice diversity, dynamic threads).
2. **The aesthetic reads as AI/vibe-coded.** The type stack is
   Outfit + Plus Jakarta Sans + Space Grotesk — the exact "blanding" trio
   algorithms default to. Uniform bento grids and smoothed geometry reinforce
   the "nobody chose this" signal that 2026 audiences actively penalize.
3. **No felt journey.** The page serves readers and analysts in one flat
   register; it never moves the visitor from public orientation into analyst
   depth.

A separate "truth pass" (already shipped on the content of both surfaces) fixed
factual staleness. This spec covers the **narrative + visual redesign**.

## 2. Goals / Non-goals

**Goals**
- A Landing that passes the 5-second test: a cold visitor understands what Atlas
  is and wants to go deeper.
- A distinctive, non-generic aesthetic with "visible fingerprints" — the
  opposite of the averaged AI look.
- A public → depth funnel made tangible through a register gradient.
- Reflect the real current product (movement, threads, research workflow, voice).

**Non-goals**
- No changes to Brief / App console / Workspace (levels 1–3).
- No backend changes. The hero consumes existing endpoints only.
- No Docs structural redesign (its content was already truth-passed; it only
  inherits the new type system for consistency).
- No new product capability — this is presentation.

## 3. Positioning (the thesis)

Atlas is **narrative intelligence, sharpened around movement**: see how a story
**spreads, mutates, and polarizes** across countries, sources, and languages.
Brief-first orientation lens. This stays in the existing "narrative
intelligence" family (chosen over "research tool" or "anti-monoculture" leads)
but sharpens it from passive observation to *movement*.

## 4. The spine: register gradient (public → depth funnel)

The page is a **descent**. As the visitor scrolls, the visual + typographic
**register shifts from editorial to console**:

- **Editorial register (top, public):** Fraunces serif, warm, newspaper rules,
  generous spacing, editorial voice. Reads like a brief.
- **Console register (bottom, analyst):** Geist + Geist Mono, technical
  uppercase labels, emerald HUD panels, denser layout, tabular figures. Reads
  like the instrument.
- A soft transitional beat — "from reading to investigating" — marks the pivot
  without a hard wall. The gradient is *felt*, not announced.

This register gradient is the organizing principle for every section below.

## 5. Hero — "the Atlas thumbnail"

A dynamic, live centerpiece that fuses three approved ideas: a traveling thread
(movement), an intelligence web (what Atlas is), over a faint world map
(geopolitics) — the "Indiana-Jones map" metaphor.

**Composition**
- Headline: **"Follow the thread."** (Fraunces). Eyebrow:
  `ATLAS · NARRATIVE INTELLIGENCE · LIVE` (Geist Mono).
- Standfirst: "Every live story is a web of countries, sources, and people.
  Watch a narrative move across the world — then pull the thread into an
  investigation."
- Visual: faint world graticule + place dots (map). A **comet** travels an
  Indiana-Jones dashed route between the countries/sources/actors a story
  touches. Touched points are typed, color-coded nodes (country=blue,
  source=amber, actor=violet, attention=teal, story/investigation=emerald per
  DESIGN.md `data.*`). The route resolves into a **constellation/web** centered
  on the live story node, which **pulses** in proportion to its spike.
- Below: a live ticker of current movers + CTAs (Read the brief / Open console /
  Read docs).

**Data + behavior**
- Source: existing `/api/v2/threads` (top movers, with `top_countries`,
  movement/velocity) and the briefing prefetch already on the page
  (`prefetchBriefing`). No new endpoint.
- The hero selects the top N moving threads and renders each as a route +
  constellation; it **cycles** through them on an interval and re-routes per
  story. Node pulse scales with the thread's velocity/trend.
- **Degradation:** if the feed is thin/unavailable, render a single calm
  story (or a static thread visual) — never an empty hero. All fetch failures
  are caught; the hero still renders structure.

**Implementation constraints**
- Built as a **bespoke lightweight SVG/CSS (or small canvas) component**. It
  MUST NOT import `InteractiveWorkspace` / react-force-graph (CLAUDE.md: that is
  lazy-loaded and would blow the main bundle). Animation via SVG SMIL / CSS /
  requestAnimationFrame at small scale.
- Respect `prefers-reduced-motion`: fall back to a static resolved
  constellation, no comet animation.
- Tailwind-only styling (Landing is the one Tailwind surface per CLAUDE.md).

## 6. Structure (smooth descent: A-base + B grafts)

Single continuous page; tone densifies down the descent.

1. **Editorial hero** (§5).
2. **Moving right now** — brief-style live preview: one lead narrative + a few
   movers, real `/threads` + briefing data. Editorial register.
3. **How narratives move** — spread / mutation / polarization explained with
   small instrument-style visuals. Register begins shifting to technical.
4. **Soft beat** — "from reading to investigating."
5. **Research Workflow — the climax** — question → ranked anchors → coverage
   gaps → Workbench, shown as a sequence with evidence-role chips
   (direct/context/weak). Full console register. This is the page's center of
   gravity.
6. **The surfaces** — Globe · Signal Stream · Narrative Threads · Anomaly Alert ·
   Workspace. The instruments behind the workflow. Varied card hierarchy (NOT a
   uniform bento — see §8).
7. **Data + voice** — source layers AND "global without the monoculture"
   (voice mix / self-coverage gets real estate, not a badge).
8. **Who it's for · Support · Footer** — journalists / researchers / readers ·
   Ko-fi · sources. (GitHub link already fixed in the truth pass.)

## 7. Type system (decision B)

Replaces the AI-trio. Encodes the register gradient in the typefaces themselves.

| Role | Family | Usage |
|------|--------|-------|
| Editorial display / headlines / leads | **Fraunces** (variable, opsz; SOFT 0 / WONK 1 for fingerprint) | Hero headline, editorial-register headings, brief leads |
| Console UI / body | **Geist** (variable) | Console-register body, panel copy, working text |
| Technical labels / counters / numbers | **Geist Mono** (variable) | Uppercase HUD labels, badges, timestamps, all tabular figures |

- **All numeric values use `font-variant-numeric: tabular-nums`** (counts,
  sentiment, countries, voice entropy, timelines).
- **Loading:** Fraunces via Google Fonts (`fonts.googleapis.com`). Geist +
  Geist Mono **self-hosted via `@fontsource-variable/geist` and
  `@fontsource-variable/geist-mono`** (npm deps) — imported once at app entry.
  Remove the old Outfit / Plus Jakarta Sans / Space Grotesk Google link.
- **`DESIGN.md` amendment:** update `tokens.typography.families` —
  `display: Fraunces`, `sans: Geist`, `technical`/`mono: Geist Mono`,
  `editorial: Fraunces` (the serif now carries the editorial voice; Georgia
  retired as the editorial face). DESIGN.md remains the source of truth and is
  edited in the same change.
- **Docs page:** swap its CSS font variables / `JetBrains Mono` references to
  the new system for consistency (Docs currently references `JetBrains Mono`
  which was never loaded → fixed as a side effect). No layout change.

## 8. Anti-AI craft rules (apply throughout)

- **Visible fingerprints over blanding:** expressive serif, real data, editorial
  rules, intentional asymmetry.
- **No uniform bento:** vary card sizes and hierarchy; a lead item dominates,
  others support. Avoid N identical evenly-spaced cards.
- **Real content, not lorem:** live threads, real country/source/voice numbers.
- **Tabular figures** everywhere numbers align.
- **Motion implies live processing** (radar/comet/pulse), never decorative
  bounce. Honor `prefers-reduced-motion`.
- **Keep the DESIGN.md palette:** dark navy + emerald, amber=caution,
  blue/cyan=geo/links, violet=people, red scarce. No cyberpunk/pastel drift.

## 9. File-level change map

- `frontend-v2/index.html` — replace the Outfit/Jakarta/Space-Grotesk Google
  link with the Fraunces link; keep Material Symbols.
- `frontend-v2/src/main.tsx` (or entry) — `import '@fontsource-variable/geist'`
  and `'@fontsource-variable/geist-mono'`.
- `frontend-v2/package.json` — add the two `@fontsource-variable/*` deps.
- Tailwind config / theme tokens — point `font-display`/`font-body`/`font-mono`
  (and the CSS custom props consumed via ThemeContext) at the new families.
- `frontend-v2/src/pages/Landing.tsx` + `Landing.css` — full restructure per §6,
  new hero component, register-gradient styling.
- New `frontend-v2/src/components/HeroThread.tsx` (+ styles) — the bespoke
  animated hero (no force-graph import).
- `frontend-v2/src/pages/Docs.css` — font-variable swap only.
- `DESIGN.md` — typography token amendment (§7).

## 10. Verification

- `npm run build` (Vite `tsc -b`, the strict gate per CLAUDE.md) must pass.
- Local preview verification (preview tools): Landing renders at `/`, hero
  animates and degrades correctly with the live feed, 0 console errors; check
  `prefers-reduced-motion` fallback; check Docs `/docs` still renders with new
  fonts; responsive at 1440 / 1280 / 375.
- Confirm fonts actually load (network) — Fraunces from Google, Geist self-host
  bundled — and that the AI-trio link is gone.
- Existing frontend test suite stays green.

## 11. Deploy plan

- Frontend-only → **Vercel**. Work proceeds on `feat/level0-redesign`; after
  local preview verification passes, merge to `v3-intel-layer` (the branch
  Vercel deploys from) and push → Vercel builds prod.
- **Fly is not part of this redesign** (no backend change). The pending #176
  typed-subjects backend (uncommitted `subjects.py` / `themes.py` /
  `nlp_pipeline.py`) is a separate concern and is NOT bundled into this deploy
  unless explicitly requested.
- Post-deploy: smoke the prod Landing + Docs (hero live, fonts loaded, no
  console errors).

## 12. Risks / open questions

- **Perf:** three font families (two variable, one self-hosted). Mitigate with
  variable fonts, `display=swap`, subsetting where possible. Watch bundle/LCP.
- **Hero animation cost:** keep node/edge counts small; SMIL/CSS over heavy JS;
  reduced-motion fallback mandatory.
- **Self-hosting Geist:** adds npm deps and a small bundle; accepted (decision
  B) for the distinctive instrument feel.
- **Open:** does Pedro also want the pending #176 Fly backend deployed in the
  same session? (Default: no — keep this deploy frontend-only.)
