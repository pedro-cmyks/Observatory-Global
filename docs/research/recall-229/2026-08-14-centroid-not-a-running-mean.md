# `dynamic_topics.centroid_vec` is not a running mean — it is a copy of the last cluster

**Date:** 2026-08-14
**Status:** READ-ONLY DIAGNOSIS. **Nothing was written.** No lifecycle state
changed, no migration, no engine flag. SELECTs only (bounded, `statement_timeout`
set per connection). **For Pedro's eye before anything is built.**

**Trigger:** the 3 byte-identical `centroid_vec` pairs found during the
2026-08-14 duplicate-live-stories sweep
(`docs/research/recall-229/2026-08-14-duplicate-live-stories.md`): 6 active
non-umbrella topics, 3 pairs, distinct labels / categories / `agg_n_signals`,
identical 768-dim vectors.

---

## 1. Verdict

The duplicate pairs are a **symptom**. The mechanism is a variable-aliasing bug
in the incremental projection path, and it is **population-wide, not a
3-pair edge case**:

> **3,065 of 3,088 active non-umbrella topics (99.3%) carry a `centroid_vec`
> that is byte-identical to the centroid of a single one of their member
> clusters — the most recent one.** Candidates: 4,655 / 4,678 with a live last
> cluster (99.5%).

`dynamic_topics.centroid_vec` is documented and consumed as a *running mean over
the topic's member clusters*. In every incremental (nightly) run it is instead
**the plain mean of only the clusters attached during that one pass** — almost
always exactly one cluster, i.e. a verbatim copy of that cluster's centroid. The
topic's accumulated position is discarded every night.

Duplicates appear when two different identities happen to last-absorb two
byte-identical re-emissions of the same emergent cluster (§4).

---

## 2. The mechanism, with file:line

`backend/scripts/project_dynamic_topics.py`

1. **`Topic.members` is overloaded.** It is (a) the queue of member rows still
   to be INSERTed by `persist()` (`:1338-1342`) *and* (b) the weight `k` of the
   incremental mean, via `n_member_clusters` (`:522-524`).

2. **`attach()` uses that same count as `k`:**
   ```py
   :548  self.centroid = running_mean(self.centroid, self.n_member_clusters, np.array(cluster["centroid"]))
   :433  def running_mean(old, k, new): return (old * k + new) / (k + 1)
   ```

3. **`hydrate_topics()` replays history correctly — then clears the queue:**
   ```py
   :1236-1246   # replay: Topic(first cluster) then attach() each later member  -> centroid IS the true running mean here
   :1256        t.members = []   # already persisted
   ```
   The comment is right about its own purpose (don't re-INSERT member rows), but
   the assignment also resets `k` to **0**.

4. **Therefore the first `attach()` of the pass wipes the centroid:**
   `running_mean(old, 0, new) = (old*0 + new)/1 = new`.
   Second attach in the same pass → `(new₁+new₂)/2`, and so on. The persisted
   value written at `:1312` (`centroid_vec=$4`) is the mean **of this pass only**.

The same reset exists at `:1230` (no-live-members fallback) and `:1347`
(post-persist clear) — the aliasing, not any one line, is the defect.

**Introduced:** `8dfd9f0b` (2026-06-02, "phase6: incremental dynamic_topics
lifecycle wired into the snapshot cron") — i.e. the running centroid has been
fiction for the whole incremental era.

**`--rebuild` is unaffected** (`:1378-1383` skips `hydrate_topics`): a rebuild
replays every snapshot in one process with a growing `members` list, so it
produces a true running mean. **Rebuild and incremental therefore disagree about
what a topic's centroid is, given identical history.** That divergence is itself
a falsifiable check of this diagnosis.

---

## 3. Evidence

**A. Population scan** (`dynamic_topics` ⋈ latest `dynamic_topic_members` ⋈
`emergent_clusters`, md5 over `centroid_vec::text`):

| state | topics w/ centroid | last member cluster still live | `centroid_vec` == that cluster's centroid |
|---|---|---|---|
| active | 3,088 | 3,088 | **3,065 (99.3%)** |
| candidate | 4,956 | 4,678 | **4,655** |

The 23 active exceptions are the topics that absorbed ≥2 clusters in their last
pass (mean of 2+), plus the members-gone fallback path.

**B. The three pairs, resolved.** Their `dynamic_topic_members` rows point at
**different** `emergent_cluster_id`s — but at clusters whose *content* is
identical (same `sample_signal_ids`, same centroid, different snapshot):

| pair | twin clusters | cluster label | n | `md5(centroid_vec)` | `md5(sample_signal_ids)` |
|---|---|---|---|---|---|
| 4082 ⟷ 3150 | 79287 (08-13) → 4082 · 72927 (08-10) → 3150 | Assault in Rethymno | 9 | `3869a07d…` (both) | `d9738e8c…` (both) |
| 9161 ⟷ 8868 | 78104 (08-12) → 9161 · 75027 (08-11) → 8868 · 72063 (08-10) → **9161** | Spain Italy Border Checks | 14 | `503b5eb1…` (all 3) | `37c63694…` (75027, 78104) |
| 7748 ⟷ 7750 | 75511 (08-11) → 7748 · 78765 (08-13) → 7750 | Lula Accuses US and Rubio | 8 | `7395b3b1…` (both) | `11096044…` (both) |

Pairwise cosine between the persisted topic vectors: **exactly 1.0** in all three
pairs (cross-pair: 0.806 / 0.836 / 0.854 — normal).

Note the 9161 → 8868 → 9161 ping-pong: the *same* re-emitted cluster changed
identity twice in three nights.

**C. The shared served signals Pedro saw are exactly the twin cluster.**
Distinct signal ids reachable through each topic's `dynamic_topic_members →
emergent_clusters.sample_signal_ids`:

| pair | A sigs | B sigs | shared |
|---|---|---|---|
| 4082 / 3150 | 97 | 57 | **9** (= the 9-signal Rethymno-assault cluster) |
| 9161 / 8868 | 56 | 78 | **14** (= the 14-signal border-checks cluster) |
| 7748 / 7750 | 59 | 99 | **9** |

The 9 shared ids under 4082/3150 are the Greek Rethymno-port beating of a
51-year-old Briton (08-08 18:30 → 22:30 UTC, `tanea.gr`, `voria.gr`,
`news247.gr`, `rethemnosnews.gr`…) — the cluster's own label was
**"Assault in Rethymno"**, and *neither* serving label ("Rethymno Fire DEDDIE
Prosecution" / "Kypseli Murder Arrest") describes it.

**D. Byte-identical clusters are common, not exotic.** Over the last 14 days of
`emergent_clusters`: 38,240 rows / 30,552 distinct centroids → **4,535 duplicate
groups covering 12,223 rows (32%)**. A recurring story whose signal set does not
change between nightly passes re-clusters to a bit-identical mean.

---

## 4. Why only 3 duplicate active pairs, if 99.3% are copies

Because a twin cluster *usually* goes back to the same identity (`72063` and
`78104` both landed on 9161). A duplicate `centroid_vec` requires two
consecutive twins to land on **different** identities. So the 3 pairs measure
the **identity coin-flip rate on recurring clusters**, not the rarity of the
copy defect.

That coin flip is made worse by the defect itself: with `centroid` = today's
fragment, both identities sit at *exactly* the fragment's position, so
`match_snapshot` (`:836`, `cosine(cluster, t.centroid) >= MATCH_THRESHOLD 0.88`)
scores them **identically at 1.0** and the winner is decided by
`pairs.sort(reverse=True)` tuple order (`:841`) — i.e. by topic index. The
anchor guard (`:838`, `ANCHOR_THRESHOLD 0.93` against `anchor_centroid`) is the
only thing still holding, and it is itself weakened by retention: the anchor is
rebuilt from the *oldest surviving* member (`:1235-1237`), so it slides forward
as old clusters age out.

---

## 5. Blast radius — every consumer of `centroid_vec` reads a single-cluster snapshot

- **Identity matching** — `project_dynamic_topics.py:836`. A topic tracks
  whatever it last absorbed; `MATCH_THRESHOLD` is evaluated against today's
  fragment, not the story. Directly relevant to the measured argmax-dispersion
  finding (2026-07-30 `used_t` simulation: same-event fragments don't share an
  argmax).
- **Unified assignment** — `build_unified_topics.py:95-102` loads all active
  centroids; `:261-263` `sims.argmax(axis=1)`. Two identical centroids = an
  exact tie broken by column index, silently and always the same way.
- **Story lens siblings / constellation walk**, **`build_universe_field.py`**
  (PCA positions + kNN edges), **`detect_overmerge.py:134`**,
  **`compute_category_typing.py:125`**, **`assemble_constellation.py`**,
  **`build_umbrella_topics.py:87`** (umbrella = centroid-of-centroids, so the
  parent inherits the fragment), **`fit_global_whitening.py`**.
- **Label vs. vector memory horizon** — the label is the *mode over all history*
  (`:539-541`), the centroid is *this pass only*. An identity can therefore be
  named after a story it no longer sits on. That is exactly the 4082/3150 case,
  and it is a plausible upstream contributor to the label-court `failed` rate
  (all four Greek/Brazil topics here are `label_status='failed'`).

**Only two writers exist** for leaf topics: `project_dynamic_topics.py:1283`
(INSERT) and `:1312` (UPDATE). `build_unified_topics.py:226` only founds `u2-*`
identities; `build_umbrella_topics.py:211` only writes umbrellas.

**Ruled out:** shared `emergent_cluster_id` (member sets are disjoint — §3B);
copy-on-founding (founding sets `k=1` at `:854-862`, and these topics carry 8–20
snapshots); `emergent_topic_identity_resolver.py` (read-only on `centroid_vec`).

---

## 6. Recommendation

**Do not patch this as a bugfix.** Restoring the true running mean changes which
cluster attaches to which identity on every future night — that is a lifecycle /
identity change, and per project discipline it needs a **pre-registered gate**
before the write.

**The fix itself is small and mechanical:** stop deriving `k` from the
pending-write queue. Add an explicit counter (e.g. `n_clusters_seen`,
incremented in `__init__` and `attach`), use it in `running_mean` (`:548`) and
in `absorb` (`:568-574` — which is *also* degenerate today: after hydrate both
sides have 0 members, so the merge weighting collapses and the victim's centroid
is silently discarded). Leave `members = []` exactly as-is; it is correct for
its stated purpose.

**Pre-registration sketch (to be written before the build, not after):**

- **Arms:** (a) production as-is, (b) true running mean, over the same nightly
  clusters — a shadow/dry-run pass, no writes.
- **Primary:** same-identity re-match rate for recurring clusters (does the
  Rethymno/border-checks twin stop changing identity?), and duplicate
  `centroid_vec` count → expect 0.
- **Guards that must not regress:** court `entailed` share, over-merge /
  black-hole counts (a longer-memory centroid absorbs more broadly — this is
  the real risk, and `ANCHOR_THRESHOLD` is the brake to re-measure), active
  topic count, serving thread count.
- **Kill rule:** written before the run.

**Backfill is possible but is a separate gated write**: the correct centroid for
any topic is recoverable by replaying `dynamic_topic_members` over the surviving
`emergent_clusters` — precisely what `hydrate_topics` already does at
`:1236-1246`, before the reset. Not to be run until the forward fix passes.

**Cheap interim, independent of the gate:** make the exact-tie in
`build_unified_topics.py:261-263` and in `match_snapshot`'s `pairs.sort` explicit
rather than index-decided (log it, or refuse to assign on a 1.0 tie between two
identities). Today a duplicate-centroid pair silently routes every one of its
signals to whichever id sorts first.

---

## 7. Reproduction

Read-only, ~1 min, no writes:

```sql
-- 99.3% claim
WITH t AS (SELECT id, state, md5(centroid_vec::text) th FROM dynamic_topics
           WHERE centroid_vec IS NOT NULL AND NOT is_umbrella
             AND state IN ('active','candidate')),
lastm AS (SELECT DISTINCT ON (dynamic_topic_id) dynamic_topic_id tid,
                 emergent_cluster_id cid
          FROM dynamic_topic_members
          ORDER BY dynamic_topic_id, snapshot_at DESC, emergent_cluster_id DESC)
SELECT t.state, count(*) topics,
       count(*) FILTER (WHERE md5(ec.centroid_vec::text) = t.th) AS centroid_eq_last_cluster
FROM t LEFT JOIN lastm ON lastm.tid = t.id
       LEFT JOIN emergent_clusters ec ON ec.id = lastm.cid
GROUP BY 1;

-- the duplicate groups (15 total, 3 active-active)
SELECT md5(centroid_vec::text) h, count(*) n, array_agg(id ORDER BY id) ids,
       array_agg(DISTINCT state) states
FROM dynamic_topics WHERE centroid_vec IS NOT NULL
GROUP BY 1 HAVING count(*) > 1 ORDER BY n DESC;
```

Full duplicate inventory (all states): **15 groups / 30 topics** — 3
active⟷active, 5 active⟷candidate, 7 candidate⟷candidate.
