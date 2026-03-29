import React, { useState } from 'react';
import { ThemeSelector } from './ThemeSelector';

interface SettingsPanelProps {
    showTerminator: boolean;
    onToggleTerminator: (v: boolean) => void;
    sizeBoost: boolean;
    onToggleSizeBoost: (v: boolean) => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
    showTerminator,
    onToggleTerminator,
    sizeBoost,
    onToggleSizeBoost,
}) => {
    const [open, setOpen] = useState(false);

    if (!open) {
        return (
            <button
                onClick={() => setOpen(true)}
                style={{
                    background: 'var(--color-bg-tertiary)',
                    border: '1px solid var(--color-border-subtle)',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    color: 'var(--color-text-secondary)',
                    cursor: 'pointer',
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                }}
            >
                Settings
            </button>
        );
    }

    return (
        <div
            className="panel"
            style={{
                position: 'fixed',
                top: '70px',
                right: '20px',
                width: '280px',
                zIndex: 1100,
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                <span className="panel-header" style={{ margin: 0 }}>Settings</span>
                <button
                    onClick={() => setOpen(false)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer', fontSize: '16px' }}
                >
                    ×
                </button>
            </div>



            <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginBottom: '8px' }}>Visual Theme</div>
                <ThemeSelector />
            </div>

            <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginBottom: '8px' }}>Map Options</div>

                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', cursor: 'pointer' }}>
                    <input
                        type="checkbox"
                        checked={showTerminator}
                        onChange={(e) => onToggleTerminator(e.target.checked)}
                        style={{ accentColor: 'var(--color-accent-primary)' }}
                    />
                    <span style={{ fontSize: '12px', color: 'var(--color-text-primary)' }}>Show day/night overlay</span>
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                    <input
                        type="checkbox"
                        checked={sizeBoost}
                        onChange={(e) => onToggleSizeBoost(e.target.checked)}
                        style={{ accentColor: 'var(--color-accent-primary)' }}
                    />
                    <span style={{ fontSize: '12px', color: 'var(--color-text-primary)' }}>Boost node sizes</span>
                </label>
            </div>

            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-border-subtle)', paddingTop: '12px' }}>
                Settings are saved locally.
            </div>
        </div>
    );
};

