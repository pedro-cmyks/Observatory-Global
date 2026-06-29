# Taxonomy revision via multi-model / multi-persona ensemble (#204)

Date: 2026-06-29 · Status: IN PROGRESS · Author: Claude (Opus 4.8) + ensemble
Origin: the Unified Engine A/B (`docs/specs/2026-06-29-atlas-unified-engine.md`
§16 F3.2b) showed topical precision vs the current taxonomy is ~40–52% for BOTH
the lexical and embedding engines — i.e. the bottleneck is the **taxonomy/labels**,
not the assignment engine. This program rebuilds the taxonomy and measures the lift.

## Why an ensemble annotator (the method, for the paper)

A single annotator (human or one LLM) carries one bias and gives no measure of its
own reliability. An ensemble of **several models × several personas** does two
things a single annotator can't:
1. **Reduces single-annotator bias** — different model families + different
   analyst lenses disagree in different places; the consensus is more robust.
2. **Makes reliability measurable** — inter-annotator agreement (Fleiss/
   Krippendorff κ) per category becomes a quality signal: high κ = the category
   is clear and separable; low κ = it is ambiguous and must be revised. This is
   the paper-grade evaluation the production-label LLM judge could not give
   (that judge was confounded by label quality — see the engine spec §16 F3.2b).

Ensemble: **DeepSeek** (`deepseek-chat`), **OpenAI** (`gpt-4o`), **Gemini** (CLI),
and **Claude** (Opus 4.8, via the orchestrator/subagent path — the org's Anthropic
API credits are dry, so Claude annotates through the agent path, not the API).
Provider-neutral client: `backend/scripts/ensemble/model_clients.py`.

## Phase A — force-fit diagnosis (DONE, 2026-06-29)

`backend/scripts/ensemble/phase_a_diagnose.py`. The ensemble classified a sample
of **gate-kept evidence** headlines (what the engine currently treats as the
verified spine) against the current 30 categories WITH an explicit `OUT_OF_SCOPE`
option (routine politics, business, sport, culture, human-interest, satire,
procedural items that aren't themselves a crisis).

**Result (50 distinct gate-kept evidence headlines):**

| annotator | OUT_OF_SCOPE rate | agrees w/ current label |
|---|---|---|
| DeepSeek | **46%** | 50% |
| GPT-4o (partial, rate-limited) | 22% | 69% |
| **ensemble unanimous OOS** | **30%** | — |

So **30% (ensemble-unanimous) to 46% (DeepSeek)** of signals the gate KEEPS as
evidence have **no honest home** in the crisis taxonomy — they are force-fit into
the nearest crisis bucket. Concrete force-fits:
- *"The last-minute Amazon buy that saved my marriage in the heatwave"* → **Heat health risk** (a shopping/lifestyle article)
- *"Lilio – L'Apostolo del Tempo: il libro … genio calabrese"* → **Armed conflict** (a book review)
- *"family gathers in memory of victim in unsolved OTR shooting"* → **Armed conflict** (a local human-interest memorial)

**Diagnosis confirmed, and it is STRUCTURAL:** the taxonomy is 100% crisis/risk
framed with no `out-of-scope` / non-crisis option, so the gate's recall errors
land as topical-precision errors. The rewrite must (a) keep Atlas crisis/risk
focused (the narrative-analyst wedge) and (b) add a rigorous **OUT_OF_SCOPE
reject** — precision via honest rejection, not by expanding into all-news.

Artifact: `docs/research/taxonomy-revision/phase-a-diagnosis.json`.

## Phases B–D (next)

- **B — propose v2 taxonomy (ensemble):** each model × persona (geopolitics
  analyst / wire taxonomist / ontology purist / end-user journalist / skeptic)
  proposes a revision + the OUT_OF_SCOPE policy → synthesize a candidate v2.
- **C — gold annotation:** N signals labeled by every model × persona →
  inter-annotator κ per category; majority → gold (the unconfounded benchmark);
  low-κ categories get revised.
- **D — re-measure:** old vs v2 topical precision on gold (the 40–52% → X lift).

Then Pedro runs a large interactive round against Atlas to validate before any
production swap.
