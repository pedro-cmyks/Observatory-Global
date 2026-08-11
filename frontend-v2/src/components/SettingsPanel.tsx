import React, { useState } from 'react';
import { ThemeSelector } from './ThemeSelector';
import {
    PAGE_LANGUAGE_OPTIONS,
    browserLanguage,
    getStoredPageLanguage,
    setPageLanguage,
    usePageLanguage,
} from '../lib/pageLanguage';

interface SettingsPanelProps {
    showTerminator: boolean;
    onToggleTerminator: (v: boolean) => void;
    sizeBoost: boolean;
    onToggleSizeBoost: (v: boolean) => void;
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
    open: controlledOpen,
    onClose,
}) => {
    const [internalOpen, setInternalOpen] = useState(false);
    // Page language (translation target). Subscribed so the select reflects
    // changes immediately; content components re-target via the same store.
    const pageLang = usePageLanguage();
    const storedLang = getStoredPageLanguage();
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
                <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginBottom: '8px' }}>Page Language</div>
                <select
                    value={storedLang ?? 'auto'}
                    onChange={(e) => setPageLanguage(e.target.value === 'auto' ? null : e.target.value)}
                    aria-label="Page language — headlines and quotes translate into this language"
                    style={{
                        width: '100%',
                        background: 'var(--color-bg-tertiary)',
                        border: '1px solid var(--color-border-subtle)',
                        borderRadius: '6px',
                        padding: '8px',
                        minHeight: '44px',
                        color: 'var(--color-text-primary)',
                        fontSize: '12px',
                        cursor: 'pointer',
                    }}
                >
                    <option value="auto">Auto — browser language ({browserLanguage().toUpperCase()})</option>
                    {PAGE_LANGUAGE_OPTIONS.map(o => (
                        <option key={o.code} value={o.code}>{o.label} ({o.code.toUpperCase()})</option>
                    ))}
                </select>
                <span style={{ display: 'block', fontSize: '10px', color: 'var(--color-text-muted)', marginTop: '6px' }}>
                    Headlines, labels and source quotes translate into this language ({pageLang.toUpperCase()} now).
                    Source names and verification chips are never translated.
                </span>
            </div>

            <div style={{ marginBottom: '16px' }}>
                <div style={{ fontSize: '11px', color: 'var(--color-text-muted)', marginBottom: '8px' }}>Map Options</div>

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

