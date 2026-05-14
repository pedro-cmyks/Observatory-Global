# Atlas — Public Attention Enrichment Layer Design Spec

**Date:** 2026-05-14  
**Branch:** `v3-intel-layer`  
**Scope:** Design spec for making Public Attention a first-class enrichment layer across existing Atlas panels.  
**Status:** Awaiting user review before implementation planning.  

---

## Context

Atlas currently has two different kinds of live signal:

- **Media signal:** GDELT, RSS, ReliefWeb, ACLED-adjacent coverage, sources, countries, headlines, themes, people, sentiment, and framing.
- **Public attention signal:** Wikipedia pageviews and Google Trends today; possible future sources include Reddit or other public-discussion surfaces.

The current UI treats Public Attention mostly as a lower-panel list and a simple center detail panel. That is useful, but too static. A user can discover something interesting, such as `ShinyHunters`, read a good Wikipedia summary, and then lose the investigative path when clicking a related chip like `Managing Director`, because the app opens the global theme instead of the theme inside the ShinyHunters/cybersecurity context.

The goal is not to create a separate Public Attention product. The goal is to let Public Attention enrich the existing Atlas surfaces: Public Attention detail, Entity/Person, ThemeDetail/Narrative Thread, Country Intelligence, Anomaly Alert, and Workspace.

---

## Product Principle

**Public Attention is the people's side of the signal system.**

Signal Stream answers: what are media outlets publishing?

Public Attention answers: what are people reading or searching for?

Narrative Threads should become the place where Atlas compares those two forces: when they converge, diverge, accelerate, or ignore each other.

Every click from Public Attention must preserve its parent context. If a user starts at `ShinyHunters` and clicks `Cyber Attack`, Atlas should open `Cyber Attack within ShinyHunters context`, not an unrelated global Cyber Attack topic.

---

## Non-Goals

This spec does not implement:

- A movable/resizable analyst canvas. That is a separate workstation-layout spec.
- A full mobile redesign. This spec should avoid making mobile worse, but mobile navigation needs its own pass.
- New Reddit/social ingestion. The design should leave room for it, but initial implementation uses current Wikipedia and Google Trends data.
- A new standalone Public Attention dashboard.
- A paid LLM call on every interaction.

---

## Current Data Sources

### Wikipedia

Current ingestion reads top articles from selected Wikipedia language editions and stores them in `wiki_pageviews_v2`.

Important limitation: this is not true per-country reader traffic. The code maps countries to language editions and reuses the same project data across countries that share a language, such as US/GB/IN for `en.wikipedia` or CO/MX/AR for `es.wikipedia`.

UI copy must therefore avoid implying exact country-level Wikipedia audience measurement. Use labels such as:

- `Wikipedia attention by language edition`
- `Countries mapped to this attention source`
- `Public attention proxy`

### Google Trends

Current ingestion reads Google Trends RSS by country (`geo=XX`) into `trends_v2` every ~30 minutes. This is closer to country-specific attention than the current Wikipedia implementation, but still a public trend proxy, not a precise population-normalized measure.

### Media Signals

Media data comes through `/api/v2/signals`, `/api/v2/search/unified`, `/api/v2/theme/{theme}`, `/api/v2/focus`, `/api/v2/narratives`, and related endpoints. Public Attention should be joined to media signals through query terms, related themes, countries, people/entities, and time window.

---

## Shared Interaction Rule

All panels should pass a `context` object when a user pivots from one item to another.

Conceptual shape:

```ts
type InvestigationContext = {
  originType: 'public_attention' | 'theme' | 'country' | 'person' | 'signal' | 'anomaly'
  originLabel: string
  query?: string
  country?: string
  theme?: string
  signalId?: number
  sourcePanel: 'PublicAttentionPanel' | 'ThemeDetail' | 'CountryBrief' | 'EntityPanel' | 'AnomalyPanel'
  timeRange: TimeRange
}
```

The implementation does not need this exact type if the existing focus/workspace context has a better shape, but the behavior must hold:

- Related chips opened from Public Attention keep the public-attention origin.
- ThemeDetail can display that it is scoped to an origin such as `ShinyHunters`.
- Workspace can record the path as a trail.
- Back navigation returns to the previous investigation state, not the generic stream.

---

## Panel Design

### 1. Public Attention Panel

Current sections:

- What is it?
- Countries talking about it
- Why these signals connect
- What they are saying

Enhancements:

- Add a compact **Media vs Public** summary:
  - public attention volume
  - media signal count
  - countries with media matches
  - trend/search match if available
- Make related theme chips contextual. A chip should open ThemeDetail with the public-attention item as parent context.
- Make signal rows actionable. Clicking a signal opens signal-level focus or pins that signal into the current workspace route.
- Add a **Next investigative steps** row:
  - open contextual theme
  - inspect countries
  - pin route to workspace
  - compare public attention vs media coverage

### 2. ThemeDetail / Narrative Thread

Current strengths:

- Evolution graph
- Narrative drift
- Activity timeline
- Related topics
- People mentioned
- Top sources
- Recent coverage

Enhancements:

- Add a **Public Attention lane** near the top or before Related Topics:
  - matching Google Trends keywords
  - matching Wikipedia topics
  - whether public attention is rising without matching media volume
  - whether media volume is high but public attention is low
- When opened from a public-attention item, show the origin:
  - `Context: ShinyHunters → Cyber Attack`
- Related topics must preserve this context.
- Recent coverage should be filterable by the context query when present.

### 3. Country Intelligence

Current issue: it has useful metrics but reads too thin compared with `/brief`.

Enhancements:

- Add a richer natural-language analysis block similar to the brief, but scoped to the selected country and time window.
- Add a **Public Attention in this context** section:
  - top Wikipedia/Trends items mapped to the country or language source
  - matched media signals
  - visible warning when Wikipedia is a language-edition proxy, not true country traffic
- Top themes and people should show whether they are media-led, public-led, or both.

### 4. Entity / Person Panel

Current issue: entity classification can treat places like `Los Angeles` as people.

Enhancements:

- Separate entity classes visually: person, organization, place, public-attention topic.
- Use NLP entity type when available instead of forcing every entity into a person workflow.
- Add public-attention match badges:
  - `Wiki`
  - `Trend`
  - future `Reddit`
- If a user opens an entity from Public Attention, preserve origin context.

### 5. Anomaly Panel

Anomaly Alert should remain in the lower operational area, but it should be connected to Public Attention.

Enhancements:

- If an anomaly country/theme also has public attention, show a small public-attention indicator.
- If public attention spikes but media coverage is low, classify it as a possible attention anomaly.
- Add the Anomaly/Public Attention relationship to the onboarding walkthrough.

### 6. Workspace

Workspace should contain the Investigation Trail, not be replaced by it.

Proposed workspace tabs:

- `Graph`: current force graph.
- `Trail`: chronological route of investigation.
- `Notes`: current note-taking/export surface.

Trail example:

```text
Public Attention: ShinyHunters
→ Theme: Cyber Attack, scoped to ShinyHunters
→ Country: Netherlands
→ Signal: Podcast De Dag...
```

When an interaction adds a route, a small tree/branch icon can light up near the clicked item or workspace button. This reinforces that the investigation is being built without forcing the user into Workspace immediately.

---

## Layout Notes

The current lower panel area is cramped, especially on laptop screens. This spec does not redesign the whole layout, but implementation should avoid adding more content to the lower panel without an expansion behavior.

Acceptable first-slice approaches:

- Keep the lower Public Attention list compact.
- Improve the center Public Attention detail panel.
- Add contextual enrichment to ThemeDetail/CountryBrief/EntityPanel.
- Add a small onboarding step for Anomaly/Public Attention.

Deferred layout tracks:

- `Attention Dock`: an expandable lower dock for Anomaly, Public Attention, Geo Alerts.
- `Analyst Canvas`: movable/resizable panels with a default layout and mobile fallback.

---

## Data Flow

### Public Attention click

1. User clicks a public-attention item such as `ShinyHunters`.
2. Atlas opens `PublicAttentionPanel`.
3. Panel fetches:
   - `/api/v2/search/unified?q=ShinyHunters&hours=<range>`
   - Wikipedia summary from external Wikipedia API, if available
   - existing public-attention counts from `/api/v2/wiki/top` or search result payload
4. Panel derives:
   - matched media signals
   - top countries from media matches
   - related themes from matched signals
   - public/media contrast state
5. Any child click passes the parent investigation context.
6. Workspace records the route when the user pins or when the product decides an interaction is trail-worthy.

### Theme opened from Public Attention

1. User clicks `Cyber Attack` from `ShinyHunters`.
2. ThemeDetail opens with:
   - `theme=Cyber Attack`
   - `origin=ShinyHunters`
   - `query=ShinyHunters`
   - current time range
3. ThemeDetail shows global theme data, but clearly marks and filters context-specific evidence.
4. Related topics and recent coverage preserve the origin unless the user explicitly resets to global.

---

## Error Handling

- If Wikipedia summary fails, keep media matches and show a neutral unavailable state.
- If Google Trends has no match, do not imply absence of public interest; label as `No matching trend in current window`.
- If media signals are absent, keep the public-attention topic visible and explain that Atlas has public attention without media matches in the selected window.
- If NLP fields are missing, fall back to current GDELT themes/persons and mark low confidence where needed.
- If the context query returns too few signals, suggest expanding the time range.

---

## Copy Guidelines

Avoid overstating precision:

- Prefer `public attention proxy` over `what people in this country are reading`.
- Prefer `Wikipedia attention by language edition` when using current wiki data.
- Prefer `search interest by country` for Google Trends RSS.
- Avoid saying `no one is talking about this`; say `Atlas has no matching media signals in this window`.

Use natural-language analysis in Country Intelligence:

- What changed?
- What themes dominate?
- What public-attention topics overlap?
- Which source patterns matter?
- What should the analyst inspect next?

---

## Testing Plan

Frontend:

- Public Attention item opens center panel.
- Related theme chip from Public Attention opens ThemeDetail with origin context visible.
- Back navigation returns to PublicAttentionPanel, not generic Signal Stream.
- CountryBrief shows public-attention enrichment when country data exists.
- ThemeDetail shows Public Attention lane when matches exist.
- EntityPanel separates person/place/org labels where NLP data is available.
- Walkthrough includes Anomaly/Public Attention explanation.

Backend/API:

- `/api/v2/wiki/top` still returns quickly.
- `/api/v2/trends/search` and `/api/v2/trends/match` return stable payloads when empty.
- `/api/v2/search/unified?q=ShinyHunters` returns public attention plus signal matches when available.
- No new endpoint is required for first slice unless existing payloads cannot preserve context cleanly.

Manual QA:

- Use `ShinyHunters` as the anchor scenario.
- Use `Colombia → Public Sector` as the brief-to-console scenario.
- Use a country with sparse data to verify empty-state copy.
- Verify laptop-height behavior so lower Public Attention remains reachable.

---

## Success Criteria

- A user can start at a Public Attention item and continue into a contextual investigation without losing the original topic.
- Public Attention data appears inside ThemeDetail/CountryBrief/EntityPanel where relevant.
- The four center panels feel like the same product family: shared header grammar, metrics, contextual chips, evidence lists, and action patterns.
- The user can tell the difference between media coverage and public attention.
- Workspace makes the investigation route visible through Trail without forcing users into Workspace at every click.
- Onboarding explains Public Attention and Anomaly enough that a first-time user knows why those panels matter.

---

## Recommended First Implementation Slice

1. Add context-preserving pivots from PublicAttentionPanel to ThemeDetail.
2. Add Public Attention lane to ThemeDetail.
3. Add a richer CountryBrief natural-language block plus public-attention section.
4. Add Workspace Trail data model/UI shell inside existing Workspace.
5. Add one onboarding step for Anomaly/Public Attention.

Analyst Canvas should be planned separately after the enrichment layer is useful.
