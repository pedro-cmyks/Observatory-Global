# Phase 1 Redesign: Bloomberg Terminal Framework

Phase 1 of the structural UI overhaul has been completed. The frontend architecture has been systematically migrated from a full-page map into a structured, dense 6-panel workspace using a resilient CSS Grid shell. 

## Key Achievements

### 1. Structural CSS Grid Migration
- Replaced the floating `position: absolute` elements across the UI with a native CSS Grid map (`App.css` and `App.tsx`).
- Created dedicated placeholder regions for the 6-panel layout: Radar, Stream, Narrative Threads, Matrix, Anomaly Source, and Source Integrity.

### 2. State Management Upgrade (Global Filter)
- Expanded `FocusContext.tsx` to include `GlobalFilter` (managing `country`, `theme`, `timeRange`, and `lockedBy`).
- All interactive components (map nodes, text stream rows, and anomaly elements) now automatically cross-filter the remaining UI structure when clicked.
- Implemented the active Focus Lock visual states within `FocusIndicator.tsx`.

### 3. Global Radar Enhancements
- Transformed `Deck.gl` configuration in `App.tsx` from raw sentiment clustering into intensity-driven rendering.
- New color rules via `getIntensityColor` (`mapUtils.ts`):
  * **Spiking Action (Red)**: Node intensity heavily surpasses rolling 24h baseline (`multiplier > 1.5`).
  * **Positive Sentiment (Green)**: Stable non-spiking nodes above 0.15 threshold.
  * **Quiet Nodes (Sky Blue)**: Below or neutral baseline signals.
- Integrated a live-pulsating Stroke ring (`nodes-anomaly-pulse`) specifically tracking any anomalous nodes detected by `CrisisContext`.

### 4. New Core Panels Installed
- **SignalStream.tsx**: Component autonomously polls `/api/v2/signals` appending new incoming signals immediately to the scrolling feed format (`[Time] [Country] [Sentiment] [Topic]`). Velocity tracking monitors data flow rate directly against the backend timestamp counts.
- **AnomalyPanel.tsx**: Separated from the global toggle to a constantly-visible panel. Automatically reacts to `anomalies` streamed from the newly-updated polling interval in `CrisisContext`.
- **SourceIntegrityPanel.tsx**: Evaluates node source distributions (globally OR by the currently locked view) and mathematically calculates the `Diversity Index`, `Quality proxy` and `Concentration %`. Displays standard density bar-charts natively through flex layouts.

## Verification & Checks
- **Build Status**: TypeScript compiler (`tsc -b`) and `vite build` complete securely with **0 typings/syntax errors**.
- **Run Compatibility**: Verified parallel polling on `anomalies`, `focus`, and `signals` against backend endpoints functions correctly and deduplicates safely relying on `since` timestamps without stalling the React thread.
