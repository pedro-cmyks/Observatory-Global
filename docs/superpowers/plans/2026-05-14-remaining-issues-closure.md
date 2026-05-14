# Remaining Issues Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the final open GitHub issues after session 16 while keeping production aligned with `v3-intel-layer`.

**Architecture:** Treat the remaining work as three lanes: production branch synchronization, closable product issues, and blocked/non-code issues. Frontend work stays in `frontend-v2`; backend/data work stays in `backend/app/services` and raw SQL migrations only if needed.

**Tech Stack:** React + Vite, FastAPI, Supabase Postgres, Fly.io, Vercel, GitHub Issues.

---

## Current State

- Active branch: `v3-intel-layer`.
- Local branch is 10 commits ahead of `origin/v3-intel-layer`.
- GitHub open issues: #82, #61, #105, #70, #46, #106.
- #46 is externally blocked by ACLED API access.
- #106 is blocked by designer-provided SVG assets.
- #105 has a candidate branch: `claude/competent-maxwell-4eb03c`, commit `0b801d3`, touching `backend/app/services/ingest_rss.py`.

## Execution Order

### Task 1: Sync production branch state

**Files:**
- Verify: repository root

- [ ] **Step 1: Confirm clean local state**

Run:

```bash
git status --short --branch
```

Expected:

```text
## v3-intel-layer...origin/v3-intel-layer [ahead 10]
```

No uncommitted files should be listed.

- [ ] **Step 2: Verify frontend build before pushing**

Run:

```bash
cd frontend-v2 && npm run build
```

Expected: Vite build succeeds with zero TypeScript errors.

- [ ] **Step 3: Push `v3-intel-layer`**

Run:

```bash
git push origin v3-intel-layer
```

Expected: remote `origin/v3-intel-layer` advances to local `HEAD`.

- [ ] **Step 4: Confirm GitHub sees the new head**

Run:

```bash
git fetch origin v3-intel-layer
git rev-parse HEAD
git rev-parse origin/v3-intel-layer
```

Expected: both hashes match.

### Task 2: Close #82 by integrating temporal graph snapshots with Workspace

**Files:**
- Modify: `frontend-v2/src/components/TemporalNarrativeGraph.tsx`
- Modify: `frontend-v2/src/components/ThemeDetail.tsx`
- Modify: `frontend-v2/src/contexts/WorkspaceContext.tsx`
- Modify: `frontend-v2/src/lib/workspaceGraph.ts`
- Test: `frontend-v2/src/lib/workspaceGraph.test.ts` or nearest existing graph test

- [ ] **Step 1: Define the workspace item shape**

Add a minimal temporal snapshot item that records theme, bucket label, countries, sources, people, and signal count. Keep it serializable for localStorage and compatible with existing pinned-item export.

- [ ] **Step 2: Add a graph test for temporal snapshot nodes**

Create or extend a workspace graph test so a pinned temporal snapshot produces:

- one pinned snapshot node
- one linked theme node
- country/source/person relationship nodes from the snapshot payload
- stable link kinds that can be filtered in the Workspace UI

- [ ] **Step 3: Add the pin action in `TemporalNarrativeGraph`**

Expose an action on the selected bucket that pins the current bucket snapshot to Workspace. Use `data-tip`, not `title`, for tooltip text.

- [ ] **Step 4: Wire `ThemeDetail` to pass the snapshot handler**

Use the existing `useWorkspace()` path in `ThemeDetail` so the graph can pin a selected temporal bucket and open the workspace without importing the heavy workspace canvas directly.

- [ ] **Step 5: Run focused and full frontend verification**

Run:

```bash
cd frontend-v2 && npm run test -- src/lib/workspaceGraph.test.ts
cd frontend-v2 && npm run build
```

Expected: tests and Vite build pass.

- [ ] **Step 6: Close issue #82**

Comment with commits, behavior, and verification, then close:

```bash
gh issue close 82 --repo pedro-cmyks/Observatory-Global --comment "Implemented temporal graph bucket snapshots into Workspace. Verification: npm run test for workspace graph and npm run build passed."
```

### Task 3: Close #61 with a reusable compare dashboard shell

**Files:**
- Create: `frontend-v2/src/components/CompareDashboard.tsx`
- Create: `frontend-v2/src/components/CompareDashboard.css`
- Modify: `frontend-v2/src/App.tsx`
- Modify: `frontend-v2/src/components/ThemeDetail.tsx`
- Modify: `frontend-v2/src/components/EntityPanel.tsx`

- [ ] **Step 1: Preserve existing compare entry points**

Keep `ThemeCompare` and `PersonCompare` working until `CompareDashboard` covers both paths. Do not remove existing compare code in the first pass.

- [ ] **Step 2: Build a dedicated overlay shell**

Create `CompareDashboard` with a compact 50/50 layout, shared header, close button, entity labels, and reusable metric row slots. Match the dark Atlas console style and avoid cards inside cards.

- [ ] **Step 3: Wire theme-vs-theme mode**

Use existing theme detail data first. Show signal count, sentiment, top countries, top sources, and narrative drift summary for both sides.

- [ ] **Step 4: Wire person-vs-person mode**

Use existing entity panel/focus data first. Show signal count, countries, related themes, top sources, and sentiment for both sides.

- [ ] **Step 5: Keep graph-driven comparison as a follow-up affordance**

From #82 temporal graph selection, expose "Compare selected" only when two comparable nodes or buckets are selected. If this is not implemented in the same pass, document it as a follow-up comment before closing #61.

- [ ] **Step 6: Verify**

Run:

```bash
cd frontend-v2 && npm run build
```

Expected: Vite build succeeds with zero TypeScript errors.

### Task 4: Close #105 by safely bringing RSS feed expansion forward

**Files:**
- Modify: `backend/app/services/ingest_rss.py`
- Test: existing backend RSS tests if present, otherwise `python3 -m py_compile backend/app/services/ingest_rss.py`

- [ ] **Step 1: Inspect candidate branch as a patch, not a merge**

Run:

```bash
git show claude/competent-maxwell-4eb03c -- backend/app/services/ingest_rss.py
```

Expected: only curated feed additions and local RSS logic changes.

- [ ] **Step 2: Apply only the RSS service change**

Use cherry-pick with no commit, or manually port the feed list into current `v3-intel-layer`. Do not merge the candidate branch because it diverges from the current router-split architecture.

- [ ] **Step 3: Validate ingestion metadata convention**

Every inserted RSS row must still set `source_family`, `source_lang`, `geo_confidence`, `attribution_method`, and `is_state_media`.

- [ ] **Step 4: Verify Python syntax**

Run:

```bash
python3 -m py_compile backend/app/services/ingest_rss.py
```

Expected: command exits 0.

- [ ] **Step 5: Close issue #105**

Comment with source count, regions covered, and verification.

### Task 5: Close or re-scope #70 after a frontend-only hierarchy pass

**Files:**
- Create: `frontend-v2/src/lib/themeHierarchy.ts`
- Modify: `frontend-v2/src/components/EntityPanel.tsx`
- Modify: `frontend-v2/src/components/NarrativeThreads.tsx`

- [ ] **Step 1: Build a top-theme cluster map**

Create a manually curated hierarchy for the highest-volume GDELT codes already visible in Atlas. Include an `Other` fallback for unknown codes.

- [ ] **Step 2: Group EntityPanel related topics**

Render related topic chips under cluster labels and hide empty groups.

- [ ] **Step 3: Group NarrativeThreads only if it does not reduce scan speed**

If grouping makes the list harder to scan, keep NarrativeThreads flat and close #70 as Phase 1 research + EntityPanel hierarchy only, with a follow-up for API-level grouping.

- [ ] **Step 4: Verify**

Run:

```bash
cd frontend-v2 && npm run build
```

Expected: Vite build succeeds.

### Task 6: Resolve blocked issues without fake implementation

**Issues:**
- #46 ACLED access
- #106 octopus mascot

- [ ] **Step 1: #46**

If ACLED credentials are not available, leave issue open with `blocked` label or close only if the product decision is "Coming Soon until access exists." Do not implement fake ACLED data.

- [ ] **Step 2: #106**

Keep blocked until SVG assets exist. Do not generate a CSS-only mascot approximation; current issue comment explicitly says that would hurt brand quality.

## Main Branch Recommendation

Do not merge to `main` until the final closable issues are closed and production is verified from `origin/v3-intel-layer`.

After that, use one controlled branch migration:

1. Protect or archive the old `main` state with a tag.
2. Fast-forward or reset `main` to `v3-intel-layer` only after confirming no production service still depends on old `main`.
3. Repoint Vercel and Fly to `main`.
4. Keep `v3-intel-layer` as a historical branch, not the active production branch.

