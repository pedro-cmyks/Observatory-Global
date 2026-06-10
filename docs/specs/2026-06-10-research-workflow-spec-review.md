# Research Workflow Spec — Critical Review

**Date:** 2026-06-10
**Status:** review / proposed amendments
**Reviews:** `docs/specs/2026-06-09-research-thread-builder-workbench.md`
**Context:** Phases 0.5, 1a, 1b shipped (+ ranking calibration harness). This
review judges the spec as written before continuing to Phase 1.5/2, and checks
its alignment with the paper/research line and the data-backing line.

## Verdict summary

The spec's product instincts are right: anchors over dossiers, no silent
filtering, honest gaps, two forcing cases, threads as the visible model. Those
survived contact with implementation.

The spec as a **document** has structural problems: it is a vision narrative, a
normative contract, a backlog triage, and a research-methods essay in one file,
with a "this section wins" self-amendment pattern. Three days into
implementation it has already drifted from reality in four places. It also has
**zero references to the paper line**, even though three of its hardest
capabilities are exactly what the paper series measures — and one required
capability (source credibility) has no backing anywhere.

What follows: confirmed strengths, divergences between spec and shipped
reality, alignment gaps with the other product lines, and concrete proposals.

## What the spec got right (keep, do not relitigate)

1. **Anchors, not dossiers.** Phase 1a/1b shipped exactly this shape and live
   smoke confirms it is the right response to broad queries.
2. **No Silent Filtering.** The ledger/tray/reason-code requirement forced an
   honest discovery implementation (skipped candidates are counted with reason
   codes). This is the spec's strongest product-trust idea.
3. **Phasing discipline (0.5 / 1a / 1b / 1.5).** The split survived
   implementation without rework. Phase 0.5 first (list/detail trust) was the
   correct call.
4. **Two forcing cases.** Topic research + claim verification cover genuinely
   different failure modes. Both are now automated fixtures.
5. **Terminology correction (threads = dynamic_topics).** Prevented a
   two-taxonomy product. All Phase 1 code reasons over threads.

## Where the spec already diverged from shipped reality

These are not future risks; they happened during Phases 1a/1b.

### D1. "Seed ranking weights from the #154 audit" was wrong

The spec (Scope Corrections + Tier C + attack order step 3) claims the
source-quality audit should produce the initial `w_*` weights. Implemented
finding: source metrics inform at most `source_actor_value` and `noise_risk` —
2 of 11 components. There is no mapping from source quality to the
intent-vs-evidence tradeoff. Weights were instead calibrated by a
constraint-satisfaction harness over the spec's *own acceptance criteria*
(gold orderings) plus live forcing-case constraints
(`backend/scripts/calibrate_research_ranking.py`,
`docs/research/ranking-calibration/2026-06-10-ranking-calibration.md`).
21/21 constraints vs 20/21 for the hand-tuned baseline.

**Amendment:** rewrite the ranking-weights paragraph: #154 narrows to
grounding `noise_risk` inputs and source-tier priors; weights come from the
calibration harness; rerun on data shift or when user relevance judgments
arrive. (Already noted on #154.)

### D2. "Evidence must outweigh intent" stopped being true once the relevance gate existed

Spec: "Do not ship an equal-weight sum: it lets cheap-to-score components
(`geo_entity_fit`, `intent_match`) dominate the expensive-but-important ones."
Implementation found the opposite failure first: big, fast-moving threads with
**no** intent match buried the direct match (live: armed-conflict 0.90
evidence / 0.94 movement outranking the water-stress direct match). The fix is
a multiplicative relevance gate (`0.5 + 0.5·intent_match`, exposed per anchor)
— a mechanism the spec does not contain — after which calibrated
`intent_match` (0.232) legitimately leads `evidence_strength` (0.146).

**Amendment:** add the relevance gate to the ranking model section; restate
the guardrail as "geo/movement must not dominate evidence/answerability"
(which is what the calibration enforces).

### D3. Movement signal: the spec names a provider that does not provide

Scope Corrections: the Kalman state pilot "is the concrete provider for the
ranking `movement_signal` component." Reality: the pilot is a **manual,
read-only script** with no callable feed (by explicit guardrail). Phase 1b
shipped `movement_signal` from `changed_10h` (thread rows). Naming a
non-callable provider in the normative ranking section is how silent scope
creep into the pilot's read-only guarantee happens.

**Amendment:** v1 provider = `changed_10h`/`trend` from thread rows. The
Kalman pilot is a *candidate v2 provider* requiring an explicit promotion
decision (cron-written state, new issue, Pedro sign-off per the read-only
guardrail). Until then it is not in the ranking dataflow.

### D4. The walkthrough fixture from "Immediate Next Step" still does not exist end-to-end

What exists: unit-level fixtures (parser, discovery, ranking, calibration
constraints) + live smoke. What the spec asked for: the 8-step walkthrough
(search → country → thread → pin → branch → Workbench) as one automated
acceptance fixture. Steps 4-8 are Phase 2 surface, so the full fixture cannot
exist yet — but the spec text reads as if it should already.

**Amendment:** re-scope the walkthrough fixture as the **Phase 2 exit
criterion**, and state that Phases 1a/1b acceptance = the per-layer fixtures
that now exist.

## Alignment gaps with the paper / research line

The spec never cites the paper series
(`docs/research/atlas-paper/2026-05-27-atlas-papers-master-plan.md`). This is
the review's most important finding: three spec capabilities are unfunded
checks drawn on accounts the paper line manages.

### P1. Evidence Role Classifier (capability C) ↔ Paper 1 — connected in spirit, unbound in numbers

Spec capability C requires roles including `contradiction`, `noise`,
`osint_verification`, and the claim-verification case makes `contradiction`
**load-bearing** ("rebuttals must surface as first-class contradicting
evidence"). Paper 1's measured reality: evidence-role student v1 = **78.2%
primary-evidence precision, 71.4% noise recall**; Atlas v2 topic precision
41.6%; `contradiction` is not a trained class today. The spec writes
acceptance language that current measured models cannot honor, and Phase 4's
85% precision target is stated without binding to the existing benchmark
infrastructure (`atlas-topic-benchmark-v2`, consensus gold, Wilson CIs) that
would make it measurable.

**Proposal:** every model-dependent capability in the spec must carry (a) its
benchmark line, (b) current measured precision, (c) the UI behavior when the
model is wrong. Phase 4 should be explicitly defined as "extend Paper 1
benchmark machinery to research-workflow roles (`contradiction` first)" — that
makes Phase 4 *also* a Paper 1 contribution (new role class + measured
distillation), instead of a parallel quality effort.

### P2. Source credibility labeling has no owner anywhere

Claim-verification demands "low-credibility/conspiracy outlets vs national met
agency vs scientific fact-checkers must be distinguishable." Search the spec's
Required Capabilities A–F: credibility scoring is **absent**. Search the
backlog: no issue. What exists: `source_blocklist.py`, `is_state_media`,
`source_family` — none of which is a credibility score. Meanwhile **Paper 2 is
literally "Cross-source source-quality scoring for narrative intelligence"**
and #154 is the audit that feeds it. Three lines describe the same object
without referencing each other.

**Proposal:** add capability **G — Source credibility tiers** to the spec,
implemented as the product face of Paper 2 + #154: start with a small,
inspectable tier map (state-media flag + fact-checker allowlist +
known-conspiracy list seeded from the claim-verification baseline sources),
measured and expanded by the Paper 2 methodology. File one issue; tier it
rw-tier-c. Without this, the claim-verification forcing case **cannot pass
honestly** — the who-says-what matrix would present Global Research and NOAA
as peers.

### P3. The Workbench is the missing relevance-judgment instrument

The calibration harness's known limit: no real user relevance judgments
(weights fit to spec-derived constraints). The spec's own Phase 2 creates the
instrument that fixes this — anchor impressions → opens → pins are graded
relevance labels (shown/ignored/opened/pinned). The spec mentions query logs
once (autocomplete context) and never connects pin behavior to ranking
calibration or to Paper 7 (analyst workflow).

**Proposal:** Phase 2 must log `(plan_id, anchor_id, rank_shown, opened,
pinned, dwell)` from day one — locally, no new infra, a Postgres table or
even JSONL. This is simultaneously: the ranking calibration dataset, the
Paper 7 analyst-workflow evidence, and the input for suggestion-guided search.
Cheap at build time, impossible to retrofit.

## Alignment gaps with the data-backing line

### B1. Long-window research has no defined data contract

`POST /api/v2/research/plan` accepts `hours` up to 720. The spec's retrieval
lanes list "historical processed" and Open Problem 5 concedes historical
tables "may lack enough evidence detail" with a hand-waved "archive bridge."
Reality of the data line: hot window (~7d in `signals_v2`), processed
historical aggregates (`/Volumes/Ext/Atlas/Processed`, no per-signal
evidence), raw archive on the external disk with verified manifests (3.9M
rows) but **no query path from the API**. Research investigations are exactly
the long-window use case ("recent + historical context" is in the spec's own
interpreted-intent example), and Phase 0.5 already showed long windows are
where list/detail trust breaks.

**Proposal:** define the window contract now, in three honest bands, and make
the research plan emit it as a gap note instead of pretending uniform depth:

| Window | Evidence depth | Research-plan behavior |
|---|---|---|
| ≤168h (hot) | full signals + evidence samples | all lanes |
| 168h–~90d (processed) | aggregates only | thread/country anchors OK; evidence samples marked unavailable; gap note "evidence detail limited to aggregates" |
| beyond / archive | manifests on external disk | not queryable live; research plan states it; archive bridge is its own future issue, not an implicit promise |

This also gives Paper 6 (temporal model) its product-facing consequence.

### B2. Reddit lane scheduling vs investigation coverage

The spec requires the public-discussion lane DB-served from `ingest_reddit.py`
and says the subreddit list "should be extended to cover the investigation's
countries/topics." That makes lane coverage a **function of a static cron
list** — an investigation about Iran works only if `r/iran` was already being
ingested. The spec does not say what the lane reports when the country has no
ingested subreddit.

**Proposal:** the lane must self-describe coverage: when geo_scope has no
ingested subreddits, emit `coverage_gap {lane: public_discussion, reason:
not_ingested}` (the Phase 1a gap mechanism already supports this). Extending
the ingest list is then a visible, data-driven action instead of silent
emptiness.

### B3. Workbench localStorage contradicts "durable research archive"

Phase 2 says localStorage v1; the sidebar section promises "a durable research
archive." localStorage is per-browser, evictable, and the Phase 3
report/dossier makes pins the source of truth. Losing localStorage = losing
the investigation and any dossier provenance.

**Proposal:** keep localStorage v1 (right call for speed) but (a) delete the
word "durable" from v1 language, (b) make export (Phase 3 Markdown/JSON) the
explicit durability mechanism and ship a minimal JSON export **in Phase 2**,
not 3, (c) note that pin-event logging (P3) incidentally provides server-side
reconstruction capability.

## Structural problems with the document itself

### S1. Self-amending "this section wins" pattern

Scope Corrections "override looser language elsewhere; where any section
disagrees, this section wins." A 1569-line document where the reader must
mentally apply a patch layer is how D1–D3 style drift happens — corrections
accrete instead of the text being fixed. The spec is already on its second
correction layer (Product Review Correction + Scope Corrections).

**Proposal:** stop patching; split. The document is three things:

1. **Normative contract** (~300 lines): API contracts, ranking model,
   capability list with benchmark bindings, phase acceptance criteria, window
   contract. This is the only part implementation must obey, and it gets
   *edited in place* when reality wins.
2. **Vision & rationale** (the walkthrough, web baselines, how-people-search,
   forcing-case narratives): moves to `docs/research/`, explicitly
   non-normative, never needs patching.
3. **Backlog alignment** (tiers, issue map): lives in the roadmap doc — it is
   already duplicated in `docs/roadmap/2026-06-09-research-workflow-roadmap.md`
   and the two will diverge.

### S2. The umbrella #213 has no closing condition

The spec sequences 30+ issues across 7 tiers under one umbrella. As written,
#213 closes when... everything closes. Umbrella issues without exit criteria
become permanent.

**Proposal:** #213 closes when the **Phase 2 walkthrough fixture passes**
(both forcing cases, E2E, automated). Everything in Tiers B/C/D beyond that is
ongoing product work that does not need an umbrella to justify it.

### S3. Acceptance criteria mix measurable and unmeasurable

Compare: "returns at least N anchors" (measurable, shipped) vs "Atlas shows
who says what and how frames differ" (unmeasurable as written) vs "85%
precision on direct evidence" (measurable but unbound to a benchmark). The
unmeasurable ones are where scope disputes will happen.

**Proposal:** in the normative contract, every acceptance criterion is either
an automated fixture or a benchmark number with named tooling. Aspirational
language lives in the vision doc.

## Proposed amendment plan (ordered)

1. **Now (docs-only, 1 commit):** apply D1–D4 amendments to the spec text;
   add capability G (source credibility) with the Paper 2 / #154 binding;
   add the window contract table (B1); fix "durable" language (B3). Add a
   changelog section to the spec instead of a third correction layer.
2. **Now (issues):** file capability-G issue (rw-tier-c); file pin-event
   logging as an explicit Phase 2 deliverable on #213 (P3); add the
   public-discussion coverage-gap behavior to the Phase 1.5/2 scope (B2).
3. **Next session (structural):** execute the S1 split — normative contract
   extracted, vision content moved under `docs/research/`, tier tables left
   only in the roadmap. Define #213 exit criterion (S2).
4. **Phase 1.5 proceeds unchanged** — the semantic lane survives this review
   intact; it is correctly scoped, reuses existing local e5-base, and is the
   real recall fix. The only addition: its fixtures should include one
   cross-language case (Persian/Arabic headline ↔ Spanish query) because that
   is the stated reason the lane exists.

## What this review deliberately does not propose

- No new ranking components (the calibrated model is young; let it accumulate
  violations before adding dimensions).
- No backend Workbench persistence (localStorage + export + event log covers
  v1 needs).
- No LLM in the research plan hot path (the deterministic+semantic design is
  a feature, not a limitation — it keeps the plan explainable and $0).
