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
        bgPrimary: '#0a0f1a',
        bgSecondary: '#0d1526',
        bgTertiary: '#111d32',
        bgPanel: 'linear-gradient(180deg, rgba(10, 22, 40, 0.95) 0%, rgba(13, 31, 60, 0.92) 100%)',
        textPrimary: '#e2e8f0',
        textSecondary: '#94a3b8',
        textMuted: '#64748b',
        borderSubtle: 'rgba(59, 130, 246, 0.15)',
        borderMedium: 'rgba(59, 130, 246, 0.3)',
        borderStrong: 'rgba(59, 130, 246, 0.5)',
        accentPrimary: '#38bdf8',
        accentSecondary: '#fbbf24',
        accentHighlight: '#67e8f9',
        severityNormal: '#94a3b8',
        severityNotable: '#fbbf24',
        severityElevated: '#f97316',
        severityCritical: '#ef4444',
        sentimentPositive: '#4ade80',
        sentimentNeutral: '#94a3b8',
        sentimentNegative: '#f87171',
        arcDefault: 'rgba(100, 150, 200, 0.6)',
        arcFocused: 'rgba(56, 189, 248, 0.9)',
        nodeGlow: 'rgba(251, 191, 36, 0.6)',
    },
    typography: {
        fontMono: "'JetBrains Mono', 'Fira Code', 'SF Mono', monospace",
        fontSans: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
    },
    spacing: {
        panelPadding: '16px',
        panelRadius: '12px',
        panelGap: '12px',
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
