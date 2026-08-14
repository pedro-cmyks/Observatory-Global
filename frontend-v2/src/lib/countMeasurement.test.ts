import { describe, it, expect } from 'vitest'
import { describeCumulativeCount, describeSourceCount } from './countMeasurement'

/**
 * Pedro's screen, 2026-08-14 — `/app?theme=dynamic-topic-242&lens=story`:
 *
 *     "Global · 18 signals · last 7d · 323 lifetime"
 *
 * Three numbers, three false labels. Backend measurement (see
 * backend/tests/test_theme_detail_count_measurement.py):
 *   * 323 is a SUM ACROSS 17 CLUSTERING PASSES that double-counts, not a
 *     lifetime count of distinct signals
 *   * 18 is ONE pass (the latest snapshot, 2026-08-13 03:27), not a rolling 7d
 *   * the "20 Sources" tile printed the length of a 20-item preview slice
 *     while the same page rendered 37 receipts from 36 distinct outlets
 *
 * These helpers own the wording so the header, the tiles and the tips cannot
 * drift apart again.
 */

describe('describeCumulativeCount', () => {
  it('never says the word "lifetime" for a cumulative sum', () => {
    const d = describeCumulativeCount({ total: 323, snapshotCount: 17 })
    expect(d.qualifier.toLowerCase()).not.toContain('lifetime')
    expect(d.tip.toLowerCase()).not.toContain('lifetime')
  })

  it('names the passes so 323 is interpretable', () => {
    const d = describeCumulativeCount({ total: 323, snapshotCount: 17 })
    expect(d.qualifier).toBe('across 17 passes')
  })

  it('warns in the tip that a signal recurs once per pass', () => {
    const d = describeCumulativeCount({ total: 323, snapshotCount: 17 })
    expect(d.tip).toContain('323')
    expect(d.tip).toContain('17')
    // the whole point: the reader must not hear "323 articles"
    expect(d.tip).toMatch(/counted again|once per pass|repeat/i)
  })

  it('degrades honestly when the pass count is absent', () => {
    const d = describeCumulativeCount({ total: 323, snapshotCount: null })
    expect(d.qualifier).toBe('cumulative')
    expect(d.tip).not.toContain('null')
    expect(d.tip).toMatch(/how many passes|not reported/i)
  })

  it('says one pass, not "1 passes"', () => {
    expect(describeCumulativeCount({ total: 43, snapshotCount: 1 }).qualifier)
      .toBe('across 1 pass')
  })
})

describe('describeSourceCount', () => {
  it('uses the counted value, never the capped preview length', () => {
    const d = describeSourceCount({
      sourceCount: 36, sourceSampleSize: 37, previewLength: 20,
    })
    expect(d.value).toBe('36')
  })

  it('states the receipt basis beside the number', () => {
    const d = describeSourceCount({
      sourceCount: 36, sourceSampleSize: 37, previewLength: 20,
    })
    expect(d.subnote).toBe('in 37 receipts')
    expect(d.tip).toContain('37')
    expect(d.tip).toMatch(/receipt|shown/i)
  })

  it('never claims the sample is the story total', () => {
    const d = describeSourceCount({
      sourceCount: 36, sourceSampleSize: 37, previewLength: 20,
    })
    expect(d.tip).toMatch(/not the (full|total)|more outlets|may carry/i)
  })

  it('falls back to the preview length only when nothing was counted', () => {
    const d = describeSourceCount({
      sourceCount: null, sourceSampleSize: 0, previewLength: 20,
    })
    expect(d.value).toBe('20')
  })

  it('renders an em dash rather than 0 when the lane did not answer', () => {
    const d = describeSourceCount({
      sourceCount: null, sourceSampleSize: 0, previewLength: 0,
    })
    expect(d.value).toBe('—')
  })

  it('a measured zero is a real 0, not an em dash', () => {
    // receipts existed, none carried attribution
    const d = describeSourceCount({
      sourceCount: 0, sourceSampleSize: 4, previewLength: 0,
    })
    expect(d.value).toBe('0')
  })

  it('singular receipt reads correctly', () => {
    const d = describeSourceCount({
      sourceCount: 1, sourceSampleSize: 1, previewLength: 1,
    })
    expect(d.subnote).toBe('in 1 receipt')
  })
})
