// Time range types for the application
export type TimeRange = '1h' | '6h' | '12h' | '24h' | '1w' | '1m' | '3m' | 'record';

export const TIME_RANGE_LABELS: Record<TimeRange, string> = {
    '1h': '1 Hour',
    '6h': '6 Hours',
    '12h': '12 Hours',
    '24h': '24 Hours',
    '1w': '1 Week',
    '1m': '1 Month',
    '3m': '3 Months',
    'record': 'All Time'
};

export const TIME_RANGE_OPTIONS: TimeRange[] = ['1h', '6h', '12h', '24h', '1w', '1m', '3m', 'record'];

// Convert time range to hours for backward compatibility
export function timeRangeToHours(range: TimeRange): number {
    switch (range) {
        case '1h': return 1;
        case '6h': return 6;
        case '12h': return 12;
        case '24h': return 24;
        case '1w': return 168;
        case '1m': return 720;
        case '3m': return 2160;
        case 'record': return 8760;
    }
}

// ── S4: TIME AS A VIEW (Pedro approved 2026-07-05; time-as-dimension spec) ──
// The selector no longer re-windows AMBIENT data. Ambient surfaces (map
// nodes/flows/heat, the global threads list, the Brief prefetch) always show
// the LIVE picture; looking back is an investigative act — the globe
// scrubber (whose SPAN the selector drives) and the focused/detail surfaces
// (which still follow the selected lens: focus summary, theme detail,
// country view, conflict markers).
// Kill-switch: TIME_IS_VIEW = false restores the old everything-re-windows
// behavior in one line.
export const TIME_IS_VIEW = true;

/** The live-picture range every ambient surface pins to under S4. */
export const AMBIENT_RANGE: TimeRange = '24h';

/** Effective range for ambient (map/threads/brief) data fetches. */
export function ambientRange(selected: TimeRange): TimeRange {
    return TIME_IS_VIEW ? AMBIENT_RANGE : selected;
}

/** Globe-scrubber span (days) driven by the view selector: sub-week lenses
 *  keep a 7-day floor (a scrubber needs room), 1w→7, 1m→30, 3m/record→90
 *  (the replay endpoint's cap). */
export function timeRangeToViewDays(range: TimeRange): number {
    return Math.max(7, Math.min(90, Math.ceil(timeRangeToHours(range) / 24)));
}
