// Dossier synthesis (contract dossier-synthesis-v1) — the standalone-brief layer.
//
// The report must stand alone (the "Frank test"): a stranger reading only it must
// understand the story. The templated one-liner can't. This asks the backend for
// ONE grounded LLM pass over the FROZEN pin evidence + the MEASURED connection
// verdict → {headline, synthesis, gap}. Measured at generation time, labeled as
// such; degrades to null so the frozen report always stands on its own.
import type { DossierModel } from './dossier'
import {
  connectionState, edgeReason, edgeStrength,
  type ConnectionsData, type ClusterResult,
} from './dossierConnections'

export interface DossierSynthesis {
  contract: string
  headline: string | null
  synthesis: string | null
  gap: string | null
  provider: string | null
  error: string | null
}

/** Build the request from the frozen dossier + the measured connection data,
 *  then POST for the synthesis. Returns null on any failure (frozen core stands). */
export async function synthesizeDossier(
  dossier: DossierModel,
  conn: { data: ConnectionsData; cluster: ClusterResult } | null,
): Promise<DossierSynthesis | null> {
  const pins = dossier.pins.map(p => ({
    label: p.label,
    type: p.anchorType,
    // Fold the source into the headline so the LLM can attribute contested
    // outcomes ("reported by <outlet>") instead of asserting them as fact.
    evidence: (p.snapshot?.evidence ?? []).slice(0, 6)
      .map(e => (e.source ? `${e.headline} — ${e.source}` : e.headline)),
    note: p.note ?? null,
  }))
  if (pins.length === 0) return null

  let connection: Record<string, unknown> | null = null
  if (conn && conn.data.nodes.length >= 2) {
    const { data, cluster } = conn
    const labelOf = (id: string) => data.nodes.find(n => n.id === id)?.label ?? id
    // Per-pin connectedness: a pin is CONFIRMED-connected when a shared-actor or
    // shared-country edge ties it to another pin, SIMILAR-ONLY when its only links
    // are semantic proximity, ISOLATED when nothing pinned connects to it. This is
    // the fix for the over-claim failure — the whole set can read 'grounded' off a
    // single confirmed edge while a third pin hangs on similarity-only edges.
    const confirmedWith = new Map<string, Set<string>>()
    const similarWith = new Map<string, Set<string>>()
    for (const n of data.nodes) { confirmedWith.set(n.id, new Set()); similarWith.set(n.id, new Set()) }
    for (const e of data.edges) {
      const bucket = edgeStrength(e) === 'strong' ? confirmedWith : similarWith
      bucket.get(e.a)?.add(e.b)
      bucket.get(e.b)?.add(e.a)
    }
    const nodes = data.nodes.map(n => {
      const conf = [...(confirmedWith.get(n.id) ?? [])]
      const confSet = confirmedWith.get(n.id) ?? new Set<string>()
      const sim = [...(similarWith.get(n.id) ?? [])].filter(id => !confSet.has(id))
      return {
        label: n.label,
        connectedness: conf.length ? 'confirmed' : sim.length ? 'similar-only' : 'isolated',
        confirmed_with: conf.map(labelOf),
        similar_with: sim.map(labelOf),
      }
    })
    connection = {
      state: connectionState(cluster, data.edges),
      nodes,
      links: data.edges.slice(0, 8).map(e => `${labelOf(e.a)} ↔ ${labelOf(e.b)} — ${edgeReason(e)}`),
      countries: (data.distributions?.countries ?? []).slice(0, 10).map(c => `${c.cc} ${c.n}`),
      languages: (data.distributions?.languages ?? []).slice(0, 8).map(l => `${l.lang} ${l.n}`),
      press: data.distributions?.roles.press ?? 0,
      public: data.distributions?.roles.public ?? 0,
      bridges: (data.neighbors ?? [])
        .filter(nb => nb.links.length > 1)
        .slice(0, 6)
        .map(nb => nb.label),
    }
  }

  try {
    const res = await fetch('/api/v2/dossier/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ title: dossier.title, pins, connection, gaps: dossier.gaps }),
    })
    if (!res.ok) return null
    return await res.json() as DossierSynthesis
  } catch {
    return null
  }
}

/** Markdown for the synthesis block (goes at the TOP of the export, above the
 *  templated summary — so the exported report leads with the finding). */
export function synthesisMarkdown(s: DossierSynthesis): string[] {
  if (!s.headline && !s.synthesis) return []
  const lines: string[] = ['## Synthesis', '']
  if (s.headline) lines.push(`**${s.headline}**`, '')
  if (s.synthesis) lines.push(s.synthesis, '')
  if (s.gap) lines.push(`*Key gap: ${s.gap}*`, '')
  lines.push(`*Synthesis measured at generation time${s.provider ? ` (${s.provider})` : ''} — not frozen; grounded in the pinned evidence + measured connections.*`, '')
  return lines
}
