// W3 (L3 review 2026-07-05) — dossier v2 enrichment: the wedge sections.
//
// The dossier core stays FROZEN (pins + snapshots, lib/dossier.ts). These
// sections are MEASURED AT GENERATION TIME from existing endpoints — labeled
// as such, never mixed with the frozen evidence:
//   - who-says-what per pinned thread: typed topic_members roles via
//     GET /api/v2/topic/{id}/relationship (press=evidence vs public=discussion)
//   - voice per pinned country: GET /api/v2/voice-mix?country=CC (self-voice
//     by OWNERSHIP, dominant outsider, state-media share)
// Every fetch degrades to absence — a missing section, never a broken report.
import type { Investigation, WorkbenchPin } from './workbench'

export interface WhoSaysWhatEntry {
  relationship: string
  evidenceCount: number
  discussionCount: number
  moodCount: number
  rationale: string
}

export interface VoiceEntry {
  selfVoiceRatio: number | null
  dominantOutsider: string | null
  stateMediaPct: number | null
  topForeignOrigins: string[]
}

export interface DossierEnrichment {
  measuredAt: string
  whoSaysWhat: Record<string, WhoSaysWhatEntry>
  voice: Record<string, VoiceEntry>
}

const THREAD_CAP = 6
const COUNTRY_CAP = 3

/** Resolve the relationship-endpoint topic id for a pin, or null. Accepts
 *  research anchors (open.params.thread_id) and W1 panel pins
 *  (?theme=dynamic-topic-N urlParams / theme-<slug> anchor ids). */
export function resolveThreadTopicId(pin: WorkbenchPin): string | null {
  const params = (pin.open?.params ?? {}) as Record<string, unknown>
  if (params.thread_id) return String(params.thread_id)
  const urlParams = typeof params.urlParams === 'string' ? params.urlParams : ''
  const theme = new URLSearchParams(urlParams.replace(/^\?/, '')).get('theme')
  if (theme) return theme
  if (pin.anchorType === 'theme' && pin.anchorId.startsWith('theme-')) {
    return pin.anchorId.slice('theme-'.length)
  }
  if (pin.anchorType === 'thread') return pin.anchorId
  return null
}

/** Countries referenced by the pinned route (country pins first). */
export function resolvePinnedCountries(pins: WorkbenchPin[]): string[] {
  const out: string[] = []
  for (const p of pins) {
    const params = (p.open?.params ?? {}) as Record<string, unknown>
    let cc: string | null = null
    if (params.country_code) cc = String(params.country_code)
    else if (typeof params.urlParams === 'string') {
      cc = new URLSearchParams(params.urlParams.replace(/^\?/, '')).get('country')
    }
    if (!cc && p.anchorType === 'country' && p.anchorId.startsWith('country-')) {
      cc = p.anchorId.slice('country-'.length)
    }
    if (cc) {
      const norm = cc.toUpperCase()
      if (norm.length === 2 && !out.includes(norm)) out.push(norm)
    }
  }
  return out.slice(0, COUNTRY_CAP)
}

export async function fetchDossierEnrichment(inv: Investigation): Promise<DossierEnrichment> {
  const whoSaysWhat: Record<string, WhoSaysWhatEntry> = {}
  const voice: Record<string, VoiceEntry> = {}

  const threadPins = inv.pins
    .map(p => ({ pin: p, topicId: resolveThreadTopicId(p) }))
    .filter((x): x is { pin: WorkbenchPin; topicId: string } => !!x.topicId)
    .slice(0, THREAD_CAP)

  const threadFetches = threadPins.map(async ({ pin, topicId }) => {
    try {
      const res = await fetch(`/api/v2/topic/${encodeURIComponent(topicId)}/relationship`)
      if (!res.ok) return
      const d = await res.json() as Record<string, unknown>
      if (typeof d.relationship !== 'string') return
      whoSaysWhat[pin.anchorId] = {
        relationship: d.relationship,
        evidenceCount: Number(d.evidence_count ?? 0),
        discussionCount: Number(d.discussion_count ?? 0),
        moodCount: Number(d.mood_count ?? 0),
        rationale: String(d.rationale ?? ''),
      }
    } catch { /* section absent, report intact */ }
  })

  const countryFetches = resolvePinnedCountries(inv.pins).map(async cc => {
    try {
      const res = await fetch(`/api/v2/voice-mix?hours=168&country=${encodeURIComponent(cc)}`)
      if (!res.ok) return
      const d = await res.json() as Record<string, unknown>
      const rel = (d.relation ?? {}) as Record<string, unknown>
      // live shapes: dominant_outsider = {origin, n, pct_of_foreign};
      // top_foreign_origins = [{cc, n}, ...]
      const dom = rel.dominant_outsider as Record<string, unknown> | null | undefined
      voice[cc] = {
        selfVoiceRatio: typeof rel.self_voice_ratio === 'number' ? rel.self_voice_ratio : null,
        dominantOutsider: dom && typeof dom === 'object' && dom.origin ? String(dom.origin) : null,
        stateMediaPct: typeof d.state_media_pct === 'number' ? d.state_media_pct : null,
        topForeignOrigins: Array.isArray(rel.top_foreign_origins)
          ? (rel.top_foreign_origins as Array<Record<string, unknown>>)
              .slice(0, 3).map(x => String(x?.cc ?? '')).filter(Boolean)
          : [],
      }
    } catch { /* section absent */ }
  })

  await Promise.allSettled([...threadFetches, ...countryFetches])
  return { measuredAt: new Date().toISOString(), whoSaysWhat, voice }
}
