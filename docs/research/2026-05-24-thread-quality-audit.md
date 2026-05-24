# Narrative Threads Quality Audit

**Date:** 2026-05-24.
**Scope:** production `v3-intel-layer` after PR #209 and #210, plus review of
open PR #211.
**Principle:** quality beats volume. Atlas already has enough data; the work now
is to make the surfaced narratives precise, explainable, and honest.

## Executive Summary

The product direction is correct, but the wording and next-step sequencing need
correction.

- **Narrative Threads is the product surface.** "Living" is descriptive, not a
  separate UI category. Do not build a parallel "Live Threads" surface.
- **`/api/v2/threads` is a backend contract for better Narrative Threads.** It
  should feed the existing `NarrativeThreads.tsx` only after quality gates pass.
- **Current production threads are mixed quality.** Some topics are strong
  enough to show; others are not ready for direct UI promotion.
- **PR #211 should not be merged as-is.** Its enriched fields are useful, but
  `top_entities` currently comes from `signals_v2.persons`; that field can
  contain climate/geographic entities such as `el nino` or `pacific ocean`.
  Those may be valid entities, but they are not persons and should not be shown
  as person chips.

## What NER Means Here

NER means **Named Entity Recognition**: extracting named things from text.
Entities can be people, organizations, places, events, products, climate
phenomena, and more.

The issue is not that `El Niño` or `Pacific Ocean` are necessarily bad
entities. In climate/disaster contexts they can be meaningful. The issue is
that Atlas currently stores/exposes them through a field named `persons` or
`top_entities` without a type. A UI chip row that implies "people involved"
should not mix:

- people: `donald trump`, `keir starmer`;
- climate phenomena: `el nino`;
- geographies: `pacific ocean`;
- religious/cultural phrases: `jesus christ`.

Correct product treatment: expose typed entities, for example:

```json
{
  "entities": {
    "people": [],
    "places": ["Pacific Ocean"],
    "climate": ["El Niño"],
    "organizations": []
  }
}
```

Until entity typing exists, PR #211 should not present `top_entities` as a
frontend-ready field.

## Current Production State

Verified against Fly production (`atlas-api-pedro`) on 2026-05-24:

- Fly app machine is running version `182`.
- `/api/v2/threads?hours=24&limit=3` returns
  `contract = living-narrative-threads-v0`.
- `/api/v2/briefing?hours=24` returns populated `top_threads`.
- `NarrativeThreads.tsx` still uses `/api/v2/narratives`, not `/api/v2/threads`.
  The visible app layout has not been swapped yet.
- Open PR #211 enriches `/api/v2/threads`; it is not deployed.

Important: production API includes M1/M2, but visible `NarrativeThreads` UI is
still on the older narratives endpoint. This is good. It gives us room to audit
quality before changing the main product surface.

## Method

Queries used:

1. Production API:
   - `/api/v2/threads?hours=24&limit=10`
   - `/api/v2/threads/{thread_id}?hours=24`
   - `/api/v2/briefing?hours=24`
2. Production database via Fly app `DATABASE_URL`, read-only SQL:
   - 24h assignment count for `theme-hint-lex-v2`;
   - top topic volume and `lex_pct`;
   - random 8-headline samples per top topic;
   - source and country-code quality checks.

Live assignment base:

| Metric | Value |
|---|---:|
| 24h `theme-hint-lex-v2` assignments | 25,138 |

## Top Topic Quality Snapshot

`lex_pct` is the share of topic assignments supported by an actual headline
lexicon term. Low `lex_pct` means the topic is mostly riding GDELT theme hints.
Theme hints are useful, but they are not enough for user-facing confidence.

| Topic | 24h assignments | avg_conf | lex_pct | Audit read |
|---|---:|---:|---:|---|
| `armed-conflict-escalation` | 7,459 | 0.659 | 5.6% | Mixed. Strong Ukraine/Iran evidence, but broad conflict/security hints admit protest/culture noise. |
| `disease-outbreak` | 4,142 | 0.672 | 9.5% | Mixed. Ebola/outbreak rows are good; generic medical/safety rows pollute. |
| `gang-control-urban-security` | 2,373 | 0.652 | 13.8% | Medium. Crime/security rows mostly fit, but label may be too narrow for police/security incidents. |
| `labor-strike-disruption` | 1,804 | 0.652 | 37.7% | Mixed. `strike` and `union` create false positives: oil strikes, credit unions, political unions. |
| `election-legitimacy-dispute` | 1,597 | 0.664 | 33.4% | Medium. Real elections present; sports/club elections and non-legitimacy primaries leak in. |
| `gender-violence-rights` | 1,494 | 0.650 | 0.2% | Poor. Mostly rides `KILL`, `HUMAN_RIGHTS`, `SOC_GENERALCRIME`; sample includes unrelated murder/TV/general crime. |
| `flood-landslide-disaster` | 1,092 | 0.654 | 28.9% | Mixed. Flood/evacuation rows present; generic evacuation/landscape/culture rows leak in. |
| `fuel-subsidy-unrest` | 771 | 0.686 | 38.4% | Medium-good. Fuel price rows are strong; non-fuel energy/theme-only rows still leak in. |
| `water-stress-drought` | 658 | 0.653 | 12.3% | Medium. Drought rows are good; dry-season tourism and generic water/place rows leak in. |
| `transport-corridor-disruption` | 478 | 0.651 | 22.6% | Poor. `canal` causes entertainment/TV/sports false positives. |
| `forced-displacement` | 452 | 0.654 | 30.8% | Mixed. Evacuation/displacement evidence present; broad death/conflict/theme noise remains. |
| `heat-health-risk` | 327 | 0.659 | 100.0% | Strong. Heatwave rows are consistently relevant. |
| `food-price-stress` | 315 | 0.657 | 4.4% | Mixed. Strong evidence exists, but random sample shows generic price/inflation/business rows. |
| `mining-royalty-risk` | 270 | 0.745 | 80.7% | Strong cluster, weak label. It is mine-disaster/resource-risk, not primarily royalty. |
| `sanctions-diplomatic-pressure` | 268 | 0.651 | 81.3% | Medium-good. Sanctions/embassy/negotiation evidence mostly fits, but broad diplomacy rows leak. |

## Evidence Review By Topic

### Strong Enough For UI After Minor Copy/Ranking Work

- `heat-health-risk`: heatwave evidence is direct and lex-supported.
- `mining-royalty-risk`: evidence is coherent, but label should be changed or
  split into mining/resource disaster risk.
- `food-price-stress`: representative detail endpoint evidence is strong, but
  random sample shows theme-only leakage. Needs a higher confidence/lex floor
  before it leads UI.
- `sanctions-diplomatic-pressure`: mostly coherent, but should down-rank broad
  `embassy` and `treaty` matches unless paired with sanctions/negotiations.

### Needs Tuning Before Main NarrativeThreads UI

- `armed-conflict-escalation`: good examples exist, but `lex_pct` is only 5.6%.
  It should separate war/armed conflict from generic security/protest.
- `disease-outbreak`: Ebola rows are good; generic medical/safety rows are not.
  This needs disease-specific evidence gates.
- `labor-strike-disruption`: the word `strike` is ambiguous. Needs phrase
  weighting or negative filters for oil/gas discovery, sports, and "credit
  union" usage.
- `election-legitimacy-dispute`: should distinguish actual public elections
  from sports/club elections and routine primaries.
- `water-stress-drought`: should distinguish drought/water stress from tourism
  dry-season content.
- `forced-displacement`: should separate emergency evacuation from migration
  displacement and war displacement.

### Not Ready For UI Promotion

- `gender-violence-rights`: `lex_pct` 0.2%; the current volume is mostly theme
  hints, not validated gender-rights evidence.
- `transport-corridor-disruption`: current `canal` term is too broad and
  creates entertainment/sports/TV false positives.

## Source Quality Findings

Aggregator and syndication dominance is still visible:

- `zazoom.it` appears as a top source across many threads.
- `indiatimes.com`, `yahoo.com`, `tvguide.co.uk`, and `rediff.com` appear in
  several top-source lists.
- This is not automatically "bad", but it should not be treated as independent
  corroboration. Source ranking needs a voice-lane model:
  - original/local reporting;
  - wire/syndication;
  - aggregator;
  - state media;
  - social/public attention;
  - humanitarian/NGO.

Current `source_count` overstates diversity because syndicated/aggregated copies
can inflate the number of distinct domains.

## Geography Findings

Thread geography is currently volume-ranked. That makes the United States,
India, and the United Kingdom dominate many topics even when the thread's more
meaningful geography may be elsewhere.

Examples:

- `armed-conflict-escalation` label says United States and Iran, while evidence
  examples are heavily Ukraine/Russia.
- `food-price-stress` and `migration-border-pressure` surface United States /
  United Kingdom / India because of publisher volume.
- Some country names are unresolved codes: `RB`, `RO`, `UG`, `BD`, etc.

Required correction:

- top geography for threads should use a heat-style adjusted ranking, not raw
  count alone;
- labels should avoid unresolved country codes;
- source geography and event geography should be separated where possible.

## Entity Findings

PR #211 adds `top_entities` from `signals_v2.persons`. This is useful only if
we are explicit about quality.

Finding:

- `El Niño` and `Pacific Ocean` can be meaningful in climate/water threads.
- They are not persons.
- `Jesus Christ` may be a valid named phrase in some contexts, but as a top
  entity for `gender-violence-rights` it is not reliable evidence of the
  narrative.

Recommendation:

- Do not expose `top_entities` as a frontend person row.
- Rename or reshape the field to typed entities before UI use.
- At minimum split:
  - `top_people`;
  - `top_places`;
  - `top_orgs`;
  - `top_other_entities`;
  - `entity_quality_flags`.

## Conceptual Correction

Replace this interpretation:

> Living Threads are a new product surface beside Narrative Threads.

With this:

> Narrative Threads are the product surface. They are live because Atlas keeps
> ingesting and reprocessing signals. `/api/v2/threads` is the improved data
> contract that should eventually feed the existing NarrativeThreads component.

This matters because the next work should not create new panels. It should make
the existing panels more truthful.

## Quality Gates Before Frontend Swap

Do not swap `NarrativeThreads.tsx` to `/api/v2/threads` until these gates pass:

1. **Thread sample precision:** at least 80% relevant in a random 10-row sample
   for every top-10 thread shown in the UI.
2. **Evidence precision:** at least 6 of 8 detail evidence samples are directly
   supportive of the thread label.
3. **Lex support or typed reason:** if `lex_pct < 20%`, the thread must carry a
   visible method flag or be down-ranked.
4. **No unresolved geography in labels:** labels cannot say `RB`, `RO`, `UG`,
   etc. unless those are resolved to user-readable names.
5. **No untyped entity chips:** entity chips must not imply "people" unless they
   are typed as people.
6. **Source diversity adjusted:** top sources should not be ranked by raw domain
   count alone when aggregator/syndication dominance is detected.

## Recommended Next Work

1. **Patch PR #211 before merge.**
   - Keep `parent_domain`, `first_seen`, `hourly_timeline`, and `trend`.
   - Hold or rename `top_entities`.
   - Add quality flags: `lex_pct`, `method_mix`, `source_quality_flags`,
     `geo_quality_flags`.
   - Do not claim frontend readiness yet.

2. **Fix two high-noise topics first.**
   - `transport-corridor-disruption`: remove or qualify `canal`.
   - `gender-violence-rights`: require gender-specific lex evidence or split
     generic violent crime from gender-rights narratives.

3. **Add thread-quality report script.**
   - Output per topic: volume, lex_pct, high_conf count, random sample,
     evidence sample, top sources, country-code quality, and quality grade.
   - Save snapshots under `docs/research/thread-quality/`.

4. **Resume data quality roadmap before UI swap.**
   - Path C taxonomy revision for split/rename decisions.
   - Entity typing/NER hygiene.
   - Source voice lanes and aggregator penalty.
   - Geography ranking based on adjusted attention, not only volume.

## Decision

Keep #209/#210. They are useful and not currently disrupting the visible
NarrativeThreads UI.

Do not merge #211 as-is. Convert it into a quality-enriched backend PR, then
run this audit again before M3b frontend work.
