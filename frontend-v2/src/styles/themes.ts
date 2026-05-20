export interface Theme {
    name: string;
    id: 'intel-noir' | 'retro-radar';
    colors: {
        bgPrimary: string;
        bgSecondary: string;
        bgTertiary: string;
        bgPanel: string;
        textPrimary: string;
        textSecondary: string;
        textMuted: string;
        borderSubtle: string;
        borderMedium: string;
        borderStrong: string;
        accentPrimary: string;
        accentSecondary: string;
        accentHighlight: string;
        severityNormal: string;
        severityNotable: string;
        severityElevated: string;
        severityCritical: string;
        sentimentPositive: string;
        sentimentNeutral: string;
        sentimentNegative: string;
        arcDefault: string;
        arcFocused: string;
        nodeGlow: string;
    };
    typography: {
        fontMono: string;
        fontSans: string;
    };
    spacing: {
        panelPadding: string;
        panelRadius: string;
        panelGap: string;
    };
}

export const THEME_INTEL_NOIR: Theme = {
    name: 'Intel Noir',
    id: 'intel-noir',
    colors: {
        bgPrimary: '#070d17',
        bgSecondary: '#0a1220',
        bgTertiary: '#0c182b',
        bgPanel: 'linear-gradient(180deg, rgba(12, 24, 43, 0.94) 0%, rgba(7, 13, 23, 0.91) 100%)',
        textPrimary: '#e2e8f0',
        textSecondary: 'rgba(226, 232, 240, 0.68)',
        textMuted: 'rgba(226, 232, 240, 0.42)',
        borderSubtle: 'rgba(29, 158, 117, 0.15)',
        borderMedium: 'rgba(29, 158, 117, 0.28)',
        borderStrong: 'rgba(104, 219, 174, 0.5)',
        accentPrimary: '#68dbae',
        accentSecondary: '#fbbf24',
        accentHighlight: '#4ade80',
        severityNormal: '#94a3b8',
        severityNotable: '#fbbf24',
        severityElevated: '#f97316',
        severityCritical: '#ef4444',
        sentimentPositive: '#4ade80',
        sentimentNeutral: '#94a3b8',
        sentimentNegative: '#f87171',
        arcDefault: 'rgba(104, 219, 174, 0.42)',
        arcFocused: 'rgba(104, 219, 174, 0.86)',
        nodeGlow: 'rgba(104, 219, 174, 0.56)',
    },
    typography: {
        fontMono: "'SF Mono', 'Fira Code', monospace",
        fontSans: "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif",
    },
    spacing: {
        panelPadding: '14px',
        panelRadius: '6px',
        panelGap: '10px',
    },
};

export const THEME_RETRO_RADAR: Theme = {
    name: 'Retro Radar',
    id: 'retro-radar',
    colors: {
        bgPrimary: '#0a1208',
        bgSecondary: '#0d1a0f',
        bgTertiary: '#142216',
        bgPanel: 'linear-gradient(180deg, rgba(10, 24, 12, 0.95) 0%, rgba(15, 35, 18, 0.92) 100%)',
        textPrimary: '#c8f7c5',
        textSecondary: '#7eb87a',
        textMuted: '#4a7048',
        borderSubtle: 'rgba(74, 222, 128, 0.15)',
        borderMedium: 'rgba(74, 222, 128, 0.3)',
        borderStrong: 'rgba(74, 222, 128, 0.5)',
        accentPrimary: '#4ade80',
        accentSecondary: '#22d3ee',
        accentHighlight: '#86efac',
        severityNormal: '#7eb87a',
        severityNotable: '#facc15',
        severityElevated: '#fb923c',
        severityCritical: '#f87171',
        sentimentPositive: '#86efac',
        sentimentNeutral: '#7eb87a',
        sentimentNegative: '#fca5a5',
        arcDefault: 'rgba(74, 222, 128, 0.5)',
        arcFocused: 'rgba(34, 211, 238, 0.9)',
        nodeGlow: 'rgba(74, 222, 128, 0.6)',
    },
    typography: {
        fontMono: "'VT323', 'Courier New', monospace",
        fontSans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    },
    spacing: {
        panelPadding: '16px',
        panelRadius: '8px',
        panelGap: '12px',
    },
};

export const THEMES: Record<string, Theme> = {
    'intel-noir': THEME_INTEL_NOIR,
    'retro-radar': THEME_RETRO_RADAR,
};

export const DEFAULT_THEME_ID = 'intel-noir';
