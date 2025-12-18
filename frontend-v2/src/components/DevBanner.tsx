import React from 'react';

export const DevBanner: React.FC = () => {
    if (import.meta.env.PROD) return null;

    return (
        <div style={{
            position: 'fixed',
            bottom: '10px',
            right: '10px',
            background: 'rgba(34, 197, 94, 0.9)',
            color: 'white',
            padding: '6px 12px',
            borderRadius: '4px',
            fontSize: '12px',
            fontFamily: 'monospace',
            zIndex: 9999,
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
        }}>
            <strong>frontend-v2</strong> | :3000 → :8000 | MapLibre
        </div>
    );
};
