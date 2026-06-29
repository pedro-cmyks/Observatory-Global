# Embedding-input ablation (spec §4B.3)

Sample: 1039 deduped rows · NER coverage 69.1% · gaza probe 448 · vegas(deduped) 131

| variant | clusters | noise | cohesion | geo_purity | gaza_recall | gaza_noise |
|---|---|---|---|---|---|---|
| A_title | 24 | 0.769 | 0.968 | 0.592 | 0.067 | 0.719 |
| B_title_entities | 26 | 0.801 | 0.967 | 0.583 | 0.074 | 0.688 |
| C_title_entities_country | 22 | 0.786 | 0.97 | 0.642 | 0.087 | 0.674 |

## Decision rule (§4B.3)
- **Win** = B (or C) raises `gaza_recall` (diverse coverage pulled together) AND lowers `gaza_noise`, WITHOUT C's `geo_purity` jumping vs A/B (geographic over-clustering).
- If B helps and C over-clusters → enrich with entities only, drop country.
- If neither beats A → headline-only stays; do NOT run the full re-embed.
- Reminder: this measures RECALL of diverse coverage only. The Las Vegas syndication problem is a ranking-count issue (spec §4), not here.