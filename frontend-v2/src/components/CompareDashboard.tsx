import type { ReactNode } from 'react'
import { X } from 'lucide-react'
import './CompareDashboard.css'

interface CompareDashboardProps {
    modeLabel: string
    leftLabel: string
    rightLabel: string
    accent?: string
    onClose: () => void
    children: [ReactNode, ReactNode]
}

export function CompareDashboard({
    modeLabel,
    leftLabel,
    rightLabel,
    accent = '#38bdf8',
    onClose,
    children,
}: CompareDashboardProps) {
    return (
        <div className="compare-dashboard-overlay">
            <div className="compare-dashboard-header">
                <div className="compare-dashboard-title">
                    <span>{modeLabel}</span>
                    <strong style={{ color: accent }}>{leftLabel}</strong>
                    <em>vs</em>
                    <strong style={{ color: accent }}>{rightLabel}</strong>
                </div>
                <button className="compare-dashboard-close" onClick={onClose} aria-label="Close comparison" data-tip="Close comparison">
                    <X size={16} />
                </button>
            </div>

            <div className="compare-dashboard-content">
                <section className="compare-dashboard-pane" aria-label={`${leftLabel} comparison pane`}>
                    <div className="compare-dashboard-pane-label" style={{ borderColor: accent }}>{leftLabel}</div>
                    {children[0]}
                </section>
                <section className="compare-dashboard-pane" aria-label={`${rightLabel} comparison pane`}>
                    <div className="compare-dashboard-pane-label" style={{ borderColor: accent }}>{rightLabel}</div>
                    {children[1]}
                </section>
            </div>
        </div>
    )
}
