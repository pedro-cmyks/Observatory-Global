# Atlas Heat — Composite Country Score

**Status:** v1 — issue [#165](https://github.com/pedro-cmyks/Observatory-Global/issues/165)
**Replaces:** raw `volume DESC` ranking in country heat surfaces
**Depends on:** signal_class semantics (#155), Voice Mix endpoint (#160), multilingual NLP (#162)

---

## Why

Atlas's prior heat ranking sorted countries by absolute signal volume in the time window. The result: the United States is always near the top, regardless of whether the day brought meaningful narrative change. Burkina Faso, Eritrea, Laos, or Bhutan rarely surface even when their narrative environment is in motion, because their absolute volume is dwarfed by routine US/UK syndication.

Atlas Heat is a transparent multi-factor score that prevents loud routine coverage from drowning narrative anomalies. Each component answers a specific product question:

| Component | Question |
|-----------|----------|
| `z_velocity` | Is this country's coverage unusual *for itself* right now? |
| `surprise_kl` | Is the country covering themes that diverge from the global mix? |
| `source_diversity` | Is the coverage broad or coming from one voice? |
| `local_voice_ratio` | Is the story being told from inside the country or from outside? |
| `polyphony` | Is there narrative debate or a single dominant frame? |
| `geo_confidence_mean` | How sure are we the signals are about this country? |
| `duplication_index` | How much of the volume is syndicated copies of the same story? |

The composite is exposed alongside the breakdown so users can always answer "why is this country hot right now?" by inspecting the components, not by trusting a black box.

---

## Formula

For a `(country, hours_window)` pair:

```
atlas_heat =
    0.25 * z_velocity_norm
  + 0.20 * surprise_kl_norm
  + 0.15 * source_diversity_norm
  + 0.15 * local_voice_ratio
  + 0.10 * polyphony_norm
  + 0.10 * geo_confidence_mean
  - 0.05 * duplication_index_norm
```

Each component is normalised to `[0, 1]` so the composite is bounded `[~-0.05, ~1.0]` and dimensionless.

### Component definitions

#### z_velocity

```
volume_now      = COUNT(signals_v2 in last `hours_window` for country)
volume_baseline = AVG(daily_count) over last 14 days, same country
volume_sigma    = STDDEV_POP(daily_count) over last 14 days
z_velocity_raw  = (volume_now / (hours_window/24) - volume_baseline) / volume_sigma
z_velocity_norm = SIGMOID(z_velocity_raw / 3)   -- 3σ maps to ~0.95
```

A z-score of +3 (volume 3 standard deviations above the country's own baseline) maps to near 1. Countries with no historical baseline (new country code, less than 7 days of data) get `z_velocity_norm = 0.5` (neutral) until baseline matures.

#### surprise_kl

Kullback-Leibler divergence between the country's theme distribution and the global theme distribution in the same window.

```
p_country[t] = share of country's signals with theme t
p_global[t]  = share of all global signals with theme t
KL           = SUM(p_country[t] * LOG(p_country[t] / p_global[t]))   -- over t where p_country > 0
surprise_kl_norm = MIN(1.0, KL / 2.0)   -- KL≥2 saturates
```

Captures "this country is covering off-baseline themes" without needing manual baselines.

#### source_diversity

Shannon entropy of `source_family` distribution for the country in the window.

```
H = -SUM(p_family * LOG(p_family))                                   -- over 5+ families
H_max = LOG(distinct_family_count)
source_diversity_norm = H / H_max IF H_max > 0 ELSE 0
```

`1.0` means perfect spread across all source families present; `0.0` means a single family dominates. The reference set: `wire`, `independent`, `state`, `ngo`, `social`, `api`.

#### local_voice_ratio

```
local_voice_ratio = COUNT(signals with source_origin_country = country)
                  / COUNT(signals where source_origin_country IS NOT NULL)
```

Already computed by migration 012 (`source_origin_country` populated from 70+ known domains + ccTLD fallback). When fewer than 50 known-origin signals exist, return `0.5` (neutral) and surface a thin-coverage badge upstream — same convention as `foreignSourcePct` in `CountryBrief`.

#### polyphony

Entropy of `nlp_framing` labels within the country window.

```
p_frame[f] = share of country's signals with nlp_framing = f
H = -SUM(p_frame * LOG(p_frame))
H_max = LOG(6)   -- six v1 frame labels
polyphony_norm = H / H_max
```

Low polyphony = single dominant frame (echo chamber or consigna). High polyphony = multiple narratives competing.

Skipped (set to `0.5`) when fewer than 25 framed signals exist — framing entropy on tiny samples is noise, not signal.

#### geo_confidence_mean

```
geo_confidence_mean = AVG(geo_confidence) over country's signals in window
```

Already populated by ADR-0003 Phase 4 logic. Range `[0, 1]` natively.

#### duplication_index

MinHash-driven measure of how much of the country's coverage is duplicated syndication. v1 approximation: ratio of *non-unique* canonical-title shingles to total signals.

```
dup_ratio = 1 - (DISTINCT canonical_title_hash) / signals_in_window
duplication_index_norm = MIN(1.0, dup_ratio)
```

Subtracted from the composite because high duplication inflates volume without adding narrative information. Subtracted, not zeroed — heavily syndicated stories still represent attention.

---

## Worked examples

### Example A — United States, last 24h (routine high-volume day)

Hypothetical numbers:

- `volume_now = 8200`, baseline `8000 ± 600` → `z_velocity_raw ≈ 0.33` → `z_velocity_norm ≈ 0.54`
- Themes spread evenly across politics/economy/health → `surprise_kl ≈ 0.4` → `0.20`
- Source families: `wire` 60%, `independent` 25%, `social` 10%, others 5% → `H/H_max ≈ 0.62`
- `local_voice_ratio = 0.71` (most coverage US-origin)
- Framing entropy across 6 labels: `polyphony_norm ≈ 0.65`
- `geo_confidence_mean = 0.93`
- `duplication_index = 0.4` (heavy AP/Reuters syndication)

```
atlas_heat ≈ 0.25*0.54 + 0.20*0.20 + 0.15*0.62 + 0.15*0.71
           + 0.10*0.65 + 0.10*0.93 - 0.05*0.4
        ≈ 0.135 + 0.04 + 0.093 + 0.107 + 0.065 + 0.093 - 0.020
        ≈ 0.513
```

Routine high-volume day. Above neutral, below alarming. Atlas Heat ≈ **0.51**.

### Example B — Burkina Faso, last 24h (anomaly day)

Hypothetical numbers:

- `volume_now = 180`, baseline `35 ± 12` → `z_velocity_raw ≈ 12.1` → `z_velocity_norm ≈ 0.98`
- Themes concentrated on conflict + humanitarian + foreign-policy (unusual mix vs global) → `surprise_kl ≈ 1.8` → `0.90`
- Source families: `wire` 70%, `ngo` 20%, `independent` 10% → `H/H_max ≈ 0.45`
- `local_voice_ratio = 0.12` (mostly external wires)
- Framing entropy: 60% conflict_escalation, 30% humanitarian_crisis, 10% diplomatic → `polyphony_norm ≈ 0.50`
- `geo_confidence_mean = 0.87`
- `duplication_index = 0.55` (same story repeated by international wires)

```
atlas_heat ≈ 0.25*0.98 + 0.20*0.90 + 0.15*0.45 + 0.15*0.12
           + 0.10*0.50 + 0.10*0.87 - 0.05*0.55
        ≈ 0.245 + 0.180 + 0.068 + 0.018 + 0.050 + 0.087 - 0.028
        ≈ 0.620
```

Atlas Heat ≈ **0.62**. Higher than US's routine day, lower than it would be with diverse local voice. The breakdown surfaces the warning: `local_voice_ratio = 0.12` flags that the story is told from outside, and `source_diversity = 0.45` flags wire dominance. Users see *both* the rank and the texture.

---

## Implementation

### SQL CTE outline (one heat refresh per `hours_window`)

```sql
WITH country_window AS (
    SELECT
        country_code,
        COUNT(*) AS volume_now,
        AVG(geo_confidence) AS geo_confidence_mean
    FROM signals_v2
    WHERE timestamp > NOW() - ($1 || ' hours')::INTERVAL
      AND country_code IS NOT NULL
    GROUP BY country_code
),
country_baseline AS (
    SELECT
        country_code,
        AVG(daily_n) AS volume_baseline_daily,
        STDDEV_POP(daily_n) AS volume_sigma_daily
    FROM (
        SELECT country_code, date_trunc('day', timestamp) AS day, COUNT(*) AS daily_n
        FROM signals_v2
        WHERE timestamp BETWEEN NOW() - INTERVAL '14 days' AND NOW() - INTERVAL '1 day'
          AND country_code IS NOT NULL
        GROUP BY 1, 2
    ) d
    GROUP BY 1
),
country_themes AS ( ... ),       -- p_country[t] vs p_global[t] for surprise_kl
country_diversity AS ( ... ),    -- Shannon entropy of source_family
country_voice AS ( ... ),        -- local_voice_ratio
country_polyphony AS ( ... ),    -- nlp_framing entropy
country_dup AS ( ... )           -- duplication_index from canonical_title_hash
SELECT
    c.country_code,
    /* normalised components and composite */
FROM country_window c
LEFT JOIN country_baseline   USING (country_code)
LEFT JOIN country_themes     USING (country_code)
LEFT JOIN country_diversity  USING (country_code)
LEFT JOIN country_voice      USING (country_code)
LEFT JOIN country_polyphony  USING (country_code)
LEFT JOIN country_dup        USING (country_code);
```

Materialised view `country_heat_v2(country_code, hours_window, atlas_heat, z_velocity_norm, …, refreshed_at)` is refreshed every 5 minutes by the aggregator. API serves directly from the view — no per-request recompute.

### Endpoint

```
GET /api/v2/heat/countries?hours=24

200 OK
{
  "hours": 24,
  "items": [
    {
      "country_code": "BF",
      "atlas_heat": 0.62,
      "components": {
        "z_velocity": 0.98,
        "surprise_kl": 0.90,
        "source_diversity": 0.45,
        "local_voice_ratio": 0.12,
        "polyphony": 0.50,
        "geo_confidence_mean": 0.87,
        "duplication_index": 0.55
      },
      "volume_now": 180,
      "volume_baseline_daily": 35,
      "warnings": ["external_coverage", "wire_dominance"]
    },
    …
  ],
  "refreshed_at": "2026-05-18T15:32:11Z"
}
```

`warnings` are computed flags surfaced to the UI:

- `external_coverage` when `local_voice_ratio < 0.2`
- `wire_dominance` when one source_family > 60%
- `thin_coverage` when `volume_now < 50` and `geo_confidence_mean < 0.7`
- `echo_chamber` when `polyphony < 0.3` and `volume_now > 100`

### Frontend integration

`CountryHeatList` consumes the composite as rank and displays component values in a tooltip. The composite is the single ranking signal; the breakdown is always accessible. No black-box scores.

---

## What this does NOT do

- Does not change other Atlas views beyond country heat ranking. Theme heat, narrative threads, briefings, and reading mode keep their existing logic until they explicitly migrate.
- Does not provide cross-component normalisation tuning. The weights (`0.25, 0.20, …`) are first-pass defaults; expected to evolve based on user feedback and offline backtests.
- Does not handle correlation between components (e.g. surprise_kl and z_velocity often co-move). Future revision can add a covariance correction; v1 prioritises explainability.
- Does not score themes the same way. Theme-level heat is a separate problem covered later under issue #70.
