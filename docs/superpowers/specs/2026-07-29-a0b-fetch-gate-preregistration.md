# A0b — the fetch-side enforcement gate (pre-registration, frozen before any run)

**Date:** 2026-07-29 · **Status:** GATES FROZEN — measurement authorized (Pedro)
**Successor to:** GA (`docs/research/label-court/2026-07-29-court-enforcement-simulation.md`,
NO-GO) whose two structural findings define this gate: the shipped damp
(`_COURT_DAMP {failed:0.5, partial:0.85}`, live via ATLAS_RANK_V2) is +0.0pp by
construction because `/threads` selects the page by `recent_n_signals` BEFORE
ranking; and a naive over-fetch "paper-passes" GA's count-only conditions while
WORSENING major-door composition. This gate closes both loopholes explicitly.

## The intervention under test
Fetch-pool over-fetch: `/threads` fetches `M × limit` candidates (M ∈ {2, 3, 4}),
applies the SHIPPED ranking (incl. the existing court damp — no new rank code),
serves the top `limit`. Umbrella rows now carry court verdicts (Lever B live),
so the damp reaches the front page for the first time.

## Frozen conditions (all must hold for the adopted M; movement after seeing results = invalid)
- **C1 (global composition):** top-40 entailed-share ≥ **+15pp** vs baseline.
- **C2 (per-door composition — the paper-pass killer):** across the 5 most
  populated doors (incl. US, TR, DE), NO door's top-N entailed-share drops by
  more than **5pp** vs baseline.
- **C3 (newsworthiness guard):** the global top-10's median `recent_n_signals`
  must remain ≥ **50%** of baseline's top-10 median (court-entailed skews small
  — median 44 vs 711 lifetime; entailed-share alone promotes honest non-news:
  the Bieniemy-at-rank-8 witness).
- **C4 (coverage, carried from GA):** no door loses >25% of served rows;
  global top-40 ≥ 30 rows.
- **C5 (serving cost):** the over-fetched SQL at M× LIMIT, measured on prod
  (read-only EXPLAIN ANALYZE or timed fetch), stays within the endpoint's
  existing budget (no new timeout class; report p50/p95 vs baseline).

**Kill:** no M satisfies C1–C5 → fetch-side enforcement waits for court
coverage/relabel recovery; record and stop (the same discipline as GA).

## Method constraints
- Extend `backend/scripts/measure_court_enforcement.py` (do not rewrite);
  read-only; the ranking path imports the REAL shipped functions.
- Umbrella verdicts now exist — the simulation must use the CURRENT stamped
  field (post-Lever-B), and report the unchecked-share of each top-N alongside
  (withheld umbrellas ride as unchecked, never damped).
- Qualitative layer mandatory: enter/exit label diffs per door, judged (the GA
  protocol) — C1–C5 are necessary, not sufficient; the human-readable diff
  rides beside the verdict.
- If adopted: implement as `ATLAS_THREADS_FETCH_MULT` env (default 1 = today),
  two-night watch vs the simulation before staying on.
