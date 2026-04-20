# ATLAS Comprehensive Review

Date: 2026-03-29
Reviewer: Claude (automated audit)
Scope: Information quality, UI hierarchy, aesthetic coherence

---

## 1. Information Quality Audit

### Signal Stream

The Signal Stream displays live GDELT headlines. Roughly 30% of displayed signals are noise:

**Noise examples from live API (2026-03-29):**
- "Chiefs Hc Andy Reid Provides Update On Patrick Mahomes Injury Rehab" (sports)
- "Tiger Woods Banned By Secret Service From Driving Trumps Grandkids Report" (celebrity)
- "Welcome To Rocky Top Reads" (campus/local)
- "Monarch Butterfly Michigan" (local nature story tagged with CRIME_VIOLENCE, BORDER, ALLIANCE)
- "Doctor Explains What Metallic Taste 33680477" (health clickbait with GDELT document ID in title)

**Existing filter**: `isValidHeadline()` catches hex-code IDs and strings with <3 words, but does not filter sports, entertainment, or local news.

**GDELT over-tagging problem**: A butterfly article is tagged with 10 themes including CRIME_VIOLENCE, BORDER, ALLIANCE. This means theme-based filtering must be conservative (use headline keywords, not theme codes alone).

**Recommendation**: Add headline keyword regex filter for sports/entertainment. Keep existing structural filter.

### Narrative Threads

At 24h window, the API returns:
- "Environment" (UNGP_FORESTS_RIVERS_OCEANS): 17,584 signals, 183 countries, 89.3% spread, "stable"
- "US Politics" (USPEC_POLITICS_GENERAL1): 13,524 signals, 174 countries, 84.9% spread, "stable"

These are not narratives — they are GDELT's broadest meta-categories. Every news article mentioning nature gets tagged UNGP_FORESTS_RIVERS_OCEANS. At 24h, these categories reach 85-89% of all countries. At longer windows, they converge toward 100%.

**The panel is meaningful only at short time ranges** (6-12h) where genuine spikes and accelerations are visible against normal background noise. At 3 months, it shows static noise at maximum spread.

**Recommendation**: Cap the panel's API query to 24h regardless of global time range.

### Anomaly Panel

The API returns 10 anomalies, ALL classified as "critical":

| Country | Code | Current | Baseline | Multiplier |
|---------|------|---------|----------|------------|
| AL      | AL   | 274     | 1.0      | 274.0x     |
| RI      | RI   | 268     | 1.5      | 178.7x     |
| RB      | RB   | 194     | 2.0      | 97.0x      |
| SI      | SI   | 95      | 1.0      | 95.0x      |
| KV      | KV   | 216     | 1.5      | 144.0x     |

**Problems:**
1. When everything is critical, nothing is useful. The panel cannot differentiate genuine crises from statistical noise.
2. Countries with baseline_avg of 1.0 (essentially no historical data) produce absurd multipliers from tiny signal counts.
3. Country codes AL, KV, SI, RI, RB display without human-readable names.
4. Iran (2,790 signals, 146.8x) is genuinely notable but drowns among noise entries.

**Recommendation**: Client-side filter requiring `current_count > 10` AND `multiplier > 5`. Recalculate severity from filtered set. Add country name lookup.

### Source Integrity

- "Source Quality: 89/100" is computed as `100 - (top_source_concentration * 1.5)`
- This is a concentration metric, not a quality assessment. A system ingesting 7,099 sources will always score high.
- The metric gives false confidence — it cannot distinguish Reuters from a content farm.

**No code change recommended** (requires backend work). The score display is what it is.

---

## 2. UI Hierarchy Audit

### Visual Weight Distribution

| Panel | Grid Area | Screen % | Visual Weight | Should Be |
|-------|-----------|----------|---------------|-----------|
| Globe | 35% x 80% | 28% | Equal to Stream | PRIMARY |
| Signal Stream | 35% x 80% | 28% | Equal to Globe | SECONDARY |
| Narrative Threads | 30% x 40% | 12% | Same as Matrix | SECONDARY |
| Correlation Matrix | 30% x 40% | 12% | Placeholder | LOW |
| Source Integrity | 35% x 20% | 7% | Same as primary | TERTIARY |
| Anomaly Alert | 65% x 20% | 13% | CRITICAL pulse draws eye | TERTIARY |

### First Impression Problems

1. **The Globe is not the center of gravity.** It shares equal column width with Signal Stream. The panel border, header, and background are identical to every other panel.
2. **The eye goes to the Anomaly pulse.** The "SYSTEM STATUS: CRITICAL" header with a pulsing red dot is the most visually aggressive element on screen.
3. **Panel headers are undifferentiated.** All 6 use 10px uppercase with 1.2px letter-spacing in #64748b. They read like debug labels, not designed interface elements.

### Recommendations

- Make Globe panel border nearly invisible, add subtle glow
- Shrink Globe header (the map IS the content)
- Give secondary panels slightly more prominent headers (11px)
- Make tertiary panels visually recessive (lighter borders, muted headers)
- Slow the anomaly pulse animation

---

## 3. Aesthetic Audit

### Background
- Current: `#0a0a0a` (near-pure black)
- Problem: Pure black causes harsh contrast with text. Dark-mode best practices recommend #121212-#1E1E1E range.
- The variables.css already defines `--color-bg-primary: #0a0f1a` (dark navy) which is superior. It is not used.

### Color System
- `variables.css` defines 20+ CSS custom properties (accent, severity, sentiment, text tiers)
- App.css and all component CSS files ignore these variables completely
- Ad-hoc colors found: #666, #888, #555, #ccc, #ddd, #aaa, #999 (generic grays with no semantic meaning)
- Accent blue appears as both `#38bdf8` (hardcoded) and `var(--color-accent-primary)` (variable)

### Typography
- Body: `'Inter', -apple-system, sans-serif` (good)
- Data: `monospace` (generic) used 15+ times instead of `var(--font-mono)` which maps to JetBrains Mono
- The font variable exists but is never referenced by component CSS

### Heatmap
- 6-color range: transparent -> blue -> teal -> green -> amber -> red
- The green midpoint (#508C50) creates false "safe" reading at moderate activity levels
- Should use a single-axis cool-to-warm progression without green

### What Feels Right
- The dark-on-dark panel structure (when borders are subtle) creates good depth
- The monospace data display in Signal Stream reads well
- The sparkline mini-charts in Narrative Threads are effective
- The overall Bloomberg Terminal inspiration is sound

---

## 4. Prioritized Change List

| # | Change | Impact | Effort | Files |
|---|--------|--------|--------|-------|
| 1 | Signal Stream relevance filtering | HIGH | LOW | SignalStream.tsx |
| 2 | Panel header typography hierarchy | HIGH | LOW | App.css |
| 3 | Globe visual dominance | MEDIUM | LOW | App.css |
| 4 | Tertiary panel quieting | MEDIUM | LOW | App.css, AnomalyPanel.css, SourceIntegrityPanel.css |
| 5 | CSS variables adoption | MEDIUM | MEDIUM | All CSS files |
| 6 | Anomaly panel data quality | HIGH | MEDIUM | CrisisContext.tsx, AnomalyPanel.tsx |
| 7 | Narrative Threads time capping | MEDIUM | LOW | NarrativeThreads.tsx |
| 8 | Heatmap color refinement | LOW-MED | LOW | App.tsx |
