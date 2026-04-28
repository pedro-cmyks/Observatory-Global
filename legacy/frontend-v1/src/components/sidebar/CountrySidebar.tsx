import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useMapStore } from '../../store/mapStore'

const CountrySidebar: React.FC = () => {
  const { selectedHotspot, setSelectedHotspot } = useMapStore()

  const getIntensityColor = (intensity: number): string => {
    if (intensity < 0.3) return '#3B82F6'
    if (intensity < 0.6) return '#FCD34D'
    return '#EF4444'
  }

  const getIntensityLabel = (intensity: number): string => {
    if (intensity < 0.3) return 'Low'
    if (intensity < 0.6) return 'Medium'
    return 'High'
  }

  const getSentimentConfig = (sentimentLabel: string, sentimentScore: number) => {
    const configs = {
      very_negative: {
        color: '#ef4444',
        bgColor: '#fee2e2',
        emoji: '😰',
        label: 'Very Negative',
      },
      negative: {
        color: '#f97316',
        bgColor: '#ffedd5',
        emoji: '😟',
        label: 'Negative',
      },
      neutral: {
        color: '#6b7280',
        bgColor: '#f3f4f6',
        emoji: '😐',
        label: 'Neutral',
      },
      positive: {
        color: '#10b981',
        bgColor: '#d1fae5',
        emoji: '🙂',
        label: 'Positive',
      },
      very_positive: {
        color: '#3b82f6',
        bgColor: '#dbeafe',
        emoji: '😊',
        label: 'Very Positive',
      },
    }

    const config = configs[sentimentLabel as keyof typeof configs] || configs.neutral
    const scoreStr = sentimentScore > 0 ? `+${sentimentScore.toFixed(1)}` : sentimentScore.toFixed(1)

    return { ...config, scoreStr }
  }

  return (
    <AnimatePresence>
      {selectedHotspot && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setSelectedHotspot(null)}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
              zIndex: 15,
            }}
          />

          {/* Sidebar */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 300 }}
            style={{
              position: 'absolute',
              top: 0,
              right: 0,
              bottom: 0,
              width: '350px',
              maxWidth: '90vw',
              backgroundColor: 'white',
              boxShadow: '-2px 0 8px rgba(0,0,0,0.2)',
              zIndex: 20,
              overflowY: 'auto',
            }}
          >
            {/* Header */}
            <div
              style={{
                padding: '1.5rem',
                borderBottom: '1px solid #e0e0e0',
                position: 'sticky',
                top: 0,
                backgroundColor: 'white',
                zIndex: 1,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                <div>
                  <h2 style={{ margin: '0 0 0.5rem 0', fontSize: '1.5rem', color: '#213547' }}>
                    {selectedHotspot.country_name}
                  </h2>
                  <div style={{ fontSize: '0.9rem', color: '#666' }}>
                    Code: {selectedHotspot.country_code}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedHotspot(null)}
                  style={{
                    padding: '0.5rem',
                    fontSize: '1.2rem',
                    backgroundColor: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    color: '#666',
                  }}
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Content */}
            <div style={{ padding: '1.5rem' }}>
              {/* Intensity Gauge */}
              <div style={{ marginBottom: '2rem' }}>
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.5rem',
                  }}
                >
                  <span style={{ fontSize: '0.9rem', fontWeight: 600, color: '#333' }}>
                    Intensity
                  </span>
                  <span
                    style={{
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      color: getIntensityColor(selectedHotspot.intensity),
                    }}
                  >
                    {getIntensityLabel(selectedHotspot.intensity)} (
                    {(selectedHotspot.intensity * 100).toFixed(0)}%)
                  </span>
                </div>
                <div
                  style={{
                    width: '100%',
                    height: '12px',
                    backgroundColor: '#f0f0f0',
                    borderRadius: '6px',
                    overflow: 'hidden',
                  }}
                >
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${selectedHotspot.intensity * 100}%` }}
                    transition={{ duration: 0.5 }}
                    style={{
                      height: '100%',
                      backgroundColor: getIntensityColor(selectedHotspot.intensity),
                    }}
                  />
                </div>
              </div>

              {/* Stats */}
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: '1fr 1fr',
                  gap: '1rem',
                  marginBottom: '2rem',
                }}
              >
                <div
                  style={{
                    padding: '1rem',
                    backgroundColor: '#f9f9f9',
                    borderRadius: '8px',
                  }}
                >
                  <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }}>
                    Topics
                  </div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#213547' }}>
                    {selectedHotspot.topic_count}
                  </div>
                </div>
                <div
                  style={{
                    padding: '1rem',
                    backgroundColor: '#f9f9f9',
                    borderRadius: '8px',
                  }}
                >
                  <div style={{ fontSize: '0.8rem', color: '#666', marginBottom: '0.25rem' }}>
                    Confidence
                  </div>
                  <div style={{ fontSize: '1.5rem', fontWeight: 600, color: '#213547' }}>
                    {(selectedHotspot.confidence * 100).toFixed(0)}%
                  </div>
                </div>
              </div>

              {/* Source Diversity - Phase 3.5 */}
              {selectedHotspot.source_count !== undefined && selectedHotspot.source_count > 0 && (
                <div
                  style={{
                    marginBottom: '2rem',
                    padding: '1rem',
                    backgroundColor: '#fefce8',
                    borderRadius: '0.5rem',
                    border: '1px solid #fde047',
                  }}
                >
                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      marginBottom: '0.5rem',
                    }}
                  >
                    <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#713f12' }}>
                      📰 Source Diversity
                    </span>
                    <span
                      style={{
                        fontSize: '1.25rem',
                        fontWeight: 700,
                        color: '#854d0e',
                      }}
                    >
                      {selectedHotspot.source_count} {selectedHotspot.source_count === 1 ? 'outlet' : 'outlets'}
                    </span>
                  </div>
                  <div
                    style={{
                      width: '100%',
                      height: '8px',
                      backgroundColor: '#fef3c7',
                      borderRadius: '4px',
                      overflow: 'hidden',
                    }}
                  >
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(selectedHotspot.source_diversity || 0) * 100}%` }}
                      transition={{ duration: 0.5 }}
                      style={{
                        height: '100%',
                        backgroundColor: '#ca8a04',
                      }}
                    />
                  </div>
                  <p
                    style={{
                      marginTop: '0.5rem',
                      margin: '0.5rem 0 0 0',
                      fontSize: '0.75rem',
                      color: '#92400e',
                      fontStyle: 'italic',
                    }}
                  >
                    {selectedHotspot.source_diversity && selectedHotspot.source_diversity > 0.7
                      ? 'Highly diverse coverage from multiple independent sources'
                      : selectedHotspot.source_diversity && selectedHotspot.source_diversity > 0.3
                      ? 'Moderate source diversity'
                      : 'Coverage concentrated in few outlets'}
                  </p>
                </div>
              )}


              {/* Sentiment Badge */}
              {selectedHotspot.dominant_sentiment && (
                <div style={{ marginBottom: '2rem' }}>
                  {(() => {
                    const { color, bgColor, emoji, label, scoreStr } = getSentimentConfig(
                      selectedHotspot.dominant_sentiment,
                      selectedHotspot.avg_sentiment_score || 0
                    )
                    return (
                      <div
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.5rem',
                          padding: '0.5rem 0.75rem',
                          backgroundColor: bgColor,
                          borderRadius: '0.5rem',
                          border: `1px solid ${color}`,
                        }}
                      >
                        <span style={{ fontSize: '1.25rem' }}>{emoji}</span>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.1rem' }}>
                          <span style={{ fontSize: '0.75rem', color: '#6b7280', fontWeight: 500 }}>
                            Sentiment
                          </span>
                          <span style={{ fontSize: '0.875rem', color, fontWeight: 600 }}>
                            {label} ({scoreStr})
                          </span>
                        </div>
                      </div>
                    )
                  })()}
                </div>
              )}

              {/* Key Actors - Phase 3.5 */}
              {selectedHotspot.signals && selectedHotspot.signals.length > 0 && (() => {
                // Aggregate actors across all signals
                const allPersons = new Set<string>()
                const allOrgs = new Set<string>()
                const allOutlets = new Set<string>()

                selectedHotspot.signals.forEach((signal) => {
                  signal.persons?.forEach((p) => allPersons.add(p))
                  signal.organizations?.forEach((o) => allOrgs.add(o))
                  if (signal.source_outlet) allOutlets.add(signal.source_outlet)
                })

                const hasActorData = allPersons.size > 0 || allOrgs.size > 0 || allOutlets.size > 0

                if (!hasActorData) return null

                return (
                  <div
                    style={{
                      marginBottom: '2rem',
                      padding: '1rem',
                      backgroundColor: '#f0f9ff',
                      borderRadius: '0.5rem',
                      border: '1px solid #bae6fd',
                    }}
                  >
                    <h4
                      style={{
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: '#111827',
                        marginBottom: '0.75rem',
                        margin: '0 0 0.75rem 0',
                      }}
                    >
                      👥 Who&apos;s Involved?
                    </h4>

                    {/* Key People */}
                    {allPersons.size > 0 && (
                      <div style={{ marginBottom: allOrgs.size > 0 || allOutlets.size > 0 ? '0.75rem' : '0' }}>
                        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.375rem', fontWeight: 600 }}>
                          KEY PEOPLE
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                          {Array.from(allPersons).slice(0, 5).map((person) => (
                            <span
                              key={person}
                              style={{
                                fontSize: '0.8125rem',
                                color: '#1e40af',
                                backgroundColor: 'white',
                                padding: '0.25rem 0.5rem',
                                borderRadius: '0.25rem',
                                border: '1px solid #bae6fd',
                                fontWeight: 500,
                              }}
                            >
                              {person}
                            </span>
                          ))}
                          {allPersons.size > 5 && (
                            <span style={{ fontSize: '0.8125rem', color: '#6b7280', alignSelf: 'center' }}>
                              +{allPersons.size - 5} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* Key Organizations */}
                    {allOrgs.size > 0 && (
                      <div style={{ marginBottom: allOutlets.size > 0 ? '0.75rem' : '0' }}>
                        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.375rem', fontWeight: 600 }}>
                          KEY ORGANIZATIONS
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                          {Array.from(allOrgs).slice(0, 5).map((org) => (
                            <span
                              key={org}
                              style={{
                                fontSize: '0.8125rem',
                                color: '#7c3aed',
                                backgroundColor: 'white',
                                padding: '0.25rem 0.5rem',
                                borderRadius: '0.25rem',
                                border: '1px solid #ddd6fe',
                                fontWeight: 500,
                              }}
                            >
                              {org}
                            </span>
                          ))}
                          {allOrgs.size > 5 && (
                            <span style={{ fontSize: '0.8125rem', color: '#6b7280', alignSelf: 'center' }}>
                              +{allOrgs.size - 5} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}

                    {/* News Outlets */}
                    {allOutlets.size > 0 && (
                      <div>
                        <div style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.375rem', fontWeight: 600 }}>
                          NEWS OUTLETS
                        </div>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.375rem' }}>
                          {Array.from(allOutlets).slice(0, 5).map((outlet) => (
                            <span
                              key={outlet}
                              style={{
                                fontSize: '0.8125rem',
                                color: '#059669',
                                backgroundColor: 'white',
                                padding: '0.25rem 0.5rem',
                                borderRadius: '0.25rem',
                                border: '1px solid #d1fae5',
                                fontWeight: 500,
                              }}
                            >
                              {outlet}
                            </span>
                          ))}
                          {allOutlets.size > 5 && (
                            <span style={{ fontSize: '0.8125rem', color: '#6b7280', alignSelf: 'center' }}>
                              +{allOutlets.size - 5} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )
              })()}

              {/* Why is this heating up? */}
              {selectedHotspot.theme_distribution &&
                Object.keys(selectedHotspot.theme_distribution).length > 0 && (
                  <div
                    style={{
                      marginBottom: '2rem',
                      padding: '1rem',
                      backgroundColor: '#f9fafb',
                      borderRadius: '0.5rem',
                    }}
                  >
                    <h4
                      style={{
                        fontSize: '0.875rem',
                        fontWeight: 600,
                        color: '#111827',
                        marginBottom: '0.75rem',
                        margin: '0 0 0.75rem 0',
                      }}
                    >
                      🔥 Why is this heating up?
                    </h4>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {/* Top 3 themes */}
                      {Object.entries(selectedHotspot.theme_distribution)
                        .sort(([, countA], [, countB]) => countB - countA)
                        .slice(0, 3)
                        .map(([theme, count]) => (
                          <div
                            key={theme}
                            style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              padding: '0.5rem',
                              backgroundColor: 'white',
                              borderRadius: '0.375rem',
                              border: '1px solid #e5e7eb',
                            }}
                          >
                            <span
                              style={{
                                fontSize: '0.875rem',
                                color: '#374151',
                                fontWeight: 500,
                              }}
                            >
                              {theme}
                            </span>
                            <span
                              style={{
                                fontSize: '0.75rem',
                                color: '#6b7280',
                                backgroundColor: '#f3f4f6',
                                padding: '0.125rem 0.5rem',
                                borderRadius: '0.25rem',
                                fontWeight: 600,
                              }}
                            >
                              {count} mentions
                            </span>
                          </div>
                        ))}
                    </div>

                    {/* Sentiment context */}
                    {selectedHotspot.avg_sentiment_score !== undefined &&
                      selectedHotspot.avg_sentiment_score !== 0 && (
                        <p
                          style={{
                            marginTop: '0.75rem',
                            margin: '0.75rem 0 0 0',
                            fontSize: '0.8125rem',
                            color: '#6b7280',
                            fontStyle: 'italic',
                            lineHeight: '1.4',
                          }}
                        >
                          Coverage is predominantly{' '}
                          <strong
                            style={{
                              color:
                                selectedHotspot.avg_sentiment_score < 0 ? '#ef4444' : '#10b981',
                            }}
                          >
                            {selectedHotspot.avg_sentiment_score < 0 ? 'negative' : 'positive'}
                          </strong>{' '}
                          (
                          {selectedHotspot.avg_sentiment_score > 0 ? '+' : ''}
                          {selectedHotspot.avg_sentiment_score.toFixed(1)} sentiment score)
                        </p>
                      )}
                  </div>
                )}

              {/* Top Topics */}
              <div>
                <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#213547' }}>
                  Top Topics
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {selectedHotspot.top_topics.map((topic, index) => (
                    <div
                      key={index}
                      style={{
                        padding: '0.75rem',
                        backgroundColor: '#f9f9f9',
                        borderRadius: '6px',
                        borderLeft: `3px solid ${getIntensityColor(selectedHotspot.intensity)}`,
                      }}
                    >
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                      >
                        <span style={{ fontSize: '0.9rem', fontWeight: 500, color: '#333' }}>
                          {topic.label}
                        </span>
                        <span
                          style={{
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            color: '#646cff',
                            backgroundColor: '#eef',
                            padding: '0.2rem 0.5rem',
                            borderRadius: '12px',
                          }}
                        >
                          {topic.count}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}

export default CountrySidebar
