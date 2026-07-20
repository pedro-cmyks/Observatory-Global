/** Workbench AI-read + LEADS client (F2/F2.5 — spec 2026-07-20 §5/§5b).
 *
 *  All server-computed, all labeled: claims carry verbatim quotes (quoteless
 *  claims never leave the backend), leads carry their measured Atlas basis.
 *  Every call degrades silently — the Workbench renders honest absence. */

export interface ReadClaim {
  text: string
  quote: string
  attribution: 'asserted' | 'attributed'
  attributed_to?: string | null
}

export interface Reading {
  claims: ReadClaim[]
  actors: Array<{ name: string; kind: string; role: string }>
  numbers: Array<{ value: string; what: string }>
  gaps: string[]
  dropped_claims?: number
  model?: string
  read_at?: string | null
}

export interface CrossFinding {
  kind: 'corroboration' | 'tension'
  a: { id: string; url: string; text: string; quote: string; attribution?: string }
  b: { id: string; url: string; text: string; quote: string; attribution?: string }
  note: string
}

export interface CrossRead {
  findings: CrossFinding[]
  articles_read: number
  articles_with_claims: number
  model?: string
  reason?: string
  note?: string
}

export interface Lead {
  entity: string
  kind: string
  role: string
  quote?: string | null
  source_url: string
  threads: Array<{ thread_id: string; label?: string | null; signal_count?: number | null }>
  thread_count: number
}

export interface LeadsResult {
  leads: Lead[]
  suppressed: Array<{ name: string; reason: string }>
  articles_read: number
  entities_considered: number
  basis?: string
  reason?: string
}

async function post<T>(path: string, body: unknown): Promise<T | null> {
  try {
    const resp = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!resp.ok) return null
    return await resp.json() as T
  } catch {
    return null
  }
}

export async function fetchReadings(urls: string[]): Promise<Map<string, Reading>> {
  const clean = urls.filter(u => (u ?? '').startsWith('http')).slice(0, 64)
  const out = new Map<string, Reading>()
  if (clean.length === 0) return out
  const data = await post<{ readings: Record<string, Reading> }>(
    '/api/v2/research/articles/read', { urls: clean })
  for (const [url, r] of Object.entries(data?.readings ?? {})) out.set(url, r)
  return out
}

export async function fetchCrossRead(urls: string[]): Promise<CrossRead | null> {
  const clean = urls.filter(u => (u ?? '').startsWith('http')).slice(0, 64)
  if (clean.length < 2) return null
  return post<CrossRead>('/api/v2/research/articles/crossread', { urls: clean })
}

export async function fetchLeads(urls: string[], pinnedIds: string[]): Promise<LeadsResult | null> {
  const clean = urls.filter(u => (u ?? '').startsWith('http')).slice(0, 64)
  if (clean.length === 0) return null
  return post<LeadsResult>('/api/v2/research/leads', { urls: clean, pinned_ids: pinnedIds.slice(0, 128) })
}

/** Label for the AI-read provenance chip — model + date, never bare "AI". */
export function readProvenance(r?: Pick<Reading, 'model' | 'read_at'> | null): string {
  if (!r) return 'AI READ'
  const day = r.read_at ? ` · ${r.read_at.slice(0, 10)}` : ''
  return `AI READ · ${r.model ?? 'model unknown'}${day}`
}
