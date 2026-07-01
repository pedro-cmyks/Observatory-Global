# Crisis-only precision + gold reliability κ (PR3-10 core) — the successor to 41.6%

**Date:** 2026-07-01 · **Gold:** batch-03 3-vendor consensus (N=691; 660 usable) · **Ledger:**
PR3-10 · **Companion:** the theme-hint ablation (PR3-05) + its CIs (PR3-10 CI slice).

PR3-10's headline gap: **"the crisis-only precision (the real successor to 41.6%) is UNMEASURED,"**
plus no inter-annotator κ. Both measured here.

## Gold reliability — inter-annotator κ (Fleiss, N=684 rows with 3 annotators)
| statistic | value | reading |
|---|---|---|
| Fleiss κ (4-cat: correct/incorrect/partial/unclear) | **0.623** | substantial (Landis–Koch 0.61–0.80) |
| Fleiss κ (binary: correct vs not) | **0.734** | substantial, near-strong |
| unanimous (3/3 agree) | 69.6% | — |

The gold the 41.6% rests on is **reliable** (binary κ 0.734) — the precision numbers are not
measuring annotator noise. (Matches the earlier κ≈0.775 base for the #204 gold.)

## Crisis-only precision — the successor to 41.6%
The taxonomy was 100%-crisis (30 crisis categories, no reject class), so its precision was dragged
down by NON-crisis signals force-fit into crisis categories (#204's structural finding). DeepSeek
split each usable assignment into IN-SCOPE (genuinely the assigned crisis category) vs OUT (force-fit):

| subset | precision | share of usable |
|---|---|---|
| baseline (all usable) | 40.9% (270/660) | 100% |
| **CRISIS-ONLY (in-scope)** | **53.8% (170/316)** | 47.9% |
| out-of-scope (force-fit) | 27.1% (88/325) | **49.2%** |

**The successor to 41.6% is ~53.8%.** Nearly HALF the usable assignments (49.2%) are out-of-scope
force-fits at 27.1% precision — they, not the crisis classifier, are what pins the headline number
at ~41%. On the signals the taxonomy is actually FOR (genuine crisis), precision is **+12.9pp
higher**. This is the measured justification for the #204 reject class / crisis-relevance lens: the
fix is not a better crisis classifier, it is refusing the non-crisis half.

## Two independent levers compound
- Remove GDELT theme-hints (PR3-05): 40.9% → 48.3% (+7.4pp, CI [5.2, 9.6], significant).
- Restrict to in-scope crisis (this): 40.9% → 53.8% (+12.9pp).
Both attack DIFFERENT noise (theme-hint false matches vs non-crisis force-fits); a v2 engine that
drops theme-hints AND applies the reject class should clear both, well above the 41.6% headline.

## Honest caveats
- The IN/OUT split is DeepSeek-judged (one model, temperature 0), not human-labeled — a second
  annotator or the ensemble would tighten it (an anchoring-control pass is the PR3-10 remainder).
- Crisis-only precision is over the same batch-03 window; no temporal hold-out yet.
- κ is on the consensus decision, not on the (unbuilt) crisis-vs-non-crisis boundary itself.

## Anchoring control (blind vs hinted) — the crisis-only number, de-biased
The 53.8% split showed DeepSeek the ASSIGNED category ("is this about category X?"). Re-running
BLIND (headline only, "is this a genuine crisis or not?") tests whether the hint anchored the judgment:

| framing | crisis-only precision | IN-rate |
|---|---|---|
| hinted (assigned category shown) | 53.8% (170/316) | 47.9% |
| **blind (unanchored)** | **48.2% (188/390)** | 59.1% |

The hint made the judge STRICTER (47.9% vs 59.1% IN) → the hinted 53.8% is **~5.6pp optimistic**.
The de-biased, conservative crisis-only number is **≈48.2%** — still clearly above the 40.9%
baseline (+7.3pp blind / +12.9pp hinted). The claim (crisis-only ≫ headline) holds either way;
report the range **48–54%** with 48% as the unanchored floor.

## Temporal hold-out — DATA-LIMITED (honest gap)
Not computable on this gold: the batch-03 consensus rows carry NO timestamp, and the underlying
signals have been PURGED from `signals_v2` (retention). A true temporal hold-out needs a FRESH
labeled window from a different week — future work, flagged as data-limited (not a computable-now item).

## PR3-10 status after this — 4 of 5 done
DONE: Wilson/bootstrap CIs + inter-annotator κ (0.734) + crisis-only precision (48–54%, anchoring-
controlled) + anchoring-effect control. DATA-LIMITED: temporal hold-out (needs fresh labels).
REMAINS: `role_noise_rate` calibration. The core unknowns are answered — the gold is reliable
(κ 0.734) and the crisis-only successor to 41.6% is **≈48% (unanchored) to 54% (hinted)**.
