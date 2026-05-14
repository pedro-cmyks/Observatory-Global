# Atlas Guided UX System Implementation Plan

> **For Pedro:** This plan executes the approved guided UX system spec. It keeps the existing React/Vite app, API contracts, and panel workflows intact while making the landing/brief/app/docs/workspace path easier to understand and use.

**Goal:** Make Atlas easier to enter and explain by connecting Landing -> Brief -> App -> Workspace -> Docs, with panel-level help and a bounded, clearer workspace experience.

**Architecture:** Frontend-only first pass. Use existing routes (`/`, `/brief`, `/app`, `/docs`), existing URL query parameters (`theme`, `country`, `attention`), existing onboarding storage key, existing workspace graph data, and no backend endpoint changes.

**Tech Stack:** React, TypeScript, Vite, React Router, lucide-react, react-force-graph-2d, existing CSS files.

## Tasks

### 1. Landing Copy And IA

**Files:**
- `frontend-v2/src/pages/Landing.tsx`

**Changes:**
- Clarify Atlas as public narrative intelligence/global observatory, not a GDELT wrapper.
- Make Brief the recommended entry while keeping direct Console access.
- Surface Docs as a first-class path from the hero.

### 2. Brief Navigation And Context Links

**Files:**
- `frontend-v2/src/pages/BriefNewspaper.tsx`
- `frontend-v2/src/pages/BriefNewspaper.css`

**Changes:**
- Add direct Home and Console controls in the masthead.
- Mark all Brief-to-App links with `entry=brief`.
- Make theme cards act as large Atlas entry targets while preserving country-pill clicks.
- Keep country/theme/range query behavior intact.

### 3. Onboarding Entry Context

**Files:**
- `frontend-v2/src/components/OnboardingCoachmark.tsx`
- `frontend-v2/src/components/OnboardingCoachmark.css`
- `frontend-v2/src/App.tsx`

**Changes:**
- Add optional entry context copy when the user arrives from Brief.
- Preserve first-run localStorage gating and manual Tour button behavior.
- Keep existing coachmark steps and new Anomaly/Public Attention step.

### 4. Panel Help Drawer

**Files:**
- `frontend-v2/src/components/PanelHelpDrawer.tsx`
- `frontend-v2/src/components/PanelHelpDrawer.css`
- `frontend-v2/src/App.tsx`

**Changes:**
- Replace the small one-paragraph `?` popup with a reusable help drawer/modal.
- Add concise panel explanations for Globe, Signal Stream, Narrative Threads, Anomaly/Public Attention, and Source Integrity.
- Link drawer content to deeper Docs anchors.

### 5. Docs Panel Guide And Methodology

**Files:**
- `frontend-v2/src/pages/Docs.tsx`
- `frontend-v2/src/pages/Docs.css`

**Changes:**
- Add Panel Guide navigation and sections.
- Add methodology anchors for coverage bias, volume normalization, sentiment, and public attention.
- Keep existing data-source and math documentation.

### 6. Workspace Bounds And Trail/Pinned Distinction

**Files:**
- `frontend-v2/src/components/InteractiveWorkspace.tsx`
- `frontend-v2/src/components/InvestigationWorkspace.css`

**Changes:**
- Ensure workspace stays inside the viewport with reachable close/actions.
- Make Trail graph visually distinct from Pinned evidence graph.
- Increase spacing/repulsion to reduce node overlap.
- Keep graph lazy-loaded through `InvestigationWorkspace`.

### 7. Verification

**Commands:**
- `cd frontend-v2 && npm run build`
- `cd frontend-v2 && npm run test`
- `cd frontend-v2 && npm run lint`

**Manual QA:**
- Landing: Brief, Console, Docs paths.
- Brief: Home, Console, country search, theme card click, country pill click.
- App: first-run/manual Tour, panel help drawer, docs links.
- Workspace: open/close bounds, Trail vs Pinned tabs, graph readability.
