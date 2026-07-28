# Gold rubric v2 — UI arm (content-first)

**Date:** 2026-07-30 · frozen BEFORE the full-20 UI run
**Supersedes:** the v1 rubric's UI application (v1 stays the record for the API-arm runs).
**Why v2:** the pilot verified NAVIGATION (clicks connect, panels load) and under-verified
CONTENT. Pedro's review of the pilot named the gap exactly: search offers related threads,
you open one, and the related ones are NOT carried into the detail — the information the
previous surface promised evaporates on arrival. "It loaded" is not evidence. The question
is **¿a qué llegué, y qué información trae?**

## Scale (rendered pixels ONLY — payload fields invisible on screen do not count)

| Level | Definition |
|---|---|
| **0** | Absent or MISLEADING: a confidently-presented wrong thread, an unflagged blob, or a degraded/empty state that does not say so. |
| **1a** | Honest floor: no thread; the absence is stated on screen; any raw material is labeled as unverified/partial. |
| **1b** | Thread-less but INFORMED: no organized thread, yet rendered receipts substantively answer the question (the GQ-08 case: 11/12 Indonesian receipts covering both strands). Counts toward *informed rate*, NOT *answered rate*. |
| **2** | A specific on-topic thread whose RENDERED content answers the core question: attributed receipts (ROR@20 ≥0.75 among what is shown), key numbers present and attributed, no unflagged cross-story blending. |
| **3** | Level 2 PLUS the relations survive: who-says-what / divergent figures attributed side-by-side, and the event's OTHER threads or strands reachable from within the detail without losing context. |

## Mandatory per-query CONTENT INVENTORY
For every panel visited, record — quoting the screen, not the payload:
- receipts actually rendered: count, languages, outlets (and whether domestic outlets appear for country-anchored queries);
- the concrete claims/numbers shown, with their attribution as displayed;
- every honesty chip as RENDERED (label-court status, coherence tier, state-media ⚑, partial-match tags) — a chip in JSON but not on screen scores as absent (D5-pixels);
- related-content affordances present at that surface (sibling threads, "stories inside", neighbors).

## New dimension N1 — NAVIGATION LOSS (Pedro's observation)
When surface A offers N related items for the query (e.g. the search dropdown lists 5
Berlin-Pride threads), and the analyst opens one: does surface B preserve, reference, or
offer a path back to the other N−1? Record **promised vs delivered**. Loss ⇒ tag
`NAV-LOSS` with the concrete items lost. This is scored per query and reported as a
product-defect count, independent of the 0–3 level (a query can score 2 AND carry
NAV-LOSS).

## Controls (GQ-15..20)
A control PASSES iff **no surface presents a confident answer-claim**. Honest floors of
any kind (1a or 1b-without-an-answer-claim) pass. A control at ≥2 fails and — kill K2,
unchanged — any control at 3 voids the run.

## K1 v2 (fixes the pre-registered contradiction, logged 2026-07-28)
v1 voided a run where `mean(controls) ≥ 1.0`, which voids six perfectly honest floors.
**K1 v2: the control arm is VALID iff every control ≤1; any control ≥2 is a control FAIL
(counted, reported); ≥2 control FAILs void the run.** The v1 contradiction stays on the
record; thresholds moved here in writing, before the run, with the reason.

## Metrics reported
- **Answered rate** (share of non-controls at ≥2) — the roadmap number.
- **Informed rate** (share at ≥1b) — new, secondary; the raw lane's honest credit.
- **Honesty rate** — share of non-answered queries whose failure mode is honest (1a/1b)
  rather than misleading (0).
- **NAV-LOSS count** and **blob-flag count** (unflagged multi-story threads observed) —
  product-defect tallies from the inventory.
- Divergence vs the API arm per query (UI-BETTER / SAME / UI-WORSE / UI-MISS).

## Procedure notes
- Real prod data; no fixture shims. ~8 min cap per query. Dismiss tours. If a surface
  errors/hangs, that IS product experience — record and continue.
- Distinguish "data absent" from "data present but the UI never led me there" (UI-MISS,
  navigable only via URL or API is NOT reachable).
- The 20 queries run in 4 batches of 5 (one browser, sequential); each batch's artifact
  appends to one dated run file so partial completion is still a valid partial record.
