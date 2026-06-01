# Narrative Cluster Evidence Roles — Design

Date: 2026-06-01  
Status: Draft for review  
Related: `2026-05-29-emergent-topic-discovery-design.md`,
`docs/specs/2026-05-25-atlas-narrative-intelligence-framework.md`

## Context

The current Atlas topic pipeline is too binary for the product goal.
`signal_topic_assignments` plus the e5-base scope gate can produce a
90%-precision kept set, but the first live coverage report showed only
`17.77%` of 24h topic assignments kept. That is acceptable for strong
claims, but not acceptable as Atlas's visible coverage of the world.

The root problem is the unit of classification. A single headline often
mentions several domains, actors, and consequences. Asking the system to
decide whether that isolated headline "is" a fixed topic collapses several
semantic roles into one binary decision. Atlas should instead classify
signals inside a narrative cluster:

```
signal -> candidate topic(s) -> narrative cluster -> evidence role -> thread tier
```

The existing topic classifier and scope gate remain useful. They become
candidate and confidence signals, not the only product truth.

## Goals

1. Keep the current `signal_topic_assignments` + scope gate as a recall and
   confidence layer.
2. Move the visible Atlas model toward narrative clusters / dynamic threads as
   the primary object.
3. Add an evidence-role classifier that labels each signal's role inside a
   cluster.
4. Use LLMs only as teachers for labeling and calibration, not as production
   classifiers for every signal.
5. Preserve a 90% precision target for strong `verified` claims while raising
   visible coverage toward at least 80% through `candidate` and `context`
   tiers.
6. Capture LLM teacher rationales in structured form so they can guide feature
   design, error analysis, and future distillation.

## Non-goals

- Do not remove `atlas_topics` or `signal_topic_assignments`.
- Do not call Anthropic/OpenAI/DeepSeek for every production signal.
- Do not promote low-confidence rows as verified evidence.
- Do not require Pedro to hand-review thousands of rows. Human review should
  focus on criteria, disagreements, and confusing examples.
- Do not build a full persistent `dynamic_topics` lifecycle in this first
  increment. This spec defines the evidence-role layer that will feed it.

## Model Roles

Atlas will use two complementary model layers.

### Topic Candidate Layer

Existing layer:

- `backfill_lexicon_topics.py`
- `signal_topic_assignments`
- `score_assignments_gate.py`
- `gate_score`, `gate_kept`, `gate_model`

This layer answers: "What known domain anchor might this signal touch, and how
confident is that candidate?"

### Evidence Role Layer

New layer:

- input: signal + cluster + candidate-topic features;
- output: role, confidence, and optional reason-code features;
- production model: local student model trained from teacher labels;
- teacher data: multi-vendor LLM labels plus structured rationales.

This layer answers: "What job does this signal perform inside this narrative?"

## Evidence Role Taxonomy

The first role set should stay small enough to train and audit:

| Role | Meaning | Product treatment |
|---|---|---|
| `primary_evidence` | Direct evidence of the cluster's core claim or event. | Can support verified thread claims. |
| `context` | Background, history, surrounding condition, or indirect mention. | Visible as context, not proof. |
| `reaction` | Political, institutional, public, or market reaction to the core event. | Useful for movement/source framing. |
| `analysis` | Opinion, explainer, forecast, editorial, or analytic interpretation. | Useful for framing, not raw event evidence. |
| `entity_reference` | Signal mainly matters because it mentions an entity connected to the thread. | Useful for entity graph and related threads. |
| `noise` | Does not belong in the cluster/thread. | Suppressed. |

The role set intentionally separates coverage from proof. A row can be useful
without being primary evidence.

## Teacher Label Schema

Each teacher model should emit one JSON object per `(cluster, signal)` pair:

```json
{
  "schema_version": "atlas-evidence-role-teacher-v1",
  "signal_id": 123,
  "cluster_id": "snapshot-id/local-cluster-id",
  "headline": "...",
  "cluster_label": "...",
  "cluster_description": "...",
  "candidate_topic_slug": "armed-conflict-escalation",
  "role": "primary_evidence",
  "role_confidence": 0.0,
  "belongs_to_cluster": true,
  "supports_cluster_claim": true,
  "reason_codes": [
    "direct_event_match",
    "same_actor",
    "same_place"
  ],
  "rationale": "Short explanation of why this role was chosen.",
  "alternate_role": "context",
  "teacher_model": "deepseek-chat",
  "teacher_vendor": "deepseek"
}
```

`rationale` is not used verbatim in production. It is retained for:

- auditing why teachers disagree;
- mining recurring reason codes;
- creating features for the local student model;
- writing paper methodology examples.

## Reason Codes

Teacher rationales should be normalized into a small reason-code vocabulary.
Initial codes:

| Code | Meaning |
|---|---|
| `direct_event_match` | Headline directly describes the cluster's event. |
| `same_actor` | Same central actor/entity as the cluster. |
| `same_place` | Same country, city, or region. |
| `same_time_window` | Event is temporally aligned with the cluster. |
| `causal_update` | Headline describes a cause, escalation, or consequence. |
| `official_action` | Government, court, military, company, or institution acts. |
| `public_reaction` | Protest, market, public, or political reaction. |
| `analysis_frame` | Interpretive/explanatory framing rather than raw event. |
| `background_only` | Mentions the subject as context only. |
| `entity_only` | Relevant mainly through a named entity. |
| `generic_roundup` | Roundup/compilation headline with mixed topics. |
| `off_topic` | Does not support the cluster. |
| `insufficient_context` | Headline alone is not enough to decide. |

The student model does not need to generate prose. It can learn from features
derived from the labels and reason codes.

## Teacher Panel

Use a small teacher panel for training data:

- Anthropic Claude/Sonnet via API when available.
- OpenAI/Codex-compatible model via API when available.
- DeepSeek chat.

Panel policy:

- `3/3` same role: high-confidence training row.
- `2/3` same role: usable training row with lower consensus confidence.
- no majority: disagreement queue, not training gold.
- `noise` from at least two teachers: safe suppression candidate.
- primary/context disagreement: high-value audit row.

Pedro should review only small disagreement packets, not the full corpus.

## Pilot Dataset

First pilot should be deliberately small:

- 20-30 clusters from recent `emergent_clusters` snapshots.
- 10-20 signals per cluster, balancing:
  - centroid-near examples;
  - centroid-far examples;
  - high `gate_score`;
  - low `gate_score`;
  - repeated/roundup headlines;
  - multiple languages.
- Target: 300-500 `(cluster, signal)` rows.

The sample should include the current failure modes:

- large low-coverage topics such as election legitimacy, flood/landslide, gang
  security, fuel subsidy, oil/gas;
- healthy high-coverage topics such as disease outbreak, heat health,
  migration, corruption;
- emergent clusters with generic labels like "News Headlines Overview" so the
  model learns to detect roundup/noise.

## Student Model

First student should be simple and local:

- embedding model: `intfloat/multilingual-e5-base`;
- features:
  - signal embedding;
  - cluster centroid embedding;
  - cosine(signal, centroid);
  - headline-to-cluster-label cosine;
  - headline-to-cluster-description cosine;
  - Atlas `gate_score`;
  - Atlas candidate confidence;
  - matched-term count;
  - source language;
  - source family;
  - country match to cluster top countries;
  - cluster size/cohesion;
  - teacher-derived reason-code labels as training targets/features for
    analysis, not required at inference.
- model: multinomial logistic regression first; calibrated classifier if needed.

The student predicts:

- `evidence_role`;
- `role_score`;
- optionally `belongs_to_cluster`.

No LLM is called at inference time.

## Product Tiers

Thread visibility should combine cluster quality and evidence roles:

| Tier | Criteria | Product meaning |
|---|---|---|
| `verified` | coherent cluster + enough `primary_evidence` with high role scores | Strong Atlas claim. |
| `candidate` | coherent cluster + mixed primary/context/reaction evidence | Visible but not asserted as verified. |
| `context_rich` | mostly context/reaction/analysis, low primary evidence | Useful background/source framing. |
| `suppressed` | noisy cluster or too many `noise` roles | Hidden by default. |

The goal is not 80% verified coverage. The goal is:

- verified precision >= 90%;
- visible coverage (`verified + candidate + context_rich`) >= 80%;
- suppressed rows mostly true noise or generic roundup artifacts.

## Data Outputs

First implementation can write file artifacts before adding tables:

- teacher labels:
  `docs/research/atlas-paper/phase-1-validation/labels/evidence-role-teacher/`
- consensus labels:
  `docs/research/atlas-paper/phase-1-validation/labels/evidence-role-consensus/`
- student reports:
  `docs/research/atlas-paper/phase-1-validation/reports/evidence-role/`

Persistent table candidate for later:

```sql
CREATE TABLE thread_evidence_roles (
    signal_id BIGINT NOT NULL,
    cluster_snapshot_at TIMESTAMPTZ NOT NULL,
    cluster_id BIGINT NOT NULL,
    role TEXT NOT NULL,
    role_score DOUBLE PRECISION,
    belongs_to_cluster BOOLEAN,
    model_version TEXT NOT NULL,
    reason_codes TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (signal_id, cluster_snapshot_at, cluster_id, model_version)
);
```

Do not add this table until the file-based pilot shows useful signal.

## Metrics

Report these together:

- `verified_precision`: precision of verified primary evidence claims.
- `visible_coverage`: share of cluster members visible as verified/candidate/context.
- `primary_evidence_precision`: correctness of `primary_evidence` rows.
- `role_macro_f1`: role classifier quality across the six roles.
- `noise_suppression_precision`: how often suppressed rows are truly noise.
- `teacher_agreement`: 3/3, 2/3, no-majority distribution.
- `coverage_by_topic`: effect on low-coverage Atlas topics.
- `coverage_by_language`: guardrail against multilingual regressions.

## Operating Constraints

- LLM teacher runs are offline/batch, never required for app requests.
- Teacher prompts must request concise rationales and reason codes.
- Do not store secrets or raw API responses containing credentials.
- Use `/Users/pedro/AtlasLocalWorker/.env` for local teacher runs when needed.
- Keep prompts and schemas versioned in the repo.
- All production inference must run from the off-iCloud local worker/runtime.

## First Increment

1. Build a read-only sampler from latest `emergent_clusters` and
   `signals_v2`.
2. Generate a 300-500 row teacher packet.
3. Run three teacher models on that packet.
4. Build consensus labels, keeping rationales and reason codes.
5. Train/evaluate a local multinomial role classifier.
6. Produce a report showing whether visible coverage can approach 80% while
   preserving >=90% precision for verified claims.

## Open Questions

- Should `context_rich` appear in the primary UI or only inside Thread Focus?
- Should generic roundup clusters be suppressed immediately or used as
  source/language health indicators?
- Should the first student predict reason codes too, or only use them for
  analysis?
- How much teacher disagreement should trigger Pedro review versus being
  excluded automatically?

