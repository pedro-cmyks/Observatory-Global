// cardDepth — el decisor puro de bloques por profundidad (P1.5 en sitio).
// Congela: LEER = cero bloques (G-ADITIVO), campo ausente = bloque ausente
// (jamás placeholder), sellado = menos campos → menos bloques + base frozen,
// construir ⊇ observar.
import { describe, it, expect } from 'vitest'
import { depthBlocksForRow, type DepthCardRow } from './cardDepth'

const FULL_LIVE_ROW: DepthCardRow = {
    thread_id: 'dynamic-topic-242',
    anchor_topics: ['some-identity-key'],
    top_entities: ['gustavo petro', 'maria corina machado', '', '  ', 'x', 'y'],
    top_countries: ['CO', 'VE', 'US', 'BR'],
    signal_count: 412,
    count_window_hours: 168,
    confidence: 'medium',
    avg_confidence: 1.0,
    confidence_measured: true,
    temporal_signature: 'resurrected',
    signature_meta: { gap_weeks: 3, returned_week: '2026-08-10' },
    discussion_count: 7,
}

describe('depthBlocksForRow', () => {
    it('LEER: cero bloques, siempre (la tarjeta de hoy intacta)', () => {
        expect(depthBlocksForRow(FULL_LIVE_ROW, 'leer')).toEqual([])
        expect(depthBlocksForRow({}, 'leer')).toEqual([])
    })

    it('OBSERVAR con fila viva completa: los 6 bloques, en orden fijo', () => {
        const blocks = depthBlocksForRow(FULL_LIVE_ROW, 'observar')
        expect(blocks.map(b => b.kind)).toEqual([
            'subjects', 'coverage', 'temporal', 'confidence', 'count', 'discussion',
        ])
    })

    it('CONSTRUIR ⊇ OBSERVAR: mismos bloques (lo extra de construir vive en el componente)', () => {
        expect(depthBlocksForRow(FULL_LIVE_ROW, 'construir'))
            .toEqual(depthBlocksForRow(FULL_LIVE_ROW, 'observar'))
    })

    it('sujetos: strings vacíos fuera, cap 4', () => {
        const blocks = depthBlocksForRow(FULL_LIVE_ROW, 'observar')
        const subjects = blocks.find(b => b.kind === 'subjects')
        expect(subjects).toEqual({
            kind: 'subjects',
            entities: ['gustavo petro', 'maria corina machado', 'x', 'y'],
        })
    })

    it('cobertura: omite los códigos que la tarjeta base ya muestra; resto vacío → sin bloque', () => {
        const some = depthBlocksForRow(FULL_LIVE_ROW, 'observar', { omitCoverage: ['CO', 'VE'] })
        expect(some.find(b => b.kind === 'coverage')).toEqual({ kind: 'coverage', codes: ['US', 'BR'] })
        const none = depthBlocksForRow(FULL_LIVE_ROW, 'observar', {
            omitCoverage: ['CO', 'VE', 'US', 'BR'],
        })
        expect(none.find(b => b.kind === 'coverage')).toBeUndefined()
    })

    it('firma temporal: continuous/NULL → sin bloque (absence over guess)', () => {
        const cont = depthBlocksForRow({ ...FULL_LIVE_ROW, temporal_signature: 'continuous' }, 'observar')
        expect(cont.find(b => b.kind === 'temporal')).toBeUndefined()
        const nul = depthBlocksForRow({ ...FULL_LIVE_ROW, temporal_signature: null }, 'observar')
        expect(nul.find(b => b.kind === 'temporal')).toBeUndefined()
    })

    it('confianza: la banda servida manda sobre el número (N14 — jamás un dígito)', () => {
        const blocks = depthBlocksForRow(FULL_LIVE_ROW, 'observar')
        expect(blocks.find(b => b.kind === 'confidence')).toEqual({
            kind: 'confidence', bucket: 'medium', source: 'band',
        })
    })

    it('confianza: sin banda, número MEDIDO → derived; número no medido → sin bloque', () => {
        const derived = depthBlocksForRow(
            { ...FULL_LIVE_ROW, confidence: null, avg_confidence: 0.8, confidence_measured: true },
            'observar',
        )
        expect(derived.find(b => b.kind === 'confidence')).toEqual({
            kind: 'confidence', bucket: 'high', source: 'derived',
        })
        const unmeasured = depthBlocksForRow(
            { ...FULL_LIVE_ROW, confidence: null, avg_confidence: 0.8, confidence_measured: false },
            'observar',
        )
        expect(unmeasured.find(b => b.kind === 'confidence')).toBeUndefined()
    })

    it('conteo vivo: base gated para filas dinámicas sin campos de gate, ventana servida', () => {
        const blocks = depthBlocksForRow(FULL_LIVE_ROW, 'observar')
        expect(blocks.find(b => b.kind === 'count')).toEqual({
            kind: 'count', count: 412, windowHours: 168, base: 'gated',
        })
    })

    it('conteo vivo: misma regla que el rail — dinámica con gate servido → raw; slug atlas → category', () => {
        const raw = depthBlocksForRow(
            { ...FULL_LIVE_ROW, gated_signal_count: 12 },
            'observar',
        )
        expect(raw.find(b => b.kind === 'count')).toMatchObject({ base: 'raw' })
        const category = depthBlocksForRow(
            { ...FULL_LIVE_ROW, thread_id: 'election-legitimacy--CO' },
            'observar',
        )
        expect(category.find(b => b.kind === 'count')).toMatchObject({ base: 'category' })
    })

    it('fila SELLADA: solo lo que el sello carga — cobertura + conteo frozen sin ventana', () => {
        const sealedRow: DepthCardRow = {
            thread_id: 'dynamic-topic-9',
            top_countries: ['UA', 'RU'],
            signal_count: 88,
        }
        const blocks = depthBlocksForRow(sealedRow, 'observar', { sealed: true })
        expect(blocks).toEqual([
            { kind: 'coverage', codes: ['UA', 'RU'] },
            { kind: 'count', count: 88, windowHours: null, base: 'frozen' },
        ])
    })

    it('discusión: 0 o ausente → sin bloque; positivo → n servido', () => {
        const zero = depthBlocksForRow({ ...FULL_LIVE_ROW, discussion_count: 0 }, 'observar')
        expect(zero.find(b => b.kind === 'discussion')).toBeUndefined()
        const blocks = depthBlocksForRow(FULL_LIVE_ROW, 'observar')
        expect(blocks.find(b => b.kind === 'discussion')).toEqual({ kind: 'discussion', n: 7 })
    })

    it('fila vacía: cero bloques a toda profundidad (nada inventado)', () => {
        expect(depthBlocksForRow({}, 'observar')).toEqual([])
        expect(depthBlocksForRow({}, 'construir')).toEqual([])
    })
})
