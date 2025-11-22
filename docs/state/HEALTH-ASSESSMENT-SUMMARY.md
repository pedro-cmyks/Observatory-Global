# Project Health Assessment - Quick Reference
**Date:** 2025-11-21
**Full Report:** [PROJECT-HEALTH-ASSESSMENT-2025-11-21.md](./PROJECT-HEALTH-ASSESSMENT-2025-11-21.md)

---

## Overall Health: 7.5/10 - Good with Notable Technical Debt

---

## CRITICAL Issues (Fix Now)

### 1. PostgreSQL Not Actually Used
- **Problem:** Complete schema (651 lines SQL) exists but NO application code uses it
- **Impact:** All data is ephemeral placeholder generation, no persistence
- **Evidence:** `grep -r "psycopg\|asyncpg\|sqlalchemy" backend/pyproject.toml` returns nothing
- **Fix:** Either implement storage layer OR remove migration files

### 2. Missing PostgreSQL Client Dependency
- **Problem:** migrate.py imports psycopg2 but it's not in pyproject.toml
- **Impact:** Fresh installs will fail, CI/CD broken
- **Fix:**
  ```bash
  # Add to backend/pyproject.toml dependencies:
  "psycopg2-binary>=2.9.0"
  ```

### 3. NLP Service Disabled (Python 3.13 Issue)
- **Problem:** sklearn/numpy hang on Python 3.13, NLP completely disabled
- **Impact:** Multi-source topic extraction broken, fetch_trending_signals() dead code
- **Fix:** Downgrade to Python 3.12 OR remove nltk/sklearn/langdetect dependencies

---

## MEDIUM Priority

### 4. Unused Frontend Dependencies
- **h3-js:** Completely unused (H3 operations in backend only) - REMOVE
- **react-router-dom:** Only wraps app, no actual routing - EVALUATE

### 5. Incomplete Country Metadata
- **Problem:** 31 countries in SignalsService, only 17 in COUNTRY_METADATA
- **Impact:** Missing centroids for: NL, BE, SE, NO, PL, CH, AT, KR, IL, SA, TR, EG, NG, UA
- **Fix:** Add 14 missing country centroids

### 6. Documentation Bloat
- **Problem:** 3000+ lines about Hacker News/Mastodon that were never implemented
- **Impact:** Confusion about system capabilities
- **Fix:** Archive Iteration 2 docs to docs/archive/

---

## CLEANUP

### 7. TEMPORARY Comments
- Remove or make permanent (signals_service.py, nlp.py)

### 8. Dead Code
- Remove `_generate_fallback_data()` in flows.py (never called)

### 9. Handoff Document Proliferation
- Archive old handoffs, keep only HANDOFF-2025-01-21.md

---

## Data Flow Assessment: ✅ EXCELLENT

**Finding:** Both /v1/flows and /v1/hexmap use IDENTICAL data source (SignalsService)

```
GET /v1/flows         GET /v1/hexmap
      │                     │
      └──── BOTH CALL ──────┘
              │
              ▼
    SignalsService.fetch_gdelt_signals()
              │
              ├─ Redis cache (5-min TTL)
              ├─ GDELTPlaceholderGenerator
              └─ Returns Dict[country → signals]
```

**No divergence, no duplication, no hidden branching** ✅

---

## Geographic Data: ✅ CORRECT

- Coordinate system: WGS84 (lat/lon format)
- Country codes: ISO 3166-1 alpha-2
- Centroids: Reasonable approximations
- H3 usage: Correct format

**Minor:** Verify frontend swaps to [lon, lat] for Mapbox

---

## PostgreSQL Schema Assessment: ✅ EXCELLENT DESIGN / ⚠️ NOT USED

**Schema Quality (003_gdelt_signals_schema.sql):**
- ✅ Proper indexes for query patterns
- ✅ Time bucketing (15-min, 1-hour)
- ✅ Normalized tables (signals, themes, entities, aggregations)
- ✅ Triggers for auto-population
- ✅ Performance targets (< 100ms query, 1-2M rows/day)

**Schema Alignment with Placeholder Data:**
- ✅ Perfect alignment (all fields match)

**Application Integration:**
- ❌ Zero queries to database
- ❌ All data is in-memory ephemeral

---

## Immediate Action Checklist

**Can be done in < 30 minutes:**

- [ ] Add psycopg2-binary to backend/pyproject.toml
- [ ] `npm uninstall h3-js` in frontend
- [ ] Add 14 missing countries to country_metadata.py
- [ ] Add note to HANDOFF-2025-01-21.md about PostgreSQL status

**Full details:** See main report

---

## Strengths

✅ Clean data flow architecture (SignalsService unification)
✅ Both endpoints consume identical signal data (no divergence)
✅ Geographic data uses consistent centroids
✅ Well-designed PostgreSQL schema
✅ Good separation of concerns (services, adapters, models)
✅ Proper Pydantic validation
✅ No critical security issues

---

## Weaknesses

⚠️ PostgreSQL schema exists but is NOT USED (no persistence layer)
⚠️ Significant documentation bloat (HN/Mastodon never implemented)
⚠️ Some unused dependencies
⚠️ NLP service disabled (Python 3.13 compatibility)
⚠️ Missing dependency: psycopg2
⚠️ Incomplete country metadata coverage

---

## Metrics

- **Frontend:** 19 TypeScript/TSX files, 30 dependencies (1 unused)
- **Backend:** 26 Python files, 15 production dependencies (3-4 potentially unused)
- **Database:** 3 migrations (651 lines SQL, unused)
- **Documentation:** 40+ markdown files (significant bloat)

---

## Recommendation

Before adding new features:
1. Execute Immediate Actions (30 minutes)
2. Make decision on PostgreSQL (implement or remove)
3. Archive obsolete Iteration 2 documentation
4. Fix or remove NLP service

This provides a clean foundation for Phase 4 development.

---

**Full report:** [PROJECT-HEALTH-ASSESSMENT-2025-11-21.md](./PROJECT-HEALTH-ASSESSMENT-2025-11-21.md)
