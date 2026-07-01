# GDELT theme-hint ablation — the reproducibility gate on Paper 1's 41.6% (PR3-05)

**Date:** 2026-07-01 · **Script:** `backend/scripts/gdelt_hint_ablation.py` (read-only,
repeatable) · **Gold:** `phase-1-validation/labels/2026-06-02-atlas-v2-batch-03.consensus-gold.jsonl`
(3-vendor consensus, the canonical N660 regime) · **Spec:** gdelt-decoupling §3.2 · **Ledger:** PR3-05.

## Why this exists
The Atlas classifier (`theme-hint-lex-v2`) reaches a topic through the JOIN
`s.themes && t.gdelt_theme_hints` — a GDELT-GKG theme overlap generates the candidate — then
qualifies via `theme_hits` (|themes ∩ hints|) and/or `lex_count` (matched lexicon terms). Four
docs cited a `gdelt_hint_ablation.py` as the 🔒 gate that must pass before theme-hints can be
removed; **it did not exist**. Removing the hints would kill the RSS/forum asymmetry and simplify
the engine — but only if they are not carrying real precision. This measures that.

## Method
Per gold assignment, decompose by mechanism (from the persisted `evidence`):
- **lexicon-recoverable** (`lex_count ≥ 1`): a standalone lexicon matcher keeps it after
  theme-hints are removed.
- **theme-hint-dependent** (`lex_count = 0`): only the GDELT-theme overlap carried it → it
  vanishes unless the **semantic** path recovers it.

The **ablated engine** = lexicon standalone (theme-hints removed). Stage 2 embeds each
theme-hint-dependent CORRECT headline vs its assigned topic's label+description (e5) and counts
cosine ≥ threshold as recovered.

## Result (Stage 1 — pure gold decomposition, threshold-INDEPENDENT)

| engine | correct / usable | precision |
|---|---|---|
| **baseline (with theme-hints)** | 270 / 660 | **40.9%** (canonical 41.6%, CI [37.8, 45.5]) |
| **ablated (lexicon-standalone)** | 235 / 487 | **48.3%** (+7.4pp) |

- **Theme-hint-dependent path: 173 assignments, only 35 correct = 20.2%** — HALF the baseline
  precision. The theme-only path is dominated by false matches (138/173 not-correct). This is the
  KILL-class-noise hypothesis (idioms like "killing it" firing the `KILL` GKG theme into
  armed-conflict), now measured.
- **Recall cost of removal: 35 correct assignments = 13.0% of all corrects.**

**Removing the theme-hints does not cost precision — it BUYS +7.4pp** by shedding a 20%-precision
noise source. The only cost is 35 true assignments (13%), addressed next.

## Result (Stage 2 — semantic recovery of the 35 lost corrects, threshold-SENSITIVE)

The 35 lost-correct headlines' e5 similarity to their topic descriptions lives in a **narrow
[0.728, 0.804] band** (median 0.780), so recovery is a cliff in the threshold:

| cosine threshold | recovered | semantic recall |
|---|---|---|
| 0.72 | 35 / 35 | **100%** |
| 0.75 | 30 / 35 | 85.7% |
| 0.78 | 18 / 35 | 51.4% |
| 0.80 | 2 / 35 | 5.7% |
| 0.82 | 0 / 35 | 0% |

This is the SAME unreliable taxonomy-similarity band R3.1 already flagged (cosine-over-descriptions
is diffuse, ~0.78–0.85). So semantic recovery is REAL but the operating threshold dominates: at a
moderate cut (0.72–0.75) the semantic path recovers 86–100% of the small true-loss; at a strict
cut it recovers little.

## Verdict (§3.2 decision rule): REMOVE-OK

The decision rule fires on TWO independent grounds:
1. **The lost assignments are measurably noise** — theme-hint-dependent precision 20.2% ≪ baseline
   40.9%. (Threshold-independent, robust.)
2. **Semantic recovers the small true-loss** — 85–100% of the 35 corrects at a moderate threshold.

So theme-hints can be demoted from a hard candidate-generator to (at most) a weak confidence
feature — consistent with the unified-engine plan. **Net effect: precision 40.9% → 48.3%, recall
cost ≤ 13% and 86–100% semantically recoverable.**

## Statistical rigor — CIs (PR3-10 slice, bootstrap 5000 + Wilson, batch-03 gold)

| quantity | point | Wilson 95% | bootstrap 95% |
|---|---|---|---|
| baseline precision (with hints) | 40.9% | [37.2, 44.7] | [37.3, 44.7] |
| ablated (lexicon-standalone) | 48.3% | [43.8, 52.7] | [43.7, 52.8] |
| theme-hint-dependent precision | 20.2% | [14.9, 26.8] | [14.5, 26.0] |
| **Δ ablated − baseline** | **+7.4pp** | — | **[5.2, 9.6]** |

Two intervals settle the claim: (1) the **ablation delta CI [5.2, 9.6] excludes zero** — removing
theme-hints improves precision *significantly*, not by noise. (2) theme-dependent [14.9, 26.8] and
baseline [37.2, 44.7] are **non-overlapping** — the theme-only path is significantly worse than the
engine average, confirming it is a net noise source, not a chance dip. (Computed by
`external`-style bootstrap in the PR3-10 slice; the baseline CI matches the canonical 41.6% band
[37.8, 45.5].)

## Honest caveats (paper-grade)
- **The ablated engine assumes lexicon becomes a standalone candidate-generator** (today it is
  gated behind the theme JOIN). The ablation MEASURES the outcome; making `lexicon_terms` a
  standalone matcher is the implementation follow-up (and is what the semantic path already does).
- **One benchmark, English-majority** (batch-03 N660). §3.3 names non-English gate recall as the
  deeper lever — untouched here. A non-English theme-hint ablation is a separate row.
- **Stage 2 is threshold-sensitive** (the cliff above) — do not quote a single recovery number;
  quote the curve. The robust claim is Stage 1 (theme-hints are net noise), not a specific recovery %.
- No temporal hold-out / CIs on the ablation itself (PR3-10 territory).

## Paper impact
Paper 1 (P1) gains a measured result: the GDELT theme-hints, long assumed a precision contributor,
are a **net noise source** on the canonical benchmark (theme-only precision 20.2% vs 40.9%
baseline; removal → 48.3%). This is the empirical justification for the unified engine's
GDELT-decoupling. Closes the PR3-05 experiment row.
