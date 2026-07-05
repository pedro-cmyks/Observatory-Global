# Self-training flywheel + history-as-asset (2026-07-04, status: DESIGN)

Pedro's ask, mid-blitz: (1) a process that keeps self-training from the
historical backlog so gold never "gets lost" again; (2) is 70% of the content
junk? (3) how does HISTORY make threads and other processes better?

## 1. The 70% answer — measured tonight

From the archive blitz (2,680 DeepSeek votes at time of writing):
**70% incorrect / 30% correct** on lexicon-matched hard-topic candidates.
Pedro's intuition is numerically exact — WITH the honest scoping: this is 70%
of *candidates that already matched a crisis lexicon* being off-topic
(substring noise, routine coverage, crisis-words-without-crisis), NOT 70% of
the firehose being ads. It is a first-class Paper 1 number: **lexicon
candidate precision ≈ 30%** — the quantitative justification for the gate's
existence and for the semantic lane. (The separate "how much of the firehose
is promo/lifestyle" question is measurable the same way — one annotator pass
over a RANDOM signal sample with a content-class schema; queued as a
flywheel byproduct below.)

## 2. The flywheel (design)

Principle: **labels are the only asset that compounds.** Every pass through
data — live or historical — should leave permanent, deduplicated, versioned
labels behind. Never re-judge what's judged; never lose what's judged.

Layers (two exist, two to add):

| layer | cadence | source | status |
|---|---|---|---|
| L1 nightly accumulator | 03:30 cron | live 7d decision band | ✅ armed (com.atlas.goldgrowth) |
| L2 archive miner | weekly (or on-demand) | external archive, ever-growing | ✅ built today — make it a cron |
| L3 frozen eval slices | per era | held-out from L1/L2 BEFORE training | ❌ to add — the overfit guard |
| L4 disagreement queue | weekly | vendor splits + human/strong-model tiebreak | ❌ to add |

Mechanics that make it self-maintaining:
- **Dedup ledger** (`labeled-ids.txt` + headline-normalized keys) means each
  archive re-run only labels NEW material — as retention rolls signals out of
  the hot DB into the archive (the export cron), the miner picks them up
  later. Nothing is ever lost to retention again: **the archive is the
  training reservoir, the hot DB is just the serving window.**
- **Budget guard**: per-topic positive targets (200 now; raise deliberately)
  stop spending when a topic is funded. Weekly L2 run costs ~$1-3 only while
  topics are under target.
- **L3 frozen eval**: before ANY training merge, split 15% of each new batch
  (stratified by topic+era) into `eval-frozen/` — never trained on. Retrains
  report against BOTH the frozen slices and OOF; a model that only improves
  OOF is overfitting the flywheel's own labels. (This absorbs the #243
  temporal-holdout item.)
- **L4 disagreement queue**: the 20% vendor splits are the most informative
  rows (boundary cases by definition). Weekly: strong-model or human
  tiebreak on that queue only — highest label-value per dollar.
- Byproducts each cycle: mined NEGATIVES feed the noise-class lexicons
  (#248 damp lists); per-topic keep-rates feed hint pruning (mig-067 style);
  a quarterly random-sample content-class audit answers the "how much is
  promo" question with a trend line.

## 3. History as an asset for the OTHER processes

The hot DB's 7-day window is a SERVING choice, not an analysis limit. The
archive (May 3+, growing forever) becomes queryable without touching prod:

- **Warm analytical tier — DuckDB over the archive.** DuckDB reads the
  partitioned `*.jsonl.gz` directly (`read_json_auto('.../**/*.jsonl.gz')`).
  Zero infra, zero Supabase cost, runs on the M1. Every research script
  (backtests, ablations, audits) points at it instead of the 7d hot window.
- **Kalman/movement backtests**: tonight's backtest was underpowered (33d of
  snapshots); archive volume series per topic-lexicon extend it to the full
  corpus era. Re-run `backtest_movement_leading` over archive-derived series.
- **Identity continuity (today's collapse class)**: resurrection matching
  can consult ARCHIVED centroids/label history instead of only the live
  table — a topic that existed in June is recognizable in August. Fold into
  the F4/identity engine session.
- **Trajectories/universe**: longer per-topic tracks (the scrubber currently
  caps at what emergent_clusters retains).
- **Better threads directly**: with archive-backed member history, a thread's
  "started 23h ago" can become "active since June 12" — narrative AGE becomes
  honest, and long-running stories (Peru) stop looking newborn after every
  identity hiccup.

## Build order (small-model-safe after Day 2-3)

1. Cron-ify the archive miner (weekly, Sunday 04:00, budget-guarded) — 1h.
2. L3 frozen-eval split in `build_goldgrowth_corpus` merge path — 1h.
3. DuckDB warm-tier helper (`scripts/archive_query.py`, a thin wrapper) — 1h.
4. L4 disagreement queue export + tiebreak runner — 2h.
5. Archive-powered movement backtest re-run — 1 session (research).
