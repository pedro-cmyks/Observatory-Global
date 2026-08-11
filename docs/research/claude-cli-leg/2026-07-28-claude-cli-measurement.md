# claude CLI headless as an insight-lane provider leg — measurement + wiring (2026-07-28)

Goal: ride Pedro's Claude subscription via the local `claude` CLI as a $0-marginal
provider leg for the sanctioned LLM lanes, replacing the DEAD Anthropic API leg
(400 since ~06-29) and de-risking the single-balance failure class that caused
the 2026-07-24..27 L1 blackout.

Harness: `backend/scripts/measure_claude_cli_latency.py` (re-runnable).
Wiring: `backend/app/services/insight_llm.py` (`claude_cli` leg, default OFF).

## VERDICT (CONFIRMED post-auth, 2026-07-28 PM): FAILOVER LEG, NOT PRIMARY

Post-`claude auth login` measurement, production command shape
(`--safe-mode --tools "" --model haiku`, the exact wired-leg invocation),
50 sequential calls on the M1 at load ~25:

| metric | claude CLI (haiku, safe-mode) | DeepSeek (same prompt) |
|---|---|---|
| p50 | **15.8s** | **1.49s** |
| p95 | 21.6s | 1.66s |
| min / max | 10.7 / 22.5s | 1.38 / 2.13s |
| throughput | **3.66 calls/min** | ~40 calls/min |
| errors / cap hits | 0/50 | 0/10 |

- 2,000 nightly court/label calls at 3.66/min = **~9.1h sequential** vs
  DeepSeek's ~50min → the CLI can NEVER carry the court/label volume as
  primary. As the low-volume insight-lane failover (handful of calls/day,
  $0 marginal) it is comfortably viable — exactly what got wired.
- **No cap behavior observed in 50 sequential calls** (~70k tokens); the
  insight lane will never approach a session cap. The cap-error shape at real
  volume remains unobserved — the exhaustion classifier keeps its marker-list
  + status-code net (401/402/403/429) until one is seen in the wild.
- Wall time splits ≈ 2-4s process spawn + 6-18s API (haiku 4.5 spends output
  tokens on reasoning: 579-653 out for a 40-token verdict).
- End-to-end through the wired leg verified live: `ATLAS_CLAUDE_CLI=on
  ATLAS_INSIGHT_CHAIN=claude_cli` → `generate_insight` returned
  `provider=claude_cli`, coherent prose, honest usage (215 in / 271 out),
  12.2s wall.
- Quality on the court prompt: verdicts correct (`entailed` + sane reason) on
  every inspected call, all four models.

### Model + flag economics (single-call, post-auth)
| config | wall | nominal cost/call | note |
|---|---|---|---|
| default model (= **opus-5**) | 25.5s | $1.47 | wrong tier — never let the leg default |
| haiku, full config (hooks/plugins) | 11.6s | $0.208 | ~200k tokens of session context per call |
| haiku, `--safe-mode --tools ""` | 9-11s | **$0.005** | 847 tokens in — 240× less context |
| sonnet | 8.5s | $0.88 | |
| `--bare` | — | — | auth-dead by design (never reads keychain) |

Nominal cost = what the subscription meters against its cap; the safe-mode
shape makes the leg's cap footprint negligible.

### The auth story (the first run's blocker — architecture datum)
The 07-28 AM run found every headless call returning
`401 OAuth access token has expired` while `claude auth status` still claimed
`loggedIn: true` — dead for ~a month (keychain entry untouched since 06-24;
the first re-login attempt refreshed Claude DESKTOP, not the CLI). The CLI leg
can silently die exactly like a prepaid balance — it must never be the only
leg, and its 401 shape is classified as exhaustion-of-leg in the wiring
(envelope frozen in `tests/test_insight_llm_cli.py::MEASURED_401_ENVELOPE`).
`subscriptionType` reads "pro".

## What was measured pre-auth (AM run)

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

## STATUS: FLIPPED ON (2026-07-28 PM, Pedro's call)
1. ~~`claude auth login`~~ DONE — auth live, post-auth numbers above. The
   fresh login also fixed the stale `subscriptionType` reading: it now says
   **"max"** (the earlier "pro" was month-old cached metadata, not a wrong
   account). CLI itself is current (2.1.220, self-updated at login).
2. ~~Flip~~ DONE: `ATLAS_CLAUDE_CLI=on` + `ATLAS_CLAUDE_CLI_BIN=
   /Users/pedro/.local/bin/claude` (absolute — launchd's minimal PATH can't
   find `claude`; the path is the stable symlink, survives self-updates) in
   `/Users/pedro/AtlasLocalWorker/.env`. The classifier runner full-sources
   .env (`set -a`); run-scoped-snapshot.sh loads only whitelisted keys, so
   both vars were added to its key loop (repo + ALW copies, byte-identical
   block verified). Chain order stays the measured default
   `anthropic,deepseek,claude_cli`. Fly needs nothing (leg guarded off there
   by construction).
3. Verified under a launchd-like env (env -i, minimal PATH, only the two
   vars): `claude_cli_available() == True` and a live `generate_insight`
   returned `provider=claude_cli` with a coherent verdict — keychain auth
   works from that context, so the seal's failover leg is armed for tonight.
4. Open watch-item: when a real cap-hit is ever observed, check its text
   against `CLI_EXHAUSTED_MARKERS` in insight_llm.py and extend if the
   dialect is new.
