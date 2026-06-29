import React, { useState } from 'react';
import { ThemeSelector } from './ThemeSelector';

interface SettingsPanelProps {
    showTerminator: boolean;
    onToggleTerminator: (v: boolean) => void;
    sizeBoost: boolean;
    onToggleSizeBoost: (v: boolean) => void;
    mapProjection?: 'mercator' | 'equalEarth';
    onToggleProjection?: () => void;
    // Controlled mode (#152): when `open` is provided the trigger button is
    // not rendered — the command bar's overflow menu owns the toggle.
    open?: boolean;
    onClose?: () => void;
}

export const SettingsPanel: React.FC<SettingsPanelProps> = ({
    showTerminator,
    onToggleTerminator,
    sizeBoost,
    onToggleSizeBoost,
    mapProjection,
    onToggleProjection,
    open: controlledOpen,
    onClose,
}) => {
    const [internalOpen, setInternalOpen] = useState(false);
    const isControlled = controlledOpen !== undefined;
    const open = isControlled ? controlledOpen : internalOpen;
    const close = () => { if (isControlled) onClose?.(); else setInternalOpen(false); };

    if (!open) {
        if (isControlled) return null;
        return (
            <button
                onClick={() => setInternalOpen(true)}
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
                    onClick={close}
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

                {mapProjection && onToggleProjection && (
                    <div style={{ marginBottom: '14px' }}>
                        <div style={{ fontSize: '12px', color: 'var(--color-text-primary)', marginBottom: '6px' }}>Projection</div>
                        <div style={{ display: 'flex', gap: '6px' }}>
                            {(['equalEarth', 'mercator'] as const).map((proj) => (
                                <button
                                    key={proj}
                                    onClick={() => { if (mapProjection !== proj) onToggleProjection(); }}
                                    className={`layer-btn ${mapProjection === proj ? 'active' : ''}`}
                                    style={{ flex: 1, fontSize: '11px' }}
                                    data-tip={proj === 'equalEarth'
                                        ? 'Equal-area strip — honest country sizes, infinite horizontal pan'
                                        : 'Web Mercator — familiar, but inflates the north'}
                                >
                                    {proj === 'equalEarth' ? 'EQUAL AREA' : 'MERCATOR'}
                                </button>
                            ))}
                        </div>
                        <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', display: 'block', marginTop: '5px' }}>
                            Equal-area shows true country sizes (no north inflation).
                        </span>
                    </div>
                )}

                <label style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', marginBottom: '12px', cursor: 'pointer' }}>
                    <input
                        type="checkbox"
                        checked={showTerminator}
                        onChange={(e) => onToggleTerminator(e.target.checked)}
                        style={{ accentColor: 'var(--color-accent-primary)', marginTop: '2px', flexShrink: 0 }}
                    />
                    <span>
                        <span style={{ fontSize: '12px', color: 'var(--color-text-primary)', display: 'block' }}>Day/Night Shadow <span style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>(experimental)</span></span>
                        <span style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>Soft twilight overlay based on current UTC time</span>
                    </span>
                </label>

                <label style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', cursor: 'pointer' }}>
                    <input
                        type="checkbox"
                        checked={sizeBoost}
                        onChange={(e) => onToggleSizeBoost(e.target.checked)}
                        style={{ accentColor: 'var(--color-accent-primary)', marginTop: '2px', flexShrink: 0 }}
                    />
                    <span>
                        <span style={{ fontSize: '12px', color: 'var(--color-text-primary)', display: 'block' }}>Boost node sizes</span>
                        <span style={{ fontSize: '10px', color: 'var(--color-text-muted)' }}>Makes low-signal countries more visible</span>
                    </span>
                </label>
            </div>

            <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', borderTop: '1px solid var(--color-border-subtle)', paddingTop: '12px' }}>
                Settings are saved locally.
            </div>
        </div>
    );
};

