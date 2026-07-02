# Pedro's live review — full capture (2026-07-02 AM)

Method note (Pedro's explicit instruction): verify IN THE BROWSER — screenshots,
interaction — "no tomes el código como verdad; lo que VES, no lo que está en el
código." Console output ≠ browser truth.

## A. MAP (desktop, EE now default) — the hottest cluster
- **A1 🔴 Country click does NOT fly/zoom** to the country on desktop (regression
  vs the MapLibre behavior; EE flyCountry effect may not fire on click path).
- **A2 🔴 Re-scope mechanics lost**: on focus the map should CONCENTRATE on the
  country + show its FLOWS/connections to other countries; today it "only colors
  red", flow toggle on shows nothing.
- **A3** Conflicts layer: unclear if/how it relates to the focused country.
- **A4** Sudan: glowing circles + dots — WHAT are they, where do they stand
  geographically (real lat/lon per event vs country centroid)? Not legible, not
  referenced in CountryBrief.
- **A5** Venezuela painted BLUE (velocity-vs-own-norm) while a deadly earthquake
  is ongoing — color semantics unclear to the user in the moment.

## B. The Venezuela case (the wedge question, verbatim)
"Entré a Venezuela… un terremoto muy fuerte, muchas vidas… quisiera ver ESO y
poder entrar ahí. Quisiera que Atlas me dijera: otros países están hablando de
Venezuela, qué temas se relacionan."
- **B1 🔴 2,570 signals → 0 narrative threads** on the country view. R1 exists
  precisely for this (VE earthquake was an R1 showcase). Country-scoped thread
  serving broken/starved? VERIFY data + endpoint.
- **B2** Country entry should LEAD with the event (the earthquake), not stats.

## C. Public attention
- **C1** Country PA = search + wiki only — WHERE are the forums? Desired: a
  public-communication line PER COUNTRY (even foreign discussion about it).
  Data reality to verify: Reddit/Lemmy/Bluesky country coverage sparsity.
- **C2** Are forum posts embedded? (Answer: YES — F1 social signals embed +
  attach as discussion members via the M1 cron; the per-country JOIN surface is
  what's missing, not the pipeline.)
- **C3 🔴** PA detail: "Cookie (informatique)" — 4M wiki views, 0 media, 1
  country = FRENCH wiki infrastructure noise passing the (English-pattern)
  filter. #145's filter needs multilingual namespace/infrastructure patterns.
- **C4** PA detail page speaks a different visual language (colors) — fine that
  pages differ, but same design language (ties #247 C batches).
- **C5** "What they're saying" — structurally right, likely not fed correctly.

## D. CountryBrief — item-by-item review requested
- **D1** Trust indicators / **D2** Sentiment overview / **D3** Public attention
  / **D4** Narrative threads / **D5** Key subjects / **D6** Top publishers /
  **D7** Recent signals — full audit pass, browser-first.
- **D8** Top publishers shows publishers but "no recent coverage" — if the
  window has no coverage, should the count even show?
- **D9** AI summary review: "People most visible include Agnes" tells the user
  NOTHING. The insight generation needs an editorial pass (say what's HAPPENING,
  not who's most-mentioned).
- **D10** Scroll economy: Sudan's real answer (RSF crimes-against-humanity
  headlines) sits BELOW the fold; the top gives stats + empty PA. Reading order
  must front-load the story. "El scroll debería ser super-invitativo."
- **D11** Title aesthetics: short-code + long-name juxtaposition is ugly.

## E. ThemeDetail (thread view)
- **E1 🔴** "Analyzing coverage patterns" pill — numbers look FAKE (capped 15
  countries / 20 sources?). Verify what that pill computes.
- **E2 🔴** Evolution graph NEVER loads. Make it work.
- **E3** "How it's covered" click → open an inline mini-pill zoom on that
  country's coverage, not the big side panel jump.
- **E4** How-covered capped at 15 countries by volume — is volume the right cut?
- **E5** Related topics inside how-covered leak GDELT topics (same #249 class,
  different surface).
- **E6** Activity timeline / key subjects / top sources: audit. (Top-source
  click → its coverage = GOOD, keep.)

## F. Stream
- **F1** Stream appeared broken during review (verify — may have been the IO
  throttling window).
- **F2 🔴 UX ask**: hovering a stream item should LIFT it out of the carousel
  (separate layer, carousel keeps flowing beneath) — clicking mid-scroll is
  nearly impossible today.

## G. Entity/person pill
- **G1 🔴** "Nvidia Gpus" classified as PERSON (screenshot) — non-person subject
  typed person; #248's typing-noise class on the entity surface.
- **G2 🔴** Compare With → "Donald trump" → "No results" — compare search broken
  for the most-mentioned person in the corpus (screenshot).
- **G3** Pill loads slowly with no loading state (read as broken, then loaded).
- **G4** (Housing Cost Pressure/Russia screenshot): thread pill w/ 3 signals —
  related topics are GDELT chips; sources fine.

## H. Investigation-grade insight (L3 seed)
- **H1** Sudan self-coverage: "only Sudan talks about Sudan" — is that persistent
  or new? The voice-mix DATA exists (self_voice_ratio history); surfacing
  persistence-over-time = an L3 investigation feature. Pedro: L3 is its own
  world — separate track.

## Standing instructions extracted
- Browser-first verification for ALL of the above (screenshots + interaction).
- M1 compute is available for whatever needs it.
- Keep the existing queue (index rebuild tonight, #247 remainder, search P3/P4).

## I. TIME MODEL RETHINK (Pedro, follow-up — possibly the biggest idea here)
Verbatim intent: stop treating the time-range as a GLOBAL FILTER that CUTS data
("filtrar de entrada mocha muchas cosas") — serve ALL available information by
default, and make TIME legible INSIDE the information instead:
- Heat map: keeps its 24h semantics (it's a "now" instrument).
- Per-surface time ranges: the range selector becomes SPECIFIC to what you're
  viewing, not a global guillotine.
- Within surfaces: CHRONOLOGY must be discernible — when did each thing happen;
  today everything reads as one undifferentiated "now".
- The Venezuela failure is the motivating case: a critical event at hour 25
  stops being "critical" because the map/window shows 24h — criticality should
  DECAY, not cliff.
- Direct tie to thread construction: news develop continuously; threads should
  carry their own timeline as a first-class read, not be pre-filtered into a
  window.
This reframes #250's fixes (a) as the first step of a larger direction:
time-as-dimension-inside-the-data, not time-as-entry-filter.

## E2 (updated) — evolution graph: rethink the CONCEPT, not just fix the load
Pedro: loves the idea — "qué se relaciona con qué y CÓMO se ha estado
relacionando EN EL TIEMPO; cosas entran y salen, los contratos entre las partes
cambian a medida que avanza el tiempo." If the current graph never loads,
redesign it around that: a temporal relation view (entities/countries/threads
entering/leaving a story's orbit over time). Connects directly to §I (time as
a visible dimension) and to P7's evolution-graph-as-engine-truth framing.

## J. Entities beyond persons — question + label audit
Surfaces only ever say PERSONS ("mentioned persons", person pills). We type
subjects as person/org/place/event since the 06-24 SUBJECTS reframe — but do
ORG/entity types ever actually SURFACE anywhere? Audit: where do orgs show, and
if nowhere, either surface them (key subjects already carries types) or rename
labels honestly. "Mentioned persons" is important — but WHICH ENTITIES are
involved matters equally (companies, agencies, armed groups).

## K. Design license (standing)
Panels may be REDESIGNED — structure, not just skin — wherever it makes the
information read better. Redesign is always valid if legibility wins.

## Execution status (running log)
- **A1 fly**: VERIFIED WORKING in current bundle (browser: click Senegal → scale 2.5 + brief). Pedro's no-fly = pre-fix SW-stale bundle.
- **A2 flows**: ✅ FIXED `4fb25a11` — country focus returned 0 flows BY CONSTRUCTION (backend filtered signals to the focus country → no partner vectors). VE now: 34 arcs (PL/DE/ES/MX↔VE). Small countries can still be honest-zero (thresholds).
- **Desktop strip regression** (found executing): ✅ FIXED `b0680068` — aspect cut 1.4 (panels world-fit, phones strip).
- **B1/B2 (#250)**: ✅ FIXED `467f2022` — 72h decay floor; VE leads with the earthquake (92+22). Promotion sweep RETIRED (noise gate was right; see #250 close).
- NEXT: C3 wiki multilingual filter, G2 compare broken, D9 insight editorial pass, C1 forum line in CountryBrief, E1/E2, F2 stream hover, G1, J entities audit, D10 reading order, A3/A4/A5.
- **A2 round 2** (Pedro: "sigue sin funcionar en EE"): TWO more layers found+fixed
  `6685a006`+ this commit — (1) country threads query had DEAD JOINs → 12s cold
  → 500 → the panel silently kept the GLOBAL list under "Scoped to Venezuela"
  (now 1.4s + a 2.5s retry); (2) visibleFlows ignored the FOCUSED fetch (used
  the global top-100 → still zero arcs for small countries). Deep-link
  ?country= now also flies. Arc DRAW verified to the data layer; pixel-confirm
  needs a real browser (headless preview pauses the canvas rAF).

## Mercator ↔ Equal Earth PARITY AUDIT (Pedro's ask, code-level 2026-07-02)
| Capability | Mercator | EE | Status |
|---|---|---|---|
| Heat composite fill + focus re-scope | ✓ | ✓ | SHARED (countryHeatStates — one source) |
| Fly-to (click / deep-link / thread / person) | ✓ | ✓ | fixed this session |
| Flow arcs | ✓ | ✓ data-wise | focused-fetch now primary (03d43f8a); CO=35, VE=20+ pairs |
| Anomaly rings / conflict dots / chokepoints / planes / ships / terminator | ✓ | ✓ | canvas overlay |
| **Hover tooltip (country name/count)** | ✓ MapTooltip | ✗ | **GAP → implementing now** |
| **Marker CLICKS (ACLED event / chokepoint open)** | ✓ | ✗ | known spec gap — canvas non-interactive v1; NEXT after tooltip |
| Zoom-adaptive flow density | ✓ (viewState.zoom) | ~ (fixed 25) | minor — feed EE k into visibleFlows later |
| Basemap streets/city labels | ✓ | by-design ✗ | abstract country-level identity; EE has zoom-in country labels |
| Pitch/bearing/two-stage reset | ✓ | by-design ✗ | 2D projection |
| Default view | fills panel | **strip fills panel (Pedro 2026-07-02)** | world reachable by zoom-out (scaleExtent min=kFit) |
- **Parity closure round**: strip default everywhere ✅ (Pedro), hover tooltip ✅
  (browser-verified), marker CLICKS ✅ (capture-phase hit test → ConflictEvent/
  chokepoint panels; country-click fallthrough verified; dot-precision needs
  Pedro's real canvas). Remaining minor: zoom-adaptive flow density in EE.
  Pedro confirmed arcs + heat re-scope LIVE on Mercator screenshot 13:26.
