import './PanelSkeleton.css'

interface PanelSkeletonProps {
    rows?: number
    className?: string
}

export function PanelSkeleton({ rows = 4, className = '' }: PanelSkeletonProps) {
    const widths = [82, 65, 90, 55, 73, 40, 68]
    return (
        <div className={`panel-skeleton ${className}`} aria-hidden="true">
            {Array.from({ length: rows }).map((_, i) => (
                <div
                    key={i}
                    className="panel-skeleton-row"
                    style={{ width: `${widths[i % widths.length]}%` }}
                />
            ))}
        </div>
    )
}

export function PanelSkeletonGrid({ cols = 2, rows = 2 }: { cols?: number; rows?: number }) {
    return (
        <div className="panel-skeleton-grid" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }} aria-hidden="true">
            {Array.from({ length: cols * rows }).map((_, i) => (
                <div key={i} className="panel-skeleton-card" />
            ))}
        </div>
    )
}
