/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import type { Theme } from '../styles/themes';
import { THEMES, DEFAULT_THEME_ID } from '../styles/themes';
import {
    resolveConsoleThemeId,
    toggledConsoleThemeId,
    readStoredConsoleThemeId,
    storeConsoleThemeId,
} from '../lib/consoleTheme';

interface ThemeContextValue {
    theme: Theme;
    themeId: string;
    setTheme: (id: string) => void;
    /** Sun/moon flip: dark-scheme -> emerald day, light -> emerald night.
        Persists as a manual override (auto clock/OS resolution stops). */
    toggleDayNight: () => void;
    availableThemes: { id: string; name: string }[];
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function kebabCase(str: string): string {
    return str.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
}

// Family keys any theme may override; inline values are REMOVED when the
// active theme carries no families so the static variables.css set applies.
const FAM_KEYS = ['conflict', 'governance', 'health', 'economy', 'society', 'culture', 'other'];

function applyThemeToCSS(theme: Theme): void {
    const root = document.documentElement;

    Object.entries(theme.colors).forEach(([key, value]) => {
        root.style.setProperty(`--color-${kebabCase(key)}`, value);
    });

    FAM_KEYS.forEach((key) => {
        const value = theme.families?.[key];
        if (value) root.style.setProperty(`--fam-${key}`, value);
        else root.style.removeProperty(`--fam-${key}`);
    });

    root.style.setProperty('--font-mono', theme.typography.fontMono);
    root.style.setProperty('--font-sans', theme.typography.fontSans);
    root.style.setProperty('--panel-padding', theme.spacing.panelPadding);
    root.style.setProperty('--panel-radius', theme.spacing.panelRadius);
    root.style.setProperty('--panel-gap', theme.spacing.panelGap);
    // Native form controls / scrollbars follow the active scheme.
    root.style.colorScheme = theme.scheme;
    root.setAttribute('data-theme', theme.id);
}

const DARK_QUERY = '(prefers-color-scheme: dark)';

function osPrefersDark(): boolean {
    return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
        ? window.matchMedia(DARK_QUERY).matches
        : false;
}

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    // Default = auto day/night over the emerald pair (lib/consoleTheme.ts):
    // stored override (atlas-console-theme) wins, else clock 19-7 / OS dark.
    const [themeId, setThemeId] = useState<string>(() =>
        resolveConsoleThemeId(new Date(), osPrefersDark(), readStoredConsoleThemeId()),
    );
    const hasOverrideRef = useRef<boolean>(readStoredConsoleThemeId() !== null);

    const theme = THEMES[themeId] || THEMES[DEFAULT_THEME_ID];

    useEffect(() => {
        applyThemeToCSS(theme);
    }, [theme]);

    // Follow the OS preference live — but only while the user has no stored
    // override (their pick is never fought). Same semantics as the reader.
    useEffect(() => {
        if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return;
        const mq = window.matchMedia(DARK_QUERY);
        const onChange = (e: MediaQueryListEvent) => {
            if (hasOverrideRef.current) return;
            setThemeId(resolveConsoleThemeId(new Date(), e.matches, null));
        };
        mq.addEventListener('change', onChange);
        return () => mq.removeEventListener('change', onChange);
    }, []);

    const setTheme = useCallback((id: string) => {
        if (THEMES[id]) {
            setThemeId(id);
            storeConsoleThemeId(id);
            hasOverrideRef.current = true;
        }
    }, []);

    const toggleDayNight = useCallback(() => {
        setThemeId((prev) => {
            const next = toggledConsoleThemeId(THEMES[prev] || THEMES[DEFAULT_THEME_ID]);
            storeConsoleThemeId(next);
            hasOverrideRef.current = true;
            return next;
        });
    }, []);

    const availableThemes = Object.entries(THEMES).map(([id, t]) => ({
        id,
        name: t.name,
    }));

    return (
        <ThemeContext.Provider value={{ theme, themeId, setTheme, toggleDayNight, availableThemes }}>
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = (): ThemeContextValue => {
    const ctx = useContext(ThemeContext);
    if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
    return ctx;
};
