import React, { useState } from 'react';
import './IndicatorTooltip.css';

interface IndicatorProps {
    score: number;
    label: string;
    tooltip: string;
    colorScale?: 'green-red' | 'blue' | 'neutral';
    showScore?: boolean;
}

/**
 * IndicatorTooltip - Displays a trust indicator score with hover tooltip
 * 
 * Used for Source Diversity, Source Quality, and other trust metrics.
 * Shows a colored score that reveals calculation explanation on hover.
 */
export const IndicatorTooltip: React.FC<IndicatorProps> = ({
    score,
    label,
    tooltip,
    colorScale = 'green-red',
    showScore = true
}) => {
    const [showTooltip, setShowTooltip] = useState(false);

    const getColor = (): string => {
        if (colorScale === 'blue') {
            return 'var(--indicator-blue)';
        }
        if (colorScale === 'neutral') {
            return 'var(--indicator-neutral)';
        }
        // green-red scale based on score
        if (score >= 70) {
            return 'var(--indicator-good)';
        }
        if (score >= 40) {
            return 'var(--indicator-warning)';
        }
        return 'var(--indicator-danger)';
    };

    const getScoreLabel = (): string => {
        if (score >= 80) return 'Excellent';
        if (score >= 60) return 'Good';
        if (score >= 40) return 'Moderate';
        if (score >= 20) return 'Limited';
        return 'Poor';
    };

    return (
        <div className="indicator-container">
            <span className="indicator-label">{label}:</span>
            {showScore && (
                <span
                    className="indicator-score"
                    style={{ color: getColor() }}
                >
                    {score}
                </span>
            )}
            <button
                className="indicator-help"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                onFocus={() => setShowTooltip(true)}
                onBlur={() => setShowTooltip(false)}
                aria-label={`Show calculation method for ${label}`}
                title="Click for more info"
            >
                ?
            </button>
            {showTooltip && (
                <div className="indicator-tooltip" role="tooltip">
                    <div className="tooltip-header">
                        <span className="tooltip-title">{label}</span>
                        <span className="tooltip-score" style={{ color: getColor() }}>
                            {score}/100 - {getScoreLabel()}
                        </span>
                    </div>
                    <div className="tooltip-content">
                        {tooltip.split('\n').map((line, i) => (
                            <p key={i}>{line}</p>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

interface VolumeIndicatorProps {
    multiplier: number | null;
    zScore: number | null;
    level: string;
    tooltip: string;
}

/**
 * VolumeIndicator - Displays normalized volume with "X times normal" format
 */
export const VolumeIndicator: React.FC<VolumeIndicatorProps> = ({
    multiplier,
    zScore,
    level,
    tooltip
}) => {
    const [showTooltip, setShowTooltip] = useState(false);

    const getLevelColor = (): string => {
        switch (level) {
            case 'exceptional':
                return 'var(--indicator-danger)';
            case 'high':
                return 'var(--indicator-warning-high)';
            case 'elevated':
                return 'var(--indicator-warning)';
            case 'low':
                return 'var(--indicator-muted)';
            default:
                return 'var(--indicator-good)';
        }
    };

    if (multiplier === null) {
        return (
            <div className="indicator-container">
                <span className="indicator-label">Volume:</span>
                <span className="indicator-score" style={{ color: 'var(--indicator-muted)' }}>
                    N/A
                </span>
            </div>
        );
    }

    return (
        <div className="indicator-container">
            <span className="indicator-label">Volume:</span>
            <span
                className="indicator-score"
                style={{ color: getLevelColor() }}
            >
                {multiplier.toFixed(1)}x normal
            </span>
            {zScore !== null && (
                <span className="indicator-zscore">
                    (z: {zScore.toFixed(1)})
                </span>
            )}
            <button
                className="indicator-help"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                aria-label="Show volume calculation method"
            >
                ?
            </button>
            {showTooltip && (
                <div className="indicator-tooltip" role="tooltip">
                    <div className="tooltip-header">
                        <span className="tooltip-title">Normalized Volume</span>
                        <span className="tooltip-score" style={{ color: getLevelColor() }}>
                            {level.charAt(0).toUpperCase() + level.slice(1)}
                        </span>
                    </div>
                    <div className="tooltip-content">
                        {tooltip.split('\n').map((line, i) => (
                            <p key={i}>{line}</p>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

export default IndicatorTooltip;
