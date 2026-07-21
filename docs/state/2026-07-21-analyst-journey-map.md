# Analyst Journey Map — the honest diagnosis (2026-07-21)

**Purpose.** Evidence input for Pedro's creative session on navigation / exploration /
the build-flow. This is a **diagnosis, not a redesign** — it walks the narrative
analyst end to end (L0 → L1 → L2 → Workbench → L3), shows exactly what state carries
and what drops at each hand-off, and names every place the app *could* lead to the
next discovery and does not. Synthesized from seven segment maps; every claim is
grounded in a file:line. The four keystone claims (thread-open frame-clear,
mutually-exclusive focus setters, missing `q`-param, inert constellation nodes) were
re-verified against source on 2026-07-21.

**The wedge.** The narrative analyst needs honest situational awareness on an
event/topic/country — the real story, who-says-what across countries/languages,
press vs public, **what is missing** — fast, with receipts. **The deeper goal Pedro
named:** the app should be an *exploration flywheel* — each finding opens the next; the
app itself leads the analyst from one discovery to the next and invites them to keep
**building** the investigation. That flywheel is what makes Atlas an *axis*, not just
a nice tool. Section 3 is the heart of this document.

**The one-line finding.** The plumbing is honest and mostly well-built — deep-links
carry, snapshots freeze, the store is unified. The failure is **momentum**: the app
captures findings but does not *compound* them. Opening a thread empties the frame you
built; the surfaces that draw "look here next" (bridge stars, leads, gaps) make the
click inert; and the report — where the sharpest next-investigation seeds live — is a
terminal file. The wheel turns one click at a time by hand instead of spinning
forward on its own.

---

## 1. THE JOURNEY, END TO END

### The carry/drop ledger (the spine)

| Hand-off | What carries | What drops | Evidence |
|---|---|---|---|
| **L0 → L1** | `prefetchBriefing(24)` warms the Brief cache → paints instantly | (bare console buttons carry nothing) | `Landing.tsx:245`; `Landing.tsx:328,452` |
| **L0 → L2** (mover card) | `?theme=<id>&entry=landing` — theme id + provenance | skips L1 entirely; only 3 movers, 1 hop each | `Landing.tsx:299,405` |
| **L1 → L2** (open thread) | theme slug + country code (2 URL strings) + `entry=brief` | thread **label**, why_now, receipts, coverage chips, sparkline, signal counts, **feed scroll position**; console re-fetches from scratch | `BriefNewspaper.tsx:593-606`; `App.tsx:716-754` |
| **L1 → L2** (category row) | — | **the entire category intent** — no `q` handler exists | `BriefNewspaper.tsx:1892`; `App.tsx:722-739` |
| **L1 → L3** (Save chip) | frozen evidence snapshot into an investigation | no navigation, no "saved" affordance — invisible artifact | `BriefNewspaper.tsx:547-582` |
| **L2 → Workbench** (pin) | active investigation id (localStorage, cross-session) → `WorkbenchPin` + async-enriched #227 snapshot | no toast on the pin path; destination investigation invisible | `WorkspaceContext.tsx:177`; `workbench.ts:208,290` |
| **L2 → Workbench** (receipt) | frozen provenance (url/origin/gate/date) into a **separate** citations array | never linked to the thread pin it came from | `PinReceiptButton.tsx:62`; `workbench.ts:133-139,343` |
| **Workbench → L3** (report) | pins → constellation/synthesis/leads/5W+H; citations → source-mix/contested | **AI-read claims + leads** (workbench local state only) | `DossierView.tsx:141-142`; `WorkbenchPanel.tsx:106-121` |
| **L3 → onward** | Copy MD / Download | everything — gaps, tensions, bridges all inert | `DossierView.tsx:452-463,968,987` |
| **L2 → L1** (return) | **only** `selectedCountryCode` | the open theme — you land back on the generic edition | `App.tsx:1287-1294` |

### The walk

**L0 — Landing.** A first-time analyst hits the marketing front door: hero, "What
Atlas is" pillars, a LIVE PROOF strip with three *"Moving right now"* thread cards
(`Landing.tsx:403-424`), Honest Limits, an Entry CTA. On mount, `prefetchBriefing(24)`
warms the Brief (`Landing.tsx:245`) so the next hop paints instantly. Three identical
"Read the Brief" buttons and two "Open the console" buttons fire bare
`navigate('/brief')` / `navigate('/app')` (`Landing.tsx:312,327,328,451,452`) — they
carry **zero** reading context. The one rich hop is a mover card:
`openThread → /app?theme=<id>&entry=landing` (`Landing.tsx:299`), which skips L1
entirely and drops the reader straight into a full console.

**L1 — Brief.** The daily edition — a genuinely phone-native reader. Lead story with
evidence receipts, three desks (World / Under the Radar / Culture-Sport-Life,
`SECTIONS` at `BriefNewspaper.tsx:290-294`), Heating strip, a Gap box ("what is
missing"), By-Category / By-Theme back-matter, Saved Watches. Every card carries an
"Open thread →" and a quiet `◇ Save` chip. Two carriers move the analyst onward:
`goToAtlas` (`BriefNewspaper.tsx:584-591`) sets `entry=brief` + params, and `openThread`
(`593-606`) builds `?theme=<slug>&country=<cc>`. **What crosses the boundary is only
the theme slug and the country code** — two strings. What the Brief already computed
and holds — the thread's real label, why_now, receipts, coverage chips, sparkline,
signal counts, and the reader's scroll position in the edition — all thrown away; the
console re-derives the theme blind. Category rows are worse: they fire
`goToAtlas('q=<category>')` (`BriefNewspaper.tsx:1892`) into a console that has **no
`q` handler** (`App.tsx:722-739`) — the click opens a bare global console and the
intent evaporates.

**L2 — Console.** Under the keep-alive shell both App and Brief mount once and toggle
via `display:none` (`main.tsx:32-54`), so the console re-hydrates instantly and never
loses in-memory state on a round trip. A URL-reactive effect (`App.tsx:716-754`),
double-fire-guarded by `deepLinkProcessedRef` and scoped to `/app`, reads
theme/country, opens the correct `ThemeDetail`, and flies the map to the country — a
clean, honest bridge. The console runs on one shared bus, `FocusContext.GlobalFilter`,
driving three always-on surfaces (globe / Universe / Narrative Threads), a
context-swapped stream slot, and a dock. **But the setters are mutually exclusive by
construction:** `setCountry`/`setTheme` null `thread/entity/person`, and
`setEntity`/`setPerson` null `country/theme` (`FocusContext.tsx:115-166`). You cannot
hold *country AND theme* at once. And the fracture at the center of the console:
**opening a thread empties the entire focus bus** — `clearFocus()` + `setTheme(null)`
+ null every selection (`App.tsx:2042-2050`). If you arrived exploring a person or a
country, that frame vanishes the instant you open a thread; each thread-open is an
island.

**Workbench — capture.** Two capture paths converge on one store
(`lib/workbench.ts`, localStorage `atlas.workbench.v1`). A **view/anchor pin**
(`WorkspaceContext.pinItem`, `:177`) auto-creates or reuses the active investigation,
freezes a minimal snapshot, then async-fetches `/theme|country|focus` to enrich it
with gate-verified evidence + the Label-Court verdict at pin time (the #227 promise).
A **receipt pin** (`PinReceiptButton`, `:62`) appends a `Citation` with frozen
provenance to a *separate* array — no re-fetch. The plumbing is solid; the problems
are feedback and destination: the anchor-pin path gives **no toast** and never says
*which* investigation received the pin, and pins land in whatever
`getActiveInvestigationId()` returns — a value persisted across sessions
(`workbench.ts:208`), so a returning analyst's captures silently attach to an old
investigation with no warning.

**L3 — Dossier.** `REPORT` re-reads the frozen store via `buildDossier()` and fires
several async passes in parallel — enrichment, connections → synthesis, publication
5W+H, optional corroboration/cross-read — assembling progressively. The frozen-snapshot
spine is genuinely honest: the report reads what the analyst *saw*, never live drift,
and every derived section is labeled frozen vs measured-at-generation. Then it ends in
`Copy MD / Download` (`DossierView.tsx:452-463`). The report surfaces exactly the
signals that should launch the next investigation — "What is missing" coverage gaps
(`:968`), "Gaps & uncertainty" (`:987`), the isolated-pin critique (`:725`), cross-read
tensions and contested-figure contradictions (`:749-836`) — and **not one of them is
clickable onward.** The deepest value moment in the app is a dead end.

**The return trip.** `openBrief` (`App.tsx:1287-1294`) carries **only**
`selectedCountryCode` back to `/brief` — never the open theme. An analyst who opened a
thread from the Brief, explored it, and hits "open Brief" loses the thread and lands
on the generic edition. State leaks on every loop, and the daily edition — the natural
spine of a day's exploration — is abandoned the moment they cross into the console.

---

## 2. THE FRICTION MAP

Ranked by momentum damage. **S = breaks the frame the analyst is building. A = drops
hard-won context at a hand-off. B = silent / uneven / dead-ends outward.**

### Segment: L2 exploration (the spine fractures live here)

- **[S] Thread-open wipes ALL global focus.** `onThreadSelect` calls `clearFocus()` +
  `setTheme(null)` and nulls every selection (`App.tsx:2042-2050`); the bus that drives
  map/universe/dock/anomaly is emptied. If you were exploring a country or person, that
  frame is gone; the list silently re-scopes to bespoke thread-*siblings*
  (`NarrativeThreads.tsx:285-320`) instead of your prior focus. **This is the single
  fracture that spins the flywheel down to one island after every discovery.**
- **[S] Focus setters are mutually exclusive — no compound frame.** Opening a thread
  from inside a CountryBrief calls `setTheme`, which nulls `filter.country`
  (`FocusContext.tsx:127-140`); the effect at `App.tsx:942` then *closes* the
  CountryBrief and re-globalizes the list. You cannot drill a country's thread and keep
  the country. The analyst must backtrack to re-enter.
- **[A] Two divergent thread-open paths.** The NarrativeThreads path clears focus
  (`App.tsx:2049`); the universe/country/theme path keeps a theme focus via `setTheme`
  (`handleThemeSelect`, `App.tsx:680`). Same user action, different surrounding-console
  state depending on where the click came from — unpredictable.
- **[B] Universe country-node click doesn't enter the country.** `onCountrySelect`
  only flies the map + opens a sliver panel; it never calls `setCountry`
  (`App.tsx:1800`), unlike the identical globe click (`App.tsx:1666`). Inconsistent,
  near-dead-end.
- **[B] ThemeDetail country card opens a sliver, not the country.**
  `onCountryCardClick` → narrow right panel, never full country focus
  (`App.tsx:1979`). To go theme → country brief the analyst must backtrack.
- **[B] Thread-row person chips are dead.** `top_entities` render as plain
  `<span className='person-pip'>` (`NarrativeThreads.tsx:551-553`) — not clickable —
  though persons ARE clickable in ThemeDetail (`:1297`) and EntityPanel (`:327`).
- **[B] Disaster marker exits the app.** A disaster marker click does
  `window.open(url,'_blank')` (`App.tsx:1650`) — a hard exit to an external source
  from one of the most exploration-inviting objects on the map.

### Segment: Entry & L1 → L2

- **[A] Asymmetric round-trip.** Brief→Console carries theme+country; Console→Brief
  carries only country (`App.tsx:1287-1294`). Explore a thread, return, lose it.
- **[A] Category click drops all intent.** `q=<category>` fired, no `q` handler
  (`BriefNewspaper.tsx:1892`; `App.tsx:722-739`) — the most investigation-worthy click
  (a coverage gap, a category) opens a bare global console.
- **[A] `openThread` passes no `labelHint`.** `handleThemeSelect(theme, country)` with
  no label (`App.tsx:729`) → the focus chip can fall back to the generic "Narrative
  Thread" skeleton for a story the Brief had fully labeled (`BriefNewspaper.tsx:601-605`).
- **[B] Bare "Open the console" buttons drop reading context.**
  `navigate('/app')` with zero state (`Landing.tsx:328,452`); Brief masthead carries
  only country, not the story on screen (`BriefNewspaper.tsx:1093`).
- **[B] `entrySource` goes stale under keep-alive.** Read once at App's first mount
  with empty deps (`App.tsx:358-361`); because App never remounts (`main.tsx:32-54`),
  an analyst who opens `/app` first (entry=null) then arrives from the Brief keeps the
  stale null — the "from the Brief" context never fires.
- **[B] Empty-lead fallback is a textual dead-end.** "Open the console to inspect raw
  coverage" as prose with no button (`BriefNewspaper.tsx:1434-1438`).

### Segment: Capture

- **[A] Two unreconciled capture models.** A thread pin (`inv.pins`) and its receipts
  (`inv.citations`) are separate arrays with no link (`workbench.ts:133-139`). Pinning a
  thread AND its receipts is two disconnected manual actions.
- **[B] Silent capture.** The `pinItem` path gives no toast — only an icon flip + a
  badge increment (`WorkspaceContext.tsx:177`); only *receipt* pins toast. Capture a
  whole thread, get almost no confirmation.
- **[B] Invisible / stale destination investigation.** Pins land in the cross-session
  active id (`workbench.ts:208`) with no L2 indicator — captures silently attach to a
  prior-session investigation.
- **[B] Panel-first pin creates a degenerate investigation.** With none active,
  `createInvestigation(item.title)` seeds the research plan from the thread *label*
  string, not a real query (`WorkspaceContext.tsx:171-174`; `workbench.ts:263`).
- **[B] Metadata-only pins freeze no evidence.** `fetchPanelSnapshot` returns null for
  signal/chokepoint/event/anomaly (`WorkspaceContext.tsx:77`) — the #227 "frozen
  evidence" promise silently doesn't hold; unflagged until the dossier gaps
  (`dossier.ts:57-62`).
- **[B] Receipt-pin coverage is uneven.** `PinReceiptButton` is on ThemeDetail /
  CountryBrief / SignalStream / ResearchPlanPanel / Brief only. EntityPanel /
  SourceProfile / PublicAttentionPanel show evidence rows with no `◆`
  (`EntityPanel.tsx:138`) — pin the entity but not the headline that made it worth
  pinning.

### Segment: Build → L3

- **[A] AI-read claims + leads are lost at report time.** `AI READ` populates
  readings/leads in WorkbenchPanel local state only (`WorkbenchPanel.tsx:106-121`);
  DossierView re-derives via its own passes. Work done while building is thrown away and
  re-paid.
- **[A] Inspecting a pin's source ejects you from the build overlay.** `handleOpenPin`
  routes through App handlers that call `setWorkbenchOpen(false)` (`App.tsx:640,652`) —
  every "let me check this source" is a full backtrack.
- **[B] Three overlapping verification passes, none sequenced.** AI READ (workbench),
  CORROBORATE (both headers), Cross-read (dossier) each pay a separate pass with
  overlapping purpose (`WorkbenchPanel.tsx:267-275`; `DossierView.tsx:497-508`); nothing
  chains them or says which to run before publishing.
- **[B] Readiness is invisible until you open the report.** The 5W+H have-vs-missing
  measurement lives inside DossierView (`:585`); `REPORT` is enabled at a single pin
  (`:267`) with no in-build guidance on whether it's publishable.
- **[B] Frozen evidence capped at 3 rows, silently.** `ev.slice(0,3)`
  (`ResearchPlanPanel.tsx:148`) — the report's Evidence section is thin by construction.
- **[B] Corroboration goes stale without warning.** Cached per investigation, re-runs
  only on explicit force (`DossierView.tsx:229-231,253-269`) — pin more after
  corroborating and the counts are silently stale.

---

## 3. THE FLYWHEEL GAPS — the heart

*Every place the app could lead to the next discovery and does not.* This is Pedro's
core question. Ordered by how much each blunts the "axis not tool" goal.

### 1. Bridge stars are inert — the app draws the arrow and disables the click. *(flagship)*

The dossier computes the single highest-value next-discovery signal: a **bridge** — an
unpinned story that sits near *more than one* of your pins, i.e. the story that
*connects your threads* (`nbGroups.bridges`, `DossierConnections.tsx:388-403`). It
renders them with special weight (`◎`, always-labelled). And they carry **no click, no
pin, no open, anywhere they appear.** `InvestigativeUniverse` takes no `onNodeClick`
prop (`DossierConnections.tsx:363`); the `<g>` for neighbor/bridge stars
(`:520-523`) and for the pins themselves (`:552-555`) have only `onMouseEnter` /
`onMouseLeave` and a `cursor:'pointer'` that *lies about being clickable*. Worse, in
the compact WorkbenchConstellation — the surface the analyst lives in while building —
even the textual "Nearby unpinned stories" fallback list is gated behind `!compact`
(`:594`), so the next-story candidates exist only as unlabeled dots on hover with no
target. **The app literally draws "look here next" between the analyst's pins and makes
it a static picture.**

### 2. Thread-open resets the frame instead of feeding the next suggestion.

Because opening a thread empties the focus bus (`App.tsx:2049`), the console cannot use
*"you just looked at X in country Y"* to shape the next hop. The only onward invitation
after a thread-open is the passive sibling dim/reorder
(`NarrativeThreads.tsx:285-320`) — and even that is siblings of the thread *alone*, not
of the investigation so far, so it cannot compound with the country/person frame the
analyst arrived with. Each discovery resets the wheel to a single island rather than
turning it forward.

### 3. The report is terminal — the sharpest next-investigation seeds are all inert.

DossierView surfaces precisely what should launch the next investigation and makes none
of it actionable: "What is missing" coverage gaps (`DossierView.tsx:968`), "Gaps &
uncertainty" (`:987`), the isolated-pin critique (`:725`), and cross-read tensions +
contested-figure contradictions (`:749-836`). A listed gap ("trade-export 72 raw
signals · none verified") cannot be opened as a new query or pin; a flagged death-toll
discrepancy cannot become a corroboration task. After `Copy MD` the loop dead-ends —
no "start a follow-up on the gap you found," no "these leads are still unpinned."
**Publishing is an exit, not a turn of the wheel.**

### 4. LEADS is the true engine, but it is gated and self-stalling.

`LEADS FROM THE TEXT` (`WorkbenchPanel.tsx:461-511`; backend `research_leads.py`) is the
*one* place the app produces a NEW measured, pinnable Atlas thread the analyst had not
seen — an actor named only in a fetched article body, resolved rarest-first with its
verbatim quote. This is the engine of the flywheel. But it is buried below citations,
appears only after a manual, paid `AI READ` press, is **disabled unless pins already
carry fetched evidence URLs** (so metadata-only pins → no AI READ → no leads,
`WorkbenchPanel.tsx:110-121,464`), and is **wiped on every investigation switch**
(`:109`). And the loop stalls one click short of turning on its own: pinning a lead
calls `addPin` only (`:486-495`) — it does **not** navigate to the new thread and does
**not** re-run `find_leads`, despite the tooltip promising "the galaxy grows a ring."

### 5. Discovery surfaces cannot capture what they surface.

The two surfaces that most invite *"what's that?"* — the globe and the Universe field —
have **no pin / `◆` affordance at all**. Capture lives only in NarrativeThreads rows,
EntityPanel, ThemeDetail, CountryBrief. A story spotted as a universe node or a globe
hotspot cannot be kept until the analyst first drills into its panel. Same for the
flagship "lead me onward" surfaces: DossierConnections, NarrativeBiography (the lineage
spine), DayEvidencePanel (real archive-day headlines + urls on the globe scrubber), and
WorkbenchConstellation — none import `useWorkspace` / `PinReceiptButton`. **The surfaces
built to lead cannot let you keep what they lead you to.**

### 6. Nearest-meaning and lineage leak *out* of Atlas.

SignalDetail's connected-threads keep you in-app (`onThemeClick`,
`SignalDetailPanel.tsx:236`), but the Semantic Neighbors right below them are plain
external `<a target='_blank'>` (`:322-343`) — the nearest-meaning signal, a prime
next-discovery, opens a news site instead of its own Atlas thread. NarrativeBiography's
week receipts are likewise external-only (`NarrativeBiography.tsx:239-242`) — the
lineage view knows a story has a past and a future but offers no step to the adjacent
Atlas thread. Every "nearest meaning" and "earlier chapter" pointer leaks the analyst
out of the flywheel.

### 7. Capture invites no next step, and the connection is hidden at the exact moment it matters.

`pinItem` / `addCitation` just flip an icon (`WorkspaceContext.tsx:177`). There is no
"you have 3 pins — here's how they connect / open the workbench" nudge; the only forward
signal is the passive WORKBENCH badge count (`App.tsx:1437`). The constellation that
*would* show how a new pin connects to the existing ones is only visible after manually
opening the Workbench overlay — so the moment of capture, the natural moment to reveal
connection, shows nothing.

### 8. `useFocusRelation` — the cross-panel connective tissue — reaches one panel.

The shared "what does this focus relate to" context, built explicitly (#234, Paper 7)
to carry a finding's relations into every next-click, is consumed by **only**
AnomalyPanel (`hooks/useFocusRelation.ts`; single consumer). NarrativeThreads, map heat,
and the universe each re-derive relation with bespoke logic or don't re-scope at all;
SourceIntegrity and the leaf panels ignore it. The mechanism that could make every
surface agree on "here's what connects to what you're looking at" exists and touches one
dock panel.

### 9. The edition spine is abandoned at the console boundary.

`openBrief` drops the theme (`App.tsx:1291`) and no "from the Brief" breadcrumb persists
in the console — so the app never says "here's what else in *today's Brief* connects to
this." The natural daily spine of exploration is severed the moment the analyst crosses
into L2.

**The through-line:** capture (pin) and navigate (open) are two clean shared verbs that
**never chain automatically**. The analyst must alternate them by hand after every
finding. The flywheel's mechanism exists — it just does not self-advance.

---

## 4. WHAT ALREADY WORKS (preserve this)

Do not only fix; the E3/Workbench spine is strong and several onward paths are the model
to copy.

**The bridges that carry honestly.**
- The theme+country deep-link is a clean, double-fire-guarded, pathname-scoped carrier;
  it opens the right ThemeDetail *and* flies the map (`App.tsx:716-754`).
- `prefetchBriefing(24)` on Landing mount makes L0→L1 feel instant (`Landing.tsx:245`).
- The keep-alive shell holds both panes + their state alive across every switch
  (`main.tsx:32-54`) — returning never loses work.

**The store & the snapshot spine.**
- The split-brain unification is genuinely solid: `WorkspaceContext` is a thin adapter,
  every panel pin becomes a `WorkbenchPin` in ONE store the dossier reads (the legacy
  `atlas-workspace` force-graph store was retired). Pins are idempotent toggles.
- The frozen #227 snapshot freezes gate-verified evidence + metrics + the Label-Court
  verdict *at pin time*, so the dossier reads what the analyst SAW, not live drift; every
  derived section is labeled frozen vs measured-at-generation.
- Receipt Citations carry frozen provenance (url / origin-country / gate-status / date)
  straight off the row (`PinReceiptButton.tsx:62`).
- Auto-create-investigation means the first pin from anywhere just works — no "create an
  investigation first" wall; `createInvestigation` dedupes by query. Destructive ops
  carry undo.

**The onward paths that flow (copy these).**
- **UniverseView is the strongest flywheel surface:** click a field node → opens its
  thread or travels into its orbital; neighbors highlight on hover
  (`UniverseView.tsx:214,604`).
- **Person focus is the strongest existing chain:** one `setPerson` lights EntityPanel +
  a *precise* backend `?person=` thread highlight (`NarrativeThreads.tsx:258`) + universe
  re-scope + map fly-to-dominant + anomaly re-scope — all from one click.
- **NarrativeThreads sibling surfacing with honest reason chips** ("↔ shared rare actor /
  country"), rarity-weighted so a common actor like "donald trump" can't glue unrelated
  threads (`NarrativeThreads.tsx:285-334,469`) — every sibling row is clickable.
- **ThemeDetail drill-down:** "STORIES INSIDE THIS TOPIC" (memberStories) + "RELATED
  INVESTIGATIONS" (relatedConcepts), both clickable (`ThemeDetail.tsx:981-1025`).
- **SignalDetail connected-threads** open the living thread in-app with
  member/semantic/keyword basis badges (`SignalDetailPanel.tsx:236`).
- **LEADS genuinely produces a new pinnable thread** the analyst hadn't seen
  (`WorkbenchPanel.tsx:486`; `research_leads.py:145-208`) — the engine exists; it's just
  gated and doesn't self-advance (§3.4).

**Honesty as a feature.**
- `FocusIndicator` chip + "Scoped to X ✕" strips make every re-scope legible and
  reversible — no silent filtering (`NarrativeThreads.tsx:416`; `App.tsx:1915`).
- Pervasive labeling: gate tiers, taxonomy-not-evidence, metadata-only, and a prose
  validator that softens unbacked "confirmed" language.
- The 5W+H Editorial Readiness panel is a true have-vs-missing measurement; the Markdown
  export is impressively complete (synthesis, contested figures, corroboration,
  cross-read, readiness, connections, timeline, gaps all travel with the file).

---

## 5. MOBILE — where the journey breaks on a phone

A single hard switch at 768px (`hooks/useIsMobile.ts:6`). The core *is* a real
phone-native re-shape, not a shrunk desktop: the tabbed console shows one full-screen
surface at a time via display-toggle keep-alive (`App.tsx:2170-2181`), a fixed bottom
tab bar honoring iOS safe-area (`App.css:1714-1746`), left-edge swipe-right back nav
(`App.tsx:977-998`), the thread read as a genuine full-screen article with body-scroll
lock (`ThemeDetail.css:1276-1302`), a clean single-column Brief reader, Universe with
proper two-finger pan/pinch/twist (`UniverseView.tsx:530-560`), and a map that
self-heals the `display:none → 0×0` box that killed the old MapLibre path
(`EqualEarthMap.tsx:394-409`). Secondary panels auto-pull the Stream tab forward so
they're never stranded (`App.tsx:1000-1013`). **The per-surface rendering mostly works;
the failures are at the seams and in the missing onward invitations.**

**Where it breaks:**
- **[S] Brief → thread → close is a one-way trip into the cockpit.** Closing the thread
  calls `popPanel`, which only clears `selectedTheme` (`App.tsx:959`) — the analyst is
  left standing in the `/app` console tabs, NOT back on the Brief they came from, with
  feed scroll lost. There is no return-to-Brief path.
- **[A] The heavy WebGL cockpit is always alive on the phone.** Keep-alive mounts both
  App and Brief permanently (`main.tsx:43-49`); the EqualEarthMap canvas + its rAF
  size-poll never unmount, so a phone reading `/brief` still runs the full map/console in
  the background — battery/memory cost, zero benefit.
- **[A] Secondary panels hijack the Stream tab.** Opening a country from Map or a thread
  from Threads force-switches `mobileTab → 'stream'` (`App.tsx:1003-1013`); no split view,
  so every drill-in costs the surface you were reading.
- **[B] Workbench 3-column collapses to a cramped vertical stack** — research-plan column
  ~154px tall (`App.css:1558-1561`) — so comparing the frozen route against live
  suggestions means scrolling one narrow column.
- **[B] CorrelationMatrix is simply gone** — rendered but `display:none`, no 5th tab
  (`App.css:960-962`): a silent capability drop.
- **[B] The Pulse tab is shrunk-desktop** — three dense sub-panels crammed into one phone
  surface (`App.tsx:2098-2168`).

**Where the flywheel gaps compound on mobile:**
- **Save from the Brief has no onward door** — the Brief route mounts no Workspace UI and
  shows no "open your investigation" link (`BriefNewspaper.tsx:547-582`), so the capture
  dies on the surface where it happened.
- **Universe — the richest onward-discovery surface — is buried** behind the
  GLOBE|UNIVERSE toggle inside the Map tab; nothing on the Brief or the thread read
  invites a phone reader into it.
- **No thread → pin → next bridge on a phone:** the constellation/dossier that would
  suggest the next thing is desktop-oriented and only in the separate full-screen
  Workbench modal, so on a phone the pin is a dead capture.
- **The 4-tab bar is orientation-only** — no tab surfaces "what changed since you last
  looked" or "your open investigation" as a persistent onward prompt.

---

## 6. DESIGN QUESTIONS FOR THE CREATIVE SESSION

Framed as open questions — the session answers them.

1. **Should opening a thread be a LENS over the current focus, not a frame-clear?** Can
   the console hold a *compound* focus — "person X **and** this thread," "country Y **and**
   this thread" — so each discovery compounds the investigation instead of resetting it?
   *(Targets §2 + the mutually-exclusive setters — the S-tier spine fracture,
   `App.tsx:2049` / `FocusContext.tsx:127-140`.)*

2. **What is the ONE gesture that captures a finding into an investigation from ANY
   surface** — a globe hotspot, a universe node, a constellation bridge, a thread row, a
   receipt — and that unifies the two capture models (thread-pin vs receipt-citation)
   into a single investigation object? *(Targets §3.1, §3.5, §5, and the pins/citations
   split, `workbench.ts:133-139`.)*

3. **Should every "here's what's missing / here's the tension" signal be a LAUNCHER?**
   Is a coverage gap, a cross-read tension, a bridge star, an unpinned lead a *clickable
   seed* for the next query/pin — so the report is a turn of the wheel, not an exit?
   *(Targets §3.1, §3.3, §3.4 — the flywheel close, `DossierView.tsx:968,987,749`;
   `DossierConnections.tsx:363`.)*

4. **What is the persistent, always-visible "investigation you're building" object in
   L2?** How does the analyst always know *which* investigation their next pin lands in,
   how many pins it holds, and how they connect — without opening a modal?
   *(Targets §3.7 + silent/invisible-destination capture, `WorkspaceContext.tsx:177`;
   `workbench.ts:208`.)*

5. **How does the dossier show what is MISSING, not just what is pinned — and make the
   gap the on-ramp to the next investigation?** Should readiness (the 5W+H have-vs-missing
   measurement) live *in the build surface*, not only inside the report?
   *(Targets §3.3 + `DossierView.tsx:585` readiness-invisible-until-report.)*

6. **When should the flywheel self-advance vs wait for the analyst?** Pinning a lead
   doesn't navigate or refresh leads; capture shows no next step; LEADS needs a manual
   paid press. What is proactive (auto-surface the next candidate) vs on-demand — and how
   is that honest about cost? *(Targets §3.4, §3.7, `WorkbenchPanel.tsx:486-495,110-121`.)*

7. **Where does exploration live on a phone, and how does a finding lead to the next one
   there?** Should the Brief-read → thread → "next related / who else covers this" be one
   reading flow rather than an ejection into the cockpit tabs? *(Targets §5 mobile seams,
   `App.tsx:959`.)*

8. **Should navigation carry the finding's context, not just its id?** When the analyst
   crosses L1→L2 or opens a neighbor, should the label / why_now / coverage / the
   provenance ("you came from the Brief," "you're chasing a gap") travel — so the next
   surface is seeded, not blind? *(Targets §1 carry/drop + the `q`-param and
   `labelHint` drops, `App.tsx:722-739,729`.)*

---

### Return summary

- **Doc:** `/Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal/docs/state/2026-07-21-analyst-journey-map.md`
- **Top-5 flywheel gaps:** (1) bridge stars inert — the app draws "look here next" and
  disables the click (`DossierConnections.tsx:363,520-523,552-555`); (2) thread-open wipes
  the focus bus so each discovery is an island, never compounding
  (`App.tsx:2042-2050`); (3) the report is terminal — coverage gaps, cross-read tensions,
  and contested figures are the sharpest next-investigation seeds and none are clickable
  (`DossierView.tsx:968,987,749-836`); (4) LEADS is the real engine but gated behind a
  manual paid trigger and doesn't self-advance — pinning a lead neither navigates nor
  re-runs (`WorkbenchPanel.tsx:110-121,486-495`); (5) the discovery surfaces (map,
  universe, constellation, biography, day-evidence) can't capture what they surface — no
  pin affordance (`WorkbenchConstellation.tsx`, `UniverseView.tsx`, `EqualEarthMap.tsx`).
- **Sharpest 3 design questions:** (1) should thread-open be a *lens over* the current
  focus rather than a frame-clear (compound focus)? (2) what is the ONE capture gesture
  that works from any surface and unifies thread-pins with receipt-citations? (3) should
  every "what's missing / here's the tension" signal — gap, cross-read tension, bridge
  star, unpinned lead — be a clickable launcher for the next query, so the report is a
  turn of the wheel, not an exit?
