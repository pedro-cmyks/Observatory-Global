# Paper 8 — Open-Set Narrative Discovery: coverage + dynamism (result skeleton)

Date: 2026-06-30 · Author: Claude (Opus 4.8) · Status: **result skeleton** (the
RQ + the measured baseline; filled as the levers ship). Companion to
`2026-05-27-atlas-papers-master-plan.md` (P8 = "the discovery value of the dark
layer / the open-set funnel") and the engine spec
`2026-06-30-atlas-engine-recall-scoped-clustering.md`.

## Research question
Can a streaming system discover the *open set* of narrative topics from a
high-volume, multilingual, short-text feed — and keep that set **dynamic**
(topics appear, grow, shrink, retire with the world) rather than a fixed,
persisting list? Two sub-claims a deployed system must defend:
1. **Coverage** — what fraction of the signal mass is assigned to a topic.
2. **Dynamism** — does the topic set track reality over time, or freeze.

## Measured baseline (live prod, 2026-06-30) — a DIAGNOSTIC negative

**Coverage is tiny and it is a clustering-recall problem, not embedding or
promotion:**
- 534,000 signals → **239,233 embedded** → only **13,354 distinct signals in any
  topic = 5.6% of embedded (2.5% of total).**
- Per-country recall < 1% even for the highest-volume countries: **US 24,709→136
  (0.6%), CN 8,720→4 (0.0%), GB 10,117→25, RU 7,036→10.** A single global HDBSCAN
  pass drops ~94% of embedded signals as noise. (The HDBSCAN purity/recall cliff
  is characterized in `gdelt-decoupling §8`: no global config gives both.)

**Dynamism is broken — the topic set is frozen + sticky:**
- `dynamic_topics` / `emergent_clusters` last updated **2026-06-29 17:00**; the
  topic-forming cron was disabled in a 2026-06-29 infra consolidation and the
  successor engine (`unified-v2`) builds but is **not served** → serving reads a
  **~1-day-frozen snapshot**; **0 new topics in ~1 day.**
- Lifecycle is sticky: **54 of 68 "active" topics have `last_seen` > 3 days** yet
  remain `active`; **185 candidates** stuck un-promoted; only 14 ever retired.
- So "68 active topics" is not a measure of the live world — it is an accumulated,
  stale list. **A fixed topic count from a streaming feed is itself the failure
  signal.**

## The thesis the result will defend
Open-set discovery needs BOTH (a) **recall** — partition-scoped clustering over
the persisted corpus so minority/regional stories that drown in a global pass
form topics (the engine recall spec, R-track), AND (b) **dynamism** — a live
former + an aging lifecycle so topics appear and retire with the feed (B-track).
Either alone is insufficient: high recall into a frozen list still goes stale; a
live lifecycle over 5.6% recall still misses 94% of the world.

## Metrics / evidence to collect (as the levers ship)
- **Coverage curve:** % embedded signals clustered, global vs scoped-by-partition
  (target 5.6% → ≥15%; per-major-country <1% → ≥5%), with the black-hole/purity
  guard (#224) held at baseline.
- **Dynamism curve:** topic births/deaths per day; median `last_seen` age of
  "active" topics (should track the feed, not grow unbounded); candidate→active
  promotion latency; active-set size as a function of real event volume (should
  vary, not pin to a constant).
- **Recovery cases:** named stories that a global pass misses but a scoped pass
  recovers (CI 238→0, China 8,720→4 as before/after).
- **Honesty invariants held:** no fabricated topics; a partition with no coherent
  cluster yields none (the honest gap).

## Relation to the other papers
- **Paper 1** (split-brain→unified, evidence-role): recall is upstream of P1's
  precision — more topics = more evidence members to classify; but recall is NOT
  the same experiment (P1's ceiling is taxonomy #204).
- **Paper 5** (multilingual): CN 8,720→4 is a recall AND a voice gap — scoped
  per-country passes give non-English regional stories their own clustering space
  (ties to T1.5: the English-centric *assignment* bottleneck).
- **Paper 3/7** (heat / workflow): a dynamic, well-covered topic set is the
  substrate the heat + analyst surfaces draw from.

## Intervention 1 — dynamism: a natural before/after (in flight 2026-06-30)
The frozen-lifecycle negative had a precise, diagnosable cause — a clean systems
result for the paper:
- **Diagnosis.** Pipeline forensics (ingest/embed/lexical-assign all LIVE; only
  the topic-forming tail frozen at 06-29 19:04) localized it to the M1 embed
  runner: Step 1 (embed) ran under `set -e` as a FATAL step, so an asyncpg
  statement-timeout (a large/slow embed backlog) aborted the run BEFORE the
  topic-projection steps. Compounded by the topic-forming cron being disabled in
  the 06-29 consolidation while the successor wasn't yet served.
- **Intervention.** (a) make the embed step non-fatal so the projection always
  runs; (b) revive the topic-forming cron mindful + off-peak (efficiency cores,
  scheduled in the gaps so it never stacks — stacking had crashed the machine).
- **Expected after (the measurement, ~24–48h):** `dynamic_topics` resumes
  forming new topics + retiring stale ones (`stale_k=2`/`retire_m=4` by
  `snapshots_since_seen`); the active-set size tracks event volume instead of
  pinning to a constant; the 54 stale-but-active topics drain. **This is the
  dynamism curve's negative→positive — a controlled before/after, not a tuned
  demo.** (Verification scheduled.)

## Intervention 2 — coverage: the scoped-pass lever (planned)
The coverage negative (5.6%) has its lever specced + an R0 probe written
(scoped per-country HDBSCAN over persisted embeddings) — the planned before/after
on the coverage curve, run off-peak, gated on the purity/black-hole guard (#224).

## Negative-result honesty
Both negatives (5.6% coverage, frozen lifecycle) are recorded BEFORE the fixes,
with the exact prod queries in the engine recall spec §1 — so each lever's lift
is a real, reproducible before/after, not a cherry-picked after. A *systems*
discovery paper's contribution is precisely this: the measured failure, the
localized cause, and the controlled intervention — not just the final number.
