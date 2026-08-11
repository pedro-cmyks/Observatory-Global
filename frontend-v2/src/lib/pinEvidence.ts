// #227 evidence freezing — shared by every pin path.
//
// The NATO-Ankara dossier run exposed two holes: (a) story-first pins (research
// plan → PIN) froze metadata only, so the dossier said "captured without frozen
// evidence"; (b) thread pins froze the 3 most RECENT members (drift, e.g. a
// Romanian tangent) instead of the CORE. This lib is the one tolerant
// extractor: it finds headline-shaped rows in any detail payload and prefers
// gate-verified / high-score rows when the payload carries them (atlas theme
// rows have gateKept/gateScore/tier; dynamic rows don't — those keep payload
// order). Pure + unit-testable; the fetch wrapper degrades to null so a pin
// never blocks on evidence.

import { decodeEntities } from './decodeEntities'
import { PIN_EVIDENCE_FREEZE_CAP } from './workbench'

export interface FrozenEvidence {
  headline: string
  source?: string
  url?: string
  /** ISO day (YYYY-MM-DD) of the underlying signal, when the payload carried a
   *  timestamp — P0.3: frozen evidence must keep its date. */
  date?: string
}

const EVIDENCE_KEYS = ['signals', 'signalSample', 'top_stories', 'evidence_samples', 'results', 'items']
const SCAN_ROWS = 24 // rank within a bounded prefix; payloads can be large

/** Lower rank = more core. gateKept/tier=verified first, then extended, then
 *  ungated; gateScore/confidence breaks ties; original order is the final tie. */
function coreRank(r: Record<string, unknown>): number {
  const tier = typeof r.tier === 'string' ? r.tier : null
  if (r.gateKept === true || r.gate_kept === true || tier === 'verified') return 0
  if (tier === 'extended') return 1
  return 2
}

function rowScore(r: Record<string, unknown>): number {
  for (const k of ['gateScore', 'gate_score', 'confidence']) {
    const v = r[k]
    if (typeof v === 'number') return v
  }
  return -1
}

/** Find the first array of headline-shaped rows in a detail payload and return
 *  up to `max` frozen evidence items, core-first when the rows carry gate/score
 *  fields. */
export function extractSnapshotEvidence(
  json: Record<string, unknown>, max = 3,
): FrozenEvidence[] {
  for (const key of EVIDENCE_KEYS) {
    const arr = json[key]
    if (!Array.isArray(arr) || arr.length === 0) continue
    const rows = arr.slice(0, SCAN_ROWS)
      .filter((row): row is Record<string, unknown> => !!row && typeof row === 'object')
      .map((r, i) => ({ r, i }))
      .filter(({ r }) => typeof (r.headline ?? r.title ?? r.label) === 'string')
    if (rows.length === 0) continue
    rows.sort((a, b) =>
      coreRank(a.r) - coreRank(b.r)
      || rowScore(b.r) - rowScore(a.r)
      || a.i - b.i)
    return rows.slice(0, max).map(({ r }) => {
      const ts = r.timestamp ?? r.time ?? r.date ?? r.published_at
      return {
        headline: String(r.headline ?? r.title ?? r.label),
        source: typeof (r.source ?? r.domain) === 'string' ? String(r.source ?? r.domain) : undefined,
        url: typeof (r.url ?? r.link) === 'string' ? String(r.url ?? r.link) : undefined,
        date: typeof ts === 'string' && ts.length >= 10 ? ts.slice(0, 10) : undefined,
      }
    })
  }
  return []
}

/** Council R4 N25 — freeze the rows the panel was DISPLAYING at pin time.
 *
 *  `extractSnapshotEvidence` above works on a payload the pin path RE-FETCHES;
 *  that re-fetch is a second network call with its own window, its own scope
 *  and its own failure modes, so a thread showing 35 signals on screen could
 *  land in the dossier as "metadata only — no frozen evidence" (the DESKTOP
 *  seat's wedge-killer). This one takes the rows already in the panel's hands.
 *  No network, no ranking: DISPLAY ORDER is preserved because the claim being
 *  frozen is "this is what the analyst saw", not "these are the best rows".
 *
 *  Tolerant like its sibling (headline|title|label, source|domain, url|link,
 *  timestamp|time|date|published_at), de-duplicated by url (syndication repeats
 *  one receipt) then by headline, and capped at {@link PIN_EVIDENCE_FREEZE_CAP}.
 *  Any non-array input returns [] — a pin never blocks or throws on evidence. */
export function freezeVisibleEvidence(
  rows: unknown, cap = PIN_EVIDENCE_FREEZE_CAP,
): FrozenEvidence[] {
  if (!Array.isArray(rows)) return []
  const out: FrozenEvidence[] = []
  const seen = new Set<string>()
  for (const row of rows) {
    if (out.length >= cap) break
    if (!row || typeof row !== 'object') continue
    const r = row as Record<string, unknown>
    const rawHeadline = r.headline ?? r.title ?? r.label
    if (typeof rawHeadline !== 'string') continue
    const headline = decodeEntities(rawHeadline).trim()
    if (!headline) continue
    const rawUrl = r.url ?? r.link
    const url = typeof rawUrl === 'string' && rawUrl.trim() ? rawUrl.trim() : undefined
    const key = url ? `u:${url}` : `h:${headline.toLowerCase()}`
    if (seen.has(key)) continue
    seen.add(key)
    const src = r.source ?? r.domain
    const ts = r.timestamp ?? r.time ?? r.date ?? r.published_at
    out.push({
      headline,
      source: typeof src === 'string' ? src : undefined,
      url,
      date: typeof ts === 'string' && ts.length >= 10 ? ts.slice(0, 10) : undefined,
    })
  }
  return out
}

/** N25 precedence rule: when a pin already froze the VISIBLE rows, a later
 *  async panel re-fetch may still enrich the snapshot (counts, label-court
 *  verdict, summary) but must NOT replace the evidence — the analyst's screen
 *  wins over a re-fetch that may have drifted, narrowed or failed. */
export function enrichmentWithoutEvidence<T extends { evidence?: unknown }>(
  snapshot: T,
): Omit<T, 'evidence'> {
  const { evidence: _dropped, ...rest } = snapshot
  void _dropped
  return rest
}

/** Fetch a thread's detail and extract frozen evidence for a pin snapshot.
 *  Null on any failure — the metadata-only snapshot stands. */
export async function fetchThreadEvidence(
  threadId: string, hours = 24,
): Promise<FrozenEvidence[] | null> {
  try {
    const res = await fetch(`/api/v2/theme/${encodeURIComponent(threadId)}?hours=${hours}`)
    if (!res.ok) return null
    const json = await res.json() as Record<string, unknown>
    const evidence = extractSnapshotEvidence(json)
    return evidence.length > 0 ? evidence : null
  } catch {
    return null
  }
}
