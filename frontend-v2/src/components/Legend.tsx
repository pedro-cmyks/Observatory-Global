import React, { useState } from 'react'

export const Legend: React.FC = () => {
    const [collapsed, setCollapsed] = useState(false)

    if (collapsed) {
        return (
            <button
                onClick={() => setCollapsed(false)}
                className="panel"
                style={{
                    position: 'fixed',
                    bottom: '20px',
                    left: '20px',
                    padding: '8px 12px',
                    cursor: 'pointer',
                    zIndex: 800,
                    fontSize: '12px',
                    color: 'var(--color-text-secondary)',
                    border: '1px solid var(--color-border-subtle)',
                }}
            >
                Legend
            </button>
        )
    }

    return (
        <div
            className="panel"
            style={{
                position: 'fixed',
                bottom: '20px',
                left: '20px',
                minWidth: '240px',
                zIndex: 800,
            }}
        >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <span className="panel-header" style={{ margin: 0 }}>Legend</span>
                <button
                    onClick={() => setCollapsed(true)}
                    style={{ background: 'transparent', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer' }}
                >
                    ×
                </button>
            </div>

            {/* Nodes Section */}
            <div style={{ marginBottom: '16px' }}>
                <div
                    title="Nodes representing countries. Larger nodes indicate higher news volume."
                    style={{ color: 'var(--color-accent-primary)', fontSize: '10px', textTransform: 'uppercase', marginBottom: '8px', cursor: 'help' }}>
                    Nodes (Countries)
                </div>

                {/* Size Examples */}
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', marginBottom: '8px' }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--color-sentiment-neutral)', margin: '0 auto 4px' }} />
                        <span className="metric-value" style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>&lt;100</span>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ width: '20px', height: '20px', borderRadius: '50%', background: 'var(--color-sentiment-neutral)', margin: '0 auto 4px' }} />
                        <span className="metric-value" style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>100-1K</span>
                    </div>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--color-sentiment-neutral)', margin: '0 auto 4px' }} />
                        <span className="metric-value" style={{ fontSize: '9px', color: 'var(--color-text-muted)' }}>&gt;1K</span>
                    </div>
                </div>
                <div title="The size of the node represents the total number of news signals (mentions/articles) for that country." style={{ fontSize: '10px', color: 'var(--color-text-muted)', marginBottom: '8px', cursor: 'help' }}>
                    Size = Signal volume (log scale)
                </div>

                {/* Sentiment Colors */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }} title="Average GDELT sentiment score > 0.1 (Scale: -1.0 to +1.0). Indicates generally positive news coverage.">
                        <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--color-sentiment-positive)' }} />
                        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>Positive tone</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }} title="Average GDELT sentiment score between -0.1 and 0.1. Indicates balanced or neutral coverage.">
                        <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--color-sentiment-neutral)' }} />
                        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>Neutral tone</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }} title="Average GDELT sentiment score < -0.1. Indicates generally negative or critical news coverage.">
                        <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--color-sentiment-negative)' }} />
                        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>Negative tone</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }} title="Current signal volume is significantly higher (>2 standard deviations) than the 7-day rolling average.">
                        <span style={{ width: '12px', height: '12px', borderRadius: '50%', background: 'var(--color-accent-secondary)', boxShadow: '0 0 8px var(--color-accent-secondary)' }} />
                        <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>Anomaly (pulsing)</span>
                    </div>
                </div>
            </div>

            {/* Flows Section */}
            <div>
                <div
                    title="Co-occurrence of themes between countries"
                    style={{ color: 'var(--color-accent-primary)', fontSize: '10px', textTransform: 'uppercase', marginBottom: '8px', cursor: 'help' }}>
                    Flows (Connections)
                </div>
                <div title="Strength of connection (Jaccard similarity)" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', cursor: 'help' }}>
                    <div style={{ width: '30px', height: '3px', background: 'linear-gradient(90deg, var(--color-accent-primary), var(--color-accent-secondary))', borderRadius: '2px' }} />
                    <span style={{ fontSize: '11px', color: 'var(--color-text-primary)' }}>Width = Correlation strength</span>
                </div>
                <div style={{ fontSize: '10px', color: 'var(--color-severity-notable)', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span style={{ color: 'var(--color-severity-notable)', fontWeight: 600 }}>Note:</span>
                    <span>Non-directional. Shared attention, not causation.</span>
                </div>
            </div>
        </div>
    )
}
