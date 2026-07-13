// Web corroboration (contract dossier-corroboration-v1, roadmap P0.6b).
//
// Productizes the manual NATO-Ankara corroboration run: each pin is checked
// against live web coverage (backend lane: GDELT DOC 2.0) with SOURCE-
// INDEPENDENCE weighting — syndicated wire copies collapse to one source,
// independently-operated outlets are counted, never articles (the G2 rule).
// LLM phrases ONE thing: the coverage-asymmetry note over the gathered titles.
//
// Cached per investigation in localStorage; re-run on demand. Degrades
// honestly: if no search path answered, the section SAYS so.
import type { WorkbenchPin } from './workbench'
import type { ConnectionNode } from './dossierConnections'

export interface CorroborationCitation {
  title: string
  url: string
  outlet: string
  language?: string | null
  seendate?: string | null
  lane?: string | null
}

export interface CorroborationPin {
  id: string
  label: string
  status: 'established' | 'contested' | 'unverified' | 'not_applicable'
  independent_outlets: number
  total_articles: number
  syndicated_clusters: number
  single_source: boolean
  citations: CorroborationCitation[]
  note: string
  queries: string[]
}

export interface CorroborationData {
  contract: string
  measured_at: string
  search_available: boolean
  search_source: string | null
  window_days: number
  pins: CorroborationPin[]
  coverage_asymmetry: { note: string; provider: string | null } | null
  meta?: { independence_rule?: string; status_rule?: string; search_note?: string | null }
}

/** ✓ established / ⚠ contested / ? unverified — the per-pin status chip. */
export function statusChip(status: CorroborationPin['status']): string {
  if (status === 'established') return '✓ established'
  if (status === 'contested') return '⚠ contested'
  if (status === 'not_applicable') return '— not applicable'
  return '? unverified'
}

/** Build the request body from the frozen pins (+ measured actors from the
 *  connection nodes, when the measurement already landed). Pure/testable. */
export function buildCorroborationRequest(
  pins: WorkbenchPin[],
  connNodes?: ConnectionNode[] | null,
): { pins: Array<{ id: string; label: string; anchor_type: string; actors: string[]; evidence: string[] }>; days: number } {
  const nodeFor = (p: WorkbenchPin): ConnectionNode | undefined =>
    (connNodes ?? undefined)?.find(n =>
      n.id === p.anchorId || n.base_id === p.anchorId || n.collapsed_from?.includes(p.anchorId)
      || n.label === p.label)
  return {
    pins: pins.map(p => ({
      id: p.anchorId,
      label: p.label,
      anchor_type: p.anchorType,
      actors: (nodeFor(p)?.persons ?? []).slice(0, 3),
      evidence: (p.snapshot?.evidence ?? []).slice(0, 6).map(e => {
        const attribution = e.source
          ? ` — ${e.source}${e.date ? `, ${e.date}` : ''}`
          : (e.date ? ` — ${e.date}` : '')
        return `${e.headline}${attribution}`
      }),
    })),
    days: 14,
  }
}

/** POST the corroboration run. Returns null on any failure (the section
 *  renders its honest empty state; never throws into the report). */
export async function fetchCorroboration(
  body: ReturnType<typeof buildCorroborationRequest>,
  force = false,
): Promise<CorroborationData | null> {
  try {
    const res = await fetch('/api/v2/dossier/corroborate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...body, force }),
    })
    if (!res.ok) return null
    return await res.json() as CorroborationData
  } catch {
    return null
  }
}

// ── Per-investigation cache (re-run on demand) ───────────────────────────────
const CACHE_KEY = 'atlas.corroboration.v2'
const CACHE_MAX_AGE_MS = 24 * 3600 * 1000

export function loadCachedCorroboration(invId: string): CorroborationData | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const map = JSON.parse(raw) as Record<string, CorroborationData>
    const hit = map[invId]
    if (!hit) return null
    if (Date.now() - new Date(hit.measured_at).getTime() > CACHE_MAX_AGE_MS) return null
    return hit
  } catch {
    return null
  }
}

export function saveCorroboration(invId: string, data: CorroborationData): void {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    const map = raw ? JSON.parse(raw) as Record<string, CorroborationData> : {}
    map[invId] = data
    // keep the map small: drop entries older than the max age
    for (const [k, v] of Object.entries(map)) {
      if (Date.now() - new Date(v.measured_at).getTime() > CACHE_MAX_AGE_MS) delete map[k]
    }
    localStorage.setItem(CACHE_KEY, JSON.stringify(map))
  } catch { /* quota — section still renders from memory */ }
}

export function clearCorroboration(invId: string): void {
  try {
    const raw = localStorage.getItem(CACHE_KEY)
    if (!raw) return
    const map = JSON.parse(raw) as Record<string, CorroborationData>
    delete map[invId]
    localStorage.setItem(CACHE_KEY, JSON.stringify(map))
  } catch { /* ignore */ }
}

function fmtMeasured(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

/** Markdown block for the export (inserted before Timeline, like the
 *  connection findings). Mirrors the on-screen section 1:1. */
export function corroborationMarkdown(c: CorroborationData): string[] {
  const lines: string[] = []
  lines.push(`## Web corroboration — measured ${fmtMeasured(c.measured_at)}, independent sources weighted`)
  if (!c.search_available) {
    lines.push('')
    lines.push(`_${c.meta?.search_note ?? 'Web-search lane unavailable — corroboration not measured.'}_`)
  } else {
    lines.push(`*Source: ${c.search_source ?? 'unknown'} · window ${c.window_days}d · syndicated wire copies collapse to one source; independently-operated outlets counted, never articles.*`)
  }
  lines.push('')
  for (const p of c.pins) {
    lines.push(`### ${statusChip(p.status)} — ${p.label}`)
    lines.push(`${p.note} (${p.independent_outlets} independent · ${p.total_articles} articles · ${p.syndicated_clusters} syndicated cluster${p.syndicated_clusters === 1 ? '' : 's'})`)
    for (const cit of p.citations) {
      lines.push(`- [${cit.title}](${cit.url}) — ${cit.outlet}`)
    }
    lines.push('')
  }
  if (c.coverage_asymmetry?.note) {
    lines.push('**Coverage asymmetry** (phrased from the gathered titles only'
      + (c.coverage_asymmetry.provider ? `, ${c.coverage_asymmetry.provider}` : '') + '):')
    lines.push(c.coverage_asymmetry.note)
    lines.push('')
  }
  return lines
}
