# Label-court blind-spot audit — court verdict × independent hand-judgment (2026-07-29)

**Question.** finder-v2 (`docs/research/recall-229/2026-07-29-sibling-finder-v2-measurement.md`)
found active topics whose labels contradict their own evidence (dt-3188
"Wildfire in Halkidiki" ≈ a Chania workshop explosion; dt-1226 "Crimea-Congo
Hemorrhagic Fever" = a Spanish femicide; dt-2944 "Russian Strikes on Ukrainian
Ports" ≈ Ukrainian drones hitting Russia); two harvested witness families
dissolved on verification because their labels lied. The label court
(`backend/scripts/label_court.py`, DeepSeek temp-0 →
`dynamic_topics.label_status ∈ {entailed, partial, failed}`) exists to catch
exactly this. **Does it?**

**Answer: yes — and the premise inverts.** On a 62-topic stratified sample the
court shows **zero blind spot at the PASS stamp** (entailed × contradicts =
0/30; every court-entailed label was hand-judged to describe its receipts). All
three named witnesses were already court-flagged. The court's real failure mode
is **over-strictness** (13/15 sampled `partial` verdicts read fine to a human;
1/17 `failed` was a clean topic). The gap the finder-v2 arc actually hit is
**enforcement and coverage**, not judgment: 702/1058 active topics (66%) are
court-FAILED and still serve, and the 14 biggest served rows (incl. 10
umbrellas — the front-page lane) carry **no verdict at all** at sampling time.

---

## Pre-registration (written before any sample was drawn)

- **Sample**: active, non-umbrella `dynamic_topics` with a label, stratified by
  `label_status`: entailed 30 / partial 15 / failed 15 (entailed oversampled —
  the blind-spot question lives in the court's PASS stamp). Deterministic draw
  `ORDER BY md5(id::text || 'blindspot-2026-07-29')`. Witness set dt-3188 /
  dt-1226 / dt-2944 force-included and tagged. Umbrellas excluded (their court
  question is family-membership, a different bar; the entailed stratum contains
  0 umbrellas anyway).
- **Evidence per topic**: label + up to 10 member headlines from the court's
  own receipt lane (`topic_members` role='evidence', freshest-first,
  HTML-decoded; emergent-sample fallback) — the judge sees the same lane the
  court reads.
- **Judge**: Claude (Fable), *blind* — topics shuffled by `md5(id||'blind')`,
  court verdicts and witness tags stripped from the judging view.
- **Rubric** (subject AND geography, majority basis — mirrors the court
  question so the matrix compares verdicts, not questions):
  - **describes** — label's event/subject and geography match the majority
    (>50%) of receipts; a generic label honestly covering a generic bucket
    counts.
  - **partially** — the labeled story is genuinely present but a large minority
    (~30–50%) of receipts are other stories, OR subject right with a
    materially-wrong specific (locality, named entity).
  - **contradicts** — the majority of receipts report a different event /
    subject / geography than the label asserts (the Halkidiki-vs-Chania class).
- **Material-blind-spot criterion (the kill line)**: court has a material blind
  spot if **≥10% of the entailed stratum is hand-judged `contradicts`**.
  Secondary health checks: entailed×describes ≥70%; failed mostly
  contradicts-or-partially.

## Harness

`backend/scripts/audit_label_court_blindspot.py` — strictly read-only (SELECT
only, no LLM calls, no writes). Samples → 
`2026-07-29-court-blindspot-samples.jsonl`; judgments joined with verdicts →
`2026-07-29-court-blindspot-judgments.jsonl` (both beside this file).

```bash
DATABASE_URL=... backend/.venv/bin/python backend/scripts/audit_label_court_blindspot.py \
    --out docs/research/label-court/2026-07-29-court-blindspot-samples.jsonl
```

Population at sampling (active, labeled): failed 702 · partial 197 · entailed
145 · unchecked 14. All checked topics stamped **2026-07-29** (the 30-min court
cadence held), so verdict-vs-receipt churn windows are hours, not days. 62
sampled (15 failed + 2 witnesses landed there; dt-2944 drew into partial
naturally). 0 topics had <2 receipts.

## Confusion matrix — court verdict × hand judgment

|              | describes | partially | contradicts | total |
|--------------|----------:|----------:|------------:|------:|
| **entailed** |    **30** |         0 |       **0** |    30 |
| **partial**  |        13 |         2 |           0 |    15 |
| **failed**   |         1 |         3 |          13 |    17 |

- **entailed × contradicts = 0/30 (0%, exact binomial CI95 0–11.6%).** The
  pre-registered ≥10% criterion is **not met** at the point estimate; the
  sample bounds a true blind-spot rate below ~12% at 95%. The PASS stamp is
  high-precision: 30/30 describes.
- **partial is over-broad**: 13/15 (87%) of sampled `partial` verdicts were
  hand-judged *describes* — e.g. dt-2832 "Iran-US Talks Continue" (9/10 clean),
  dt-1214 "Wildfires Rage in Spain and France" (10/10), dt-6957 "Lavrov-Rubio
  Meeting in Manila" (7/10). The court demands near-unanimity before granting
  `entailed`; one or two stray receipts demote a healthy label.
- **failed is mostly right**: 13/17 contradicts + 3/17 partially. One false
  conviction: **dt-106 "US Strikes on Iran" — 10/10 receipts match the label**
  and the court still says failed (worth a spot-check of its check-time
  receipts; at 2,000+ signals its receipt window may churn fast). The 3
  "partially" cases are specific-detail misses the court punished as failures:
  dt-467 (Marc poll labeled "MRB Poll"), dt-3188 (real Halkidiki wildfire,
  wrong village), dt-7751 (bakery attacks present but the majority facet is the
  consulate shooting).

## The witness set, re-examined

| topic | finder-v2 characterization | court verdict | hand judgment today |
|---|---|---|---|
| dt-1226 "Crimea-Congo Hemorrhagic Fever Death" | Spanish femicide | **failed** ✓ | contradicts (0/10 CCHF; Benahavís femicide + LatAm women-found-dead) |
| dt-3188 "Wildfire in Psakoudia, Halkidiki" | Chania workshop explosion | **failed** ✓ | partially (today: 6/10 a *real* Halkidiki wildfire — at Mola Kalyva, not Psakoudia; membership churned since the finder run) |
| dt-2944 "Russian Strikes on Ukrainian Ports" | Ukrainian drones hitting Russia | **partial** ✓ | describes (today's majority receipts *are* Russian strikes on Nikolaev/port infrastructure) |

The court had **already flagged all three** before this audit. dt-3188 and
dt-2944 also show how fast the receipt ground truth moves under a hot topic —
the same topic id reads differently hours apart, which is an identity-churn
fact, not a court error.

## What the finder-v2 arc actually needs (the real gap)

The instrument works; nothing downstream consumes it:

1. **Enforcement.** 702/1058 actives (66%) are court-FAILED **and still serve**.
   All 702 carry an unused `label_proposed` (`ATLAS_LABEL_COURT_APPLY=off`).
   The 07-20 relabel pass covered the then-pool; the pool churned past it.
2. **Coverage at the top.** Top-40 active by `agg_n_signals`: **0 entailed, 21
   partial, 5 failed, 14 never-checked** — the unchecked 14 include 10
   umbrellas, i.e. the served front-page lane. Umbrella rebuilds mint new ids
   nightly, faster than the court stamps them; the biggest served rows are
   systematically the least-judged.
3. **For witness-family harvesting** (the 07-28 arc's ask): `label_status`
   is usable **today** as a trust filter — require `entailed` anchors
   (high-precision PASS, 0/30 contradiction), treat `partial` as
   usable-with-a-look (87% actually fine), and treat `failed` as
   label-untrustworthy while remembering the *topic* may still be coherent
   (1/17 was). Two witness families dissolved because the harvest trusted
   labels the court had already convicted.

## Caveats

- n=30 entailed bounds the blind spot at ≤11.6% (CI95), not zero-zero; a larger
  pass tightens it.
- Single hand-judge (Claude), blind to verdicts but sharing the court's
  question form; a second annotator would give κ.
- Receipts drawn at audit time, not check time — same-day stamps keep the
  window to hours, but hot topics (dt-106, dt-3188) demonstrably churn within
  it.
- Umbrellas out of scope; the family-membership bar needs its own audit
  (and is where the unchecked mass sits).

*Read-only throughout: no engine changes, no relabeling, no writes to any
table.*
