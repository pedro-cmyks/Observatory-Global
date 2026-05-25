# Path B Priority Label Results

Date: 2026-05-25  
Issue: https://github.com/pedro-cmyks/Observatory-Global/issues/203  
Input sample:
`docs/research/topic-quality/benchmark-samples/2026-05-25-path-b-priority-topics.jsonl`  
Labeled sample:
`docs/research/topic-quality/benchmark-samples/2026-05-25-path-b-priority-topics-labeled.jsonl`  
Score:
`docs/research/topic-quality/benchmark-scores/2026-05-25-path-b-priority-topics-score.json`

Note: the original sample was generated before the v2 semantic/evidence-role
schema. It remains score-compatible, and the score artifact was regenerated with
`atlas-topic-benchmark-v2`; `by_scope`, `by_evidence_role`, and
`by_supported_question` are empty until the sample is supplemented with v2
labels.

## Result

The first labeled benchmark did **not** clear the Atlas product-quality gate.

| Scope | Precision | Gate |
|---|---:|---|
| Overall | 80.85% | fail |
| Minimum | 85.00% | pass floor |
| Target | 90.00% | product target |

Per topic:

| Topic | Precision | Gate | Interpretation |
|---|---:|---|---|
| `disease-outbreak` | 100.00% | pass_target | Strong. Theme-only Ebola rows were valid in this sample. |
| `food-price-stress` | 90.00% | pass_target | Strong enough for target, with one primary-context miss. |
| `forced-displacement` | 81.82% | fail | Close to floor, but broad `exodus`/thin asylum rows need scope handling. |
| `gender-violence-rights` | 75.00% | fail | Main issue is substring noise: `rape` inside `parapente`. |
| `labor-strike-disruption` | 71.43% | fail | Specific strike rows are good; broad union/sindicato rows often belong to a broader labor/cost-of-living context. |
| `armed-conflict-escalation` | 69.57% | fail | Lex-supported war-operation rows are strong; theme-only rows mix current conflict, diplomacy, sports, and history. |
| `transport-corridor-disruption` | 66.67% | fail | Disruption rows are valid; broad corridor/entity terms also capture parent-thread candidates. |

## Error Types

The important finding is that not every failed row is the same kind of failure.

| Error type | Count | Product meaning |
|---|---:|---|
| `scope_mismatch` | 8 | The row is near the domain but assigned to a too-specific anchor. |
| `insufficient_context` | 5 | The headline alone is too thin. It should not train a hard negative. |
| `parent_thread_candidate` | 4 | The concept may be valid as a parent/entity thread, but not as a disruption/crisis child. |
| `primary_context_mismatch` | 4 | The matched term appears as background, not the main narrative. |
| `substring_noise` | 3 | Mechanical matching bug; safe to repair. |
| `off_topic` | 3 | True negative/noise. |

## Product Interpretation

This benchmark should **not** be read as "broad concepts are bad."

It shows that Atlas needs separate levels:

1. **Parent domain / broad thread**: health, labor, transport corridors,
   displacement, conflict, gender rights.
2. **Living child threads** inside that parent: Ebola expansion, health-worker
   strikes, Panama Canal drought/closure, Gaza refugee-camp casualties, Kyiv
   missile strikes.
3. **Evidence rows**: individual signals that support one child thread or
   appear as context for another.

Example:

- `Panama Canal` may be a legitimate large thread or entity-centered thread.
- It is not automatically evidence for `transport-corridor-disruption` unless
  the headline says closure, drought, blockade, delay, shipping disruption, or
  operational impact.

Example:

- A general health parent can contain multiple live child threads:
  - Ebola expansion and border preparedness;
  - hantavirus concern;
  - measles deaths;
  - hospital attacks around outbreak response.
- The Narrative Threads surface should be able to reload around that parent
  cluster and show the related child threads, rather than pretending there is
  only one fixed "Disease outbreak" card.

## Data Decision

Do not apply a broad lexicon purge just because a row failed this specific
assignment. Repairs should be typed:

- `substring_noise`: fix matching mechanics or replace term with safer phrases.
- `primary_context_mismatch`: improve primary-topic scoring and evidence role.
- `scope_mismatch`: route to a broader parent or neighboring child thread.
- `parent_thread_candidate`: keep as candidate for living thread hierarchy.
- `off_topic`: prune or downweight.
- `insufficient_context`: keep out of hard-positive/hard-negative training.

## Next Actions

1. Supplement this sample or the next sample with v2 semantic labels:
   `gold_scope`, `gold_evidence_role`, parent/child thread candidates, and
   supported Atlas questions.
2. Use `substring_noise` rows for immediate precision repairs.
3. Use `parent_thread_candidate` rows to design nested Narrative Threads:
   parent focus -> related child threads -> evidence.
4. Keep encoder/ranking promotion blocked until the benchmark clears 85%
   precision minimum and preferably 90% target.
