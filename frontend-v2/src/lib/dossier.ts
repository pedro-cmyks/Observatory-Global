// Phase 3 — Dossier/report view, generated from the FROZEN Workbench state
// (spec 2026-06-09 §7 / Dossier View; unblocked by #227 pin snapshots).
//
// The report reads ONLY from what the analyst pinned — each pin's frozen
// snapshot, note, and the investigation trail — never a live re-fetch. It is
// traceable back to the pinned route, and it says what it cannot answer (gaps).
import type { Investigation, WorkbenchPin, TrailStep } from './workbench'
import type { DossierEnrichment } from './dossierEnrichment'

export interface DossierModel {
  title: string
  queries: string[]
  generatedAt: string
  pinCount: number
  summary: string
  timeline: TrailStep[]
  pins: WorkbenchPin[]
  gaps: string[]
  /** W3: pins grouped by R3 category (uncategorized pins under null). */
  categoryGroups: Array<{ category: string | null; anchorIds: string[] }>
  /** W3: measured-at-generation sections (who-says-what + voice). Absent when
   *  no enrichment could be fetched — the frozen core never depends on it. */
  enrichment?: DossierEnrichment
}

function uniq<T>(xs: T[]): T[] {
  return [...new Set(xs)]
}

/** Pure: build the dossier model from the frozen investigation. `now` is passed
 *  in so the function stays deterministic/testable. */
export function buildDossier(
  inv: Investigation, now: string, enrichment?: DossierEnrichment,
): DossierModel {
  const pins = inv.pins
  const types = uniq(pins.map(p => p.anchorType).filter(Boolean))
  const queries = uniq(pins.map(p => p.queryText).filter((q): q is string => !!q))

  // W3: R3 category grouping — categorized pins first, uncategorized last.
  const byCategory = new Map<string | null, string[]>()
  for (const p of pins) {
    const key = p.category ?? null
    byCategory.set(key, [...(byCategory.get(key) ?? []), p.anchorId])
  }
  const categoryGroups = [...byCategory.entries()]
    .map(([category, anchorIds]) => ({ category, anchorIds }))
    .sort((a, b) => (a.category === null ? 1 : 0) - (b.category === null ? 1 : 0))

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
  if (enrichment && Object.keys(enrichment.whoSaysWhat).length === 0 && Object.keys(enrichment.voice).length === 0) {
    gaps.push('Who-says-what and voice sections could not be measured (endpoints unavailable at generation time).')
  }

  return {
    title: inv.title,
    queries,
    generatedAt: now,
    pinCount: pins.length,
    summary,
    timeline: inv.trail,
    pins,
    gaps,
    categoryGroups,
    enrichment,
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
  // W3: the wedge sections — who says what (press vs public) + voice.
  // Measured at GENERATION time from typed topic_members roles and the
  // ownership voice-mix; never mixed with the frozen pin evidence.
  const wsw = d.enrichment?.whoSaysWhat ?? {}
  if (Object.keys(wsw).length > 0) {
    lines.push('## Who says what (press vs public)')
    lines.push(`*Measured at generation time (${fmt(d.enrichment!.measuredAt)}), not frozen — typed member roles: press = verified evidence, public = forum/social discussion (never verified).*`)
    for (const p of d.pins) {
      const e = wsw[p.anchorId]
      if (!e) continue
      lines.push(`- **${p.label}** — ${e.relationship}: press ${e.evidenceCount} · public ${e.discussionCount}${e.moodCount ? ` · mood ${e.moodCount}` : ''} (${e.rationale})`)
      if (e.sourceTiers) {
        const tiers = Object.entries(e.sourceTiers).sort((a, b) => b[1] - a[1])
          .map(([t, n]) => `${t} ${n}`).join(' · ')
        lines.push(`  - receipts by credibility tier: ${tiers}`)
      }
    }
    lines.push('')
  }
  const voice = d.enrichment?.voice ?? {}
  if (Object.keys(voice).length > 0) {
    lines.push('## Voice (who covers, not just who is covered)')
    lines.push('*Self-voice = outlets OWNED in the country (ownership, not language). Measured at generation time over 168h.*')
    for (const [cc, v] of Object.entries(voice)) {
      const bits: string[] = []
      if (v.selfVoiceRatio !== null) bits.push(`self-voice ${(v.selfVoiceRatio * 100).toFixed(0)}%`)
      if (v.dominantOutsider) bits.push(`dominant outsider ${v.dominantOutsider}`)
      if (v.stateMediaPct !== null) bits.push(`state media ${v.stateMediaPct.toFixed(0)}%`)
      if (v.topForeignOrigins.length) bits.push(`top foreign: ${v.topForeignOrigins.join(', ')}`)
      lines.push(`- **${cc}** — ${bits.join(' · ')}`)
    }
    lines.push('')
  }
  const categorized = d.categoryGroups.filter(g => g.category !== null)
  if (categorized.length > 0) {
    lines.push('## Categories covered (R3 lens)')
    for (const g of d.categoryGroups) {
      const labels = g.anchorIds
        .map(id => d.pins.find(p => p.anchorId === id)?.label)
        .filter(Boolean)
      lines.push(`- **${g.category ?? 'uncategorized'}**: ${labels.join('; ')}`)
    }
    lines.push('')
  }
  const covGaps = d.enrichment?.coverageGaps ?? []
  if (covGaps.length > 0) {
    lines.push('## What is missing (attention without verified coverage)')
    lines.push('*Categories with attention but zero gate-verified coverage in the last 24h. Measured at generation time, global.*')
    for (const g of covGaps) {
      lines.push(`- **${g.label}** — ${g.rawSignals} raw signals · ${g.status === 'gate_pending' ? 'awaiting gate' : 'none verified'}`)
    }
    lines.push('')
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
