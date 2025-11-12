# Frontend Map Agent

## Role
Senior frontend engineer for React and Mapbox GL.

## Mission
Replace the map placeholder with an interactive visualization and clear status bar.

## Deliverables

### 1. Country Hotspot Visualization
- **Circles on map** representing countries
  - Size: proportional to `topic_count`
  - Color gradient: based on `intensity` [0,1]
    - 0.0-0.3: Cool blue (#3B82F6)
    - 0.3-0.6: Warm yellow (#FCD34D)
    - 0.6-1.0: Hot red (#EF4444)
  - Smooth transitions on data updates

### 2. Flow Arcs Between Countries
- **Curved lines** connecting countries with shared topics
  - Stroke width: proportional to `heat` score
  - Opacity: based on `heat` (min 0.3, max 1.0)
  - Animated pulse when `heat > 0.7`
  - Direction arrow indicating flow (from → to)
  - Hover shows: similarity %, time delta, shared topics

### 3. Time Window Selector
- Dropdown or button group: **1h, 6h, 12h, 24h**
- Default: 24h
- Updates URL query param: `?window=24h`
- Triggers data refetch on change

### 4. Country Filter
- Multi-select dropdown
- Default: All countries
- Checkboxes for quick toggle
- "Select All" / "Clear All" options
- Updates URL query param: `?countries=US,CO,BR`

### 5. Auto-Refresh
- Default: 5 minutes
- User configurable: 1m, 5m, 15m, Off
- Visual countdown timer
- Pause on user interaction (dragging map, filters open)
- Resume after 30s of inactivity

### 6. Country Click Interaction
- Sidebar panel slides in from right
- Shows:
  - Country name and flag
  - Current intensity score with visual gauge
  - Top 10 topics with counts
  - Confidence scores
  - Sample article titles
  - Sources (GDELT, Trends, Wikipedia)
- "Close" button or click outside to dismiss

### 7. Data Status Bar
- Fixed position at bottom
- Shows:
  - Last update timestamp (e.g., "Updated 2 min ago")
  - Backend status: 🟢 Healthy / 🟡 Degraded / 🔴 Down
  - Active sources: GDELT, Trends, Wikipedia (with status icons)
  - Refresh countdown
  - Manual refresh button

## Component Architecture

```
MapView/
├── MapContainer.tsx          # Mapbox GL wrapper
├── HotspotLayer.tsx          # Country circles
├── FlowLayer.tsx             # Flow arcs with animation
├── CountrySidebar.tsx        # Detail panel
├── TimeWindowSelector.tsx    # Time controls
├── CountryFilter.tsx         # Multi-select
├── AutoRefreshControl.tsx    # Refresh settings
└── DataStatusBar.tsx         # Status indicator
```

## Conventions

### TypeScript
- Strict typing enabled
- Define interfaces for all API responses
- No `any` types unless absolutely necessary
- Use Zod for runtime validation of API responses

### Error Handling
- Network errors: Show toast notification, retry button
- Parsing errors: Log to console, show fallback UI
- Missing data: Graceful degradation (show available data)
- API timeout: Show "Loading..." → "Taking longer than usual..." after 5s

### Loading States
- Initial load: Skeleton map with pulsing circles
- Refetching: Subtle loading indicator in status bar
- Filter change: Fade out old data, fade in new data (300ms)

### Empty States
- No data: "No trends found for selected filters"
- No flows: "No information flows detected in this time window"
- Actionable suggestions: "Try expanding the time window or selecting more countries"

### Performance
- Virtualize large datasets (>100 countries)
- Debounce filter changes (300ms)
- Memoize expensive calculations
- Lazy load Mapbox GL library

## Definition of Done
- Runs via `docker compose up`
- Connects to real API (or mock with MSW for offline dev)
- All filters and refresh logic working
- Responsive design (desktop, tablet, mobile)
- Keyboard accessible (tab navigation, ARIA labels)
- Demo GIF recorded and saved to `docs/demos/iter1c.gif`
- README updated with screenshots and usage instructions

## Testing
- Unit tests for components (React Testing Library)
- Integration tests for user flows:
  - Select country → view details
  - Change time window → see updated data
  - Apply filters → see filtered results
- Visual regression tests (optional, nice-to-have)

## Styling
- Tailwind CSS for utility classes
- Dark mode support (system preference)
- Smooth animations (framer-motion or CSS transitions)
- Consistent spacing and typography
- Accessibility: WCAG AA contrast ratios

## Dependencies
```json
{
  "mapbox-gl": "^3.0.0",
  "react-map-gl": "^7.1.0",
  "@turf/turf": "^6.5.0",  // Geo calculations
  "framer-motion": "^10.0.0",  // Animations
  "date-fns": "^3.0.0",  // Date formatting
  "zustand": "^4.5.0"  // State management
}
```

## Configuration
- Mapbox token from environment: `VITE_MAPBOX_TOKEN`
- API base URL: `VITE_API_BASE_URL`
- Default refresh interval: `VITE_DEFAULT_REFRESH_MS`
