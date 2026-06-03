# Workbench Early-Access Waitlist Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the static `mailto:` Workbench preview overlay with an interactive, Supabase-backed early-access waitlist that captures `email` + `use_case`, shows a real waitlist count, and keeps a separate support CTA.

**Architecture:** New RLS-locked `workbench_waitlist` table. A new FastAPI router (`app/routers/waitlist.py`) exposes `POST /api/v2/waitlist` (validate, honeypot, soft in-process per-IP rate limit, idempotent insert) and `GET /api/v2/waitlist/count` (aggregate only). The frontend gets a small lib (`lib/waitlist.ts`) and a focused component (`WorkbenchWaitlistGate.tsx`) that replaces the inline overlay block in `InteractiveWorkspace.tsx`. Frontend talks to the backend via relative `/api/v2/...` fetches — no `supabase-js`, no anon key.

**Tech Stack:** Python 3.12 / FastAPI / asyncpg / Postgres (Supabase); React + TypeScript + Vite; vanilla CSS.

**Spec:** `docs/superpowers/specs/2026-06-03-workbench-waitlist-gate-design.md`

---

## File Structure

- Create: `backend/migrations/051_workbench_waitlist.sql` — table + RLS.
- Create: `backend/app/routers/waitlist.py` — router, validation helper, rate limit, endpoints.
- Modify: `backend/app/main_v2.py` — register the router (one `include_router` line + import).
- Create: `backend/tests/test_waitlist_email_validation.py` — unit test for the pure validator.
- Create: `backend/tests/test_waitlist_router_shape.py` — source-string guardrails (matches existing `test_emergent_router_shape.py` style).
- Create: `frontend-v2/src/lib/waitlist.ts` — `postWaitlist`, `getWaitlistCount`.
- Create: `frontend-v2/src/components/WorkbenchWaitlistGate.tsx` — the interactive overlay.
- Modify: `frontend-v2/src/components/InteractiveWorkspace.tsx` — replace the inline overlay JSX block (lines ~676–711) with `<WorkbenchWaitlistGate ... />`.
- Modify: `frontend-v2/src/components/InvestigationWorkspace.css` — add form/state styles under the existing `workspace-preview-*` namespace.

---

## Task 1: Database migration

**Files:**
- Create: `backend/migrations/051_workbench_waitlist.sql`

- [ ] **Step 1: Write the migration file**

```sql
-- Migration 051: workbench_waitlist (public MVP early-access gate)
--
-- Captures early-access interest from the gated Workbench preview overlay.
-- Minimal fields: email + optional use_case. referrer is server-derived.
-- RLS locked: only the backend service role reads/writes; emails are never
-- exposed by any public GET (only an aggregate count).

CREATE TABLE IF NOT EXISTS workbench_waitlist (
    id          BIGSERIAL PRIMARY KEY,
    email       TEXT NOT NULL,
    use_case    TEXT NULL,
    referrer    TEXT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT workbench_waitlist_email_unique UNIQUE (email)
);

ALTER TABLE workbench_waitlist ENABLE ROW LEVEL SECURITY;
-- No public policies created on purpose: only the service role bypasses RLS.
```

- [ ] **Step 2: Apply via Supabase MCP**

Apply with the Supabase MCP `apply_migration` tool, name `051_workbench_waitlist`, using the SQL above. Then verify:

Run (MCP `execute_sql`):
```sql
SELECT to_regclass('workbench_waitlist') AS tbl,
       (SELECT relrowsecurity FROM pg_class WHERE oid = 'workbench_waitlist'::regclass) AS rls;
```
Expected: `tbl = workbench_waitlist`, `rls = true`.

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/051_workbench_waitlist.sql
git commit -m "feat(waitlist): add workbench_waitlist table (migration 051)"
```

---

## Task 2: Backend email validator (pure function, TDD)

**Files:**
- Create: `backend/app/routers/waitlist.py` (validator only in this task)
- Test: `backend/tests/test_waitlist_email_validation.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_waitlist_email_validation.py
from app.routers.waitlist import normalize_email, is_valid_email


def test_normalize_trims_and_lowercases():
    assert normalize_email("  A@B.COM ") == "a@b.com"


def test_valid_simple_email():
    assert is_valid_email("user@example.com") is True


def test_valid_after_normalize():
    assert is_valid_email(normalize_email("  User@Example.Com ")) is True


def test_rejects_no_at():
    assert is_valid_email("userexample.com") is False


def test_rejects_no_domain_dot():
    assert is_valid_email("user@example") is False


def test_rejects_spaces():
    assert is_valid_email("user @example.com") is False


def test_rejects_empty():
    assert is_valid_email("") is False


def test_rejects_too_long():
    assert is_valid_email("a" * 320 + "@x.com") is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_waitlist_email_validation.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.routers.waitlist'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/routers/waitlist.py
"""
Workbench early-access waitlist (public MVP launch gate).

  POST /api/v2/waitlist         — capture email + optional use_case.
  GET  /api/v2/waitlist/count   — aggregate waitlist size (no emails).

Emails are never returned by any GET. Bot defense is a hidden honeypot
field plus a soft in-process per-IP rate limit (the API runs as a single
Fly app machine, so in-process state is sufficient for the MVP).
"""
from __future__ import annotations

import re

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MAX_EMAIL_LEN = 320


def normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def is_valid_email(email: str) -> bool:
    if not email or len(email) > _MAX_EMAIL_LEN:
        return False
    return _EMAIL_RE.match(email) is not None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_waitlist_email_validation.py -v`
Expected: PASS (8 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/waitlist.py backend/tests/test_waitlist_email_validation.py
git commit -m "feat(waitlist): email normalize + validate helpers (TDD)"
```

---

## Task 3: Backend endpoints + rate limit + router registration

**Files:**
- Modify: `backend/app/routers/waitlist.py`
- Modify: `backend/app/main_v2.py` (import + `include_router`)
- Test: `backend/tests/test_waitlist_router_shape.py`

- [ ] **Step 1: Write the failing source-guardrail test**

```python
# backend/tests/test_waitlist_router_shape.py
"""Source-string guardrails for the /api/v2/waitlist router, matching the
existing test_emergent_router_shape.py style (no live DB)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WAITLIST_ROUTER = ROOT / "app" / "routers" / "waitlist.py"
MAIN = ROOT / "app" / "main_v2.py"


def _src() -> str:
    return WAITLIST_ROUTER.read_text(encoding="utf-8")


def test_post_endpoint_registered():
    assert '@router.post("/api/v2/waitlist")' in _src()


def test_count_endpoint_registered():
    assert '@router.get("/api/v2/waitlist/count")' in _src()


def test_honeypot_field_present():
    # hidden "company" field; non-empty means bot -> silent success, no write
    src = _src()
    assert "company" in src
    assert "honeypot" in src.lower()


def test_idempotent_insert():
    assert "ON CONFLICT" in _src()
    assert "DO NOTHING" in _src()


def test_count_is_aggregate_only():
    src = _src()
    assert "COUNT(*)" in src
    # the count endpoint must never select the email column
    assert "SELECT email" not in src


def test_rate_limited_status_429():
    assert "429" in _src()


def test_table_guarded_with_to_regclass():
    assert "to_regclass('workbench_waitlist')" in _src()


def test_router_registered_in_main():
    main = MAIN.read_text(encoding="utf-8")
    assert "from app.routers import" in main or "import waitlist" in main
    assert "app.include_router(waitlist.router)" in main
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_waitlist_router_shape.py -v`
Expected: FAIL (assertions missing — endpoints/registration not written yet).

- [ ] **Step 3: Append endpoints + rate limit to `waitlist.py`**

Append below the validator in `backend/app/routers/waitlist.py`:

```python
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app import db

logger = logging.getLogger(__name__)
router = APIRouter()

# Soft in-process per-IP rate limit. Single Fly app machine -> module state is
# enough for the MVP. Not durable across restarts; that is acceptable here.
_RATE_WINDOW_SECONDS = 600  # 10 minutes
_RATE_MAX = 5
_rate_log: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_limited(ip: str) -> bool:
    now = time.monotonic()
    hits = [t for t in _rate_log.get(ip, []) if now - t < _RATE_WINDOW_SECONDS]
    if len(hits) >= _RATE_MAX:
        _rate_log[ip] = hits
        return True
    hits.append(now)
    _rate_log[ip] = hits
    return False


class WaitlistPayload(BaseModel):
    email: str = Field(..., max_length=_MAX_EMAIL_LEN)
    use_case: str | None = Field(default=None, max_length=500)
    company: str | None = Field(default=None, max_length=200)  # honeypot


@router.post("/api/v2/waitlist")
async def join_waitlist(payload: WaitlistPayload, request: Request):
    """Capture an early-access signup. Idempotent on email.

    Never reveals whether the email already existed. A non-empty `company`
    honeypot field means a bot filled a hidden input -> silent success.
    """
    # honeypot: hidden field real users never fill
    if payload.company and payload.company.strip():
        return {"ok": True}

    ip = _client_ip(request)
    if _rate_limited(ip):
        raise HTTPException(status_code=429, detail="too many requests")

    email = normalize_email(payload.email)
    if not is_valid_email(email):
        raise HTTPException(status_code=422, detail="invalid email")

    use_case = (payload.use_case or "").strip() or None
    referrer = request.headers.get("referer")

    async with db.pool.acquire() as conn:
        if await conn.fetchval("SELECT to_regclass('workbench_waitlist')") is None:
            logger.error("workbench_waitlist missing — is migration 051 applied?")
            raise HTTPException(status_code=503, detail="waitlist unavailable")
        await conn.execute(
            """
            INSERT INTO workbench_waitlist (email, use_case, referrer)
            VALUES ($1, $2, $3)
            ON CONFLICT (email) DO NOTHING
            """,
            email,
            use_case,
            referrer,
        )

    return {"ok": True}


@router.get("/api/v2/waitlist/count")
async def waitlist_count():
    """Aggregate waitlist size only. Never returns emails."""
    async with db.pool.acquire() as conn:
        if await conn.fetchval("SELECT to_regclass('workbench_waitlist')") is None:
            return {"count": 0}
        n = await conn.fetchval("SELECT COUNT(*) FROM workbench_waitlist")
    return {"count": int(n or 0)}
```

- [ ] **Step 4: Register the router in `main_v2.py`**

In `backend/app/main_v2.py`, the routers are imported as a tuple at lines 103–107:

```python
from app.routers import (
    stats, trends, signals, themes, search,
    geo, workspace, briefing, indicators, wiki, events, narratives, heat,
    nlp_corrections, threads, emergent, translate,
)
```

Add `waitlist` to that import tuple (append to the last line):

```python
    nlp_corrections, threads, emergent, translate, waitlist,
```

Then add the registration line after the last existing `app.include_router(translate.router)` (line 125):

```python
app.include_router(waitlist.router)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_waitlist_router_shape.py tests/test_waitlist_email_validation.py -v`
Expected: PASS (all).

- [ ] **Step 6: Verify the app imports cleanly**

Run: `cd backend && python -c "import app.main_v2"`
Expected: no ImportError, no exception.

- [ ] **Step 7: Commit**

```bash
git add backend/app/routers/waitlist.py backend/app/main_v2.py backend/tests/test_waitlist_router_shape.py
git commit -m "feat(waitlist): POST/GET endpoints, honeypot, rate limit, register router"
```

---

## Task 4: Frontend waitlist API lib

**Files:**
- Create: `frontend-v2/src/lib/waitlist.ts`

- [ ] **Step 1: Write the lib**

```typescript
// frontend-v2/src/lib/waitlist.ts
export interface WaitlistSubmission {
  email: string
  use_case?: string
  company?: string // honeypot, always empty in the real UI
}

export async function postWaitlist(body: WaitlistSubmission): Promise<{ ok: boolean; status: number }> {
  const res = await fetch('/api/v2/waitlist', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return { ok: res.ok, status: res.status }
}

export async function getWaitlistCount(): Promise<number | null> {
  try {
    const res = await fetch('/api/v2/waitlist/count')
    if (!res.ok) return null
    const data = (await res.json()) as { count?: number }
    return typeof data.count === 'number' ? data.count : null
  } catch {
    return null
  }
}
```

- [ ] **Step 2: Typecheck**

Run: `cd frontend-v2 && npx tsc --noEmit -p tsconfig.app.json`
Expected: no errors referencing `waitlist.ts`. (If the local Node/tsc hangs — a known issue in this environment, see `STATUS.md` — rely on the `npm run build` gate in Task 6 instead.)

- [ ] **Step 3: Commit**

```bash
git add frontend-v2/src/lib/waitlist.ts
git commit -m "feat(waitlist): frontend waitlist API lib"
```

---

## Task 5: Frontend interactive gate component + CSS, wire into overlay

**Files:**
- Create: `frontend-v2/src/components/WorkbenchWaitlistGate.tsx`
- Modify: `frontend-v2/src/components/InteractiveWorkspace.tsx` (replace overlay block ~676–711)
- Modify: `frontend-v2/src/components/InvestigationWorkspace.css`

- [ ] **Step 1: Create the component**

```tsx
// frontend-v2/src/components/WorkbenchWaitlistGate.tsx
import { useEffect, useState } from 'react'
import { getWaitlistCount, postWaitlist } from '../lib/waitlist'

const COUNT_DISPLAY_THRESHOLD = 25
const SUPPORT_URL = 'https://ko-fi.com/observatoryglobalatlas'

interface WorkbenchWaitlistGateProps {
  onKeepExploring: () => void
}

type Status = 'idle' | 'submitting' | 'success' | 'error'

export function WorkbenchWaitlistGate({ onKeepExploring }: WorkbenchWaitlistGateProps) {
  const [email, setEmail] = useState('')
  const [useCase, setUseCase] = useState('')
  const [company, setCompany] = useState('') // honeypot
  const [status, setStatus] = useState<Status>('idle')
  const [count, setCount] = useState<number | null>(null)

  useEffect(() => {
    let alive = true
    getWaitlistCount().then((n) => {
      if (alive) setCount(n)
    })
    return () => {
      alive = false
    }
  }, [])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (status === 'submitting') return
    setStatus('submitting')
    const { ok } = await postWaitlist({ email, use_case: useCase || undefined, company })
    if (ok) {
      setStatus('success')
    } else {
      setStatus('error')
    }
  }

  const countLabel =
    count !== null && count >= COUNT_DISPLAY_THRESHOLD
      ? `Ya van ${count} en la lista`
      : 'Beta privada · primeros accesos'

  return (
    <div
      className="workspace-preview-overlay"
      role="dialog"
      aria-modal="true"
      aria-labelledby="workspace-preview-title"
    >
      <div className="workspace-preview-panel">
        <span className="workspace-preview-kicker">Workbench · beta privada</span>
        <h3 id="workspace-preview-title">Sé de los primeros en usarlo</h3>
        <p>
          Atlas no te dice qué creer. Te muestra cómo se mueve la información, de
          dónde viene y cómo cambia con el tiempo. El Workbench es donde armas esa
          investigación: unes narrativas, fuentes y países en un solo mapa.
        </p>

        {status === 'success' ? (
          <p className="workspace-preview-note workspace-waitlist-success">
            Estás dentro. Te escribimos pronto con tu acceso.
          </p>
        ) : (
          <form className="workspace-waitlist-form" onSubmit={handleSubmit}>
            <span className="workspace-waitlist-count">{countLabel}</span>
            <input
              type="email"
              required
              placeholder="tu@correo.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="workspace-waitlist-input"
              aria-label="Correo electrónico"
            />
            <textarea
              placeholder="¿Para qué lo usarías? (opcional)"
              value={useCase}
              onChange={(e) => setUseCase(e.target.value)}
              className="workspace-waitlist-textarea"
              aria-label="Para qué lo usarías"
              rows={2}
            />
            {/* honeypot: visually hidden, real users never fill it */}
            <input
              type="text"
              tabIndex={-1}
              autoComplete="off"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              className="workspace-waitlist-honeypot"
              aria-hidden="true"
            />
            {status === 'error' && (
              <span className="workspace-waitlist-error">
                No se pudo enviar. Revisa el correo e intenta de nuevo.
              </span>
            )}
            <button
              type="submit"
              className="workspace-preview-primary"
              disabled={status === 'submitting'}
            >
              {status === 'submitting' ? 'Enviando…' : 'Pedir acceso'}
            </button>
          </form>
        )}

        <div className="workspace-preview-actions workspace-waitlist-footer">
          <a
            className="workspace-preview-secondary"
            href={SUPPORT_URL}
            target="_blank"
            rel="noopener noreferrer"
          >
            Apoyar Atlas
          </a>
          <button type="button" className="workspace-preview-ghost" onClick={onKeepExploring}>
            Keep exploring
          </button>
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Replace the overlay block in `InteractiveWorkspace.tsx`**

At the top of the file, add the import next to the existing component imports (near line 15, `import { ReadingMode } from './ReadingMode'`):

```tsx
import { WorkbenchWaitlistGate } from './WorkbenchWaitlistGate'
```

Replace the entire existing overlay JSX block (currently lines ~676–711, the `{lockedForPublicPreview && ( <div className="workspace-preview-overlay" ...> ... </div> )}`) with:

```tsx
                {lockedForPublicPreview && (
                    <WorkbenchWaitlistGate onKeepExploring={() => setIsOpen(false)} />
                )}
```

- [ ] **Step 3: Add CSS for the form/states**

Append to `frontend-v2/src/components/InvestigationWorkspace.css` (after the existing `workspace-preview-actions` rules):

```css
.workspace-waitlist-form {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-top: 14px;
}

.workspace-waitlist-count {
    font-size: 12px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--accent, #38bdf8);
    opacity: 0.85;
}

.workspace-waitlist-input,
.workspace-waitlist-textarea {
    width: 100%;
    box-sizing: border-box;
    padding: 10px 12px;
    border-radius: 8px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    background: rgba(15, 23, 42, 0.55);
    color: inherit;
    font: inherit;
    font-size: 14px;
}

.workspace-waitlist-textarea {
    resize: vertical;
    min-height: 44px;
}

.workspace-waitlist-input:focus,
.workspace-waitlist-textarea:focus {
    outline: none;
    border-color: var(--accent, #38bdf8);
}

/* honeypot: removed from layout and from assistive tech, but still in DOM */
.workspace-waitlist-honeypot {
    position: absolute;
    left: -10000px;
    width: 1px;
    height: 1px;
    overflow: hidden;
}

.workspace-waitlist-error {
    font-size: 13px;
    color: #f87171;
}

.workspace-waitlist-success {
    color: #4ade80;
}

.workspace-waitlist-footer {
    margin-top: 16px;
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend-v2/src/components/WorkbenchWaitlistGate.tsx \
        frontend-v2/src/components/InteractiveWorkspace.tsx \
        frontend-v2/src/components/InvestigationWorkspace.css
git commit -m "feat(waitlist): interactive Workbench early-access overlay"
```

---

## Task 6: Build, deploy, smoke

**Files:** none (verification + deploy)

- [ ] **Step 1: Frontend production build (the real gate)**

Run: `cd frontend-v2 && npm run build`
Expected: build succeeds (Vite `tsc -b` is stricter than `tsc --noEmit`; this is the authoritative frontend check per CLAUDE.md).

- [ ] **Step 2: Full backend test sweep for the new module + neighbors**

Run: `cd backend && python -m pytest tests/test_waitlist_router_shape.py tests/test_waitlist_email_validation.py -v`
Expected: PASS.

- [ ] **Step 3: Deploy backend**

Run: `bash scripts/deploy-fly-api.sh`
Expected: deploy completes; then verify health:
Run: `curl -s https://atlas-api-pedro.fly.dev/health | python -m json.tool`
Expected: `"status": "healthy"`, `"db_ok": true`.

- [ ] **Step 4: Smoke the new endpoints in production**

Run:
```bash
curl -s https://atlas-api-pedro.fly.dev/api/v2/waitlist/count
curl -s -X POST https://atlas-api-pedro.fly.dev/api/v2/waitlist \
  -H 'Content-Type: application/json' \
  -d '{"email":"smoke-test@example.com","use_case":"smoke"}'
curl -s https://atlas-api-pedro.fly.dev/api/v2/waitlist/count
```
Expected: first count `{"count":N}`; POST `{"ok":true}`; second count `N+1`. Then confirm via Supabase MCP `execute_sql`:
```sql
SELECT email, use_case FROM workbench_waitlist WHERE email = 'smoke-test@example.com';
```
Expected: one row. Clean it up:
```sql
DELETE FROM workbench_waitlist WHERE email = 'smoke-test@example.com';
```

- [ ] **Step 5: Deploy frontend**

Frontend deploys via Vercel on push to `v3-intel-layer`. Push the branch:
```bash
git push origin v3-intel-layer
```
Then browser-smoke the deployed Workbench preview: open the production app, navigate to the Workbench, confirm the overlay shows the form + count label, submit a test email, confirm the success state, confirm the Workbench stays gated, and confirm `Apoyar Atlas` + `Keep exploring` work. Delete the browser-smoke test email from the table afterward via MCP as in Step 4.

- [ ] **Step 6: Update docs + inventory**

```bash
python3 scripts/project_inventory.py
git add docs/state/PROJECT_INVENTORY.md STATUS.md SESSION_LOG.md
git commit -m "docs(waitlist): regenerate inventory + log waitlist gate shipment"
git push origin v3-intel-layer
```
(Add a STATUS.md handoff entry and a SESSION_LOG.md entry describing the waitlist gate shipment before committing.)

---

## Self-review notes

- **Spec coverage:** table (T1), POST/GET + honeypot + rate limit + idempotent + count-aggregate-only (T2/T3), overlay states + minimal fields + real-count-with-threshold + separate support CTA + mailto removed (T5), no supabase-js (T4 uses relative fetch), smoke + deploy order (T6). Out-of-scope items (Option B, language pass, email delivery, captcha) are not in any task — correct.
- **Type consistency:** `normalize_email`/`is_valid_email` defined in T2 and used in T3; `WaitlistPayload.company` honeypot matches frontend `WaitlistSubmission.company`; `postWaitlist`/`getWaitlistCount` defined in T4 and consumed in T5; `COUNT_DISPLAY_THRESHOLD` (25) matches the spec's count threshold.
- **Placeholders:** none — every code/SQL/command step is concrete.
