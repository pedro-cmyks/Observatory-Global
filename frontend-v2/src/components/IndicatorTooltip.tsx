import React, { useState } from 'react';
import './IndicatorTooltip.css';
import { volumeZBasis } from '../lib/volumeBasis';

interface IndicatorProps {
    score: number;
    label: string;
    tooltip: string;
    colorScale?: 'green-red' | 'blue' | 'neutral';
    showScore?: boolean;
    /**
     * Fix round 2026-08-12 pair (e): the composite's INPUTS, rendered inline so
     * the score is auditable at a glance ("48 outlets · top tribunnews.com 11%")
     * instead of an unexplained 99 sitting next to an unexplained 30.
     */
    inlineNote?: string | null;
    inlineTip?: string;
    /**
     * Overrides the score band word. Used when the band would be an unearned
     * verdict — a quality score held down purely by outlets missing from our
     * allowlist is "unclassified", never "Poor".
     */
    verdictLabel?: string | null;
    /** Paints that unearned-verdict case neutral instead of danger red. */
    neutralVerdict?: boolean;
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
    showScore = true,
    inlineNote,
    inlineTip,
    verdictLabel,
    neutralVerdict
}) => {
    const [showTooltip, setShowTooltip] = useState(false);

    const getColor = (): string => {
        // An unearned verdict never gets a judgement colour: danger red on a
        // score that only means "we have not catalogued this country's press"
        // reads as an accusation we cannot support.
        if (neutralVerdict) {
            return 'var(--indicator-neutral)';
        }
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
        if (verdictLabel) return verdictLabel;
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
            {inlineNote && (
                <span className="indicator-inputs" data-tip={inlineTip}>
                    {inlineNote}
                </span>
            )}
            <button
                className="indicator-help"
                onMouseEnter={() => setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                onFocus={() => setShowTooltip(true)}
                onBlur={() => setShowTooltip(false)}
                aria-label={`Show calculation method for ${label}`}
                data-tip="Click for more info"
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
                        {inlineTip && <p className="tooltip-basis">{inlineTip}</p>}
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
    /** Printed window the CURRENT half of the z-score covers, e.g. '24h'. */
    windowLabel?: string | null;
    baselineDays?: number | null;
    daysObserved?: number | null;
    /** Baseline too sparse for a meaningful sigma — show direction, not a number. */
    thinBaseline?: boolean | null;
}

/**
 * VolumeIndicator - Displays normalized volume with "X times normal" format
 */
export const VolumeIndicator: React.FC<VolumeIndicatorProps> = ({
    multiplier,
    zScore,
    level,
    tooltip,
    windowLabel,
    baselineDays,
    daysObserved,
    thinBaseline
}) => {
    const [showTooltip, setShowTooltip] = useState(false);
    // Fix round 2026-08-12 pair (c): the z-score is a DIFFERENT statistic on a
    // DIFFERENT window from the × badge above it, and on a thin baseline its
    // sigma is meaningless — printing "z: 71.2" there is fabricated precision.
    // The pure decision lives in lib/volumeBasis (tested); this only renders it.
    const zBasis = volumeZBasis({ zScore, windowLabel, baselineDays, daysObserved, thinBaseline });

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
                data-tip={`Signal volume for this window as a share of this country's normal day. ${zBasis.tip}`}
            >
                {multiplier.toFixed(1)}x normal
            </span>
            {zBasis.text && (
                <span
                    className={`indicator-zscore${zBasis.precise ? '' : ' indicator-zscore--degraded'}`}
                    data-tip={zBasis.tip}
                >
                    ({zBasis.text})
                </span>
            )}
            {/* X4 (2026-08-13, blind college C5): "z" is the densest token on
                this panel. The number stays for the analyst; the direction and
                its coarse size ride beside it for everyone else. Null on a thin
                baseline by construction — the chip already withholds precision
                there, and words must not smuggle a magnitude back in. */}
            {zBasis.plain && (
                <span className="indicator-zplain">{zBasis.plain}</span>
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
