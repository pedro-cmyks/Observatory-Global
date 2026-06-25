import { useEffect, useRef, useState } from 'react'
import { buildHeroThreads, type HeroMover, type RawThread } from '../lib/heroThreads'
import './HeroThread.css'

const FALLBACK: RawThread[] = [
  { thread_id: 'fallback', label: 'Tracking global narratives', trend: 'stable', velocity: 0, top_countries: ['US', 'GB', 'IR'] },
]

const NODE_COLOR: Record<string, string> = {
  story: '#68dbae',
  country: '#60a5fa',
  source: '#f59e0b',
  actor: '#a78bfa',
  attention: '#2dd4bf',
}

export function HeroThread() {
  const [movers, setMovers] = useState<HeroMover[]>(() => buildHeroThreads(FALLBACK, { max: 1 }))
  const [active, setActive] = useState(0)
  const reduced = useRef(false)

  useEffect(() => {
    reduced.current = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    fetch('/api/v2/threads?hours=24&limit=6')
      .then(r => (r.ok ? r.json() : null))
      .then(d => {
        const list: unknown[] = d?.threads ?? d ?? []
        const raw: RawThread[] = (Array.isArray(list) ? list : []).map((item) => {
          const t = item as Record<string, unknown>
          return {
            thread_id: (t.thread_id ?? t.id) as string,
            label: (t.label ?? t.title) as string,
            trend: t.trend as string | undefined,
            velocity: t.velocity as number | undefined,
            top_countries: t.top_countries as string[] | undefined,
          }
        }).filter((t: RawThread) => Boolean(t.thread_id && t.label))
        const built = buildHeroThreads(raw, { max: 5 })
        if (built.length) setMovers(built)
      })
      .catch(() => { /* keep fallback */ })
  }, [])

  useEffect(() => {
    if (reduced.current || movers.length <= 1) return
    const id = setInterval(() => setActive(a => (a + 1) % movers.length), 5200)
    return () => clearInterval(id)
  }, [movers])

  const m = movers[active] ?? movers[0]
  const routeD = 'M' + m.route.map(p => `${p.x},${p.y}`).join(' L')

  return (
    <div className="hero-thread" aria-hidden="true">
      <svg viewBox="0 0 640 240" preserveAspectRatio="xMidYMid meet">
        <defs>
          <filter id="ht-glow" x="-70%" y="-70%" width="240%" height="240%">
            <feGaussianBlur stdDeviation="3" />
          </filter>
        </defs>

        {/* faint world graticule */}
        <g className="ht-grid" fill="none">
          <ellipse cx="320" cy="120" rx="300" ry="110" />
          <line x1="20" y1="120" x2="620" y2="120" />
          <line x1="20" y1="80" x2="620" y2="80" />
          <line x1="20" y1="160" x2="620" y2="160" />
          <line x1="170" y1="14" x2="170" y2="226" />
          <line x1="320" y1="10" x2="320" y2="230" />
          <line x1="470" y1="14" x2="470" y2="226" />
        </g>

        {/* constellation edges */}
        <g className="ht-edges">
          {m.satellites.map((s, i) => (
            <line key={i} x1={m.center.x} y1={m.center.y} x2={s.x} y2={s.y} />
          ))}
        </g>

        {/* route */}
        <path className="ht-route" d={routeD} />

        {/* comet (skip under reduced motion) */}
        {!reduced.current && (
          <circle r="4" fill="#86f8c9" filter="url(#ht-glow)">
            <animateMotion key={m.id} dur="3.4s" repeatCount="indefinite" path={routeD} />
            <animate attributeName="opacity" values="0;1;1;1;0" dur="3.4s" repeatCount="indefinite" />
          </circle>
        )}

        {/* satellites */}
        {m.satellites.map((s, i) => (
          <g key={i}>
            <circle cx={s.x} cy={s.y} r="8" fill={NODE_COLOR[s.type]} filter="url(#ht-glow)" opacity="0.45" />
            <circle cx={s.x} cy={s.y} r="4.5" fill={NODE_COLOR[s.type]} />
          </g>
        ))}

        {/* center story (pulse) */}
        <circle className={reduced.current ? '' : 'ht-pulse'} cx={m.center.x} cy={m.center.y} r="20" fill="#68dbae" filter="url(#ht-glow)" opacity="0.4" />
        <circle cx={m.center.x} cy={m.center.y} r="12" fill="#0a1220" stroke="#68dbae" strokeWidth="1.5" />
        <text x={m.center.x} y={m.center.y - 18} fill="#68dbae" fontSize="11" textAnchor="middle" style={{ fontFamily: 'Fraunces, Georgia, serif' }}>
          {m.title}{m.trend === 'accelerating' ? ' ▲' : ''}
        </text>
      </svg>
    </div>
  )
}
