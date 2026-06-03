# Frontend Surface Data Map

**Date:** 2026-06-03  
**Scope:** `frontend-v2` only. The old `frontend/` directory is deprecated and
out of scope.  
**Purpose:** make it cheap to connect or disconnect Atlas data work without
guessing which UI surface owns a contract.

## Route Map

| Route | Surface | Primary owner | Data role |
|---|---|---|---|
| `/` | Landing | `pages/Landing.tsx` | Entry page, health check, brief prefetch |
| `/brief` | Newspaper brief | `pages/BriefNewspaper.tsx` | First-pass narrative briefing and Watchlist |
| `/app` | Main console | `App.tsx` | Live exploration workspace with panels |
| `/docs`, `/docs/*` | Docs page | `pages/Docs.tsx` | Static product/API docs |

## Main Console Surface Map

| Surface | Mounted now | File(s) | Primary data | What it shows | Dynamic-topic impact |
|---|---:|---|---|---|---|
| Command bar stats | yes | `App.tsx`, `FocusDataContext.tsx` | `/api/v2/nodes`, `/api/v2/stats` | country/signal counts, data start date | indirect only; still node/signal aggregate based |
| Search | yes | `SearchBar.tsx` | `/api/v2/search/unified`, fallback `/api/v2/search` | countries, themes, people, public-attention searches | partial; dynamic-topic slugs can open if searched/passed, but search is not a dynamic-topic discovery surface |
| Globe / heat | yes | `App.tsx`, `FocusDataContext.tsx` | `/api/v2/nodes`, `/api/v2/flows`, `/api/v2/conflict-markers` | country heat, flows, ACLED/GDELT conflict markers | not fed by `dynamic_topics`; country heat remains aggregate signal activity |
| Aircraft layer | toggle | `App.tsx` | `/api/v2/aircraft` | ADS-B aircraft positions | unrelated |
| Vessel/chokepoint layer | toggle/contextual | `App.tsx`, `ChokepointPanel.tsx` | `/api/v2/vessels`, `/api/v2/nodes`, `/api/v2/signals` | maritime chokepoints and nearby signals | unrelated except signals can overlap topic searches |
| Signal Stream blank state | yes | `SignalStream.tsx` | `/api/v2/signals`, `/api/indicators/allowlist` | recent notable signals with local noise filters | not dynamic-topic aware unless `filter.theme` is a dynamic-topic slug; needs smoke before relying on this path |
| Country detail stream state | yes | `CountryBrief.tsx` | `/api/v2/nodes`, `/api/indicators/country/{code}`, `/api/v2/signals`, public attention endpoints | country facts, signals, themes, source pivots | static signal/country route; does not summarize dynamic-topic membership |
| Theme/detail stream state | yes | `ThemeDetail.tsx`, `NarrativeDrift.tsx`, `ExportMenu.tsx` | `/api/v2/theme/{slug}`, `/api/v2/theme/{slug}/insight`, `/api/v2/theme/{slug}/drift`, `/api/v2/search/unified`, `/api/v2/trends/match`, `/api/v2/wiki/match` | theme/thread detail, country breakdown, evidence, public attention, drift | yes for `/api/v2/theme/dynamic-topic-*`; local fix skips static insight for dynamic topics |
| Living Thread detail | yes | `ThreadFocusPanel.tsx` | `/api/v2/threads/{thread_id}`, `/api/v2/translate/batch` | thread explanation, countries, movement, sources, evidence | yes; primary dynamic-topic detail path |
| Public attention detail | yes | `PublicAttentionPanel.tsx` | `/api/v2/search/unified`, `/api/v2/wiki/top` | public-interest item linked to signals/themes | not dynamic-topic-first; can pivot into theme search |
| Person/entity detail | yes | `EntityPanel.tsx` | `/api/v2/focus?focus_type=person` | person-centered signals, themes, countries, sources | entity hygiene issue surfaces here after noisy dynamic entities become clickable |
| Narrative Threads panel | yes | `NarrativeThreads.tsx` | `/api/v2/threads` | living threads list, movement, top countries/sources | yes; primary dynamic-topic list path |
| Correlation Matrix | yes | `CorrelationMatrix.tsx` | `/api/v2/correlation` | country/theme similarity matrix | no direct dynamic-topic feed; `theme` mode still uses static theme-style correlation |
| Anomaly Alert | yes | `AnomalyPanel.tsx`, `CrisisContext.tsx`, `FocusDataContext.tsx` | `/api/v2/anomalies`, `/api/v2/anomalies/themes`, `/api/v2/wiki/top`, `/api/v2/trends/search`, `/api/v2/conflict-markers` | abnormal country movement, public attention, conflict markers | no direct dynamic-topic feed; useful as external corroboration |
| Source Integrity | yes | `SourceIntegrityPanel.tsx` | global `/api/v2/briefing` or focused `/api/v2/focus` summary | source diversity/concentration risk | global view benefits from dynamic-topic briefing only indirectly through source totals; focused theme summary still relies on `/focus` |
| Brief modal | yes, modal | `Briefing.tsx`, `briefingPrefetch.ts` | `/api/v2/briefing`, `/api/v2/briefing/insight` | compact briefing, Watchlist, top countries/sources | yes; Watchlist reads `top_atlas_topics` now backed by dynamic topics |
| Workspace | yes, lazy; production preview-locked | `InvestigationWorkspace.tsx`, `InteractiveWorkspace.tsx`, `WorkspaceContext.tsx`, `workspaceGraph.ts` | pinned item enrichment via `/theme`, `/country`, `/focus`, `/source`, `/search/unified` | session graph and dossier/export workflow | partial; dynamic-topic pins enrich through `/api/v2/theme/dynamic-topic-*`, but there is no explicit `thread` pinned item type |
| Compare person/theme | yes, modal | `PersonCompare.tsx`, `ThemeCompare.tsx`, `CompareBar.tsx` | `/api/v2/compare`, `/api/v2/theme/{slug}` | side-by-side comparisons | theme compare may work with dynamic-topic slug only if `/theme/dynamic-topic-*` shape matches expected fields; needs smoke |
| Country-in-theme drilldown | yes, side panel | `CountryThemePanel.tsx` | `/api/v2/theme/{slug}?country_code=...` | a theme's evidence inside a selected country | should work for dynamic-topic detail branch if country filtering is supported by that endpoint branch; needs targeted smoke |

## Brief Surface Map

| Surface | File | Primary data | What it owns |
|---|---|---|---|
| Newspaper overview | `BriefNewspaper.tsx` | `/api/v2/briefing`, `/api/v2/briefing/insight` | stats, AI/narrative summary, top countries, Watchlist |
| Watchlist evidence snippets | `BriefNewspaper.tsx` | `/api/v2/signals?theme=...` | top three headlines per top theme/topic |
| Country brief inside `/brief` | `BriefNewspaper.tsx` | `/api/v2/nodes`, `/api/v2/signals` | country-filtered summary and theme snippets |
| Saved watches | `useSavedWatches.ts` | `/api/v2/signals` | local named filters with counts |

Current caution: the Watchlist row itself is dynamic-topic aware through
`/api/v2/briefing`, but the headline-snippet fetch still uses
`/api/v2/signals?theme=<slug>`. For `dynamic-topic-*`, the better contract is
`/api/v2/theme/dynamic-topic-*` because member samples come from dynamic topic
membership, not static `signals_v2.themes`.

## Currently Not Visible Or Only Partially Wired

| Item | File(s) | Status | Recommendation |
|---|---|---|---|
| Workbench full interaction | `InvestigationWorkspace.tsx`, `InteractiveWorkspace.tsx` | visible as a blurred public preview in production with `Request early access` and `Support Atlas` CTAs; fully usable on localhost or with `VITE_ENABLE_WORKBENCH=true` | keep public MVP focused on Brief/Globe/Threads while local development continues against real data; use early-access emails as lean demand validation |
| Discovery panel / Atlas heat list | `DiscoveryPanel.tsx`, `AtlasHeatList.tsx` | component exists, no current `App.tsx` mount | either retire or decide where discovery belongs before adding new discovery UI |
| `/api/v2/narratives` concepts path | `DiscoveryPanel.tsx`, backend `narratives.py` | not visible in current app route | treat as legacy/static narrative path unless explicitly revived |
| Crisis dashboard/toggle | `CrisisDashboard.tsx`, `CrisisToggle.tsx` | toggle hidden in `App.tsx`; crisis context still feeds anomaly panel | keep hidden unless crisis mode becomes a product mode again |
| Focus summary panel | `FocusSummaryPanel.tsx` | component exists, not mounted | source of older architecture comments; avoid adding data here unless remounted |
| Placeholders | `CorrelationMatrixPlaceholder.tsx`, `NarrativeThreadsPlaceholder.tsx` | not mounted | safe to delete later after a cleanup pass |
| Dev banner | `DevBanner.tsx` | not mounted | optional dev-only surface; not product data path |
| `/api/v2/emergent` | no frontend caller | backend endpoint exists for raw emergent clusters | keep as debug/research endpoint, not user-facing product path |
| `/api/v2/events`, `/api/v2/events/clusters`, `/api/v2/acled` | no current frontend caller | backend exposed; conflict markers use `/api/v2/conflict-markers` instead | do not wire directly unless a dedicated event layer is designed |
| `/api/v2/heatmap` | no current frontend caller | older heat endpoint | current app uses `/api/v2/nodes` and optional `/api/v2/heat/countries` in an unmounted panel |
| NLP corrections/calibration endpoints | no current frontend caller | backend exists for review/calibration | keep out of public product until a controlled review UI is explicitly scoped |

## Contract Ownership

| Contract family | Canonical product owner | Secondary consumers | Notes |
|---|---|---|---|
| Dynamic narrative threads | `NarrativeThreads` + `ThreadFocusPanel` | Brief Watchlist, ThemeDetail dynamic branch | This is the main lane for anti-disinformation sensemaking: movement, source amplification, evidence, context/noise |
| Static theme/detail | `ThemeDetail`, `CountryThemePanel`, compare/export | Workspace, Search, SignalStream filter | Still required for old GDELT/static topic compatibility |
| Country/geography | Globe, CountryBrief, AnomalyPanel | Brief country filter, ChokepointPanel | Country heat is not proof of topic truth; it is evidence-density/geographic activity |
| Source concentration | SourceIntegrityPanel | SourceProfile, Workspace | Should become more important for disinformation framing; currently metric is concentration proxy |
| Public attention | AnomalyPanel, PublicAttentionPanel | ThemeDetail public-attention badges, Search | Useful for "attention vs evidence" comparisons |
| Workspace/dossier | InvestigationWorkspace | all pin-capable panels | Currently lacks a first-class living-thread pin type |

## Immediate Fix/Validation Queue

1. Verify local frontend fixes with a stable Node/browser pass:
   `ThemeDetail(dynamic-topic-*)` and `ThreadFocusPanel(dynamic-topic-*)`.
2. Replace `/brief` Watchlist snippet fetch for `dynamic-topic-*`:
   use `/api/v2/theme/dynamic-topic-*` samples instead of
   `/api/v2/signals?theme=dynamic-topic-*`.
3. Add a first-class workspace item type for living threads, or document that
   dynamic-topic pins must use `theme` until the workspace graph supports
   `thread`.
4. Decide whether `CorrelationMatrix` should remain static-theme based or gain
   a dynamic-thread mode. Do not mix both silently.
5. Keep Entity Focus cleanup as a model-quality lane: normalize raw/repeated
   entity strings before making dynamic-topic entities more central.
6. Either revive or delete unmounted discovery/placeholder/crisis surfaces in a
   later cleanup PR; do not route new data work into hidden panels by accident.

## Change Rule

Before adding or changing a backend contract, update this table first:

1. Which visible surface owns the contract?
2. Which secondary surfaces read it?
3. Is the identifier a static theme slug, dynamic-topic id, country code,
   person/entity string, source domain, or public-attention query?
4. Does the surface show evidence, movement, geography, source mix, or only
   volume?
5. What happens when the contract is missing, empty, slow, or filtered by a
   wider time range?
