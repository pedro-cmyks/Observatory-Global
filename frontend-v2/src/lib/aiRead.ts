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

/** Source-independence verdict on a corroboration (Council R3 P1): syndicated
 *  wire copies of one story are 'shared_source', not corroboration.
 *
 *  corroborate-v2 R2 adds two DERIVATION reasons above byte-identity —
 *  'same_primary_source' (both articles attribute their content to the same
 *  outlet, or one attributes to the other's masthead: the G-HAARETZ witness,
 *  three rewrites of one report) and 'shared_quotes' (two "independent"
 *  accounts built from the same quote set). `label` is authored by the backend
 *  (`_INDEPENDENCE_LABEL`); the render shows it verbatim. */
export type IndependenceReason =
  | 'independent' | 'same_outlet' | 'same_wire'
  | 'same_primary_source' | 'shared_quotes'

export interface Independence {
  independent: boolean
  reason: IndependenceReason
  label: string
}

/** Compact chip for a cross-read finding. The `reason` refines a
 *  'shared_source': naming DERIVATION where it was measured, instead of
 *  calling every non-independent pair a wire echo. Pure. */
export function crossFindingLabel(kind: string, reason?: IndependenceReason | string | null): string {
  if (kind === 'tension') return '⚠ possible tension'
  if (kind === 'shared_source' || kind === 'same_primary_source' || kind === 'shared_quotes') {
    if (reason === 'same_primary_source' || kind === 'same_primary_source') return '⊘ 1 primary source (attributed)'
    if (reason === 'shared_quotes' || kind === 'shared_quotes') return '⊘ same underlying quotes'
    return '⊘ same source (not independent)'
  }
  return '✓ corroboration'
}

/** The same distinction spelled out for the markdown export (no glyphs). Pure. */
export function crossFindingLabelLong(kind: string, reason?: IndependenceReason | string | null): string {
  if (kind === 'tension') return 'Possible tension'
  if (kind === 'shared_source' || kind === 'same_primary_source' || kind === 'shared_quotes') {
    if (reason === 'same_primary_source' || kind === 'same_primary_source') {
      return '1 primary source (attributed) — not independent corroboration'
    }
    if (reason === 'shared_quotes' || kind === 'shared_quotes') {
      return 'Same underlying quotes — not independent corroboration'
    }
    return 'Same source (not independent corroboration)'
  }
  return 'Corroboration'
}

/** Why this pair is (or is not) independent corroboration — one sentence,
 *  keyed on the MEASURED reason. Pure. */
export function independenceTip(ind: Independence): string {
  if (ind.independent) return 'Two independent sources agree — corroboration.'
  switch (ind.reason) {
    case 'same_primary_source':
      return 'Both accounts attribute their content to the same outlet — one primary source retold, not two sources converging.'
    case 'shared_quotes':
      return 'The two accounts rest on the same underlying quotes — one reporting act reaching you twice, not independent corroboration.'
    case 'same_outlet':
      return 'Two pages of one masthead — the same outlet agreeing with itself.'
    default:
      return 'The claims agree but come from one wire source echoing itself — not independent corroboration.'
  }
}

export interface CrossFinding {
  kind: 'corroboration' | 'tension' | 'shared_source'
  a: { id: string; url: string; outlet?: string; text: string; quote: string; attribution?: string }
  b: { id: string; url: string; outlet?: string; text: string; quote: string; attribution?: string }
  note: string
  independence?: Independence
}

export interface CrossRead {
  findings: CrossFinding[]
  articles_read: number
  articles_with_claims: number
  independent_corroborations?: number
  shared_source_findings?: number
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
