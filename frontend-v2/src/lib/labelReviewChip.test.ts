import { describe, expect, it } from 'vitest'
import type { ReactElement } from 'react'
import { labelReviewReason, labelReviewTip, LABEL_REVIEW_FLOOR, LabelReviewChip } from './labelReviewChip'

const FLOOR = 0.7

describe('labelReviewReason', () => {
  it('flags a court-failed label regardless of confidence', () => {
    expect(labelReviewReason({
      labelStatus: 'failed',
      avgConfidence: 0.98,
      confidenceMeasured: true,
      floor: FLOOR,
    })).toBe('label-failed')
  })

  it('flags a court-partial label regardless of confidence', () => {
    expect(labelReviewReason({
      labelStatus: 'partial',
      avgConfidence: 0.99,
      confidenceMeasured: true,
      floor: FLOOR,
    })).toBe('label-partial')
  })

  it('never chips a court-entailed label even when confidence is low', () => {
    // The court validated the label against its receipts; its verdict is
    // authoritative over the raw assignment-confidence floor.
    expect(labelReviewReason({
      labelStatus: 'entailed',
      avgConfidence: 0.10,
      confidenceMeasured: true,
      floor: FLOOR,
    })).toBeNull()
  })

  it('falls back to the confidence floor when the court has not run (null status)', () => {
    // The LIVE motivating case: prod lead "17-Year-Old British Teen Fall",
    // avg_confidence 0.214, label_status still NULL (nightly not yet run).
    expect(labelReviewReason({
      labelStatus: null,
      avgConfidence: 0.214,
      confidenceMeasured: true,
      floor: FLOOR,
    })).toBe('low-confidence')
  })

  it('does not chip an unchecked thread that sits above the floor', () => {
    expect(labelReviewReason({
      labelStatus: null,
      avgConfidence: 0.92,
      confidenceMeasured: true,
      floor: FLOOR,
    })).toBeNull()
  })

  it('does not chip a thread whose confidence is unmeasured (atlas path, avg=null)', () => {
    expect(labelReviewReason({
      labelStatus: null,
      avgConfidence: null,
      confidenceMeasured: false,
      floor: FLOOR,
    })).toBeNull()
  })

  it('treats an explicitly-unmeasured thread as un-chippable even with a stray number', () => {
    expect(labelReviewReason({
      labelStatus: undefined,
      avgConfidence: 0,
      confidenceMeasured: false,
      floor: FLOOR,
    })).toBeNull()
  })

  it('treats a missing confidenceMeasured flag as measured when a finite number is present', () => {
    expect(labelReviewReason({
      labelStatus: null,
      avgConfidence: 0.4,
      floor: FLOOR,
    })).toBe('low-confidence')
  })

  it('does not fire exactly at the floor (floor is the passing bar)', () => {
    expect(labelReviewReason({
      labelStatus: null,
      avgConfidence: FLOOR,
      confidenceMeasured: true,
      floor: FLOOR,
    })).toBeNull()
  })

  it('exports a sane default floor', () => {
    expect(LABEL_REVIEW_FLOOR).toBeGreaterThan(0.5)
    expect(LABEL_REVIEW_FLOOR).toBeLessThan(1)
  })
})

// 2026-07-29 GB4 fix 1: a court-withheld row (quote-gate / absence-check /
// rule-4 failure, umbrella lane) must render something — the confidence
// floor structurally can never fire for an umbrella (avg_confidence 0.95+).
describe('labelReviewReason courtWithheld (GB4 fix 1)', () => {
  it('derives awaiting-verification for a withheld row regardless of high confidence', () => {
    // the dt-8070/dt-8084 case: avg_confidence ~0.98, label_status null,
    // but the court DID try and could not ground a verdict.
    expect(labelReviewReason({
      labelStatus: null,
      avgConfidence: 0.984,
      confidenceMeasured: true,
      courtWithheld: true,
      floor: FLOOR,
    })).toBe('awaiting-verification')
  })

  it('is a no-op when courtWithheld is absent — existing callers unaffected', () => {
    expect(labelReviewReason({
      labelStatus: null,
      avgConfidence: 0.984,
      confidenceMeasured: true,
      floor: FLOOR,
    })).toBeNull()
  })

  it('court verdicts still take precedence over courtWithheld', () => {
    // withheld is only meaningful when there is NO verdict; a real verdict
    // (even courtWithheld=true stale on the same payload) must win.
    expect(labelReviewReason({
      labelStatus: 'failed',
      avgConfidence: 0.98,
      courtWithheld: true,
      floor: FLOOR,
    })).toBe('label-failed')
  })

  it('courtWithheld=false behaves identically to omitted', () => {
    expect(labelReviewReason({
      labelStatus: null,
      avgConfidence: 0.984,
      confidenceMeasured: true,
      courtWithheld: false,
      floor: FLOOR,
    })).toBeNull()
  })
})

describe('labelReviewTip', () => {
  it('SUPPRESSES the internal token-triple placeholder (#261 — never surface it)', () => {
    // build_neutral_label emits "<geo>: <subject> — from N receipts" as an
    // internal placeholder before the DeepSeek relabel; it must never reach the user.
    const tip = labelReviewTip('label-failed', 'Iran: Hormuz blockade & US strikes — from 6 receipts')
    expect(tip).toContain('did not match its receipts')
    expect(tip).not.toContain('receipts suggest')
  })

  it('surfaces a REAL relabel (no receipts-count tail) as advisory', () => {
    const tip = labelReviewTip('label-failed', 'Spain tops Argentina in dominant World Cup final')
    expect(tip).toContain('receipts suggest: Spain tops Argentina in dominant World Cup final')
  })

  it('explains a court partial match', () => {
    expect(labelReviewTip('label-partial', null)).toContain('only partially matches its receipts')
  })

  it('explains a below-floor low-confidence demotion', () => {
    expect(labelReviewTip('low-confidence', null).toLowerCase()).toContain('low assignment confidence')
  })

  it('omits the advisory clause when there is no proposed label', () => {
    expect(labelReviewTip('label-failed', null).toLowerCase()).not.toContain('receipts suggest')
  })
})

// LabelReviewChip uses no hooks, so it can be invoked directly and its returned
// element inspected — no DOM renderer required.
describe('LabelReviewChip reason override (unassembled-tray path)', () => {
  it('forces the chip to render even when the row carries only a band (no measured avg_confidence)', () => {
    // A tray row admitted by the band-aware leadBlockReason would derive NO
    // reason (confidence unmeasured) — the explicit override guarantees the
    // "LABEL UNDER REVIEW" chip still renders, so no unassembled card is chipless.
    const el = LabelReviewChip({ reason: 'low-confidence', avgConfidence: null }) as ReactElement
    expect(el).not.toBeNull()
    expect(el.props['data-reason']).toBe('low-confidence')
    expect(el.props.children).toBe('LABEL UNDER REVIEW')
  })

  it('renders label-failed via the override with the same single class', () => {
    const el = LabelReviewChip({ reason: 'label-failed' }) as ReactElement
    expect(el.props.className).toContain('label-review-chip')
    expect(el.props['data-reason']).toBe('label-failed')
  })

  it('reason=null hides the chip regardless of confidence', () => {
    expect(LabelReviewChip({ reason: null, avgConfidence: 0.1, confidenceMeasured: true })).toBeNull()
  })

  it('without an override it still derives from the court verdict', () => {
    const el = LabelReviewChip({ labelStatus: 'failed' }) as ReactElement
    expect(el.props['data-reason']).toBe('label-failed')
  })
})

// N15 (council R2): dense surfaces (universe hover, search rows, CountryBrief
// chips, dossier pin labels) render the SAME component in a compact dot
// variant — one source of truth for when/why, two densities of how.
describe('LabelReviewChip dot variant (dense surfaces)', () => {
  it('renders a dot with the same reason + tip semantics', () => {
    const el = LabelReviewChip({ labelStatus: 'failed', variant: 'dot' }) as ReactElement
    expect(el).not.toBeNull()
    expect(el.props.className).toContain('label-review-chip--dot')
    expect(el.props['data-reason']).toBe('label-failed')
    expect(el.props['data-tip']).toContain('did not match its receipts')
    // Accessible name replaces the visible copy in the dot form.
    expect(el.props['aria-label']).toBe('Label under review')
  })

  it('partial verdict also fires with only labelStatus on the row (status-only payloads)', () => {
    const el = LabelReviewChip({ labelStatus: 'partial', variant: 'dot' }) as ReactElement
    expect(el.props['data-reason']).toBe('label-partial')
  })

  it('entailed / unchecked status-only payloads render nothing', () => {
    expect(LabelReviewChip({ labelStatus: 'entailed', variant: 'dot' })).toBeNull()
    expect(LabelReviewChip({ labelStatus: null, variant: 'dot' })).toBeNull()
  })

  it('default variant keeps the visible chip copy', () => {
    const el = LabelReviewChip({ labelStatus: 'failed' }) as ReactElement
    expect(el.props.children).toBe('LABEL UNDER REVIEW')
    expect(el.props.className).not.toContain('label-review-chip--dot')
  })
})
