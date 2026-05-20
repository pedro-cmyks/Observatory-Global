# Public Attention Enrichment Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to execute this plan.

**Goal:** Enrich the existing Atlas investigation panels with public-attention context without creating a new standalone product surface. Public Attention should behave as the people-side signal layer that complements media signals, preserves context when the analyst pivots, and feeds the Workspace trail.

**Architecture:** Keep the current React/Vite shell, existing `/api/v2` contracts, lazy graph workspace, and panel routing. Implement this as a small frontend enrichment layer using existing backend data: unified search, Trends search/match, Wiki top/match, country signals, and workspace session tracking.

**Tech Stack:** React 18, TypeScript, Vite, Vitest, existing CSS modules/files, FastAPI v2 APIs.

---

### Task 1: Add Public Attention helper utilities and tests

**Files:**
- `frontend-v2/src/lib/publicAttention.ts`
- `frontend-v2/src/lib/publicAttention.test.ts`

**Steps:**
1. Extend the current Wiki top URL helper to accept optional `countryCode`.
2. Add a Google Trends URL helper for country/global attention rows.
3. Add a country narrative helper that turns country metrics, top themes, public searches, and Wiki articles into a short readable analyst paragraph.
4. Add Vitest coverage before implementation for country-specific Wiki/Trends URLs and the country narrative copy.

**Acceptance Criteria:**
- Country-specific Wiki URLs include `country_code=XX`.
- Trends URLs include `country_code=XX` when scoped.
- Country narrative mentions the country, strongest media theme, and public-attention proxy when present.

---

### Task 2: Preserve attention context across pivots

**Files:**
- `frontend-v2/src/App.tsx`
- `frontend-v2/src/components/PublicAttentionPanel.tsx`
- `frontend-v2/src/components/ThemeDetail.tsx`

**Steps:**
1. Extend `SelectedTheme` with an optional `originAttention`.
2. Change `handleThemeSelect` to accept optional attention context while keeping existing country-scoped pivots working.
3. When a Public Attention theme chip is clicked, pass the originating attention item into the theme panel.
4. When related investigations/topics are clicked from a context-enriched theme panel, preserve that attention origin for the next theme.
5. Track the enriched theme visit in Workspace metadata and URL params where practical.

**Acceptance Criteria:**
- Clicking `ShinyHunters -> Cyber Attack` opens Cyber Attack with visible `opened from Public Attention: ShinyHunters` context.
- Related topic clicks from that panel keep the public-attention origin instead of becoming a generic global pivot.
- Existing theme/country/source/person pivots still work.

---

### Task 3: Enrich the Public Attention and Theme panels

**Files:**
- `frontend-v2/src/components/PublicAttentionPanel.tsx`
- `frontend-v2/src/components/PublicAttentionPanel.css`
- `frontend-v2/src/components/ThemeDetail.tsx`
- `frontend-v2/src/components/ThemeDetail.css`

**Steps:**
1. Make Public Attention communicate its role explicitly: public attention versus media coverage.
2. Add a compact “media contrast” band using current Wiki views/countries/media matches.
3. Make theme chips contextual CTAs: “open narrative thread with this attention context.”
4. Add an origin-attention block in ThemeDetail that shows the public topic, Wiki views/country spread, matching headlines, and how it is being absorbed into media themes.
5. Keep layout dense and consistent with the existing premium console language.

**Acceptance Criteria:**
- PublicAttentionPanel is still scrollable and not externally navigating on item clicks.
- ThemeDetail shows a Public Attention lane even when Trends/Wiki theme match is sparse, if opened from a public-attention item.
- All touched tooltips use `data-tip`.

---

### Task 4: Enrich CountryBrief with public-attention proxies

**Files:**
- `frontend-v2/src/components/CountryBrief.tsx`
- `frontend-v2/src/components/CountryBrief.css`

**Steps:**
1. Fetch country-scoped `/api/v2/wiki/top` and `/api/v2/trends/search` alongside existing node/indicator/signal calls.
2. Store a small `publicAttention` object in `BriefData`.
3. Replace the thin connection sentence with a richer country-analysis paragraph using the helper from Task 1.
4. Add a compact Public Attention section showing Google searches and Wiki reads for the country/language-edition proxy.
5. Keep caveat language honest: Wikipedia is language/country-edition pageview proxy, not a perfect population-normalized opinion measure.

**Acceptance Criteria:**
- Country panel reads more like the Brief while staying in-panel.
- Country Public Attention rows are clickable where they have a natural Atlas action, or clearly presented as evidence otherwise.
- No new backend endpoints are required.

---

### Task 5: Add Workspace Trail as a first-class workspace view

**Files:**
- `frontend-v2/src/components/InteractiveWorkspace.tsx`
- `frontend-v2/src/components/InvestigationWorkspace.css`

**Steps:**
1. Use existing `sessionItems` from `WorkspaceContext`.
2. Add a Graph/Trail/Notes mode switch inside the Workspace side panel.
3. Render the session trail as chronological analyst pivots with open/pin affordances.
4. Keep pinned notes available and export unchanged.

**Acceptance Criteria:**
- Workspace has a visible Trail surface, not a separate global panel.
- Trail entries open the corresponding Atlas view.
- Existing pinned item notes continue to work.

---

### Task 6: Teach the first-run walkthrough about Anomaly/Public Attention

**Files:**
- `frontend-v2/src/components/OnboardingCoachmark.tsx`
- `frontend-v2/src/App.tsx`

**Steps:**
1. Add a tour step targeting the lower anomaly/public-attention panel.
2. Add a stable `data-tour` target in the app layout.
3. Explain that Anomaly Alert surfaces unusual movement, and Public Attention is the people-side counterpoint to Signal Stream.

**Acceptance Criteria:**
- New users are told why the lower panel matters.
- The existing tour still progresses and can open Brief/Workspace.

---

### Task 7: Verify

**Commands:**
- `cd frontend-v2 && npm run test`
- `cd frontend-v2 && npm run build`
- `cd frontend-v2 && npm run lint`

**Manual QA:**
1. Open `/app`, click Public Attention item, click a related theme.
2. Confirm ThemeDetail keeps public-attention context.
3. Open a country panel and confirm public-attention rows appear or degrade gracefully.
4. Open Workspace and confirm Trail entries are visible and navigable.
5. Run the tour and confirm the anomaly/public-attention step targets a visible panel.

