const CACHE_KEY = 'atlas_brief_prefetch'
const MAX_AGE_MS = 4 * 60 * 1000
const MAX_STALE_AGE_MS = 24 * 60 * 60 * 1000

interface PrefetchPayload {
  briefing: unknown
  insight: string | null
  fetchedAt: number
  hours: number
}

interface BriefingCacheRead {
  briefing: unknown
  insight: string | null
  isStale: boolean
}

export function readBriefingCache(
  hours: number,
  options: { allowStale?: boolean } = {},
): BriefingCacheRead | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const payload: PrefetchPayload = JSON.parse(raw)
    if (payload.hours !== hours) return null
    const age = Date.now() - payload.fetchedAt
    if (age > MAX_STALE_AGE_MS) return null
    const isStale = age > MAX_AGE_MS
    if (isStale && !options.allowStale) return null
    return { briefing: payload.briefing, insight: payload.insight, isStale }
  } catch {
    return null
  }
}

export function writeBriefingCache(
  hours: number,
  briefing: unknown,
  insight: string | null = null,
): void {
  const payload: PrefetchPayload = {
    briefing,
    insight,
    fetchedAt: Date.now(),
    hours,
  }
  sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))
}

export async function prefetchBriefing(hours = 24): Promise<void> {
  if (readBriefingCache(hours)) return
  try {
    // Cache the brief as soon as it lands — do NOT wait on the insight LLM
    // (Anthropic→DeepSeek) call, which can take seconds or hang and would
    // otherwise leave the prefetch cache empty when the user reaches /brief.
    const briefRes = await fetch(`/api/v2/briefing?hours=${hours}`)
    if (!briefRes.ok) return
    const briefing = await briefRes.json()
    writeBriefingCache(hours, briefing)

    // Fill the insight into the cached payload in the background, best-effort.
    fetch(`/api/v2/briefing/insight?hours=${hours}`)
      .then(r => (r.ok ? r.json() : null))
      .then(insightData => {
        const insight: string | null = insightData?.insight ?? null
        if (!insight) return
        const raw = sessionStorage.getItem(CACHE_KEY)
        if (!raw) return
        const current: PrefetchPayload = JSON.parse(raw)
        if (current.hours !== hours) return
        sessionStorage.setItem(CACHE_KEY, JSON.stringify({ ...current, insight }))
      })
      .catch(() => { /* insight is best-effort */ })
  } catch {
    // prefetch is best-effort
  }
}
