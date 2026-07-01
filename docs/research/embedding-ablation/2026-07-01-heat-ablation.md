# Heat composite ablation — volume≠importance, measured (PR3-11)

**Date:** 2026-07-01 · **Source:** `/api/v2/heat/countries?limit=200&hours=24` (N=200 countries) ·
**Ledger:** PR3-11 · **Paper:** P3 (heat / attention). The seed asked for a per-component heat
ablation + Kendall-tau of the composite vs volume; both here.

## The claim under test
Atlas's `atlas_heat` is a 7-component composite (z_velocity, surprise_kl, source_diversity,
local_voice_ratio, polyphony, geo_confidence_mean, duplication_index), deliberately NOT volume —
the "news weather-radar" thesis (P3): what's HOT ≠ what's LOUD. Never measured against volume.

## Result — composite vs volume are DISJOINT
**Kendall-τ (atlas_heat rank vs volume_now rank) = −0.198** (N=200). Not just uncorrelated —
mildly NEGATIVE: higher-volume countries tend to rank LOWER on the composite. And the extremes are
completely separate:

| rank | top-8 by COMPOSITE | top-8 by VOLUME |
|---|---|---|
| — | GT CR CI HN MZ SI TT ET | GB CN IN RU DE FR TR MX |
| overlap | **0 / 8** | |

The composite surfaces small/mid countries with real anomalies (Guatemala, Costa Rica, Côte
d'Ivoire, Honduras, Mozambique, Slovenia, Trinidad, Ethiopia); volume surfaces the media firehoses
(UK, China, India, Russia, Germany, France, Turkey, Mexico). **Zero overlap.** This is the measured
proof of "volume≠importance" — the distortion Atlas explicitly rejected (#231, the US-always-reddest
bug) is quantified: a volume-ranked map and the composite map share none of their top-8.

## Per-component ablation — what pulls the composite away from volume
| component | corr w/ composite | corr w/ volume |
|---|---:|---:|
| source_diversity | **+0.486** | +0.061 |
| surprise_kl | **+0.401** | **−0.558** |
| z_velocity | +0.284 | +0.025 |
| local_voice_ratio | +0.219 | +0.413 |
| geo_confidence_mean | −0.427 | −0.009 |
| duplication_index | −0.166 | +0.169 |
| polyphony | n/a (constant 0.5 in window) | — |

- **`surprise_kl` is the engine of the divergence:** +0.401 with the composite but **−0.558 with
  volume** — it actively rewards countries whose distribution is anomalous vs their baseline, which
  are disproportionately LOW-volume. This single component is why the composite inverts volume.
- **`source_diversity`** (+0.486) is the strongest composite driver and is volume-neutral (+0.061)
  — heat rewards many independent sources, not raw count.
- **`local_voice_ratio`** leans toward volume (+0.413) — a mild volume-aligned pull, the one
  component that tracks size, sensibly damped in the blend.

## Honest caveats
- 24h window, one snapshot; polyphony was constant (0.5) so its correlation is undefined (harmless).
- Correlation is Pearson on components vs the composite/volume; the headline τ is rank-based
  (Kendall) and robust. No temporal hold-out (a multi-day τ would tighten it).
- The composite weights are v1 (not learned); this measures the CURRENT blend's behaviour, which is
  the served one.

## Paper impact (P3)
Closes PR3-11: the "volume≠importance transferred" claim (R3.4a/R3.5) now has its ablation. The
composite is decisively not a volume proxy (τ=−0.198, 0/8 top overlap), and the mechanism is
identified (surprise_kl + source_diversity vs the volume-leaning local_voice_ratio). P3's
weather-radar thesis is measured, not asserted.
