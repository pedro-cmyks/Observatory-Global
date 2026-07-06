# L4 M0 — event study (#226): Atlas narrative spikes vs market |moves|

Substrate: archive story units 2026-05-04 → 2026-07-03 · events = category-day z>=2.0 vs trailing 21d · returns = Yahoo daily closes · inference = 10k permutations.

**HONESTY HEADER — pilot power only**: ~44 trading days, single regime (May-Jul 2026), |return| (volatility) not signed direction, UTC-day alignment. t0 = REACTION (same-day close contains the news); a LEAD claim is only t+1/t+2. Nothing here is tradeable evidence; it is the go/no-go for collecting MORE evidence.

| category → instrument @lag | n events | mean \|ret\| | baseline | ratio | perm p |
|---|---|---|---|---|---|
| agriculture-crop-risk | 0 (no spikes) | — | — | — | — |
| currency-debt-stress → GC=F @t+0 | 3 | 0.01499 | 0.01369 | 1.1 | 0.3796 |
| gang-control-urban-security | 0 (no spikes) | — | — | — | — |
| migration-border-pressure → MXN=X @t+0 | 3 | 0.00355 | 0.00447 | 0.79 | 0.6007 |
| migration-border-pressure → MXN=X @t+1 | 3 | 0.00526 | 0.00447 | 1.18 | 0.3321 |
| migration-border-pressure → MXN=X @t+2 | 4 | 0.00196 | 0.00447 | 0.44 | 0.918 |
| sanctions-diplomatic-pressure → GC=F @t+0 | 4 | 0.01026 | 0.01369 | 0.75 | 0.7033 |
| sanctions-diplomatic-pressure → GC=F @t+1 | 4 | 0.02066 | 0.01369 | 1.51 | 0.1166 |
| sanctions-diplomatic-pressure → GC=F @t+2 | 4 | 0.01192 | 0.01369 | 0.87 | 0.586 |
| sanctions-diplomatic-pressure → CL=F @t+0 | 4 | 0.03112 | 0.03488 | 0.89 | 0.5315 |
| sanctions-diplomatic-pressure → CL=F @t+1 | 4 | 0.04065 | 0.03488 | 1.17 | 0.3069 |
| sanctions-diplomatic-pressure → CL=F @t+2 | 4 | 0.01761 | 0.03488 | 0.5 | 0.8975 |

Candidate leads (p<0.10 at t+1/t+2): **0**

## Reading
- ratio > 1 = market moves MORE than baseline after an Atlas spike.
- t+0 rows measure REACTION (sanity check that the categories are market-relevant at all); only t+1/t+2 rows can support the L4 gate.
- With ~44 trading days, even p<0.10 is fragile — the honest verdict space is {collect-more, stop}, never {trade}.

## Verdict (the #226 gate)

**No exploitable lead found with honest timestamps → L4 build STOPS, per the
gate.** One suggestive cell (sanctions → gold @t+1: ratio 1.51, p=0.117) is
exactly the kind of underpowered near-miss that becomes a false alarm if
acted on at n=4 events.

Honest qualifier: this is an UNDERPOWERED NULL, not a disproof — 44 trading
days, 3-4 events per pair. The correct next move costs nothing: the
category-day series regenerates from the archive as it grows; re-run this
exact script at ~150+ trading days (≈October) and let the gate re-decide.
No L4 code, no overlay, no trading anything until then.

What the result DOES feed today (issue's fallback value):
- #219: market |moves| as external "after what" anchors — the t+0 rows show
  the mapped categories are at least market-relevant (reaction present).
- #151 overlay: stays gated (correctly) — the relation is unproven.
- Paper line: the leakage-honest protocol (t0=reaction, lead=t+1 only,
  permutation inference, |ret| not signed) is the method contribution.
