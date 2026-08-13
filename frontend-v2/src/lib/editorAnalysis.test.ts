import { readFileSync } from 'node:fs'
import { describe, it, expect } from 'vitest'
import {
  ANALYSIS_BASIS,
  ANALYSIS_LABEL,
  ANALYSIS_NATURE,
  insightStaleness,
} from './editorAnalysis'

describe('the analysis names what it is', () => {
  it('says "interpretation, not measurement" in reader-facing words', () => {
    expect(ANALYSIS_NATURE).toMatch(/interpretation, not measurement/)
    expect(ANALYSIS_NATURE.toLowerCase()).toContain('ai')
  })

  it('names BOTH populations and BOTH scales so the panels stop contradicting it', () => {
    // Traced to backend/app/routers/briefing.py: the insight prompt receives
    // country_hourly_v2 ORDER BY volume LIMIT 5, tone/10 (±1 scale). The tone
    // columns below are the sentiment extremes across all countries, ×10.
    expect(ANALYSIS_BASIS).toMatch(/five most-covered countries/)
    expect(ANALYSIS_BASIS).toMatch(/±1/)
    expect(ANALYSIS_BASIS).toMatch(/−10…\+10/)
    expect(ANALYSIS_BASIS).toMatch(/not a disagreement/)
  })

  it('keeps the label stable', () => {
    expect(ANALYSIS_LABEL).toBe("Editor's analysis")
  })
})

describe('insightStaleness — a stale reading is labeled, never dropped', () => {
  const now = new Date('2026-08-13T12:00:00Z')

  it('is silent for a reading written inside the hour', () => {
    expect(insightStaleness('2026-08-13T11:20:00Z', now)).toEqual({ stale: false, note: null })
  })

  it('labels a reading older than an hour with when it was written', () => {
    const result = insightStaleness('2026-08-13T08:00:00Z', now)
    expect(result.stale).toBe(true)
    expect(result.note).toMatch(/Earlier reading/)
    expect(result.note).toMatch(/4h ago/)
    expect(result.note).toMatch(/Shown rather than dropped/)
  })

  it('drops the hour count once it passes a day', () => {
    const result = insightStaleness('2026-08-11T12:00:00Z', now)
    expect(result.stale).toBe(true)
    expect(result.note).not.toMatch(/\dh ago/)
  })

  it('stays silent on a missing or malformed timestamp rather than crying stale', () => {
    expect(insightStaleness(null, now).stale).toBe(false)
    expect(insightStaleness(undefined, now).stale).toBe(false)
    expect(insightStaleness('not-a-date', now).stale).toBe(false)
  })
})

describe('BriefNewspaper wiring', () => {
  const source = readFileSync(new URL('../pages/BriefNewspaper.tsx', import.meta.url), 'utf8')

  it('prints the nature + basis as visible copy, not only as a hover tip', () => {
    expect(source).toContain('ANALYSIS_NATURE')
    expect(source).toContain('ANALYSIS_BASIS')
    expect(source).toMatch(/brief-analysis-nature/)
  })

  it('keeps a served reading across reloads instead of letting it vanish', () => {
    // (iii) the flicker: the cache was written BEFORE the insight arrived and
    // never updated, so the next cached load short-circuited with insight=null
    // and the analysis silently became a bare signal count.
    expect(source).toContain('updateCachedInsight')
    expect(source).toContain('insightStaleness')
  })
})
