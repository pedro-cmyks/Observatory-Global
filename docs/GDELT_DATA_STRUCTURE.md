# GDELT Data Structure & Extraction Plan

## 📊 What is GDELT?

**GDELT (Global Database of Events, Language, and Tone)** is the world's largest open database of human society. It monitors print, broadcast, and web news from nearly every corner of every country in 100+ languages, every moment of every day.

**Update Frequency**: New files every 15 minutes (96 files per day)
**Coverage**: 200+ countries, 100+ languages
**Scale**: 400+ million records and growing
**Cost**: **FREE** (Public domain)

---

## 🗂️ GDELT Data Types

### 1. **GKG (Global Knowledge Graph)** ← **WE SHOULD USE THIS**
The most valuable for narrative tracking. Updated every 15 minutes.

**File Format**: `YYYYMMDDHHMMSS.gkg.csv.zip`
**Example**: `20251114020000.gkg.csv.zip`
**URL**: `http://data.gdeltproject.org/gdeltv2/20251114020000.gkg.csv.zip`

**Size per file**: ~5-15 MB compressed, ~50-150 MB uncompressed
**Rows per file**: ~10,000-30,000 articles

---

## 📋 GKG File Structure (27 Columns)

### **Core Columns We Should Use:**

| Column | Name | Description | Example | Use Case |
|--------|------|-------------|---------|----------|
| 1 | **GKGRECORDID** | Unique identifier | `20251114020000-T1` | Deduplication |
| 2 | **DATE** | Publication date | `20251114020000` | Temporal analysis |
| 4 | **V2Locations** | Geo-tagged locations | `1#CO#CO#-4.5,-74.3#Bogota#CO#CO#BOGOTA#-4.5#-74.3#CO#ADMC#US#424` | **Map visualization** |
| 5 | **V2Persons** | People mentioned | `Donald Trump;Joe Biden;Vladimir Putin` | **Narrative actors** |
| 6 | **V2Organizations** | Organizations | `United Nations;White House;Kremlin` | **Institutional analysis** |
| 7 | **V2Tone** | Sentiment scores | `-3.21,-3.21,50,2.5,25,3` | **Sentiment heatmaps** |
| 8 | **V2Themes** | GDELT taxonomy codes | `TAX_FNCACT;WB_632_WOMEN_IN_POLITICS` | **Topic clustering** |
| 9 | **V2GCAM** | Content metrics | `wc:523,c3.1:medical,c3.2:politics` | **Content quality** |
| 10 | **V2Locations** | Full location data | See detailed format below | **Geospatial analysis** |
| 15 | **Counts** | Mention frequencies | `52#TAX_TERROR#52;34#WB_ECONOMY#34` | **Topic intensity** |
| 16 | **V15Tone** | Enhanced sentiment | `-2.3,12.5,0.8` | **Emotion tracking** |
| 20 | **URLs** | Source article links | `https://www.bbc.com/news/...` | **Content preview** |
| 23 | **SharingImage** | Article thumbnail URL | `https://img.url/thumb.jpg` | **Visual preview** |

---

## 🔥 **Most Valuable Columns for Observatory Global**

### 1. **V2Themes** (Column 8) - Topic Classification
GDELT has **280+ predefined themes** that categorize content:

**Examples:**
```
TAX_FNCACT                    # Financial/Economic Activity
TAX_TERROR                    # Terrorism
ENV_CLIMATECHANGE             # Climate Change
SOC_POINTSOFVIEW              # Social Perspectives
WB_632_WOMEN_IN_POLITICS      # Women in Politics
ECON_INFLATION                # Inflation
ARMEDCONFLICT                 # Armed Conflict
MEDIA_MSM                     # Mainstream Media
SELF_HEALTH                   # Health Topics
```

**Format**: Semicolon-separated list
```
TAX_TERROR;ARMEDCONFLICT;SOC_POINTSOFVIEW
```

### 2. **V2Locations** (Column 4) - Geographic Data
**Format**: Type#Country#ADM1#Lat#Long#FeatureID#...

**Example**:
```
1#US#USNY#40.7128#-74.0060#New York#US#NY#NEW YORK#40.7128#-74.0060#US#PPLA#US#5128581
```

**Parsed:**
- Type: `1` (Location type)
- Country: `US`
- State: `USNY` (New York)
- Coordinates: `40.7128, -74.0060`
- City: `New York`
- Feature ID: `5128581` (GeoNames ID)

### 3. **V2Tone** (Column 7) - Sentiment Analysis
**Format**: `Tone,Positive,Negative,Polarity,ActivityRef,SelfRef`

**Example**: `-3.21,-3.21,50,2.5,25,3`
- **Tone**: `-3.21` (Overall sentiment, -100 to +100)
- **Positive**: `-3.21%` (Positive word percentage)
- **Negative**: `50%` (Negative word percentage)
- **Polarity**: `2.5` (Emotional polarity)
- **ActivityRef**: `25` (Activity references)
- **SelfRef**: `3` (Self-references)

### 4. **V2Persons** (Column 5) - Named Individuals
**Format**: Semicolon-separated list

**Example**:
```
Donald Trump;Joe Biden;Vladimir Putin;Xi Jinping
```

**Use**: Track narrative actors, identify key figures in flows

### 5. **Counts** (Column 15) - Theme Frequencies
**Format**: `Count#Theme#Count;Count#Theme#Count`

**Example**:
```
52#TAX_TERROR#52;34#WB_ECONOMY#34;12#ENV_CLIMATE#12
```
- `TAX_TERROR` mentioned **52 times**
- `WB_ECONOMY` mentioned **34 times**
- `ENV_CLIMATE` mentioned **12 times**

---

## 🎯 **Extraction Plan for Observatory Global**

### Phase 1: Basic GDELT Integration (Days 8-9)
**Goal**: Replace placeholder data with real GDELT themes

**Steps**:
1. Download latest GKG file every 15 minutes
2. Parse tab-delimited CSV
3. Extract **V2Themes** column (column 8)
4. Extract **V2Locations** column (4) for country filtering
5. Extract **Counts** column (15) for intensity
6. Extract **V2Tone** column (7) for sentiment

**Data Flow**:
```
GDELT GKG → Parse CSV → Filter by country → Extract themes →
Count frequencies → Create Topic objects → NLP processing →
FlowDetector → Frontend
```

**Example Output** (per country):
```json
{
  "country": "US",
  "topics": [
    {
      "label": "TAX_TERROR",
      "count": 152,
      "confidence": 0.89,
      "sentiment": -5.2
    },
    {
      "label": "WB_632_WOMEN_IN_POLITICS",
      "count": 87,
      "confidence": 0.76,
      "sentiment": 2.1
    }
  ]
}
```

### Phase 2: Enhanced Data (Days 10-11)
**Goal**: Add sentiment and named entities

**Additional Extraction**:
- **V2Persons**: Track narrative actors
- **V2Tone**: Add sentiment heatmaps
- **URLs**: Enable content preview
- **SharingImage**: Show thumbnails

### Phase 3: Full Integration (Week 2)
**Goal**: Multi-source correlation

**Features**:
- Cross-reference GDELT Events database
- Add actor analysis (governments, rebels, etc.)
- Temporal trend detection
- Geographic precision (city-level)

---

## 📦 Sample Real GDELT Record

Here's what ONE record looks like (simplified):

```csv
GKGRECORDID: 20251114020000-T52
DATE: 20251114020000
SourceCommonName: bbc.com
V2Locations: 1#US#USNY#40.71#-74.00#New York#US#NY
V2Persons: Donald Trump;Joe Biden
V2Organizations: White House;FBI;Department of Justice
V2Tone: -3.5,2.1,45.2,1.8,12,5
V2Themes: TAX_FNCACT;SOC_POINTSOFVIEW;LEADER
Counts: 24#TAX_FNCACT#24;15#SOC_POINTSOFVIEW#15
URLs: https://www.bbc.com/news/us-politics-52134567
```

**This ONE article gives us**:
- ✅ Location: New York, US (40.71, -74.00)
- ✅ People: Trump, Biden
- ✅ Organizations: White House, FBI, DOJ
- ✅ Sentiment: -3.5 (negative)
- ✅ Themes: Financial, Politics, Leadership
- ✅ Counts: 24 financial mentions, 15 opinion mentions
- ✅ Source URL for preview

**Multiply by 20,000 articles per 15-minute file = MASSIVE DATA**

---

## 💾 Storage & Performance

### Current State
- **Storage**: None (using placeholders)
- **Processing**: 0 GDELT files parsed
- **Data Quality**: 2% (fake data)

### After Real GDELT Integration
- **Storage**: ~500 MB/day (compressed CSVs)
- **Processing**: 96 files/day (15-min intervals)
- **Data Quality**: 95%+ (real global news)

### Caching Strategy
1. **Download** latest GKG file to `/data/gdelt/`
2. **Parse** and extract columns 4, 5, 7, 8, 15
3. **Filter** by country codes
4. **Aggregate** themes and counts
5. **Cache** in Redis (5-min TTL)
6. **Persist** to PostgreSQL for historical analysis

---

## 🚀 Implementation Priority

**IMMEDIATE (Day 8-9)**:
```python
# backend/app/services/gdelt_parser.py
class GDELTParser:
    def download_latest_gkg(self) -> str:
        """Download most recent GKG file"""

    def parse_gkg_csv(self, filepath: str) -> List[GKGRecord]:
        """Parse tab-delimited GKG CSV"""

    def extract_themes(self, record: GKGRecord, country: str) -> List[str]:
        """Extract V2Themes for a country"""

    def calculate_sentiment(self, record: GKGRecord) -> float:
        """Parse V2Tone to get sentiment score"""
```

**Use in GDELTClient**:
```python
async def fetch_trending_topics(self, country: str):
    # Download latest GKG
    gkg_file = await gdelt_parser.download_latest_gkg()

    # Parse CSV
    records = gdelt_parser.parse_gkg_csv(gkg_file)

    # Filter by country in V2Locations
    country_records = [r for r in records if country in r.v2_locations]

    # Extract and count themes
    theme_counts = Counter()
    for record in country_records:
        themes = gdelt_parser.extract_themes(record)
        theme_counts.update(themes)

    # Return top themes
    return [
        {
            "title": theme,
            "source": "gdelt",
            "count": count,
        }
        for theme, count in theme_counts.most_common(50)
    ]
```

---

## 📊 Expected Impact

**Current**:
- Topics: `["Political Developments in US", "Economic Indicators US"]` (fake)
- Counts: `[45, 38, 32, 28, 25]` (hardcoded)
- Coverage: 0 real articles

**After Real GDELT**:
- Topics: `["TAX_TERROR", "WB_ECONOMY", "ENV_CLIMATE", ...]` (real GDELT taxonomy)
- Counts: `[152, 87, 64, 43, 38]` (actual mention frequencies)
- Coverage: **20,000+ real articles every 15 minutes**

**This transforms Observatory Global from a demo to a production system.**

---

## 🔗 References

- **GDELT Documentation**: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook-V2.1.pdf
- **GKG Codebook**: http://data.gdeltproject.org/documentation/GDELT-Global_Knowledge_Graph_Codebook.pdf
- **Theme Taxonomy**: http://data.gdeltproject.org/documentation/CAMEO.Manual.1.1b3.pdf
- **Live File List**: http://data.gdeltproject.org/gdeltv2/lastupdate.txt

---

**Next Steps**: Implement `gdelt_parser.py` and replace placeholder data with real GDELT extraction. This should be the #1 priority after black screen fixes.
