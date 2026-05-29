# Atlas LLM spend ledger

Running record of API spend on the Atlas precision / annotator-panel work.
Numbers below are **vendor-billed actuals** (from the provider dashboards),
not token estimates, unless marked otherwise.

## Running total (cumulative, as of 2026-05-29)

| Vendor | Cumulative spend |
|---|---|
| Anthropic | $23.09 |
| OpenAI | $9.11 |
| DeepSeek | $0.25 |
| **Total** | **$32.45** |

## By work phase

| Phase | Anthropic | OpenAI | DeepSeek | Phase total | Notes |
|---|---|---|---|---|---|
| Methodology study (256-row panel, baselines, vocab mining) — to 2026-05-28 | ~$4.58 | ~$0.90 | $0.00 | ~$5.48 | 7-model panel over 247 signals; from prior session handoff. |
| Phase A 5k 3-vendor annotation (2026-05-28) | ~$18.51 | ~$8.21 | $0.25 | ~$26.97 | sonnet-4-6 + gpt-4.1 + deepseek-chat over ~5.5k assignments. Derived = cumulative − methodology. |
| Semantic embeddings (text-embedding-3-small, 4,911 rows) | — | <$0.01 | — | <$0.01 | folded into the OpenAI total; negligible. |

Phase splits are derived from the cumulative dashboard totals minus the
prior-session handoff figure (~$5.48); the cumulative row is the source of
truth.

## Budget context

- Authorized envelope for the 5k annotation run: $45-90. Actual Phase A
  spend ~$27 — comfortably under.
- Sonnet-4-6 is the dominant cost (~3x slower and pricier per call than
  gpt-4.1; deepseek-chat is near-free at $0.25 for 5.5k rows).

## What the spend bought

- 5,557-assignment stratified sample, 3-vendor consensus (5,507 assignments).
- Validated that a learned scope gate clears 90% precision at 64%
  evidence-recall (lexical lower bound) — the v3 architecture proof.
- One-time cost: the gate trains on this corpus and runs free in the
  worker (no per-signal LLM cost at inference).

## Update protocol

After any LLM-spend work block, read the provider dashboards and append the
new cumulative totals here with the date. Keep the cumulative table as the
single source of truth; phase rows are explanatory.
