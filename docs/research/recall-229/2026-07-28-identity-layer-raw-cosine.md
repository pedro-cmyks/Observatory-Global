# The clustering failure is not "no topic forms" — the story is SHREDDED and SCATTERED

**Date:** 2026-07-28 · measure-first diagnosis, read-only, no code changed
**Trigger:** the primary metric came back 14% (2/14 gold queries); the dominant failure
kind was labelled `clustering` — "no topic exists for a story that IS in the corpus".
**That label was wrong**, and the real mechanism is worse.

## Mechanism (one sentence)

The identity layer compares topic centroids in **raw e5 cosine**, where the same-story and
different-story distributions overlap almost completely — so all three identity gates
(`MATCH_THRESHOLD 0.88`, `ANCHOR_THRESHOLD 0.93`, `MERGE_THRESHOLD 0.90`) sit **inside the
overlap band**, which simultaneously **shatters one event into 8–33 clusters that never
merge** and **lets unrelated stories be absorbed by stale identities**.

## The evidence that settles it

Frozen anchor `dynamic-topic-784` "Cabo Verde Captain Rape Allegations" (NZ), vs each
cluster it absorbed:

| date | cc | n | **raw cos** | **whitened** | cluster label |
|---|---|---|---|---|---|
| 07-02 | NZ | 11 | 0.9971 | **0.9751** | Cape Verde Captain Sexual Assault Allegations *(true match)* |
| 07-17 | BO | 14 | 0.9318 | **0.3873** | Bolivian Recruitment for Russia-Ukraine War |
| 07-22 | CO | 9 | 0.9391 | **0.4501** | Assassination Plot Allegations |
| 07-24 | CO | 10 | 0.9406 | **0.4524** | (null) |
| 07-25 | CO | 13 | 0.9370 | **0.4374** | (null) |

In raw e5 an unrelated Colombian political cluster sits **0.938** from a New Zealand
sexual-assault anchor — *above* the 0.93 gate. In whitened space the same pairs are
**0.39–0.45** against a true match at **0.975**. **The geometry that rejects these already
ships** (`app/data/e5_whitening.npz`); the identity layer simply does not use it. Whitening
is applied only to the HDBSCAN *input*, and even there it is default-off
(`ATLAS_CLUSTER_WHITEN_K=0`).

## GQ-05 funnel (Colombia / `%espriella%`), measured

| Stage | Count |
|---|---|
| corpus, 7d | **658** signals / 126 outlets / **604 distinct headlines** (not syndication) |
| embedded | **654 / 658 = 99.4%** — embed coverage is NOT the problem |
| HDBSCAN | **382/598 (63.9%) → NOISE**; 216 spread over **33 fragments** (cohesion 0.95–0.99) |
| precision gate | cuts a further 146/598 (24.4%) — zeroes cohesion-0.99 clusters |
| `min_kept=8` | drops 28 of the 33 story-carrying clusters |
| **persisted in a cluster** | **38 / 598 = 6.4%**, largest 13 members |

**Volume does not help** — this is the biggest CO story of the week (10% of the national
corpus) and it yields the same 8–13-member artifacts as anything else.
**Language bias is DISPROVED** — CO's gate keep-rate (57.3%) is the *highest* of the four
countries tested (IE 55.3, PH 50.2, ZA 46.9); noise rates are ~69–76% everywhere.

## GQ-12: the same mechanism, legible in the labels

`%caspian%` = 370 signals, 0 topics named Caspian. One snapshot produced **nine clusters of
one event** (~183 signals): *Iran Accuses Ukraine of Caspian Attack* (70) · *Iran Condemns
Ukraine Ship Attack* (25) · *Iran Threatens Ukraine Over Ship Attack* (18) · … Pairwise raw
centroid cosine among them: **0.865–0.993**, straddling all three gates.

**Two structural reasons they never reconverge:**
1. `process_snapshot` matching is **greedy 1-to-1** (`used_c`/`used_t`) — a topic absorbs at
   most **one** cluster per snapshot, so 8 fragments of one event *cannot* land on one
   identity in a night, by construction.
2. `merge_duplicates` also requires **label-string** similarity ≥0.80 (SequenceMatcher).
   On those nine labels only **2 of 15 pairs** clear it.

## CONFOUNDER on the 14%: a five-day label blackout

`emergent_clusters.label` was **100% NULL on 2026-07-23 → 07-27** (3,475/3,475 on 07-27) —
DeepSeek `402 Payment Required`, the same exhausted balance that blacked out the front
page. Because `labels_compatible(None, None)` is **False**, **fragment merging was fully
disabled for the entire eval week.** The gold eval ran on the worst possible night, so
**14% is a floor, not a steady-state reading.**

Separately: **457 of 1,165 active topics (39%) carry `label_status='failed'`** — the label
does not describe the receipts.

## The premise "ZERO topic in any state" was FALSE — and that is worse

- **`dynamic-topic-52` "Cepeda Concedes to De la Espriella"** — 28 snapshots, **439**
  aggregate signals, cohesion 0.956 — existed since 06-03 and was **active on eval day**.
  The harness still served *"Nicaragua Ends Elections"* for GQ-05.
- It is a black hole: cluster lineage `Costa Rica News Mix` → `Mexican Ex-Officials Legal
  Cases` → `Japanese Culture in Dominican Republic` → CO Espriella, under a June label with
  `label_status='failed'`. It was correctly demoted on 07-28 (one of 187).
- **`dynamic-topic-8057` "Perry Warjiyo Resigns"** (GQ-08's exact story) also exists —
  `candidate`, 8 signals, blocked by BOTH `persist_min=2` and `volume_min=12`.

## Attribution: this explains 4 of the 5 "clustering" failures

GQ-05, GQ-08, GQ-10, GQ-12 — all shredded-and-scattered, all ≥97% embed coverage.
**GQ-11 (Azad Kashmir) is mislabelled**: only **17 signals exist in 7 days** — that is the
ingestion gap (#235), not an engine miss.

## Minimal fix, ordered by leverage (NOT implemented)

1. **Run the identity layer in whitened space.** Compute MATCH/ANCHOR/MERGE on
   `apply_whitening(centroid)` and re-fit the three thresholds on the whitened
   distribution. Directly validated above: 0.975 true vs 0.39–0.45 false, where raw offers
   0.997 vs 0.938.
2. **Drop `used_t` in `process_snapshot`** so one topic can absorb many clusters per
   snapshot (keep one-topic-per-cluster). Safe **only after (1)** — on raw cosine it makes
   black holes worse.
3. **Stop gating merges on label-string similarity** (0-recall when labels are NULL, 2/15
   when they exist). Use the entity/receipt-overlap signal `overmerge.py` already has, plus
   the existing DeepSeek "one story or two?" confirmer for the borderline band.
4. **Make `PROVIDER_EXHAUSTED` fatal to the snapshot write** — a labelless snapshot
   silently disables merging.

**Deliberately NOT proposed:** lowering `min_kept` or loosening the precision gate. It
accounts for only 5.4% of GQ-05's loss and would multiply fragments rather than unify them.

## Pre-registered success metrics (write these down BEFORE running anything)

- **Primary — story coverage:** story signals landing in ONE persisted topic / story
  signals in corpus. Baseline **GQ-05 = 38/598 = 6.4%** (largest topic 13). **Target ≥50%.**
- **Fragments per event:** baseline 33 (GQ-05), 9 (GQ-12). **Target ≤3.**
- **False-absorption guard (must not regress):** topics whose absorbed clusters span ≥3
  unrelated primary countries under a court-failed label. Baseline: topic 784 (NZ→BO→CO),
  topic 52 (CR→MX→DO→CO). **Target 0 new.**
- **Purity control:** `detect_overmerge` demote count next nightly. Baseline 187. Fix (2)
  without (1) will spike this — that is the falsifier.
- **Confounder removed:** the measurement snapshot must have a 0% NULL-label rate, else the
  run is VOID.
