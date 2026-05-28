# Dual-annotator precision picture (post-044)

Date: 2026-05-28
Status: central Paper 1 finding

## The two estimates disagree massively

The same Atlas v2 classifier (post-migration-044 lexicon + theme hints)
scored against two annotators on the same stratified sample:

| Annotator | N | Topics | Precision | Wilson 95% CI |
|---|---:|---:|---:|---|
| Pedro (human, initial) | 61 | 6 | 73.77% | [61.56%, 83.16%] |
| Sonnet 4.6 (LLM, initial) | 243 | 30 | 38.68% | [32.78%, 44.94%] |

These differ by **35 percentage points**. Two causes compound:

### Cause 1 — topic coverage

Pedro only labeled 6 topics, and they skew toward the cleaner ones
(corruption 83%, constitutional 88%, cyberattack 100% post-044). The
LLM annotator covers all 30, including a long noisy tail that Pedro
never reached.

### Cause 2 — annotator strictness (the kappa gap)

Cohen's kappa between the two annotators on the overlap was 0.549
(moderate). The LLM is systematically stricter: it used `partial` 56
times and `incorrect` 108 times across 252 decisions, where Pedro used
`correct` far more freely. That strictness pushes the LLM precision
estimate down.

## Per-topic precision (LLM annotator, N=243, 30 topics)

| Tier | Topics |
|---|---|
| Strong (>=75%) | gender-violence (100%), disease-outbreak (92%), corruption (83%), constitutional (75%), cyberattack (75%), press-freedom (100%, n=1) |
| Mid (40-67%) | food-price (67%), armed-conflict (60%), labor-strike (60%), flood (50%), oil-gas (50%), housing (45%), migration (44%) |
| Weak (<=33%) | agriculture (33%), student-youth (33%), heat (25%), disinformation (25%), trade (25%), transport (25%), currency (18%), gang (18%), energy (20%), election (7%) |
| Zero | mining-royalty (0/12), fuel-subsidy (0/11), sanctions (0/9), humanitarian (0/8), telecom (0/4), water (0/4), forced-displacement (0/2) |

The zero-precision topics are the alarming part. `mining-royalty-risk`
scored 0/12 under the LLM annotator despite the earlier topic-quality
audit calling it 91% lexicon-supported and "promising". That is the
kappa disagreement in raw form: the lexicon-support metric and the
LLM's semantic judgement disagree completely on mining.

## Why this is the central Paper 1 result

1. **Single-annotator precision claims are unreliable.** The same
   classifier looks like a 74% system or a 39% system depending on who
   labels and which topics are covered. Any narrative-intelligence
   paper that reports a single precision number without inter-annotator
   agreement is overclaiming.

2. **Coverage bias is as large as the model's own error.** The 6 topics
   Pedro labeled are not representative of the 30-topic taxonomy. A
   stratified benchmark must cover the full taxonomy, weighted by
   production volume, before any global precision claim.

3. **The kappa gap sets the trust ceiling.** With kappa = 0.549, the
   precision estimate carries a structural uncertainty band of roughly
   +-35pp between annotators. Tightening that requires either
   adjudication (resolve LLM vs human disagreements case by case) or a
   third annotator to break ties.

4. **The zero-precision topics are the highest-value next audit.**
   mining-royalty, fuel-subsidy, sanctions, humanitarian, telecom,
   water, forced-displacement all scored 0 under the LLM. Either the
   LLM is miscalibrated on them or they are genuinely broken. The next
   migration cycle (045+) should adjudicate these specific topics with
   both annotators on the same rows.

## Method note on confidence intervals

N=243 gives a Wilson CI half-width of ~6pp; N=61 gives ~12pp. So the
LLM-annotator estimate is statistically tighter, but it is built on
lower-trust labels (kappa 0.549). The human estimate is higher-trust
but statistically loose and coverage-biased. Neither alone is
publishable; the pair, plus the kappa, is the honest story.

## Recommended next steps

1. **Adjudicate the zero-precision topics.** Pull the 0% topics'
   sampled rows, have Pedro label them blind, compute per-topic kappa,
   and decide whether each topic is broken or the LLM is miscalibrated.
2. **Expand Pedro gold beyond 6 topics** toward full-taxonomy coverage
   so the human estimate is no longer coverage-biased.
3. **Report both estimates with the kappa** in the paper; do not
   collapse to a single precision number.
