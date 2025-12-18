/**
 * FocusSummaryPanel - Right sidebar showing focus metadata.
 * Uses useFocusData from provider (no duplicate fetching).
 */
import React from 'react'
import { useFocus } from '../contexts/FocusContext'
import { useFocusData } from '../contexts/FocusDataContext'
import './FocusSummaryPanel.css'

export const FocusSummaryPanel: React.FC = () => {
    const { focus, clearFocus, isActive } = useFocus()
    const { summary, meta, loading } = useFocusData()

    if (!isActive) {
        return null
    }

    return (
        <div className="focus-summary-panel">
            {/* Header */}
            <div className="focus-summary-header">
                <div className="focus-summary-header-row">
                    <h3>FOCUS SUMMARY</h3>
                    <button onClick={clearFocus} className="focus-clear-btn">
                        Clear Focus
                    </button>
                </div>
                <h2 className="focus-summary-title">
                    {focus.label || focus.value}
                </h2>
                {loading ? (
                    <div className="focus-summary-loading">Loading...</div>
                ) : (
                    <div className="focus-summary-stats">
                        <span>
                            <strong>{meta.totalCountries}</strong> countries
                        </span>
                        <span>
                            <strong>{meta.totalSignals.toLocaleString()}</strong> signals
                        </span>
                    </div>
                )}
            </div>

            {/* Scrollable Content */}
            {summary && (
                <div className="focus-summary-content">
                    {/* Related Topics */}
                    {summary.related_topics && summary.related_topics.length > 0 && (
                        <section className="focus-section">
                            <h4>Related Topics</h4>
                            <div className="focus-topics">
                                {summary.related_topics.slice(0, 10).map((topic, i) => (
                                    <span key={i} className="focus-topic-chip" title={`${topic.count} signals`}>
                                        {topic.topic}
                                        <span className="focus-topic-count">{topic.count}</span>
                                    </span>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Top Sources */}
                    {summary.top_sources && summary.top_sources.length > 0 && (
                        <section className="focus-section">
                            <h4>Top Sources</h4>
                            <div className="focus-sources">
                                {summary.top_sources.slice(0, 6).map((source, i) => (
                                    <div key={i} className="focus-source-row">
                                        <span className="focus-source-name">{source.source}</span>
                                        <span className="focus-source-count">{source.count} articles</span>
                                    </div>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Recent Headlines */}
                    {summary.headlines && summary.headlines.length > 0 && (
                        <section className="focus-section">
                            <h4>Recent Coverage</h4>
                            <div className="focus-headlines">
                                {summary.headlines.slice(0, 5).map((headline, i) => (
                                    <a
                                        key={i}
                                        href={headline.url}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="focus-headline-link"
                                    >
                                        <div className="focus-headline-source">{headline.source}</div>
                                    </a>
                                ))}
                            </div>
                        </section>
                    )}
                </div>
            )}
        </div>
    )
}
