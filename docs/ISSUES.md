# Observatory Global - Open Issues & Enhancements

## Active Bugs 🐛

### BUG-001: Theme detail performance with large datasets
- **Severity**: Low
- **Description**: Theme detail modal may be slow when theme has 1000+ signals
- **Impact**: User experience degradation for popular themes
- **Potential fix**: Add pagination or limit to first 100 signals
- **Status**: Monitoring

## Recently Fixed Bugs ✅

### BUG-002: Coordinates were being overwritten (FIXED)
- **Severity**: Critical
- **Description**: `update_countries()` overwrote manual coordinate fixes
- **Status**: ✅ Fixed Dec 2 - changed to `ON CONFLICT DO NOTHING`

### BUG-003: Flows endpoint Decimal serialization (FIXED)
- **Severity**: High
- **Description**: FastAPI couldn't serialize Decimal flow strength values
- **Status**: ✅ Fixed Dec 3 - convert to float before response

### BUG-004: Theme drill-down showed "0 signals" (FIXED)
- **Severity**: Medium
- **Description**: Frontend passing display label instead of raw GDELT code
- **Status**: ✅ Fixed - ensuring raw theme code is passed

## Enhancements 🚀

### ENH-001: Article titles and snippets
- **Priority**: High
- **Description**: Theme drill-down should show actual article headlines
- **Blocker**: GDELT GKG doesn't include article content
- **Approach**:
  - Investigate GDELT Events API for URLs
  - Consider NewsAPI integration
  - Add web scraping for top sources

### ENH-002: AI-powered theme summaries
- **Priority**: High
- **Description**: Generate human-readable summaries of what themes mean
- **Approach**:
  - Use Claude/GPT to summarize grouped articles
  - Cache summaries for popular themes
  - Update summaries daily
- **Cost**: Estimate $0.001 per theme summary

### ENH-003: Additional data sources
- **Priority**: Medium
- **Description**: GDELT has limitations (no precise coords, few persons)
- **Options**:
  - NewsAPI (has titles, descriptions, images)
  - RSS feeds from major outlets (NYT, BBC, Al Jazeera)
  - Twitter/X API for trending (expensive)
  - Reddit for discussion threads
- **Effort**: 2-3 days per source

### ENH-004: Heatmap with real coordinates
- **Priority**: Low (blocked by data)
- **Description**: Weather-radar style heatmap showing precise locations
- **Blocker**: GDELT only provides coordinates for 0.02% of articles
- **Alternative**:
  - Use city-level aggregation
  - Integrate with location data from other sources
  - Generate synthetic coordinates based on theme density

### ENH-005: Time-lapse animation
- **Priority**: Medium
- **Description**: Animate flows/activity over time periods
- **Approach**:
  - Store hourly snapshots of signals
  - Implement timeline scrubber UI
  - Animate map transitions between snapshots
- **Effort**: 3-5 days

### ENH-006: Custom alerts and notifications
- **Priority**: Low
- **Description**: User-defined alerts for themes, countries, or sentiment changes
- **Requirements**:
  - User accounts and authentication
  - Email/push notification system
  - Alert configuration UI
- **Effort**: 1-2 weeks

### ENH-007: Improved theme labeling
- **Priority**: Medium
- **Description**: Only ~200 of 1000+ themes have human-readable labels
- **Approach**:
  - Scrape GDELT Cameo codebook
  - Use LLM to generate labels for unlabeled themes
  - Allow user contributions
- **Effort**: 2-3 days

### ENH-008: User accounts and saved searches
- **Priority**: Low
- **Description**: Allow users to save preferences, searches, and alerts
- **Requirements**:
  - Authentication system (OAuth or JWT)
  - User database schema
  - Settings UI
- **Effort**: 1 week

### ENH-009: Public API access
- **Priority**: Low
- **Description**: Expose read-only API for researchers and developers
- **Requirements**:
  - API key management
  - Rate limiting
  - Documentation
- **Effort**: 3-4 days

### ENH-010: Mobile app
- **Priority**: Low
- **Description**: Native iOS/Android apps
- **Approach**: React Native or Flutter
- **Effort**: 4-6 weeks

## Technical Debt 🔧

### TD-001: Frontend type safety
- **Description**: Some components lack proper TypeScript types
- **Files**: SearchBar.tsx, ThemeDetail.tsx
- **Effort**: 1-2 hours

### TD-002: Backend error handling
- **Description**: Some endpoints lack comprehensive try/catch blocks
- **Files**: main_v2.py endpoints
- **Effort**: 2-3 hours

### TD-003: Test coverage
- **Description**: No automated tests for frontend or backend
- **Priority**: Medium
- **Effort**: 1 week for basic coverage

### TD-004: Logging improvements
- **Description**: Add structured logging with correlation IDs
- **Benefits**: Better debugging and monitoring
- **Effort**: 1 day

## Feature Requests from Users 💬

*(None yet - add user feedback here)*

## Legend

- 🐛 **Bug**: Something is broken
- ✅ **Fixed**: Issue resolved
- 🚀 **Enhancement**: New feature or improvement
- 🔧 **Technical Debt**: Code quality or maintainability issue
- 💬 **User Request**: Feedback from users

## Priority Levels

- **Critical**: Blocks core functionality
- **High**: Significant impact on user experience
- **Medium**: Notable improvement but not urgent
- **Low**: Nice-to-have, can wait
