// Attention-eclipse / under-the-radar — pure client helpers.
//
// Feeds the L1 "MEANWHILE, OFF THE FRONT PAGE" strip from GET /api/v2/attention/eclipse.
// The strip renders ONLY when the window is eclipsed (one event dominates coverage)
// AND something consequential is under the radar — otherwise it stays invisible (a
// diffuse day surfaces nothing; a 404/failure degrades silently). Coverage-volume
// concentration is a PROXY for attention, not audience eyeballs; the strip ranks
// candidates, it does not certify them.

export interface EclipseItem {
  topic_id: string
  label: string
  attention: number
  attention_share: number
  consequence: number
  language_breadth: number
  country_breadth: number
  velocity: number
  lane: string
  reason_codes: string[]
}

export interface EclipseData {
  eclipse: boolean
  dominant: { topic_id?: string; label?: string; attention?: number; share?: number; lane?: string }
  window: { top1_share?: number; hhi?: number; [k: string]: unknown }
  selected: EclipseItem[]
}

export function shouldShowEclipse(data: EclipseData | null | undefined): boolean {
  return Boolean(data && data.eclipse && Array.isArray(data.selected) && data.selected.length > 0)
}

// decodeEntities was promoted to its own module (src/lib/decodeEntities.ts)
// so every surface shares ONE decoder; re-exported here for existing imports.
export { decodeEntities } from './decodeEntities'

export function eclipseDominantLine(data: EclipseData): string {
  const label = data.dominant?.label ?? 'one story'
  const pct = Math.round((data.dominant?.share ?? data.window?.top1_share ?? 0) * 100)
  return `While “${label}” holds ${pct}% of today’s coverage, these consequential stories are running quiet:`
}

export interface FormattedEclipseItem {
  breadthLabel: string
  sharePct: string
  rising: boolean
}

// A workbench pin built from an eclipsed story — the L3 ramp. Structurally a
// WorkbenchPin (minus pinnedAt, stamped by addPin); typed loosely here so the
// pure lib stays decoupled from the workbench store. Reuses the same theme /
// l2_params surface every other console pin uses (one pool, one ramp), and freezes
// an honest snapshot of WHY the story was under the radar.
export interface EclipsePin {
  anchorId: string
  anchorType: string
  label: string
  open: { surface: string; params: { urlParams: string } }
  snapshot: {
    capturedAt: string
    summary: string
    metrics: Record<string, number>
  }
}

export function buildEclipsePin(item: EclipseItem, capturedAt: string): EclipsePin {
  const { sharePct, breadthLabel } = formatEclipseItem(item)
  return {
    anchorId: `eclipse-${item.topic_id}`,
    anchorType: 'theme',
    label: item.label,
    open: {
      surface: 'l2_params',
      params: { urlParams: `?theme=${encodeURIComponent(item.topic_id)}&entry=eclipse` },
    },
    snapshot: {
      capturedAt,
      summary: `${item.label} · under the radar · ${sharePct} of coverage · ${breadthLabel}`,
      metrics: {
        attention_share: item.attention_share,
        consequence: item.consequence,
        language_breadth: item.language_breadth,
        country_breadth: item.country_breadth,
        velocity: item.velocity,
      },
    },
  }
}

export function formatEclipseItem(item: EclipseItem): FormattedEclipseItem {
  const langs = Math.max(0, item.language_breadth)
  const countries = Math.max(0, item.country_breadth)
  const share = Math.max(0, item.attention_share) * 100
  // Keep a real-but-tiny share legible: one decimal, never rounds to 0.0 for a
  // present story.
  const sharePct = share > 0 && share < 0.1 ? '<0.1%' : `${share.toFixed(1)}%`
  return {
    breadthLabel: `${langs} ${langs === 1 ? 'language' : 'languages'} · ${countries} ${countries === 1 ? 'country' : 'countries'}`,
    sharePct,
    rising: (item.velocity ?? 0) > 0.05,
  }
}
