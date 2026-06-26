// Phase 3 — Dossier/report view, generated from the FROZEN Workbench state
// (spec 2026-06-09 §7 / Dossier View; unblocked by #227 pin snapshots).
//
// The report reads ONLY from what the analyst pinned — each pin's frozen
// snapshot, note, and the investigation trail — never a live re-fetch. It is
// traceable back to the pinned route, and it says what it cannot answer (gaps).
import type { Investigation, WorkbenchPin, TrailStep } from './workbench'

export interface DossierModel {
  title: string
  queries: string[]
  generatedAt: string
  pinCount: number
  summary: string
  timeline: TrailStep[]
  pins: WorkbenchPin[]
  gaps: string[]
}

function uniq<T>(xs: T[]): T[] {
  return [...new Set(xs)]
}

/** Pure: build the dossier model from the frozen investigation. `now` is passed
 *  in so the function stays deterministic/testable. */
export function buildDossier(inv: Investigation, now: string): DossierModel {
  const pins = inv.pins
  const types = uniq(pins.map(p => p.anchorType).filter(Boolean))
  const queries = uniq(pins.map(p => p.queryText).filter((q): q is string => !!q))

  const summary = pins.length === 0
    ? 'No pins yet — open a research plan and pin useful anchors to build a report.'
    : `${pins.length} pinned ${pins.length === 1 ? 'item' : 'items'}`
      + (types.length ? ` across ${types.join(', ')}` : '')
      + `. Leading: ${pins.slice(0, 3).map(p => p.label).join('; ')}.`

  // Gaps/uncertainty — derived honestly from the frozen snapshots, never hidden.
  const gaps: string[] = []
  const noEvidence = pins.filter(p => !p.snapshot?.evidence || p.snapshot.evidence.length === 0)
  if (noEvidence.length > 0) {
    gaps.push(`${noEvidence.length} of ${pins.length} pins were captured without frozen evidence (metadata only) — re-open them to inspect the live source.`)
  }
  const keywordOnly = pins.filter(p =>
    (p.snapshot?.evidence ?? []).some(e => /^keyword\b/i.test(e.headline)))
  if (keywordOnly.length > 0) {
    gaps.push(`${keywordOnly.length} connection(s) are keyword-only (lower confidence than a semantic or member match) — the item was not in the embedded corpus when pinned.`)
  }
  const taxonomy = pins.filter(p => p.matchBasis === 'topic_description')
  if (taxonomy.length > 0) {
    gaps.push(`${taxonomy.length} anchor(s) matched the taxonomy description, not found evidence — treat as context, not proof.`)
  }
  gaps.push('This report is frozen at pin time; live counts, gate scores, and threads may have drifted since.')

  return {
    title: inv.title,
    queries,
    generatedAt: now,
    pinCount: pins.length,
    summary,
    timeline: inv.trail,
    pins,
    gaps,
  }
}

function fmt(iso: string): string {
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

/** Render the dossier as portable Markdown (the spec's report export). */
export function dossierToMarkdown(d: DossierModel): string {
  const lines: string[] = []
  lines.push(`# ${d.title}`)
  lines.push('')
  lines.push(`*Atlas investigation report — generated ${fmt(d.generatedAt)} from ${d.pinCount} pinned item(s). Frozen at pin time.*`)
  if (d.queries.length) lines.push(`\n**Queries:** ${d.queries.join(' · ')}`)
  lines.push('')
  lines.push('## Executive summary')
  lines.push(d.summary)
  lines.push('')
  lines.push('## Evidence (from pins)')
  if (d.pins.length === 0) {
    lines.push('_No pins._')
  } else {
    for (const p of d.pins) {
      lines.push(`### ${p.label}  \`${p.anchorType}\``)
      if (p.snapshot?.summary) lines.push(p.snapshot.summary)
      for (const e of p.snapshot?.evidence ?? []) {
        lines.push(`- ${e.url ? `[${e.headline}](${e.url})` : e.headline}${e.source ? ` — ${e.source}` : ''}`)
      }
      if (p.note) lines.push(`> **Note:** ${p.note}`)
      lines.push(`*pinned ${fmt(p.pinnedAt)}*`)
      lines.push('')
    }
  }
  lines.push('## Timeline')
  for (const s of d.timeline) {
    lines.push(`- ${fmt(s.at)} — **${s.action}** ${s.detail}`)
  }
  lines.push('')
  lines.push('## Gaps & uncertainty')
  for (const g of d.gaps) lines.push(`- ${g}`)
  lines.push('')
  return lines.join('\n')
}
