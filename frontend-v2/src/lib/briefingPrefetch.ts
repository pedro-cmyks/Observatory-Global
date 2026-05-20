const CACHE_KEY = 'atlas_brief_prefetch'
const MAX_AGE_MS = 4 * 60 * 1000

interface PrefetchPayload {
  briefing: unknown
  insight: string | null
  fetchedAt: number
  hours: number
}

export function readBriefingCache(hours: number): { briefing: unknown; insight: string | null } | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const payload: PrefetchPayload = JSON.parse(raw)
    if (payload.hours !== hours) return null
    if (Date.now() - payload.fetchedAt > MAX_AGE_MS) return null
    return { briefing: payload.briefing, insight: payload.insight }
  } catch {
    return null
  }
}

export async function prefetchBriefing(hours = 24): Promise<void> {
  if (readBriefingCache(hours)) return
  try {
    const [briefRes, insightRes] = await Promise.all([
      fetch(`/api/v2/briefing?hours=${hours}`),
      fetch(`/api/v2/briefing/insight?hours=${hours}`)
    ])
    if (!briefRes.ok) return
    const briefing = await briefRes.json()
    let insight: string | null = null
    if (insightRes.ok) {
      const insightData = await insightRes.json()
      if (insightData.insight) insight = insightData.insight
    }
    const payload: PrefetchPayload = { briefing, insight, fetchedAt: Date.now(), hours }
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))
  } catch {
    // prefetch is best-effort
  }
}
