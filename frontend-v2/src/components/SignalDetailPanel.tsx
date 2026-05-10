import React from 'react'
import { getThemeLabel, getThemeIcon } from '../lib/themeLabels'
import './SignalDetailPanel.css'

export interface Signal {
    id: number
    timestamp: string
    country: string
    source: string
    url: string
    headline: string | null
    sentiment: number
    themes: string[]
    persons: string[]
}

interface Props {
    signal: Signal
    onClose: () => void
    onThemeClick: (theme: string) => void
    onCountryClick: (country: string) => void
    onPersonClick: (person: string) => void
    allowlist?: string[]
}

const getSentimentColor = (s: number) => {
    if (s > 0.1) return '#4ade80'
    if (s < -0.1) return '#f87171'
    return '#94a3b8'
}

const getSentimentLabel = (s: number) => {
    if (s > 1) return 'POSITIVE'
    if (s > 0.1) return 'SLIGHT POS'
    if (s < -1) return 'NEGATIVE'
    if (s < -0.1) return 'SLIGHT NEG'
    return 'NEUTRAL'
}

const formatTimestamp = (ts: string) => {
    try {
        return new Date(ts).toLocaleString(undefined, {
            month: 'short', day: 'numeric',
            hour: '2-digit', minute: '2-digit'
        })
    } catch {
        return ts
    }
}

const barLeft = (s: number) => {
    const clamped = Math.max(-3, Math.min(3, s))
    if (clamped >= 0) {
        return { left: '50%', width: `${(clamped / 3) * 50}%` }
    }
    const w = (Math.abs(clamped) / 3) * 50
    return { left: `${50 - w}%`, width: `${w}%` }
}

export const SignalDetailPanel: React.FC<Props> = ({
    signal, onClose, onThemeClick, onCountryClick, onPersonClick, allowlist = []
}) => {
    const getSourceClass = (source: string) => {
        const s = source.toLowerCase()
        if (allowlist.some(a => s.includes(a.toLowerCase()))) return 'source-trusted'
        if (s.includes('yahoo') || s.includes('msn') || s.includes('aol') || s.includes('newsbreak')) return 'source-tabloid'
        return ''
    }

    const barStyle = barLeft(signal.sentiment)
    const sentimentColor = getSentimentColor(signal.sentiment)

    const handleOverlayClick = (e: React.MouseEvent) => {
        if (e.target === e.currentTarget) onClose()
    }

    return (
        <div className="signal-detail-overlay" onClick={handleOverlayClick}>
            <div className="signal-detail-panel">
                <div className="sdp-header">
                    <span className="sdp-label">Signal Detail</span>
                    <button className="sdp-close" onClick={onClose}>×</button>
                </div>

                <div className="sdp-body">
                    <div className="sdp-headline">
                        {signal.headline || `Signal from ${signal.source}`}
                    </div>

                    <div className="sdp-meta-row">
                        <span
                            className="sdp-country clickable"
                            onClick={() => { onCountryClick(signal.country); onClose(); }}
                        >
                            {signal.country || 'GLO'}
                        </span>
                        <span className={`sdp-source ${getSourceClass(signal.source)}`}>
                            {signal.source}
                        </span>
                        <span className="sdp-time">{formatTimestamp(signal.timestamp)}</span>
                    </div>

                    <div className="sdp-divider" />

                    <div>
                        <div className="sdp-section-label">Sentiment</div>
                        <div className="sdp-sentiment-row">
                            <span className="sdp-sentiment-label" style={{ color: sentimentColor }}>
                                {getSentimentLabel(signal.sentiment)}
                            </span>
                            <div className="sdp-sentiment-bar-track">
                                <div
                                    className="sdp-sentiment-bar-fill"
                                    style={{
                                        left: barStyle.left,
                                        width: barStyle.width,
                                        background: sentimentColor,
                                    }}
                                />
                            </div>
                            <span className="sdp-sentiment-value">
                                {signal.sentiment > 0 ? '+' : ''}{signal.sentiment.toFixed(2)}
                            </span>
                        </div>
                    </div>

                    {signal.themes.length > 0 && (
                        <div>
                            <div className="sdp-section-label">Themes</div>
                            <div className="sdp-tags">
                                {signal.themes.map(t => (
                                    <span
                                        key={t}
                                        className="sdp-theme-tag"
                                        onClick={() => { onThemeClick(t); onClose(); }}
                                    >
                                        {getThemeIcon(t)} {getThemeLabel(t)}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}

                    {signal.persons.length > 0 && (
                        <div>
                            <div className="sdp-section-label">People</div>
                            <div className="sdp-tags">
                                {signal.persons.map(p => (
                                    <span
                                        key={p}
                                        className="sdp-person-tag"
                                        onClick={() => { onPersonClick(p); onClose(); }}
                                    >
                                        {p}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                <div className="sdp-footer">
                    <a
                        className="sdp-read-btn"
                        href={signal.url}
                        target="_blank"
                        rel="noopener noreferrer"
                    >
                        Read original article ↗
                    </a>
                </div>
            </div>
        </div>
    )
}
