# Data Funnel, Serving Maturity, and "Why Atlas?" — Analysis

**Date:** 2026-06-10
**Status:** analysis + proposals (nothing implemented yet)
**Origin:** Pedro's three questions while reading the spec: (1) should we serve
T-1h so served data is always processed? (2) we collect ~190K signals/24h but
serve ~2K — how do we attack that for diversity? (3) why would anyone use
Atlas instead of Google?
**Related:** spec capability H (evidence-window contract), #213, #164 (NLP
backfill ADR), #161 (query-time enrichment), Paper 1 (precision), Paper 6
(temporal model).

## 0. Measured reality first (2026-06-10, live 24h window)

| Stage | Count | % of raw | Drop cause |
|---|---|---|---|
| Raw ingested (`signals_v2`) | 194,674 | 100% | — |
| Distinct headlines | 153,538 | 79% | syndication duplication (legit) |
| Atlas-topic assigned | 14,343 | 7.4% | lexicon/theme classification coverage |
| NLP processed | 6,785 | 3.5% | NLP throughput (~200/h on Fly) |
| Emergent snapshot input | 15,000 (cap) | 7.7% | **hard cap** in snapshot script |
| Latest snapshot cluster members | 442 | 0.23% | HDBSCAN density + precision gate |

Two different kinds of drop are mixed and must be separated:

- **Deliberate precision filtering** (gates, noise rates, roundup rules) —
  this is the product working as designed; Paper 1 measured why (41.6% raw
  precision → 70-90% gated). **Caveat (Pedro, 2026-06-10):** those paper
  numbers are themselves method-dependent estimates — one sampling strategy,
  one annotator process, one window — not law. A different method can
  legitimately yield a different number. This is now a standing spec rule
  (Measurement Provenance Principle in
  [[2026-06-09-research-thread-builder-workbench]]): any number that gates a
  product decision gets an alternate-method probe before it hardens. The
  stratified-sampling issue (#222) is the first such probe: the current
  cluster population is partly an artifact of latest-N sampling.
- **Capacity/coverage ceilings** (15K snapshot cap, 7.4% classification
  coverage, 3.5% NLP coverage) — these are NOT editorial decisions. They are
  silent recall losses that nobody chose per-signal.

The product principle already adopted for search ("No Silent Filtering": rank
down, label, ledger — never silently omit) currently applies only to the
research plan. The ingest→serve pipeline has no equivalent ledger. That is
the actual problem behind the 99% number.

## 1. The T-1h idea: right instinct, wrong mechanism

Pedro's proposal: collect hourly, serve one hour later, so served information
is always processed.

**Why the instinct is right:** served surfaces today mix maturity levels
silently. A signal seen at minute 5 may have raw GDELT tone, no NER, no topic
assignment; the same signal at hour 6 looks different. Counts shift under the
user. Nothing tells the user which state they're looking at.

**Why a blanket 1-hour delay doesn't deliver it:** the bottleneck is not
time, it's throughput. NLP covers 3.5% of a 24h window — delaying serving by
1h would deliver data that is still ~96% unprocessed, just older. Topic
classification (the 30-min cron) does clear within ~1h, but NLP never catches
up at current capacity (#163/#164/#184 territory). A delay buys consistency
only for the pipelines that actually complete within the delay.

**Proposal — maturity contract instead of delay:**

Serve everything, but label maturity, and let surfaces choose their floor:

| Maturity tier | Meaning | Guarantee |
|---|---|---|
| `provisional` | ingested < 1h ago | exists, deduped; tone is raw GDELT; topic/NLP may be missing |
| `classified` | topic cron has passed (≤1h) | dedup + topic assignment stable; counts stop moving |
| `enriched` | NLP done | sentiment is RoBERTa, NER done |

- Aggregate surfaces (Brief, threads, country counts) read from **sealed
  hours only** (last fully-elapsed hour, `classified` floor). This is
  Pedro's T-1h, applied exactly where it matters: counts and rankings stop
  shifting under the user. Cheap: pre-agg tables already work this way;
  the change is making live-count endpoints respect the same boundary.
- Stream/live surfaces keep serving `provisional` but **badge it** ("last
  hour, unconsolidated") — Atlas's "what's moving now" value survives.
- `enriched` is never promised globally until NLP capacity is solved; it is
  a per-signal badge, not a tier gate.

This extends spec capability H (window contract) backward: H defined honesty
bands for old data (hot/processed/archive); this defines honesty bands for
**new** data. Same product idea: never pretend uniform depth.

## 2. The 99% funnel: don't loosen gates — make the discarded pool reachable

Wrong attack: lowering precision gates for diversity. Paper 1 measured what
lives below the gates (41.6% precision, off-topic/scope-mismatch dominated).
Diversity of noise is not diversity of signal.

Right attack, three moves:

### 2a. Funnel observability ledger (do first — cheap, pure measurement)

A nightly (or on-demand) report + `/api/v2/stats/funnel` endpoint:
stage-by-stage counts with drop reasons, per day:

```text
raw → deduped → blocklisted → classified → nlp'd → snapshot-sampled →
clustered → gate-survived → thread-served
```

Today those numbers required hand-written SQL (section 0). Make the funnel a
first-class observable so "we serve 1%" becomes "we drop 21% syndication,
71% unclassified, 92% snapshot-uncapped..." — each with an owner. This is
the pipeline-level version of the research plan's downranking ledger, and it
feeds Paper 6/Paper 2 with real numbers.

### 2b. Raise the capacity ceilings that are not editorial

In measured-impact order:

1. **Snapshot input cap 15K** — the cheapest lever. The cap exists for
   embedding cost on the M1; measure actual headroom and raise it, or sample
   stratified-by-country instead of latest-N (latest-N over-represents
   high-volume anglophone sources — a *diversity* loss exactly of the kind
   Pedro is worried about).
2. **Classification coverage 7.4%** — corpus-mined lexicon (#185) widens the
   assigned pool with $0 inference. Each point of coverage is ~1.5K more
   signals/day eligible for threads.
3. **NLP 3.5%** — already tracked (#163 split process, #164 backfill ADR,
   #184 worker limit). The maturity contract (section 1) makes this gap
   visible instead of silent, which is the prerequisite for prioritizing it.

### 2c. Second-chance retrieval: gates curate defaults, search reaches the full corpus

The deepest fix and it's already on the roadmap: default surfaces (Brief,
Watchlist, threads) stay heavily gated — that's curation. But a research
query (Phase 1.5 semantic lane, #161 query-time enrichment) should retrieve
from the **full deduped corpus** (153K), not just the gated pool, with
evidence labels carrying the quality verdict (`weak_support`,
`below_gate`, `unclassified`). The 99% is then not "deleted" — it is
default-hidden but query-reachable, with the tray/ledger pattern the
research workflow already established.

One rule ties it together:

```text
Gates decide what Atlas volunteers.
Gates must not decide what Atlas can find when asked.
```

### What about deletion?

Retention policy deletes unprocessed signals after 90 days. With the archive
line (external disk, manifests verified) the raw sample is preserved; the
above does not require changing retention — it requires the query path
(2c) to exist before signals age out of the hot window, plus the archive
bridge staying an explicit future issue (capability H).

## 3. "Why Atlas and not Google?"

The spec does **not** answer this, and it's the right question to force. It
is a positioning question, so it belongs here / in a positioning doc, not in
the workflow spec — but the answer is built FROM the spec's features.

Google answers: *"find me documents matching these words, ranked by
popularity/SEO/personalization, one query at a time, no memory."*

Atlas answers questions Google structurally cannot:

| Question | Why Google can't | Atlas mechanism |
|---|---|---|
| "Who is talking about this, and who is NOT?" | Google shows what exists; it cannot show absence | coverage gaps, silent-risk (#172), source lanes |
| "How is the same story framed differently across countries/source families?" | one ranked list, no source-family model | who-says-what matrix, frame comparison, drift |
| "Is this story accelerating or fading?" | no temporal signal model | movement (changed_10h → Kalman feed #219), timelines |
| "Is this claim supported, contested, or fringe-amplified?" | ranking ≠ verification; SEO rewards the claim | evidence roles, contradiction surfacing, credibility tiers (#217), unsupported-claim flags |
| "What did my investigation look like and how did I get here?" | no memory between queries | Workbench route, pins, trail (Phase 2) |
| "Why am I seeing this result?" | opaque ranking | reason codes, score components, downranking ledger |
| "What is happening in places that don't write in English?" | English-dominant ranking | cross-language normalization, multilingual lanes (Tier B) |

Compressed positioning:

```text
Google finds documents. Atlas instruments the information field:
who says what, where, with what frame, with what evidence,
what's moving, and what's missing — with inspectable reasons
and investigation memory.
```

**The honest test** (and the real success criterion behind the forcing
cases): the spec's "Web Investigation Baseline" sections document ~30-60 min
of skilled manual googling for each forcing case. Atlas wins when it gets a
user to an equal-or-better picture in minutes, **plus** the things Google
never shows: the gaps, the frames side-by-side, and the route. Each forcing
case is exactly that benchmark — keep writing the web baseline for every new
fixture, because it is the Google-comparison control group.

Where Atlas honestly does NOT beat Google today: document-level recall
(Google's index is the web; our corpus is GDELT+RSS+trends+wiki), arbitrary
topics outside the ingested field, and deep document reading. Positioning
must not pretend otherwise; the external-context lane (Phase 5) exists
precisely because Atlas should *orchestrate* web context, not replace it.

## Actions taken (approved by Pedro 2026-06-10)

1. **#220 — funnel observability ledger** (2a): stats endpoint + nightly
   report; measurement only.
2. **#221 — serving maturity contract** (1): sealed-hour floor for aggregate
   surfaces + provisional badge for live stream; spec capability H extended.
3. **#222 — stratified snapshot sampling** (2b.1): also the first
   Measurement Provenance probe.
4. **Folded into Phase 1.5 scope** (2c): semantic lane retrieves the full
   deduped corpus with quality labels — spec Phase 1.5 deliverables +
   acceptance updated.
5. **Spec amended**: Pipeline Funnel Principle + Measurement Provenance
   Principle added to [[2026-06-09-research-thread-builder-workbench]]
   (see its Changelog, second 2026-06-10 pass).
6. **Positioning** stays seeded in section 3; promote to standalone when
   Landing/marketing needs it.

## Obsidian connections

- Spec (work guide): [[2026-06-09-research-thread-builder-workbench]]
- Spec review that preceded this: [[2026-06-10-research-workflow-spec-review]]
- Paper line: [[2026-05-27-atlas-papers-master-plan]],
  [[2026-06-03-paper-1-result-skeleton]], [[2026-06-02-rq1-improvement-methods]]
- Data line: [[2026-05-20-atlas-hot-cold-data-operating-model-design]],
  [[2026-05-21-data-operating-roadmap]]
- Ranking calibration this builds on:
  `docs/research/ranking-calibration/2026-06-10-ranking-calibration.md`
