import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __dirname = dirname(fileURLToPath(import.meta.url))
const source = readFileSync(resolve(__dirname, '../components/ThemeDetail.tsx'), 'utf-8')

describe('ThemeDetail dynamic topic insight guardrail', () => {
    it('does not request the static theme insight endpoint for dynamic topics', () => {
        expect(source).toContain('isDynamicTopic')
        expect(source).toContain("theme.toLowerCase().startsWith('dynamic-topic-')")
        expect(source).toContain('buildDynamicTopicInsight')

        const effectStart = source.indexOf('// Fetch AI insight async after main data loads')
        const effectEnd = source.indexOf('const getSentimentColor')
        const effectSource = source.slice(effectStart, effectEnd)

        // guard must bail for dynamic topics (query threads may share the guard)
        expect(effectSource).toMatch(/if \(isDynamicTopic[^)]*\) return/)
        expect(effectSource).toContain('/api/v2/theme/${encodeURIComponent(theme)}/insight')
    })
})
