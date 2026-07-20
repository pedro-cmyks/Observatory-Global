# F3b measurement — body embeddings in the headline-calibrated e5 space

**Date:** 2026-07-20 · **Verdict: PASS** (gate criteria met decisively) ·
Harness: `backend/scripts/measure_body_embed_neighbors.py` (repeatable) ·
Raw numbers: `2026-07-20-body-embed-measurement.json`

## Question

`/dossier/connections` neighbors run whitened e5 cosine (all-but-top k=1,
NEIGHBOR_TAU=0.40) calibrated on HEADLINE-derived centroids. Do 300-800-word
article bodies (a different text distribution) behave in that space, or do
they degrade it? Engine-surgery rule: measure BEFORE serving.

## Method

24 active dynamic topics (centroid_vec, non-umbrella) × up to 6 evidence
URLs → fetched through the F1 pipeline (honest yield: 17 usable bodies
across 11 topics — GDELT-firehose URLs are mostly walled, consistent with
every yield measurement today). Bodies + their headlines embedded with the
engine's own `research_semantic.embed_texts` (multilingual-e5-base,
`passage:` prefix, snapshot-identical pooling). Pos pairs = text ↔ OWN
topic centroid; neg = text ↔ 8 random other centroids. Raw + whitened
cosine; AUC, p50 gap, behavior at the served tau.

## Result (whitened space — the one that serves)

| | body | headline baseline |
|---|---|---|
| AUC | **0.9983** | 0.9208 |
| pos p50 | 0.588 | 0.599 |
| neg p50 | −0.005 | −0.014 |
| gap p50 | 0.593 | 0.613 |
| pos ≥ tau(0.40) | **94.1%** | 64.7% |
| neg ≥ tau | **0.7%** | 0.0% |

**Body embeddings separate BETTER than headlines in the whitened space** —
more text, more signal, and the headline-fit whitening transfers. The
served tau keeps 94% of true-topic bodies and passes 0.7% of impostors.
(Raw space floods for both — same anisotropic cone as always; whitening
remains mandatory.)

## Caveats (honest)

- n=17 samples / 11 topics — modest; the margin (AUC .998 vs .921) is far
  larger than the sample noise, but re-run the harness when the cache is
  richer (it is repeatable and cheap).
- Yield-biased sample: only extractable outlets contribute bodies.
- Bodies truncated at 4000 chars (e5's 512-token window truncates further).

## Consequence (wired same day)

`/dossier/connections` neighbor links now carry `basis: 'centroid' |
'body-e5-whitened'`: pins with fetched bodies get a second representation
(mean body embed) through the SAME whitening + tau. Additive lane — its
failure never costs centroid neighbors; bases never silently mixed.
