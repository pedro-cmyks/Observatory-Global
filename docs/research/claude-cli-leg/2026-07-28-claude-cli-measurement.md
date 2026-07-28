# claude CLI headless as an insight-lane provider leg — measurement + wiring (2026-07-28)

Goal: ride Pedro's Claude subscription via the local `claude` CLI as a $0-marginal
provider leg for the sanctioned LLM lanes, replacing the DEAD Anthropic API leg
(400 since ~06-29) and de-risking the single-balance failure class that caused
the 2026-07-24..27 L1 blackout.

Harness: `backend/scripts/measure_claude_cli_latency.py` (re-runnable).
Wiring: `backend/app/services/insight_llm.py` (`claude_cli` leg, default OFF).

## VERDICT (provisional): FAILOVER LEG, NOT PRIMARY — and live measurement is
## BLOCKED on re-auth (NEEDS PEDRO)

Every headless `claude -p` call on the M1 currently returns:

    rc=1, JSON envelope {"is_error": true, "api_error_status": 401,
    "result": "Failed to authenticate. API Error: 401 OAuth access token has
               expired. Re-authenticate to continue."}

`claude auth status` still reports `loggedIn: true` (claude.ai,
`subscriptionType: "pro"` — note: status says pro, not max) but the refresh
token is dead, so real latency/throughput/cap-behavior numbers could not be
collected. **Pedro: run `claude auth login` on the M1, then re-run the harness
(commands in its header).** The dead-auth state is itself the strongest
architecture datum: the CLI leg can silently die the same way a prepaid balance
does — it must never be the only leg, and its 401 shape is classified as
exhaustion-of-leg in the wiring (measured envelope frozen in
`tests/test_insight_llm_cli.py::MEASURED_401_ENVELOPE`).

## What WAS measured

### DeepSeek baseline (the bar to beat) — same label-court judge prompt
label + 12 headlines (~380 tokens in / ~40 out), n=10 sequential, measured at
M1 load-average 40 (network-bound, load-insensitive):

| metric | seconds |
|---|---|
| p50 | **1.49** |
| p95 | 1.66 |
| min / max | 1.38 / 2.13 |
| mean | 1.56 |
| errors | 0/10 |

### claude CLI process overhead (auth-independent, measured to the 401/refusal)
| config | wall | notes |
|---|---|---|
| `--bare`, idle-ish | 1.5s | best case observed |
| `--bare`, load 40 | 14–27s (n=6) | user CPU only ~0.9s — spawn cost + starvation |
| full config (hooks/plugins) | 8–50s | claude-mem/caveman hooks etc. load per call |

Load 40 is not an anomaly: the nightly window IS the scoped-snapshot regime
(the 6h job pegs the M1), so the loaded numbers are the honest nightly ones.

### Two wiring-relevant CLI facts
1. **`--bare` disables subscription auth entirely** (never reads keychain
   OAuth; always answers "Not logged in · Please run /login"). The wired leg
   uses **`--safe-mode`** (keeps auth, skips hooks/plugins/MCP) +
   `--tools ""` + `--no-session-persistence`.
2. `--output-format json` emits one envelope: `is_error`, `api_error_status`,
   `result`, `usage.{input,output}_tokens`, `total_cost_usd` — parseable, and
   failure shapes are programmatic (no stderr scraping needed).

### Nightly volume (from atlas-topic-classifier / scoped-snapshot logs)
- LABEL COURT: 40 judgments per 30-min cycle (`LABEL COURT DONE: 40 tried ·
  ... tokens in/out 15219/1592`) → ~1,900/day ceiling, ~380 in / ~40 out
  tokens per call.
- RELABEL: 20 per cycle → ~960/day ceiling.
- Plus nightly cluster labeling in the snapshot. Total ~2–3k calls/day across
  lanes — matches the ~2,000 planning number.

## Capacity math → architecture

- DeepSeek does the whole court+relabel day sequentially in ~50–75 min.
- CLI per-call floor = subprocess spawn + node boot + API. Even POST-auth,
  best case ≈ 3–6s/call idle; at the measured nightly load, 15–25s/call.
  2,000 calls → **1.7–3.3h best case, 8–14h under real nightly load**. That is
  not a primary leg for the court/label volume; it is a viable failover for
  the LOW-VOLUME insight lane (Brief "Editor's Analysis", theme insight,
  dossier synthesis — a handful of calls/day) and an emergency fallback when
  the DeepSeek balance dies (the L1-blackout class).
- Session-window caps (Pro per `auth status`) are un-measured (blocked); a
  2k-call/night lane would almost certainly hit them. Another reason the CLI
  is failover-tier. The batch harness mode exists precisely to observe the
  cap error shape post-auth.
- One-call-per-process is the current architecture. If the CLI ever needs to
  carry real volume, the fix is amortizing startup (persistent
  `--input-format stream-json` session), not more subprocesses — follow-up,
  not this pass.

## Wiring shipped (default OFF — nothing changes until Pedro flips it)

`insight_llm.generate_insight` chain is now order-configurable:

- `ATLAS_INSIGHT_CHAIN` (default `anthropic,deepseek,claude_cli` — measurement
  puts the CLI last).
- `ATLAS_CLAUDE_CLI=on` required for the leg (default off).
- Never on Fly: `FLY_APP_NAME`/`FLY_MACHINE_ID` env → leg skipped; binary must
  be on PATH (the M1 marker).
- `INSIGHT_CLAUDE_CLI_MODEL` (default `haiku`), `ATLAS_CLAUDE_CLI_TIMEOUT`
  (default 120s), `ATLAS_CLAUDE_CLI_BIN`.
- Envelope parsing is truncation-tolerant (strict parse → outermost `{...}`
  span → honest failure). A CLI error falls through to the next leg, logged,
  never silent.
- Cost still ledgered (`ai_cost_events`, provider `claude_cli`, $0 pricing is
  the ledger's concern; tokens honest from the envelope).

### Exhaustion honesty (the e658dddf contract)
- Cap-hit / dead-auth shapes (`usage limit reached`, `Not logged in`,
  `OAuth ... expired`, envelope status 401/402/403/429, …) classify as
  **exhaustion-of-that-leg**: fall through, `logger.warning` with
  NON-canonical wording — a chain that recovers via DeepSeek must never trip
  the runner's `_ATLAS_EXHAUSTED_RE` grep (which only scans FAILED steps).
- Only when the WHOLE chain returns nothing and the CLI leg was exhausted does
  the module emit one `logger.error` line containing the canonical
  `quota exceeded` vocabulary → a failed step now ledgers PROVIDER_EXHAUSTED
  exactly when it truly produced nothing. New error code:
  `insight_cli_exhausted` (existing codes unchanged).
- Contract frozen in `backend/tests/test_insight_llm_cli.py` (19 tests): a
  byte-copy of `_ATLAS_EXHAUSTED_RE` asserts leg-level lines never match and
  the total-failure line matches exactly once.

## NEEDS PEDRO
1. `claude auth login` on the M1 (interactive; cannot be done headless).
2. Then: `python3 backend/scripts/measure_claude_cli_latency.py single` and
   `batch 50 haiku` — fills in real p50/p95, calls/min, and the cap-hit error
   shape (extend `CLI_EXHAUSTED_MARKERS` in insight_llm.py if the observed cap
   text differs).
3. Decide the flip: `ATLAS_CLAUDE_CLI=on` (+ optionally reorder
   `ATLAS_INSIGHT_CHAIN`) in the M1 runner env. Fly needs nothing (leg is
   guarded off there by construction).
4. Note the `subscriptionType: "pro"` reading — if this machine is supposed to
   ride a Max plan, the CLI may be logged into the wrong account.
