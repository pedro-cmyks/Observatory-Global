# Atlas — Session Log

## 2026-04-24 (session 2)

### Added
- **EntityPanel component** — right panel for person/keyword search results. Shows: trust indicators (source diversity, countries, global sentiment), coverage by country (bar chart colored by sentiment), related themes (clickable chips → ThemeDetail), top sources with sentiment, recent headlines. Opens automatically when `focus.type === 'person'`.
- **Keyword search fully connected** — SearchBar now triggers map fly + correct panel for all result types:
  - Country result → fly + CountryBrief
  - Theme result → fly to top country + ThemeDetail + arcs
  - Person result → fly to top country + EntityPanel (person-filtered map)
- **FocusContext: person as first-class focus type** — added `person: string | null` to `GlobalFilter`, `setPerson()` method, `focus.type` now returns `'person'`. Previously `setFocus('person',...)` called `clearFilter()` silently.
- **Search endpoint enriched** — themes and persons now return `total_signals` + `top_countries [{code, name, count}]` (needed for map fly). TAX_* and WORLDLANGUAGES_* themes excluded from results. Redis cache 2 min.
- **Search dropdown redesigned** — country tag (blue), person tag (violet), signal count + top country codes in meta. ESC closes, × button clears.

### Fixed
- `setFocus('person', ...)` was silently calling `clearFilter()` — EntityPanel never rendered
- Country click inside EntityPanel now calls `clearFocus()` first so CountryBrief can take over
- Theme search was matching GDELT taxonomy codes (TAX_WORLDFISH_TRUMPETER for "trump") — filtered

### Known issues / Roadmap
- AI insight: account needs Anthropic credits (key is loaded, auth works)
- Person click inside CountryBrief/ThemeDetail pill → still no action (separate from search)
- Aircraft: still amber dots, needs intelligence-value filter (military/diplomatic callsigns)
- Maritime vessels: AISStream Phase 3C, not started
- Globe 3D: deferred

### Next session
- Sort/rank for article coverage in ThemeDetail (currently timestamp, consider relevance)
- Hosting: move off local Mac → Fly.io (backend) + Vercel (frontend)
- Aircraft intel layer: filter by military/diplomatic callsigns (ADSBExchange)
- Maritime layer design + implementation

---

## 2026-04-24

### Added
- **Country territory click** — Mapbox fill layer (`country-heat-fill`) click handler replaces node dot clicks. Clicking anywhere on a country's geography fires `handleCountryClick`. Includes `ISO_TO_GDELT` mapping for code mismatches (ID→RI, RS→RB, XK→KV, etc.)
- **Node dots removed** — `nodes-core` ScatterplotLayer deleted. Territory click handles selection. Anomaly pulse rings (red circles for crisis countries) preserved.
- **NODES toggle button removed** — was controlling the now-deleted dots layer.
- **AI insight error codes** — backend now returns `insight_no_credits` (vs `insight_unavailable`) when the Anthropic API rejects due to low balance. ThemeDetail shows actionable message: "Anthropic account has no credits (top up at console.anthropic.com)"
- **Insight model fix** — model name corrected from `claude-haiku-4-5` → `claude-haiku-4-5-20251001`
- **CorrelationMatrix parse error fix** — removed IIFE pattern `(() => { ... })()` inside JSX ternary (Babel parser incompatible). Refactored normalization into a plain variable block before the return.

### Known issues / Roadmap
- **AI insight**: `ANTHROPIC_API_KEY` is loaded and auth works, but account has no API credits — add funds at console.anthropic.com to activate
- People Mentioned: pills shown but person click → no action yet
- Keyword/company search: SearchBar exists but free-text search not connected to backend
- Aircraft icon: still amber dot, real plane SVG shape deferred
- Maritime vessel layer (AISStream): Phase 3C, not started
- Globe 3D: deferred

### Next session
- Signal stream sort order — review how articles are ordered inside ThemeDetail recent coverage (currently by timestamp, consider by relevance/sentiment)
- Person click → search/filter view
- Keyword search → backend `/api/v2/search?q=` endpoint
- Aircraft icon → real plane SVG shape

---

## 2026-04-23 (session 2)

### Added
- `COUNTRY_COORDS` static coordinate table in App.tsx — map fly now works for countries without active signals (Slovenia, Tanzania, Albania, etc.)
- `CountryThemePanel` component — right panel showing a country's specific coverage of a theme (timeline, sources, articles, related topics). Positioned at right:0, z-index 500
- ThemeDetail `hasRightPanel` prop — shifts overlay left (padding-right: 420px) so it doesn't cover CountryThemePanel
- ThemeDetail `onCountryCardClick` prop — "How It's Covered" cards now update the right CountryThemePanel instead of drilling in center
- ThemeDetail `originCountry` — origin country appears first in "How It's Covered" grid with blue highlight
- `rightPanelThemeCountry` state in App.tsx — manages which country+theme to show in right panel
- Backend: `load_dotenv()` added to main_v2.py to auto-load root `.env` (fixes ANTHROPIC_API_KEY not found)
- Better insight error message: "AI analysis not configured — add ANTHROPIC_API_KEY to .env and restart the backend"
- Welcome card switched from `localStorage` to `sessionStorage` — shows on every new session, not once ever
- AnomalyPanel now calls `setFocus('country', code)` + `setMapFlyCountry(code)` — map flies on anomaly click
- CountryBrief: `useCrisis()` anomaly lookup — shows `▲ Nx above 7-day baseline` badge + spike indicator on top theme
- CountryBrief: `WORLDLANGUAGES_` and `TAX_WORLDLANGUAGES_` themes filtered from top themes (GDELT language metadata, not actual topics)
- Help mode toggle (`?` button in toolbar) — cursor changes, `[data-help]` hover tooltips enabled globally
- `data-help` attributes on ThemeDetail section headers

### Fixed
- AnomalyAlert click had no map fly (used `setCountry` not `setFocus`)
- CountryBrief theme click opened ThemeDetail without country context or map fly
- ThemeDetail showed "Coverage analysis unavailable" without explanation
- Welcome card never showed again after first dismiss
- ThemeDetail auto-drilled into country (reverted) — now always shows global view
- "Language: Slovenian" no longer appears in top themes (GDELT language tag, not topic)

### Known issues / Roadmap
- ANTHROPIC_API_KEY: backend must be restarted after adding key to .env
- People Mentioned: pills shown but person click → no action yet (search/filter by person not implemented)
- Keyword/company search: SearchBar exists but free-text topic search not yet connected to backend
- Aircraft icon: still amber dot, real plane shape deferred
- Maritime vessel layer (AISStream): Phase 3C, not started
- Globe 3D: deferred to later phase
- OpenSky free tier: ~1 req/60s rate limit

### Next session
- Person click → search/filter view
- Keyword search → backend `/api/v2/search?q=` endpoint
- Maritime vessel layer (AISStream Phase 3C)
- Aircraft icon → real plane SVG shape
- UX: first-minute experience / onboarding improvements

---

## 2026-04-23

### Added
- AI Coverage Insight endpoint: `GET /api/v2/theme/{theme_code}/insight` (Claude Haiku, Redis-cached 15 min, Ollama fallback)
- `anthropic>=0.40.0` added to backend/pyproject.toml
- `.env.example` updated with `ANTHROPIC_API_KEY`, `INSIGHT_PROVIDER`, `OLLAMA_HOST`, `OLLAMA_MODEL`
- ThemeDetail: async insight block, person pills, 2-col related grid, source-filter for Recent Coverage
- FocusContext: `mapFlyCountry` state + `setMapFlyCountry()` for cross-component fly-to hints
- App.tsx: 4 new effects — map fly from Correlation Matrix, fly from NarrativeThreads hint, open ThemeDetail on filter.theme change, close CountryBrief on external country clear
- ESC handler and close callbacks now call `clearFocus()` consistently
- ArcLayer now renders on theme focus; `filter.theme` added to layers useMemo deps

### Fixed
- CountryBrief re-open bug (close was being overridden by focus sync)
- NarrativeThreads theme click only showed pill — ThemeDetail never opened
- Country click in Correlation Matrix did not animate map

### Activate insight feature
Add `ANTHROPIC_API_KEY=sk-ant-...` to `.env`. Without it the endpoint returns `insight: null` gracefully.

### Known issues
- OpenSky free tier rate limits (~1 req/60s recommended)
- Globe 3D deferred to later phase
- Some GDELT theme codes still not in manual label dictionary

### Next session
- UX first minute experience (auto-focus, welcome card)
- Maritime vessel layer (AISStream Phase 3C)
- Aircraft icon → real plane shape

---

## 2026-04-20

### Added
- Aircraft layer: OpenSky integration, amber dots, PLANE toggle
- Graceful degradation for API rate limits (no fake data)
- ThemeDetail framing section promoted to top
- Correlation Matrix → CountryBrief click navigation
- Source Integrity: real domain names from backend (extract_domain)
- GDELT theme label improvements (regex cleanup in themeLabels.ts)
- README rewritten for Atlas public launch
- CONTRIBUTING.md added

### Known issues
- OpenSky free tier rate limits (~1 req/60s recommended)
- Globe 3D deferred to later phase
- Some GDELT theme codes still not in manual label dictionary

### Next session
- UX first minute experience (auto-focus, welcome card)
- Maritime vessel layer (AISStream Phase 3C)
- Aircraft icon → real plane shape
