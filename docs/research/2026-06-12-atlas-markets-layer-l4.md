# Atlas L4 — Markets Layer (personal trading research app)

**Date:** 2026-06-12
**Status:** considered + planned, not started (nothing blocks the current spec)
**Origin:** Pedro's idea: a fourth Atlas layer — personal-only app that uses
Atlas narrative data + statistical models + LLM inference (Anthropic/OpenAI/
DeepSeek APIs available) to understand market behavior and eventually place
trades. Noted a fork of this repo by someone with an auto-trading engine.
**Related:** #151 (financial overlay — the Atlas *product* side), #219
(Kalman movement feed), [[2026-06-10-funnel-maturity-and-positioning]],
[[2026-06-09-research-thread-builder-workbench]].

## 0. Two different things, kept separate on purpose

1. **Atlas product (#151)**: market context overlay — commodity/asset prices
   shown next to relevant threads. Editorial, descriptive, public. Already
   in the backlog; the L4 work feeds it analysis but is not it.
2. **L4 (this doc)**: a **separate, private repo** ("atlas-markets") that
   *consumes* the Atlas API. Personal tool. Never deployed with Atlas, never
   shares credentials or DB. Atlas must work well first — Pedro's own
   framing: "el uno va después del otro."

## 1. What the literature actually says (read 2026-06-12)

- **LLM multi-agent trading frameworks exist and are maturing**:
  [TradingAgents](https://github.com/TauricResearch/TradingAgents) (analyst
  roles: fundamental/sentiment/technical → researcher debate → trader →
  risk), [FinRL contests](https://arxiv.org/pdf/2504.02281) benchmark RL+LLM
  agents, and a 2025 survey ([ACL Findings](https://aclanthology.org/2025.findings-emnlp.972.pdf))
  maps the space.
- **Evidence is mixed and the failure modes are instructive**: studies report
  LLM sentiment signals adding non-redundant predictive power
  ([MDPI 2025](https://www.mdpi.com/0718-1876/20/2/77),
  [PMC review](https://pmc.ncbi.nlm.nih.gov/articles/PMC12421730/)), but
  critical work finds **naive multi-source aggregation reduces returns and
  increases drawdown** (noise injection), that sentiment-via-web-search is
  **leakage-prone**, and that LLM traders are **manipulable through
  adversarial headlines** ([arXiv 2026](https://arxiv.org/html/2601.13082v1)).
  [TrustTrade](https://arxiv.org/pdf/2603.22567): selective consensus across
  agents reduces decision uncertainty — relevant to the 3-provider ensemble
  idea.
- **GDELT→markets is an established research line**:
  [macro-alpha news-sentiment studies](https://arxiv.org/html/2505.16136v1)
  (FinBERT+XGBoost on GDELT, claimed Sharpe 4-6 — treat numbers that high as
  leakage red flags, not targets), and commercial products already do it
  ([GDELT Cloud](https://gdeltcloud.com/), [GeoStrat](https://geostrat.app/)
  mixing GDELT tone + OSINT + prediction markets). Known caveat that matches
  our own funnel measurements: GDELT field accuracy ~55%, redundancy ~20%
  ([MDPI](https://www.mdpi.com/2306-5729/10/10/158)) — **Atlas's dedup +
  gates + thread identities are exactly the preprocessing this literature
  says is required**. That is our genuine edge: curated narrative state, not
  raw feeds.
- **Tooling is a solved problem** ([landscape](https://python.financial/),
  [awesome-systematic-trading](https://github.com/wangzhe3224/awesome-systematic-trading)):
  research backtesting → **vectorbt**; execution-grade engine →
  **NautilusTrader**; crypto loop → freqtrade; paper trading → Alpaca.
  We build zero trading infrastructure.

## 2. Honest judgment (no tomarlo como verdad — incluida esta sección)

- The signal Pedro intuits (narratives lead/lag markets) **exists in the
  literature but is weak, decays fast, and is mostly arbitraged in liquid
  markets**. The realistic edge for a personal system is in *slow,
  narrative-driven* moves (geopolitical risk premia, commodity supply
  stories) — exactly what Atlas tracks — not in HFT-speed reaction.
- **LLMs are analysts, not oracles.** The defensible architecture uses them
  to produce *structured event-impact hypotheses* ("strikes on Gulf bases →
  tanker insurance ↑ → Brent spread" with direction + horizon + confidence),
  which a statistical layer tests. LLMs placing trades directly = the
  adversarial-headline failure mode, on our own ingest noise.
- **Backtest theater is the main risk.** Published Sharpe 5+ on news signals
  almost always means leakage (timestamps, survivorship, search-retrieved
  sentiment that includes the future). Our Measurement Provenance Principle
  applies with full force: every number carries its method; walk-forward
  out-of-sample only; paper trading before a single real peso.
- **Do NOT use the employer's algorithms.** Pedro already concluded this —
  affirmed: they are not open source, and using a trading employer's IP in a
  personal trading system is a legal/employment risk with zero upside given
  the open-source landscape. Public tools only.
- The fork with a trading engine: fine and expected (license is
  source-available); it validates the use case but creates no obligation.

## 3. What Atlas gives back (why this helps the product even if L4 never trades)

- **An external validation dataset for the movement signal** (#219): if
  thread velocity/surprise systematically *precedes* measurable market moves
  in related assets, that is hard evidence the movement model captures
  something real — Paper-grade material.
- **The "after what" axis**: market reaction timestamps are independent,
  high-precision event markers to anchor narrative timelines against.
- **#151 product overlay** gets its analysis layer for free.

## 4. Plan (phased, evidence-gated — each phase can kill the next)

**M0 — Event study (research only, ~no new infra).** Question: do Atlas
thread movements lead price moves in mapped assets? Method: map thread
domains → instruments (energy threads → Brent/natgas; Gulf conflict →
tanker rates/defense ETFs; LatAm unrest → COP/MXN, country ETFs); take
thread `changed_10h`/velocity spikes as events; classical event study on
daily/hourly returns (free data: yfinance/Alpaca). Output: a measured
lead/lag table with CIs. **Gate: if no exploitable lead exists, L4 stops
here and the result still feeds #219/#151 and a paper.**

**M1 — Signal dataset + backtest harness.** Private repo `atlas-markets`.
Pull Atlas API (threads, movement, research plans) into a feature store;
vectorbt walk-forward harness; baseline strategies (momentum, vol) as the
bar to beat. No LLMs yet — establish the statistical floor first.

**M2 — LLM analyst ensemble.** Anthropic + OpenAI + DeepSeek as three
*independent analysts* producing structured hypotheses from Atlas thread
state (schema: instrument, direction, horizon, confidence, reasoning,
falsifier). Selective consensus (TrustTrade-style): trade-hypothesis only
when ≥2 agree with calibrated confidence. Hypotheses are *features* for the
M1 harness, never direct orders.

**M3 — Paper trading.** Alpaca paper account, NautilusTrader or plain
Alpaca API execution, 3+ months live-paper with the same risk gates as
real money (position limits, max drawdown kill-switch, no leverage).
**Gate: out-of-sample paper Sharpe/drawdown must beat the M1 baseline
after realistic costs.**

**M4 — Small real capital.** Only if M3 passes its gate. Size that can be
lost without pain. This is 6-12 months away at minimum and that is correct.

## 5. Guardrails (standing)

- Private repo, separate credentials, consumes Atlas over its public API.
- No employer IP, ever.
- Measurement Provenance applies: leakage audit on every backtest;
  timestamps from Atlas maturity tiers (#221 — `provisional` data is
  exactly what you must NOT trade on as if consolidated).
- Heavy compute (backtests, embedding) runs off working hours, same as the
  Atlas crons (17:30+).
- Nothing here is investment advice; personal risk only.

## Sources

- https://github.com/TauricResearch/TradingAgents · https://tradingagents-ai.github.io/
- https://arxiv.org/html/2601.13082v1 (adversarial headlines vs LLM traders)
- https://arxiv.org/pdf/2603.22567 (TrustTrade selective consensus)
- https://aclanthology.org/2025.findings-emnlp.972.pdf (LLM finance agents survey)
- https://www.mdpi.com/0718-1876/20/2/77 · https://pmc.ncbi.nlm.nih.gov/articles/PMC12421730/
- https://arxiv.org/html/2505.16136v1 (GDELT macro alpha) · https://www.mdpi.com/2306-5729/10/10/158 (GDELT accuracy)
- https://gdeltcloud.com/ · https://geostrat.app/
- https://python.financial/ · https://github.com/wangzhe3224/awesome-systematic-trading · https://nautilustrader.io/ · https://arxiv.org/pdf/2504.02281 (FinRL contests)
