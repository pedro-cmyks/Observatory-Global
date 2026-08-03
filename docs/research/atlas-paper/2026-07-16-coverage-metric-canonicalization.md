# Coverage / recall denominator reconciliation (housekeeping)

Date: 2026-07-16 · Author: Claude (Opus 4.8) · Status: **canonical reference**
· Scope: reconciles the many `%` coverage/recall numbers scattered across the
Atlas docs into ONE table + ONE canonical metric per claim-type, so papers stop
chaining incomparable numbers.

Trigger: the papers-reorganization framing doc
(`2026-07-16-papers-reorganization-justification-framing.md` §P8) flagged three
defects to fix before P8 ships — (a) reconcile the coverage denominators into
ONE defined metric, (b) kill the "54×" cross-country double-count, (c) delete
the all-zeros bootstrap artifact. This doc does (a)–(c).

The root problem: at least **12 distinct percentages** all get called
"coverage" or "recall" in prose, but they use **different numerators, different
denominators, different windows, and different scopes**. Chaining them (e.g.
"0.04% → 39.7% → ~38% useful → 26.72% scoped") reads as one arc but silently
switches the denominator 4 times. Every number below is real; the sin is
comparing them as if they measured the same thing.

---

## 1. Every distinct coverage/recall number found, with its EXACT definition

Grouped by which **claim-type** it actually measures (see §2 for the canonical
pick per group). "num/den" = numerator / denominator.

### Group A — FUNNEL COVERAGE (what fraction of the *signal corpus* lands in a topic)

| # | num / den | window · scope | state | source doc |
|---|---|---|---|---|
| **2.5%** | 13,354 distinct signals in any topic / **534,000 total signals** | all · global | BEFORE (superseded) | `atlas-paper/2026-06-30-paper-8-result-skeleton.md` §baseline |
| **5.6%** | 13,354 / **239,233 embedded signals** | all · global (single HDBSCAN pass) | BEFORE (superseded) | paper-8 skeleton §baseline |
| **0.04%** | distinct signals in an active thread / signals (active threads = 30) | 24h · global served | BEFORE (superseded by the 9d1b04e7 recall fix) | paper-8 §addendum; `state/2026-07-09-useful-coverage-gate.md` |
| **39.7%** | distinct signals in an active thread / signals (active threads 30→**597**) | 24h · global served | AFTER recall fix (`9d1b04e7`), raw (incl. junk) | paper-8 §addendum |
| **41.7%** | assigned signals / **~123k 24h signals** (unified-v2, incl. junk) | 24h · global served | live prod 2026-07-09, raw (incl. junk) — **same metric as 39.7%, re-measured** | `state/2026-07-09-useful-coverage-gate.md` §1 |
| **25.8%** | **non-junk** assigned signals / ~123k 24h signals | 24h · global served | live prod 2026-07-09, **useful** (after junk gate) | useful-coverage-gate.md §1 |
| **~38%** *(projected)* | useful coverage after applying the 74.6% reclaim ratio + embed-backlog drain | 24h · global served | **PROJECTION, not a measurement** | useful-coverage-gate.md §5, §7 |
| **17.4% / 38.1%** | junk-held signals / assigned (A/B arm-A 17.4%; live-prod 38.1%) | 24h · global served | the junk fraction being removed | useful-coverage-gate.md §1, §5 |

> Note the 39.7% vs 41.7% "discrepancy": these are the **same raw-coverage
> metric** (assigned/served ÷ 24h signals, junk included) measured at two moments
> under slightly different configs. The useful-coverage doc itself annotates its
> 41.7% as "*= the task's 39.7%*". They are NOT two findings — treat as one
> raw-coverage number with measurement noise, and prefer the **useful** 25.8%
> as the headline (see §2).

### Group B — SCOPED RECALL (the discovery/geometry result: global-pass vs partition-scoped)

| # | num / den | window · scope | state | source doc |
|---|---|---|---|---|
| **4.94%** | signals in a topic under a **global** pass / **131,210 country-attributable signals** (117 countries, cap 6000/country) | 168h · system aggregate | R0 read-only measurement | `recall-scoped/system-estimate.md` |
| **26.72%** | signals in a topic when **every country is clustered within its own partition** / same 131,210 den | 168h · system aggregate | R0 read-only measurement | `recall-scoped/system-estimate.md` |
| **2.59%** | 388 / **15,000 US embedded signals** in a topic (global pass) | 168h · US only | R0 single-country probe baseline | `recall-scoped/scoped-probe-US.md` |
| **38.11%** *(US)* / rounded **"38%"** in paper-8 | US scoped recall, best non-blob HDBSCAN config (leaf, mcs5, ms2) | 168h · US only | R0 single-country probe best | scoped-probe-US.md; paper-8 §Intervention-2 |
| **2.43%** *(CN)* | 146 / **6,000 CN embedded signals** (global pass) | 168h · CN only | R0 single-country probe baseline | `recall-scoped/scoped-probe-CN.md` |
| **32.92%** *(CN)* / rounded **"33%"** | CN scoped recall, best non-blob config | 168h · CN only | R0 single-country probe best | scoped-probe-CN.md; paper-8 §Intervention-2 |
| per-country **37% / 34% / 32% / 25%…** | US/DE-GR/IR/MX scoped recall rows | 168h · per country | R0 detail rows of the 4.94→26.72 aggregate | system-estimate.md table |

> The single-country probe bests (US **38.11%**, CN **32.92%**) use a
> **different denominator** (per-country embedded in a recent window) and a
> **different config search** than the 117-country system estimate (which scores
> US at **37.4%**, CN unblobbed). They are consistent in magnitude but are NOT
> the same measurement — do not quote "38%" and "26.72%" in the same sentence as
> if one aggregates the other.

### Group C — SERVED-THREAD / NARRATIVE COUNTS (counts, not percentages — but chained as if comparable)

| # | meaning | source doc |
|---|---|---|
| **68** | active served topics under the old global regime (BEFORE) | paper-8 §baseline; system-estimate.md |
| **392 → 348** | active after R1 scoped serving + retirement sweep | paper-8 §Intervention-3 |
| **597 → 549** | active after the recall fix, then after junk-gate demotion (−48 junk) | useful-coverage-gate.md §5 |
| **3,662** | scoped **clusters** formed across 117 countries (R0) | system-estimate.md |
| **731** | scoped clusters written by the R1 production run (126 countries) | paper-8 §Intervention-3 |
| **26 umbrellas / 55 children** | R2 complete-linkage collapse of cross-country duplicates | paper-8 §Intervention-4 |
| **"~54× more narratives"** | 3,662 scoped clusters ÷ ~68 global topics | paper-8 §Intervention-2 table — **DEFECTIVE, see §3** |

### Out-of-scope legacy numbers (name-collide with "coverage/recall" but measure something else — do NOT fold into the arc)

| # | what it actually is | source doc |
|---|---|---|
| **0.2%** | `gender-violence-rights` **lex_pct** — fraction of that GDELT-theme topic's volume matching its lexicon (a per-topic lexical-match rate, not system coverage) | `2026-05-24-thread-quality-audit.md` |
| **20.2%** | theme-hint-dependent assignment **precision** (Paper 1 ablation), not coverage | `embedding-ablation/2026-07-01-gdelt-hint-ablation.md` |
| **41.6% / 48.3% / 40.9%** | Paper 1 classification **precision** numbers, not coverage | gate-recall / paper-1 skeleton |
| **9.4% / 20.7%** | **relative lift** in written-cluster count from whitening (control→whitened), not an absolute coverage % | `recall-229/2026-07-16-whitening-recall-harness.md` |
| **59.02%** (Wilson [46.5, 70.5]) | bootstrap-combined **precision** on N=61 labels, not coverage | `phase-1-validation/reports/bootstrap-combined/` |

---

## 2. Recommendation — ONE canonical metric per claim-type

Papers and CLAUDE.md should cite exactly one number per claim-type, always
stated as **num / den / window / scope**, and never chain across groups.

### Canonical FUNNEL COVERAGE → **"useful served coverage"**
> **non-junk assigned signals ÷ 24h ingested signals** (currently **25.8%**,
> live prod 2026-07-09, unified-v2 + junk gate).

- This is the honest served number: it excludes junk grab-bags (which the junk
  gate proved are 25% true-junk / 75% reclaimable) and uses the stable 24h
  ingested denominator.
- **Report raw coverage (39.7% / 41.7%) only as a labelled secondary** ("raw,
  incl. junk"), never as the headline.
- **The "~38% projected" is a projection** — label it as such every time; it is
  not a measurement until the next gated 60k+new-topics cron cycle produces it.
- Always carry the caveat: **absolute % is capped by embed backlog** (a
  ~210k-signal backlog means un-embedded 24h signals can't be assigned at all).

### Canonical SCOPED RECALL → **the system aggregate pair**
> **global 4.94% → scoped 26.72%** over **131,210 country-attributable signals /
> 117 countries** (R0 read-only, 168h).

- This is the only apples-to-apples pair: **same denominator**, global vs
  partition-scoped. It is the number that justifies the per-country loop and is
  the defensible P8 discovery result.
- **Demote the single-country probe bests (US 38.11%, CN 32.92%)** to per-country
  detail / illustration. Do NOT headline "38%" — it is a different denominator
  and window than the 26.72% system figure, and reads as if scoping gets you to
  38% system-wide (it does not; system-wide is 26.72%).
- State it as **recall lift ~5.4×**, not "54× more narratives" (that is the
  broken count metric — §3).

### Canonical SERVED-THREAD COUNT → **active served topic count**
> **active served topics** (current: **549** after the junk gate; historically
> 68 → 392/348 → 597 → 549).

- This is a count of *served* topics, deduplicated by R2 umbrellas. Use it for
  "how many live narratives does Atlas serve".
- **Never chain a topic count to a recall %** as a multiplier (that is exactly
  the 54× error). If a growth factor is wanted, quote the recall lift (5.4×) or
  the served-topic delta (68→549), each with its own denominator stated.

---

## 3. The "54× more narratives" double-count — DROP or caveat

**Defect.** `paper-8 §Intervention-2` reports "**~54× more narratives**" =
**3,662 scoped clusters ÷ ~68 global topics**. This double-counts cross-country
duplicates. A single global story (France heatwave, World Cup, a G20 summit)
forms **one scoped cluster per country it appears in** — correct for
country-scoped *serving*, but it means 3,662 is a count of
(story × country) pairs, not distinct narratives.

**Proof it is a double-count from Atlas's own pipeline:** R2
(`§Intervention-4`) exists specifically to collapse this — complete-linkage over
the scoped centroids folded a sample down to **26 umbrellas over 55 children**
(Venezuela Earthquake ×2, France Heatwave ×2, Egypt World Cup ×4). The umbrella
layer is the built-in admission that the raw scoped-cluster count over-counts
cross-country duplicates. So "54×" multiplies exactly the duplication R2 removes.

**Recommendation:**
- **Drop "54× more narratives" entirely** from papers and CLAUDE.md. It is not a
  defensible discovery magnitude.
- If a magnitude is needed, use the **recall lift (~5.4×)** — it is denominator-
  honest (same 131,210 signals both arms).
- If a *narrative-count* growth is genuinely wanted, quote the **served,
  umbrella-deduplicated** count (68 → 549 active served topics), or the R2
  umbrella/child structure — never the raw pre-R2 scoped-cluster count.
- Wherever "54×" survives in a non-headline context, caveat it inline:
  "*(raw pre-R2 scoped-cluster count; inflated by cross-country duplication that
  R2 umbrellas collapse — not distinct narratives)*".

---

## 4. Broken artifact confirmed: `bootstrap-batch-02.json` is superseded

**Confirmed broken / all-zeros.**
`docs/research/atlas-paper/phase-1-validation/reports/bootstrap-batch-02.json`
(and its `.md` / `-forest.svg` siblings) contain an **empty result**:

```
overall: { labeled: 0, correct: 0, incorrect: 0, precision: 0.0,
           wilson_ci_low: 0.0, wilson_ci_high: 0.0, gate: "fail" }
by_topic: {}
```

Its single input is only the batch-02 reviewed labels file, which standalone
yielded **0 parseable labels** → every statistic is 0.0 and the gate reads
`fail` for a degenerate (not a real) reason. Any doc citing batch-02's
precision/CI is citing zeros.

**Superseded by** `bootstrap-combined/bootstrap-combined-01-02.json`, which
pools batch-01 + batch-02 reviewed labels and is the real N=61 result:

```
labeled: 61, correct: 36, incorrect: 25, unclear: 3,
precision: 0.5902, wilson_ci: [0.465, 0.7046],
bootstrap_ci: [0.4754, 0.7049], gate: "fail"
```

**Recommendation:** delete (or mark `SUPERSEDED — all-zeros, do not cite`) the
three `bootstrap-batch-02.*` files, and cite only **combined-01-02** (precision
**59.02%**, Wilson **[46.5%, 70.5%]**, N=61) for the Paper-1 v2 stratified
precision claim. This matches the framing doc's §P8 instruction ("delete the
all-zeros bootstrap-batch-02.json").

---

## 5. Quick citation card (paste into papers / CLAUDE.md)

| claim-type | canonical number | full form to always write |
|---|---|---|
| funnel coverage | **25.8% useful** | non-junk assigned ÷ 24h ingested signals, live prod 2026-07-09, embed-backlog-capped |
| scoped recall | **4.94% → 26.72%** | global vs partition-scoped, over 131,210 signals / 117 countries, R0 168h; lift **~5.4×** |
| served narratives | **549 active** | umbrella-deduplicated served topics (68→392/348→597→549) |
| v2 label precision | **59.02%** [46.5, 70.5] | bootstrap-combined-01-02, N=61 (NOT batch-02) |
| DROP | ~~54× more narratives~~ | cross-country double-count; R2 collapses it — use 5.4× or 68→549 |
