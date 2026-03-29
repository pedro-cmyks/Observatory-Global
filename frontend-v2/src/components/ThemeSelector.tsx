import React from 'react';
import { useTheme } from '../contexts/ThemeContext';

export const ThemeSelector: React.FC = () => {
    const { themeId, setTheme, availableThemes } = useTheme();

    return (
        <div
            style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '4px 8px',
                background: 'var(--color-bg-tertiary)',
                borderRadius: '6px',
                border: '1px solid var(--color-border-subtle)',
            }}
        >
            <span style={{ fontSize: '11px', color: 'var(--color-text-muted)' }}>Theme:</span>
            <select
                value={themeId}
                onChange={(e) => setTheme(e.target.value)}
                style={{
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--color-text-primary)',
                    fontSize: '12px',
                    cursor: 'pointer',
                    outline: 'none',
                }}
            >
                {availableThemes.map((t) => (
                    <option key={t.id} value={t.id} style={{ background: '#1a1a2e' }}>
                        {t.name}
                    </option>
                ))}
            </select>
        </div>
    );
};
