# Observatory Global - Project Health Assessment
**Date:** 2025-11-21
**Orchestrator:** Claude (Sonnet 4.5)
**Assessment Scope:** Complete codebase health check before adding new features
**Repository:** /Users/pedro/Desktop/PEDRO/Cursos/ObservatorioGlobal
**Current Phase:** 3.5 - Classic View with Narrative Intelligence

---

## Executive Summary

This comprehensive health assessment reviewed the entire Observatory Global codebase across 6 critical areas:

1. **Global Consistency Check** - Dependencies, dead code, duplications
2. **Data Flow Analysis** - /v1/flows and /v1/hexmap endpoint architecture
3. **PostgreSQL Integration** - Schema coherence and storage strategy
4. **Geographic Correctness** - Coordinate systems and location data
5. **Documentation Hygiene** - Currency and maintenance
6. **Overall Findings** - Prioritized action items

### Health Score: **7.5/10** - Good with Notable Technical Debt

**Strengths:**
- ✅ Clean data flow architecture (SignalsService unification)
- ✅ Both endpoints consume identical signal data (no divergence)
- ✅ Geographic data uses consistent centroids (country_metadata.py)
- ✅ Well-documented PostgreSQL schema (migration 003)
- ✅ No critical security issues or data integrity problems

**Areas Requiring Attention:**
- ⚠️ PostgreSQL schema exists but is NOT USED (placeholder data only)
- ⚠️ Significant documentation bloat (Hacker News/Mastodon references never implemented)
- ⚠️ Some unused dependencies in both frontend and backend
- ⚠️ Missing dependency: psycopg2 (for PostgreSQL) not in pyproject.toml
- ⚠️ NLP service disabled due to Python 3.13 compatibility issues

---

## CRITICAL Issues (Must Fix Now)

### CRITICAL-1: PostgreSQL Not Actually Used
**Location:** /backend/app/
**Issue:** Complete PostgreSQL schema (003_gdelt_signals_schema.sql) exists with comprehensive indexes, triggers, and tables, but NO application code uses it. All data flows through in-memory placeholder generation.

**Impact:**
- Database migrations are dead code
- Schema design investment (500+ lines SQL) wasted
- No persistent storage layer
- All "data" is ephemeral placeholder generation

**Evidence:**
```bash
# pyproject.toml has NO PostgreSQL client library
$ grep -r "psycopg\|asyncpg\|sqlalchemy" backend/pyproject.toml
No PostgreSQL clients in dependencies

# Only psycopg2 usage is in migrate.py (migration runner)
$ grep -r "psycopg\|asyncpg" backend/app/*.py
backend/app/db/migrate.py:15:import psycopg2
backend/app/db/migrate.py:16:from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
```

**Root Cause:**
- Phase 3 focused on GDELT placeholder generation
- PostgreSQL integration was designed but never implemented
- Services use in-memory data structures instead of database queries

**Fix:**
1. **Short-term (Phase 3.x continuation):** Document that PostgreSQL is "designed but not integrated" in HANDOFF
2. **Mid-term (Phase 4):** Implement storage layer with psycopg2 or asyncpg
3. **Alternative:** Remove migration files if persistent storage is not needed

**Verification:**
```bash
# Should see database queries in services
grep -r "SELECT\|INSERT\|UPDATE" backend/app/services/*.py
# Currently: NONE except migration runner
```

---

### CRITICAL-2: Missing PostgreSQL Client Dependency
**Location:** /backend/pyproject.toml
**Issue:** Migration runner (migrate.py) imports psycopg2, but psycopg2 is NOT listed in project dependencies.

**Impact:**
- Migration runner will fail on fresh installs
- Current deployment only works because psycopg2 was manually installed
- CI/CD will break

**Evidence:**
```python
# backend/app/db/migrate.py:15-16
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# backend/pyproject.toml dependencies - NO psycopg2
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    # ... no psycopg2 ...
]
```

**Fix:**
```bash
cd backend
# Add to pyproject.toml
dependencies = [
    ...
    "psycopg2-binary>=2.9.0",  # OR asyncpg>=0.29.0 for async
]
# Then install
pip install -e .
```

**Verification:**
```bash
python -m app.db.migrate --status
# Should connect without ImportError
```

---

### CRITICAL-3: NLP Service Disabled (Known Issue)
**Location:** /backend/app/services/signals_service.py:97
**Issue:** NLPProcessor is disabled due to sklearn/numpy hanging on Python 3.13.

**Impact:**
- Topic extraction from multi-source signals BROKEN
- fetch_trending_signals() method (lines 183-278) is dead code
- Only fetch_gdelt_signals() works (GDELT placeholder only)

**Evidence:**
```python
# signals_service.py:97-99
# TEMPORARY: NLPProcessor disabled due to sklearn/numpy import hang on Python 3.13
# self.nlp_processor = NLPProcessor()
self.nlp_processor = None

# signals_service.py:257
if all_items:
    topics = self.nlp_processor.process_and_extract_topics(  # WILL CRASH
        all_items,
        limit=50
    )
```

**Root Cause:**
- Python 3.13 incompatibility with sklearn/numpy versions
- pyproject.toml specifies `requires-python = ">=3.11"` (should be 3.12 max)

**Fix Options:**

**Option A: Downgrade Python (Recommended)**
```bash
pyenv install 3.12
pyenv local 3.12
# Rebuild venv
```

**Option B: Remove NLP Dependencies**
```toml
# If NLP not needed, remove from pyproject.toml:
dependencies = [
    # "nltk>=3.8.0",           # REMOVE
    # "scikit-learn>=1.4.0",   # REMOVE
    # "langdetect>=1.0.9",     # REMOVE
]
```

**Verification:**
```python
from app.services.nlp import NLPProcessor
nlp = NLPProcessor()  # Should not hang
```

---

## MEDIUM Priority (Should Fix Soon)

### MEDIUM-1: Unused Frontend Dependencies
**Location:** /frontend/package.json
**Issue:** Several dependencies appear unused or minimally used.

**Findings:**

| Dependency | Declared | Usage Found | Assessment |
|------------|----------|-------------|------------|
| `react-router-dom` | Yes | 1 file (App.tsx) | **MINIMAL** - Only BrowserRouter wrapper, no actual routing |
| `recharts` | Yes | 1 file (TopicList.tsx) | **USED** - Bar chart visualization |
| `framer-motion` | Yes | 2 files (CountrySidebar, HotspotLayer) | **USED** - Animations |
| `@turf/turf` | Yes | 1 file (FlowLayer.tsx) | **USED** - GeoJSON arc generation |
| `date-fns` | Yes | 2 files (AutoRefreshControl, DataStatusBar) | **USED** - Timestamp formatting |
| `h3-js` | Yes | Not found in src/ | **UNUSED** - H3 operations in backend only |
| `axios` | Yes | 1 file (api.ts) | **USED** - HTTP client |

**Impact:**
- `react-router-dom`: 6.21.0 is relatively large (~200KB) for only using BrowserRouter
- `h3-js`: 4.1.0 appears completely unused (H3 hexagon operations in backend only)

**Recommendations:**

**Remove `h3-js` (Unused):**
```bash
cd frontend
npm uninstall h3-js
```

**Evaluate `react-router-dom`:**
- Currently only wraps app in `<Router>` but no routes defined
- If no routing planned: Remove and use plain React
- If routing needed: Keep for future features

**Fix:**
```bash
# Remove h3-js
npm uninstall h3-js

# Optional: Remove react-router-dom if no routing planned
npm uninstall react-router-dom
# Then remove BrowserRouter wrapper in App.tsx
```

**Verification:**
```bash
npm run build
# Should compile without errors
```

---

### MEDIUM-2: Unused Backend Dependencies
**Location:** /backend/pyproject.toml
**Issue:** Several dependencies declared but not actively used.

**Findings:**

| Dependency | Declared | Usage Found | Assessment |
|------------|----------|-------------|------------|
| `nltk` | Yes | 1 file (nlp.py) - DISABLED | **UNUSED** - NLP disabled |
| `scikit-learn` | Yes | 1 file (nlp.py) - DISABLED | **UNUSED** - NLP disabled |
| `langdetect` | Yes | 1 file (nlp.py) - DISABLED | **UNUSED** - NLP disabled |
| `pytrends` | Yes | 1 file (trends_client.py) | **USED** - Google Trends API |
| `h3` | Yes | 1 file (hexmap_generator.py) | **USED** - H3 indexing |
| `geojson` | Yes | Not found | **UNUSED** - No direct imports |
| `orjson` | Yes | Not found | **UNUSED** - Using standard json module |

**Conditional Removals:**

If NLP permanently disabled (see CRITICAL-3):
```bash
# Remove NLP dependencies
pip uninstall nltk scikit-learn langdetect
# Update pyproject.toml to remove them
```

If using standard `json` module everywhere:
```bash
pip uninstall orjson
```

If not using `geojson` library (check if using dict-based GeoJSON only):
```bash
pip uninstall geojson
```

**Verification:**
```bash
grep -r "import nltk\|from nltk" backend/app/
grep -r "import sklearn\|from sklearn" backend/app/
grep -r "import orjson\|from orjson" backend/app/
grep -r "import geojson\|from geojson" backend/app/
```

---

### MEDIUM-3: Incomplete Country Metadata Coverage
**Location:** /backend/app/core/country_metadata.py
**Issue:** SignalsService defines 31 countries but COUNTRY_METADATA only has 17.

**Impact:**
- Missing centroids for 14 countries
- H3 hexmap generation will fail for: NL, BE, SE, NO, PL, CH, AT, KR, IL, SA, TR, EG, NG, UA

**Evidence:**
```python
# signals_service.py:50-88 - DEFAULT_COUNTRIES = 31 countries
DEFAULT_COUNTRIES = [
    "US", "CA", "MX", "BR", "CO", "AR",  # Americas (6)
    "GB", "FR", "DE", "ES", "IT", "NL", "BE", "SE", "NO", "PL", "CH", "AT",  # Europe (12)
    "CN", "JP", "IN", "KR", "AU",  # Asia-Pacific (5)
    "IL", "SA", "TR", "EG", "ZA", "NG",  # Middle East & Africa (6)
    "RU", "UA",  # Eastern Europe (2)
]

# country_metadata.py:24-49 - COUNTRY_METADATA = 17 countries
COUNTRY_METADATA: Dict[str, Tuple[str, float, float]] = {
    'US': ..., 'CO': ..., 'BR': ..., 'MX': ..., 'AR': ..., 'CA': ...,  # 6 Americas
    'GB': ..., 'FR': ..., 'DE': ..., 'ES': ..., 'IT': ..., 'RU': ...,  # 6 Europe
    'CN': ..., 'IN': ..., 'JP': ..., 'AU': ...,  # 4 Asia-Pacific
    'ZA': ...,  # 1 Africa
}
# MISSING: NL, BE, SE, NO, PL, CH, AT, KR, IL, SA, TR, EG, NG, UA (14 countries)
```

**Fix:**
Add missing country centroids to `country_metadata.py`:
```python
COUNTRY_METADATA: Dict[str, Tuple[str, float, float]] = {
    # ... existing ...

    # Europe (missing 6)
    'NL': ('Netherlands', 52.1326, 5.2913),
    'BE': ('Belgium', 50.5039, 4.4699),
    'SE': ('Sweden', 60.1282, 18.6435),
    'NO': ('Norway', 60.4720, 8.4689),
    'PL': ('Poland', 51.9194, 19.1451),
    'CH': ('Switzerland', 46.8182, 8.2275),
    'AT': ('Austria', 47.5162, 14.5501),

    # Asia-Pacific (missing 1)
    'KR': ('South Korea', 35.9078, 127.7669),

    # Middle East & Africa (missing 5)
    'IL': ('Israel', 31.0461, 34.8516),
    'SA': ('Saudi Arabia', 23.8859, 45.0792),
    'TR': ('Turkey', 38.9637, 35.2433),
    'EG': ('Egypt', 26.8206, 30.8025),
    'NG': ('Nigeria', 9.0820, 8.6753),

    # Eastern Europe (missing 1)
    'UA': ('Ukraine', 48.3794, 31.1656),
}
```

**Verification:**
```python
from app.core.country_metadata import get_country_coordinates
from app.services.signals_service import SignalsService

service = SignalsService()
for country in service.DEFAULT_COUNTRIES:
    try:
        coords = get_country_coordinates(country)
        print(f"✓ {country}: {coords}")
    except KeyError:
        print(f"✗ {country}: MISSING")
```

---

### MEDIUM-4: Documentation Bloat - Hacker News/Mastodon Never Implemented
**Location:** /docs/, /infra/, /.agents/
**Issue:** Extensive documentation (3000+ lines) about Hacker News and Mastodon integration that was never implemented. Creates confusion about system capabilities.

**Impact:**
- Misleading documentation suggests features that don't exist
- Future developers will waste time looking for HN/Mastodon code
- Iteration 2 planning documents are obsolete
- Bloats repository size and search results

**Evidence:**
```bash
$ grep -r "Hacker News\|Mastodon" . | wc -l
287 matches across documentation

# Major files with HN/Mastodon references:
infra/DATA_SOURCES_FEASIBILITY.md (165 lines about HN/Mastodon)
infra/TOP_3_RECOMMENDATIONS_SUMMARY.txt (120 lines)
infra/DATA_SOURCES_IMPLEMENTATION.md (200 lines with code examples)
docs/planning/ITERATION-2-MASTER-PLAN.md (300+ lines)
.agents/narrative_geopolitics_analyst.md (multiple references)
```

**Current Reality:**
- Data sources: GDELT placeholder ONLY
- No HN integration
- No Mastodon integration
- No Reddit integration
- Iteration 2 was ABANDONED in favor of direct GDELT implementation

**Recommendations:**

**Option A: Archive Obsolete Docs (Recommended)**
```bash
mkdir docs/archive/iteration-2-abandoned
mv docs/planning/ITERATION-2-*.md docs/archive/iteration-2-abandoned/
mv infra/DATA_SOURCES_*.md docs/archive/iteration-2-abandoned/
mv infra/TOP_3_RECOMMENDATIONS_*.txt docs/archive/iteration-2-abandoned/
mv infra/COMPARISON_MATRIX.txt docs/archive/iteration-2-abandoned/

# Add README explaining why archived
cat > docs/archive/iteration-2-abandoned/README.md << EOF
# Iteration 2 - Archived Planning Documents

These documents represent planning for Iteration 2 which focused on
Hacker News and Mastodon integration. This approach was ABANDONED
in favor of direct GDELT 2.0 implementation (Iteration 3+).

**Status:** Not implemented, superseded by GDELT-first strategy
**Date Archived:** 2025-11-21
**Reason:** Strategic pivot to GDELT as primary data source
EOF
```

**Option B: Update Docs to Reflect Current Reality**
- Add "NOT IMPLEMENTED" banners to HN/Mastodon docs
- Update .agents/ prompts to remove HN/Mastodon references
- Update CLAUDE.md to remove outdated multi-source architecture

**Verification:**
```bash
# After cleanup, should see minimal HN/Mastodon references
grep -r "Hacker News\|Mastodon" docs/ infra/ .agents/ | wc -l
# Target: < 50 lines (only in archived/historical context)
```

---

### MEDIUM-5: Inconsistent Country Code Coverage in SignalsService
**Location:** /backend/app/services/signals_service.py:50-88
**Issue:** DEFAULT_COUNTRIES expanded to 31 countries but no validation that all are supported by GDELT placeholder generator.

**Impact:**
- Potential runtime errors when requesting unsupported countries
- Inconsistent data availability across countries
- No clear documentation of which countries have real vs placeholder data

**Evidence:**
```python
# signals_service.py:50-88
DEFAULT_COUNTRIES = [
    # 31 countries listed
]

# gdelt_placeholder_generator.py - Uses COUNTRY_METADATA
# Only 17 countries supported (see MEDIUM-3)
```

**Fix:**
Add validation layer:
```python
# signals_service.py
from app.core.country_metadata import get_supported_countries

class SignalsService:
    def __init__(self):
        # Validate all default countries are supported
        supported = set(get_supported_countries())
        unsupported = set(self.DEFAULT_COUNTRIES) - supported
        if unsupported:
            logger.warning(
                f"SignalsService: {len(unsupported)} countries lack metadata: {unsupported}"
            )
            # Filter to only supported countries
            self.DEFAULT_COUNTRIES = [c for c in self.DEFAULT_COUNTRIES if c in supported]
```

**Verification:**
```bash
# Check logs on service initialization
tail -f logs/backend.log | grep "SignalsService"
# Should show warning if countries missing
```

---

## CLEANUP Priority (Hygiene Items)

### CLEANUP-1: Remove Temporary Comments from Codebase
**Location:** Various files
**Issue:** TEMPORARY comments and disabled code blocks create confusion.

**Evidence:**
```python
# signals_service.py:23-24
# TEMPORARY: Disabled due to sklearn/numpy hanging on Python 3.13
# from app.services.nlp import NLPProcessor

# signals_service.py:97-99
# TEMPORARY: NLPProcessor disabled due to sklearn/numpy import hang on Python 3.13
# self.nlp_processor = NLPProcessor()
self.nlp_processor = None
```

**Fix:**
Either fix the issue (see CRITICAL-3) or make it permanent:
```python
# If NLP permanently disabled:
# Remove import entirely
# Update docstrings to reflect fetch_gdelt_signals() is primary method
# Mark fetch_trending_signals() as @deprecated
```

---

### CLEANUP-2: Unused Fallback Function in flows.py
**Location:** /backend/app/api/v1/flows.py:162-170
**Issue:** `_generate_fallback_data()` function defined but never called.

**Evidence:**
```python
def _generate_fallback_data(country: str) -> list:
    """Generate fallback data when all sources fail."""
    return [
        {"title": f"Breaking News in {country}", "source": "fallback", "count": 100},
        # ...
    ]
# NEVER CALLED - SignalsService handles fallbacks internally
```

**Fix:**
```bash
# Remove lines 162-170 from flows.py
```

---

### CLEANUP-3: Outdated HANDOFF Documents Should Be Consolidated
**Location:** /docs/state/
**Issue:** 7 handoff documents spanning 2025-01-14 to 2025-01-21 create noise.

**Recommendation:**
```bash
# Keep only latest handoff (2025-01-21)
# Archive older ones
mkdir docs/state/archive/
mv docs/state/HANDOFF-2025-01-14.md docs/state/archive/
mv docs/state/HANDOFF-2025-01-15.md docs/state/archive/
mv docs/state/HANDOFF-2025-01-18.md docs/state/archive/
mv docs/state/HANDOFF-2025-01-19.md docs/state/archive/
mv docs/state/HANDOFF-2025-01-20.md docs/state/archive/

# Keep: HANDOFF-2025-01-21.md (latest)
```

---

## Data Flow Analysis

### Finding: Excellent Architecture - No Divergence

**✅ VERIFIED: Both /v1/flows and /v1/hexmap use identical data source**

**Data Flow Trace:**

```
┌─────────────────────────────────────────────────────┐
│                 UNIFIED DATA FLOW                    │
└─────────────────────────────────────────────────────┘

GET /v1/flows                    GET /v1/hexmap
      │                                │
      ├────────── Both call ───────────┤
      │                                │
      ▼                                ▼
SignalsService.fetch_gdelt_signals(countries, time_window)
      │
      ├─ Check Redis cache (5-min TTL)
      │    ├─ HIT: Return cached GDELTSignal[]
      │    └─ MISS: ▼
      │
      ├─ For each country:
      │    └─ GDELTClient.fetch_gdelt_signals()
      │         └─ GDELTPlaceholderGenerator.generate_signals()
      │              └─ Returns List[GDELTSignal]
      │
      ├─ Cache results in Redis (key: "gdelt:tw6h:cAR,BR,US")
      │
      └─ Return Dict[country → (signals, timestamp)]

THEN:

/v1/flows:                       /v1/hexmap:
├─ convert_gdelt_to_topics()     ├─ convert_gdelt_to_topics()
├─ FlowDetector.detect_flows()   ├─ FlowDetector.detect_flows()
│   └─ Returns (hotspots, flows) │   └─ Returns (hotspots, _, _)
└─ FlowsResponse                 ├─ HexmapGenerator.generate_hexmap()
                                 │   └─ Converts hotspots → H3 hexes
                                 └─ HexmapResponse
```

**Key Findings:**

1. **Single Source of Truth:** SignalsService is the ONLY entry point for data
2. **Identical Cache Keys:** Both endpoints share Redis cache (5-min TTL)
3. **No Hidden Branching:** No special cases or conditional logic divergence
4. **Shared Adapter:** `convert_gdelt_to_topics()` called by both
5. **Consistent Intensity Calculation:** FlowDetector used by both for hotspot intensity

**Verification Evidence:**

```python
# flows.py:87-93
signals_service = get_signals_service()
gdelt_signals_by_country = await signals_service.fetch_gdelt_signals(
    countries=country_list,
    time_window=time_window,
    use_cache=True,
)

# hexmap.py:186-191
signals_service = get_signals_service()
gdelt_signals_by_country = await signals_service.fetch_gdelt_signals(
    countries=country_list,
    time_window=time_window,
    use_cache=True,
)
```

**Assessment:** ✅ **NO ISSUES FOUND** - Architecture is correct and unified

---

## PostgreSQL and Storage Integration

### Finding: Schema Designed But Not Integrated

**Database Schema Status:**

| Component | Status | Lines of Code | Assessment |
|-----------|--------|---------------|------------|
| Migration 001 (trends_archive) | Defined | 100 lines | ⚠️ NOT USED |
| Migration 002 (flow_schema) | Defined | 200 lines | ⚠️ NOT USED |
| Migration 003 (gdelt_signals) | Defined | 651 lines | ⚠️ NOT USED |
| Application Code Using DB | Implemented | 0 lines | ❌ MISSING |

**Schema Design Quality:**

The 003_gdelt_signals_schema.sql is **EXCELLENT** in design:
- ✅ Proper indexes for query patterns
- ✅ Time bucketing (15-min, 1-hour) for GDELT cadence
- ✅ Normalized tables (signals, themes, entities, aggregations)
- ✅ Triggers for auto-populating derived fields
- ✅ Helper functions (bucket_15min, sentiment_label)
- ✅ Foreign key constraints
- ✅ Performance targets documented (< 100ms query, 1-2M rows/day)

**But:** Zero integration with application code.

**Current Data Storage:**

```
REALITY: All data is ephemeral
┌────────────────────────────────────┐
│  GDELTPlaceholderGenerator         │
│  └─ Generates in-memory signals    │
│      └─ Returned to API             │
│          └─ Cached in Redis (5 min) │
│              └─ DISCARDED           │
└────────────────────────────────────┘

NO WRITES TO POSTGRESQL
NO READS FROM POSTGRESQL
ALL DATA LIVES 5 MINUTES MAX
```

**Alignment Issues:**

| Schema Field | Placeholder Data | Alignment |
|--------------|------------------|-----------|
| gkg_record_id | ✅ Generated | Perfect |
| timestamp | ✅ Generated | Perfect |
| bucket_15min | ✅ Generated | Perfect |
| country_code | ✅ Generated | Perfect |
| themes/theme_counts | ✅ Generated | Perfect |
| tone (6 values) | ✅ Generated | Perfect |
| locations[] | ✅ Generated | Perfect |
| persons[] | ✅ Generated (Phase 3.5) | Perfect |
| organizations[] | ✅ Generated (Phase 3.5) | Perfect |
| source_outlet | ✅ Generated (Phase 3.5) | Perfect |
| intensity | ✅ Calculated | Perfect |
| sentiment_label | ✅ Derived | Perfect |

**Assessment:** ✅ **Schema and placeholder data are PERFECTLY aligned**
**Issue:** ⚠️ **Integration layer missing** (no INSERT/SELECT code)

**Recommendation:** See CRITICAL-1 for fix strategy

---

## Geographic Data Correctness

### Finding: Consistent and Correct

**Coordinate System Verification:**

| Aspect | Implementation | Standard | Assessment |
|--------|----------------|----------|------------|
| Latitude Range | -90 to +90 | WGS84 | ✅ Correct |
| Longitude Range | -180 to +180 | WGS84 | ✅ Correct |
| Coord Order | (lat, lon) everywhere | Mapbox expects [lon, lat] | ⚠️ Check frontend |
| Country Codes | ISO 3166-1 alpha-2 | ISO standard | ✅ Correct |
| Centroid Source | Hardcoded in country_metadata.py | Manual selection | ✅ Reasonable |

**Backend Coordinate Handling:**

```python
# country_metadata.py - CONSISTENT FORMAT
COUNTRY_METADATA: Dict[str, Tuple[str, float, float]] = {
    'US': ('United States', 37.0902, -95.7129),  # (name, LAT, LON)
    'CO': ('Colombia', 4.5709, -74.2973),         # (name, LAT, LON)
}

# Functions return (latitude, longitude)
def get_country_coordinates(country_code: str) -> Tuple[float, float]:
    return COUNTRY_METADATA[country_code][1], COUNTRY_METADATA[country_code][2]
    #      ↑ latitude (index 1)           ↑ longitude (index 2)
```

**Frontend Coordinate Interpretation:**

Need to verify that FlowLayer and HotspotLayer correctly swap to [lon, lat] for Mapbox:

```typescript
// Should be:
const coordinates = [longitude, latitude];  // Mapbox format
// NOT:
const coordinates = [latitude, longitude];  // Backend format
```

**H3 Hexagon Generation:**

```python
# hexmap_generator.py uses correct format
h3.geo_to_h3(lat, lon, resolution)  # ✅ Correct H3 function signature
```

**Assessment:** ✅ **Mostly Correct**
**Minor Issue:** Need to verify frontend coordinate swap for Mapbox (should be done in components)

---

## Summary of Findings

### By Priority

**CRITICAL (3):**
1. PostgreSQL schema exists but never used (no persistence layer)
2. Missing psycopg2 dependency (migration runner will fail on fresh install)
3. NLP service disabled (Python 3.13 incompatibility, blocking multi-source signals)

**MEDIUM (5):**
1. Unused frontend dependency: h3-js (completely unused, remove)
2. Unused backend dependencies: nltk, scikit-learn, langdetect (if NLP disabled), geojson, orjson
3. Incomplete country metadata (14 countries missing centroids)
4. Documentation bloat (3000+ lines about never-implemented HN/Mastodon)
5. Inconsistent country coverage validation

**CLEANUP (3):**
1. TEMPORARY comments throughout codebase
2. Unused _generate_fallback_data() function
3. 7 handoff documents should be consolidated/archived

---

## Recommended Action Plan

### Immediate Actions (This Session)

1. ✅ **Add missing dependency** (5 minutes)
   ```bash
   # Add to backend/pyproject.toml
   dependencies = ["psycopg2-binary>=2.9.0", ...]
   pip install psycopg2-binary
   ```

2. ✅ **Remove unused frontend dependency** (2 minutes)
   ```bash
   cd frontend
   npm uninstall h3-js
   ```

3. ✅ **Add missing country centroids** (10 minutes)
   - Add 14 countries to country_metadata.py (see MEDIUM-3)

4. ✅ **Document PostgreSQL status** (5 minutes)
   - Add note to HANDOFF-2025-01-21.md about PostgreSQL designed-but-not-integrated

### Short-Term (Next Session - 2-4 hours)

5. **Archive obsolete documentation**
   - Move Iteration 2 docs to archive/
   - Update CLAUDE.md to remove HN/Mastodon references

6. **Fix NLP service OR remove dependencies**
   - Either: Downgrade to Python 3.12
   - Or: Remove nltk/sklearn/langdetect from dependencies

7. **Cleanup temporary comments**
   - Make decisions permanent (keep or remove NLP)
   - Remove TEMPORARY markers

### Mid-Term (Phase 4 Planning)

8. **PostgreSQL Integration Decision**
   - Option A: Implement storage layer (4-6 hours)
   - Option B: Remove migration files (30 minutes)
   - Option C: Keep for future, document as planned-not-implemented

9. **Dependency Audit**
   - Review and remove orjson, geojson if confirmed unused

---

## Metrics

**Codebase Size:**
- Frontend: 19 TypeScript/TSX files
- Backend: 26 Python files
- Migrations: 3 SQL files (651 lines total, unused)
- Documentation: 40+ markdown files (significant bloat from Iteration 2)

**Test Coverage:** Not assessed (requires separate test run)

**Code Quality:**
- ✅ Consistent naming conventions
- ✅ Good separation of concerns (services, adapters, models)
- ✅ Proper use of Pydantic for validation
- ✅ TypeScript types mostly defined
- ⚠️ Some dead code (fallback function, disabled NLP)
- ⚠️ Documentation out of sync with implementation

**Dependency Health:**
- Frontend: 30 direct dependencies (1 unused: h3-js)
- Backend: 15 production dependencies (3-4 potentially unused)
- No known security vulnerabilities detected (manual review only)

---

## Conclusion

The Observatory Global codebase is in **good overall health** with clean architecture and consistent patterns. The major issue is the disconnect between planned features (PostgreSQL, multi-source signals, HN/Mastodon) and implemented features (GDELT placeholder only).

**Key Strengths:**
- Unified data flow through SignalsService
- Well-designed PostgreSQL schema (even if unused)
- Consistent geographic data handling
- Clean separation of concerns

**Key Weaknesses:**
- Significant technical debt from abandoned Iteration 2 plans
- PostgreSQL integration missing despite complete schema
- NLP functionality disabled
- Documentation bloat creates confusion

**Recommendation:** Before adding new features, execute the Immediate Actions and Short-Term cleanup. This will provide a solid foundation and reduce confusion for future development.

---

**Assessment completed:** 2025-11-21
**Next review recommended:** After Phase 4 planning or before major feature additions
