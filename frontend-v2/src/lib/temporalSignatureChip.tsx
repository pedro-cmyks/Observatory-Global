// TEMPORAL SIGNATURE chip (Lane C, mig 085) — the lineage speaks for every
// thread, not just the giants with a full biography.
//
// The nightly classifier (backend/scripts/temporal_signature.py) types each
// active topic's shape in TIME from the narrative-lineage census:
//   new          no ancestor archive units matched since the archive begins
//                (May) — only asserted when the census actually attempted the
//                topic (member coverage >= floor)
//   continuous   one unbroken weekly chain — the DEFAULT, deliberately NOT a
//                badge (the absence of a chip is the common case)
//   resurrected  one >=2-week quiet gap, then returned
//   recurrent    went quiet and returned twice or more (>=3 active eras)
//
// Honesty rules: signature NULL (below the census member floor, classifier
// not yet run, or umbrella tie) -> NO chip — absence over guess. The chip is
// purely additive labeling; it never hides a thread, never changes ranking.
import React from 'react'
import './temporalSignatureChip.css'

export interface TemporalSignatureMeta {
  eras?: number | null
  gap_weeks?: number | null
  first_seen_week?: string | null
  returned_week?: string | null
  inherited?: boolean
}

export interface TemporalChip {
  /** Short chip text: NEW | RECURRENT | RESURRECTED. */
  label: string
  /** Plain-language explanation for the data-tip. */
  tip: string
}

function ordinal(n: number): string {
  const rem10 = n % 10
  const rem100 = n % 100
  if (rem10 === 1 && rem100 !== 11) return `${n}st`
  if (rem10 === 2 && rem100 !== 12) return `${n}nd`
  if (rem10 === 3 && rem100 !== 13) return `${n}rd`
  return `${n}th`
}

function fmtWeek(iso: string): string {
  const d = new Date(iso + 'T00:00:00Z')
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

/**
 * Resolve a served temporal_signature (+ meta) to chip copy, or null when no
 * chip should render (continuous = default; NULL = below the member floor or
 * unclassified — absence over guess). Pure; TDD'd.
 */
export function resolveTemporalChip(
  signature: string | null | undefined,
  meta?: TemporalSignatureMeta | null,
): TemporalChip | null {
  switch (signature) {
    case 'new':
      return {
        label: 'NEW',
        tip: 'No prior coverage matched in the archive since May — first appearance of this narrative.',
      }
    case 'recurrent': {
      const eras = typeof meta?.eras === 'number' && meta.eras > 0 ? meta.eras : null
      const returned = meta?.returned_week ? `, returned ${fmtWeek(meta.returned_week)}` : ''
      return {
        label: 'RECURRENT',
        tip: eras
          ? `${ordinal(eras)} active era — this story has gone quiet and come back before${returned}.`
          : `This story has gone quiet and come back more than once${returned}.`,
      }
    }
    case 'resurrected': {
      const gap = typeof meta?.gap_weeks === 'number' && meta.gap_weeks > 0 ? meta.gap_weeks : null
      const returned = meta?.returned_week ? `, returned ${fmtWeek(meta.returned_week)}` : ''
      return {
        label: 'RESURRECTED',
        tip: gap
          ? `Quiet ${gap} week${gap === 1 ? '' : 's'}${returned} — this narrative went dormant and is active again.`
          : `This narrative went dormant and is active again${returned}.`,
      }
    }
    default:
      // 'continuous' (default state, not a badge), null/undefined (below the
      // census member floor or unclassified), or an unknown future value.
      return null
  }
}

export interface TemporalSignatureChipProps {
  signature?: string | null
  meta?: TemporalSignatureMeta | null
  /** Extra class for surface-specific spacing. */
  className?: string
}

/** Renders the signature chip, or nothing (continuous / unclassified). */
export function TemporalSignatureChip(
  props: TemporalSignatureChipProps,
): React.ReactElement | null {
  const chip = resolveTemporalChip(props.signature, props.meta)
  if (!chip) return null
  return (
    <span
      className={`temporal-signature-chip${props.className ? ` ${props.className}` : ''}`}
      data-signature={props.signature ?? undefined}
      data-tip={chip.tip}
    >
      {chip.label}
    </span>
  )
}
