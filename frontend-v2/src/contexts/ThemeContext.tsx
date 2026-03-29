import React, { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react';
import type { Theme } from '../styles/themes';
import { THEMES, DEFAULT_THEME_ID } from '../styles/themes';

interface ThemeContextValue {
    theme: Theme;
    themeId: string;
    setTheme: (id: string) => void;
    availableThemes: { id: string; name: string }[];
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

const STORAGE_KEY = 'observatory_theme';

function kebabCase(str: string): string {
    return str.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
}

function applyThemeToCSS(theme: Theme): void {
    const root = document.documentElement;

    Object.entries(theme.colors).forEach(([key, value]) => {
        root.style.setProperty(`--color-${kebabCase(key)}`, value);
    });

    root.style.setProperty('--font-mono', theme.typography.fontMono);
    root.style.setProperty('--font-sans', theme.typography.fontSans);
    root.style.setProperty('--panel-padding', theme.spacing.panelPadding);
    root.style.setProperty('--panel-radius', theme.spacing.panelRadius);
    root.style.setProperty('--panel-gap', theme.spacing.panelGap);
    root.setAttribute('data-theme', theme.id);
}

export const ThemeProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
    const [themeId, setThemeId] = useState<string>(() => {
        const stored = localStorage.getItem(STORAGE_KEY);
        return stored && THEMES[stored] ? stored : DEFAULT_THEME_ID;
    });

    const theme = THEMES[themeId] || THEMES[DEFAULT_THEME_ID];

    useEffect(() => {
        applyThemeToCSS(theme);
    }, [theme]);

    const setTheme = useCallback((id: string) => {
        if (THEMES[id]) {
            setThemeId(id);
            localStorage.setItem(STORAGE_KEY, id);
        }
    }, []);

    const availableThemes = Object.entries(THEMES).map(([id, t]) => ({
        id,
        name: t.name,
    }));

    return (
        <ThemeContext.Provider value={{ theme, themeId, setTheme, availableThemes }}>
            {children}
        </ThemeContext.Provider>
    );
};

export const useTheme = (): ThemeContextValue => {
    const ctx = useContext(ThemeContext);
    if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
    return ctx;
};
