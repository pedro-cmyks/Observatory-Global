# GATE GB — blind hand-check of the umbrella label court (first run)

**Date:** 2026-07-29
**Protocol:** `docs/superpowers/plans/2026-07-29-identity-three-levers.md`, gate GB
**Bar:** ≥8/10 agreement between an independent blind human-equivalent judgment and the
court's verdict before the cron flag flips.
**DB:** read-only (`SET default_transaction_read_only = on`). No writes, no commits.

## Method

1. Deterministic draw, 10 of the 36 active umbrellas:
   `ORDER BY md5(id::text || 'gb-blind') LIMIT 10`. `label_status` was deliberately
   **not** selected in this query.
2. For each umbrella: children (`parent_id`) + up to 3 receipt headlines per child from
   `topic_members` (`role='evidence'`, `engine_version='v1-compat'`, not quarantined),
   joined to `signals_v2.headline`.
3. Judgments written below **before** any court verdict was read.
4. Only then `label_status` was fetched and compared.

Judgment scale (the court's own bar):
- **entailed** — the family coherently IS what the label says.
- **partial** — the label covers a real majority; a material minority is other stories.
- **failed** — the family is substantially other stories than the label claims.

---

## Part 1 — the 10 blind judgments (written before seeing any verdict)

### 1. `8095` — "Syros stabbing death: 41-year-old apologizes for killing rescuer"
Children: 810 "Ryanair Window Incident", 2253 "Ryanair Window Incident".
Receipts: 5 of 6 are the Ryanair window/decompression incident (the 61-year-old passenger
partially sucked out — Greek + English coverage of the same event); 1 is a toddler pulled
unconscious from a pool in Chania.

**→ FAILED.** Not one receipt concerns a Syros stabbing, a rescuer, or an apology. The
family is an aviation incident; the label describes a homicide case. Total subject
mismatch, not borderline.

### 2. `8168` — "Wildfires Across Europe and Greece; Quake Hits Japan"
Children: 342 (France/Spain fires, heatwave), 458 (Greece red-alert fire risk), 578
(Adami/Argolida fire), 1638 (Sicily/Agrigento fires, firefighter dies), 2990 (Turkey —
Mersin/Muğla/Fethiye forest fires), 3181 (label says Greece; receipts are US NWS
Extreme Heat Warning/Watch and Dense Fog Advisory for Galena IL and Dubuque IA), 4329
(label says Norway; receipts are Gironde/Bordeaux, 220k evacuated).

**→ PARTIAL.** The "wildfires across Europe and Greece" clause is honest and covers 6 of
7 children (FR, ES, GR, IT, TR). But the "Quake Hits Japan" clause has **zero** receipts
anywhere in the family — a fabricated conjunct — and one child is US heat/fog advisories,
not fire. Majority coverage holds, so not failed; the unsupported half-label and the US
weather child are the material minority.

### 3. `8084` — "OPEKEPE Sentencing"
Children: 393 "OPEKEPE Sentencing" — receipts are a Crete criminal-organisation bust:
8 arrests for livestock theft, extortion and fraud, >€270,000 illicit profit, one receipt
naming *παράνομες επιδοτήσεις* (illegal subsidies). 3189 "OPEKEPE Illegal Subsidies
Verdict" — receipts are three renderings of two Turkish truck drivers **acquitted** in
Thessaloniki of illegally transporting migrants.

**→ FAILED (borderline).** Half the family (3/6 receipts) is a migrant-smuggling acquittal
with no connection to OPEKEPE. The other half is subsidy-fraud-adjacent but is an arrest
operation, not a sentencing. No receipt depicts an OPEKEPE sentencing. Borderline because
child 393 does genuinely touch the illegal-subsidy domain the label names.

### 4. `8093` — "Earthquake Reports Indonesia"
Children: 604 (BMKG quake reports — Maluku, North Sumatra, North Maluku), 3084 (M5.8
Ternate, M5.6 Gayo Lues Aceh, M5.4 Enggano).

**→ ENTAILED.** All 6 receipts are Indonesian earthquake reports. Clean.

### 5. `8180` — "Financial Market Updates and Stock Movements"
Children: 1203 (HSBC Portföy fund repo filings, TR), 1767 (Pomerantz LLP securities class
actions), 4013 (analyst Buy/Hold rating reiterations), 4836 (share price moving-average
crosses), 6439 (quarterly earnings and dividends), 6734 (Indonesian 700 MHz / 2.6 GHz
spectrum auction results).

**→ ENTAILED (borderline).** A generic category label over a genuinely generic financial
bucket: 5 of 6 children are squarely market/investor news, and the label honestly
describes them. The one miss is the Indonesian spectrum auction (telecom-regulatory, no
market angle). Borderline entailed/partial on whether one off-topic child of six is
"material".

### 6. `8133` — "CSD Berlin Vehicle Attack"
Children: 7356 (German — car into crowd at Berlin CSD, one woman dead, driver at large),
7714 (Russian — car into crowd in Berlin, 1 dead, 14 injured).

**→ ENTAILED.** All 6 receipts are the same Berlin CSD vehicle attack, cross-lingual.

### 7. `8130` — "Daniel Siad Found Dead"
Children: 6021, 6023, 6739 (all same label). Receipts in FR/DE/ES/IT: Daniel Siad, alleged
Epstein recruiter, found dead near Paris; consequences for the French Epstein inquiry.

**→ ENTAILED.** All 9 receipts are the same death, across four languages.

### 8. `8108` — "Ahbap Charity Fraud Scandal"
Children: 2973, 2975. Receipts: Ahbap association investigation, 4th wave of operations,
13 suspects detained; celebrities summoned.

**→ ENTAILED.** All 6 receipts are the Ahbap fraud investigation.

### 9. `8165` — "Wildfires Rage in Spain and France, Over 200,000 Evacuated"
13 children, several carrying stale/wrong labels ("Fontainebleau Forest Fire",
"Waldbrandrauch in Toronto und New York", "Incêndio Florestal na Espanha"). Receipts
across EL/PT/FR/ES/SK/UK/DE/AR/IT/MK/RU: the Gironde–Bordeaux and Spain wildfire
emergency, evacuation counts of 220k / 250k / 300k / 325k / 370k.

**→ ENTAILED.** Every receipt is the same France–Spain wildfire evacuation event; the
umbrella label matches the evidence exactly, including the >200,000 figure. The child
labels are wrong but the family is one story — this is the cross-lingual consolidation
working as intended.

### 10. `8175` — "Oil Drops as US-Iran Tensions Ease"
Children: 576 (oil falls 5–6% after US/Iranian attacks stop), 2799 (US military announces
end of latest raids), 5054 (Iran warns US against striking nuclear sites), 5881 + 5882
(Pentagon war-cost estimate $37.5bn), 6993 (Trump vows to punish Iran over Houthi attacks;
**oil surges past $100**), 7727 + 7733 (Iran claims $18bn oil sales during the war), 7730
(Pentagon revises Iran casualty figures).

**→ FAILED (borderline).** Only 1 of 9 children (576) is the labelled event — oil dropping
as tensions ease. One child asserts the exact opposite (oil surging over $100 as Trump
threatens Iran). Five children have no oil-price angle at all (war cost, casualty-data
revision, nuclear-site warnings). The family is a coherent macro-story — the US–Iran war
and its oil dimension — but the label freezes a single transient market moment over it and
misdescribes the direction. Borderline because the label's subject matter (US–Iran, oil)
is present throughout.

**Blind tally:** entailed 6 (8093, 8180, 8133, 8130, 8108, 8165) · partial 1 (8168) ·
failed 3 (8095, 8084, 8175).

---

## Part 2 — the court comparison

Court output read only after the above was written: `label_court_model =
label-court-v0/deepseek-chat`, all 36 stamped `label_checked_at =
2026-07-29 15:16:43.538555+00` (one batch).

| # | id | label (truncated) | blind | court | agree? |
|---|----|-------------------|-------|-------|--------|
| 1 | 8095 | Syros stabbing death… | **failed** | failed | ✅ exact |
| 2 | 8168 | Wildfires Across Europe…; Quake Hits Japan | **partial** | failed | ❌ partial↔failed |
| 3 | 8084 | OPEKEPE Sentencing | **failed** (borderline) | failed | ✅ exact |
| 4 | 8093 | Earthquake Reports Indonesia | **entailed** | failed | ❌ two steps |
| 5 | 8180 | Financial Market Updates… | **entailed** (borderline) | failed | ❌ two steps |
| 6 | 8133 | CSD Berlin Vehicle Attack | **entailed** | partial | ❌ adjacent, reason not borderline |
| 7 | 8130 | Daniel Siad Found Dead | **entailed** | partial | ❌ adjacent, reason not borderline |
| 8 | 8108 | Ahbap Charity Fraud Scandal | **entailed** | failed | ❌ two steps |
| 9 | 8165 | Wildfires Rage in Spain and France… | **entailed** | failed | ❌ two steps |
| 10 | 8175 | Oil Drops as US-Iran Tensions Ease | **failed** (borderline) | failed | ✅ exact |

Scoring is strict per the protocol: agreement = exact match, or `entailed↔partial`
adjacency **only** where the written reason says borderline. `failed↔partial` adjacency is
disagreement by explicit rule. Rows 6 and 7 are adjacent but my reasons said "Clean" /
"All 9 receipts are the same death" — not borderline — so they score as disagreements.

### **GB SCORE: 3 / 10 — FAIL** (bar: ≥8/10)

Court verdict distribution over all 36 active umbrellas: **29 failed · 5 partial ·
2 entailed** (81% failed). My blind read of a random 10 was 60% entailed. The two
distributions are irreconcilable, which pointed at a defect rather than a calibration gap.

---

## Part 3 — disagreement analysis: the court is mis-fed, not miscalibrated

### The receipts the court judged are not the receipts the product serves

The failures ledger (`2026-07-29-label-court-failures.jsonl`, 58 lines, all
`lane: umbrella`, all `verdict: failed`) shows the court's reasoning is *internally sound*
— it is reasoning correctly about evidence that is wrong.

For `8093` "Earthquake Reports Indonesia" the court wrote:

> "The second child story's label and headlines refer to earthquakes in China, Peru, and a
> football match, not Indonesia."

Its six receipts were three Indonesian BMKG quake reports plus `Çinghay'da 5.7 ve 5.8
Büyüklüğünde Deprem` (Qinghai, China), `Sismo de magnitud 4.6 remeció Pucallpa` (Peru) and
`Mitchell Baker Antar Timnas Tekuk Kamboja 5-1` (a football match). Given that, "failed" is
the right call.

But those three headlines **do not exist in the served evidence pool**. Child 3084 carries:

| engine_version | role | rows | content |
|---|---|---|---|
| `v1-compat` | evidence | 8 | all Indonesian quakes (**this is what is served**) |
| `disaster-v1` | movement | 8 | — |
| `unified-v2` | evidence | 3 | Qinghai · Pucallpa · Cambodia football |

The court sampled exactly the three `unified-v2` rows. Same mechanism on `8165`: the
court cited "hepatitis deaths" as proof the wildfire family is incoherent — that headline
(`Epatite, nel mondo ci convivono circa 287 milioni di persone…`) is a `unified-v2` row on
child 5119, absent from the v1-compat pool.

### Root cause (code)

`backend/scripts/label_court.py:62-71`, `_RECEIPTS_SQL`:

```sql
SELECT s.headline, s.country_code
FROM topic_members tm
JOIN signals_v2 s ON s.id = tm.signal_id
WHERE tm.topic_id = $1 AND tm.role = 'evidence'
  AND s.headline IS NOT NULL AND length(s.headline) >= 12
GROUP BY s.headline, s.country_code
ORDER BY max(s.timestamp) DESC
LIMIT $2
```

Two filters are missing:

1. **No `engine_version` filter.** `topic_members` holds both `v1-compat` (served) and
   `unified-v2` (the F3 experimental construction, never cut over — `topic_members_engine_version()`
   still defaults to `v1-compat` and `ATLAS_TOPIC_MEMBERS_ENGINE_VERSION` is unset). The
   unified-v2 lane assigns at the measured cos≥0.88 cliff and is *known* to be noisier; it
   is exactly the lane that contributes the Peru quake and the football match.
2. **No `quarantined` filter.** Migration 087 / `audit_topic_blackholes.py` quarantined
   1,192 members precisely because they are off-centroid; nothing excludes them here.

`ORDER BY max(s.timestamp) DESC LIMIT 3` (per child, `_UMBRELLA_RECEIPTS_PER_CHILD = 3`)
makes it worse: unified-v2 rows are rebuilt nightly and carry fresh timestamps, so where a
child has ≥3 of them they **crowd the served evidence out of the window entirely**.

### Blast radius, measured

Replicating the court's exact per-child window (top-10 children by `agg_n_signals`, 3
receipts each, grouped by headline, ordered by `max(timestamp)`):

- **36 of 36** active umbrellas had at least one non-served receipt inside the trial window.
- Dose-response by verdict — contamination tracks harshness, monotonically:

| court verdict | umbrellas | mean % of trial receipts NOT served | min | max |
|---|---|---|---|---|
| failed | 29 | **85.9%** | 50% | 100% |
| entailed | 2 | 75.0% | 50% | 100% |
| partial | 5 | **50.0%** | 33% | 83% |

The umbrellas the court failed were judged on receipts that were ~86% invisible to users.
The ones it treated most leniently were the least contaminated. The verdict is tracking
the contamination, not the label.

### Independent re-verification of my own reads

Because a 3-per-child cap could equally have under-sampled *my* view, I re-sampled the
umbrellas' own aggregated pools (`role='evidence'`, `v1-compat`, not quarantined), 12–14
receipts drawn at random:

- `8093` — 12/12 Indonesian BMKG quake reports. **entailed confirmed**; court wrong.
- `8130` — 14/14 Daniel Siad death coverage (FR/ES/IT). **entailed confirmed**; court wrong.
- `8133` — 14/14 Berlin CSD vehicle attack (DE/RU). **entailed confirmed**; court wrong.
- `8165` — 14/14 France–Spain wildfire evacuation, 140k–325k figures. **entailed
  confirmed**; court wrong.
- `8108` — 7/12 Ahbap, **5/12 the Gülistan Doku investigation** (a genuinely separate case,
  linked in Turkish coverage only because the same minister announced both and Mehmet Aca
  appears in each). Honest verdict here is **partial**, not entailed — my blind read was
  generous because the 3-per-child cap hid the minority. The court's `failed` is still one
  step too harsh, and for the wrong reason.

So one of my six entailed calls (`8108`) softens to partial on fuller evidence. The other
five stand. The disagreement is not a sampling artifact on my side.

### What this does and does not indict

- **Not indicted:** the umbrella *question* (Lever B1's family framing) and the judge. On
  the evidence handed to it, DeepSeek's reasoning was correct and its written reasons were
  specific and checkable — the ledger is doing its job.
- **Indicted:** the receipt plumbing. A court that judges served labels against
  un-served, experimental-lane evidence cannot measure label honesty at all.
- **Consequence:** the 81% failure rate is not a finding about umbrella quality. It is an
  artifact. Any downstream use — the Lever A `rank_threads` court damp, relabel triggers —
  would have been driven by noise, and would have demoted coherent front-page families
  (the France–Spain wildfire umbrella, the Berlin CSD attack, the Epstein-recruiter death).

---

## Part 4 — verdict and required fix

**GATE GB: FAIL — 3/10 agreement (bar ≥8/10).** `ATLAS_COURT_UMBRELLAS` must stay **off**;
do not flip the cron flag.

Required before GB can be re-run:

1. Add `AND tm.engine_version = $N` (bound to `topic_members_engine_version()`, i.e.
   `v1-compat` today) and `AND COALESCE(tm.quarantined, false) = false` to `_RECEIPTS_SQL`.
   The court must read what the product serves, and must follow the F4 cutover var rather
   than hardcoding, so the two never drift apart again.
2. Consider ordering the per-child window by `assigned_at`/confidence rather than raw
   `max(s.timestamp)`, so a freshness accident cannot again select an entire trial window.
3. Re-run `--only-umbrellas --write` and repeat GB with a fresh deterministic draw (a new
   salt — this sample is now burned, since the 10 ids and their evidence are documented
   here).
4. Treat the current 36 verdicts as void: `label_status` on umbrella rows is not evidence
   of anything until the re-run.

**Generalisable lesson (this is the fifth time this pattern has paid):** the measurement
disagreed with the instrument, so the instrument got audited before the data was believed.
The court's own written reasons were what made the defect findable in minutes — a verdict
without a checkable reason would have shipped an 81% failure rate as a finding. Same class
as the two false audit recommendations of 2026-07-27: *a number produced by a pipeline is a
claim about the pipeline first, and about the world second.*

**Artifact:** `docs/research/label-court/2026-07-29-gb-blind-check.md` (this file).
No code, DB or config was modified; the session ran read-only.
