# Corroborate lane — latency measurement + the proxy ceiling (tren B2 V5)

**Date:** 2026-08-12 · **Surface:** prod (`atlas-api-pedro.fly.dev`, proxied by
`observatory-global.vercel.app`) · **Trigger:**
`docs/research/gold/2026-08-12-frank-test-fresh.md` §3a — the lane measured at
**1 success in 4** (2 × HTTP 502, 1 × "lane unavailable", 1 × 200).

The plan (`docs/superpowers/plans/2026-08-12-tren-b2-two-reviews.md` V5) said:
serialize, always serve partials, surface the throttled status, and **measure
before** deciding whether the proxy ceiling forces a job+poll. This is that
measurement.

---

## 1. The report's causal diagnosis is REFUTED (and it matters)

> "The handler fires its per-pin queries **concurrently** (`asyncio.gather`),
> which violates that limit by construction."

It does not. `app/services/external_depth.throttle()` is a process-wide
`asyncio.Lock` that releases at most one DOC 2.0 request per 5.1s, and
`fetch_external_depth` has awaited it since `c7e69832`. `asyncio.gather` starts
the coroutines together; the lock releases them 5.1s apart. The claim lane
(`corroboration.doc20_fetch_status`) shares the same lock.

**The report's own numbers prove the throttle was live**: 1 evidence pin (2
queries) = 21.7s, 2 evidence pins (4 queries) = 31.4s. Δ = 9.7s for two extra
queries ≈ 2 × 5.1s. Concurrent firing would have shown ~0 Δ.

So the 429s in the report came from its 3 rapid hand-probes, not from the
handler. **Concurrency was never the cause. Serialized latency versus the proxy
ceiling is.** This distinction decides the fix: pacing the requests harder would
have changed nothing, and would have made the real problem worse.

## 2. Measured latency vs pin count (prod, pre-change)

Harness: `scratchpad/measure_corroborate.py`, direct to Fly, `force: true`, a
**distinct real story per run** so the 30-min DOC 2.0 query cache could not
flatter a later run.

| Pins (evidence) | Queries | Wall clock | HTTP |
|---|---|---|---|
| 1 | 2 | ~23s | 200 |
| 2 | 4 | ~35s | 200 |
| 3 | 6 | **46.3s** | 200 |
| 4 | 8 | **57.8s** | 200 |

Fit: **≈ 5.75s per query + ~12s fixed** (5.1s throttle + fetch jitter; the fixed
term is the last query's own fetch plus the asymmetry LLM pass).

## 3. The ceiling

`frontend-v2/vercel.json` rewrites `/api/:path*` to Fly — a plain edge proxy, so
its response ceiling applies. Bracketed by the report's own runs: **21.7s → 200,
31.4s → 502**, i.e. ~30s. Same class as the `/api/v2/universe` 502 already in
the record ("the ceiling is the Fly proxy, not Postgres").

**Verdict: the ceiling genuinely binds after serialization.** A 2-evidence-pin
route (~35s) already exceeds it, and a real investigation is 3-4 pins (46-58s).
Serialization + partials alone cannot fit a real route into one HTTP response.
**Job+poll was therefore built**, not merely considered.

## 4. What was built

* `POST /api/v2/dossier/corroborate/start` + `GET .../corroborate/status/{id}` —
  start returns immediately; the client polls. A complete cached run is returned
  inline. A lost job (restart/expiry) answers `unknown`, which the client renders
  as "the run was interrupted", never as an empty result.
* The synchronous `POST /corroborate` stays, now **budgeted** under the ceiling
  (`ATLAS_CORROB_SYNC_BUDGET_S`, default 20s): it can no longer die as a 502; it
  returns partials and says so.
* **Partials always** — at the budget, in-flight queries are cancelled, their
  pins read `timeout`, and every pin that landed still serves its receipts.
* `search_status` per pin (`ok|partial|throttled|timeout|unavailable|
  not_applicable`) + `queries_run`/`queries_answered`; run-level `partial`,
  `pins_measured`, `pins_partial`, `pins_applicable`.
* `fetch_external_depth_status` distinguishes **throttled ≠ down ≠ measured-zero**,
  and a failed window is no longer negative-cached for 30 minutes (60s for a
  network failure, 120s for a throttle). The old 1800s negative cache is a strong
  candidate for the report's third failure ("lane unavailable" on a re-run).

## 5. A finding the fix cannot remove: the throttle is UPSTREAM

Probed DOC 2.0 directly, 6 sequential queries at **5.2s spacing** (wider than the
documented limit), from an idle client:

```
1..6  http=429  (every one, including the first after minutes of idleness)
```

Then single probes after **45s, 60s and 90s of complete idleness**: `429`, `429`,
`429`.

So GDELT's free tier enforces more than per-request spacing — it applies
multi-minute IP-level windows once it has seen sustained use. **No client-side
pacing fixes this.** That makes the plan's items (2) and (3) — partials always,
throttled visible — the load-bearing repairs, and it is why the cooldown for a
throttle is 120s rather than a re-fire every minute.

Product consequence, honestly stated: on a throttled window the analyst gets
"web lane throttled — not measured; re-run in a minute", not a fabricated zero
and not a spinner that dies at 30s.

## 6. Live verification (prod, through the Vercel rewrite)

Every request below traverses `observatory-global.vercel.app/api/...` — the exact
path the browser uses, i.e. the proxy that was 502-ing. Harness:
`scratchpad/verify_corroborate_live.py`.

**4 consecutive runs, 3-pin investigation (2 evidence + 1 context), ×3 batches:**

| Batch | Requests (start + polls) | non-200 | Longest run | Result |
|---|---|---|---|---|
| A (GDELT partly up) | 16 | **0** | 31.2s | 1 pin `established` 20 voices, 1 `throttled` |
| B (GDELT banned) | 16 | **0** | 28.8s | both pins `throttled`, honest note |
| C (GDELT banned) | 16 | **0** | 37.2s | both pins `throttled`, honest note |
| D (final build) | 16 | **0** | **38.3s** | 1 `established` 20 voices `partial`, 1 `throttled` |

Batch D, run 1 — the acceptance case, 8.3s past the ceiling that used to kill it:

```
run 1:  38.3s  start+13 polls  non-200=0  partial=True  measured=1/2
  dynamic-topic-12280  search=partial         status=established     voices=20
  dynamic-topic-11944  search=throttled       status=unverified      voices=0
  country-SY           search=not_applicable  status=not_applicable
note: web lane throttled on part of this run — 1 of 2 evidence pins measured
      (1 of them only partially); the pin not reached is shown unmeasured,
      not as zero coverage
```

**Healthy path, same proxy** (client-supplied lane + live DOC 2.0, 16 requests,
0 non-200):

```
partial=True  measured=2/2  partially=1
  dt-A  search=ok       measured=True  status=established  voices=22  cits=5
  dt-B  search=partial  measured=True  status=established  voices=20  cits=5
  country-SY  search=not_applicable  status=not_applicable
note: web lane did not answer on part of this run — all 2 evidence pins
      measured, 1 of them only partially
```

**0 silent 502s in 80 proxied requests**, including runs of 28.8s, 31.2s, 37.2s
and 38.3s — every one of which is above the ceiling that used to kill this lane.

One transient `502` was observed **on `start`** (0.3s, not a timeout; the same
body succeeded seconds later). That failure mode is now cheap and recoverable:
`runCorroborationJob` falls back to the budgeted synchronous endpoint when the
start call fails, so a proxy blip degrades instead of ending the run.

### Two honesty defects the LIVE run caught (both fixed, both test-frozen)

1. `measured=0/2` rendered beside a pin that was `established` on 20 voices and
   4 receipts — its web query was throttled but the supplied lane had measured
   it. `search_status` describes the WEB lane; a new per-pin `measured` describes
   the PIN. A 0 must never land next to a receipt list (the N19 class).
2. "2 of 2 evidence pins measured … **the rest** are shown unmeasured" — there
   was no rest. A degraded-but-complete run now says "all 2 evidence pins
   measured, 1 of them only partially".

## 7. Residuals (honest)

* The frontend job+poll client ships in this change but the **Vercel deploy is
  the integrator's** (plan: one Fly+Vercel deploy at integration). Until it
  lands, the browser still calls the synchronous endpoint — which is now budgeted,
  so it degrades to an honest partial instead of a 502.
* **Browser check is partial.** Driving the real UI (seeded 3-pin investigation →
  REPORT → CORROBORATE) confirmed the new bundle loads and the UI calls
  `POST /api/v2/dossier/corroborate/start`, and the running-state copy renders.
  The section never resolved because **every** `/api/v2/dossier/*` POST hung
  through the shared local dev proxy — `connections`, `walk` and `synthesize`
  included, none of which V5 touches — a local artifact of stale keep-alive
  sockets after four Fly redeploys. The shared dev server was left running
  rather than restarted (a peer agent was using it). The visual gate belongs to
  the integrator's browser pass on the deployed build; the payload itself is
  verified live in §6.
* In-process job registry (one uvicorn worker, matching `_CORROB_CACHE`): a
  machine restart loses in-flight jobs and the poll answers `unknown`. Correct,
  visible, and cheap to survive (re-run). A DB-backed job table would remove it.
* The upstream throttle is not ours to fix. A SERP/Brave key would add an
  independent lane; `supplied_results` already accepts one today.
* Batches B and C could not exercise the healthy path because this session's own
  measurement traffic put GDELT into its ban window; batches A and D show the
  `established` path inside the acceptance batch itself.
* **Commit provenance:** the V5 code was staged pathspec-only but a concurrent
  agent in the same worktree committed non-pathspec and swept it into
  `e00cd167` ("fix(markets): the summary card's delta never renders without its
  window"). Nothing was lost — every V5 file is in that tree — but the log
  attributes it to the markets message. History was NOT rewritten: five other
  agents were committing to this branch at the time. The follow-up commit that
  carries this artifact holds the honest V5 record.
