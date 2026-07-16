export interface Theme {
    name: string;
    id: 'intel-noir' | 'retro-radar' | 'emerald-light' | 'emerald-dark';
    /** Drives the CSS color-scheme property + the sun/moon day-night flip. */
    scheme: 'light' | 'dark';
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
        info: string;        // cyan lane (trends/wiki/attention badges)
        onAccent: string;    // text on solid accent grounds
        // RGB channel triplets ("r, g, b") so alpha-varied component CSS can
        // theme via rgba(var(--color-ink-rgb), .55) instead of hardcoding the
        // intel-noir literals (the #247 adoption-gap fix, done mechanically).
        inkRgb: string;          // body-text family
        accentDeepRgb: string;   // border/tint emerald (noir: 29,158,117)
        accentBrightRgb: string; // glow/highlight emerald (noir: 104,219,174)
        shellRgb: string;        // deepest ground (noir: 7,13,23)
        raiseRgb: string;        // raised panel ground (noir: 12,24,43)
        infoRgb: string;         // cyan channel triplet
        neutralRgb: string;      // cool-neutral text/chip channel triplet
        subjPerson: string;      // typed-subject PERSON badge (Ocean --subj-person)
    };
    /** Category-family palette (--fam-*). Omit to keep the static
        variables.css dark-tuned set (intel-noir / retro-radar). */
    families?: Record<string, string>;
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

const GEIST_TYPOGRAPHY = {
    fontMono: "'Geist Mono Variable', 'Geist Mono', 'SF Mono', monospace",
    fontSans: "'Geist Variable', 'Geist', -apple-system, BlinkMacSystemFont, sans-serif",
};

const CONSOLE_SPACING = {
    panelPadding: '14px',
    panelRadius: '6px',
    panelGap: '10px',
};

// Ocean reference (console-l2.html): panels are 12px-rounded cards on paper.
// Emerald-only — intel-noir/retro keep the 6px console radius exactly.
const EMERALD_SPACING = {
    panelPadding: '14px',
    panelRadius: '12px',
    panelGap: '10px',
};

export const THEME_INTEL_NOIR: Theme = {
    name: 'Intel Noir',
    id: 'intel-noir',
    scheme: 'dark',
    colors: {
        bgPrimary: '#070d17',
        bgSecondary: '#0a1220',
        bgTertiary: '#0c182b',
        bgPanel: 'linear-gradient(180deg, rgba(12, 24, 43, 0.94) 0%, rgba(7, 13, 23, 0.91) 100%)',
        textPrimary: '#e2e8f0',
        textSecondary: 'rgba(226, 232, 240, 0.68)',
        textMuted: 'rgba(226, 232, 240, 0.55)', // #247 A1: 0.55 = AA floor; 0.42 failed 3.52:1
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
        // Identity triplets: these ARE the literals component CSS carried, so
        // intel-noir renders byte-identically after the rgba(var()) sweep.
        info: '#38bdf8',
        onAccent: '#003827',
        infoRgb: '56, 189, 248',
        neutralRgb: '148, 163, 184',
        subjPerson: '#a78bfa', // the literal person-badge violet noir always used
        inkRgb: '226, 232, 240',
        accentDeepRgb: '29, 158, 117',
        accentBrightRgb: '104, 219, 174',
        shellRgb: '7, 13, 23',
        raiseRgb: '12, 24, 43',
    },
    typography: GEIST_TYPOGRAPHY,
    spacing: CONSOLE_SPACING,
};

export const THEME_RETRO_RADAR: Theme = {
    name: 'Retro Radar',
    id: 'retro-radar',
    scheme: 'dark',
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
        info: '#22d3ee',
        onAccent: '#003827',
        infoRgb: '34, 211, 238',
        neutralRgb: '126, 184, 122',
        subjPerson: '#a78bfa',
        inkRgb: '200, 247, 197',
        accentDeepRgb: '74, 222, 128',
        accentBrightRgb: '74, 222, 128',
        shellRgb: '10, 18, 8',
        raiseRgb: '13, 26, 15',
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

// ---------------------------------------------------------------------------
// EMERALD pair — the shipped Atlas identity (L0/L1/L3 reader pages, console
// reference spec console-l2.html). Light is the risky one (the console was
// designed dark): every text/chip token below clears WCAG AA on its ground —
// textMuted #5a6861 = 5.2:1 on paper / 5.9:1 on white; accentPrimary #0f7b5a
// = 5.3:1 on white; severity/sentiment use the deep semantic set (#a86a0c /
// #a8412a), never the bright dark-tuned ones.
// ---------------------------------------------------------------------------

export const THEME_EMERALD_LIGHT: Theme = {
    name: 'Emerald Day',
    id: 'emerald-light',
    scheme: 'light',
    colors: {
        bgPrimary: '#eef1ef',   // paper
        bgSecondary: '#f4f6f4', // surface-2
        bgTertiary: '#e6ebe7',  // chip ground
        bgPanel: '#ffffff',     // surface (cards are solid white on paper)
        textPrimary: '#14201b', // ink
        textSecondary: '#3a4842',
        textMuted: '#5a6861',   // AA: 5.2:1 on paper, 4.9:1 on chip
        borderSubtle: '#d6dcd7', // line
        borderMedium: '#c2ccc4',
        borderStrong: 'rgba(15, 123, 90, 0.55)',
        accentPrimary: '#0f7b5a',
        accentSecondary: '#8f5b0a',  // warn — AA on white 5.7 / paper 5.0 / chip 4.7 (was #a86a0c: 4.44 on white, 3.90 on paper)
        accentHighlight: '#0d6b4f',
        severityNormal: '#6b7772',
        severityNotable: '#8f5b0a',
        severityElevated: '#9d4f16',
        severityCritical: '#a8412a',
        sentimentPositive: '#0f7b5a',
        sentimentNeutral: '#6b7772',
        sentimentNegative: '#a8412a',
        arcDefault: 'rgba(15, 123, 90, 0.42)',
        arcFocused: 'rgba(15, 123, 90, 0.86)',
        nodeGlow: 'rgba(15, 123, 90, 0.45)',
        info: '#0e8fa8',
        onAccent: '#ffffff',
        infoRgb: '14, 143, 168',
        neutralRgb: '44, 56, 50',
        subjPerson: '#7a5aa6', // Ocean --subj-person, light-tuned (4.9:1 on white)
        inkRgb: '20, 32, 27',
        accentDeepRgb: '15, 123, 90',
        accentBrightRgb: '15, 123, 90',
        shellRgb: '238, 241, 239',
        raiseRgb: '255, 255, 255',
    },
    families: {
        // Light-tuned family palette (console-l2 reference, CVD-validated)
        conflict: '#c23f2e',
        governance: '#a3791f',
        health: '#1789a8',
        economy: '#3d7fd1',
        society: '#c9528a',
        culture: '#5b6472',
        other: '#8a938c',
    },
    typography: GEIST_TYPOGRAPHY,
    spacing: EMERALD_SPACING,
};

export const THEME_EMERALD_DARK: Theme = {
    name: 'Emerald Night',
    id: 'emerald-dark',
    scheme: 'dark',
    colors: {
        bgPrimary: '#0d1512',   // paper
        bgSecondary: '#0f1a15',
        bgTertiary: '#1b2620',  // chip ground
        bgPanel: 'linear-gradient(180deg, rgba(19, 30, 25, 0.96) 0%, rgba(13, 21, 18, 0.93) 100%)',
        textPrimary: '#e7ece8', // ink
        textSecondary: '#b9c4bd',
        textMuted: '#8a988f',   // AA: 5.9:1 on paper
        borderSubtle: '#243029', // line
        borderMedium: '#2f3d34',
        borderStrong: 'rgba(47, 208, 160, 0.5)',
        accentPrimary: '#2fd0a0',
        accentSecondary: '#e0a54c',  // warn
        accentHighlight: '#68dbae',
        severityNormal: '#8a988f',
        severityNotable: '#e0a54c',
        severityElevated: '#e08c55',
        severityCritical: '#e07a5f',
        sentimentPositive: '#2fd0a0',
        sentimentNeutral: '#8a988f',
        sentimentNegative: '#e07a5f',
        arcDefault: 'rgba(47, 208, 160, 0.42)',
        arcFocused: 'rgba(47, 208, 160, 0.86)',
        nodeGlow: 'rgba(47, 208, 160, 0.56)',
        info: '#49b6d0',
        onAccent: '#0d1512',
        infoRgb: '73, 182, 208',
        neutralRgb: '138, 152, 143',
        subjPerson: '#b79ad6', // Ocean --subj-person, dark-tuned
        inkRgb: '231, 236, 232',
        accentDeepRgb: '29, 158, 117',
        accentBrightRgb: '47, 208, 160',
        shellRgb: '13, 21, 18',
        raiseRgb: '19, 30, 25',
    },
    families: {
        // Dark-tuned family palette — mirrors the static variables.css set
        conflict: '#cc5d47',
        governance: '#b58733',
        health: '#0f92b0',
        economy: '#5183cc',
        society: '#c8659a',
        culture: '#8a949c',
        other: '#64748b',
    },
    typography: GEIST_TYPOGRAPHY,
    spacing: EMERALD_SPACING,
};

export const THEMES: Record<string, Theme> = {
    'emerald-light': THEME_EMERALD_LIGHT,
    'emerald-dark': THEME_EMERALD_DARK,
    'intel-noir': THEME_INTEL_NOIR,
    'retro-radar': THEME_RETRO_RADAR,
};

/** Last-resort fallback only — the real default is auto day/night over the
    emerald pair (lib/consoleTheme.ts). */
export const DEFAULT_THEME_ID = 'emerald-dark';
