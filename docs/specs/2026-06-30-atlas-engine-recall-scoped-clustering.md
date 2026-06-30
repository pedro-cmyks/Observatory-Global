# Spec — Atlas Engine: recall via scoped clustering (#229, the lead engine lever)

Date: 2026-06-30 · Branch: `v3-intel-layer` · Status: **DRAFT for Pedro's review.**
Author: Claude (Opus 4.8). The self-eval (2026-06-30) of the attention/anomaly
spec concluded RECALL is the engine's #1 lever and was only *referenced*, never
*specced*. This specs it. Companion to `2026-06-29-atlas-unified-engine.md`,
`2026-06-29-atlas-engine-gdelt-decoupling-syndication.md` (the HDBSCAN cliff),
and `2026-06-30-atlas-engine-attention-anomaly-roles.md` (which waits on this).

> **One sentence.** Atlas embeds everything (239K signals) but clusters almost
> nothing into topics (5.6% of embedded; <1% per country even for 24K-signal
> countries) — global HDBSCAN drops ~94% as noise, so most real stories never
> form a topic. The fix is **scoped clustering passes** over the persisted
> embedding corpus (by country / region / time partition), merged + anchor-
> guarded into the global topic set — recovering the regional stories (CI's
> 238→0, China's 8,720→4) that a single global pass drowns.

---

## 1. Problem — measured 2026-06-30 (live prod)

| metric | value |
|---|---|
| signals total | 534,000 |
| signal_embeddings (embedded corpus) | 239,233 |
| distinct signals in ANY topic | **13,354 (5.6% of embedded, 2.5% of total)** |
| active topics | 68 (median 84 sig, min 30, max 2402) |

Per-country recall (24h signals → in a topic): **US 24,709→136 (0.6%), CN
8,720→4 (0.0%), GB 10,117→25 (0.2%), RU 7,036→10 (0.1%), IN 8,186→16, MX/BR/ID
~3.6K→2–3.** Every high-volume country clusters **<1%** of its signals.

**Conclusion:** the bottleneck is NOT embedding (239K done) and NOT promotion
(the gate works) — it is **clustering assignment**. A single global HDBSCAN pass
captures a thin spine and discards the rest as noise. This is the structural
cause of the L2 dishonesty (CI: a 238-signal surge that never formed a topic →
the alert layer had nothing real to point at → the fake "Flood disaster" lead).

## 1.5 SECOND root cause — the topic layer is FROZEN + sticky (not dynamic)

(Pedro's instinct 2026-06-30: "68 fixed makes no sense — nothing in Atlas
persists, everything is dynamic." Verified — he was right.)

The 68 "active" topics are **not a live set; they are a ~1-day-frozen, stale
snapshot:**
- `dynamic_topics` last created/updated **2026-06-29 17:00**; `emergent_clusters`
  last snapshot **2026-06-29 17:00**. The `emergent-snapshot` cron that forms /
  ages / retires dynamic topics was **booted OFF in the 06-29 consolidation** —
  and `unified-v2` (which IS building) is **not served** (read flag OFF). So
  serving reads a frozen snapshot; **no new topic has formed in ~1 day.**
- Even pre-freeze the lifecycle is **sticky**: **54 of 68 "active" topics have
  `last_seen` > 3 days** yet stay `active`; only 1 created in the last 2 days;
  **185 candidates stuck** un-promoted, only 14 ever retired. So topics
  accumulate and persist instead of appearing/growing/retiring.

**Implication:** the recall problem is TWO problems. (A) clustering drops 94% as
noise (§2) — and (B) the topic LIFECYCLE is frozen + sticky, so even the topics
that DO form don't refresh, retire, or get replaced by fresher ones. Scoped
clustering (§3) fixes (A) but is wasted if (B) leaves the output frozen. **Both
must ship.** (B) is also the cheaper, more urgent fix: revive a live topic-former
(either flip serving to the already-building `unified-v2`, or re-enable a
mindful emergent-snapshot) + make retirement actually age stale topics out
(`snapshots_since_seen` / `last_seen` → `state` transitions). This is open-set
discovery's core invariant: **topics must appear and disappear with the world.**

**ROOT CAUSE + PARTIAL FIX (2026-07-01).** Pinpointed: ingest/embed/lexical-assign
were all LIVE; only the topic-forming tail froze. The M1 embed runner
(`run-embed-hot-corpus.sh`) ran Step 1 (embed) under `set -e` as a FATAL step —
when embed hit an asyncpg statement-timeout (a large/slow embed backlog, ~59K
pending, #241), the whole runner aborted BEFORE Steps 2–4 (attach / `etl_topic_
members` / `build_unified_topics`), so `topic_members` stopped refreshing at
06-29 19:04. **Fixed:** made Step 1 non-fatal (`|| echo … non-fatal`) — the ETL
projects fresh LEXICAL assignments and doesn't need embed to fully succeed — and
re-ran `etl_topic_members` once by hand → `topic_members` fresh again
(latest-member signal 06-29 19:04 → **06-30 17:52**, +4,810 evidence rows).
Synced to AtlasLocalWorker. **STILL FROZEN:** the SERVED layer — `/threads` reads
`dynamic_topics` (via `emergent_clusters`, last 06-29 17:00) because the
emergent-snapshot former is OFF and serving hasn't flipped to `topic_members`.
Unfreezing serving = **E4** (§7): flip the F0.3 read-flag to the now-fresh
`unified-v2`/`topic_members`, OR revive a mindful emergent-snapshot. That is a
serving cutover (read-path + parity), Pedro's call — NOT done here.

## 2. Root cause (verified, not re-investigate — see gdelt-decoupling §8)
The HDBSCAN sweep already proved there is **no global config with both high
recall and high purity**: `leaf` → purity 1.0 but shatters (Gaza recall 0.04,
~70% noise); `eom`/large `min_cluster_size` → recall 0.97 but a mega-blob
(896/1074 rows, purity 0.49 = the #224 black-hole). The recall ceiling is
**intrinsic to global clustering of headline-only short text**. Two compounding
factors:
1. **Global drowning.** A country's regional story (hundreds of signals) is a
   minority cluster in a 200K global space → HDBSCAN treats it as noise.
2. **Windowed input.** The emergent-snapshot historically clustered a ~15K hot
   WINDOW, not the persisted 239K corpus (#223 paid for persistence; #229 lever 1
   = cluster over the persisted corpus to dissolve the 15K cap).

## 3. The lever — scoped passes over the persisted corpus
Partition the embedded corpus and cluster WITHIN each partition (where the
regional story is the MAJORITY, not noise), then merge into the global set.

- **Partition keys (measure which wins, §6 R0):** (a) `country_code`, (b) region
  (country groups), (c) `country × time-window`, (d) topical pre-bucket (coarse
  embedding k-means then HDBSCAN per bucket). Start with **country** — the
  per-country evidence above makes it the obvious first cut.
- **Per-partition HDBSCAN** with partition-tuned `min_cluster_size` (small
  partitions need a smaller floor than 30) over `signal_embeddings` (persisted,
  not the 15K window).
- **Merge + anchor-guard (#224).** Scoped topics dedup against existing global
  topics by centroid similarity; the anchor-centroid guard prevents the
  same-domain conflation that caused the black-hole. A scoped topic that
  duplicates a global one merges; a genuinely new regional one promotes.
- **Honesty:** scoped topics carry their partition provenance; nothing is
  fabricated — a partition with no coherent cluster yields no topic (the honest
  gap, same as today).

## 4. Success metric (the A/B)
Primary: **% of embedded signals that land in a topic** (today 5.6%) and
**per-country recall** (today <1%) — both UP, WITHOUT purity collapse (the #224
black-hole rate must not worsen; reuse `engine_ab_report.py` purity/coherence/
black-hole columns). Target a first milestone: lift overall recall 5.6% → ≥15%
and per-major-country recall <1% → ≥5%, black-hole ≤ today's 12–19%. Paper 8 gets
its result (the recall negative→positive turn).

## 5. Compute discipline (NON-NEGOTIABLE — the crash lesson)
Re-clustering 239K embeddings PER partition is the heaviest job in Atlas.
- **STRICTLY off-peak on the M1**, around the embed cron (17:30/23:30/05:30),
  efficiency cores (`taskpolicy -b`) + a load guard + MPS-fallback. NEVER during
  Pedro's work hours (the M1 crashed at load 177 from stacked compute).
- Build + measure OFFLINE first (a scoped pass on ONE country, scored against the
  global pass) before any cron wiring. No production cron change until the A/B
  proves the lift on a sample.
- Reuse the existing emergent-snapshot machinery (it's OFF now) — extend it with
  a partition loop, don't add a new always-on heavy cron.

## 6. Phases (executable)

**B-track (URGENT, parallel — fixes the freeze §1.5, cheaper than R):**
- **B0 — unfreeze serving.** Decide + do: either (a) flip the read flag to the
  already-building `unified-v2` (`ATLAS_SERVE_THREADS_FROM_TOPIC_MEMBERS`, after a
  parity eyeball — the F0.3 parity passed), or (b) re-enable a mindful
  emergent-snapshot on the M1 (off-peak). (a) is faster + needs no heavy compute.
  *Decision E4 below.*
- **B1 — dynamic retirement.** Make the lifecycle age stale topics out:
  `snapshots_since_seen` / `last_seen` past a threshold → `state` active→dormant→
  retired; promote stuck candidates on momentum. Pure-SQL/light. So "active"
  means *currently alive*, not *ever seen*.

**R-track (recall via scoped clustering — the bigger, heavier fix):**
- **R0 — measure the partition (offline, daytime-safe SQL + one M1 sample).**
  Per-country embedded-signal counts; run ONE scoped HDBSCAN pass on a high-volume
  country (US or CN) over its persisted embeddings; score recall + purity vs that
  country's slice of the global pass. Decides the partition key (§3) + the
  min_cluster_size curve. *(The SQL half is daytime; the single-country HDBSCAN is
  light enough for a measured daytime run OR the next off-peak window.)*
- **R1 — scoped pass (off-peak M1).** Loop partitions, HDBSCAN each over persisted
  embeddings, label survivors (reuse the DeepSeek labeler). Write to a staging
  topic set (isolated, NOT serving).
- **R2 — merge + anchor-guard.** Dedup staging vs active `dynamic_topics`;
  promote new regional topics; the #224 anchor guard blocks conflation.
- **R3 — A/B + cutover.** `engine_ab_report` extended with the §4 recall metric;
  flip serving (more topics) only on a measured recall lift without purity loss.

## 7. Decisions (need Pedro) + my defaults
- **E1 — partition key.** *Default:* country first (the evidence is per-country),
  measure region/topical next. *Alt:* topical pre-bucket (language-agnostic, but
  needs a coarse clustering step first).
- **E2 — recall vs purity trade.** How much black-hole are we willing to accept
  for recall? *Default:* hard-cap black-hole at today's rate; prefer more small
  pure regional topics over fewer big ones (the opposite of the #224 failure).
- **E3 — scoped topics: separate lane or merged?** *Default:* merge into the one
  `dynamic_topics` population (on-thesis: one topic model), provenance-tagged.
- **E4 — unfreeze approach (B0, urgent).** *Default:* flip serving to the
  already-building `unified-v2` (no heavy compute; the A/B already showed it wins
  + parity passed) — this makes serving live again immediately. *Alt:* re-enable a
  mindful emergent-snapshot on the M1 (off-peak, more compute, keeps v1). Leaning
  flip-to-v2, because it ALSO advances F4 and removes the dead-old-cron gap.

## 8. Why this is the lead lever (vs the other engine work)
- Fixes the L2 §3 split-brain at the ROOT (CI gets a topic → the alert layer has
  something real → no fake disaster). The attention/anomaly roles only enrich the
  68 topics that exist; THIS makes more exist.
- Unblocks `anomaly→movement` (more topics = more movement coverage) and the
  `attention` role (more topics to bind to) — both wait on this.
- Multilingual recall (T1.5): the English-centric ASSIGNMENT bottleneck is partly
  this — scoped per-country passes give non-English regional stories their own
  space to cluster (CN 8,720→4 is both a voice gap AND a recall gap).
- Paper 8 (open-set discovery): turns the measured negative (0.2–5.6% coverage)
  into a result.

## 9. Cross-refs
#229 (the program this specs); gdelt-decoupling §8 (the HDBSCAN cliff — do not
re-investigate); #224 (anchor-guard / black-hole — the merge guard); #223
(persisted embeddings — the substrate); #162 (multilingual — scoped passes help);
attention/anomaly spec (waits on this); Paper 8 (recall), Paper 1 (the engine
experiment). Honesty invariants unchanged (no fabricated topics; gate stays
evidence-only; verified=false on social).
