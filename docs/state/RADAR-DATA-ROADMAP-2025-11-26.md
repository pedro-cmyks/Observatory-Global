# Radar Data Roadmap & Baseline
**Date:** 2025-11-26
**Status:** Baseline Established (Mock Data)

## 1. Current Baseline (Mock Data)
The current stable version (`main` branch) uses a self-contained mock data generator in `radarStore.ts`.

### Data Logic
*   **Nodes (Countries):**
    *   Source: Hardcoded list of 15 major countries (US, CN, RU, IN, DE, etc.).
    *   Intensity: Base intensity (0.4 - 0.9) adjusted by time window multiplier (shorter window = higher burst intensity).
    *   Sentiment: Hardcoded static values (-0.5 to 0.3).
    *   Themes: Static list per country (e.g., US: ['Politics', 'Economy']).
*   **Flows:**
    *   Logic: Generated dynamically between active nodes.
    *   Condition: Nodes share at least one theme.
    *   Strength: `(SharedThemes * (IntensityA + IntensityB) / 2)`.
    *   Visual: Arcs drawn if strength >= 0.5.
*   **Heatmap:**
    *   Logic: "Major Cities" dictionary maps country codes to specific lat/lon points.
    *   Generation: Creates dispersed points around these cities.
    *   Weight: Scales with node intensity.
*   **Time Window:**
    *   Effect: Controls `nodeCount` (Top 5 for 1h -> All 15 for 24h) and intensity multipliers.

### Assumptions & Limitations
*   **Centroid Bias:** Heatmap is purely decorative around major cities, not reflecting real event locations.
*   **Static Relationships:** Flows are based on static themes, not real-time narrative connections.
*   **Western/Major Power Bias:** Only 15 countries are represented.

---

## 2. Phase 1: GDELT Live Integration
**Goal:** Replace mock generator with `SignalsService` (GDELT) while maintaining visual stability.

### Data Mapping Strategy
| Radar Element | GDELT Source Field | Transformation Logic |
| :--- | :--- | :--- |
| **Nodes** | `ActionGeo_CountryCode` | Aggregated volume of events/mentions per country. Normalized (0-1) against global max volume in window. |
| **Intensity** | Event Count / Article Count | `(CountryVolume / MaxCountryVolume)`. Logarithmic scale recommended to prevent US/China dominance. |
| **Sentiment** | `AvgTone` | Average `AvgTone` of articles for that country. Normalized to -1.0 to 1.0 range. |
| **Flows** | Co-occurrence | Count of articles mentioning both Country A and Country B. Strength = Normalized co-occurrence count. |
| **Heatmap** | `ActionGeo_Lat/Long` | Use actual event coordinates from GDELT GKG. Fallback to capital city if specific geo missing. |
| **Themes** | `Themes` (GKG) | Top 3 most frequent themes for that country in the window. |

### Normalization & "Red Map" Prevention
*   **Problem:** US/Europe have 100x more coverage than Madagascar.
*   **Solution:**
    *   **Relative Intensity:** Visualize intensity *relative to that country's baseline* (Z-score) OR use logarithmic scaling for global comparison.
    *   **Cap:** Cap the "Red" intensity at the 95th percentile to allow smaller spikes to be visible.

### Time Window Implementation
*   **Backend:** `/v1/flows?time_window=X` endpoint already accepts `1h`, `6h`, etc.
*   **Query:** `SignalsService` filters GDELT data by `DATE > NOW - Window`.

---

## 3. Phase 2: Query & Topic Mode (Medium Term)
**Goal:** "Show me the radar for 'Bitcoin' or 'Climate Change'".

### Architecture Changes
*   **API:** New parameter `?query=topic` or `?entity=name`.
*   **Backend:**
    *   Filter GDELT GKG records where `Themes` contains TOPIC or `Persons`/`Orgs` contains ENTITY.
    *   Re-aggregate Nodes/Flows/Heatmap *only* for that subset.
*   **UI:**
    *   "Global" vs "Topic" mode toggle.
    *   Search bar in header.

---

## 4. Phase 3: Multi-Source Narrative (Long Term)
**Goal:** Merge GDELT with Reddit, Twitter/X, Financial News.

### Unified Signal Model
*   **Abstract Signal:**
    ```typescript
    interface Signal {
      source: 'GDELT' | 'REDDIT' | 'TWITTER';
      location: GeoPoint;
      timestamp: Date;
      intensity: number;
      sentiment: number;
      entities: string[];
    }
    ```
*   **Fusion Engine:**
    *   Normalize intensity per source (1000 Tweets != 1 GDELT Event).
    *   Weighted average for Sentiment.
    *   Union of Entities/Themes.

---

## Next Steps
1.  **Backend Stability:** Ensure `uvicorn` runs reliably (Dockerize).
2.  **Data Wiring:** Switch `useMockData = false` and consume `/v1/flows`.
3.  **Validation:** Compare "Real" GDELT map vs "Mock" map and tune normalization.
