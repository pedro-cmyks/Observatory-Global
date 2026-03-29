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
