# L0→L3 Deep Review — data congruence · design · persona walkthroughs

Date: 2026-07-01 · Branch: `v3-intel-layer` · Status: DELIVERED (fixes shipped
same-session are marked ✅). Author: Claude (Fable 5), commissioned by Pedro:
*"revisar lo que ya tenemos, asegurarnos de que no estemos construyendo sobre
algo que está malo"* — judge the foundation, not just attack problems.

Method: 3 lenses run in parallel. (1) **Data congruence** — one agent traced
every surface's displayed numbers to endpoint → service → SQL → table, plus
pipeline-health SQL beneath. (2) **Design** — one agent audited all CSS against
the root `DESIGN.md` token system (computed WCAG ratios, not vibes). (3)
**Personas** — I drove the real UI in a browser as four users with live
investigative questions, documenting routes and dead ends. L4 (markets) is not
implemented — out of scope by definition.

---

## 0. Executive verdict

**The foundation is sound — you are NOT building on something broken.** The
product's spine (real threads → honest counts → evidence with receipts →
research plan with ledger) holds under adversarial use: every number I chased
traced to real Atlas-processed data, honesty labels (UNVERIFIED / below-gate /
DISCUSSION) are present where required, and the research workbench delivers
genuinely ranked, pin-able anchors (49 anchors with DIRECT/CONTEXT labels +
reconciling ledger for a live query). The problems found are (a) **seams
between levels** (L0→L2 handoff drops intent), (b) **one silently-broken data
path** (map heat fill — 422 on every request, FIXED ✅), (c) **systematic
design debt** (142 computed WCAG failures, 2 alien panel palettes, the Brief
never got its brand serif), and (d) **noise classes at the evidence edges**
(bylines/photo-credits as subjects — one class fixed ✅, movie-promo leaking
into a crisis mega-thread).

Fixed live during this review: heat-fill 422 (`c9eaffac`, deployed), photo-agency
person leak (`2264ecf`, deployed), mobile Brief 71px overflow (`f8b880a1`),
`brief_open`/value-moment telemetry for /brief (`4ba7b25`), embed-watchdog
false-healthy (`171459b`).

---

## 1. Persona walkthroughs (the product as four users)

### P1 — Marta, desk journalist. Q: "What's happening with the France heatwave? Who covers it?"
Route: Landing → "Moving right now" card *France Heatwave Deaths* → …
- 🔴 **The landing story card drops her intent.** Click lands on `/app` with NO
  theme param — console opens cold, France Heatwave NOT opened, and the
  first-session tour immediately covers the screen. The L0→L2 seam loses the
  one thing she came for. (Landing.tsx "Moving now" buttons navigate bare;
  contrast: the Brief's `openThread` builds `?theme=&country=` correctly.)
- 🟡 Tour stacks on top of an intent-carrying entry. Tour should be suppressed
  (or deferred) when the session starts with a story click / deep link.
- 🟢 Once she finds the thread in NarrativeThreads: **ThemeDetail delivers.**
  Honest header ("Global · 78 signals · Last 24h · hot window"), data-derived
  summary ("France reports ~1,000 excess deaths…"), evidence headlines with
  sources, typed KEY SUBJECTS, forum lane correctly badged DISCUSSION ·
  UNVERIFIED, countries DE/FR. This is the wedge working.
- 🟡 Key-subject noise: for this thread the top people were *tedros adhanom
  ghebreyesus* (plausible), *tosselilla sommarland* (a Swedish amusement park),
  *karel janicek* (AP byline). New noise class: **journalist bylines +
  entity-dense boilerplate rank as subjects** (photo-credit class fixed ✅
  `2264ecf`; "by<name>" concatenations like *bysarah falson* remain — risky to
  auto-filter: "Byron").
- Verdict: value reached in ~3 clicks *after* two seam frictions. **B**.

### P2 — Tom, OSINT researcher. Q: "Lebanon-Israel framework — evidence, who says what?"
Route: console search "Lebanon Israel agreement" → …
- 🔴 **Search never surfaces the LIVE thread** "Lebanon-Israel Framework
  Agreement" (top-10 global, n=78) — dropdown offers only Build-a-thread /
  Start-investigation / odd concept chips ("lebanonagreement"). The tour calls
  search "the fastest way into the console"; for living threads it is a dead
  end. (`/api/v2/search/unified` fired; thread results not rendered.)
- 🟢 **"Start investigation" fully redeems it**: research plan loads with 49
  anchors — the exact live threads as DIRECT anchors (Israel-Lebanon Framework
  0.83, Hezbollah Rejects Deal 0.79), investigative scores, PIN buttons,
  downranking ledger. The L3 contract (ranked anchors + honest gaps + no
  silent filtering) is real.
- ⚪ (Retracted:) I initially logged "no loading skeleton" — wrong;
  `ResearchPlanPanel:158` shows "BUILDING RESEARCH PLAN…"; my probe matched
  the sidebar node. The plan panel's loading state is fine.
- Verdict: **A− via workbench, D via search dropdown.** The gap between the two
  entries is the finding.

### P3 — Ana, policy analyst. Q: "Water crisis in Tehran" (the canonical forcing case)
API-level verification (browser path shares P2's plumbing): `POST
/api/v2/research/plan {"query":"crisis hídrica en Teherán"}` → plan with
**semantic lane LIVE** (2 semantic anchors + 3 semantic_evidence items,
cross-language ES→EN/FA) — the pure-semantic recall path that lexical search
can't do. Embed service confirmed alive end-to-end. Verdict: **A** for the
capability; discoverability of "Start investigation" from a cold start is the
constraint (it lives behind typing a query into search).

### P4 — Mobile reader on /brief (375×812)
- 🟢 Lead = the real top-ranked thread (Flood/landslide, 726 signals, 529
  sources, ▲+262/10h) with real evidence headlines + honest "COVERED FROM"
  chips. Watchlist + Heating Up render. The consumer front door shows Atlas
  data, not marketing.
- 🔴→✅ **71px horizontal overflow** at 375w — the lead's thread-label kicker
  never ellipsized (outside `.brief-thread-row`, the mobile rule missed it).
  FIXED `f8b880a1` (verified scrollWidth 446→375).
- 🟡 29 tap targets under 32px height (range chips, country chips) — #236
  territory.
- 🟡 **Evidence contamination in the mega-thread lead**: "Ek Hota Maalin movie
  Teaser released… Malin Landslide True Story" — a *film about a historical
  landslide* served as evidence of the current disaster. Class: lexical
  containment in broad atlas category-threads; the reject gate misses
  entertainment-about-crisis. Pairs with the "Hannah St Hotel Review"
  finding below.
- Verdict: **B+** (after the overflow fix).

### Cross-persona finding — ranking honesty
"Hannah St Hotel Review" (n=55, category *Health & Lifestyle*) ranks **#5 in
the global top threads** — the editorial-lane damp (lifestyle/sport demote)
did not fire for it. Either `classify_stream_lane` misses it or the damp isn't
applied on this path. A lifestyle hotel review sitting between Lebanon-Israel
and a disease outbreak is exactly the volume≠importance failure the ranking
was built to prevent. → filed as an issue.

---

## 2. Data congruence (agent audit — traced, not assumed)

> Verdicts per surface: see §2a below (agent report). Highlights integrated
> here; the full evidence tables live in the agent transcript summary.

**Verified SOUND (don't re-audit):** landing "Moving now" = real `/threads`
data; Brief lead = top-ranked thread via the same ranking as `/threads`
(briefLead.ts); ThemeDetail counts window-scoped and matching list counts (#214
semantics held on spot-checks); heat composite = `/heat/countries` atlas_heat
(volume only affects glow); semantic neighbors = real `signal_embeddings` ANN;
research ledger reconciles; honesty labels present in payloads (verified=false
on social/attention, UNVERIFIED trays, below_gate_evidence).

**Broken/degraded found:**
- 🔴→✅ **Map heat fill 422 on EVERY request** — frontend `limit=250` vs
  endpoint cap `le=200`. The composite-heat layer (the #231 volume≠importance
  fix) was silently dark in prod. FIXED + deployed (`c9eaffac`); endpoint now
  serves 250. *Lesson: a validation-cap mismatch is invisible without network
  inspection — the map degraded gracefully into wrongness.*
- 🟡 Photo-agency credits served as people (`/country/IT`) — FIXED ✅ deployed.
- 🟡 Byline-as-subject class remains (P1). 
- 🟡 Entertainment-about-crisis contamination in mega-threads (P4).

*(§2a — full agent report appended at the bottom of this doc.)*

---

## 3. Design review (computed audit vs DESIGN.md v1.0.0)

Pedro's instincts all confirmed with numbers:

1. **"Letras que se pierden" = 142 failing `color:` declarations.** Worst
   offenders: `#64748b` (101 uses, 4.09:1 — FAIL), `#475569` (2.57:1),
   `#4a5568`, `#666`, `#6b7280`, `#6b7585`, `#4a6a8a`. Aggravated by 9–11px
   sizes. Even the DESIGN.md token `text.muted` (opacity 0.42 → 3.52:1) fails;
   **0.55 is the AA floor** — one token bump fixes 43 declarations.
2. **Hero landing ≠ docs, explained**: Docs uses a different background hue
   (`#080c12` vs `#070d17`+glow), a **cyan** accent (`#38bdf8`) instead of the
   brand emerald, a Geist-Mono "ATLAS" wordmark instead of the Fraunces
   "Atlas", and a slate text family the console doesn't use. Small one-file
   re-skin unifies it.
3. **The Brief never received Fraunces.** The one surface DESIGN.md designates
   for the editorial serif uses **Georgia** in 20+ rules (incl. the masthead).
   The serif situation is *inverted*: marketing pages got the brand serif, the
   newspaper didn't. One-line-per-rule fix.
4. **Two panels belong to a different app**: EntityPanel + FocusSummaryPanel
   run an alien blue-slate palette (`#0a1628/#1e3a5f/#63b3ed`), 0 CSS
   variables — the Retro Radar theme literally cannot touch them.
5. **L2 heterogeneity quantified**: ≥8 section-label styles, 10 bespoke panel
   headers (while the shared `.panel-header` utility — the DESIGN.md spec — is
   used by exactly ONE component), ~25 badge/chip families, 6 empty-state
   patterns, 28 font sizes. The token PLUMBING is correct
   (`variables.css`/`themes.ts` match DESIGN.md byte-for-byte) — adoption is
   the gap.
6. **DESIGN.md contradicts itself** (tokens say Fraunces/Geist; its prose
   §Typography still says Outfit/Jakarta/Space Grotesk from the stitch file)
   and the stitch palette leaked into `tailwind.config.js` (Landing's
   text-secondary is 0.55 vs the console's 0.68).
7. **Unloaded fonts referenced**: `Inter` as the app-root default (index.css:4
   — renders system), bare `'JetBrains Mono'`, `'SF Mono'`, undefined
   `--font-serif`.

**Top design fixes by impact/effort** (agent's ranked list, condensed):
(1) bump `text.muted` 0.42→0.55 · (2) scripted replace of the 7 failing grays
→ `var(--color-text-muted)` (~140 fixes, one PR) · (3) Docs re-skin to Atlas
identity · (4) Brief gets Fraunces · (5) adopt `.panel-header`/`.section-label`
across the 10 panels · (6) one `.badge` base + role modifiers · (7) EntityPanel/
FocusSummaryPanel palette migration · (8) kill unloaded font refs · (9)
truncation-affordance pass (thread label needs `data-tip`; 2 native `title=`
stragglers in AnomalyPanel) · (10) unify type scale + de-leak tailwind config.

**Preserve (working well):** the token system itself; Landing (best-adhering
surface — Pedro likes it for a reason); #152 headline min-width fix intact;
`data-tip` discipline (79 uses, 2 stragglers); emerald restraint.

---

## 4. Prioritized action list

| # | What | Type | Size |
|---|------|------|------|
| 1 | ✅ heat-fill 422 (deployed) | data | done |
| 2 | Landing "Moving now" cards → deep-link `?theme=` (reuse Brief's `resolveThreadThemeTarget`) + suppress tour on intent-carrying entry | seam | S |
| 3 | Search dropdown: surface matching LIVE threads (the unified endpoint already fires) | seam | M |
| 4 | Ranking: editorial damp missed "Hannah St Hotel Review" — diagnose lane classification on category-typed topics | data | S |
| 5 | Design batch A: muted-token bump + 7-gray replace (fixes ~140 WCAG fails) | design | S |
| 6 | Design batch B: Docs re-skin + Brief Fraunces + unloaded-font cleanup | design | S-M |
| 7 | Design batch C: `.panel-header`/`.section-label`/`.badge` adoption (10 panels) | design | M |
| 8 | Byline-person + entertainment-about-crisis noise classes (needs design, not a token blocklist) — #248 | data | M |
| 9 | Mobile tap-target pass (29 <32px) — fold into #236 | polish | S |

---

## §2a — Data-congruence agent full report

*(appended verbatim below)*

---

### Verdicts per surface (agent, live-traced 2026-07-01 ~21:20 UTC)

| Surface | Verdict | Key finding |
|---|---|---|
| L0 Landing | MINOR-ISSUES | hero stats live from /health + /threads ✓; "126 countries / 31 languages / 0.71 entropy" hardcoded (still ~true: live 123/53/0.717) — will drift silently |
| L1 Brief | MINOR-ISSUES | lead/watchlist/heat all == /threads & /heat (same ranking fn) ✓; stats were starved by the dead matview (FIXED ✅) |
| L2 Console | MINOR-ISSUES | #214 counts EXACT (CO/IT spot-checks); heat=composite ✓; semantic neighbors real ✓; 3 defects found → all FIXED ✅ same-session |
| L3 Workbench | **SOUND** | scores present; ledger reconciles EXACTLY (83 = 9+2+72, every omission reasoned); semantic lane live; pin-log + telemetry writing |

### The 5 ranked problems (agent) — status after same-session fixes

1. 🔴→✅ **`country_hourly_v2` refresh dead since ~08:00 UTC, silently** — outgrew
   the DB statement_timeout (measured 2m35s vs ~120s default). Brief stats,
   `/stats`, geo detail, anomaly baselines served a 24h window missing 13h
   (58% of data), failure handler was a bare `print`. FIXED `abd61cd0`:
   session-level `statement_timeout=600s` + RESET (CONCURRENTLY can't run in
   a txn) + `logger.error`; manual backfill refresh verified raw==agg across
   the dead window; prod `/stats` 24h now 163,956 (was 71,108).
2. 🔴→✅ **`changed_10h` = lifetime MAX velocity** (`thread_intelligence.py`,
   both list + detail SQL): 69/101 multi-snapshot topics overstated movement,
   feeding trend arrows + 35% of `rank_threads` — the #224 stale-looks-alive
   pathology regrowing. FIXED `abd61cd0`: velocity at the LATEST snapshot
   (SUM for umbrellas).
3. 🟠→✅ **Relationship endpoint asserted "no discussion/mood" falsely** —
   discussion/mood pinned to `engine_version='v1-compat'` (structurally ~0)
   while unified-v2 held 74+74. FIXED `abd61cd0` (engine-agnostic, deduped
   by signal): dt-84 now serves discussion 10 / mood 10 (was 0/0) with a
   truthful rationale. The v1‖v2 UNION debt, paid at this consumer.
4. 🟡 **NER coverage collapsed to 2% of daily inflow** (166K/24h unprocessed,
   5.2-day lag) — the "verified subjects" tier is dark; gazetteer carries
   typing honestly. Cause stack: fleet 2-day death (watchdog now guards) +
   burst=1 memory guard + multilingual drain cost. → #243 (model-caching,
   burst=2) is the lever; labels stay honest meanwhile.
5. 🟡 **Editorial damp ignores the served category** — hotel review at #3-4
   global. → #246 (damp should consume R3.1 `category`/`crisis_relevant`).

### Remaining minor (tracked)
- Landing hardcoded diversity stats (swap to `/api/v2/voice-mix` fetch) — small.
- Forum lane provenance says `reddit`/`subreddit` for Lemmy items — label fix.
- Wiki pageviews missing days 06-26/06-29; trends currently FRESH (0.78h).
- 4 signals with future timestamps (publisher-date noise).
- **ReliefWeb near-silent: 2 ngo rows/7d** — #180 was closed as "live" this
  morning; REOPENED with this measurement (wired ≠ producing).
- Dynamic topics refresh nightly (snapshot 17.6h old at audit) vs atlas live
  counts — two freshness regimes interleaved in one ranked list (design note
  for the 3-speed cadence deferral, R3 §10).
- `is_umbrella` not serialized in /threads payload (umbrellas serve fine;
  frontend just can't distinguish them yet — matters for hierarchy rendering).

### Verified SOUND — do not re-audit (agent's list, condensed)
Brief lead = same ranking as /threads (identical order/ids live); #214 list==
detail counts exact; below-gate UNVERIFIED tray renders; heat = composite
(fresh matview, volume only in glow); window-scoped atlas counts; category
badge served+rendered; SignalDetail neighbors = real HNSW (sim .944/.928 with
honest gate labels); R2 umbrellas genuinely in the served top-list; research
ledger reconciles exactly with inspectable omissions; pin-events + telemetry
(incl. the new brief_open) writing; trends fresh; conflict markers honestly
labeled gdelt_events (never claim ACLED); forum lane verified=false.

---

## 5. Equal Earth map — dedicated design pass (Pedro's priority, added 2026-07-01 PM3)

**Assessment: the strongest piece of original design in the product** — and it
was shipping with two defects that hid that quality.

What's genuinely good (preserve): the infinite horizontal wrap (3-tile strip,
seamless ±180° rotation); the heat-CONDUCTION render (Gaussian-blurred heat
bleeding across borders — the weather-radar identity, Pedro's idea, no map
library does this); animated alert semantics (anomaly radar pings, pulsing
conflict dots); day/night terminator; zoom-gated country labels; GPU-composited
CSS transform (no per-frame SVG re-raster — the mobile "se tuesta" fix);
graticule + vignette (situation-room look); NO WebGL (the mobile blank-map
class deleted by construction); shared single projection instance (SVG, canvas,
hit-test can't drift); shared heat source with MapLibre.

Defects found + FIXED (`c72baae0`):
1. 🔴→✅ **The default view never showed the world.** `fitHeight` over-zoomed
   any panel narrower than the world strip (500×625 opened on "somewhere in
   Africa") and `scaleExtent` min=1 could never zoom OUT. Now: `kFit` world-fit
   default + dblclick reset, vertical letterbox centered, wrap re-engages on
   zoom-in. Browser-verified: world visible, click-at-fit opens CountryBrief +
   #234 re-scope repaints.
2. 🔴→✅ **Rainbow world after the heat-fill fix.** The `[0.1,1.0]` min-max
   (tuned for the warm top-80) stretched ALL ~200 countries across the full
   ramp once the 422 was fixed — everything colored, nothing hot. Now
   rank^1.6: bottom third ≈ transparent, middle cyan/green, top decile
   yellow→red (shared with MapLibre — both engines healed).
3. 🟡→✅ Canvas labels now Geist (was system sans).

Honest naming note: the engine is `geoCylindricalEqualArea().parallel(30)`
(Behrmann-family), NOT `geoEqualEarth` — a deliberate trade (the infinite wrap
needs a RECTANGULAR projection; true Equal Earth's curved outline can't tile).
Equal-AREA honesty is preserved — the ADR-0005 principle holds — but the
toggle label "EQ EARTH" is now approximate. Either rename the label (e.g.
"EQUAL AREA") or note it in Docs; do not silently claim Equal Earth.

**Route recommendation (#212 was closed as shipped; the road to DEFAULT):**
1. Pedro's visual sign-off on desktop + MOBILE (the spec's P6 gate — never
   done; mobile is the whole reason the SVG engine exists).
2. Promote Equal Earth to default (`atlas.mapProjection` default flip).
3. Parity follow-ups before retiring MapLibre: #234 fly-to-bounds on focus
   (EE re-scopes heat but doesn't pan/zoom to the focused country), marker
   interactivity (ACLED/chokepoint clicks are MapLibre-only).
4. Retire MapLibre + react-map-gl (bundle drop ~1MB+, kills the WebGL mobile
   bug permanently) — separate commit per the spec.
