# Subject Geography Math-First Design

**Date:** 2026-07-12  
**Status:** Approved design  
**Primary issue:** GitHub #238  
**Roadmap links:** P3.4 C7 voice asymmetry, P2.5 actor quality, P0.6 publishable dossier

## Goal

Build a deterministic, read-only subject-geography inference and evaluation
layer that distinguishes what a Narrative Thread is about from which countries
or outlets covered it. The first delivery measures and explains subject-country
candidates across the complete topic universe. It does not yet change chips,
ranking, lifecycle, persistence, or public API contracts.

## Product Decisions

1. There is no semantic `LIMIT 100`, top-N topic ceiling, or silent omission.
   Every relevant topic is processed and represented in the output.
2. Cursor pagination and bounded database batches are operational controls, not
   information filters. The run continues until the full selected state space
   is exhausted.
3. LLMs do not classify subject geography, choose countries, adjudicate
   disagreements, or manufacture ground truth.
4. Atlas uses deterministic text signals, gazetteers, multilingual patterns,
   embeddings, consensus, entropy, temporal stability, and ablations.
5. The LLM boundary remains the publishable dossier: it may synthesize prose
   only after evidence, provenance, relationships, contradictions, and
   uncertainty have been computed.
6. The model may abstain. An explicit unknown is better than presenting a
   coverage country as the subject.

## Scope and Issue Closure

This design advances #238 but does not claim to close it. The issue closes only
after three separately verifiable stages:

1. **Measure/infer:** this read-only complete-universe report, deterministic
   fixtures, invariants, reason ledger, and ablations.
2. **Persist/serve:** a reviewed subject-geography contract stored at the
   correct signal/thread layer, with coverage geography retained separately.
3. **Reconcile product:** chips, cross-language deduplication, thread detail,
   and geo navigation consume the contract and pass production smokes.

C7 remains read-only until Stage 2. Its 2026-07-12 false positives demonstrate
why coverage geography cannot stand in for semantic subject geography.

## Current Truth Model

Atlas must preserve three distinct geographic dimensions:

- **Subject geography:** where or whom the event/story is about.
- **Coverage geography:** countries attached to member signals by the coverage
  pipeline; useful for describing the information sphere, not subject truth.
- **Outlet origin:** where the publisher is based; a voice/provenance feature,
  never subject geography.

`archive_story_units.top_cc` is an independent historical cluster signal. It is
useful as a comparison feature but is not gold and must not be labeled as truth.

## Complete-Universe Processing

The report enumerates all `dynamic_topics` rows in the chosen lifecycle scope,
including active and candidate rows and any deprecated rows requested for
historical evaluation. Results are grouped by lifecycle state and quality lane;
junk, thin, ambiguous, and abstained rows remain visible.

Database reads use stable cursor pagination such as `(id > last_id ORDER BY id)`
and bounded member batches. Batch size can be tuned for memory and database
health, but the CLI has no topic-count ceiling and emits completion metadata:

- rows discovered;
- rows processed;
- rows emitted by lifecycle/quality lane;
- failures and retries;
- whether the cursor reached exhaustion.

A run that does not reach exhaustion is incomplete and cannot be reported as a
full-universe result.

## Deterministic Subject-Country Features

### Signal-level features

For each member signal, candidate countries come only from explainable inputs:

- exact country/place mentions in the headline;
- existing multilingual and native-script country patterns;
- gazetteer matches with word-boundary and ambiguity handling;
- available NER place entities, preserving verified/unverified provenance;
- distinctive place/entity neighbors in embedding space;
- source-independent repetition across member headlines.

Body boilerplate, publisher origin, and raw coverage-volume order cannot create
a subject candidate by themselves. They can only appear in the comparison and
provenance ledger.

### Cluster/thread aggregation

For candidate country `c`, the report computes a transparent component vector:

```text
subject_score(c) =
    0.35 * headline_geo_support
  + 0.20 * native_pattern_support
  + 0.15 * ner_gazetteer_support
  + 0.15 * member_consensus
  + 0.10 * embedding_neighborhood_consistency
  + 0.05 * temporal_stability
  - coverage_only_penalty
  - ambiguity_penalty
```

Each component is normalized to `[0, 1]`. The report retains the component
values, candidate distribution, entropy, top-two margin, supporting member IDs,
languages, snapshots, and reason codes. The weights are an initial transparent
baseline and must be evaluated by ablation rather than treated as doctrine.

### Abstention

The engine returns no primary subject when independent evidence is insufficient,
the candidate entropy is high, or the top-two margin is unstable. It still emits
the complete candidate ledger. No fallback copies the first coverage country
into `subject_country`.

## Evaluation Without LLM Classification

The first stage evaluates the method using deterministic and structural tests:

1. **Known fixtures:** explicit headline cases already documented in #238 and
   geo regression tests, including Venezuela, Iran, Palestine, Belén/Belém,
   native-script cases, and multi-country events.
2. **Cross-language consistency:** language slices of the same event should
   converge on compatible subject distributions.
3. **Temporal stability:** adjacent snapshots should not change subject without
   changed member evidence.
4. **Leave-one-source-family-out:** removing a dominant publisher/source family
   must not flip the subject solely because coverage volume changed.
5. **Ablation:** remove each component and report changes in fixture accuracy,
   abstention, stability, and disagreement.
6. **Embedding perturbation:** small member-sample changes should not produce
   large subject shifts unless the semantic cluster itself changed.
7. **Independent-proxy comparison:** compare against coverage countries and
   `archive_story_units.top_cc`, labeled as disagreement rather than error when
   no deterministic fixture resolves truth.

Human editorial review is deferred to the P0.6 publishable-dossier exit. It is
not a prerequisite for running or improving this mathematical layer.

## Outputs

The read-only CLI produces:

- a complete JSON report with run-completion metadata;
- a Markdown summary by lifecycle/quality lane;
- a machine-readable per-topic candidate ledger;
- an ablation report;
- a known-fixture score report;
- explicit `read_only`, `no_llm_classification`, and `complete_universe` fields.

Outputs must distinguish measured facts, inferred candidates, weak proxies,
and unknowns.

## Error Handling

- Missing optional NER data reduces feature availability; it does not abort the
  topic or silently substitute coverage geography.
- Missing embedding data places the topic in an explicit degraded lane and
  continues processing.
- Database timeouts retry the current cursor batch and record the retry.
- Partial runs state `complete_universe=false` and preserve the last cursor for
  resumption.
- No error path writes lifecycle, topic membership, or subject fields.

## Out of Scope for Stage 1

- schema migrations or persistent subject-country columns;
- API or frontend contract changes;
- country-chip reordering;
- cross-language topic merges;
- C7 promotion to UI/ranking/cron;
- LLM country classification or LLM-generated gold labels;
- event-marker hover/enrichment, which belongs to a separate structured-event
  receipt issue.

## Acceptance Criteria

- The run processes the complete chosen topic universe with cursor exhaustion
  evidence and no topic-count ceiling.
- No LLM call participates in subject inference or evaluation.
- Coverage geography and outlet origin remain separate from subject candidates.
- Known fixtures pass deterministic expectations, including explicit
  abstention for ambiguous cases.
- Every inferred candidate exposes components, provenance, uncertainty, and
  reason codes.
- Ablations, cross-language consistency, temporal stability, and
  leave-one-source-family-out results are included.
- The implementation is read-only and cannot affect serving behavior.
- The result states exactly which #238 stage it completes and what remains
  before the issue can close.
