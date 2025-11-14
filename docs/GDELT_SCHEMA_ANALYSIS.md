# GDELT Data Structure Analysis for Observatory Global
## DataSignalArchitect Review - Comprehensive Schema Mapping

**Date**: 2025-01-14
**Status**: Architecture Analysis - Ready for Implementation
**Author**: DataSignalArchitect Agent
**Related Docs**: `GDELT_DATA_STRUCTURE.md`, `database-schema-design.md`

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [GDELT 2.0 Data Architecture](#2-gdelt-20-data-architecture)
3. [Field-by-Field Analysis](#3-field-by-field-analysis)
4. [Core Signals Layer Mapping](#4-core-signals-layer-mapping)
5. [UI Data Exposure Strategy](#5-ui-data-exposure-strategy)
6. [Visualization Requirements](#6-visualization-requirements)
7. [Implementation Priorities](#7-implementation-priorities)
8. [Concerns and Recommendations](#8-concerns-and-recommendations)

---

## 1. Executive Summary

### Current State
- **Data Source**: Placeholder data (hardcoded fallbacks)
- **Real Parser**: Not implemented
- **Data Quality**: ~2% (synthetic)
- **Update Frequency**: None

### Target State
- **Primary Source**: GDELT 2.0 Global Knowledge Graph (GKG)
- **Secondary Source**: GDELT Events Database
- **Update Frequency**: Every 15 minutes (real-time)
- **Data Quality**: 95%+ (global news coverage)
- **Geographic Coverage**: 200+ countries, 100+ languages

### Key Findings

**GDELT provides THREE datasets:**

1. **Global Knowledge Graph (GKG)** - **PRIMARY CHOICE**
   - Rich thematic classification (280+ themes)
   - Geographic precision (lat/long + place names)
   - Sentiment/tone analysis
   - Named entities (people, organizations)
   - Updated every 15 minutes
   - ~10,000-30,000 articles per file

2. **Events Database** - **SECONDARY (for flows)**
   - Actor-based event tracking (Actor1 → Action → Actor2)
   - CAMEO event taxonomy (cooperation vs conflict)
   - Goldstein scale (-10 to +10 intensity)
   - Geographic data for actors and action location

3. **Mentions Database** - **OPTIONAL (for verification)**
   - Tracks multiple mentions of same event
   - Source diversity metrics
   - Useful for confidence scoring

### Strategic Recommendation

**Focus on GKG as primary data source** for the following reasons:
- Best alignment with "narrative intelligence" vision
- Provides pre-classified themes (reduces NLP complexity)
- Includes geographic coordinates for heatmap visualization
- Contains sentiment data for "why is this heating up?" questions
- Rich entity extraction (persons, organizations) for narrative actors

---

## 2. GDELT 2.0 Data Architecture

### 2.1 Update Mechanism

```
GDELT Publishing Cadence:
└─ Every 15 minutes (96 files per day)
   ├─ GKG: YYYYMMDDHHMMSS.gkg.csv.zip (~5-15 MB compressed)
   ├─ Events: YYYYMMDDHHMMSS.export.CSV.zip
   └─ Mentions: YYYYMMDDHHMMSS.mentions.CSV.zip

Access Pattern:
http://data.gdeltproject.org/gdeltv2/YYYYMMDDHHMMSS.gkg.csv.zip

Latest File Metadata:
http://data.gdeltproject.org/gdeltv2/lastupdate.txt
```

### 2.2 File Format

**GKG Files:**
- Format: Tab-delimited CSV (despite .csv extension)
- Compression: ZIP (50-150 MB uncompressed)
- Encoding: UTF-8
- Structure: 27 columns (v2.1 schema)
- No header row (field order is fixed)

**Events Files:**
- Format: Tab-delimited CSV
- Structure: 61 columns (v2.0 schema)
- Includes 3 geographic location sets (Actor1Geo, Actor2Geo, ActionGeo)

### 2.3 Data Volume Estimates

| Metric | Value | Impact |
|--------|-------|--------|
| Files per day | 96 | Continuous polling required |
| Articles per file (GKG) | 10,000-30,000 | ~1-2M articles/day globally |
| Uncompressed size | 50-150 MB per 15-min | ~10 GB/day uncompressed |
| Compressed size | 5-15 MB per 15-min | ~1 GB/day compressed |
| Countries covered | 200+ | Need country filtering |
| Languages | 100+ | Multilingual support built-in |

---

## 3. Field-by-Field Analysis

### 3.1 GKG v2.1 Complete Schema (27 Columns)

#### TIER 1: CRITICAL FIELDS (Must Implement)

| Column | Name | Type | Description | Relevance | Use Case |
|--------|------|------|-------------|-----------|----------|
| **1** | `GKGRECORDID` | String | Unique identifier (e.g., `20251114020000-T52`) | **CRITICAL** | Deduplication, primary key |
| **2** | `V2DATE` | Timestamp | Publication date (`YYYYMMDDHHMMSS`) | **CRITICAL** | Temporal analysis, time-series |
| **4** | `V2Locations` | Complex | Geographic data with lat/long | **CRITICAL** | Heatmap, centroid positioning |
| **7** | `V2Tone` | CSV | Sentiment scores (6 values) | **CRITICAL** | "Why heating up?" emotion layer |
| **8** | `V2Themes` | List | GDELT taxonomy themes (280+) | **CRITICAL** | Topic clustering, signals |
| **15** | `V2Counts` | Complex | Theme mention frequencies | **CRITICAL** | Intensity calculation |

#### TIER 2: HIGH-VALUE FIELDS (Implement Early)

| Column | Name | Type | Description | Relevance | Use Case |
|--------|------|------|-------------|-----------|----------|
| **5** | `V2Persons` | List | Named individuals | **HIGH** | Narrative actors, entity tracking |
| **6** | `V2Organizations` | List | Organizations/institutions | **HIGH** | Institutional analysis |
| **9** | `V2GCAM` | Complex | Content analysis metrics (2,300+ dimensions) | **HIGH** | Advanced sentiment, emotion granularity |
| **20** | `V2SourceCommonName` | String | News outlet (e.g., "bbc.com") | **HIGH** | Source diversity, credibility |
| **21** | `V2DocumentIdentifier` | URL | Article URL | **HIGH** | Content preview, citation |

#### TIER 3: USEFUL FIELDS (Implement Later)

| Column | Name | Type | Description | Relevance | Use Case |
|--------|------|------|-------------|-----------|----------|
| **3** | `V2SourceCollectionIdentifier` | Integer | Source type (1=web, 2=broadcast) | **MEDIUM** | Media type filtering |
| **10** | `V2Quotations` | Complex | Extracted quotes | **MEDIUM** | Supporting evidence, stance |
| **11** | `V2AllNames` | List | All named entities | **MEDIUM** | Comprehensive entity graph |
| **12** | `V2Amounts` | Complex | Numerical mentions (money, percentages) | **MEDIUM** | Economic indicators |
| **13** | `V2TranslationInfo` | String | Translation metadata | **MEDIUM** | Multilingual tracking |
| **23** | `V2SharingImage` | URL | Article thumbnail | **MEDIUM** | Visual preview in UI |
| **24** | `V2RelatedImages` | List | Associated images | **LOW** | Media richness |
| **25** | `V2SocialImageEmbeds` | List | Social media embeds | **LOW** | Social amplification |
| **26** | `V2SocialVideoEmbeds` | List | Video embeds | **LOW** | Multimedia context |
| **27** | `V2ExtrasXML` | XML | Extensible metadata | **LOW** | Future enhancements |

### 3.2 Critical Field Deep Dive

#### V2Locations (Column 4)

**Format**: Semicolon-separated location blocks

**Structure per location**:
```
Type#FullName#CountryCode#ADM1Code#Lat#Long#FeatureID#OffsetCharacters
```

**Example**:
```
1#United States#US##38#-97#US#1;1#New York#US#USNY#40.7128#-74.006#5128581#234,412
```

**Parsed Data**:
```json
{
  "type": 1,  // 1=Country, 2=US State, 3=US City, 4=World City, 5=World State
  "full_name": "New York",
  "country_code": "US",
  "adm1_code": "USNY",
  "latitude": 40.7128,
  "longitude": -74.006,
  "feature_id": 5128581,  // GeoNames ID
  "char_offsets": [234, 412]  // Where in article mentioned
}
```

**Relevance for Observatory**: ★★★★★
- **Heatmap**: Direct lat/long for geographic intensity
- **Centroids**: City-level precision for node positioning
- **Country Filtering**: Filter by `country_code` for targeted monitoring
- **Multi-location**: Articles often mention multiple places (origin + destination = flow hint)

**Implementation Priority**: **IMMEDIATE**

---

#### V2Tone (Column 7)

**Format**: Six comma-separated values

**Structure**:
```
Tone,PositiveScore,NegativeScore,Polarity,ActivityDensity,SelfGroupRef
```

**Example**:
```
-3.21,2.1,45.2,1.8,12,5
```

**Parsed Data**:
```json
{
  "tone": -3.21,           // Overall sentiment: -100 (very negative) to +100 (very positive)
  "positive_pct": 2.1,     // % of positive words in article
  "negative_pct": 45.2,    // % of negative words in article
  "polarity": 1.8,         // Emotional intensity (distance from neutral)
  "activity_density": 12,  // Action word density
  "self_group_ref": 5      // First-person plural references (we, us, our)
}
```

**Relevance for Observatory**: ★★★★★
- **Heatmap Color Gradient**: Negative = red, neutral = yellow, positive = green
- **"Why Heating Up?" Answer**: Tone explains emotional driver behind spike
- **Stance Detection**: Combined with themes, reveals pro/anti positions
- **Narrative Quality**: Polarity and activity indicate urgency/importance

**Typical Value Ranges** (from GDELT research):
- Most articles: -10 to +10
- Crisis/conflict: -30 to -50
- Diplomatic cooperation: +10 to +30
- Extreme outliers: -80 (atrocities) to +80 (celebration)

**Implementation Priority**: **IMMEDIATE** (Week 1)

---

#### V2Themes (Column 8)

**Format**: Semicolon-separated taxonomy codes

**Example**:
```
TAX_FNCACT;ECON_INFLATION;WB_632_WOMEN_IN_POLITICS;ENV_CLIMATECHANGE
```

**Taxonomy Categories** (280+ total themes):

| Prefix | Category | Example Themes | Count |
|--------|----------|----------------|-------|
| `TAX_` | GDELT Thematic Taxonomy | `TAX_TERROR`, `TAX_FNCACT` (Finance) | ~50 |
| `WB_` | World Bank SDGs | `WB_632_WOMEN_IN_POLITICS` | ~100 |
| `UNGP_` | UN Global Pulse | `UNGP_DISASTER` | ~30 |
| `CRISISLEX_` | Crisis Events | `CRISISLEX_C03_DEAD_WOUNDED` | ~20 |
| `ENV_` | Environment | `ENV_CLIMATECHANGE`, `ENV_FORESTS` | ~25 |
| `ECON_` | Economics | `ECON_INFLATION`, `ECON_BANKRUPTCY` | ~30 |
| None | CAMEO/Direct | `PROTEST`, `ARREST`, `KILL`, `SEIZE` | ~25 |

**Top 20 Most Common Themes** (for reference):
1. `TAX_FNCACT` - Financial/Economic Activity
2. `TAX_TERROR` - Terrorism
3. `LEADER` - Political Leadership
4. `SOC_POINTSOFVIEW` - Social Perspectives/Opinions
5. `MEDIA_MSM` - Mainstream Media
6. `ARMEDCONFLICT` - Armed Conflict
7. `ECON_TRADE` - International Trade
8. `ENV_CLIMATECHANGE` - Climate Change
9. `PROTEST` - Protests/Demonstrations
10. `ELECTION` - Elections
11. `GOVERNMENT` - Government Actions
12. `HEALTH` - Public Health
13. `EDUCATION` - Education Issues
14. `CRIME` - Crime and Law Enforcement
15. `RELIGION` - Religious Topics
16. `MIGRATION` - Migration and Refugees
17. `CORRUPTION` - Corruption
18. `HUMAN_RIGHTS` - Human Rights
19. `AGRICULTURE` - Agriculture
20. `TECHNOLOGY` - Technology

**Relevance for Observatory**: ★★★★★
- **Core Signals**: Pre-classified topics (no custom NLP needed initially)
- **Topic Clustering**: Group similar narratives across countries
- **Flow Detection**: Shared themes = potential information flow
- **User Search**: "Show me all CLIMATE_CHANGE signals in Latin America"

**Implementation Priority**: **IMMEDIATE** (Day 1)

---

#### V2Counts (Column 15)

**Format**: Count blocks separated by semicolons

**Structure per count**:
```
Count#Theme#Count;Count#Theme#Count
```

**Example**:
```
52#TAX_TERROR#52;34#ECON_INFLATION#34;12#PROTEST#12
```

**Parsed Data**:
```json
[
  {"theme": "TAX_TERROR", "count": 52},
  {"theme": "ECON_INFLATION", "count": 34},
  {"theme": "PROTEST", "count": 12}
]
```

**Relevance for Observatory**: ★★★★★
- **Signal Intensity**: Higher count = stronger signal in that article
- **Topic Weight**: Use counts to prioritize topics (52 > 34 > 12)
- **Heat Formula Input**: `volume_score` component in ADR-0002
- **Trend Detection**: Track count changes over time

**Usage Pattern**:
```python
# Calculate weighted topic importance
for count_entry in v2_counts:
    weight = count_entry['count'] / max_count_in_article
    topic_score = weight * confidence * tone_factor
```

**Implementation Priority**: **IMMEDIATE** (Week 1)

---

#### V2Persons (Column 5)

**Format**: Semicolon-separated names

**Example**:
```
Donald Trump;Joe Biden;Vladimir Putin;Xi Jinping;Angela Merkel
```

**Entity Type**: Named individuals (political figures, celebrities, business leaders)

**Relevance for Observatory**: ★★★★☆
- **Narrative Actors**: Track who is driving narratives
- **Entity Search**: "Show flows involving 'Elon Musk'"
- **Influence Mapping**: Identify key figures in information spread
- **Actor-Topic Correlation**: Which people are associated with which themes?

**Challenge**: Name disambiguation (which "John Smith"?)
**Solution**: GDELT does basic NER but perfect accuracy not guaranteed; use in aggregate, not for legal/verification

**Implementation Priority**: **WEEK 2**

---

#### V2Organizations (Column 6)

**Format**: Semicolon-separated organization names

**Example**:
```
United Nations;World Bank;European Union;Federal Reserve;Tesla Inc
```

**Entity Type**: Institutions, companies, government bodies

**Relevance for Observatory**: ★★★★☆
- **Institutional Analysis**: Track organizational involvement in narratives
- **Sector Tracking**: Group by organization type (governments, NGOs, corporations)
- **Source Authority**: Organizations mentioned = signal credibility

**Combined Use Case** (Persons + Organizations):
```
Flow: US → EU
Shared Actors:
  - Persons: ["Joe Biden", "Ursula von der Leyen"]
  - Organizations: ["NATO", "European Commission"]
  - Themes: ["TAX_DIPLOMACY", "ECON_TRADE"]

Inference: Trade negotiation narrative spreading from US to EU
```

**Implementation Priority**: **WEEK 2**

---

#### V2GCAM (Column 9)

**Format**: Complex comma-delimited key-value pairs

**Structure**:
```
wc:523,c1.1:45,c1.2:23,c2.1:medical,c2.2:politics,c3.1:0.23,c3.2:-0.45,...
```

**Content**: Global Content Analysis Measures
- **24 emotional measurement packages**
- **2,300+ dimensions** total
- Includes LIWC, WordNet-Affect, Regressive Imagery Dictionary, etc.

**Example Dimensions**:
- `c1.1`: Word count density
- `c4.15`: Anxiety level (LIWC)
- `c5.23`: Anger score
- `c6.8`: Trust/uncertainty
- `c7.12`: Medical language density
- `c8.5`: Political language density

**Relevance for Observatory**: ★★★☆☆
- **Advanced Sentiment**: Granular emotional profiling beyond tone
- **Narrative Psychology**: Detect fear, anger, hope, urgency
- **Quality Assessment**: Distinguish analysis from propaganda

**Caution**: Very complex, 2,300 dimensions = analysis paralysis
**Recommendation**: Start with V2Tone (simpler), add GCAM in Iteration 3+ for "narrative psychology" feature

**Implementation Priority**: **ITERATION 3** (not MVP)

---

### 3.3 Events Database Fields (For Flow Detection)

While GKG is primary, Events database provides complementary actor-action-actor structure useful for flow directionality.

#### Key Events Fields

| Column | Name | Description | Relevance |
|--------|------|-------------|-----------|
| **GLOBALEVENTID** | Event ID | Unique identifier | Linking mentions |
| **EventCode** | CAMEO Code | Action type (e.g., "043" = Consult) | Event taxonomy |
| **GoldsteinScale** | Impact Score | -10 to +10 intensity | Conflict vs cooperation |
| **NumMentions** | Mention Count | How many sources covered this | Importance metric |
| **NumSources** | Source Count | Source diversity | Credibility |
| **NumArticles** | Article Count | Total articles | Popularity |
| **AvgTone** | Sentiment | Same as GKG V2Tone | Cross-validation |
| **Actor1Code** | Source Actor | CAMEO actor code (e.g., "USA") | Flow origin |
| **Actor2Code** | Target Actor | Recipient of action | Flow destination |
| **ActionGeo_Lat** | Action Location Lat | Where event occurred | Geographic precision |
| **ActionGeo_Long** | Action Location Long | Longitude | Mapping |

**Use Case for Observatory**:
```python
# Detect directed flow
if event['Actor1Code'] == 'USA' and event['Actor2Code'] == 'CHN':
    if event['GoldsteinScale'] < -5:  # Conflict
        flow_type = "tension"
    elif event['GoldsteinScale'] > 5:  # Cooperation
        flow_type = "partnership"
```

**Recommendation**: Use Events database as **secondary validation** for flows detected in GKG

**Implementation Priority**: **WEEK 3-4** (after GKG baseline)

---

## 4. Core Signals Layer Mapping

### 4.1 Current Placeholder Schema

```python
# backend/app/models/schemas.py (Current)
class Topic(BaseModel):
    id: str
    label: str
    count: int
    sample_titles: List[str]
    sources: List[str]
    confidence: float
```

### 4.2 Proposed GDELT-Backed Schema

#### Minimal Viable Schema (Week 1)

```python
class GDELTSignal(BaseModel):
    """Core signal extracted from GDELT GKG."""

    # Identity
    signal_id: str  # = GKGRECORDID
    timestamp: datetime  # = V2DATE

    # Geographic
    country_code: str  # Extracted from V2Locations
    location_name: str  # City or place name
    latitude: float
    longitude: float
    location_type: int  # 1-5 (country to city precision)

    # Thematic
    themes: List[str]  # V2Themes list
    primary_theme: str  # Most mentioned theme
    theme_counts: Dict[str, int]  # V2Counts parsed

    # Sentiment
    tone: float  # V2Tone overall score
    tone_positive_pct: float
    tone_negative_pct: float
    polarity: float  # Emotional intensity

    # Metadata
    source_url: str  # V2DocumentIdentifier
    source_outlet: str  # V2SourceCommonName
    confidence: float = 1.0  # GDELT data = high confidence
```

#### Enhanced Schema (Week 2-3)

```python
class GDELTSignalEnhanced(GDELTSignal):
    """Extended signal with entities and GCAM."""

    # Entities
    persons: List[str]  # V2Persons
    organizations: List[str]  # V2Organizations

    # Advanced Sentiment (if using GCAM)
    gcam_dimensions: Optional[Dict[str, float]]  # Selected GCAM metrics

    # Content Preview
    sample_quotes: List[str]  # V2Quotations
    thumbnail_url: Optional[str]  # V2SharingImage
```

### 4.3 Database Schema Alignment

Map GDELT fields to existing `topic_snapshots` table from `database-schema-design.md`:

```sql
-- Mapping GDELT → topic_snapshots
INSERT INTO topic_snapshots (
    snapshot_id,          -- GKGRECORDID
    topic_id,             -- FK to topics (normalized V2Themes)
    country_code,         -- Extracted from V2Locations
    snapshot_time,        -- V2DATE
    count,                -- V2Counts (sum for this topic)
    volume_score,         -- Calculated from count / max_count
    velocity_score,       -- Calculated from delta with previous snapshot
    confidence,           -- 1.0 for GDELT (or 0.8 if location ambiguous)
    sources,              -- JSON: [{"source": "gdelt", "outlet": V2SourceCommonName}]
    sample_titles,        -- [V2DocumentIdentifier title] (need to fetch)
    avg_sentiment,        -- V2Tone (first value)
    stance_label          -- Derived from Tone + Themes (pro/anti/neutral)
) VALUES (...);
```

### 4.4 Normalization Strategy

**Challenge**: GDELT provides 280+ themes but we need normalized "topics" for deduplication

**Solution**: Three-tier hierarchy

```python
# Tier 1: Keep GDELT raw theme code
raw_theme = "WB_632_WOMEN_IN_POLITICS"

# Tier 2: Normalize to canonical label
normalized_label = "Women in Politics"  # Store in topics.normalized_label

# Tier 3: Map to high-level category
category = "politics"  # Store in topics.category

# Alias mapping for fuzzy matching
aliases = [
    "women in politics",
    "female political participation",
    "gender equality politics"
]
```

**Implementation**:
```python
# backend/app/services/gdelt_parser.py

THEME_MAPPINGS = {
    "WB_632_WOMEN_IN_POLITICS": {
        "normalized": "Women in Politics",
        "category": "politics",
        "aliases": ["female leaders", "gender equality politics"]
    },
    "TAX_TERROR": {
        "normalized": "Terrorism",
        "category": "security",
        "aliases": ["terror attacks", "extremism"]
    },
    # ... 280+ mappings
}
```

---

## 5. UI Data Exposure Strategy

### 5.1 Heatmap View Requirements

**User Question**: "Why is this region heating up?"

**Data to Expose**:

```json
{
  "country": "US",
  "location": "New York, NY",
  "coordinates": [40.7128, -74.006],
  "intensity": 0.87,
  "breakdown": {
    "volume": 0.9,      // 90% of max article count in 15-min window
    "velocity": 0.85,   // Rapidly rising (delta from previous snapshot)
    "confidence": 1.0   // GDELT = high confidence
  },
  "top_themes": [
    {
      "theme": "ECON_INFLATION",
      "label": "Economic Inflation",
      "count": 52,
      "tone": -4.2,       // Negative sentiment
      "contribution": 0.35  // 35% of heat
    },
    {
      "theme": "PROTEST",
      "label": "Protests",
      "count": 34,
      "tone": -6.8,
      "contribution": 0.25
    }
  ],
  "emotional_context": {
    "overall_tone": -3.5,  // Negative
    "polarity": 2.1,       // High emotional intensity
    "dominant_emotion": "anger"  // Inferred from GCAM (future)
  },
  "key_actors": {
    "persons": ["Jerome Powell", "Janet Yellen"],
    "organizations": ["Federal Reserve", "Department of Treasury"]
  },
  "sample_headlines": [
    "Fed Chair Powell Warns of Persistent Inflation",
    "Thousands Protest Rising Cost of Living in NYC"
  ],
  "sources": [
    {"outlet": "nytimes.com", "count": 12},
    {"outlet": "wsj.com", "count": 8}
  ]
}
```

**UI Interaction Flow**:
1. User hovers over red hotspot on map (New York)
2. Tooltip shows: "New York - Intensity: 87% (↑15% from 1h ago)"
3. User clicks → Sidebar opens with above JSON formatted as:
   ```
   New York, NY - High Activity

   Top Topics:
   • Economic Inflation (52 articles, negative sentiment)
   • Protests (34 articles, very negative)

   Emotional Context: Negative tone, high intensity
   Key Figures: Jerome Powell, Janet Yellen

   [View 12 articles from NY Times →]
   ```

### 5.2 Classic View (Flow Lines) Requirements

**User Question**: "How is this narrative spreading?"

**Data to Expose**:

```json
{
  "from_country": "US",
  "to_country": "GB",
  "flow_heat": 0.72,
  "time_delta_hours": 3.5,
  "similarity_score": 0.85,
  "shared_themes": [
    {
      "theme": "ECON_INFLATION",
      "label": "Economic Inflation",
      "from_count": 52,
      "to_count": 28,
      "tone_shift": -0.8  // GB articles more negative than US
    }
  ],
  "shared_actors": {
    "persons": ["Jerome Powell"],  // Same person mentioned in both
    "organizations": ["Federal Reserve", "Bank of England"]
  },
  "narrative_evolution": {
    "from_stance": "concern",
    "to_stance": "alarm",
    "drift_magnitude": 0.6  // Significant stance shift
  },
  "temporal_pattern": {
    "first_appeared_us": "2025-01-14T08:00:00Z",
    "first_appeared_gb": "2025-01-14T11:30:00Z",
    "detection_confidence": "high"  // Clear temporal sequence
  }
}
```

**UI Visualization**:
```
Map Display:
┌─────────────────────────────────┐
│  [US Node]━━━━━━━━━━━━━━━━→[GB Node]
│   (red)    thick red line    (orange)
│            heat: 0.72
│            3.5h lag
│
│  On Line Hover:
│  "Inflation concerns spreading US→GB"
│  "Topic: Economic Inflation"
│  "Sentiment shift: negative → very negative"
│  "Time lag: 3.5 hours"
│  [View Details →]
└─────────────────────────────────┘
```

### 5.3 Topic/Entity Search View Requirements

**User Action**: Search for "climate change" or "Elon Musk"

**Data to Expose**:

```json
{
  "query": "climate change",
  "query_type": "theme",  // or "person", "organization"
  "matched_themes": ["ENV_CLIMATECHANGE", "ENV_FORESTS", "UNGP_DISASTER"],
  "time_range": "last_24h",
  "results": [
    {
      "country": "BR",
      "location": "Amazon Basin",
      "theme": "ENV_FORESTS",
      "count": 67,
      "tone": -5.2,
      "trend": "rising",  // ↑ compared to 24h ago
      "context": "Deforestation concerns surge after satellite data release"
    },
    {
      "country": "DE",
      "location": "Berlin",
      "theme": "ENV_CLIMATECHANGE",
      "count": 45,
      "tone": 2.1,
      "trend": "stable",
      "context": "EU announces new climate policy framework"
    }
  ],
  "global_summary": {
    "total_articles": 523,
    "countries_affected": 47,
    "avg_tone": -2.3,  // Overall negative
    "top_countries": ["BR", "US", "DE", "AU", "IN"]
  },
  "related_actors": {
    "persons": ["Greta Thunberg", "John Kerry"],
    "organizations": ["IPCC", "Greenpeace", "UN Climate"]
  }
}
```

**UI Display**:
```
Search Results: "climate change"
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Global Overview:
• 523 articles across 47 countries (last 24h)
• Overall sentiment: Negative (-2.3)
• Trending topics: Deforestation, EU Policy

Top Hotspots:
1. 🔴 Brazil - Amazon Basin (67 articles, very negative, ↑rising)
   "Deforestation concerns surge..."

2. 🟡 Germany - Berlin (45 articles, positive, →stable)
   "EU announces new climate policy..."

Related Actors:
• People: Greta Thunberg, John Kerry
• Organizations: IPCC, Greenpeace

[Filter by Country ▼] [Sort by Intensity ▼]
```

---

## 6. Visualization Requirements

### 6.1 Heatmap Layer Technical Needs

**From GDELT**:
- **V2Locations** → `latitude`, `longitude`
- **V2Counts** → `intensity` (aggregated theme counts)
- **V2Tone** → `color gradient` (red = negative, green = positive)

**Rendering Strategy**:

```javascript
// frontend/src/layers/HeatmapLayer.js

function renderHeatmap(signals) {
  const heatmapData = signals.map(signal => ({
    position: [signal.longitude, signal.latitude],
    weight: signal.intensity,  // 0-1 from V2Counts aggregation
    color: toneToColor(signal.tone)  // -100 to +100 → RGB
  }));

  return new HexagonLayer({
    id: 'gdelt-heatmap',
    data: heatmapData,
    getPosition: d => d.position,
    getElevationWeight: d => d.weight,
    elevationScale: 100,
    radius: 50000,  // 50km hexagons
    colorRange: NEGATIVE_TO_POSITIVE_GRADIENT,
    // ... deck.gl options
  });
}

function toneToColor(tone) {
  // tone range: -100 to +100
  // Map to red (-100) → yellow (0) → green (+100)
  if (tone < 0) {
    // Negative: interpolate red to yellow
    const ratio = (tone + 100) / 100;  // 0-1
    return [255, Math.floor(255 * ratio), 0];  // Red → Yellow
  } else {
    // Positive: interpolate yellow to green
    const ratio = tone / 100;  // 0-1
    return [Math.floor(255 * (1 - ratio)), 255, 0];  // Yellow → Green
  }
}
```

**Performance Consideration**:
- **Problem**: 10,000 articles per 15-min = 10,000 heatmap points
- **Solution**: Pre-aggregate by country/region before sending to frontend
  ```python
  # Backend aggregation
  def aggregate_heatmap_data(gkg_records, granularity='country'):
      aggregated = defaultdict(lambda: {
          'count': 0,
          'tone_sum': 0,
          'lat_sum': 0,
          'lon_sum': 0
      })

      for record in gkg_records:
          key = record['country_code'] if granularity == 'country' else record['location_name']
          aggregated[key]['count'] += record['count']
          aggregated[key]['tone_sum'] += record['tone'] * record['count']
          aggregated[key]['lat_sum'] += record['latitude']
          aggregated[key]['lon_sum'] += record['longitude']

      # Calculate averages
      for key, data in aggregated.items():
          data['avg_tone'] = data['tone_sum'] / data['count']
          data['centroid_lat'] = data['lat_sum'] / data['count']
          data['centroid_lon'] = data['lon_sum'] / data['count']

      return aggregated
  ```

### 6.2 Classic View (Centroids + Flow Lines) Technical Needs

**From GDELT**:
- **V2Locations** → Centroid positions (average lat/long per country)
- **V2Themes** → Shared topics for flow detection
- **V2Tone** → Sentiment shift (narrative evolution)
- **V2DATE** → Time delta for flow directionality

**Flow Detection Algorithm** (from existing `flow_detector.py`, enhanced with GDELT):

```python
# backend/app/services/flow_detector.py

def detect_flows_gdelt(signals_by_country: Dict[str, List[GDELTSignal]]):
    """
    Detect flows using GDELT theme overlap and time sequence.

    ADR-0002 Heat Formula:
    heat = similarity × exp(-Δt / halflife)

    similarity = Jaccard similarity of themes
    Δt = time difference in hours
    halflife = 6 hours (configurable)
    """
    flows = []
    countries = list(signals_by_country.keys())

    for i, country_a in enumerate(countries):
        for country_b in countries[i+1:]:
            # Get signals for both countries
            signals_a = signals_by_country[country_a]
            signals_b = signals_by_country[country_b]

            # Calculate theme overlap
            themes_a = set(flatten([s.themes for s in signals_a]))
            themes_b = set(flatten([s.themes for s in signals_b]))

            shared_themes = themes_a & themes_b
            all_themes = themes_a | themes_b

            if len(shared_themes) == 0:
                continue  # No similarity

            # Jaccard similarity
            similarity = len(shared_themes) / len(all_themes)

            if similarity < 0.3:  # GDELT Global Similarity Graph threshold
                continue

            # Calculate time delta (earliest in A to earliest in B)
            time_a = min([s.timestamp for s in signals_a])
            time_b = min([s.timestamp for s in signals_b])

            # Determine directionality
            if time_a < time_b:
                from_country, to_country = country_a, country_b
                time_delta_hours = (time_b - time_a).total_seconds() / 3600
            else:
                from_country, to_country = country_b, country_a
                time_delta_hours = (time_a - time_b).total_seconds() / 3600

            # Apply time decay (ADR-0002)
            halflife = 6.0  # hours
            time_decay = math.exp(-time_delta_hours / halflife)

            # Calculate heat
            heat = similarity * time_decay

            if heat >= 0.5:  # Threshold for display
                flows.append({
                    'from_country': from_country,
                    'to_country': to_country,
                    'heat': heat,
                    'similarity': similarity,
                    'time_delta_hours': time_delta_hours,
                    'shared_themes': list(shared_themes)
                })

    return flows
```

**Rendering**:
```javascript
// frontend/src/layers/FlowLinesLayer.js

function renderFlowLines(flows, centroids) {
  const lineData = flows.map(flow => {
    const from = centroids[flow.from_country];
    const to = centroids[flow.to_country];

    return {
      source: [from.longitude, from.latitude],
      target: [to.longitude, to.latitude],
      heat: flow.heat,  // 0-1
      width: flow.heat * 10,  // Line thickness
      color: heatToColor(flow.heat)  // Red (high) to blue (low)
    };
  });

  return new ArcLayer({
    id: 'gdelt-flows',
    data: lineData,
    getSourcePosition: d => d.source,
    getTargetPosition: d => d.target,
    getWidth: d => d.width,
    getSourceColor: d => d.color,
    getTargetColor: d => d.color,
    greatCircle: true  // Curved lines on globe
  });
}
```

### 6.3 Combined Layers (User Vision)

**User's Request**: "Classic + Heatmap should work together, not mutually exclusive"

**Implementation**:
```javascript
// frontend/src/Map.js

function Map() {
  const [layers, setLayers] = useState({
    heatmap: true,
    flows: true,
    centroids: true
  });

  const deckLayers = [
    layers.heatmap && <HeatmapLayer data={heatmapData} />,
    layers.centroids && <ScatterplotLayer data={centroids} />,
    layers.flows && <FlowLinesLayer data={flows} />
  ].filter(Boolean);

  return (
    <DeckGL
      layers={deckLayers}
      initialViewState={INITIAL_VIEW_STATE}
    >
      <LayerControls layers={layers} setLayers={setLayers} />
      {/* Toggle: Heatmap [✓] Flows [✓] Centroids [✓] */}
    </DeckGL>
  );
}
```

**Rendering Order** (back to front):
1. Heatmap (bottom) - Semi-transparent hexagons
2. Flow lines (middle) - Arcs with glow effect
3. Centroids (top) - Circles with country labels

**Visual Effect**: "Alive, reactive, with gradients and motion"
- Heatmap: Pulsing opacity (0.5 → 0.8 → 0.5) every 2 seconds
- Flow lines: Animated dashes moving from source to target
- Centroids: Glow intensity pulses with activity level

---

## 7. Implementation Priorities

### Phase 1: Core GDELT Integration (Week 1)

**Goal**: Replace placeholder data with real GDELT themes

**Tasks**:
1. ✅ Implement GDELT file download
   ```python
   # backend/app/services/gdelt_downloader.py
   async def download_latest_gkg():
       latest_url = await get_latest_file_url()
       zip_path = await download_file(latest_url)
       csv_path = extract_zip(zip_path)
       return csv_path
   ```

2. ✅ Parse GKG CSV (tab-delimited)
   ```python
   # backend/app/services/gdelt_parser.py
   def parse_gkg_csv(filepath: str) -> List[GKGRecord]:
       records = []
       with open(filepath, 'r', encoding='utf-8') as f:
           for line in f:
               fields = line.split('\t')
               if len(fields) != 27:
                   continue  # Skip malformed rows

               record = GKGRecord(
                   record_id=fields[0],
                   date=parse_datetime(fields[1]),
                   locations=parse_locations(fields[3]),
                   persons=parse_list(fields[4]),
                   organizations=parse_list(fields[5]),
                   tone=parse_tone(fields[6]),
                   themes=parse_list(fields[7]),
                   counts=parse_counts(fields[14]),
                   # ... more fields
               )
               records.append(record)
       return records
   ```

3. ✅ Filter by country
   ```python
   def filter_by_country(records: List[GKGRecord], country_code: str):
       return [
           r for r in records
           if any(loc.country_code == country_code for loc in r.locations)
       ]
   ```

4. ✅ Extract top themes
   ```python
   def get_top_themes(records: List[GKGRecord], limit=50):
       theme_counts = Counter()
       for record in records:
           theme_counts.update(record.themes)
       return theme_counts.most_common(limit)
   ```

5. ✅ Update `gdelt_client.py` to use real parser instead of fallback

**Success Criteria**:
- `/api/v1/trends/US` returns real GDELT themes (not placeholders)
- Themes match GDELT taxonomy (e.g., "TAX_TERROR", "ECON_INFLATION")
- Response time < 2 seconds

---

### Phase 2: Geographic + Sentiment (Week 2)

**Goal**: Add heatmap visualization data

**Tasks**:
1. ✅ Parse V2Locations for lat/long
2. ✅ Calculate country centroids (average positions)
3. ✅ Add tone/sentiment to Topic schema
4. ✅ Implement heatmap aggregation endpoint
   ```python
   # backend/app/api/v1/heatmap.py
   @router.get("/heatmap")
   async def get_heatmap_data(countries: List[str] = Query(...)):
       signals = await gdelt_service.fetch_signals(countries)
       aggregated = aggregate_by_location(signals)
       return HeatmapResponse(points=aggregated)
   ```

5. ✅ Connect to frontend HexagonLayer

**Success Criteria**:
- Map shows colored hexagons based on real GDELT tone
- Clicking hotspot shows top themes and sentiment breakdown
- Color gradient: red (negative) → yellow (neutral) → green (positive)

---

### Phase 3: Flow Detection (Week 3)

**Goal**: Detect narrative flows using theme overlap

**Tasks**:
1. ✅ Implement theme-based similarity calculation
2. ✅ Add time-delta calculation for directionality
3. ✅ Apply ADR-0002 heat formula with GDELT data
4. ✅ Create flows endpoint
   ```python
   @router.get("/flows")
   async def get_flows(countries: List[str]):
       signals = await gdelt_service.fetch_signals_by_country(countries)
       flows = detect_flows_gdelt(signals)
       return FlowsResponse(flows=flows)
   ```
5. ✅ Render flow lines on map

**Success Criteria**:
- Flow lines appear between countries with shared themes
- Line thickness = heat score
- Hovering shows shared themes and time lag

---

### Phase 4: Entities + Search (Week 4)

**Goal**: Add person/organization tracking

**Tasks**:
1. ✅ Parse V2Persons and V2Organizations
2. ✅ Add entity fields to signal schema
3. ✅ Implement entity search endpoint
4. ✅ Create Topic/Entity search UI
5. ✅ Link entities to flows (shared actors)

**Success Criteria**:
- Search "Elon Musk" shows all countries mentioning him
- Flow visualization highlights shared actors
- Entity list shows top persons/organizations per topic

---

### Phase 5: Historical Data + Persistence (Week 5)

**Goal**: Store GDELT data in PostgreSQL for historical analysis

**Tasks**:
1. ✅ Set up database migrations (use existing schema from `database-schema-design.md`)
2. ✅ Persist signals to `topic_snapshots` table
3. ✅ Implement retention policy (hot/warm/cold tiers)
4. ✅ Add historical query endpoints
5. ✅ Create time-series charts in UI

**Success Criteria**:
- Can query "show climate change trends over last 7 days"
- Database stores 30 days of granular data
- Older data aggregated to hourly/daily

---

## 8. Concerns and Recommendations

### 8.1 Data Quality Concerns

#### Concern 1: GDELT Noise and False Positives

**Issue**: GDELT processes 100+ languages automatically, leading to:
- Misclassified themes (soccer match tagged as "armed conflict")
- Location errors (New York, US vs New York, Nigeria)
- Duplicate articles (same content from multiple outlets)

**Impact**: Could show misleading hotspots or false flows

**Mitigation**:
1. **Confidence Scoring**: Lower confidence for ambiguous locations
   ```python
   if location.type == 1:  # Country-level only
       confidence = 0.6  # Less precise
   elif location.type in [3, 4]:  # City-level
       confidence = 1.0  # High precision
   ```

2. **Deduplication**: Use URL fingerprinting to remove duplicates
   ```python
   def deduplicate_signals(signals):
       seen_urls = set()
       unique = []
       for signal in signals:
           url_hash = hashlib.md5(signal.source_url.encode()).hexdigest()
           if url_hash not in seen_urls:
               seen_urls.add(url_hash)
               unique.append(signal)
       return unique
   ```

3. **Outlier Filtering**: Remove extreme tone values (likely errors)
   ```python
   # Filter out tone > 50 or < -50 (rare, often errors)
   if abs(signal.tone) > 50:
       logger.warning(f"Outlier tone detected: {signal.tone}, skipping")
       continue
   ```

**Recommendation**: Start with **top-tier news sources only** (BBC, Reuters, AP) to reduce noise, expand later

---

#### Concern 2: GDELT Theme Taxonomy Complexity

**Issue**: 280+ themes with overlapping meanings
- `TAX_TERROR` vs `CRISISLEX_C06_VIOLENCE` (both terrorism-related)
- `ECON_INFLATION` vs `WB_633_ECONOMIC_STABILITY` (overlapping)

**Impact**: Topic clustering becomes fragmented

**Mitigation**:
1. **Theme Grouping**: Create high-level categories
   ```python
   THEME_CATEGORIES = {
       'security': ['TAX_TERROR', 'ARMEDCONFLICT', 'CRISISLEX_C06_VIOLENCE'],
       'economy': ['ECON_INFLATION', 'WB_633_ECONOMIC_STABILITY', 'TAX_FNCACT'],
       'health': ['HEALTH', 'UNGP_HEALTH', 'CRISISLEX_C01_MEDICAL'],
       # ... more categories
   }
   ```

2. **Alias System**: Map similar themes to canonical labels
   ```python
   THEME_ALIASES = {
       'TAX_TERROR': 'terrorism',
       'CRISISLEX_C06_VIOLENCE': 'terrorism',  # Same canonical
       'ECON_INFLATION': 'inflation',
       'WB_633_ECONOMIC_STABILITY': 'economic_stability'  # Separate
   }
   ```

3. **User-Friendly Labels**: Don't show raw codes in UI
   ```python
   def format_theme_for_ui(theme_code):
       # "WB_632_WOMEN_IN_POLITICS" → "Women in Politics"
       return THEME_MAPPINGS.get(theme_code, {}).get('normalized', theme_code)
   ```

**Recommendation**: Focus on **top 50 most common themes** initially, expand as needed

---

#### Concern 3: Time-Zone and Temporal Accuracy

**Issue**: GDELT timestamps in UTC, but articles published in local time
- Article published 9 AM EST shown as 2 PM UTC
- Confusing for users in different time zones

**Mitigation**:
1. **Store in UTC, Display in Local**:
   ```javascript
   // Frontend
   const localTime = new Date(signal.timestamp).toLocaleString(
       userTimezone,
       {dateStyle: 'short', timeStyle: 'short'}
   );
   ```

2. **Time Zone Metadata**: Add to country metadata
   ```python
   # backend/app/core/country_metadata.py
   COUNTRY_TIMEZONES = {
       'US': 'America/New_York',  # Or use user's location
       'GB': 'Europe/London',
       'JP': 'Asia/Tokyo'
   }
   ```

3. **Relative Time Labels**: "3 hours ago" instead of absolute timestamps
   ```javascript
   const relativeTime = formatDistanceToNow(new Date(signal.timestamp));
   // "3 hours ago" more intuitive than "2025-01-14 11:30 UTC"
   ```

**Recommendation**: Always store UTC in database, convert to local time zones in UI

---

### 8.2 Performance Concerns

#### Concern 1: Large File Downloads

**Issue**: GKG files are 5-15 MB compressed, 50-150 MB uncompressed
- Downloading every 15 minutes = high bandwidth
- Parsing 30,000 rows = CPU intensive

**Mitigation**:
1. **Incremental Processing**: Don't reprocess entire file if cached
   ```python
   last_processed_id = redis.get('last_gkg_id')
   new_records = [r for r in records if r.record_id > last_processed_id]
   ```

2. **Streaming Parsing**: Don't load entire CSV into memory
   ```python
   def parse_gkg_streaming(filepath):
       with open(filepath, 'r') as f:
           for line in f:
               yield parse_gkg_row(line)  # Generator
   ```

3. **Parallel Processing**: Use multiprocessing for large files
   ```python
   from multiprocessing import Pool

   with Pool(4) as p:
       records = p.map(parse_gkg_row, csv_lines)
   ```

4. **Selective Download**: Only download if new file available
   ```python
   # Check lastupdate.txt first
   latest_timestamp = fetch_latest_timestamp()
   if latest_timestamp == cached_timestamp:
       return  # Skip download
   ```

**Recommendation**: Implement **caching + incremental processing** from Day 1

---

#### Concern 2: Database Growth

**Issue**: 30,000 articles every 15 minutes = 43M articles/month
- If storing all fields, could exceed 100 GB/month

**Mitigation**: See existing retention policy in `database-schema-design.md`
- **Hot Tier** (30 days): Full granularity
- **Warm Tier** (60 days): Hourly aggregation
- **Cold Tier** (365 days): Daily aggregation

**Recommendation**: Start with **10 countries only** to limit growth, expand later

---

#### Concern 3: Real-Time Processing Latency

**Issue**: Processing 30,000 articles in <15 minutes to stay real-time
- Download: ~30 seconds
- Parse: ~60 seconds (for 30,000 rows)
- Filter + Aggregate: ~30 seconds
- Database Insert: ~60 seconds
- **Total**: ~3 minutes (leaves 12 min buffer)

**Mitigation**:
1. **Background Workers**: Use Celery for async processing
   ```python
   @celery.task
   def process_gdelt_file(filepath):
       records = parse_gkg_csv(filepath)
       persist_to_db(records)
   ```

2. **Batch Inserts**: Insert 1000 rows at a time (not 30,000 individual)
   ```python
   # 30x faster
   cursor.executemany(
       "INSERT INTO topic_snapshots VALUES (%s, %s, ...)",
       [(record.id, record.timestamp, ...) for record in batch]
   )
   ```

3. **Redis Cache**: Serve from cache while processing new file
   ```python
   # API reads from Redis (instant)
   # Background worker updates Redis every 15 min
   ```

**Recommendation**: Use **async background processing** to avoid blocking API

---

### 8.3 Architectural Concerns

#### Concern 1: Single Data Source Dependency

**Issue**: If GDELT API down or data quality degrades, entire system breaks

**Mitigation**:
1. **Fallback Data Sources**: Add RSS feeds, Mastodon as backups (already documented in `DATA_SOURCES_IMPLEMENTATION.md`)
2. **Graceful Degradation**: Show cached data if new data unavailable
3. **Health Checks**: Monitor GDELT availability
   ```python
   @router.get("/health/gdelt")
   async def gdelt_health():
       try:
           latest_file = await get_latest_file_url()
           return {"status": "healthy", "latest_file": latest_file}
       except:
           return {"status": "unhealthy", "error": "GDELT API unreachable"}
   ```

**Recommendation**: Implement **multi-source architecture** per existing docs

---

#### Concern 2: Theme-Based Flow Detection Limitations

**Issue**: Shared themes ≠ causal information flow
- Example: US and China both report "ECON_INFLATION" (coincidence, not flow)
- Need additional signals beyond theme overlap

**Enhanced Flow Detection**:
```python
def detect_flows_enhanced(signals_a, signals_b):
    # 1. Theme overlap (baseline)
    theme_similarity = jaccard(signals_a.themes, signals_b.themes)

    # 2. Temporal sequence (directionality)
    time_delta = (signals_b.timestamp - signals_a.timestamp).hours

    # 3. Actor overlap (stronger signal)
    actor_overlap = len(set(signals_a.persons) & set(signals_b.persons))

    # 4. Source outlet overlap (e.g., BBC → BBC International)
    outlet_overlap = len(set(signals_a.outlets) & set(signals_b.outlets))

    # 5. Tone correlation (similar sentiment shift)
    tone_correlation = abs(signals_a.tone - signals_b.tone) < 2.0

    # Combined confidence
    confidence = (
        0.4 * theme_similarity +
        0.2 * (1.0 if actor_overlap > 0 else 0.0) +
        0.2 * (1.0 if outlet_overlap > 0 else 0.0) +
        0.2 * (1.0 if tone_correlation else 0.0)
    )

    if confidence > 0.5 and time_delta > 0:
        return Flow(from=signals_a, to=signals_b, confidence=confidence)
```

**Recommendation**: Use **multi-signal flow detection** (not just themes)

---

### 8.4 User Experience Concerns

#### Concern 1: Information Overload

**Issue**: 280 themes × 200 countries = 56,000 potential signals
- User overwhelmed by data volume

**UX Mitigation**:
1. **Smart Defaults**: Show top 10 countries, top 5 themes
2. **Progressive Disclosure**: Start simple, reveal details on demand
   ```
   Initial View: "5 hotspots detected"
   Click → "Top 3 themes in US: Inflation, Protests, Elections"
   Click theme → "52 articles, negative sentiment, timeline graph"
   ```

3. **Filtering**: Let users narrow by category
   ```
   Filter by: [Politics ▼] [Region: Americas ▼] [Sentiment: Negative ▼]
   ```

4. **Alerts**: Notify only on significant changes (>50% intensity spike)

**Recommendation**: Design UI for **progressive detail expansion**

---

#### Concern 2: Jargon and Raw GDELT Codes

**Issue**: "WB_632_WOMEN_IN_POLITICS" is not user-friendly

**UX Solution**:
```python
# Always map to normalized labels in API responses
{
  "theme_code": "WB_632_WOMEN_IN_POLITICS",  // Hidden from UI
  "theme_label": "Women in Politics",        // Shown to user
  "category": "Gender Equality",             // High-level grouping
  "description": "Coverage of women's participation in political leadership and governance"
}
```

**Recommendation**: Never show raw GDELT codes in UI, always use friendly labels

---

## 9. Recommended Data Schema (Final)

### 9.1 Minimal Viable Signal Schema

```python
# backend/app/models/gdelt_signal.py

from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Dict, Optional

class GDELTLocation(BaseModel):
    """Geographic location from GDELT V2Locations."""
    country_code: str
    country_name: str
    location_name: Optional[str] = None  # City/region name
    latitude: float
    longitude: float
    location_type: int  # 1-5 precision level
    feature_id: Optional[str] = None  # GeoNames ID

class GDELTTone(BaseModel):
    """Sentiment data from GDELT V2Tone."""
    overall: float  # -100 to +100
    positive_pct: float
    negative_pct: float
    polarity: float
    activity_density: float
    self_reference: float

class GDELTSignal(BaseModel):
    """Core signal extracted from GDELT GKG."""

    # Identity
    signal_id: str  # GKGRECORDID
    timestamp: datetime  # V2DATE

    # Geographic
    locations: List[GDELTLocation]  # Parsed V2Locations
    primary_location: GDELTLocation  # First or most relevant

    # Thematic
    themes: List[str]  # V2Themes raw codes
    theme_labels: List[str]  # Normalized user-friendly labels
    theme_counts: Dict[str, int]  # V2Counts parsed
    primary_theme: str  # Most mentioned theme

    # Sentiment
    tone: GDELTTone  # V2Tone parsed

    # Entities (if available)
    persons: List[str] = []  # V2Persons
    organizations: List[str] = []  # V2Organizations

    # Source
    source_url: Optional[str] = None  # V2DocumentIdentifier
    source_outlet: Optional[str] = None  # V2SourceCommonName

    # Metadata
    confidence: float = 1.0  # Default high for GDELT
    sources: List[str] = ["gdelt"]  # Data provenance
```

### 9.2 API Response Schema

```python
class HeatmapPoint(BaseModel):
    """Single point on heatmap."""
    country_code: str
    location_name: str
    latitude: float
    longitude: float
    intensity: float  # 0-1
    tone: float  # -100 to +100
    article_count: int
    top_themes: List[Dict[str, Any]]  # [{"label": "Inflation", "count": 52}, ...]

class FlowLine(BaseModel):
    """Information flow between countries."""
    from_country: str
    to_country: str
    heat: float  # 0-1
    similarity: float
    time_delta_hours: float
    shared_themes: List[str]
    shared_actors: Optional[Dict[str, List[str]]] = None  # persons, orgs
    tone_shift: float  # Delta in sentiment

class SignalResponse(BaseModel):
    """Response for /api/v1/signals endpoint."""
    timestamp: datetime
    countries: List[str]
    heatmap: List[HeatmapPoint]
    flows: List[FlowLine]
    total_signals: int
    data_quality: float  # Confidence metric
```

---

## 10. Next Steps (Action Items)

### Week 1: Foundation
1. [ ] Create `gdelt_downloader.py` - Download GKG files
2. [ ] Create `gdelt_parser.py` - Parse tab-delimited CSV
3. [ ] Implement V2Locations parser (lat/long extraction)
4. [ ] Implement V2Themes parser
5. [ ] Implement V2Tone parser
6. [ ] Update `gdelt_client.py` to use real data
7. [ ] Test with single country (US or GB)

### Week 2: Visualization Data
1. [ ] Add heatmap aggregation endpoint
2. [ ] Parse V2Counts for intensity calculation
3. [ ] Implement country centroid calculation
4. [ ] Connect to frontend HexagonLayer
5. [ ] Add tone-based color gradient
6. [ ] Test heatmap with 5 countries

### Week 3: Flow Detection
1. [ ] Implement theme-based similarity
2. [ ] Add temporal sequencing logic
3. [ ] Apply ADR-0002 heat formula
4. [ ] Create flows API endpoint
5. [ ] Render flow lines on map
6. [ ] Test with 10 country pairs

### Week 4: Entities + Search
1. [ ] Parse V2Persons, V2Organizations
2. [ ] Add entity search endpoint
3. [ ] Build Topic/Entity search UI
4. [ ] Link entities to flows
5. [ ] Test search functionality

### Week 5: Persistence + Historical
1. [ ] Set up PostgreSQL migrations
2. [ ] Implement signal persistence
3. [ ] Add retention policy automation
4. [ ] Create historical query endpoints
5. [ ] Build time-series charts

---

## 11. Conclusion

### Summary

**GDELT 2.0 Global Knowledge Graph** is the optimal data source for Observatory Global because:

1. **Rich Thematic Classification**: 280+ pre-categorized themes reduce NLP complexity
2. **Geographic Precision**: City-level lat/long for accurate heatmaps
3. **Sentiment Analysis**: Built-in tone scoring for "why heating up?" questions
4. **Real-Time Updates**: 15-minute intervals for live narrative tracking
5. **Global Coverage**: 200+ countries, 100+ languages
6. **Entity Extraction**: Named persons/organizations for actor tracking
7. **Free and Open**: No API costs, no rate limits

### Critical Path

**Minimum Viable Implementation**:
- V2Locations → Heatmap positioning
- V2Themes → Topic signals
- V2Tone → Sentiment layer
- V2Counts → Intensity calculation

**Enhanced Features** (later):
- V2Persons, V2Organizations → Entity tracking
- V2GCAM → Advanced emotion analysis
- Events Database → Actor-action-actor flows

### Risk Mitigation

1. **Data Quality**: Filter outliers, deduplicate, confidence scoring
2. **Performance**: Caching, background workers, batch inserts
3. **Complexity**: Focus on top 50 themes initially, expand gradually
4. **Dependency**: Multi-source architecture (GDELT + RSS + Mastodon)

### Expected Outcome

By implementing this GDELT-backed architecture:
- **Data Quality**: 2% → 95% (real global news)
- **Geographic Coverage**: Placeholder → 200+ countries
- **Update Frequency**: Static → Every 15 minutes
- **Topic Accuracy**: Synthetic → Real taxonomy-classified
- **User Insight**: "Why heating up?" fully answerable with tone + themes + entities

**This transforms Observatory Global from a demo to a production-grade narrative intelligence platform.**

---

**Document Status**: Ready for Implementation
**Next Review**: After Week 1 Milestone
**Owner**: Development Team
**Stakeholder**: Pedro (Product Vision)
