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

/** Coarse credibility rollup (#217) measured server-side by
 *  `source_tiers.tier_payload` — the authoritative classification travels with
 *  the citation so the render never re-guesses it. Optional: pre-v2 payloads
 *  carry no credibility block and render without a chip. */
export interface CorroborationCredibility {
  tier: number | string
  label: string
  provenance?: string | null
}

export interface CorroborationCitation {
  title: string
  url: string
  outlet: string
  language?: string | null
  seendate?: string | null
  lane?: string | null
  /** corroborate-v2 R1: ownership key that collapsed this outlet into a shared
   *  VOICE (e.g. 'state:ru' for ria/tass/rt). null/absent = no known shared
   *  owner — the outlet counts as its own voice. */
  ownership_group?: string | null
  credibility?: CorroborationCredibility | null
}

export interface CorroborationPin {
  id: string
  label: string
  status: 'established' | 'contested' | 'unverified' | 'not_applicable'
  /** Distinct outlets after syndication clustering — receipts stay visible. */
  independent_outlets: number
  /** corroborate-v2 R1: outlets AFTER ownership collapse — the number the
   *  status is judged on. Absent on pre-v2 payloads (then outlets == voices by
   *  construction, and the render says nothing it did not measure). */
  independent_voices?: number
  /** How many outlets the ownership collapse absorbed (outlets − voices). */
  state_collapsed?: number
  total_articles: number
  syndicated_clusters: number
  single_source: boolean
  citations: CorroborationCitation[]
  note: string
  queries: string[]
}

/** Per-claim verdict from `POST /api/v2/corroborate` (corroboration-v1 +
 *  corroborate-v2 fields). `template_matches` = matches that shared only a
 *  casualty TEMPLATE and no entity anchor (F2); `aged` = receipts outside the
 *  `window_days` temporal window (R3), counted as context, never as backing.
 *  All v2 fields optional — an older backend's verdict still parses. */
export interface CorroborationVerdict {
  status: 'corroborated' | 'contradicted' | 'uncorroborated' | string
  corroborating: number
  contradicting: number
  official_corroborating: number
  note: string
  template_matches?: number
  aged?: number
  window_days?: number
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

/** The counts line under a pin's note. v2 leads with VOICES (the number the
 *  status is judged on) and keeps outlets visible beside it, naming the
 *  ownership collapse when it changed the number. A pre-v2 payload (no
 *  `independent_voices`) renders the original outlets-only line byte-for-byte
 *  — we never restate an old measurement in new words. Pure. */
export function pinCountsText(p: CorroborationPin): string {
  const clusters = `${p.syndicated_clusters} syndicated cluster${p.syndicated_clusters === 1 ? '' : 's'}`
  if (p.independent_voices === undefined || p.independent_voices === null) {
    return `${p.independent_outlets} independent · ${p.total_articles} articles · ${clusters}`
  }
  const collapse = (p.state_collapsed ?? 0) > 0 ? ' · same-owner outlets counted as one voice' : ''
  return `${p.independent_voices} independent voice${p.independent_voices === 1 ? '' : 's'}`
    + ` · ${p.independent_outlets} outlets · ${p.total_articles} articles · ${clusters}${collapse}`
}

/** The credibility chip for one corroboration citation — from the backend's
 *  own classification, never re-derived here. Returns null when the backend
 *  said nothing (absence over guess) or the tier is 'unknown'. Pure. */
export function citationTierChip(cit: CorroborationCitation): string | null {
  const label = (cit.credibility?.label ?? '').trim()
  if (!label || label.toLowerCase() === 'unknown') return null
  return `[${label.toUpperCase()}]`
}

/** Backend tier vocabulary (source_tiers.TIER_LABELS) → the shared receipt-chip
 *  modifier the L2 surfaces already style (`.l2-tier-chip--*`). Labels without
 *  a hue of their own reuse the nearest established one rather than rendering
 *  an unstyled chip. null when there is nothing to show. Pure. */
const TIER_CHIP_CLASS: Record<string, string> = {
  state: 'state', wire: 'wire', reference: 'wire',
  mainstream: 'major', major: 'major', local: 'local', flagged: 'state',
}

export function citationTierClass(cit: CorroborationCitation): string | null {
  if (!citationTierChip(cit)) return null
  const label = (cit.credibility?.label ?? '').trim().toLowerCase()
  return TIER_CHIP_CLASS[label] ?? 'local'
}

/** Why this citation did not count as its own voice, in one plain line — or
 *  null when it did. Pure. */
export function citationCollapseNote(cit: CorroborationCitation): string | null {
  const group = (cit.ownership_group ?? '').trim()
  if (!group) return null
  const state = group.startsWith('state:') ? group.slice('state:'.length).toUpperCase() : null
  return state
    ? `Same state apparatus (${state}) as other outlets here — counted as one voice, not several.`
    : `Shares an ownership group (${group}) with other outlets here — counted as one voice.`
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
    lines.push(`${p.note} (${pinCountsText(p)})`)
    for (const cit of p.citations) {
      const chip = citationTierChip(cit)
      lines.push(`- [${cit.title}](${cit.url}) — ${cit.outlet}${chip ? ` ${chip}` : ''}`)
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
