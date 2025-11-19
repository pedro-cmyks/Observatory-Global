# Visualization Architecture Specification

**Issue:** #15 - Dual-Layer Visualization Architecture
**Status:** Design Complete
**Version:** 1.0
**Last Updated:** 2025-01-18
**Author:** NarrativeGeopoliticsAnalyst + Frontend Architect

---

## Executive Summary

This document specifies the technical architecture for Observatory Global's dual-layer visualization system. The system renders both Classic (flow lines) and Heatmap (H3 hexagons) layers simultaneously, creating a "weather radar of global information" that enables users to understand narrative propagation patterns in real-time.

---

## Table of Contents

1. [Layer Stack Specification](#layer-stack-specification)
2. [Tooltip System Design](#tooltip-system-design)
3. [Animation Specifications](#animation-specifications)
4. [Narrative Intelligence Integration](#narrative-intelligence-integration)
5. [API Response Schema](#api-response-schema)
6. [User Interaction Flows](#user-interaction-flows)
7. [Performance Optimization](#performance-optimization)
8. [Implementation Roadmap](#implementation-roadmap)

---

## Layer Stack Specification

### Z-Index Ordering

The visualization uses a layered approach where each visual element occupies a specific z-index level. Layers are rendered from bottom to top:

```
+---------------------------------------------+
| Layer 5: Labels & UI Overlays    (z: 1000)  |
+---------------------------------------------+
| Layer 4: Country Centroids       (z: 800)   |
+---------------------------------------------+
| Layer 3: Flow Lines (Particles)  (z: 600)   |
+---------------------------------------------+
| Layer 2: Heatmap (H3 Hexagons)   (z: 400)   |
+---------------------------------------------+
| Layer 1: Mapbox Base Map         (z: 0)     |
+---------------------------------------------+
```

### Detailed Layer Specifications

#### Layer 1: Mapbox Base Map
- **Style:** `mapbox://styles/mapbox/dark-v11`
- **Purpose:** Provides geographic context without visual competition
- **Z-Index:** 0 (default Mapbox)
- **Interactivity:** Pan, zoom, rotate

#### Layer 2: Heatmap (H3 Hexagons)
- **Technology:** deck.gl `H3HexagonLayer`
- **Z-Index:** 400
- **Resolution:** H3 resolution 2-4 (adaptive based on zoom)
- **Smoothing:** K-ring blur with k=2

**Opacity Settings:**
```typescript
const heatmapOpacity = {
  base: 0.6,              // Default opacity
  hovered: 0.85,          // When hex is hovered
  selected: 0.95,         // When hex is selected
  dimmed: 0.3,            // When other layers active
}
```

**Blend Mode:**
```css
mix-blend-mode: screen;  /* Allows underlying map to show through */
```

**Color Gradient (Sentiment-Based):**
```typescript
const sentimentColorScale = [
  { value: -1.0, color: [239, 68, 68, 255] },   // Red: Very negative
  { value: -0.5, color: [251, 146, 60, 255] },  // Orange: Moderately negative
  { value: 0.0, color: [250, 204, 21, 255] },   // Yellow: Neutral
  { value: 0.5, color: [163, 230, 53, 255] },   // Lime: Moderately positive
  { value: 1.0, color: [34, 197, 94, 255] },    // Green: Very positive
]
```

#### Layer 3: Flow Lines
- **Technology:** Mapbox GL `line` layer + deck.gl `TripsLayer` for particles
- **Z-Index:** 600
- **Purpose:** Show narrative propagation paths between countries

**Line Styling:**
```typescript
const flowLineStyle = {
  'line-color': [
    'interpolate', ['linear'], ['get', 'heat'],
    0.0, '#3B82F6',  // Cool blue
    0.5, '#FCD34D',  // Warm yellow
    1.0, '#EF4444',  // Hot red
  ],
  'line-width': [
    'interpolate', ['linear'], ['get', 'heat'],
    0.0, 1,
    1.0, 4,
  ],
  'line-opacity': [
    'interpolate', ['linear'], ['get', 'heat'],
    0.0, 0.3,
    1.0, 0.8,
  ],
}
```

#### Layer 4: Country Centroids
- **Technology:** React Map GL `Marker` + Framer Motion
- **Z-Index:** 800
- **Purpose:** Represent country-level aggregations as interactive nodes

**Size Calculation:**
```typescript
const centroidSize = (topicCount: number): number => {
  const minSize = 20   // px
  const maxSize = 60   // px
  const minCount = 0
  const maxCount = 300

  const normalized = Math.min(Math.max(
    (topicCount - minCount) / (maxCount - minCount), 0
  ), 1)

  return minSize + normalized * (maxSize - minSize)
}
```

#### Layer 5: Labels & UI Overlays
- **Technology:** HTML/CSS positioned overlays
- **Z-Index:** 1000
- **Components:** Tooltips, control panels, sidebars

### Dual-Layer Simultaneous Rendering

When both Classic and Heatmap views are active simultaneously:

```typescript
const simultaneousLayerConfig = {
  heatmap: {
    opacity: 0.5,              // Reduced for visibility
    blurRadius: 8,             // Subtle blur effect
    saturation: 0.7,           // Slightly desaturated
  },
  flows: {
    opacity: 0.9,              // High visibility
    particleDensity: 0.5,      // Reduced particle count
    lineWidth: 0.8,            // Slightly thinner
  },
  centroids: {
    opacity: 1.0,              // Full visibility
    scale: 0.9,                // Slightly smaller
  },
}
```

---

## Tooltip System Design

### "Why Is This Heating Up?" Tooltip

The tooltip provides progressive disclosure of narrative intelligence, helping users understand the forces driving information activity in any region.

### Data Fields Structure

```typescript
interface NarrativeTooltipData {
  // Core Identification
  location: {
    country_code: string           // ISO 3166-1 alpha-2
    country_name: string           // Human-readable name
    region: string                 // Geographic region
    coordinates: [number, number]  // [lng, lat]
  }

  // Intensity Metrics
  intensity: {
    score: number                  // 0.0 to 1.0
    percentile: number             // Compared to global average
    trend: 'rising' | 'stable' | 'falling'
    change_24h: number             // Percentage change
  }

  // Thematic Analysis
  themes: {
    top_themes: Array<{
      code: string                 // GDELT theme code
      label: string                // Human-readable label
      count: number                // Article count
      sentiment: number            // -1.0 to 1.0
    }>
    theme_diversity: number        // 0.0 to 1.0 (Shannon entropy)
  }

  // Sentiment Analysis
  sentiment: {
    average: number                // -1.0 to 1.0
    variance: number               // 0.0 to 1.0
    dominant_emotion: string       // e.g., "anger", "fear", "hope"
    polarity: number               // 0.0 to 1.0
  }

  // Actor Analysis
  actors: {
    persons: Array<{
      name: string
      mention_count: number
      sentiment: number
    }>
    organizations: Array<{
      name: string
      mention_count: number
      sentiment: number
    }>
  }

  // Source Attribution
  outlets: {
    top_outlets: Array<{
      name: string
      article_count: number
      avg_sentiment: number
    }>
    source_diversity: number       // 0.0 to 1.0
    state_media_ratio: number      // Proportion from state media
  }

  // Narrative Intelligence
  narrative: {
    drift_score: number            // 0.0 to 1.0 (divergence from global)
    stance: 'supportive' | 'critical' | 'neutral' | 'mixed'
    cluster_id: string             // Narrative cluster membership
    cluster_label: string          // Human-readable cluster name
  }

  // Temporal Context
  temporal: {
    first_signal: string           // ISO timestamp
    peak_activity: string          // ISO timestamp
    recency_score: number          // 0.0 to 1.0
  }

  // Sample Content
  sample_headlines: Array<{
    title: string
    url: string
    outlet: string
    timestamp: string
  }>
}
```

### Progressive Disclosure Levels

The tooltip implements three levels of detail:

#### Level 1: Summary (Default Hover)

Appears after 200ms hover delay. Displays essential information at a glance.

```
+------------------------------------------+
|  US - United States              Rising  |
|  ========================================|
|  Intensity: 87%  |  Sentiment: -0.35     |
|  ----------------------------------------|
|  Top Themes:                             |
|  - Economic Inflation (23)               |
|  - Labor Protests (15)                   |
|  ----------------------------------------|
|  Click for details                       |
+------------------------------------------+
```

**Plain Language Explanation:**
```typescript
const summaryExplanation = (data: NarrativeTooltipData): string => {
  const intensity = data.intensity.percentile > 75 ? 'unusually high' :
                    data.intensity.percentile > 50 ? 'moderate' : 'low'
  const sentiment = data.sentiment.average < -0.3 ? 'predominantly negative' :
                    data.sentiment.average > 0.3 ? 'predominantly positive' : 'mixed'
  const trend = data.intensity.trend === 'rising' ? 'increasing' :
                data.intensity.trend === 'falling' ? 'decreasing' : 'stable'

  return `${data.location.country_name} is showing ${intensity} information ` +
         `activity with ${sentiment} coverage. Activity is ${trend}.`
}
```

#### Level 2: Detailed (Click to Expand)

Full analysis panel with tabs for different aspects.

```
+--------------------------------------------------+
|  US - United States                    [X Close] |
|  ================================================|
|  [Themes] [Actors] [Sources] [Timeline]          |
|  ------------------------------------------------|
|  THEMES TAB:                                     |
|                                                  |
|  Top Active Themes (24h)                         |
|  ------------------------------------------------|
|  Economic Inflation    ████████████  23 signals  |
|    Sentiment: -0.42    Trend: Rising             |
|                                                  |
|  Labor Protests        ████████      15 signals  |
|    Sentiment: -0.28    Trend: Stable             |
|                                                  |
|  Federal Reserve       ██████        11 signals  |
|    Sentiment: -0.15    Trend: Rising             |
|                                                  |
|  ------------------------------------------------|
|  Theme Diversity: 0.72 (High)                    |
|  This indicates multiple competing narratives    |
|  ------------------------------------------------|
|                                                  |
|  KEY ACTORS:                                     |
|  - Jerome Powell (Fed Chair) - 18 mentions       |
|  - Janet Yellen (Treasury) - 12 mentions         |
|                                                  |
|  DRIVING OUTLETS:                                |
|  - Bloomberg (28%)                               |
|  - Reuters (22%)                                 |
|  - WSJ (18%)                                     |
|                                                  |
|  ------------------------------------------------|
|  Sample Headlines:                               |
|  > Fed Maintains High Interest Rates...          |
|  > Labor Unions Rally Against Economic...        |
+--------------------------------------------------+
```

#### Level 3: Deep Dive (Full Screen Modal)

Accessed via "Analyze Narrative" button. Opens comprehensive analysis view.

```
+------------------------------------------------------------+
|  NARRATIVE ANALYSIS: United States                    [X]   |
|  ===========================================================|
|                                                              |
|  EXECUTIVE SUMMARY                                           |
|  ------------------------------------------------------------|
|  The United States is experiencing elevated information      |
|  activity centered on economic policy. Coverage is           |
|  predominantly negative (sentiment: -0.35) with anger as     |
|  the dominant emotional tone.                                |
|                                                              |
|  Key Finding: Narrative drift score of 0.68 indicates this   |
|  coverage diverges significantly from global framing of      |
|  similar topics.                                             |
|                                                              |
|  ===========================================================|
|                                                              |
|  [Visualization: Sentiment Timeline]                         |
|  [Visualization: Actor Network Graph]                        |
|  [Visualization: Source Distribution]                        |
|  [Table: All Active Themes]                                  |
|                                                              |
+------------------------------------------------------------+
```

### Non-Expert Plain Language Explanations

Each metric includes a plain language explanation:

| Metric | Technical | Plain Language |
|--------|-----------|----------------|
| Intensity 0.87 | 87th percentile activity | "This area has more news activity than 87% of other regions right now" |
| Sentiment -0.35 | Negative tone | "The overall tone of coverage is moderately negative" |
| Drift Score 0.68 | High narrative divergence | "This region's coverage differs significantly from how other regions are reporting the same topics" |
| Theme Diversity 0.72 | High entropy | "Multiple different narratives are competing for attention" |
| Polarity 0.65 | High variance | "Opinions are strongly divided - some very positive, some very negative" |

---

## Animation Specifications

### Pulsing Centroids (Breathing Effect)

Country centroid nodes pulse to indicate activity level and recency.

**Formula:**
```typescript
const breathingAnimation = (
  baseSize: number,
  intensity: number,
  recency: number,
  time: number
): number => {
  // Breathing amplitude scales with intensity
  const amplitude = 0.1 + (intensity * 0.15)  // 10-25% size variation

  // Breathing speed increases with recency
  const frequency = 0.5 + (recency * 1.5)  // 0.5-2.0 Hz

  // Sinusoidal breathing with easing
  const breath = Math.sin(time * frequency * Math.PI * 2) * 0.5 + 0.5
  const eased = breath * breath * (3 - 2 * breath)  // Smoothstep

  return baseSize * (1 + eased * amplitude)
}
```

**Implementation (Framer Motion):**
```typescript
const centroidAnimation = {
  initial: { scale: 0, opacity: 0 },
  animate: {
    scale: [1, 1.15, 1],
    opacity: [0.8, 1, 0.8],
  },
  transition: {
    duration: 2,
    repeat: Infinity,
    ease: 'easeInOut',
    times: [0, 0.5, 1],
  },
}
```

### Flow Line Particles

Animated particles travel along flow lines to show narrative propagation direction.

**Configuration:**
```typescript
interface FlowParticleConfig {
  speed: number           // Units per second (default: 50)
  density: number         // Particles per 1000km (default: 3)
  size: number            // Particle radius in pixels (default: 3)
  trailLength: number     // Trail length as fraction of path (default: 0.1)
  color: string           // Particle color (default: '#FFFFFF')
  opacity: number         // Particle opacity (default: 0.8)
}
```

**deck.gl TripsLayer Implementation:**
```typescript
const flowParticleLayer = new TripsLayer({
  id: 'flow-particles',
  data: flowPaths,
  getPath: d => d.path,
  getTimestamps: d => d.timestamps,
  getColor: d => {
    const heat = d.properties.heat
    return heat > 0.7 ? [255, 255, 255] :
           heat > 0.4 ? [252, 211, 77] :
                        [147, 197, 253]
  },
  getWidth: 3,
  opacity: 0.8,
  widthMinPixels: 2,
  rounded: true,
  trailLength: 0.1,
  currentTime: animationTime,
  shadowEnabled: false,
})
```

**Animation Loop:**
```typescript
const animateParticles = () => {
  const loopLength = 1800  // Loop duration in "time units"
  const animationSpeed = 30  // Time units per second

  const animate = (timestamp: number) => {
    const time = ((timestamp / 1000) * animationSpeed) % loopLength
    setAnimationTime(time)
    requestAnimationFrame(animate)
  }

  requestAnimationFrame(animate)
}
```

### Heatmap Gradient Transitions

Smooth color interpolation when data updates or sentiment changes.

**Color Interpolation (CIELAB Space):**
```typescript
import { interpolateLab } from 'd3-interpolate'

const interpolateHeatColor = (
  sentiment: number,  // -1.0 to 1.0
  intensity: number   // 0.0 to 1.0
): [number, number, number, number] => {
  // Color scale from red (negative) to green (positive)
  const sentimentColors = [
    '#EF4444',  // -1.0: Red
    '#FB923C',  // -0.5: Orange
    '#FACC15',  //  0.0: Yellow
    '#A3E635',  //  0.5: Lime
    '#22C55E',  //  1.0: Green
  ]

  // Normalize sentiment to 0-1 range
  const t = (sentiment + 1) / 2

  // Interpolate in CIELAB space for perceptual uniformity
  const colorIndex = t * (sentimentColors.length - 1)
  const lower = Math.floor(colorIndex)
  const upper = Math.ceil(colorIndex)
  const frac = colorIndex - lower

  const interpolator = interpolateLab(
    sentimentColors[lower],
    sentimentColors[upper]
  )

  const color = interpolator(frac)
  const rgb = hexToRgb(color)

  // Alpha based on intensity
  const alpha = Math.round(150 + intensity * 105)  // 150-255

  return [rgb.r, rgb.g, rgb.b, alpha]
}
```

**Transition Animation:**
```typescript
const heatmapTransition = {
  duration: 500,  // ms
  easing: 'ease-in-out',
  updateTriggers: {
    getFillColor: [sentimentData, intensityData],
  },
  transitions: {
    getFillColor: {
      duration: 500,
      easing: (t: number) => t * t * (3 - 2 * t),  // Smoothstep
    },
  },
}
```

### Temporal Glow (Recency Decay)

Recent activity appears brighter and gradually fades.

**Recency Score Calculation:**
```typescript
const calculateRecency = (
  signalTimestamp: Date,
  currentTime: Date,
  decayHalfLife: number = 3600000  // 1 hour in ms
): number => {
  const age = currentTime.getTime() - signalTimestamp.getTime()

  // Exponential decay
  const recency = Math.exp(-age * Math.LN2 / decayHalfLife)

  return Math.max(0, Math.min(1, recency))
}
```

**Glow Effect (CSS/Canvas):**
```typescript
const glowStyle = (recency: number) => ({
  filter: `drop-shadow(0 0 ${8 + recency * 12}px rgba(255, 255, 255, ${recency * 0.6}))`,
  opacity: 0.6 + recency * 0.4,
})
```

**deck.gl Implementation:**
```typescript
const getElevation = (d: HexCell): number => {
  // Elevation creates 3D "glow" effect
  return d.recency * 1000  // 0-1000m based on recency
}

const elevationScale = 20  // Exaggerate for visibility
```

---

## Narrative Intelligence Integration

### Drift Score Visual Mapping

Drift score indicates how much a region's framing diverges from the global consensus on a topic.

**Visual Indicators:**

| Drift Score | Interpretation | Visual Indicator |
|-------------|----------------|------------------|
| 0.0 - 0.3 | Low divergence | Standard hexagon fill |
| 0.3 - 0.6 | Moderate divergence | Patterned fill (diagonal stripes) |
| 0.6 - 0.8 | High divergence | Animated border pulse |
| 0.8 - 1.0 | Extreme divergence | Glowing outline + warning icon |

**Implementation:**
```typescript
const getDriftIndicator = (driftScore: number) => {
  if (driftScore < 0.3) {
    return {
      borderWidth: 0,
      pattern: null,
      glow: false,
    }
  } else if (driftScore < 0.6) {
    return {
      borderWidth: 1,
      pattern: 'diagonal',
      glow: false,
    }
  } else if (driftScore < 0.8) {
    return {
      borderWidth: 2,
      pattern: 'diagonal',
      glow: false,
      animation: 'pulse',
    }
  } else {
    return {
      borderWidth: 3,
      pattern: 'diagonal',
      glow: true,
      glowColor: '#FF6B6B',
      animation: 'pulse',
      showWarning: true,
    }
  }
}
```

### Sentiment to Color Gradient Mapping

```typescript
const SENTIMENT_COLOR_SCALE = {
  // Negative sentiment (concerns, criticism, fear)
  veryNegative: {
    range: [-1.0, -0.6],
    color: '#EF4444',  // Red
    label: 'Very Negative',
  },
  negative: {
    range: [-0.6, -0.2],
    color: '#FB923C',  // Orange
    label: 'Negative',
  },
  // Neutral sentiment
  neutral: {
    range: [-0.2, 0.2],
    color: '#FACC15',  // Yellow
    label: 'Neutral',
  },
  // Positive sentiment (optimism, support, hope)
  positive: {
    range: [0.2, 0.6],
    color: '#A3E635',  // Lime
    label: 'Positive',
  },
  veryPositive: {
    range: [0.6, 1.0],
    color: '#22C55E',  // Green
    label: 'Very Positive',
  },
}
```

### Stance Diversity Visual Cues

Stance diversity measures how varied the perspectives are on a topic within a region.

**Visual Representation:**

```typescript
interface StanceDiversityIndicator {
  diversity: number      // 0.0 to 1.0
  visual: 'solid' | 'gradient' | 'split'
  description: string
}

const getStanceDiversityVisual = (diversity: number): StanceDiversityIndicator => {
  if (diversity < 0.3) {
    // Uniform stance - single solid color
    return {
      diversity,
      visual: 'solid',
      description: 'Uniform perspective - most sources agree',
    }
  } else if (diversity < 0.7) {
    // Moderate diversity - gradient fill
    return {
      diversity,
      visual: 'gradient',
      description: 'Mixed perspectives - some disagreement',
    }
  } else {
    // High diversity - split/pattern fill
    return {
      diversity,
      visual: 'split',
      description: 'Polarized - strongly opposing views',
    }
  }
}
```

**Split Fill Implementation:**
```typescript
// For highly polarized regions, show both positive and negative sentiment
const polarizedFill = (hexagon: HexCell) => {
  const positiveRatio = hexagon.positive_sentiment_ratio

  return {
    type: 'split',
    colors: [
      { color: '#22C55E', ratio: positiveRatio },        // Green (positive)
      { color: '#EF4444', ratio: 1 - positiveRatio },   // Red (negative)
    ],
    orientation: 'diagonal',
  }
}
```

### Narrative Cluster Visualization

Countries with similar framing are grouped into narrative clusters.

```
ASCII Diagram - Cluster View:

  +---------+                    +---------+
  | Cluster |                    | Cluster |
  |    A    |                    |    B    |
  |  US,UK  |                    |  RU,CN  |
  | "Threat"|                    |"Defense"|
  +---------+                    +---------+
       \                              /
        \    +---------------+       /
         \   |   Cluster C   |      /
          \  |   IN,BR,ZA    |     /
           \ |  "Neutral"    |    /
            \+---------------+   /
             \                  /
              \                /
               +==============+
               | Topic: Ukraine |
               +==============+
```

**Cluster Color Coding:**
```typescript
const CLUSTER_COLORS = {
  western_aligned: '#3B82F6',   // Blue
  eastern_aligned: '#EF4444',   // Red
  neutral_bloc: '#A855F7',       // Purple
  regional_focus: '#F59E0B',     // Amber
  outlier: '#6B7280',            // Gray
}
```

---

## API Response Schema

### Enhanced `/v1/narratives/topic` Endpoint

```typescript
interface NarrativeTopicRequest {
  theme: string              // GDELT theme code (e.g., "ECON_INFLATION")
  time_window: string        // "1h" | "6h" | "12h" | "24h" | "7d"
  countries?: string[]       // ISO country codes to filter
  include_samples?: boolean  // Include sample headlines
  include_clusters?: boolean // Include narrative clustering
}

interface NarrativeTopicResponse {
  // Request context
  request: {
    theme: string
    theme_label: string
    time_window: string
    generated_at: string
    query_time_ms: number
  }

  // Global summary
  global_summary: {
    total_signals: number
    unique_countries: number
    average_sentiment: number
    sentiment_variance: number
    dominant_stance: 'supportive' | 'critical' | 'neutral' | 'mixed'
    drift_score: number
    polarization_index: number
  }

  // Geographic distribution
  geographic_distribution: Array<{
    country_code: string
    country_name: string
    region: string
    latitude: number
    longitude: number

    // Volume metrics
    signal_count: number
    signal_percentage: number

    // Sentiment metrics
    average_sentiment: number
    sentiment_variance: number
    dominant_emotion: string

    // Narrative metrics
    stance: 'supportive' | 'critical' | 'neutral' | 'mixed'
    drift_from_global: number
    narrative_cluster: string

    // Top elements
    top_keywords: Array<{
      term: string
      count: number
      sentiment: number
    }>
    top_actors: Array<{
      name: string
      type: 'person' | 'organization'
      mention_count: number
    }>
    top_outlets: Array<{
      name: string
      article_count: number
    }>

    // Sample content
    sample_urls: Array<{
      title: string
      url: string
      outlet: string
      sentiment: number
      timestamp: string
    }>
  }>

  // Narrative clusters
  narrative_clusters: Array<{
    cluster_id: string
    cluster_label: string
    description: string

    // Cluster characteristics
    dominant_stance: string
    average_sentiment: number
    framing_keywords: string[]

    // Member countries
    countries: Array<{
      country_code: string
      country_name: string
      membership_strength: number  // 0.0 to 1.0
    }>
  }>

  // Temporal evolution
  temporal_evolution: Array<{
    timestamp: string
    period_label: string

    // Metrics for this period
    total_signals: number
    average_sentiment: number
    dominant_stance: string

    // Geographic shifts
    geographic_shift: {
      emerging_countries: string[]
      declining_countries: string[]
    }
  }>

  // Source breakdown
  source_breakdown: {
    by_source_family: Array<{
      source_family: string  // "gdelt" | "reddit" | "mastodon" | etc.
      signal_count: number
      average_sentiment: number
      unique_countries: number
    }>

    by_outlet_type: {
      mainstream: number
      state_media: number
      independent: number
      social: number
    }
  }

  // Confidence indicators
  confidence: {
    overall_confidence: number  // 0.0 to 1.0
    data_quality_score: number
    source_diversity_score: number
    temporal_coverage_score: number

    // Warnings
    warnings: Array<{
      type: string
      message: string
      affected_countries: string[]
    }>
  }

  // Plain language summary
  summary: {
    headline: string          // One sentence summary
    key_findings: string[]    // 3-5 bullet points
    interpretation_notes: string[]
  }
}
```

### Example Response

```json
{
  "request": {
    "theme": "ECON_INFLATION",
    "theme_label": "Economic Inflation",
    "time_window": "24h",
    "generated_at": "2025-01-18T14:30:00Z",
    "query_time_ms": 342
  },
  "global_summary": {
    "total_signals": 4523,
    "unique_countries": 87,
    "average_sentiment": -0.28,
    "sentiment_variance": 0.45,
    "dominant_stance": "critical",
    "drift_score": 0.52,
    "polarization_index": 0.61
  },
  "geographic_distribution": [
    {
      "country_code": "US",
      "country_name": "United States",
      "region": "North America",
      "latitude": 37.0902,
      "longitude": -95.7129,
      "signal_count": 847,
      "signal_percentage": 18.7,
      "average_sentiment": -0.35,
      "sentiment_variance": 0.38,
      "dominant_emotion": "anger",
      "stance": "critical",
      "drift_from_global": 0.12,
      "narrative_cluster": "western_critical",
      "top_keywords": [
        {"term": "Federal Reserve", "count": 234, "sentiment": -0.42},
        {"term": "interest rates", "count": 198, "sentiment": -0.38},
        {"term": "consumer prices", "count": 156, "sentiment": -0.25}
      ],
      "top_actors": [
        {"name": "Jerome Powell", "type": "person", "mention_count": 312},
        {"name": "Federal Reserve", "type": "organization", "mention_count": 456}
      ],
      "top_outlets": [
        {"name": "Bloomberg", "article_count": 89},
        {"name": "Reuters", "article_count": 76},
        {"name": "Wall Street Journal", "article_count": 54}
      ],
      "sample_urls": [
        {
          "title": "Fed Maintains High Interest Rates Amid Inflation Concerns",
          "url": "https://example.com/article1",
          "outlet": "Bloomberg",
          "sentiment": -0.42,
          "timestamp": "2025-01-18T12:00:00Z"
        }
      ]
    }
  ],
  "narrative_clusters": [
    {
      "cluster_id": "western_critical",
      "cluster_label": "Western Critical",
      "description": "Coverage emphasizes policy failures and economic hardship",
      "dominant_stance": "critical",
      "average_sentiment": -0.38,
      "framing_keywords": ["crisis", "failure", "hardship", "burden"],
      "countries": [
        {"country_code": "US", "country_name": "United States", "membership_strength": 0.92},
        {"country_code": "GB", "country_name": "United Kingdom", "membership_strength": 0.88},
        {"country_code": "DE", "country_name": "Germany", "membership_strength": 0.85}
      ]
    },
    {
      "cluster_id": "emerging_resilient",
      "cluster_label": "Emerging Markets Resilient",
      "description": "Coverage emphasizes local economic strength despite global pressures",
      "dominant_stance": "neutral",
      "average_sentiment": 0.05,
      "framing_keywords": ["resilience", "growth", "adaptation", "opportunity"],
      "countries": [
        {"country_code": "IN", "country_name": "India", "membership_strength": 0.89},
        {"country_code": "BR", "country_name": "Brazil", "membership_strength": 0.82}
      ]
    }
  ],
  "temporal_evolution": [
    {
      "timestamp": "2025-01-18T00:00:00Z",
      "period_label": "00:00-06:00 UTC",
      "total_signals": 892,
      "average_sentiment": -0.22,
      "dominant_stance": "neutral",
      "geographic_shift": {
        "emerging_countries": ["JP", "AU"],
        "declining_countries": []
      }
    }
  ],
  "source_breakdown": {
    "by_source_family": [
      {
        "source_family": "gdelt",
        "signal_count": 4523,
        "average_sentiment": -0.28,
        "unique_countries": 87
      }
    ],
    "by_outlet_type": {
      "mainstream": 3245,
      "state_media": 456,
      "independent": 678,
      "social": 144
    }
  },
  "confidence": {
    "overall_confidence": 0.87,
    "data_quality_score": 0.92,
    "source_diversity_score": 0.85,
    "temporal_coverage_score": 0.84,
    "warnings": [
      {
        "type": "low_volume",
        "message": "Insufficient data for reliable analysis",
        "affected_countries": ["LY", "YE", "SO"]
      }
    ]
  },
  "summary": {
    "headline": "Global inflation coverage is predominantly negative, with Western nations most critical and emerging markets showing resilience narratives.",
    "key_findings": [
      "United States leads coverage volume with 18.7% of all signals",
      "Western cluster shows coordinated critical framing of central bank policies",
      "Emerging markets cluster presents contrasting narrative of economic resilience",
      "Polarization index of 0.61 indicates significant stance divergence globally"
    ],
    "interpretation_notes": [
      "High drift score (0.52) suggests regional framing varies significantly",
      "State media proportion (10.1%) within normal range for this topic"
    ]
  }
}
```

---

## User Interaction Flows

### Layer Toggle Behavior

```
+---------------------------------------------------+
|  User Action     |  System Response               |
+------------------+--------------------------------+
|  Click "Heatmap" |  1. Fade out Classic layers    |
|                  |     (300ms ease-out)           |
|                  |  2. Fetch hexmap data if stale |
|                  |  3. Fade in Heatmap layer      |
|                  |     (300ms ease-in)            |
|                  |  4. Update controls state      |
+------------------+--------------------------------+
|  Click "Classic" |  1. Fade out Heatmap layer     |
|                  |     (300ms ease-out)           |
|                  |  2. Fetch flows data if stale  |
|                  |  3. Fade in Classic layers     |
|                  |     (300ms ease-in)            |
|                  |  4. Update controls state      |
+------------------+--------------------------------+
|  Click "Both"    |  1. Blend both layer sets      |
|                  |  2. Reduce opacities           |
|                  |  3. Show layer balance slider  |
+---------------------------------------------------+
```

**State Machine:**
```typescript
type ViewMode = 'classic' | 'heatmap' | 'both'

interface ViewState {
  mode: ViewMode
  classicOpacity: number
  heatmapOpacity: number
  transitionProgress: number
}

const transitions: Record<string, ViewState> = {
  'classic': {
    mode: 'classic',
    classicOpacity: 1.0,
    heatmapOpacity: 0.0,
    transitionProgress: 1.0,
  },
  'heatmap': {
    mode: 'heatmap',
    classicOpacity: 0.0,
    heatmapOpacity: 0.6,
    transitionProgress: 1.0,
  },
  'both': {
    mode: 'both',
    classicOpacity: 0.8,
    heatmapOpacity: 0.4,
    transitionProgress: 1.0,
  },
}
```

### Hover/Click Interactions

#### Hexagon Hover (Heatmap Mode)

```
Timeline:
0ms      - Mouse enters hexagon
200ms    - Hover delay elapsed, show Level 1 tooltip
200ms+   - Tooltip follows cursor with 50px offset
Exit     - Tooltip fades out (150ms)
```

```typescript
const hexHoverHandler = {
  onHover: (info: PickingInfo) => {
    if (!info.object) {
      hideTooltip()
      return
    }

    clearTimeout(hoverTimeout)
    hoverTimeout = setTimeout(() => {
      showTooltip({
        level: 1,
        data: info.object,
        position: info.coordinate,
      })
    }, 200)
  },
}
```

#### Centroid Click (Classic Mode)

```
Timeline:
0ms      - Mouse click on centroid
50ms     - Scale animation (1.0 -> 1.2)
100ms    - Sidebar panel slides in from right
150ms    - Sidebar populated with country data
```

```typescript
const centroidClickHandler = {
  onClick: (hotspot: CountryHotspot) => {
    // Update store
    setSelectedHotspot(hotspot)

    // Animate centroid
    animateSelected(hotspot.country_code)

    // Show sidebar
    setSidebarOpen(true)

    // Fetch detailed data
    fetchCountryNarrative(hotspot.country_code)
  },
}
```

#### Flow Line Click

```
Timeline:
0ms      - Mouse click on flow line
50ms     - Line pulses (opacity: 1.0)
100ms    - Popup appears at click point
150ms    - Popup shows flow details
```

```typescript
interface FlowClickPopup {
  from_country: string
  to_country: string
  heat: number
  shared_topics: string[]
  time_delta: string
  similarity_explanation: string
}
```

### Time Scrubbing

Time scrubbing allows users to see how narratives evolved over a time window.

```
+----------------------------------------------------------+
|  Timeline Control                                         |
|  =========================================================|
|                                                           |
|  [|----o--------------|]  12:00 UTC                       |
|   ^                    ^                                  |
|  Start                End                                 |
|                                                           |
|  Speed: [<] 1x [>]    [Play] [Pause] [Reset]             |
+----------------------------------------------------------+
```

**Interaction States:**

1. **Drag Scrubber:** Move playhead to specific time
2. **Click Timeline:** Jump to clicked position
3. **Play/Pause:** Auto-advance at selected speed
4. **Speed Control:** 0.5x, 1x, 2x, 4x playback

**Implementation:**
```typescript
interface TimelineState {
  windowStart: Date
  windowEnd: Date
  currentTime: Date
  isPlaying: boolean
  playbackSpeed: number
}

const timelineReducer = (state: TimelineState, action: TimelineAction) => {
  switch (action.type) {
    case 'SCRUB':
      return { ...state, currentTime: action.time }
    case 'PLAY':
      return { ...state, isPlaying: true }
    case 'PAUSE':
      return { ...state, isPlaying: false }
    case 'SET_SPEED':
      return { ...state, playbackSpeed: action.speed }
    case 'RESET':
      return { ...state, currentTime: state.windowStart }
  }
}
```

### Search Filtering

Search allows users to filter the visualization by theme, entity, or keyword.

```
+----------------------------------------------------------+
|  Search & Filter                                          |
|  =========================================================|
|                                                           |
|  [Search themes, actors, keywords...]         [X]         |
|                                                           |
|  Quick Filters:                                           |
|  [Economic] [Political] [Military] [Social] [More...]    |
|                                                           |
|  Active Filters:                                          |
|  [ECON_INFLATION x] [Jerome Powell x]                    |
|                                                           |
|  Showing 847 signals in 12 countries                      |
+----------------------------------------------------------+
```

**Search Flow:**

1. User types query (debounced 300ms)
2. System searches themes, actors, keywords
3. Autocomplete dropdown shows matches
4. User selects or presses Enter
5. Filter applied to visualization
6. Data re-fetched with filter parameters

**Filter Types:**
```typescript
interface SearchFilter {
  type: 'theme' | 'actor' | 'keyword' | 'country' | 'sentiment'
  value: string
  label: string
}

const applyFilters = (filters: SearchFilter[]): URLSearchParams => {
  const params = new URLSearchParams()

  filters.forEach(filter => {
    switch (filter.type) {
      case 'theme':
        params.append('theme_filter', filter.value)
        break
      case 'actor':
        params.append('actor_filter', filter.value)
        break
      case 'sentiment':
        params.append('sentiment_range', filter.value)
        break
      // etc.
    }
  })

  return params
}
```

---

## Performance Optimization

### Rendering Performance

#### Target Metrics
- **Initial render:** < 1 second
- **Layer toggle:** < 100ms
- **Frame rate:** 60 FPS sustained
- **Data update:** < 500ms (visual refresh)

#### Optimization Strategies

**1. WebGL Layer Batching**
```typescript
// Combine multiple layers into single draw call where possible
const combinedLayers = [
  new CompositeLayer({
    id: 'narrative-composite',
    layers: [heatmapLayer, flowLayer, centroidLayer],
    pickable: true,
  }),
]
```

**2. Data Decimation**
```typescript
// Reduce data points at low zoom levels
const decimateData = (data: HexCell[], zoom: number): HexCell[] => {
  const decimationFactor = zoom < 3 ? 4 : zoom < 5 ? 2 : 1

  if (decimationFactor === 1) return data

  return data.filter((_, i) => i % decimationFactor === 0)
}
```

**3. Progressive Loading**
```typescript
// Load visible region first, then expand
const loadProgressively = async (bounds: Bounds) => {
  // Phase 1: Load visible hexes immediately
  const visibleData = await fetchHexes(bounds)
  setHexmapData(visibleData)

  // Phase 2: Load surrounding region in background
  const expandedBounds = expandBounds(bounds, 1.5)
  const surroundingData = await fetchHexes(expandedBounds)
  setHexmapData(mergeData(visibleData, surroundingData))
}
```

**4. Memoization**
```typescript
// Memoize expensive layer calculations
const layers = useMemo(() => {
  if (!hexmapData?.hexes) return []

  return [
    new H3HexagonLayer({
      id: 'h3-hexagon-layer',
      data: hexmapData.hexes,
      // ... layer config
    }),
  ]
}, [hexmapData, viewState.zoom])
```

**5. RAF Throttling**
```typescript
// Throttle animations to avoid frame drops
const throttledAnimate = () => {
  if (!animating) return

  requestAnimationFrame((timestamp) => {
    const elapsed = timestamp - lastFrame

    if (elapsed >= 16.67) {  // 60 FPS target
      updateAnimationState(timestamp)
      lastFrame = timestamp
    }

    throttledAnimate()
  })
}
```

### Data Transfer Optimization

**1. Compression**
```typescript
// Use gzip/brotli compression for API responses
// Backend: app.use(compression())
// Response size reduction: ~70-80%
```

**2. Field Selection**
```typescript
// Request only needed fields
const fetchData = async (fields: string[]) => {
  const params = new URLSearchParams({
    fields: fields.join(','),
  })
  return fetch(`/api/hexmap?${params}`)
}
```

**3. Incremental Updates**
```typescript
// Delta updates instead of full refresh
interface DeltaUpdate {
  added: HexCell[]
  modified: HexCell[]
  removed: string[]  // h3_index values
}

const applyDelta = (current: HexCell[], delta: DeltaUpdate): HexCell[] => {
  const indexed = new Map(current.map(h => [h.h3_index, h]))

  delta.removed.forEach(id => indexed.delete(id))
  delta.modified.forEach(h => indexed.set(h.h3_index, h))
  delta.added.forEach(h => indexed.set(h.h3_index, h))

  return Array.from(indexed.values())
}
```

### Memory Management

**1. Object Pooling**
```typescript
// Reuse layer objects instead of recreating
class LayerPool {
  private pool: Map<string, Layer> = new Map()

  getLayer(id: string, config: LayerConfig): Layer {
    const existing = this.pool.get(id)

    if (existing) {
      existing.setProps(config)
      return existing
    }

    const newLayer = createLayer(config)
    this.pool.set(id, newLayer)
    return newLayer
  }
}
```

**2. Cleanup on Unmount**
```typescript
useEffect(() => {
  return () => {
    // Clean up WebGL resources
    deckRef.current?.finalize()

    // Clear cached data
    setHexmapData(null)
    setFlowsData(null)
  }
}, [])
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1)

**Deliverables:**
- [ ] Refactor MapContainer for dual-layer support
- [ ] Implement layer toggle with transitions
- [ ] Add performance monitoring hooks

**Tasks:**
1. Create ViewModeProvider context for layer state
2. Implement fade transitions between modes
3. Add "both" mode with opacity blending
4. Set up performance metrics collection

### Phase 2: Heatmap Enhancement (Week 2)

**Deliverables:**
- [ ] Fix H3HexagonLayer rendering (Issue #13)
- [ ] Implement sentiment color gradient
- [ ] Add k-ring blur smoothing
- [ ] Create recency glow effect

**Tasks:**
1. Debug deck.gl/mapbox integration
2. Implement CIELAB color interpolation
3. Add elevation-based glow
4. Test with GDELT-shaped placeholders

### Phase 3: Animation System (Week 3)

**Deliverables:**
- [ ] Implement breathing centroids
- [ ] Add flow line particles
- [ ] Create gradient transitions
- [ ] Build time scrubbing UI

**Tasks:**
1. Integrate Framer Motion for centroids
2. Configure TripsLayer for particles
3. Implement smooth color transitions
4. Build timeline control component

### Phase 4: Tooltip System (Week 4)

**Deliverables:**
- [ ] Implement three-level progressive disclosure
- [ ] Create plain language explanations
- [ ] Build detailed analysis panel
- [ ] Add narrative cluster view

**Tasks:**
1. Design tooltip component hierarchy
2. Implement hover delay and positioning
3. Create narrative summary generator
4. Build tabbed detail view

### Phase 5: Integration & Polish (Week 5)

**Deliverables:**
- [ ] Connect to `/v1/narratives/topic` endpoint
- [ ] Implement search filtering
- [ ] Performance optimization pass
- [ ] User testing and refinement

**Tasks:**
1. Integrate narrative API responses
2. Build search autocomplete
3. Profile and optimize render performance
4. Address user feedback

---

## Success Criteria

### Performance Targets

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Initial render | < 1s | Lighthouse FCP |
| Layer toggle | < 100ms | Performance API |
| Frame rate | 60 FPS | Chrome DevTools |
| Data update | < 500ms | Network waterfall |
| Memory usage | < 200MB | Chrome Task Manager |

### User Experience Goals

| Goal | Success Metric | Target |
|------|----------------|--------|
| Understand intensity | Task completion time | < 5s |
| Identify narratives | Accuracy rate | > 85% |
| Compare regions | Time to compare | < 10s |
| Find specific topic | Search success rate | > 90% |

### Quality Assurance

- [ ] All animations run at 60 FPS on mid-range devices
- [ ] Tooltips display correct data for all regions
- [ ] Layer transitions are smooth and consistent
- [ ] No memory leaks after extended use
- [ ] Accessible keyboard navigation
- [ ] Screen reader compatibility

---

## Appendix A: Color Palettes

### Sentiment Palette
```css
--sentiment-very-negative: #EF4444;
--sentiment-negative: #FB923C;
--sentiment-neutral: #FACC15;
--sentiment-positive: #A3E635;
--sentiment-very-positive: #22C55E;
```

### UI Palette
```css
--ui-background: rgba(33, 37, 71, 0.95);
--ui-foreground: #FFFFFF;
--ui-accent: #646CFF;
--ui-muted: rgba(255, 255, 255, 0.7);
--ui-border: rgba(255, 255, 255, 0.1);
```

### Cluster Palette
```css
--cluster-western: #3B82F6;
--cluster-eastern: #EF4444;
--cluster-neutral: #A855F7;
--cluster-regional: #F59E0B;
--cluster-outlier: #6B7280;
```

---

## Appendix B: Animation Timing Functions

```typescript
// Easing functions for smooth animations
const easings = {
  // Smooth deceleration
  easeOut: (t: number) => 1 - Math.pow(1 - t, 3),

  // Smooth acceleration
  easeIn: (t: number) => t * t * t,

  // Smooth acceleration and deceleration
  easeInOut: (t: number) => t < 0.5
    ? 4 * t * t * t
    : 1 - Math.pow(-2 * t + 2, 3) / 2,

  // Smoothstep for breathing
  smoothstep: (t: number) => t * t * (3 - 2 * t),

  // Elastic for bouncy effects
  elastic: (t: number) => {
    const c4 = (2 * Math.PI) / 3
    return t === 0 ? 0 : t === 1 ? 1 :
      Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * c4) + 1
  },
}
```

---

## Appendix C: Testing Checklist

### Visual Testing
- [ ] Heatmap renders at all zoom levels (2-12)
- [ ] Flow lines curve correctly over long distances
- [ ] Centroids scale properly with topic count
- [ ] Tooltips position correctly near viewport edges
- [ ] Animations are smooth without stuttering
- [ ] Colors are distinguishable for color-blind users

### Functional Testing
- [ ] Layer toggle preserves data state
- [ ] Hover interactions work on mobile (touch)
- [ ] Search filters return correct results
- [ ] Time scrubbing updates visualization
- [ ] Sidebar displays correct country data

### Performance Testing
- [ ] 1000+ hexagons render at 60 FPS
- [ ] 100+ flow lines animate smoothly
- [ ] Memory stable after 10 minutes of use
- [ ] Network requests cached appropriately

---

**Document Version:** 1.0
**Status:** Ready for Implementation
**Next Review:** After Phase 2 completion
