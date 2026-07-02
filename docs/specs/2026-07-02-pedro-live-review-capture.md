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
- **C3** ✅ (web-infrastructure wiki class multilingual + CountryBrief was the
  ONE unfiltered surface — fixed; 'Cookie (informatique)' dead; real cyber
  stories pass — tested). **G2** ✅ — finding: person search NEVER worked (the
  aggregate measures 14-25s → permanently degraded-empty on BOTH endpoints);
  fixed structurally with person_vocab (mig 063) rebuilt by the M1 cron +
  /api/v2/persons/suggest (ms); prod-verified. **G1** ✅ tech-token person
  filter. **F2** ✅ hover-lift (pause existed, affordance didn't).
  NEXT: D9 insight editorial pass, E1/E2, D10 reading order, J entities audit.

## L. PA round 2 (Pedro live, 15:47 screenshot)
- **L1 🔴 Mbappé hole**: PA item = 2.4M wiki views, "12 countries", **0 media
  signals** — mid-World-Cup, France's top scorer. Impossible → the PA→media
  match is losing everything. Prime suspect: accent/diacritic mismatch
  ("Mbappé" vs GDELT's "kylian mbappe") + possibly the sports-lane filter.
  Likely affects MOST PA items (his generalization). DIAGNOSE + FIX.
- **L2** Random PA items (".xyz", stray names) in the global dock — wiki/trend
  garbage class; filter.
- **L3 (RESOLVED — Pedro's correction 2026-07-02)**: a forum IS public
  attention — "a lo que están atentos es de lo que están discutiendo." Do NOT
  split the lanes: ONE Public Attention surface containing search + wiki +
  FORUM, with honest per-source badges ([S]/[W]/[F], verified=false on forum
  items) — the dock already models this. C1 therefore = add the FORUM column
  inside CountryBrief's PA section (endpoint exists).
- **L4** PA focus should re-center the map on where that attention concentrates
  (#234 family — PA lens).
- **L5** Anomaly-alert box reads cut off at the bottom — layout.
- **L6** Stream pacing: news must enter ONE BY ONE, continuously spaced — not a
  burst then dry-out. Drip cadence should adapt so the buffer lasts until the
  next poll ("que se vea que están entrando constantemente"). Categories can
  stay, but the feel = constant arrival. (Pause verified working — the stream
  had simply run out.)
- **L7** MAP KEY: "Sources: GDELT 2.0" is stale (GDELT+RSS+NewsData+social+
  USGS/GDACS today). "Conflict events · 500": riots/other-violence never seen —
  verify the class mapping is real; and WHERE do natural disasters (we ingest
  USGS/GDACS!) appear on the map? Candidate: disaster markers layer.
- **L8** Reset ↺ semantic upgrade: reset should re-center on the HOTTEST region
  (composite), not just the default strip — "que empiece siempre en lo más
  caliente". (The dead-button fix itself is deployed; his machine had the old
  bundle — the behavior he described, clearing toggles, was the pre-fix code.)
- **L9** Pitch/tilt: liked it, but self-resolved — NOT needed ("ocupa bien la
  pantalla"). No action.
- **L10 (validation)** The arcs DELIGHT: "el mundo no se conecta con África, es
  Europa↔US↔India↔China — qué bacanería, nada más viendo el mapa" — the
  product thesis working on sight.
- **L11 (E2 concept — Pedro's "locura")**: evolution graph as a SOLAR SYSTEM —
  the thread at center; entities/countries/subthreads = planets/comets that
  enter orbit, interact for a while, leave; threads themselves orbiting larger
  attractors (categories/events) = a GALAXY of information. Time = orbital
  motion. Feed into the E2/§I redesign (P7 evolution-graph-as-engine-truth).
- **L12** "Outlet" classification judged wrong somewhere he clicked ("outlet no
  tenemos — clasificar como eventos/conflictos/desastres") — locate the surface
  labeling things 'outlet' and re-type. NEEDS LOCATION (ask/inspect).

## Feeding matrix (Pedro's recurring question — answered honestly, 2026-07-02)
| Source | Feeds narrative threads? | How / Why not |
|---|---|---|
| **Forums** (Lemmy/Bluesky/Reddit) | ✅ YES | embedded + attached as DISCUSSION members (semantic ≥0.90); deliberately never SEED clusters (F2 guard) — they join stories, don't invent them |
| **Events/Disasters** (CAMEO, USGS/GDACS) | ✅ YES | bound as MOVEMENT members (R3.4b geo-temporal) |
| **Search** (Google Trends) | ❌ not yet | R3.5 unbuilt — held on the diffuse-centroid finding (binding needs DeepSeek/magnitude, not cosine) |
| **Wiki** pageviews | ❌ not yet | same R3.5 + #104 thin data |
| **Anomaly alerts** | N/A | they're an OUTPUT (volume vs baseline over signals), a lens — not an input |
R3.5 is the named gap: attention→topic binding + the uncoupled-attention
gap-box (#168/#172). Until then search/wiki enrich SURFACES only.

## L12 located: Signal Stream lane tabs (under LIVE)
ALL / CRITICAL / ELEVATED / NOTABLE / TREND / PERSON / MARITIME — mixes
PRIORITY tiers with TYPE lanes; Pedro doubts their usefulness and suggested
typing by CONTENT instead (events / conflicts / disasters). Rework candidate:
keep 2 priority chips + retype the rest by story class.

## L11 extended (Pedro, round 2) — orbital PHYSICS = relatedness
- Distance AND orbital velocity encode HOW related a body is to the thread:
  closer orbit = same category (they orbit together because they belong
  together); velocity = strength/recency of the interaction. Comets = entities
  that swing by briefly (a person who enters a story for two days).
- **L3 as UNIVERSE BUILDER**: the Workbench (level 3) builds YOUR universe —
  the investigation question at the center, pinned threads/entities/countries
  as bodies you capture into orbit; Atlas's galaxy is the shared sky, your
  investigation is your own solar system carved from it. ("¿Por qué no
  construye su propio universo alrededor de la investigación de uno?")
- Design session material: E2 redesign + L3 workspace = the same visual
  language (P7). Physics mapping draft: orbit radius = semantic distance to
  the center; angular velocity = interaction intensity; entry/exit = the §I
  time dimension; body size = volume; color = category.
- **E1** ✅ `720a05aa` — dynamic threads fed the AI insight the GDELT universe
  (data_points 0/0/0 → fabricated numbers). Dynamic branch: true latest-
  snapshot total + sample-based countries/sources. Prod: dt-981 = 78/2/18
  real. NOTE: insight TEXT currently `insight_no_credits` (Anthropic key dry)
  — candidate: swap the insight provider to DeepSeek (already integrated).
- **D9** ✅ story-first country insight (browser-verified VE). **Feeding
  matrix** written. **L11-extended + L3-universe-builder** captured (orbital
  physics = relatedness; the Workbench builds YOUR universe).

## L11 — Claude's honest assessment (Pedro asked)
STRONG: the metaphor is structurally honest — every visual DOF maps to a real
engine quantity (orbit radius=semantic distance, velocity=membership
intensity, entry/exit=assigned_at/first-last-seen, size=volume, color=R3.1
category). Buildable with EXISTING data. 'Comets' shows what no current
surface can (transient entities). L3-universe-builder gives the Workbench an
identity it lacks.
RISKS: (1) perpetual animation kills analyst reading — mitigate: static rings,
motion driven by a TIME SCRUBBER (interaction, not idle); (2) beauty>utility
trap — must beat the list on task time ('who entered this story this week?'),
measure it; (3) 3D is a trap — 2D radial, firm no.
VERDICT: prototype on ONE thread detail replacing the evolution graph,
evaluated on task time. Paper 7 contribution IF evaluated. Design session
before code.
- **D10** ✅ story-first CountryBrief order (Threads→PA→Subjects→meta→Publishers), browser-verified SD.
- **L2** ✅ domain-title noise class + trends lane filtered + global forum lane requires geolocation (XX excluded). Prod: Taiwan/Kyiv/Trump vs CSS-blog randoms.
- **L5** ✅ anomaly col scrolls instead of clipping second subsection.
- **L4** ✅ wiki/top serves top_country; PA wiki click flies map there.
- **L7 (disasters-on-map)** ✅ /api/v2/disasters (Green-wildfire spam excluded,
  measured 161/72h) → Mercator circles + EE triangles, per-type palette, click
  opens USGS/GDACS page, Legend "Natural Hazards · N". Prod API 68 events.
  Riots/other-violence dot classes verified present in conflict layer (legend).
- **J** ✅ AUDIT ANSWERED: orgs/places/events DO surface — Key Subjects with
  type badges in CountryBrief + EntityPanel + ThemeDetail (the #176 reframe).
  Gap found+fixed: SignalDetailPanel labeled raw GDELT persons "People" —
  now typed Key Subjects (shared gazetteer; non-persons visible, unclickable).
  DEEPER GAP (captured, not built): GDELT GKG ORGANIZATIONS field is NOT
  ingested — signal-level org data doesn't exist; NER orgs only. Ingesting it
  = the real "which companies/agencies/armed groups" answer. → issue-worthy.
- **E3** ✅ how-covered card → inline peek (4 country headlines, translatable)
  + explicit "Full coverage ↗" button. Browser-verified dt-981/LB.
- **E4 ANSWERED**: volume cut is right for coverage-share AND the subject
  country is always spliced to front when absent (originCountry logic,
  ThemeDetail:874) — no change needed.
- **D11** ✅ getCountryFlag was a stub returning the raw code ("SD Sudan") —
  real flag emoji + GDELT→ISO remap. Verified 🇸🇩.
- **J** ✅ (see above) + #251 filed for GKG ORGANIZATIONS ingestion.
- **L12 (outlet)**: exhaustive grep — NO surface renders "outlet" as a
  classification (only tooltip prose). Needs Pedro's screenshot to locate.
  Stream-tab retype (priority vs content mix) = design decision, captured.
- **A4 ANSWERED**: Sudan dots = conflict events at REAL per-event lat/lon
  (GDELT coords, not centroids); anomaly rings = country-level. Legend now
  documents both classes + Natural Hazards. Dock lists them country-scoped.
- **HNSW**: moved M1-launchd → pg_cron INSIDE Supabase (Pedro: nothing heavy
  depends on his machine). Job 'hnsw-rebuild-once' 08:15 UTC, self-unschedules
  FIRST (failure ≠ retry). Check cron.job_run_details tomorrow.
- **L12** ✅ LOCATED (Pedro: the stream tabs) + SHIPPED: CONFLICT + DISASTER
  content tabs added next to TREND/PERSON/MARITIME. Theme lists dodge the
  KILL⊂SKILLS and DISASTER⊂MAN_MADE substring traps (validated vs 300 prod
  signals). Honest cap: precision bounded by GDELT's loose tagging — same
  bound as the existing CRITICAL/ELEVATED tabs. "outlet" was a misread of
  these tab labels; no code change needed for that word.
- **INCIDENT (18:20 UTC)**: /signals flapping 500 — TWO country_hourly_v2
  refreshes at once (API's zombie refresh path, unbounded via pooler-dropped
  SET ‖ M1 cron). Killed orphan; refresh_aggregates retired to no-op; M1 cron
  got an atomic mkdir lock (macOS has NO flock — a flock guard would have
  silently skipped every run; caught pre-deploy). Signals 200/~1s after.
- **RESOURCE MAP (Pedro's economy question)**: M1 = all heavy ML (free);
  Supabase = storage+serving only (fixed tier; index builds are server-side
  BY NATURE — a Postgres index cannot be built by another machine; pg_cron
  costs the same as M1-triggered psql, just removes the Mac dependency);
  Fly = API+ingest+e5 query service (cents); Vercel = static (free).
- **D8** ✅ /signals?source= + on-demand publisher fetch (dostor.org/SD: 3
  Arabic headlines where "no recent coverage" contradicted the count; HTML
  entities decoded).
- **C5** ✅ VERIFIED working (Mamdani 12 real matches — trigram/unaccent fix
  carried this surface) + syndication dedupe added.
- **A5** ✅ EE hover tooltip carries the color's meaning ("· at its baseline"
  / "· strongly above its norm") — verified live on Venezuela itself.
- QUEUE DRAINED: remaining = design sessions (E2/L11 solar-system+universe,
  C4→#247 C1/C2) + programs (#249 GDELT eviction, #248 noise, search P3/P4).
