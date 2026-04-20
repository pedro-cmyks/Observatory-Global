# Atlas — Session Log

## 2026-04-20

### Added
- Aircraft layer: OpenSky integration, amber dots, PLANE toggle
- Graceful degradation for API rate limits (no fake data)
- ThemeDetail framing section promoted to top
- Correlation Matrix → CountryBrief click navigation
- Source Integrity: real domain names from backend (extract_domain)
- GDELT theme label improvements (regex cleanup in themeLabels.ts)
- README rewritten for Atlas public launch
- CONTRIBUTING.md added

### Known issues
- OpenSky free tier rate limits (~1 req/60s recommended)
- Globe 3D deferred to later phase
- Some GDELT theme codes still not in manual label dictionary

### Next session
- UX first minute experience (auto-focus, welcome card)
- Maritime vessel layer (AISStream Phase 3C)
- Aircraft icon → real plane shape
