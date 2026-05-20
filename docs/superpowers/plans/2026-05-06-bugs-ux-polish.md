# Bugs + UX Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix two backend bugs (#71 SQL LIMIT, #54 broken TRENDING), improve pin discoverability (#50), and add a first-load onboarding coachmark (#65). Also activate the pending Fly.io deploy.

**Architecture:** All changes are additive and independent — backend SQL fix, a frontend data-source swap, two frontend UX additions. No schema changes. No new dependencies.

**Tech Stack:** Python/FastAPI (backend), React/TypeScript + Vanilla CSS (frontend), localStorage for onboarding state, Lucide icons already installed.

---

## Task 1: Fly.io deploy — activate pending ON CONFLICT fix

**Files:**
- No code changes — just a deploy command.

- [ ] **Step 1: Deploy to Fly.io**

```bash
fly deploy
```

Expected output ends with: `✓ Machine ... is now running`, `Monitoring deployment... 1/1 machines running`.

- [ ] **Step 2: Verify health endpoint responds**

```bash
curl -s https://atlas-api-pedro.fly.dev/health | python3 -m json.tool | head -10
```

Expected: JSON with `"status": "ok"` and recent `last_ingest` timestamp.

- [ ] **Step 3: Commit nothing** — no code changed. Update STATUS.md only after verifying.

---

## Task 2: Fix #71 — SQL syntax error in `/api/v2/concept/{slug}`

**Root cause:** `array_agg(DISTINCT source ORDER BY source LIMIT 5)` is not valid PostgreSQL. `LIMIT` cannot appear inside an aggregate function. PostgreSQL raises `syntax error at or near "LIMIT"`. The fix is to use array slice notation `[1:5]` after the aggregation.

**Files:**
- Modify: `backend/app/main_v2.py:3535`

- [ ] **Step 1: Fix the SQL**

In `backend/app/main_v2.py`, find line 3535 and replace:

```python
                    array_agg(DISTINCT source ORDER BY source LIMIT 5) AS top_sources,
```

With:

```python
                    (array_agg(DISTINCT source ORDER BY source))[1:5] AS top_sources,
```

- [ ] **Step 2: Verify syntax locally**

```bash
cd backend && python3 -c "from app.main_v2 import app; print('OK')"
```

Expected: `OK` (no import errors).

- [ ] **Step 3: Smoke-test the endpoint**

```bash
curl -s "https://atlas-api-pedro.fly.dev/api/v2/concept/public-health?hours=48" | python3 -m json.tool | head -20
```

Expected: JSON with `"countries": [...]` array, no `"detail"` error key. If still seeing a SQL error, deploy first (Task 1) then re-test.

- [ ] **Step 4: Also test the slug that was failing**

```bash
curl -s "https://atlas-api-pedro.fly.dev/api/v2/concept/blood-diamonds?hours=168" | python3 -m json.tool | head -10
```

Expected: `"countries": [...]` (may be empty if no signals match, but no error).

- [ ] **Step 5: Commit**

```bash
git add backend/app/main_v2.py
git commit -m "fix(backend): replace array_agg LIMIT with array slice in concept endpoint (#71)

PostgreSQL does not support LIMIT inside aggregate functions.
array_agg(DISTINCT source ORDER BY source LIMIT 5) →
(array_agg(DISTINCT source ORDER BY source))[1:5]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 6: Close GitHub issue**

```bash
gh issue close 71 --comment "Fixed in this commit. array_agg LIMIT → [1:5] slice. Test: curl .../api/v2/concept/blood-diamonds?hours=168 now returns JSON without SQL error."
```

---

## Task 3: Fix #54 — Replace broken TRENDING with Wikipedia public attention

**Root cause:** Google Trends RSS (`trends.google.com/trending/rss`) blocks requests from Fly.io datacenter IPs. The `trends_v2` table is always empty. `AnomalyPanel.tsx` shows "No data yet" permanently.

**Fix:** Replace the TRENDING section with Wikipedia pageview data from `/api/v2/wiki/top`. The Wikimedia REST API (wikimedia.org/api/rest_v1) does NOT block datacenter IPs. The `wiki_pageviews_v2` table IS populated every 24h. Rename the section "PUBLIC ATTENTION" to reflect the data source.

**Files:**
- Modify: `frontend-v2/src/components/AnomalyPanel.tsx`

- [ ] **Step 1: Update the state type and fetch in AnomalyPanel**

In `frontend-v2/src/components/AnomalyPanel.tsx`, find lines 21–28 and replace:

```tsx
    const [trendingSearches, setTrendingSearches] = useState<{ keyword: string; country_count: number }[]>([])

    useEffect(() => {
        fetch('/api/v2/trends/search?hours=24&limit=10')
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (d?.trending) setTrendingSearches(d.trending) })
            .catch(() => {})
    }, [])
```

With:

```tsx
    const [wikiArticles, setWikiArticles] = useState<{ title: string; views: number; country_count?: number }[]>([])

    useEffect(() => {
        fetch('/api/v2/wiki/top?days=1&limit=10')
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (d?.articles?.length) setWikiArticles(d.articles) })
            .catch(() => {})
    }, [])
```

- [ ] **Step 2: Update the render section**

Find lines 143–160 (the TRENDING label and its scroll div) and replace:

```tsx
                    <div className="col-label" style={{ marginTop: themeAnomalies?.length ? '8px' : 0 }}>
                        TRENDING
                    </div>
                    <div className="col-scroll">
                        {trendingSearches.length === 0 ? (
                            <div className="ap-empty">No data yet</div>
                        ) : (
                            trendingSearches.map((t, i) => (
                                <div key={i} className="ap-row ap-row--trend">
                                    <span className="ap-rank">#{i + 1}</span>
                                    <span className="ap-keyword">{t.keyword}</span>
                                    {t.country_count > 1 && (
                                        <span className="ap-ctry-count">{t.country_count}</span>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
```

With:

```tsx
                    <div className="col-label" style={{ marginTop: themeAnomalies?.length ? '8px' : 0 }}
                        data-tip="Top Wikipedia articles by pageviews — what people are reading globally right now">
                        PUBLIC ATTENTION
                    </div>
                    <div className="col-scroll">
                        {wikiArticles.length === 0 ? (
                            <div className="ap-empty">Loading…</div>
                        ) : (
                            wikiArticles.map((a, i) => (
                                <div key={i} className="ap-row ap-row--trend">
                                    <span className="ap-rank">#{i + 1}</span>
                                    <span className="ap-keyword">{a.title.replace(/_/g, ' ')}</span>
                                    {a.country_count && a.country_count > 1 && (
                                        <span className="ap-ctry-count">{a.country_count}</span>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
```

- [ ] **Step 3: Build to verify no TypeScript errors**

```bash
cd frontend-v2 && npm run build 2>&1 | tail -8
```

Expected: `✓ built in Xs` with no TypeScript errors.

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/AnomalyPanel.tsx
git commit -m "fix(anomaly): replace broken TRENDING with Wikipedia public attention (#54)

Google Trends RSS blocks Fly.io datacenter IPs — trends_v2 is always empty.
Switched to /api/v2/wiki/top (Wikimedia REST API, not blocked) which
provides top Wikipedia articles by pageview. Renamed section 'PUBLIC ATTENTION'.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 5: Close GitHub issue**

```bash
gh issue close 54 --comment "Fixed: Google Trends RSS was blocked from Fly.io. Replaced with Wikimedia REST API (/api/v2/wiki/top). AnomalyPanel now shows top Wikipedia articles under 'PUBLIC ATTENTION'."
```

---

## Task 4: Fix #50 — Pin mechanism not discoverable

**Root cause:** The pin icon (📌) exists in CountryBrief, ThemeDetail, EntityPanel, and SignalStream headers, but first-time users never see those panels and don't know the workspace exists. The workspace toggle tab (folder icon, bottom-left) is subtle and has no affordance for new users.

**Fix:** Two small changes:
1. The workspace toggle tab pulses with a green ring when 0 items are pinned — draws the eye without being annoying.
2. The workspace empty state gets a more specific hint: instead of generic text, it references the pin icon by showing a small inline Pin icon.

**Files:**
- Modify: `frontend-v2/src/components/InvestigationWorkspace.tsx`
- Modify: `frontend-v2/src/components/InvestigationWorkspace.css`

- [ ] **Step 1: Add pulse animation to InvestigationWorkspace.css**

In `frontend-v2/src/components/InvestigationWorkspace.css`, append at the end of the file:

```css
/* Pulse ring on workspace tab when no items pinned */
@keyframes ws-tab-pulse {
    0%   { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.6); }
    70%  { box-shadow: 0 0 0 7px rgba(16, 185, 129, 0); }
    100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

.workspace-toggle-tab.pulse-hint {
    animation: ws-tab-pulse 2s ease-out infinite;
}
```

- [ ] **Step 2: Wire the pulse class to the toggle tab**

In `frontend-v2/src/components/InteractiveWorkspace.tsx`, find the toggle button (around line 135–143):

```tsx
            <button
                type="button"
                className={`workspace-toggle-tab ${isOpen ? 'open' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
                data-tip="Investigation Workspace"
                aria-label="Investigation Workspace"
            >
                <FolderKanban size={18} />
            </button>
```

Replace with:

```tsx
            <button
                type="button"
                className={`workspace-toggle-tab ${isOpen ? 'open' : ''} ${items.length === 0 && !isOpen ? 'pulse-hint' : ''}`}
                onClick={() => setIsOpen(!isOpen)}
                data-tip={items.length === 0 ? 'Investigation Workspace — pin countries, topics & people here' : 'Investigation Workspace'}
                aria-label="Investigation Workspace"
            >
                <FolderKanban size={18} />
            </button>
```

- [ ] **Step 3: Update the empty state to reference the Pin icon inline**

Find the workspace empty state text (around line 245–250):

```tsx
                        ) : filteredGraph.nodes.length === 0 ? (
                            <div className="workspace-empty workspace-empty-board">
                                <Filter size={24} />
                                <p>No nodes match this filter.</p>
                                <p>Clear the search box or re-enable node and relationship filters.</p>
                            </div>
                        ) : (
```

And the main empty state just above it:

```tsx
                        {items.length === 0 ? (
                            <div className="workspace-empty workspace-empty-board">
                                <FolderKanban size={24} />
                                <p>Your workspace is empty.</p>
                                <p>Open a country, topic, person, source, or signal, then click the pin icon to save it here.</p>
                            </div>
```

Replace the main empty state (items.length === 0) with:

```tsx
                        {items.length === 0 ? (
                            <div className="workspace-empty workspace-empty-board">
                                <FolderKanban size={24} />
                                <p>Your workspace is empty.</p>
                                <p style={{ display: 'flex', alignItems: 'center', gap: '4px', flexWrap: 'wrap', justifyContent: 'center' }}>
                                    Click any <Pin size={13} style={{ color: '#94a3b8', flexShrink: 0 }} /> icon inside a country, topic, or person panel to add it here.
                                </p>
                            </div>
```

Note: `Pin` is already imported from `lucide-react` at the top of the file.

- [ ] **Step 4: Build to verify**

```bash
cd frontend-v2 && npm run build 2>&1 | tail -8
```

Expected: `✓ built in Xs`.

- [ ] **Step 5: Commit**

```bash
git add frontend-v2/src/components/InteractiveWorkspace.tsx frontend-v2/src/components/InvestigationWorkspace.css
git commit -m "fix(ux): pulse hint on workspace tab + inline Pin icon in empty state (#50)

Workspace toggle tab pulses green when nothing is pinned, stopping
when the user opens it or adds their first item. Empty board state now
shows an inline Pin icon so users know exactly what to look for.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 6: Close GitHub issue**

```bash
gh issue close 50 --comment "Shipped: workspace tab pulses when empty (stops on open/first pin). Empty state now shows inline Pin icon as a visual reference."
```

---

## Task 5: Add #65 — First-load onboarding coachmark

**Goal:** Show a 3-step overlay on first visit that teaches the core mental model: (1) click the map to explore a country, (2) Narrative Threads shows macro trends, (3) pin items to build an investigation. Stored in `localStorage` — never shown twice.

**Files:**
- Create: `frontend-v2/src/components/OnboardingCoachmark.tsx`
- Create: `frontend-v2/src/components/OnboardingCoachmark.css`
- Modify: `frontend-v2/src/App.tsx` — import and render `<OnboardingCoachmark />`

### Sub-task 5a: CSS

- [ ] **Step 1: Create `frontend-v2/src/components/OnboardingCoachmark.css`**

```css
.onboarding-overlay {
    position: fixed;
    inset: 0;
    background: rgba(4, 10, 20, 0.82);
    backdrop-filter: blur(3px);
    z-index: 9000;
    display: flex;
    align-items: center;
    justify-content: center;
}

.onboarding-card {
    background: #0c1828;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 32px 36px;
    max-width: 420px;
    width: calc(100vw - 48px);
    box-shadow: 0 24px 64px rgba(0,0,0,0.6);
}

.onboarding-step-indicator {
    display: flex;
    gap: 6px;
    margin-bottom: 24px;
}

.onboarding-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: rgba(255,255,255,0.2);
    transition: background 0.2s;
}

.onboarding-dot.active {
    background: #10b981;
    width: 20px;
    border-radius: 3px;
}

.onboarding-icon {
    font-size: 28px;
    margin-bottom: 12px;
}

.onboarding-title {
    font-size: 15px;
    font-weight: 700;
    color: #e2e8f0;
    margin: 0 0 8px;
    font-family: 'Space Grotesk', monospace;
    letter-spacing: 0.03em;
}

.onboarding-body {
    font-size: 13px;
    color: #94a3b8;
    line-height: 1.6;
    margin: 0 0 28px;
}

.onboarding-body strong {
    color: #cbd5e1;
}

.onboarding-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.onboarding-skip {
    background: none;
    border: none;
    color: #475569;
    font-size: 12px;
    cursor: pointer;
    padding: 0;
}

.onboarding-skip:hover {
    color: #94a3b8;
}

.onboarding-next {
    background: #10b981;
    border: none;
    color: #021a10;
    font-size: 13px;
    font-weight: 700;
    padding: 8px 20px;
    border-radius: 6px;
    cursor: pointer;
    font-family: 'Space Grotesk', monospace;
    letter-spacing: 0.04em;
    transition: background 0.15s;
}

.onboarding-next:hover {
    background: #34d399;
}
```

### Sub-task 5b: Component

- [ ] **Step 2: Create `frontend-v2/src/components/OnboardingCoachmark.tsx`**

```tsx
import { useState } from 'react'
import './OnboardingCoachmark.css'

const STORAGE_KEY = 'atlas_onboarding_v1'

const STEPS = [
    {
        icon: '🌍',
        title: 'Click any country on the map',
        body: (
            <>
                Tap a country to open its <strong>Coverage Brief</strong> — top narratives,
                sentiment tone, key people, and signal volume. This is your entry point
                into what any country is talking about right now.
            </>
        ),
    },
    {
        icon: '📈',
        title: 'Narrative Threads shows the big picture',
        body: (
            <>
                The right panel tracks <strong>global topic narratives</strong> — not
                individual articles, but the patterns that emerge across thousands of
                signals. Watch the trend arrows and spread bars to see what's accelerating
                and how far it's reached.
            </>
        ),
    },
    {
        icon: '📌',
        title: 'Pin items to build your investigation',
        body: (
            <>
                Every country, topic, or person panel has a <strong>pin icon</strong> in
                its header. Pinned items appear in the <strong>Workspace Board</strong>
                (folder icon, bottom-left) as a visual relationship graph you can explore
                and annotate.
            </>
        ),
    },
]

export function OnboardingCoachmark() {
    const [step, setStep] = useState(0)
    const [visible, setVisible] = useState(() => {
        try {
            return !localStorage.getItem(STORAGE_KEY)
        } catch {
            return false
        }
    })

    if (!visible) return null

    const dismiss = () => {
        try { localStorage.setItem(STORAGE_KEY, '1') } catch { /* noop */ }
        setVisible(false)
    }

    const next = () => {
        if (step < STEPS.length - 1) {
            setStep(s => s + 1)
        } else {
            dismiss()
        }
    }

    const current = STEPS[step]

    return (
        <div className="onboarding-overlay" onClick={dismiss}>
            <div className="onboarding-card" onClick={e => e.stopPropagation()}>
                <div className="onboarding-step-indicator">
                    {STEPS.map((_, i) => (
                        <div key={i} className={`onboarding-dot ${i === step ? 'active' : ''}`} />
                    ))}
                </div>
                <div className="onboarding-icon">{current.icon}</div>
                <p className="onboarding-title">{current.title}</p>
                <p className="onboarding-body">{current.body}</p>
                <div className="onboarding-actions">
                    <button className="onboarding-skip" onClick={dismiss}>
                        Skip intro
                    </button>
                    <button className="onboarding-next" onClick={next}>
                        {step < STEPS.length - 1 ? 'Next →' : 'Got it'}
                    </button>
                </div>
            </div>
        </div>
    )
}
```

### Sub-task 5c: Wire into App

- [ ] **Step 3: Import and render in `frontend-v2/src/App.tsx`**

Find the existing imports block (near line 40–43) and add:

```tsx
import { OnboardingCoachmark } from './components/OnboardingCoachmark'
```

Then find the final closing `</div>` of the main return (just before `</WorkspaceProvider>` or the last `</FocusProvider>`) and add `<OnboardingCoachmark />` just inside it. Look for the very end of the JSX return — find this pattern:

```tsx
      <PanelErrorBoundary panelName="WORKSPACE">
```

and after the WorkspaceProvider closing tag or the outermost wrapping div, render:

```tsx
      <OnboardingCoachmark />
```

The exact location: search for the closing of the outer div that wraps everything. Add `<OnboardingCoachmark />` as the last child before `</div>` of the outermost wrapper in the JSX return of `AppInner`. It renders on top of everything via `position: fixed` so placement doesn't affect layout.

- [ ] **Step 4: Build to verify**

```bash
cd frontend-v2 && npm run build 2>&1 | tail -8
```

Expected: `✓ built in Xs`.

- [ ] **Step 5: Manual test**

1. Open browser DevTools → Application → Local Storage → delete `atlas_onboarding_v1` key
2. Reload `/app` — coachmark should appear centered over the map
3. Click Next → step indicator advances, content changes
4. Click "Got it" on step 3 → overlay dismisses, localStorage key is set
5. Reload → coachmark does NOT appear again

- [ ] **Step 6: Commit**

```bash
git add frontend-v2/src/components/OnboardingCoachmark.tsx frontend-v2/src/components/OnboardingCoachmark.css frontend-v2/src/App.tsx
git commit -m "feat(ux): first-load onboarding coachmark — 3-step mental model (#65)

3-step overlay shown once per browser (localStorage key atlas_onboarding_v1).
Steps: map → narrative threads → pin to workspace. Click outside or
Skip to dismiss at any point. Stops after 'Got it' on step 3.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

- [ ] **Step 7: Close GitHub issue**

```bash
gh issue close 65 --comment "Shipped: OnboardingCoachmark.tsx — 3-step overlay (map, threads, pin). localStorage-gated, never shown twice. Click outside or Skip to dismiss early."
```

---

## Final: Update STATUS.md

After all tasks are done:

- [ ] **Update STATUS.md** — move #50, #54, #65, #71 to closed. Update "Changes this session" block. Update "Recommended next order" to #69 (Spanish search), #68 (source classification), #62 (ESLint debt).

```bash
git add STATUS.md
git commit -m "docs(status): session 7 completions — #50 #54 #65 #71 closed

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Self-Review

**Spec coverage check:**
- ✅ fly deploy (Task 1)
- ✅ #71 SQL LIMIT bug (Task 2) — exact line 3535 identified and fixed
- ✅ #54 Trending broken (Task 3) — root cause (IP block) confirmed, replaced with wiki data
- ✅ #50 Pin not discoverable (Task 4) — pulse on tab + inline icon in empty state
- ✅ #65 Onboarding coachmark (Task 5) — full component with CSS

**Placeholder scan:** No TBDs. All code blocks complete.

**Type consistency:**
- `wikiArticles` typed as `{ title: string; views: number; country_count?: number }[]` matches the `/api/v2/wiki/top` response shape (`r['article_title']` → `"title"`, `r['views']` → `"views"`)
- `OnboardingCoachmark` exported as named export, imported as named import in App.tsx
- `pulse-hint` CSS class used exactly as defined in the CSS keyframe rule
