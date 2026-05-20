# Atlas — First-User Experience Design Spec

**Date:** 2026-05-05  
**Branch:** v3-intel-layer  
**Scope:** UX improvements for a first-time user arriving at the Atlas dashboard with zero prior context — no defined search goal, no knowledge of what Atlas is.  
**Constraint:** No new backend features. Improvements to entry experience, exploration flow, and comprehension. Layout restructuring is on the table if justified.

---

## Context

Atlas is a global narrative intelligence tool that shows how topics are covered differently across countries and media sources. The current dashboard is designed for power users (journalists, researchers, analysts). A curious newcomer arriving with no context finds a dense 6-panel interface filled with technical jargon and raw GDELT data codes — and no clear explanation of what Atlas does or where to start.

The use case file (`atlas_use_case_analysis.md`) documents three expert personas (journalist, researcher, citizen) but doesn't address the pre-persona moment: the anonymous curious visitor who doesn't yet know if Atlas is for them.

---

## Current Layout

```css
grid-template-areas:
  "radar  stream  threads"
  "radar  stream  matrix"
  "integrity  anomaly  anomaly";

grid-template-columns: minmax(280px, 35%) minmax(280px, 1fr) minmax(240px, 30%);
grid-template-rows: minmax(220px, 40%) minmax(180px, 1fr) minmax(140px, 20%);
```

6 panels: Globe (radar), Signal Stream (stream), Narrative Threads (threads), Correlation Matrix (matrix), Source Integrity (integrity), Anomaly Alert (anomaly).

---

## 1. First Impression Diagnosis

The user arrives with zero context. The experience unfolds in three phases:

**0–2s:** A dark world map with countries glowing in red-orange heat. Visually striking. The brain registers "something global is happening."

**2–5s:** Reads "ATLAS." No context. Scans the command bar: empty search field (search what?), time buttons 6H/24H/48H/7D (controls what?), "36 ctry • 1.2M sig" (what's a sig?), "BRIEF" button (what's a brief?).

**5–10s:** Panels. "SIGNAL STREAM" shows `US · CONSULT · EU · MAKE STATEMENT` — raw GDELT codes, reads like a developer terminal. "NARRATIVE THREADS" shows `ARMED_CONFLICT`, `UNGROUPED_ELECTIONS` — internal GDELT tags. "CORRELATION MATRIX" shows a green heatmap grid with no axis labels visible.

**Second 10:** Decision point. Options: type something into search (but what?), click on a country (is it clickable?), or leave.

**Verdict:** Atlas projects the right aesthetic — serious intelligence tool, dark mode, live data — but fails to communicate its purpose or suggest a first action. It's a control room with no instructions.

---

## 2. Visual Reading Order

Eye scan follows an approximate Z-pattern:

1. **Logo (top-left):** "ATLAS" — establishes brand, nothing else
2. **SearchBar (top-center):** User looks for a placeholder hint. None. The field is passive.
3. **Globe (left, large):** Highest visual weight. The heat animations attract attention. Many users will try to hover or click — but there's no affordance indicating interactivity. Those who click discover CountryBrief, which is a coherent experience. Those who don't click miss the best natural entry path.
4. **Signal Stream (center):** Second-largest panel. Scanned and mentally tagged as "data for experts." Actively repels the curious non-expert.
5. **Narrative Threads (right column):** More readable, but `ARMED_CONFLICT` and `UNGROUPED_ELECTIONS` are still technical tags. User might click, but doesn't know what to expect.
6. **Bottom row:** Source Integrity + Anomaly Alert. Visually so subdued that most new users never reach them. Anomaly Alert has the most intriguing content ("CO ×3.2") but near-zero visual weight.
7. **Welcome card:** Bottom-left corner of the map. 10px monospace text. The only explicit onboarding. Located at the lowest-attention point of the entire screen.

---

## 3. Hierarchy and Layout Problems

**Problem A — Central panel communicates the wrong message.**
The Stream panel occupies the most semantically prominent position (center column, largest vertical span) but shows the least accessible content for a new user. The most readable, explorable content (Narrative Threads) is in the weakest position.

**Problem B — The map dominates but doesn't invite action.**
35% width × 80% height with glow animations. Maximum visual weight. But without a visible affordance, users read it as decoration, not interface. Only cursor change on hover — invisible until tried.

**Problem C — Visual hierarchy inverts utility.**
Panels most valuable for a curious newcomer (Anomaly Alert — *what is unusual right now?*; Narrative Threads — *what topics can I explore?*) have the lowest visual weight. Panels requiring expertise to interpret (Signal Stream, Correlation Matrix) have the highest.

**Problem D — Onboarding is broken by position.**
The Welcome Card exists, but: (a) it's at the lowest-attention point of the screen, (b) "See what's happening →" doesn't explain what Atlas is, (c) clicking it opens the Briefing modal — a dense text summary that informs but doesn't onboard.

**Problem E — All panel titles are jargon-first.**
`SIGNAL STREAM`, `NARRATIVE THREADS`, `CORRELATION MATRIX`, `SOURCE INTEGRITY`, `ANOMALY ALERT` — correct for analysts, opaque for curious newcomers. Subtitles exist ("how topics spread over time") but are rendered at 9px with 0.25 opacity.

**Problem F — No primary call to action.**
No element on the screen says "start here." Every panel presents itself as equally available, creating decision paralysis.

---

## 4. Improvement Opportunities

1. **SearchBar as active invitation.** A placeholder transforms the field from passive to directive — no backend work needed.
2. **Welcome Card as value moment.** Instead of a generic link, surface 3 hot topics of the moment with one-line context. User clicks on a topic they care about without needing to understand what Atlas is.
3. **Signal Stream default → Discovery Mode.** When no context is active (no search, no country, no theme selected), the center panel shows top topics in natural language with volume/trend signals instead of raw GDELT codes.
4. **Narrative Threads in natural language.** GDELT theme codes mapped to human-readable names. `ARMED_CONFLICT` → `Armed conflict`. `UNGROUPED_ELECTIONS` → `Elections 2025`. Turns the most explorable panel into something a newcomer can actually read.
5. **Map affordance hint.** A subtle animated hint appears 2 seconds after load and disappears on first map click. Eliminates the "is this clickable?" friction.
6. **Anomaly Alert with real visual weight.** The most intriguing content for a curious user ("Colombia: 3× normal coverage") is nearly invisible. A visible border and larger grid-area allocation surfaces it.
7. **Human-readable stats.** `36 ctry • 1.2M sig` → `36 countries · 1.2M signals today`.

---

## 5. Proposed Layout

```css
grid-template-areas:
  "radar  discovery  threads"
  "radar  discovery  threads"
  "anomaly  anomaly  integrity";
```

**What changes:**

- `stream` → `discovery` in the default state. When user has no active context, the center panel shows the Discovery Panel. When a search or selection is active, the panel reverts to its current behavior (CountryBrief, ThemeDetail, EntityPanel, SignalStream).
- `matrix` removed from initial state. Correlation Matrix is accessible from within ThemeDetail as a tab — it's a power-user tool that shouldn't consume real estate on the blank-state screen.
- `anomaly` expanded to 2/3 of the bottom row. Gives Anomaly Alert the visual presence its content deserves.
- `threads` spans both rows of the right column (currently shared with `matrix`).

**What doesn't change:** Grid column/row proportions, Globe size, all existing panel behaviors, routing logic, all backend endpoints.

---

## 6. Concrete Recommendations

### R1 — SearchBar placeholder *(~10 min)*

Add `placeholder="Search a topic, country, or person..."` to `SearchBar.tsx`. No other changes.

### R2 — Rewrite the Welcome Card *(~30 min)*

Replace "Last 24 hours / See what's happening →" with:

- Title: "Atlas tracks how the world covers the news"
- Subtitle: "Click any country on the map, or search a topic"

Same position, same dismiss logic, same `sessionStorage` flag.

### R3 — Map click affordance *(~45 min)*

A subtle hint anchored to the center-bottom of the map panel. Appears 2 seconds after `mapReady` fires. Disappears on first `country-heat-fill` click. Uses `sessionStorage('atlas-map-hinted')` to not reshow. Example: `↑ click any country to explore`.

### R4 — Discovery Panel as stream default *(1–2 days)*

New component `DiscoveryPanel.tsx`. Renders when `focus.type === null && !selectedTheme && !selectedCountry && !selectedChokepoint`. Shows top 4–5 topics from the `/api/v2/narratives/threads` endpoint (already used by NarrativeThreads), but formatted as cards with natural-language names, signal count, trend direction, and country spread. Auto-refreshes on the same 5-minute cycle as the rest of the app. When user selects a context, the panel transitions to the existing slot behavior.

> **Implementation note:** The DOM element and CSS class remain `.terminal-panel.stream` with `grid-area: stream`. "Discovery" is the conceptual name for the default content state, not a new DOM node. The slot already handles context switching (CountryBrief, ThemeDetail, EntityPanel) — Discovery Panel is simply a new branch in that existing conditional.

### R5 — Display name mapping for Narrative Threads *(half day)*

Create `src/lib/themeDisplayNames.ts` — a constant map from GDELT theme codes to human-readable names. Apply in `NarrativeThreads.tsx` and `DiscoveryPanel.tsx`. Example:

```ts
export const THEME_DISPLAY_NAMES: Record<string, string> = {
  ARMED_CONFLICT: 'Armed conflict',
  UNGROUPED_ELECTIONS: 'Elections',
  ECON_TRADE_PARTNER: 'Global trade',
  // ...
}
```

### R6 — Anomaly Alert visual weight + grid reorder *(~30 min — CSS only)*

Update `grid-template-areas` to give Anomaly Alert 2/3 of the bottom row (as in Section 5 proposal). Change Anomaly Alert border to `rgba(239, 68, 68, 0.15)`. Move Correlation Matrix out of the default layout — it becomes a tab/section within ThemeDetail (already partially rendered there via CorrelationMatrix component), accessible after the user has selected a theme. Narrative Threads expands to fill both right-column rows.

### R7 — Human-readable stats *(~15 min)*

In `App.tsx`, change the stats display from `${nodes.length} ctry • ${totalSignals.toLocaleString()} sig` to `${nodes.length} countries · ${totalSignals.toLocaleString()} signals today`.

---

## 7. Prioritized Change List

| Priority | Change | Impact | Effort |
| --- | --- | --- | --- |
| 🔴 1 | Discovery Panel as stream default | Eliminates the biggest first-impression blocker | Medium |
| 🔴 2 | Display names in Narrative Threads | Makes the most explorable panel readable | Low-medium |
| 🟡 3 | Map affordance hint | Activates the most natural exploration path | Low |
| 🟡 4 | Welcome Card rewrite | Minimum viable onboarding | Low |
| 🟡 5 | SearchBar placeholder | Turns passive field into an invitation | Minimal |
| 🟡 6 | Anomaly Alert visual weight | Surfaces the most intriguing content | Minimal (CSS) |
| 🟢 7 | Human-readable stats | Removes jargon from command bar | Minimal |
| 🟢 8 | Grid reorder (remove Matrix from default) | Reduces cognitive load on blank state | Low (CSS) |

---

## 8. Design Risks

**Risk A — Discovery Panel with stale content.**
If Discovery Panel shows the same 4 topics for hours, returning users lose trust that Atlas is live. Must refresh on the same 5-minute cycle as the rest of the app.

**Risk B — Map hint that doesn't disappear.**
If the affordance hint persists after the user has already interacted with the map, it becomes noise. Must dismiss on first click and use `sessionStorage` to prevent reappearance.

**Risk C — Display names too generic.**
`ARMED_CONFLICT` → `Conflict` loses specificity. Names must be informative: `Armed conflict`, not `Conflict`. A rushed mapping makes topics look identical.

**Risk D — Discovery Panel permanently replacing the Stream.**
Raw SignalStream has value for power users. The condition for showing Discovery vs Stream must be strictly `no active context`. Any ambiguity causes regression for expert users.

**Risk E — Larger Welcome Card covering active map countries.**
If the welcome card grows to include more content, it may cover actively glowing countries and feel like an interstitial. Must remain small and immediately dismissible.

---

## 9. Success Criteria

1. **First interactive click under 30 seconds.** A new user makes their first click (country, topic, search) within 30 seconds. Today many sessions end with zero clicks.
2. **First click via Discovery Panel or Narrative Threads (not search).** If Discovery Panel works, users without a goal should explore from there — not get stuck at an empty search field.
3. **User can describe Atlas without reading documentation.** After 2 minutes of free exploration, the user can say "it shows how different countries cover the news." If they say "I don't understand what this is for," onboarding failed.
4. **Reduced dashboard bounce rate.** Measurable in analytics: % of sessions where no interactive action occurs before exit.
5. **Increased Narrative Threads click-through.** Natural-language topic names should drive more clicks. Clearest direct signal that the copy change had effect.

---

## Implementation Notes

- All changes are frontend-only except Discovery Panel (needs `/api/v2/narratives/threads` — already implemented for NarrativeThreads).
- No new backend endpoints required.
- Discovery Panel can reuse the NarrativeThreads data fetch — different presentation layer only.
- Changes should be delivered as separate PRs in priority order so each can be validated independently.
- Tailwind CSS must NOT be used in dashboard components — vanilla CSS only, CSS custom properties from `ThemeContext`.
