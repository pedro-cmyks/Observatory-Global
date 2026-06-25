import { describe, it, expect } from 'vitest'
import { buildShareText } from './shareCard'

describe('buildShareText', () => {
  it('includes label, why-now, and url with the Atlas attribution', () => {
    const t = buildShareText({
      label: 'Ukraine War Updates',
      whyNow: 'Up 147 vs the prior 10h',
      url: 'https://atlas.app/app?theme=x',
    })
    expect(t).toContain('Ukraine War Updates')
    expect(t).toContain('Up 147')
    expect(t).toContain('https://atlas.app/app?theme=x')
    expect(t).toContain('Atlas')
  })
  it('omits the why-now line when absent', () => {
    const t = buildShareText({ label: 'Quiet thread', url: 'https://atlas.app/x' })
    expect(t).toContain('Quiet thread')
    expect(t.split('\n')).toHaveLength(2)
  })
})
