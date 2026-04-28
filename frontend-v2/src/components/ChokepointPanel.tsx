import { useState, useEffect } from 'react'
import { type Chokepoint } from '../lib/chokepoints'
import { getThemeLabel } from '../lib/themeLabels'

interface CountrySignals {
  code: string
  signal_count: number
  avg_sentiment: number
  top_themes: string[]
}

interface RecentSignal {
  timestamp: string
  country: string
  source: string
  url: string
  sentiment: number
  themes: string[]
}

interface ChokepointPanelProps {
  chokepoint: Chokepoint
  vesselCount: number
  hours: number
  onCountryClick: (code: string) => void
}

const isoToFlag = (code: string) =>
  code?.length === 2
    ? String.fromCodePoint(...code.toUpperCase().split('').map(c => 0x1F1E6 + c.charCodeAt(0) - 65))
    : '🌐'

const sentimentColor = (s: number) => s > 0.5 ? '#4ade80' : s < -0.5 ? '#f87171' : '#fbbf24'

export function ChokepointPanel({ chokepoint, vesselCount, hours, onCountryClick }: ChokepointPanelProps) {
  const [countryData, setCountryData] = useState<CountrySignals[]>([])
  const [signals, setSignals] = useState<RecentSignal[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const countries = chokepoint.countries.join(',')

    Promise.all([
      // Country signal volumes
      fetch(`/api/v2/nodes?hours=${hours}&countries=${countries}`)
        .then(r => r.ok ? r.json() : { hotspots: [] }),
      // Recent signals from chokepoint countries
      fetch(`/api/v2/signals?hours=${Math.min(hours, 24)}&countries=${countries}&limit=15`)
        .then(r => r.ok ? r.json() : { signals: [] }),
    ]).then(([nodesData, signalsData]) => {
      const hotspots: CountrySignals[] = (nodesData.hotspots || [])
        .filter((h: any) => chokepoint.countries.includes(h.country_code))
        .map((h: any) => ({
          code: h.country_code,
          signal_count: h.signal_count || 0,
          avg_sentiment: h.avg_sentiment || 0,
          top_themes: h.top_themes || [],
        }))
        .sort((a: CountrySignals, b: CountrySignals) => b.signal_count - a.signal_count)

      // Fill in countries with 0 signals
      const coveredCodes = new Set(hotspots.map((h: CountrySignals) => h.code))
      for (const code of chokepoint.countries) {
        if (!coveredCodes.has(code)) hotspots.push({ code, signal_count: 0, avg_sentiment: 0, top_themes: [] })
      }

      setCountryData(hotspots)
      setSignals((signalsData.signals || []).slice(0, 12))
    }).catch(() => {
      setCountryData(chokepoint.countries.map(code => ({ code, signal_count: 0, avg_sentiment: 0, top_themes: [] })))
    }).finally(() => setLoading(false))
  }, [chokepoint.id, hours])

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '16px 20px', scrollbarWidth: 'thin' }}>
      {/* Header */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 15, fontWeight: 700, color: '#e2e8f0', marginBottom: 4 }}>{chokepoint.name}</div>
        <div style={{ fontSize: 12, color: '#64748b', lineHeight: 1.6 }}>{chokepoint.description}</div>
        {vesselCount > 0 && (
          <div style={{ fontSize: 12, color: '#2dd4bf', marginTop: 8, fontFamily: 'var(--font-mono)' }}>
            ⚓ {vesselCount} vessels currently in range
          </div>
        )}
      </div>

      {/* Countries by signal volume */}
      <div style={{ marginBottom: 20 }}>
        <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
          Countries by media volume
        </div>
        {loading ? (
          <div style={{ fontSize: 12, color: '#475569', fontFamily: 'var(--font-mono)' }}>loading...</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {countryData.map((c, i) => {
              const maxCount = countryData[0]?.signal_count || 1
              const pct = maxCount > 0 ? Math.round((c.signal_count / maxCount) * 100) : 0
              return (
                <button key={c.code}
                  onClick={() => onCountryClick(c.code)}
                  style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 8, padding: '10px 12px', cursor: 'pointer', textAlign: 'left', width: '100%', transition: 'background 0.15s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'rgba(29,158,117,0.1)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.03)')}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                    <span style={{ fontSize: 13, color: '#e2e8f0', fontWeight: 500 }}>
                      {isoToFlag(c.code)} {c.code}
                    </span>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span style={{ fontSize: 11, color: sentimentColor(c.avg_sentiment), fontFamily: 'var(--font-mono)' }}>
                        {c.avg_sentiment > 0 ? '+' : ''}{c.avg_sentiment.toFixed(1)}
                      </span>
                      <span style={{ fontSize: 11, color: '#94a3b8', fontFamily: 'var(--font-mono)' }}>
                        {c.signal_count.toLocaleString()} sig
                      </span>
                    </div>
                  </div>
                  {c.signal_count > 0 && (
                    <>
                      <div style={{ height: 3, background: 'rgba(255,255,255,0.06)', borderRadius: 2, marginBottom: 6, overflow: 'hidden' }}>
                        <div style={{ height: '100%', width: `${pct}%`, background: i === 0 ? '#2dd4bf' : 'rgba(45,212,191,0.5)', borderRadius: 2 }} />
                      </div>
                      {c.top_themes.length > 0 && (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {c.top_themes.slice(0, 3).map(t => (
                            <span key={t} style={{ fontSize: 10, color: '#64748b', background: 'rgba(255,255,255,0.05)', borderRadius: 4, padding: '1px 6px' }}>
                              {getThemeLabel(t)}
                            </span>
                          ))}
                        </div>
                      )}
                    </>
                  )}
                </button>
              )
            })}
          </div>
        )}
      </div>

      {/* Recent signals from the area */}
      {!loading && signals.length > 0 && (
        <div>
          <div style={{ fontSize: 11, color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 10 }}>
            Recent coverage from area
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {signals.map((sig, i) => (
              <a key={i} href={sig.url} target="_blank" rel="noopener noreferrer"
                style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 6, padding: '8px 10px', textDecoration: 'none', display: 'block' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 11, color: '#94a3b8' }}>{isoToFlag(sig.country)} {sig.source}</span>
                  <span style={{ fontSize: 10, color: sentimentColor(sig.sentiment), fontFamily: 'var(--font-mono)' }}>
                    {sig.sentiment > 0 ? '+' : ''}{sig.sentiment.toFixed(1)}
                  </span>
                </div>
                {sig.themes.slice(0, 2).map(t => (
                  <span key={t} style={{ fontSize: 10, color: '#475569', background: 'rgba(255,255,255,0.04)', borderRadius: 4, padding: '1px 6px', marginRight: 4 }}>
                    {getThemeLabel(t)}
                  </span>
                ))}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
