/* eslint-disable react-refresh/only-export-components */
import React, { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react'
import { type EclipseData, type EclipseModeState, type EclipseAction,
         eclipseTier, episodeKey, nextEclipseMode, applyEclipseAction } from '../lib/attentionEclipse'

const STORAGE_KEY = 'atlas.eclipse.v1'
const POLL_MS = 4 * 60 * 1000

interface EclipseModeValue {
  data: EclipseData | null
  tier: 'none' | 'partial' | 'total'
  mode: EclipseModeState['mode']
  act: (a: EclipseAction) => void
}

const Ctx = createContext<EclipseModeValue | undefined>(undefined)

function loadState(): EclipseModeState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) { const p = JSON.parse(raw); if (p && p.seenEpisode !== undefined) return { mode: 'normal', seenEpisode: p.seenEpisode } }
  } catch { /* ignore */ }
  return { mode: 'normal', seenEpisode: null }
}

export const EclipseProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [data, setData] = useState<EclipseData | null>(null)
  const [state, setState] = useState<EclipseModeState>(loadState)
  const stateRef = useRef(state)
  stateRef.current = state

  // Persist only the seenEpisode marker (mode is session-derived).
  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify({ seenEpisode: state.seenEpisode })) } catch { /* ignore */ }
    document.body.classList.toggle('eclipsed', state.mode === 'ambient')
  }, [state])

  const poll = useCallback(async () => {
    try {
      const r = await fetch('/api/v2/attention/eclipse?hours=24')
      if (!r.ok) return
      const payload = (await r.json()) as EclipseData
      setData(payload)
      const tier = eclipseTier(payload)
      setState(prev => nextEclipseMode(prev, tier, episodeKey(payload)))
    } catch { /* diffuse day / offline — leave state */ }
  }, [])

  useEffect(() => {
    poll()
    const id = setInterval(poll, POLL_MS)
    return () => clearInterval(id)
  }, [poll])

  useEffect(() => {
    const h = () => poll()
    window.addEventListener('atlas:eclipse-refresh', h)
    return () => window.removeEventListener('atlas:eclipse-refresh', h)
  }, [poll])

  const act = useCallback((a: EclipseAction) => setState(prev => applyEclipseAction(prev, a)), [])

  return (
    <Ctx.Provider value={{ data, tier: eclipseTier(data), mode: state.mode, act }}>
      {children}
    </Ctx.Provider>
  )
}

export const useEclipseMode = (): EclipseModeValue => {
  const v = useContext(Ctx)
  if (!v) throw new Error('useEclipseMode must be used within EclipseProvider')
  return v
}
