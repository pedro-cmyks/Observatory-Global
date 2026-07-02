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
