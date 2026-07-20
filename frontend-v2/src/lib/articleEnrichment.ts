/** Workbench article enrichment F1 (spec 2026-07-20-workbench-article-enrichment).
 *
 *  Pinning fires a fire-and-forget fetch of the pin's frozen evidence URLs;
 *  the backend caches extracted text server-side (`pinned_articles`). Article
 *  text NEVER lands in localStorage or the accounts sync payload — this module
 *  only moves URL lists out and display states (status + ~60-word excerpt) in.
 *  Partial yield is a normal state: paywall/robots/error are product statuses,
 *  not failures to hide. Every network call here degrades silently — a pin or
 *  a dossier never waits on, or breaks over, enrichment. */
import { useEffect, useRef, useState } from 'react'
import type { PinSnapshot } from './workbench'

export interface ArticleState {
  url: string
  status: 'pending' | 'ok' | 'paywall' | 'robots' | 'error' | 'unsupported' | 'queued' | 'rejected'
  via?: 'live' | 'wayback'
  title?: string | null
  outlet?: string | null
  excerpt?: string | null
  word_count?: number | null
  fetched_at?: string | null
  fetch_error?: string | null
}

/** Evidence URLs worth fetching, deduped, capped to the API limit. */
export function extractSnapshotUrls(snapshot?: Pick<PinSnapshot, 'evidence'> | null): string[] {
  const urls = (snapshot?.evidence ?? [])
    .map(e => (e.url ?? '').trim())
    .filter(u => u.startsWith('http'))
  return Array.from(new Set(urls)).slice(0, 64)
}

/** True while a re-poll can still change something (unknown or in-flight). */
export function statesSettled(urls: string[], states: Map<string, ArticleState>): boolean {
  return urls.every(u => {
    const s = states.get(u)
    return !!s && s.status !== 'pending' && s.status !== 'queued'
  })
}

function post(path: string, urls: string[]): Promise<Response> {
  return fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ urls }),
  })
}

/** Fire-and-forget: register + start background fetches for a snapshot's
 *  evidence URLs. Safe to call anywhere (store included): never throws, never
 *  blocks, no-ops without URLs or outside a browser. */
export function enqueueSnapshotFetch(snapshot?: Pick<PinSnapshot, 'evidence'> | null): void {
  const urls = extractSnapshotUrls(snapshot)
  if (urls.length === 0 || typeof fetch !== 'function') return
  try {
    void post('/api/v2/research/articles/fetch', urls).catch(() => {})
  } catch { /* enrichment is best-effort by contract */ }
}

export function enqueueUrls(urls: string[]): void {
  const clean = Array.from(new Set(urls.filter(u => (u ?? '').startsWith('http')))).slice(0, 64)
  if (clean.length === 0 || typeof fetch !== 'function') return
  try {
    void post('/api/v2/research/articles/fetch', clean).catch(() => {})
  } catch { /* best-effort */ }
}

export async function fetchArticleStates(urls: string[]): Promise<Map<string, ArticleState>> {
  const map = new Map<string, ArticleState>()
  const clean = Array.from(new Set(urls.filter(u => (u ?? '').startsWith('http')))).slice(0, 64)
  if (clean.length === 0) return map
  try {
    const resp = await post('/api/v2/research/articles/state', clean)
    if (!resp.ok) return map
    const data = await resp.json()
    for (const item of (data?.items ?? []) as ArticleState[]) {
      if (item?.url) map.set(item.url, item)
    }
  } catch { /* silent degrade — callers render absence */ }
  return map
}

const POLL_MS = 4000
const MAX_POLLS = 8   // bounded wait ≈ 32s, then whatever landed stands

/** Display states for a URL set; polls while fetches are in flight (bounded).
 *  Pass stable url arrays (memoized by caller) to avoid refetch churn. */
export function useArticleStates(urls: string[]): Map<string, ArticleState> {
  const [states, setStates] = useState<Map<string, ArticleState>>(new Map())
  const key = urls.join('\n')
  const pollsRef = useRef(0)
  useEffect(() => {
    if (urls.length === 0) { setStates(new Map()); return }
    let alive = true
    pollsRef.current = 0
    const tick = async () => {
      const next = await fetchArticleStates(urls)
      if (!alive) return
      setStates(next)
      pollsRef.current += 1
      if (!statesSettled(urls, next) && pollsRef.current < MAX_POLLS) {
        timer = window.setTimeout(tick, POLL_MS)
      }
    }
    let timer = window.setTimeout(tick, 0)
    return () => { alive = false; window.clearTimeout(timer) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return states
}

/** Honest yield line: how many receipts have full text vs attempted. */
export function fullTextYield(urls: string[], states: Map<string, ArticleState>): { ok: number; total: number } {
  let ok = 0
  for (const u of urls) if (states.get(u)?.status === 'ok') ok++
  return { ok, total: urls.length }
}

/** Short honest tag for a non-ok state (UI + export). */
export function stateTag(s?: ArticleState): string | null {
  if (!s) return null
  switch (s.status) {
    case 'ok': return null
    case 'pending':
    case 'queued': return 'fetching full text…'
    case 'paywall': return 'full text unavailable · paywall or wall'
    case 'robots': return 'full text unavailable · site refused'
    case 'unsupported': return 'full text unavailable · non-article content'
    case 'rejected': return null   // gate said no (unknown domain) — say nothing, headline stands
    default: return 'full text unavailable'
  }
}
