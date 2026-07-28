/* eslint-disable react-refresh/only-export-components */
// User-driven lens mode — EclipseModeContext's shell without the poll/tier
// machinery. Entering the lens fetches GET /api/v2/story/{thread_id}/siblings
// (contract "story-siblings-v1") once; nothing polls, nothing persists across
// reloads (unlike Eclipse's localStorage seenEpisode marker — the lens is a
// per-session investigative act, not an ambient condition).
import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { lensErrorCopy, type StoryLensData, type StoryLensState } from '../lib/storyLens'

interface StoryLensValue {
  state: StoryLensState
  data: StoryLensData | null
  error: string | null
  loading: boolean
  enter: (threadId: string) => void
  exit: () => void
}

const StoryLensContext = createContext<StoryLensValue | undefined>(undefined)

export const StoryLensProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, setState] = useState<StoryLensState>({ active: false, anchorId: null })
  const [data, setData] = useState<StoryLensData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  // Mirrors EclipseModeContext's stateRef: kept in sync every render so the
  // async fetch callbacks below can read the LATEST anchorId without a stale
  // closure (enter() is a stable useCallback with an empty dep array; without
  // the ref its closure would freeze on whatever anchorId was current the
  // first time it was created).
  const stateRef = useRef(state)
  stateRef.current = state
  // Same reasoning, for the idempotent-enter check below: enter() needs to
  // know whether data has ALREADY landed for the currently-active anchor.
  const dataRef = useRef(data)
  dataRef.current = data

  useEffect(() => {
    document.body.classList.toggle('story-lensed', state.active)
    return () => document.body.classList.remove('story-lensed')
  }, [state.active])

  const enter = useCallback((threadId: string) => {
    // Idempotent, but only for a genuinely resolved payload: no-op only when
    // this anchor already has an ANCHORED payload (dataRef.current?.anchor
    // truthy) — no redundant fetch, no flash of the loading state. Anchorless
    // payloads (degraded — db_error/db_unavailable/etc — or an honest
    // no-anchor empty) always refetch on re-enter, since the router answers
    // those with HTTP 200 via _empty(), so dataRef.current itself is truthy
    // even though there is nothing to show yet and a retry may now succeed.
    if (stateRef.current.anchorId === threadId && dataRef.current?.anchor) return
    setState({ active: true, anchorId: threadId })
    setData(null)
    setError(null)
    setLoading(true)
    fetch(`/api/v2/story/${encodeURIComponent(threadId)}/siblings`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((json: StoryLensData) => {
        // Race guard: enter('A') then enter('B') in quick succession must not
        // let A's (slower) response clobber B's (faster) once it lands — the
        // banner would show sibling data for the wrong anchor. anchorId is the
        // guard token; stateRef always holds the latest one.
        if (stateRef.current.anchorId !== threadId) return
        setData(json)
        if (!json.anchor) setError(lensErrorCopy(json.notes?.[0]))
      })
      .catch(() => {
        if (stateRef.current.anchorId !== threadId) return
        setError(lensErrorCopy('db_error'))
      })
      .finally(() => {
        if (stateRef.current.anchorId !== threadId) return
        setLoading(false)
      })
  }, [])

  const exit = useCallback(() => {
    setState({ active: false, anchorId: null })
    setData(null)
    setError(null)
  }, [])

  return (
    <StoryLensContext.Provider value={{ state, data, error, loading, enter, exit }}>
      {children}
    </StoryLensContext.Provider>
  )
}

export const useStoryLens = (): StoryLensValue => {
  const ctx = useContext(StoryLensContext)
  if (!ctx) throw new Error('useStoryLens must be used within StoryLensProvider')
  return ctx
}
