const CACHE_KEY = 'atlas_brief_prefetch'
const MAX_AGE_MS = 4 * 60 * 1000
const MAX_STALE_AGE_MS = 24 * 60 * 60 * 1000

interface PrefetchPayload {
  briefing: unknown
  insight: string | null
  /** When the insight itself was generated (server truth), not when it cached. */
  insightGeneratedAt?: string | null
  fetchedAt: number
  hours: number
}

interface BriefingCacheRead {
  briefing: unknown
  insight: string | null
  insightGeneratedAt: string | null
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
    return {
      briefing: payload.briefing,
      insight: payload.insight,
      insightGeneratedAt: payload.insightGeneratedAt ?? null,
      isStale,
    }
  } catch {
    return null
  }
}

export function writeBriefingCache(
  hours: number,
  briefing: unknown,
  insight: string | null = null,
  insightGeneratedAt: string | null = null,
): void {
  const payload: PrefetchPayload = {
    briefing,
    insight,
    insightGeneratedAt,
    fetchedAt: Date.now(),
    hours,
  }
  sessionStorage.setItem(CACHE_KEY, JSON.stringify(payload))
}

/**
 * Fold a late-arriving insight into the cached payload.
 *
 * THIS IS THE FLICKER (judge §4.10: "Editor's Analysis appears and disappears
 * between reloads"). The brief is cached the instant it lands — deliberately,
 * so the front page never waits on an LLM — but the insight resolves seconds
 * later and used to be written to React state ONLY. The next load inside the
 * 4-minute TTL therefore read a cached payload whose `insight` was `null`,
 * short-circuited before re-requesting it, and rendered the bare fallback line
 * ("41,898 signals across 202 countries…") in its place. Two loads with the
 * analysis, two without, for no reason the reader could see.
 *
 * Writing it back makes the surface deterministic: once a reading exists for a
 * window, every load in that window shows it.
 */
export function updateCachedInsight(
  hours: number,
  insight: string | null,
  insightGeneratedAt: string | null = null,
): void {
  if (!insight) return
  try {
    const raw = sessionStorage.getItem(CACHE_KEY)
    if (!raw) return
    const current: PrefetchPayload = JSON.parse(raw)
    if (current.hours !== hours) return
    sessionStorage.setItem(
      CACHE_KEY,
      JSON.stringify({ ...current, insight, insightGeneratedAt }),
    )
  } catch {
    /* the cache is an optimisation; never let it throw into a render */
  }
}

/** Force the next read to go to the network (the reader pressed retry). */
export function clearBriefingCache(): void {
  try {
    sessionStorage.removeItem(CACHE_KEY)
  } catch {
    /* best-effort */
  }
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
        updateCachedInsight(
          hours,
          insightData?.insight ?? null,
          insightData?.generated_at ?? null,
        )
      })
      .catch(() => { /* insight is best-effort */ })
  } catch {
    // prefetch is best-effort
  }
}
