# Atlas — Pre-Launch Security Audit (2026-07-06)

Read-only audit, 3 parallel sweeps, nothing modified. This is the **Phase 0
blindaje work-list** — the gate before any external user touches the app.
Source: GTM plan `docs/state/2026-07-06-gtm-plan.md` Phase 0 security sub-gate.

## TL;DR

- **SQL injection: NONE.** Every user-input → SQL path is parameterized. Not a
  worry. (One defense-in-depth note below.)
- **Secrets: never committed.** `.env` is gitignored, 0 hits in git history.
  Frontend bundle clean, no XSS. Real but non-urgent: rotate 5 live keys sitting
  cleartext on local disk.
- **The real problem = the API is wide open.** No auth, no rate limiting, CORS
  `*`, a 5-connection pool trivially exhausted, paid-LLM endpoints anonymous
  (direct billing drain), two anonymous DB writes. THIS is the launch blocker.

---

## P0 — BLOCKS external launch (the API is undefended)

Nothing here needs the full accounts system except item 2b — most is cheap and
should ship regardless.

| # | Item | Where | Why |
|---|------|-------|-----|
| 1 | **Add global rate limiting** (per-IP, slowapi/middleware/Redis bucket). None exists today except the waitlist. | `main_v2.py:42` (only CORS middleware) | Without it every item below is trivially abusable. |
| 2a | **Interim-gate the paid/heavy endpoints** with per-IP quotas NOW | `research/plan` (embed), `translate` + `translate/batch` (DeepSeek 64/call), `theme/{c}/insight` + `briefing/insight` (Anthropic→DeepSeek), `threads/{id}?llm=1`, `signal/{id}/context` (on-demand embed), `theme/{c}/external-depth` (GDELT, 25s hold) | Anonymous → direct billing drain + embed-service starvation. Cache evaded by varying `hours`/`query`/`signal_id`. |
| 2b | **Auth-gate them properly** once accounts exist | same set | The durable fix; folds into the Phase 0 accounts build. |
| 3 | **Lock CORS** `allow_origins` to the Vercel domain(s) | `main_v2.py:44` (`["*"]`) | Zero origin restriction today. |
| 4 | **Gate or drop the two anonymous writes** | `POST /api/v2/research/events` (200 rows/call), `POST /api/v2/telemetry` (50 rows/call) | Table-pollution / disk-fill; telemetry poisoning corrupts the wedge-governing read. Both return `accepted` on abuse → no alert. |
| 5 | **Raise pool `max_size` + bound slow endpoints** | `main_v2.py:65` (`max_size=5`); `external-depth` holds 25s | 5 conns + one 25s endpoint = full-API DoS with a handful of concurrent requests, no botnet. |
| 6 | **Make `/api/v2/emergent` non-public** | `emergent.py:26` | Dumps internal cluster snapshots (gate thresholds, cohesion, vendor agreement, sample ids). |

## P1 — before launch, not blocking the audit gate

| # | Item | Where |
|---|------|-------|
| 7 | **Rotate 5 live keys** (Anthropic, OpenAI, DeepSeek, Supabase `DATABASE_URL` pw, OpenSky secret) — cleartext on local disk, never committed, but real. | `/.env:25,30,32,34,35` |
| 8 | **Add a backend lockfile** (`uv.lock`/pinned `requirements.txt`) — floors (`>=`) today = no supply-chain pinning. | `backend/pyproject.toml` |
| 9 | Confirm `ATLAS_ADMIN_TOKEN` is SET in prod (fails closed if unset — good — but then admin refresh/corrections are unusable). | env |

## Defense-in-depth (note, not a fix)

- Window/limit params (`hours`, `limit`, `days`) are interpolated as SQL **text**
  (`INTERVAL '{hours} hours'`, `% hours`) across geo/indicators/themes/signals/
  events/trends/workspace. **Safe today** solely because FastAPI `Query(int, ge=,
  le=)` coerces + range-checks them. Single point of failure: if any of those
  param types is ever loosened to `str`, the site becomes injectable. Keep them
  `int`-typed; ideally migrate to bound params over time.

---

## What is NOT a problem (verified, don't re-investigate)

- SQL injection — all paths parameterized, both asyncpg + psycopg.
- Frontend secret leakage — no sensitive `VITE_*` reaches the client bundle.
- XSS — no `dangerouslySetInnerHTML`/`eval`; the one `innerHTML` is a detached
  textarea entity-decode (not in DOM, not executable).
- Secrets in git — never committed.
- Admin-guarded writes (`heat/countries/refresh` matview, `nlp/corrections`) —
  behind `X-Atlas-Admin-Token`, fail closed.

---

## Implementation status (2026-07-06)

**Interim hardening batch SHIPPED to code (NOT deployed) — gate = per-IP rate
limit (Pedro's call).** Tested: `backend/tests/test_rate_limit.py` 12/12.

- ✅ **1 Rate limiting** — `backend/app/rate_limit.py` (`RateLimitMiddleware`,
  per-IP sliding window). Buckets: paid 20/5min, slow 8/5min, write 60/min,
  global 600/min — all env-tunable. Kill switch `ATLAS_RATE_LIMIT_ENABLED=false`.
  Installed before CORS so 429s keep CORS headers (verified in test).
  - **Client-IP under the Vercel proxy:** the frontend proxies /api/* through
    the Vercel rewrite, so Fly-Client-IP is Vercel's egress (one IP for ALL
    users → would collapse everyone into one bucket). `client_ip()` therefore
    keys on the **leftmost X-Forwarded-For** (the real client Vercel forwards),
    falling back to Fly-Client-IP for direct hits. **Known interim limitation:**
    XFF is spoofable on a direct-to-fly.dev request, so a determined attacker
    bypassing Vercel can rotate it to dodge the limit — durable fix = per-account
    quotas + a trusted-proxy allowlist (accounts build). **Verify post-deploy**
    that Vercel actually forwards the client IP in XFF (else limiting collapses
    to the proxy IP).
- ✅ **2a Interim quota** on paid/heavy endpoints (research/plan, translate[/batch],
  theme/*/insight, briefing/insight, signal/*/context, external-depth→slow,
  threads/*?llm=1). ⏳ **2b** proper auth-gate deferred to the accounts build.
- ✅ **3 CORS** — env-driven `ATLAS_CORS_ORIGINS`; falls back to `*` with a loud
  startup warning if unset (no silent deploy breakage; lock = set the env var).
- ✅ **4 Anonymous writes** — telemetry + research/events now in the `write`
  bucket (60/min/IP). They stay anonymous by design (the frontend fires them);
  rate limit is the interim mitigation.
- ✅ **5 Pool** — `max_size` 5→10, `min_size` 2 (env `ATLAS_DB_POOL_MAX/MIN`).
- ✅ **6 `/api/v2/emergent`** — admin-token gated (frontend does not use it).
- ⏳ **7/8/9** housekeeping — not started.

### Deploy prerequisites (Fly secrets — set BEFORE `deploy-fly-api.sh`)

1. `ATLAS_CORS_ORIGINS=https://<vercel-prod-domain>[,<preview-domains>]` — until
   set, CORS stays open (`*`). REQUIRED for the lock.
2. Confirm `ATLAS_ADMIN_TOKEN` is set (or `/api/v2/emergent`, heat-refresh, and
   nlp-corrections all 403 — fails closed by design).
3. Optional tuning: `ATLAS_RL_*` limits, `ATLAS_DB_POOL_MAX` (keep under the
   Supabase pooler connection cap).

Reversible: `ATLAS_RATE_LIMIT_ENABLED=false` disables all limiting instantly.

## Sequencing recommendation

- **Interim hardening batch (cheap, ship now, buys safety even pre-accounts):**
  items 1, 3, 4, 5, 6 + interim quotas (2a). No auth system needed. One backend
  deploy.
- **With the accounts build:** item 2b (proper auth-gating of paid endpoints).
- **Housekeeping:** items 7, 8, 9.
