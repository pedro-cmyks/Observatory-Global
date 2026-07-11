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

export interface FrozenEvidence {
  headline: string
  source?: string
  url?: string
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
    return rows.slice(0, max).map(({ r }) => ({
      headline: String(r.headline ?? r.title ?? r.label),
      source: typeof (r.source ?? r.domain) === 'string' ? String(r.source ?? r.domain) : undefined,
      url: typeof (r.url ?? r.link) === 'string' ? String(r.url ?? r.link) : undefined,
    }))
  }
  return []
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
