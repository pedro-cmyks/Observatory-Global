# Dataviz Expert Audit — L1 → L3 (2026-07-11)

**Scope:** the visualizations themselves — encodings, scales, ramps, legends, chart
forms. Panel layout / grid / de-densify belongs to the parallel UI/UX track
(task_e03c57d5); overlaps are noted, not duplicated.

**Method:** live walkthrough of https://observatory-global.vercel.app at 1280–1440px
(Browser pane) + code verification of every encoding claim
(`frontend-v2/src/…`, file:line cited per finding). Judged against: Tufte data-ink,
Cleveland–McGill perceptual ranking (position > length > angle > color), color
honesty (sequential = one hue light→dark; never rainbow; status colors reserved),
DESIGN.md ("restrained color coding", "instruments", movement-first temporal
charts), and the app's own honesty principles (label approximations, never
fabricate).

**Audit-day conditions (matters for reproduction):**
- Backend was degraded during the audit: `GET /api/v2/signals` returned **500** on
  every request, and `GET /api/v2/universe` returned `{nodes:[], reason:"error"}`.
  A fix task was spawned (see chip "Fix prod 500 on /api/v2/signals").
  Consequence: SIGNAL STREAM and UNIVERSE/orbital could not be judged live —
  universe/orbital findings below are **code-verified only**.
- Global 24h substrate was thin: /brief lead story = honest empty state; watchlist
  behavior was audited via `/brief?country=US` (6 threads with sparklines).
- 2560px+ behavior untested (viewport tooling caps below that); no findings claimed
  there.

Severity scale: **MISLEADING** (encoding claims something the data doesn't say) >
**ILLEGIBLE** (true but unreadable at glance distance) > **WASTEFUL** (ink/space
with no information).

---

## L1 — /brief (BriefNewspaper)

| # | Sev | What the encoding claims vs. the truth | Fix |
|---|-----|----------------------------------------|-----|
| B1 | MISLEADING | Watchlist movement reads "34 **▼ −168 / 10h**": the row count (window/gated signals) and the delta (`changed_10h`, raw thread velocity over the whole feed) come from different lineages and denominators — a delta 5× the displayed count reads as broken math. [BriefNewspaper.tsx:172](frontend-v2/src/pages/BriefNewspaper.tsx:172) | Show relative movement ("−45% vs prior 10h") or label the lineage ("raw feed velocity"); never juxtapose two unlabeled counts of different bases. |
| B2 | MISLEADING | Sparklines are **per-row max-normalized** (`max = Math.max(...counts, 1)`) — a 3-signal/h ripple draws the same amplitude as a 300-signal/h spike; rows invite cross-comparison they cannot support. [BriefNewspaper.tsx:185](frontend-v2/src/pages/BriefNewspaper.tsx:185) | Shared y-max across the visible list (one scale per surface), or annotate each spark with its peak ("peak 41/h"). Zero baseline is already correct — keep it. |
| B3 | MISLEADING | "Most Negative −0.88 / Most Positive +0.52" carry no unit and no n: this surface uses the ÷10 scale (±1), ThemeDetail shows raw ±10 ("−2.54"), the dossier gets raw ±20 (comment at [DossierConnections.tsx:585](frontend-v2/src/components/DossierConnections.tsx:585)). Three sentiment scales, none labeled. | Pick ONE user-facing tone scale (raw GDELT ±10 is already explained in ThemeDetail tooltips) and convert everywhere; add the n behind each country tone or a thin-coverage floor. |
| B4 | ILLEGIBLE | Coverage-gaps rows render full-bleed and the right-hand text ("… none cleared the gate") clips at the viewport edge at 1440. | Contain rows to the page column; let the verdict text wrap. *(Layout-adjacent — coordinate with UI/UX track.)* |
| B5 | WASTEFUL→ILLEGIBLE | Heating Up chips ("Somalia **67** SURPRISE") give a magnitude with no scale anchor (out of 100? rank?) and no comparison affordance; four chips, numbers within ±2 of each other. | Tooltip with the composite formula + range ("heat 67/100 vs own baseline"), or drop the number and keep rank order + dominant-component tag. |
| B6 | ILLEGIBLE | Signal-density mini-map normalizes linearly by max (`c.signals / maxSignals`) over a heavy-tailed distribution — US saturates, ~90% of countries sit in the bottom 10% of the ramp and read as "no data". [BriefNewspaper.tsx:470](frontend-v2/src/pages/BriefNewspaper.tsx:470) | `sqrt` (or log) normalize the fill; the honest tooltip ("coverage volume reflects media attention, not geopolitical importance", [BriefNewspaper.tsx:843](frontend-v2/src/pages/BriefNewspaper.tsx:843)) already carries the semantics. |

**Good (keep, and copy the pattern):** honest empty lead ("No narrative thread
cleared the quality gate in this window"); factual standfirst fallback instead of
template essays; `NLP n% / GDELT` sentiment-provenance badges with low-coverage
downgrade ([BriefNewspaper.tsx:156](frontend-v2/src/pages/BriefNewspaper.tsx:156)) —
this is exactly what a provenance label should be.

---

## L2 — /app console

### Globe heat layer + map key

| # | Sev | What vs. truth | Fix |
|---|-----|----------------|-----|
| G1 | MISLEADING (perceptual) | The heat ramp is a **rainbow** (blue→cyan→green→yellow→orange→red, [countryHeatStates.ts:118](frontend-v2/src/lib/countryHeatStates.ts:118)). Luminance is non-monotonic: yellow at 0.64 `rgb(235,205,45)` is far *lighter* than max-heat red `rgb(242,45,30)` — a country at 0.64 heat **out-pops** a country at 1.0. Deutan/protan viewers additionally lose the green→orange distinction, i.e. the middle half of the scale. This also strains DESIGN.md's "restrained color coding". | Keep the weather-radar identity but make luminance climb monotonically: compress the cool end (transparent→deep blue→teal) and run the hot end dark-orange→bright red→near-white red at max (magma-like). Any candidate ramp goes through a CVD check before shipping, not after. |
| G2 | MISLEADING | Legend gradient used **full-opacity** RGB while the map fills with alpha 0→1.0: the "at baseline" end showed vivid blue in the key but is nearly invisible on the map. [Legend.tsx:152](frontend-v2/src/components/Legend.tsx:152) | **FIXED this session** — legend now uses the exact map stops *and alphas* (transparent left end). |
| G3 | ILLEGIBLE | Ramp has endpoint labels only ("at baseline" / "spiking vs own norm"); a 6-hue scale with no midpoint anchor can't be read back into values. | Add one mid anchor ("elevated") under the bar; the excellent composite explanation currently lives only in a hover tooltip — surface one line of it. |
| G4 | ILLEGIBLE | Conflict-event dot colors (Battle/Explosion, Riot/Protest, Other violence) are three near-identical warm hues at ~3px — indistinguishable on the map and barely in the key. | Separate by hue-family or by **shape** (dot/triangle/square) — at marker size, shape beats hue. Natural-hazard dots (amber/blue/purple/orange, [EqualEarthMap.tsx:486](frontend-v2/src/components/EqualEarthMap.tsx:486)) are fine except wildfire-vs-earthquake proximity; the key already confesses "Wildfire (Orange/Red)". |
| G5 | MISLEADING | SIGNAL STREAM renders **"No signals found" 
when the API 500s** — a service failure dressed as an honest empty. During the audit every tab (ALL included) showed it while `/api/v2/signals` errored. | Distinguish fetch-error from empty: "Signal feed unavailable — retrying" state. (Backend incident spawned separately.) |

**Good:** the persistent header line "Coverage bias: map heat is
baseline-normalized; raw volume is evidence density, not importance"; flows
labeled "Non-directional · shared attention, not causation"; scrubber labeled
"volume replay"; anomaly ring semantics documented in the key; source provenance
line ("GDELT 2.0 · RSS ×219 · NewsData · Social").

### Narrative Threads panel

| # | Sev | What vs. truth | Fix |
|---|-----|----------------|-----|
| T1 | MISLEADING | The **confidence bar + label is degenerate**: live list showed "90% confidence" on ~10 of 20 rows (default assignment confidence) and "100%" twice — including "Fiji Hotel Promotions · 90% confidence". A bar that always reads 90–100 discriminates nothing and *launders trust* onto junk rows. Also false precision: "59.15%". [NarrativeThreads.tsx:115](frontend-v2/src/components/NarrativeThreads.tsx:115), [:459](frontend-v2/src/components/NarrativeThreads.tsx:459) | Whole-percent **FIXED this session**. Real fix: render the bar only when confidence is *measured and informative* (e.g. < 0.9 or variance known); suppress the number on default-confidence rows ("unscored") — a missing bar is honest, a 90% default is not. |
| T2 | MISLEADING | Sparkline color encodes trend with **red = accelerating** ([NarrativeThreads.tsx:71](frontend-v2/src/components/NarrativeThreads.tsx:71)): an accelerating World Cup match glows the same alarm-red as accelerating armed conflict. Status colors are reserved for severity, not direction. | Neutral accent (blue/emerald) for acceleration; red only when `crisis_relevant && accelerating`. Trend words + arrows already carry direction. |
| T3 | MISLEADING | Same per-row max-normalization as B2 — 20 mini-charts, 20 private y-scales, zero cross-row comparability. | Same fix as B2 (shared scale or peak annotation). |
| T4 | MISLEADING | Count triad: the row says **92**, the opened detail says **544 signals**, its source list says **"Show all coverage (107)"** — three unlabeled counts for one thread visible simultaneously (the #214 semantics resurfacing at the panel seam). | Label the lineage at both ends: "92 verified · 544 raw" on the row, "544 raw · 107 sourced · 92 verified" in the detail header. Numbers may differ; unlabeled they read as bugs. |

### ThemeDetail

| # | Sev | What vs. truth | Fix |
|---|-----|----------------|-----|
| D1 | MISLEADING | "How it's covered" country cards give **n=1 countries the same card size and a confident tone number** ("+0.7 tone" from one signal) as Russia's n=31. The thin-coverage badge pattern (n<10) exists elsewhere in the app but not here. | Dim/downsize n<5 cards or stamp the existing `coverage-badge--thin`; tone from n<3 should render as "—". |
| D2 | MISLEADING | Header "544 signals · 12 countries" vs. country cards summing ≈110: the cards cover only geo-attributed signals, unlabeled. | One line: "110 of 544 signals are geo-attributed" — same honesty move as the gap box. |
| D3 | ILLEGIBLE | Activity Timeline legend reads "Positive / Neutral / Negative" like stacked counts, but each bar is volume-height colored by the **bucket's average sentiment class** ([ThemeDetail.tsx:1065](frontend-v2/src/components/ThemeDetail.tsx:1065)) — a bucket at −0.11 flips red while −0.09 shows yellow. | Caption "bar color = avg tone of that hour"; consider a continuous color (tone→diverging ramp) instead of 3-class thresholds to kill the boundary flicker. |
| D4 | MISLEADING | **Every source wears an "INDEPENDENT" badge.** Root cause is the backend default: any domain not in the exact-match map classifies as `independent` ([gdelt_taxonomy.py:1311](backend/app/core/gdelt_taxonomy.py:1311)); the frontend *also* defaulted unknown→Independent ([sourceFamily.ts:31](frontend-v2/src/lib/sourceFamily.ts:31)). A 100%-uniform badge is zero-information ink AND an unverified classification claim on every unclassified outlet. | Frontend fallback **FIXED this session** (unknown → muted "Unclassified"). Backend follow-up (not trivial: `_signal_class.py:37` and `source_tiers.py:125` consume the value): emit `unknown` for unmapped domains, badge only state/wire confidently. |

**Good:** tone tooltips state the scale and its realistic range ("−10 to +10 …
scores rarely exceed ±3"); UNVERIFIED / below-gate banners; two-tier
verified/extended banner; honest empty reasons.

### Universe / orbital (code-verified; live view blocked by backend error)

| # | Sev | What vs. truth | Fix |
|---|-----|----------------|-----|
| U1 | ILLEGIBLE | Non-highlighted edges draw at `strokeOpacity 0.02` ([UniverseView.tsx:631](frontend-v2/src/components/UniverseView.tsx:631)) — the field's headline honesty claim is "relations exact", but the relations are effectively invisible until hover. | Floor idle edge opacity ~0.08–0.12 with depth dimming; keep hover as the emphasis state, not the existence state. |
| U2 | ILLEGIBLE | One glyph carries ≥6 channels: size, fill (type), rim (tone), velocity halo, crisis ring, orphan dash, drift tail. Each is individually principled (tail floor = 4% of measured span, [orbitalLayout.ts:44](frontend-v2/src/lib/orbitalLayout.ts:44)) but jointly they exceed glance-decoding capacity. | Prioritize at rest (size + halo only), reveal rim/tail/rings on hover or per-lens toggle (CRISIS/ORPHANS chips already exist as lenses — bind channels to them). |
| U3 | WASTEFUL→MISLEADING | Orbital radius is min-max normalized **within a thread** ([orbitalLayout.ts:71](frontend-v2/src/lib/orbitalLayout.ts:71), lone body sits mid-orbit): radii across threads are incomparable, but nothing says so. | One caption line in the orbital header: "distances relative within this story". |

**Good:** persistent "positions approximate · relations exact" footer
([UniverseView.tsx:780](frontend-v2/src/components/UniverseView.tsx:780)) — the
honesty split as one line of UI is the app's best single label.

---

## L3 — Workbench / dossier

| # | Sev | What vs. truth | Fix |
|---|-----|----------------|-----|
| W1 | MISLEADING (worst finding of the audit) | **The report contradicts itself.** SYNTHESIS: "No confirmed link or shared actor/place is established." Two sections later, CONNECTION ANALYSIS: "✓ CONFIRMED — connected by shared actors … linked via *marea neagra, states states, tayyip erdogan*" — and the investigative-universe edge draws **solid** (= confirmed grammar). The confirmed-link test accepted junk entities ("states states"), and the LLM synthesis and the measured connection layer don't reconcile before print. | (a) Run shared-actor candidates through the person-hygiene gate (`_is_valid_person` / blocklist already exists) before an edge may be CONFIRMED; (b) one source of truth: the synthesis must consume the connection verdict (or vice versa) — a professional intel product cannot ship both sentences. |
| W2 | ILLEGIBLE | Touched-countries map claims "shaded by volume" but encodes volume as **alpha only, floored at 0.35** (`t = 0.35 + 0.6·(n/maxN)`, [DossierConnections.tsx:564](frontend-v2/src/components/DossierConnections.tsx:564)) — RU(33) vs MD(4) is a 0.95-vs-0.42 alpha difference that compresses on a dark surface. | Widen the range (floor 0.2) or step luminance instead of alpha; the count chips below (RU 33 · MD 4) are the saving grace — keep them. |
| W3 | MISLEADING | Sentiment-by-story diverging bars are scaled **relative to the most-charged pin** ([DossierConnections.tsx:587](frontend-v2/src/components/DossierConnections.tsx:587)) — correct midpoint grammar, but the scale is per-report and unlabeled: the same bar length means −2.5 in one dossier and −9 in another. | Caption "scaled to the most-charged pin (−2.54)" or fix the axis at ±10. Midpoint tick contrast should also rise — it's nearly invisible. |
| W4 | MISLEADING | Count reconciliation: the same investigation shows **544 signals** (pin card), **press 142** (distributions), **press 73 + 31** (who-says-what). Three totals, no lineage. | One reconciliation line in the report header ("544 raw · 142 typed members · 104 role-attributed"), mirroring the downranking-ledger discipline the research plan already has. |
| W5 | WASTEFUL | With 2 pins the "investigative universe" renders a dumbbell in ~300px of vertical space; its 5-line mono legend outweighs the graph. | Below 3 nodes, collapse to the sentence form ("2 pins · 1 confirmed link via X") and keep the graph for ≥3 nodes. Minor: CATEGORIES COVERED label collides with story names (CSS). |

**Good:** the dashed-similarity edge rule is exemplary and documented in code —
"a higher cosine must never read as a stronger link" ([DossierConnections.tsx:390](frontend-v2/src/components/DossierConnections.tsx:390));
GAPS & UNCERTAINTY closes every report ("frozen at pin time; live counts may have
drifted"); "measured at generation time · deepseek — grounded in pinned evidence"
provenance line; press-vs-public tooltip defines the roles.

---

## Top 10 fixes, priority order

1. **W1 — dossier self-contradiction + junk-entity CONFIRMED edges.** Entity-hygiene
   gate before edge confirmation; synthesis must consume the connection verdict.
   (Trust-destroying in the flagship deliverable.)
2. **T1 — degenerate confidence encoding.** Suppress bar+number on
   default-confidence rows; show only measured confidence. *(precision half
   applied this session)*
3. **T4/W4/D2 — count-lineage labels at every seam** (row 92 vs detail 544 vs
   sourced 107; dossier 544/142/104; detail 544 vs geo ~110). One labeling
   convention: `raw · sourced · verified`.
4. **G1 — heat ramp luminance monotonicity + CVD.** Keep radar identity, fix the
   yellow>red luminance inversion; validate for deutan/protan before deploy.
5. **D4 — source-family "INDEPENDENT" default (backend).** Unknown domains →
   `unknown`, badge only state/wire confidently. *(frontend fallback applied)*
6. **B3 — one sentiment scale, labeled, everywhere** (±1 vs ±10 vs ±20 today).
7. **B1 — movement label lineage** ("−168/10h raw velocity" next to a 34-count
   window number).
8. **B2/T3 — sparkline shared scale or peak annotation** (per-row max hides
   magnitude everywhere sparklines appear).
9. **G5 — error state ≠ empty state** in SIGNAL STREAM (500 must not render as
   "No signals found").
10. **D1 — thin-coverage treatment in country cards** (n=1 tone cards); reuse the
    existing thin/limited badge system.

Honorable mentions: G3 legend mid-anchor, U1 edge-opacity floor, W2 map alpha
range, W3 relative-scale caption, B6 sqrt density map, G4 conflict-marker shapes.

---

## Fixes applied this session (smallest, highest-value, trivially safe)

1. **Legend↔map ramp honesty (G2)** — [Legend.tsx:152](frontend-v2/src/components/Legend.tsx:152):
   the map-key gradient now uses the exact `heatFillColor` stops *including
   alpha*; "at baseline" reads transparent in the key exactly as it does on the
   map. Verified in the local preview: key left end fades to surface, matching
   the rendered globe.
2. **Unknown source family no longer claims "Independent" (D4, frontend half)** —
   [sourceFamily.ts](frontend-v2/src/lib/sourceFamily.ts): unknown/missing family
   → muted "Unclassified" badge (`--unknown` class added in ThemeDetail.css). The
   prior unit test froze the dishonest fallback and was updated to freeze the
   honest one. NOTE: live prod still shows all-INDEPENDENT because the *backend*
   sends `family: "independent"` for unmapped domains
   ([gdelt_taxonomy.py:1311](backend/app/core/gdelt_taxonomy.py:1311)) — that's
   fix #5 above and is not a trivial change (two consumers key on the value).
3. **Confidence false precision (T1, precision half)** —
   [NarrativeThreads.tsx](frontend-v2/src/components/NarrativeThreads.tsx):
   `59.15% confidence` → `59%`. A model-average does not support two decimals.
   Verified live in the local preview ("99% confidence" rendering).

Validation: `vitest` 203/203 passed, `npm run build` green. Before-state captured
from production; after-state verified in the local dev preview (port 3777) against
the live API.

## Overlaps with the parallel UI/UX track (not duplicated here)

- B4 full-bleed gaps rows, T-row chip density, W5 legend-vs-graph balance, and the
  CATEGORIES COVERED label collision are layout-adjacent; flagged, left to
  task_e03c57d5's panel-grid/de-densify scope.
