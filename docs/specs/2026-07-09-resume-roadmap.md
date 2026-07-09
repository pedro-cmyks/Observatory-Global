# Atlas resume roadmap — structured plan (2026-07-09)

Written to start immediately on resume. Pairs with the vision doc
`docs/specs/2026-07-08-narrative-intelligence-vision.md` (the deeper capability
layers) and today's engine fixes. Principle everywhere: **math/data first, LLM
only for the brief; measure honestly; never leave data silently unclassified —
an unclassifiable floor is a RESULT to report, not a black hole.**

## Where we are (baseline on resume)
- Embedding: durable (chunked query + `SET LOCAL statement_timeout=0` per insert), cron sustains it off-peak. Draining a ~196K backlog.
- Clustering recall: 30 → 597 threads; total story coverage 0.04% → ~40%.
- Quality gate (`topic_junk.py`, mig 074 `is_junk`): junk 38% of coverage → 0 active; **useful coverage ~26%** (the honest number); assign window raised 15k→40k (prod 60k).
- Geo attribution fixed; mobile perf (#254) merged; dossier layer (verdict/synthesis/black-hole/whitening/cost-ledger) shipped.
- Operational watch: Supabase DB runs hot under embedder+clustering load (queries timing out) — capacity is a real constraint to monitor.

---

## GOAL 1 — Coverage 80% of the firehose, 80% of that USEFUL
Target: cover ≥80% of daily signals in a story, ≥80% of covered = useful (real
stories, not junk). Current: ~40% total / ~26% useful.

**The honest-floor mandate (Pedro):** if a high % of the firehose is genuine
garbage/unclassifiable, that is a MEASURED RESULT, reported — not stagnant
unclassified data. Every signal ends in one labeled bucket: `useful story` /
`junk (typed: roundup/celebrity/listicle/…)` / `unclassifiable-noise (measured)`.

Workstream A steps (sequenced):
1. **A0 — measure the honest ceiling + floor FIRST.** Take 24h signals; classify
   every one into {in-useful-thread, in-junk-thread, unassigned}. For the
   unassigned, split into (a) real-but-unclustered (recall gap) vs (b) genuine
   noise/unclassifiable — using the junk gate + a residual-cluster probe. Report
   the three-way split. This number defines what "80%" even means.
2. **A1 — push the assignment window** (already 40k/60k). Measure coverage vs
   window size; find where useful-coverage plateaus (the numpy assign is cheap;
   cost is embed-fetch + residual HDBSCAN — scale on the M1).
3. **A2 — scoped/regional + multilingual passes** (#229 lever 2 / R1). Global
   HDBSCAN drowns regional stories (Peru recount, a Colombian sub-story). Cluster
   per-country/per-language over the persisted corpus so mid-size real stories
   form their own threads → lifts recall WITHOUT lowering purity.
4. **A3 — language coverage.** Non-English volume vs GDELT English firehose; the
   voice-mix program. Ensure the 80% isn't 80%-of-English.
5. **A4 — cadence/staleness.** Build runs 3×/day; 24h active-member coverage
   decays between runs. Consider more frequent scoped passes or a rolling assign.

Measure: total-cover %, useful-cover %, junk %, unclassifiable-floor % — all four,
every run. Success = useful-cover ≥ 0.8 × total AND total ≥ 0.8 (or the honest
floor explains the gap).

---

## GOAL 2 — Investigations backbone + whole-internet corroboration
Objective: an investigation is not just Atlas-internal; it CORROBORATES against
the open web, so a finding is cross-checked against what the whole internet says.

Current: dossier/connection layer + `deep-research` skill (web fan-out → fetch →
adversarial verify → cited synthesis) exists but is NOT wired into the analyst flow.

Workstream B steps:
1. **B1 — the corroboration lane.** When an analyst pins/builds an investigation,
   run a bounded web-search pass (the deep-research harness) over the thesis +
   pinned actors: who else reports this, what does the open web confirm/contradict,
   what's the established vs contested split. Attach as a "web corroboration"
   section, clearly separated from Atlas-measured findings.
2. **B2 — structured backbone.** Atlas-internal (measured: who-says-what, voice,
   coverage gaps) + web-corroboration (external truth check) + the LLM synthesis
   (grounded, cited, glass-box) = the full report. Each layer labeled by trust.
3. **B3 — contradiction surfacing.** Where Atlas's coverage-derived picture
   disagrees with the open web = itself a finding (a coverage bias / a gap).
Measure: on a test investigation, does web corroboration confirm/contradict Atlas,
and does the report stand alone (Frank test) with the corroboration layer.

---

## GOAL 3 — EMERGING / ANOMALOUS story detection (the new profile — the anti-bias engine)
Objective (Pedro's new capability): surface stories that are EMERGING, out of the
public eye, happening with STRANGE VOLUME, or forming NOVEL RELATIONS not visible
at a glance — the things the analyst is NOT looking for, that their worldview
biases them away from. Atlas finds what you'd miss.

Current raw material: Kalman movement (velocity/surprise), universe orphans
(semantic oddities), heat, the parked #172 silent-risk, co-occurrence edges.

Workstream C steps (the highest-novelty, most-differentiating work):
1. **C1 — anomalous volume vs baseline.** A topic whose volume/velocity is strange
   against ITS OWN history (Kalman surprise) OR against its expected level — a
   spike with no obvious trigger. Already have the Kalman field; turn `surprise`
   into a ranked "unusual right now" surface.
2. **C2 — coverage-vs-attention ratio (the under-the-radar signal, done right).**
   A story with real coverage volume but LOW public attention (trends/forum/wiki)
   = happening but not in the public eye. The revived, measured #172 — the honest
   version (needs an attention denominator that isn't sports/celebrity-dominated).
3. **C3 — novelty / out-of-distribution.** A topic that fits NO existing category,
   or an actor/topic pair that co-occurs for the FIRST time (a relation never seen
   before). Compare emerging topics against the historical topic set + the
   category taxonomy → flag genuinely-new vs known-recurring.
4. **C4 — novel relations (discovery, not validation).** The connection layer,
   inverted: rarity-weighted co-occurrence between actors/topics that appear
   together unusually — surface links a human wouldn't draw. (The dossier connects
   what you pinned; C4 proposes what you SHOULD look at.)
5. **C5 — the anti-bias panel.** Explicitly surface stories DISTANT from the
   analyst's current focus (geo/topic/language) — "you are not looking at this,
   and it's moving." Counters the worldview bias Pedro named.
Measure (task-time): does it surface a real under-the-radar story a human wouldn't
have found? Does a flagged "novel relation" hold up on inspection?

---

## GOAL 4 — The narrative-intelligence vision (deeper layers, now unblocked)
From `2026-07-08-narrative-intelligence-vision.md` (substrate now healthy enough to
build on): the report answers 5W+H; stance/framing (who is favored, honest);
temporal propagation + origin (who started it, coordinated vs organic — the
signature capability); pin-carries-full-thread-context; incremental constellation
in the Workbench (not only at report time); actor = ANY entity (person/org/
company/phenomenon/object/system).

---

## SEQUENCING on resume — "empezar de una"
1. **A0 first** (measure the honest coverage ceiling + junk floor + unclassifiable
   floor). One measurement session; it defines the 80/80 target and grounds all else.
2. **A1–A2** push useful coverage toward 80/80 (window + scoped/multilingual passes).
3. **C1–C2 in parallel** — the emerging/anomalous engine is the highest-novelty,
   most-differentiating capability and reuses existing Kalman/attention material;
   start it alongside coverage.
4. Then **B (web corroboration)** + **C3–C5 (novelty/relations/anti-bias)** +
   the **Goal-4 vision layers**, in that rough order of leverage.
5. Throughout: watch Supabase capacity; keep the cron sustaining embedding;
   spawn engine-heavy work to isolated chats, consolidate to `v3-intel-layer`.

## First concrete actions when we return
- Run A0: the 3-way signal classification (useful / junk-typed / unclassifiable),
  reported as a table — the honest state of the firehose.
- Stand up C1: rank topics by Kalman `surprise` into an "Unusual now" list; eyeball
  whether it surfaces real under-the-radar movement.
- Re-run the LatAm investigation on the now-full+clean engine as the dogfood that
  validates coverage + geo + (eventually) the corroboration + anomaly layers.
