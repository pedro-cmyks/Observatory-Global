# Gap 2 — event-level umbrella via an LLM same-event judge (2026-07-14)

**Status: DESIGN, validated by a live read-only probe. Not yet wired.**

## The problem, and why the last approach failed

Gap 2 = reconnect the fragments of ONE real-world event that clustering split into
several threads. The live case: the US-Iran confrontation is three active threads —

| id | label | n |
|---:|---|---:|
| 121 | US Bombards Iran Over Ormuz Attack | 369 |
| 583 | US-Iran Military Strikes | 91 |
| 881 | Bahrain Accuses Iran of Drone Attack | 69 |

These should serve as ONE umbrella over three children. The earlier attempt —
shared distinctive **actors** (`_shared_actor_edges` in `build_umbrella_topics.py`)
— was a **negative result** (see `docs/state/2026-07-14-ner-184-diagnosis-plan.md`):
these fragments do not share distinctive persons (Ormuz / Bahrain-drone / US-Iran
carry different actors), so on the active set the linkage either **chained
unrelated wars** at a loose centroid floor or produced **zero edges** at a tight
one. There is no operating point. The connector is the **event** (same episode,
place, actors-as-a-situation), not a shared byline — and semantic-centroid linkage
alone can't tell "same event" from "same domain" (it merges Iran+Ukraine or emits
nothing, the same cliff #224/R2 hit).

## The design: an LLM same-event judge over the active labels

An LLM reading the *labels* resolves same-event vs same-domain trivially. The
mechanism:

1. **Candidate set** — the active `dynamic_topics` (`state='active'`, non-junk,
   labeled). At today's scale (~28–60 active) feed all labels in ONE call. At
   larger scale, bound the set first with a loose centroid-cosine prefilter
   (≥0.80) so the LLM only judges plausible neighbours; batch if needed.
2. **Same-event judge** — one LLM call (DeepSeek, temp 0, JSON). The prompt
   (validated below, verbatim in `scripts/gap2_event_judge_probe.py`) groups only
   threads reporting the **same real-world event or a single tightly-coupled
   situation**, with hard rules: fragments-of-one-incident merge; **distinct
   events stay separate even in the same domain** (two different wars, two
   countries' elections); a recurring **category** label ("Crime and Accidents",
   "TV News Broadcasts") is never an event; **precision over recall** — do not
   merge on doubt. Output: `{"events":[{"name","topic_ids","confidence"}]}`, 2+
   ids per group.
3. **Groups → umbrellas** — each returned group with ≥2 ids and confidence ≥ 0.70
   becomes an umbrella, written through the EXISTING umbrella infra (mig 058
   `parent_id`/`is_umbrella`; `build_umbrella_topics.py`). Umbrella label = the
   LLM event name; centroid = centroid-of-children (existing). The LLM verdict is
   a labeled, auditable basis — `umbrella_basis='llm-same-event-v1'` + the event
   name is the "why grouped" receipt (no silent merges).
4. **Serving** — unchanged. Top-level `/threads` already collapses umbrella
   children (R2), so the umbrella serves as one row over its children; drill-down
   shows the fragments.

## Validation (live probe, read-only, 2026-07-14)

`backend/scripts/gap2_event_judge_probe.py` ran the judge over the 28 live active
threads. Result — it recovers exactly the groups shared-actor could not, and
keeps distinct events apart:

```
● US-Iran Military Strikes        (conf 0.85)  → 121, 583, 881
● Ukraine War Updates             (conf 0.90)  → 452, 439
● Trump FIFA World Cup Scandal    (conf 0.90)  → 2029, 90   (a duplicate identity)

ACCEPTANCE
US-Iran fragments [121,583,881] → one group: True
Iran group != Ukraine group (no cross-war merge): True
```

Precision held: only 3 confident groups, no chaining (World Cup threads were NOT
swept into Trump-FIFA; distinct conflicts stayed separate). The exact fragments
with no shared actors merged correctly. The design is sound.

## Guardrails / cost / honesty

- **Determinism + cost:** temp 0, one call per snapshot (~$0.001). Cache by the
  sorted active-id set — re-judge only when the active set changes.
- **Precision-first + confidence floor** prevents the chaining that killed the
  centroid and actor approaches.
- **Auditable basis** (`llm-same-event-v1` + event name) — every merge carries its
  reason, consistent with the no-silent-filtering rule.
- **Reversible** behind a flag (`ATLAS_EVENT_UMBRELLA=on`); umbrellas are already
  rebuilt each pass, so turning it off reverts to semantic/singleton serving.
- **Bonus:** it also collapses duplicate identities (2029≡90 Trump-FIFA) — a free
  dedupe the clustering rebuild leaves behind.

## Build steps (when greenlit)

1. `assign_event_umbrellas.py` (or a `--linkage llm-event` mode in
   `build_umbrella_topics.py`): pull active labels → judge → write umbrellas with
   `umbrella_basis`. TDD the pure grouping (verdict JSON → parent/child rows) with
   a fixture; the LLM call is mocked.
2. Migration: add `umbrella_basis` provenance (or reuse an existing label/model
   column) so the "why" is queryable.
3. Wire into the scoped-snapshot cron Step where umbrellas already build; gate on
   the flag; cache by active-id set.
4. Serving needs no change; verify the US-Iran umbrella serves as one `/threads`
   row over 121/583/881.

Probe: `backend/scripts/gap2_event_judge_probe.py` (read-only, repeatable).
