// Dossier synthesis (contract dossier-synthesis-v1) — the standalone-brief layer.
//
// The report must stand alone (the "Frank test"): a stranger reading only it must
// understand the story. The templated one-liner can't. This asks the backend for
// ONE grounded LLM pass over the FROZEN pin evidence + the MEASURED connection
// verdict → {headline, synthesis, gap}. Measured at generation time, labeled as
// such; degrades to null so the frozen report always stands on its own.
import type { DossierModel } from './dossier'
import {
  connectionState, edgeReason, edgeStrength, coverageLensNote, buildFrozenCrossRefs,
  type ConnectionsData, type ClusterResult,
} from './dossierConnections'

export interface DossierCitation {
  n: number
  headline: string
  source: string | null
  date: string | null
  url: string | null
  pin: string
}

export interface DossierSynthesis {
  contract: string
  headline: string | null
  // P0.6a article shape — publishable mini-article. lede/body carry inline [n]
  // receipt markers; citations is the server-resolved numbered receipts table
  // (authoritative — built from the request, never echoed by the model).
  lede: string | null
  body: string[] | null
  unknowns: string[] | null
  citations: DossierCitation[] | null
  // Legacy shape (fallback renderer when the model answers in the old form).
  synthesis: string | null
  gap: string | null
  provider: string | null
  error: string | null
}

/** True when the response carries the publishable article shape. */
export function isArticle(s: DossierSynthesis): boolean {
  return Boolean(s.lede || (s.body && s.body.length))
}

/** Split article text on its [n] receipt markers → renderable parts. Pure. */
export type CitationPart = { kind: 'text'; text: string } | { kind: 'cite'; n: number }
export function splitCitations(text: string): CitationPart[] {
  const parts: CitationPart[] = []
  const re = /\[(\d{1,3})\]/g
  let last = 0
  for (let m = re.exec(text); m; m = re.exec(text)) {
    if (m.index > last) parts.push({ kind: 'text', text: text.slice(last, m.index) })
    parts.push({ kind: 'cite', n: Number(m[1]) })
    last = m.index + m[0].length
  }
  if (last < text.length) parts.push({ kind: 'text', text: text.slice(last) })
  return parts
}

/** Build the complete grounded input from frozen pins + measured connections.
 * No semantic top-N is applied: every frozen receipt remains addressable. The
 * backend may still fail honestly if a provider cannot accept the context. */
export function buildSynthesisRequest(
  dossier: DossierModel,
  conn: { data: ConnectionsData; cluster: ClusterResult } | null,
): Record<string, unknown> & { pins: Array<Record<string, unknown>> } {
  const pins = dossier.pins.map(p => ({
    label: p.label,
    type: p.anchorType,
    // Fold source + signal DATE into the headline so the LLM can attribute AND
    // date contested outcomes ("reported by <outlet>, 2026-07-08") instead of
    // asserting them as undated fact. (Legacy field — older backends read this.)
    evidence: (p.snapshot?.evidence ?? [])
      .map(e => {
        const attribution = e.source
          ? ` — ${e.source}${e.date ? `, ${e.date}` : ''}`
          : (e.date ? ` — ${e.date}` : '')
        return `${e.headline}${attribution}`
      }),
    // P0.6a structured evidence — the server numbers these [1..N] into the
    // article's authoritative receipts table (with URLs for clickable receipts).
    evidence_items: (p.snapshot?.evidence ?? []).map(e => ({
      headline: e.headline,
      source: e.source ?? null,
      date: e.date ?? null,
      url: e.url ?? null,
    })),
    note: p.note ?? null,
  }))
  let connection: Record<string, unknown> | null = null
  if (conn && conn.data.nodes.length >= 2) {
    const { data, cluster } = conn
    const labelOf = (id: string) => data.nodes.find(n => n.id === id)?.label ?? id
    // Per-pin connectedness: only a distinctive shared actor is CONFIRMED.
    // Shared coverage country is CONTEXT; semantic proximity is SIMILAR-ONLY.
    // the fix for the over-claim failure — the whole set can read 'grounded' off a
    // single confirmed edge while a third pin hangs on similarity-only edges.
    const confirmedWith = new Map<string, Set<string>>()
    const textWith = new Map<string, Set<string>>()
    const contextWith = new Map<string, Set<string>>()
    const similarWith = new Map<string, Set<string>>()
    const textTerms = new Map<string, string[]>()
    for (const n of data.nodes) {
      confirmedWith.set(n.id, new Set()); textWith.set(n.id, new Set())
      contextWith.set(n.id, new Set()); similarWith.set(n.id, new Set())
      textTerms.set(n.id, [])
    }
    for (const e of data.edges) {
      const s = edgeStrength(e)
      const bucket = s === 'strong' ? confirmedWith
        : s === 'text' ? textWith : s === 'context' ? contextWith : similarWith
      bucket.get(e.a)?.add(e.b)
      bucket.get(e.b)?.add(e.a)
      // glass box: hand the model the EXACT measured mention terms per pin.
      for (const term of e.text_mentions ?? []) {
        textTerms.get(e.a)?.push(`evidence text mentions “${term}” (link to ${labelOf(e.b)})`)
        textTerms.get(e.b)?.push(`evidence text mentions “${term}” (link to ${labelOf(e.a)})`)
      }
    }
    // Frozen-evidence cross-refs (client mirror): an "isolated" pin whose own
    // frozen headline references another pin must carry that fact to the model.
    const crossRefs = buildFrozenCrossRefs(dossier.pins, data)
    const crossRefByLabel = new Map<string, string[]>()
    for (const x of crossRefs) {
      crossRefByLabel.set(x.pinLabel, [
        ...(crossRefByLabel.get(x.pinLabel) ?? []),
        `frozen evidence text references “${x.term}” (${x.otherLabel}) — entity extraction found no overlap; verify`,
      ])
    }
    const nodes = data.nodes.map(n => {
      const conf = [...(confirmedWith.get(n.id) ?? [])]
      const confSet = confirmedWith.get(n.id) ?? new Set<string>()
      const text = [...(textWith.get(n.id) ?? [])].filter(id => !confSet.has(id))
      const context = [...(contextWith.get(n.id) ?? [])]
        .filter(id => !confSet.has(id) && !textWith.get(n.id)?.has(id))
      const sim = [...(similarWith.get(n.id) ?? [])]
        .filter(id => !confSet.has(id) && !textWith.get(n.id)?.has(id) && !contextWith.get(n.id)?.has(id))
      const mentions = [
        ...(textTerms.get(n.id) ?? []),
        ...(crossRefByLabel.get(n.label) ?? []),
      ]
      return {
        label: n.label,
        connectedness: conf.length ? 'confirmed'
          : (text.length || mentions.length) ? 'text-linked'
          : context.length ? 'coverage-context'
            : sim.length ? 'similar-only' : 'isolated',
        confirmed_with: conf.map(labelOf),
        contextual_with: context.map(labelOf),
        similar_with: sim.map(labelOf),
        text_mentions: mentions,
      }
    })
    connection = {
      state: connectionState(cluster, data.edges),
      nodes,
      links: data.edges.map(e => `${labelOf(e.a)} ↔ ${labelOf(e.b)} — ${edgeReason(e)}`),
      countries: (data.distributions?.countries ?? []).map(c => `${c.cc} ${c.n}`),
      languages: (data.distributions?.languages ?? []).map(l => `${l.lang} ${l.n}`),
      press: data.distributions?.roles.press ?? 0,
      public: data.distributions?.roles.public ?? 0,
      bridges: (data.neighbors ?? [])
        .filter(nb => nb.links.length > 1)
        .map(nb => nb.label),
      lens_note: coverageLensNote(data.distributions?.languages ?? []),
    }
  }

  return { title: dossier.title, pins, connection, gaps: dossier.gaps }
}

/** Build the request from the frozen dossier + the measured connection data,
 * then POST for the synthesis. Returns null on any failure (frozen core stands). */
export async function synthesizeDossier(
  dossier: DossierModel,
  conn: { data: ConnectionsData; cluster: ClusterResult } | null,
): Promise<DossierSynthesis | null> {
  const body = buildSynthesisRequest(dossier, conn)
  if (body.pins.length === 0) return null
  try {
    const res = await fetch('/api/v2/dossier/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) return null
    return await res.json() as DossierSynthesis
  } catch {
    return null
  }
}

/** Markdown for the synthesis block (goes at the TOP of the export, above the
 *  templated summary — so the exported report leads with the finding).
 *  Article shape → mini-article with numbered receipts; legacy shape → old block. */
export function synthesisMarkdown(s: DossierSynthesis): string[] {
  if (!s.headline && !s.synthesis && !isArticle(s)) return []
  const lines: string[] = ['## Synthesis', '']
  if (s.headline) lines.push(`**${s.headline}**`, '')
  if (isArticle(s)) {
    if (s.lede) lines.push(`*${s.lede}*`, '')
    for (const para of s.body ?? []) lines.push(para, '')
    if (s.unknowns && s.unknowns.length) {
      lines.push('**What we don\'t know**', '')
      for (const u of s.unknowns) lines.push(`- ${u}`)
      lines.push('')
    }
    if (s.citations && s.citations.length) {
      lines.push('**Receipts**', '')
      for (const c of s.citations) {
        const head = c.url ? `[${c.headline}](${c.url})` : c.headline
        const attribution = [c.source, c.date].filter(Boolean).join(', ')
        lines.push(`${c.n}. ${head}${attribution ? ` — ${attribution}` : ''} *(${c.pin})*`)
      }
      lines.push('')
    }
  } else {
    if (s.synthesis) lines.push(s.synthesis, '')
    if (s.gap) lines.push(`*Key gap: ${s.gap}*`, '')
  }
  lines.push(`*Synthesis measured at generation time${s.provider ? ` (${s.provider})` : ''} — not frozen; grounded in the pinned evidence + measured connections.*`, '')
  return lines
}
