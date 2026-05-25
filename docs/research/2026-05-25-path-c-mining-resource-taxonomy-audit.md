# Path C Taxonomy Audit: Mining / Resource Risk

Date: 2026-05-25  
Issue: https://github.com/pedro-cmyks/Observatory-Global/issues/204  
Contract observed: `living-narrative-threads-v0`

## Question

Does `mining-royalty-risk` still describe the evidence that Atlas is surfacing,
or did Path A reveal a better living-thread anchor?

## Live Thread Snapshot

Source endpoint:

```text
GET https://atlas-api-pedro.fly.dev/api/v2/threads?hours=24&limit=50
GET https://atlas-api-pedro.fly.dev/api/v2/threads/mining-royalty-risk--cn-au-ca?hours=24
```

Observed thread:

| Field | Value |
|---|---:|
| `thread_id` | `mining-royalty-risk--cn-au-ca` |
| visible label | Mining royalty and resource risk intensifies in China and Australia |
| signal_count | 203-218, depending on cache minute |
| source_count | 191-202 |
| country_count | 3-15 across list/detail cache windows |
| avg_confidence | 0.77-0.78 |
| lex_pct | 90.83%-96.06% |
| changed_10h | +13 to +14 |
| confidence band | high |

Representative evidence from the detail endpoint:

1. Authorities investigate safety lapses after China coal mine blast kills at
   least 82.
2. Lee offers condolences over deadly China coal mine explosion.
3. Authorities investigate after China coal mine explosion kills at least 82.
4. South Korea's President condoles coal mine explosion in China.
5. China Coal Mine Explosion Leaves 90 Dead, Rescue Operations Underway.
6. China Coal Mine Explosion Death Toll Revised to 82 in Shanxi.

## Finding

The cluster is real and high-confidence, but the current anchor label is wrong.
This is not primarily a royalty, concession, or resource-nationalism thread. It
is a mining safety / resource disaster thread, currently centered on a major
China coal mine explosion and its diplomatic/media afterlife.

The Path A migration did its job: multilingual lexicon expansion exposed a real
cluster. Path C should now correct the internal anchor and visible label.

## Decision Recommendation

Keep the existing slug for compatibility in the first migration, but change the
human-facing anchor fields:

- label: `Mining and resource safety crisis`
- description: `Mine accidents, extraction-site safety failures, illegal mining,
  resource-disaster events, and related regulatory or accountability fallout.`

Then treat royalty/concession/resource nationalism as a subthread candidate,
not as the primary label.

Do **not** create a separate new slug yet. The live volume is dominated by one
mine-disaster cluster, and the existing classifier key is already wired through
hot-window assignments, `/api/v2/threads`, `/api/v2/briefing`, and historical
aggregates. A rename-only first step reduces product mismatch without creating a
parallel topic split before benchmark labels exist.

## Migration Shape

Preferred first migration:

```sql
UPDATE atlas_topics
SET
  label = 'Mining and resource safety crisis',
  description = 'Mine accidents, extraction-site safety failures, illegal mining, resource-disaster events, and related regulatory or accountability fallout.',
  updated_at = NOW()
WHERE slug = 'mining-royalty-risk';
```

Leave `lexicon_terms` intact for now. The current terms are pulling coherent
mine-disaster evidence. Removing royalty/concession terms should wait until a
spot check shows whether there is still meaningful royalty/concession evidence
inside the same anchor.

## Secondary Findings For Later Path C

The same live top-20 thread pull showed additional quality concerns, but they
should not expand this first PR:

| Thread | Signal |
|---|---|
| `disease-outbreak--us-gb-in` | Very high volume but low lex_pct around 10.7%; likely theme-heavy noise mixed with true disease evidence. |
| `labor-strike-disruption--us-in-gb` | Top entities include golf/player names, consistent with `strike` ambiguity. |
| `food-price-stress--gb-in-us` | Low lex_pct around 4.6%; still theme-heavy after Path A cleanup. |

These belong in follow-up Path C or Path B benchmark work after the mining label
correction.

## Gate

Before applying a broader split:

1. Pull at least 25 unique evidence headlines for the current anchor.
2. Classify each as `mine_disaster`, `royalty_concession`, `illegal_mining`,
   `resource_nationalism`, or `noise`.
3. If one non-disaster class reaches meaningful independent volume, create a new
   topic or subthread proposal.
4. If disaster remains dominant, keep the broader label and build subthread
   detection later.
