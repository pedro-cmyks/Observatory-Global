# Atlas — 2026-05-27 session summary

Date: 2026-05-27
Status: handoff doc (active)

## Vision recap (Pedro's words, end of session)

Atlas exists to answer:

> Given information flowing in real time, how can we build narrative
> threads that explain how news, public attention, markets, and world
> events connect, evolve, and shape perceptions across actors and
> time?

The paper series justifies the methodology behind that goal. Today's
session shipped Paper 1's full distillation cycle (topic classifier
quality measurement + LLM teacher loop). The wider questions Atlas
needs to answer — who covers what, who started talking about it, how
that connects to markets and other topics, how it evolves — are
addressed by Papers 2-8 (already scoped in
`2026-05-27-atlas-papers-master-plan.md`).

## What landed today

Six commits to `v3-intel-layer`:

| Commit | What |
|---|---|
| `ca3bb3b` | batch 02 score reviewed |
| `6807df8` | bootstrap CIs + Sonnet 4.6 zero/few-shot baseline |
| `01d5afb` | LLM annotator + Cohen's kappa + reasoning mining |
| `d9b723e` | papers master plan (series of 8) + outline reframe |
| `d7f3b45` | LLM multilingual vocab mining + migration 042 draft |
| (pending) | migration 042 applied to production + session summary |

API spend today: ~$2.40 USD (under the $10 ceiling Pedro authorized).
Tests: 57 passing across research scripts.

## Migration 042 applied to production (Supabase MCP)

`mcp__supabase__apply_migration` succeeded with name
`migration_042_llm_distilled_lexicon_expansion`. Effect across the
30 active atlas topics: lexicon size grew by 5-15 entries per topic
covering EN/ES/PT/IT/FR/DE.

Examples of new terms now live in production:

| Topic | Sample new multilingual terms |
|---|---|
| armed-conflict-escalation | `military offensive launched`, `escalade militaire`, `bombardamenti intensificati`, `militäroffensive gestartet` |
| agriculture-crop-risk | `récolte menacée par la sécheresse`, `ernteverlust durch dürre`, `perda de safra` |
| cyberattack-infrastructure | `ransomware hits water utility`, `ciberataque oleoducto`, `cyberangriff auf stromnetz` |
| currency-debt-stress | `crise cambial`, `crollo della lira`, `dépréciation monétaire` |
| disease-outbreak | `surto de doença`, `épidémie de`, `ausbruch der krankheit` |
| heat-health-risk | `mortes por calor`, `coup de chaleur`, `hitzewelle gesundheitsrisiko` |

Lex size delta per topic verified via
`SELECT cardinality(lexicon_terms) FROM atlas_topics` — matches
proposal predictions.

## Production re-classification status

The cron `com.atlas.atlas-topic-classifier.plist` runs every 30
minutes against `--window-hours 0.5`. Last successful run
`2026-05-27 13:48 UTC` (local Pedro time `08:48`). The gap since
then is because Pedro's Mac was asleep. On next wake, cron will
classify new signals using the post-042 lexicon.

Important boundary: cron only processes NEW signals each cycle. It
does NOT retroactively re-classify hot-window rows already classified
under pre-042 lex. Two ways to refresh those:

1. **Wait** for cron to roll over 48 cycles (~24h) — natural drift.
2. **Force backfill** with wider window via Supabase MCP `apply_migration`
   — attempts during this session timed out at 6h window. The script
   `backend/scripts/backfill_lexicon_topics.py` exists for that
   purpose; running it locally with `DATABASE_URL` from Fly would
   bypass MCP timeout.

## Re-benchmark blocker

The 64 reviewed gold signal_ids (from May 25 stratified sample) have
already been pruned to cold storage (24h hot retention is canonical).
Same-signal apples-to-apples lift comparison requires restoring those
signals from `/Users/pedro/AtlasArchive` back into `signals_v2`, then
re-classifying. That is a one-off operator action; ~64 rows,
trivial cost.

Alternative path: re-sample stratified 256 rows from post-042 hot
window, repeat Pedro labeling + LLM annotator + κ calculation. Costs
new labeling time + ~$0.80 API.

## Connection to Pedro's vision

Where each of today's deliverables sits against the wider questions:

| Pedro's question | Today's contribution | Future paper |
|---|---|---|
| How is information classified? | Lexicon distillation (mig 042) + benchmark methodology | Paper 1 |
| What sentiment does each source carry? | Existing `sentiment_fusion.py` + LLM annotator captures `annotator_evidence_role` | Paper 5 |
| Who covers a topic? | Source-quality stack (source_family, geo_confidence, is_state_media) | Paper 2 |
| How do topics connect to each other? | Brief co-occurrence (`related_topics` in `/api/v2/briefing`) | Paper 4 (thread aggregation) |
| How does perception evolve over time? | Atlas heat with velocity + surprise + duplication components | Paper 3 |
| Who started talking about it? | First-seen detection in `living-narrative-threads-v0` | Paper 4 |
| Who is amplifying it now? | `top_sources` + `source_mix` in thread response | Paper 4 |
| How are sub-threads forming? | `subthreads` field in thread response | Paper 4 |
| Are new topics emerging that don't fit the taxonomy? | Not solved today — flagged | Paper 8 |
| Does the visualization reveal the story? | Not measured today — flagged | Paper 7 |

The full Atlas vision is multi-paper. Paper 1 closes the
classification quality loop, which is the foundation: without
correct topic assignment, every higher-level metric (sentiment per
topic, who covers topic, how topic connects to other topics) is
built on noise.

## Open tracking — what next session must pick up

### Required to close Paper 1

1. Re-benchmark Atlas v2 post-042 — restore 64 reviewed signals from
   local archive into `signals_v2` (one-off script), re-run cron OR
   inline classifier, compare per-topic precision against the
   pre-042 Wilson CI baseline [46.50%, 70.46%].
2. Run `benchmark_bootstrap.py` again on the post-042 predictions
   against the same gold labels.
3. Document lift in
   `docs/research/atlas-paper/phase-1-validation/reports/migration-042/post-042-lift.md`.
4. If lift exists, decide whether to expand benchmark sample beyond
   N=61 (probably yes — N >= 150 is the methodology paper threshold
   per outline doc).

### Future research per the master plan

- Paper 2 (source quality): start with cross-source coverage matrix
  using existing ingest connectors.
- Paper 5 (sentiment fusion): human/LLM sentiment labels on a
  stratified 100-row headline sample.
- Paper 4 (threads): thread-level benchmark — sample 30 live threads,
  LLM-annotator scores each against the 7 product questions.

## Files added this session

Scripts:
- `backend/scripts/benchmark_bootstrap.py`
- `backend/scripts/llm_baseline_classifier.py`
- `backend/scripts/llm_baseline_compare.py`
- `backend/scripts/llm_annotator.py`
- `backend/scripts/kappa_calculator.py`
- `backend/scripts/llm_reasoning_mine.py`
- `backend/scripts/llm_topic_vocab_mine.py`
- `backend/scripts/propose_migration_042.py`

Tests (57 passing):
- `backend/tests/test_benchmark_bootstrap.py`
- `backend/tests/test_llm_baseline_classifier.py`
- `backend/tests/test_llm_annotator.py`
- `backend/tests/test_kappa_calculator.py`
- `backend/tests/test_llm_reasoning_mine.py`
- `backend/tests/test_llm_topic_vocab_mine.py`
- `backend/tests/test_propose_migration_042.py`

Migration:
- `backend/migrations/042_llm_distilled_lexicon_expansion.sql` (applied to prod via Supabase MCP)

Data snapshots:
- `backend/data/atlas_topics_snapshot_2026-05-25.json`
- `backend/data/atlas_topics_snapshot_pre_042.json` (rollback reference)

Canon docs:
- `docs/research/atlas-paper/2026-05-27-atlas-papers-master-plan.md`
- `docs/research/atlas-paper/2026-05-27-methodology-paper-outline.md` (updated)
- `docs/research/atlas-paper/2026-05-27-session-summary.md` (this file)

Phase 1 validation artifacts:
- Reviewed batch 02 + score (precision 64.52%, gate fail)
- Combined bootstrap CI report (N=61, precision 59.02%, CI [46.50%, 70.46%])
- Coverage-gap doc (6 of 30 topics labeled by Pedro)
- LLM baseline predictions JSONL (128 rows zero+few-shot)
- LLM-vs-Atlas comparison forest plot
- LLM annotator predictions JSONL (256 rows, Sonnet 4.6)
- Cohen's kappa report (κ = 0.549, moderate)
- Reasoning mining JSON + Markdown (zero-shot baseline)
- Migration 042 proposal Markdown + JSON
- Vocab mining JSONL (30 topics, 450 positive + 150 negative across 6 langs)

## Pedro's checklist for next session

1. Confirm Mac woke and cron resumed (`launchctl list | grep atlas`).
2. Restore the 64 reviewed signals from `/Users/pedro/AtlasArchive`
   into a staging table, run the classifier against them with
   post-042 lexicon, compute precision vs gold, write
   `post-042-lift.md`.
3. Decide whether to expand benchmark sample (Paper 1 N target
   >= 150).
4. Pick the next paper in the series to start.
