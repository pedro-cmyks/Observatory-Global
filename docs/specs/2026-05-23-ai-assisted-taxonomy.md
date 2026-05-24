# AI-assisted atlas-topic taxonomy expansion

**Status:** Path A implemented across the six low-lex priority topics; Paths B/C remain specs.
**Author:** 2026-05-23 session.
**Context:** PR #197 (v2 classifier), #199 (mig 034 precision), #200 (mig 035 recall), #201 (hierarchy + related topics), and #205 (Path A pilot via mig 036).

## Why

The current atlas-topic classifier is **purely rule-based**:

- `atlas_topics.gdelt_theme_hints` — manually curated arrays of GDELT GKG codes
- `atlas_topics.lexicon_terms` — manually curated substring matchers against the headline
- `backend/scripts/backfill_lexicon_topics.py` — single-statement SQL that fires when `lex_count >= 1 OR theme_hits >= 1` and scores via a confidence formula

Zero machine learning is involved in topic assignment. Sentiment is the only path that uses transformers (`xlm-roberta-base` for NLP sentiment + multilingual NER + distilroberta NLI framing), and even those are off-the-shelf pre-trained models — never fine-tuned on Atlas data.

The 2026-05-23 coverage audit measured:

- Global recall before Path A: **13.08% of 24h-eligible signals** received any atlas_topic (up from 10.73% before mig 035+035b).
- Global recall after the first Path A pilot: **13.35%**. The global lift is modest because only one topic changed.
- 87% of unclassified signals have themes — the classifier just isn't looking for them.
- 64% of unclassified are `xx` language (multilingual; lex terms are English-only).
- Topic taxonomy itself (30 topics across 10 domains) is hand-curated. There is no systematic process for adding topics, retiring topics, or splitting topics as the world's narrative density shifts.

This spec proposes three complementary AI-assisted paths to lift recall and quality without abandoning the rule-based core (which gives us interpretability, idempotent backfills, and SQL-only operations).

## Paths

### Path A — LLM-generated lexicon expansion (lowest risk, ship first)

Use Claude / GPT to expand `atlas_topics.lexicon_terms` per topic, including multilingual variants. The LLM never assigns topics directly; it only suggests terms that humans (or the rule engine) consume.

**Pipeline:**

1. For each topic, pull 200 random recent headlines that v2 classified with high confidence (lex-supported, conf >= 0.75) — these are the topic's "exemplar headlines".
2. For each topic, pull 200 random recent headlines that v2 classified with low confidence (theme-only, single hit) — these are the "false-positive candidates" to AVOID matching.
3. Single prompt per topic to an LLM:

   > "Topic: `disease-outbreak`. Domain: `public-health`.
   > Description: '...'.
   > These 200 headlines are real examples of this topic: [...].
   > These 200 headlines were tagged with the topic but probably do NOT belong: [...].
   > Existing lexicon terms (English): [...].
   > Propose 40 new substring matchers — 15 English, 8 Spanish, 8 French, 5 Portuguese, 4 German. Each must appear in at least one real example and not appear in any false-positive. Output JSONL."

4. Human review of the LLM proposal (5 minutes per topic, 30 topics = 2.5 hours one-shot).
5. Append accepted terms to `atlas_topics.lexicon_terms` via a normal migration.

**Expected impact:** 64% of unclassified is `xx` language — multilingual lex would let many of those signals match. Sample fix on `currency-debt-stress` (peso, lira, naira added in mig 034) jumped lex_pct from 0% → 84.9%.

**Cost:** ~30 LLM calls × ~3K tokens each = ~90K tokens. Trivial.

**When to do it:** First — biggest leverage, no architectural change, no schema change. Can be implemented in a single 4-hour session.

**Pilot result:** Implemented in `backend/migrations/036_election_legitimacy_multilingual_lex.sql` for `election-legitimacy-dispute`. The topic's lex-supported share moved **6.3% -> 31.6%**, high-confidence assignments moved **5 -> 27**, and multilingual terms produced **74%** of the lex-match volume. The accepted workflow is now sample-driven and SQL-verified: pull positives/negatives, propose multilingual terms from real headlines, measure candidate volume, spot-check precision, reject noisy terms, migrate, purge that topic's assignments, re-backfill, and measure lift.

**Second rollout result:** Implemented in `backend/migrations/037_armed_conflict_multilingual_lex.sql` for `armed-conflict-escalation`. This was intentionally precision-first: it removed noisy existing terms (`clashes`, `offensive`, `shelling`) and rejected tempting broad terms (`shots fired`, `opening fire`, `firing at`, `ataque armado`, `battlefield`) after spot checks showed local-crime, sports, historical, or metaphorical noise. Final live result after purge + 24h re-backfill: lex_pct **2.10% -> 6.56%**, high_conf **22 -> 85**, global v2 coverage **17.22%**. This does **not** clear the 30% Path A gate, but it is the right product tradeoff: avoid inflating armed-conflict with local armed incidents and use this result as evidence that the taxonomy may need a separate public-security/armed-incident topic later.

**Remaining low-lex rollout result:** Implemented in `backend/migrations/038_remaining_low_lex_multilingual_terms.sql` for `fuel-subsidy-unrest`, `food-price-stress`, `housing-cost-pressure`, and `mining-royalty-risk`. Results after purge + 24h re-backfill:

| Topic | Before lex_pct | After lex_pct | Before high_conf | After high_conf | Read |
|---|---:|---:|---:|---:|---|
| `fuel-subsidy-unrest` | 5.20% | **37.12%** | 2 | **136** | Gate cleared cleanly. |
| `food-price-stress` | 17.52% | 4.63% | 7 | **10** | Precision cleanup; removed noisy `shortage`/`hunger`, but current window has little food-pressure vocabulary. |
| `housing-cost-pressure` | 10.16% | 8.20% | 0 | **2** | Precision cleanup; Spanish housing protest terms help, but volume remains low. |
| `mining-royalty-risk` | 12.33% | **78.99%** | 0 | **100** | Gate cleared by a major coal-mine-disaster cluster; label should probably evolve toward mining/resource risk, not only royalty. |

Global v2 coverage after the full Path A rollout: **18.47%** of 24h eligible signals.

### Path B — Bootstrap-trained encoder classifier (medium term)

Train a small multilingual sentence encoder + linear head on the 21,919 high-confidence v2 assignments we already have. The encoder produces a topic probability vector per headline; predictions above a threshold supplement the rule-based classifier.

**Architecture:**

- Base model: `paraphrase-multilingual-MiniLM-L12-v2` (84MB, multilingual, fast). Already what spaCy + lex pipeline would use as a feature extractor.
- Training set: the 21,919 high-confidence v2 assignments as labels (precision >= 0.9 estimated). One-hot encode the 30 topics; multi-label.
- Loss: binary cross-entropy with negative sampling (sample 5 random topics per headline that didn't fire).
- Validation: hold out 20% per topic; track per-topic precision, recall, and F1.
- Inference: emit topic probabilities; combine with rule-based score via `score = 0.6 * lex_score + 0.4 * encoder_score` then apply min_confidence floor.

**Promotion gate:** Do not merge encoder scores into product ranking unless measured precision is at least **85%**, with **90%** as the target for production default behavior. Recall lift is useful only after that precision floor is met.

**Expected impact:** the encoder learns context patterns the lex/theme rules miss. Topics with low lex_pct (election-legitimacy 6.3%, fuel-subsidy 10.4%, mining 12.5%) get help from the encoder catching headlines that don't contain the lex terms verbatim but discuss the same narrative.

**Cost:** training on a single GPU machine — ~30 min on Mac M-series MPS or a free Colab T4. Inference per signal: ~5ms on CPU.

**Operational shape:**

- New table `signal_topic_encoder_scores (signal_id, topic_id, score, model_version, computed_at)`.
- New worker `encoder_topic_worker.py` reading from a queue, similar to NLP worker.
- briefing.py reads both `signal_topic_assignments` (lex) and `signal_topic_encoder_scores` (encoder), merges via `score = 0.6 * lex + 0.4 * encoder`.
- v2 lex-classifier stays as ground-truth signal. Encoder is a refinement layer.

**When:** after Path A confirms the data is rich enough.

### Path C — LLM-assisted taxonomy revision (cyclical, every 4–8 weeks)

Use an LLM to recommend changes to the topic taxonomy itself (split / merge / add / retire) based on the actual narrative density in the data.

**Pipeline:**

1. Every 4–8 weeks, sample 1000 headlines that v2 was unable to classify.
2. Pass to LLM with the current taxonomy:

   > "Current atlas_topics taxonomy: [JSON dump of 30 topics + parent_domain + lexicon_terms].
   > These 1000 headlines did not match any topic. Cluster them into 5–15 themes. For each cluster, propose: (a) does an existing topic almost fit (suggest amendment); (b) should a new topic be added (propose slug, label, parent_domain, initial lexicon_terms, initial gdelt_theme_hints); (c) is the cluster low-value noise (no action)."

3. Human review of the LLM proposal.
4. New migration (036, 037, ...) adds new topics or modifies existing ones; mig 035-style guardrails enforce precision before promoting.

**Expected impact:** taxonomy evolves with the world. Today's missing topics (crime/homicide, space launches, sports protest, large-scale environmental destruction beyond floods) get added when narrative volume justifies it.

**Cost:** ~10K tokens per cycle. Negligible.

**When:** start once we have ≥3 months of v2 production data so the "unclassified" pool reflects real long-tail narratives, not just current vocabulary gaps.

## Sequencing

1. **Path A** (multilingual lex expansion) — six-topic priority rollout is complete. Election, fuel, and mining cleared the 30% lex_pct gate; armed-conflict improved high_conf but stayed below the gate; food and housing became more precise but need either more multilingual evidence or taxonomy refinement.
2. **Path B** (encoder classifier) — design proposal only after Path A stabilizes and a labeled validation set can enforce the 85-90% precision gate.
3. **Path C** (taxonomy revision) — quarterly cadence once Path A + B are running and the unclassified pool reflects durable gaps rather than vocabulary gaps.

## Sentiment vs. tone — product decision

For the analyst-facing product, use **one sentiment**: Atlas sentiment.

- **"Tone"** historically means GDELT's V2Tone column — a single number per signal, computed by GDELT's own lexicon over the article text. Atlas stores this in `signals_v2.sentiment`. Range: roughly −10 (very negative) to +10 (very positive); we divide by 10 for the frontend ±1 scale.
- **"Sentiment"** in modern usage refers to NLP-based polarity from a transformer model. Atlas stores this in `signals_v2.nlp_sentiment`, computed by `xlm-roberta-base` for multilingual headlines and `cardiffnlp/twitter-roberta-base-sentiment` for English. Range: same.
- **Implementation can still return source labels** (`gdelt`, `nlp`, `nlp_weighted`) for provenance and debugging, but the UI should not present multiple competing sentiment systems as if they were separate product metrics.

GDELT Tone is useful as a fallback, calibration input, or benchmark against Atlas sentiment. It should not be shown as a parallel yardstick beside Atlas sentiment in normal product flows. The desired product state is: one normalized Atlas sentiment value, with provenance available when needed.

## Decisions from analyst review

- User-facing sentiment: collapse around Atlas sentiment; keep GDELT Tone internal for fallback/calibration.
- Topic/model precision floor: target 85-90% precision before product promotion. Below that, stay in benchmark/shadow mode.
- Topic correction UI: do not build a user-facing "this topic is wrong" affordance for now. It adds product and training complexity before the taxonomy pipeline is stable. Use SQL samples, benchmark labels, and controlled review sets first.

## What's already done

- **Hierarchy is already exposed**: as of PR #201 (2026-05-23) the briefing returns `topics_by_domain` (parent_domain grouping) and `related_topics` (co-occurrence map). Frontend can render the tree without further backend work.
- **Co-occurrence pairs already validate the taxonomy is conceptually coherent**: fuel-subsidy ↔ labor-strike (373 co-signals), food-price ↔ housing-cost (210), water-drought ↔ flood-disaster (149), migration-border ↔ forced-displacement (95), armed-conflict ↔ forced-displacement (56). These are exactly the "related narratives" an analyst would expect.
