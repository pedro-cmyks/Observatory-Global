# Gate-recall by language — measured (master-consolidation T1.5 / L2 B4)

Date: 2026-06-26 · `scripts/gate_recall_by_language.py` on the current corpus,
model_version `theme-hint-lex-v2`.

## Result
| lang | scored | kept | kept_rate | deficit vs en | bias flagged |
|---|---|---|---|---|---|
| **en** | 14,358 | 4,711 | **0.33** (baseline) | — | — |
| **xx** (undetermined) | **6,921** | 727 | **0.10** | **+0.22** | **YES** |
| es | 7 | 1 | 0.14 | +0.19 | no (n too small) |
| de | 6 | 2 | 0.33 | −0.01 | no |
| pt | 6 | 3 | 0.50 | −0.17 | no |
| id | 6 | 1 | 0.17 | +0.16 | no |
| fr | 4 | 0 | 0.00 | +0.33 | no (n too small) |
| tr/ko/ro/sk/zh | ≤2 each | — | — | — | no |

## The reframe (important — corrects the L2 hypothesis)
The L2 review feared a broad **non-English gate bias** (the CI-French / Peru-
Spanish 0/43 failures). The measurement says something more precise:

1. **The gate keeps only 33% of even ENGLISH scored assignments** — the gate is
   strict for everyone. Paper 1's 41.6%→70% precision claim is **English-
   conditioned**; state that limitation.
2. **Detected non-English barely ENTERS scoring at all.** fr scored=4, es=7,
   de=6… The gate cannot be "biased against French" when it scores 4 French
   assignments total. The bottleneck is UPSTREAM: the lexical topic-assignment
   (`theme-hint-lex-v2`) is English-centric, so non-English signals rarely get a
   topic assignment to score in the first place.
3. **The real bias bucket is `xx` (undetermined language): 6,921 scored, kept at
   0.10 — a third of English.** "xx" is the large mis-/un-detected bucket
   (short/garbled/non-Latin headlines whose language wasn't tagged). The gate
   rejects it ~3× more.

## Implication (what to fix, and what NOT to)
- **NOT** a per-language gate-threshold recalibration (the script's default
  interpretation) — detected non-English has no sample to recalibrate against.
- **The fix is upstream:** get non-English signals INTO the topic-assignment
  pipeline — multilingual lexical/NLP assignment (#162) + the **semantic
  assignment** path (the one T2 just shipped for forums via embeddings, which is
  language-agnostic). The semantic route bypasses the English-lexical gate
  entirely — that is the cross-language recall lever.
- Improve language detection so the `xx` bucket shrinks (more signals get a real
  lang tag + proper handling) — #150 native geo-tagging is adjacent.

## Paper track
Paper 1: add the **English-conditioned** caveat to the gate-precision claim, with
this table. Paper 8 (open-set): the semantic-assignment route is the measured
cross-language recall path. Hand to the librarian.
