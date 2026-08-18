import { describe, it, expect, beforeEach, vi } from 'vitest'

// vitest corre en node sin jsdom — el stub Map-backed es la convención del
// repo (workbench.test.ts:8-15).
const store = new Map<string, string>()
vi.stubGlobal('localStorage', {
    getItem: (k: string) => store.get(k) ?? null,
    setItem: (k: string, v: string) => { store.set(k, String(v)) },
    removeItem: (k: string) => { store.delete(k) },
    clear: () => store.clear(),
})

import { DIAL_KEY, loadDialPosition, saveDialPosition, dialTarget, dialFromUrl } from './depthDial'

describe('depthDial', () => {
    beforeEach(() => store.clear())

    it('primera visita: LEER (spec §7)', () => {
        expect(loadDialPosition()).toBe('leer')
    })

    it('persiste la elección; basura almacenada cae a leer', () => {
        saveDialPosition('observar')
        expect(loadDialPosition()).toBe('observar')
        store.set(DIAL_KEY, 'nonsense')
        expect(loadDialPosition()).toBe('leer')
    })

    it('dialFromUrl: ?depth= válido gana; ausente o inválido → null', () => {
        expect(dialFromUrl('?depth=observar')).toBe('observar')
        expect(dialFromUrl('?depth=zzz')).toBeNull()
        expect(dialFromUrl('?country=CO')).toBeNull()
    })

    describe('dialTarget — el destino con foco acarreado (invariante 4)', () => {
        it('leer desde /app: a /brief llevando SOLO country', () => {
            expect(dialTarget('leer', '?theme=dynamic-topic-9&country=CO&entry=x'))
                .toEqual({ path: '/brief', search: '?country=CO' })
            expect(dialTarget('leer', '?theme=dt-9'))
                .toEqual({ path: '/brief', search: '' })
        })

        it('observar desde /brief: a /app llevando country + entry=dial', () => {
            expect(dialTarget('observar', '?country=CO'))
                .toEqual({ path: '/app', search: '?country=CO&entry=dial' })
            expect(dialTarget('observar', ''))
                .toEqual({ path: '/app', search: '?entry=dial' })
        })

        it('construir: /app + workbench=1 + country', () => {
            expect(dialTarget('construir', '?country=VE'))
                .toEqual({ path: '/app', search: '?country=VE&entry=dial&workbench=1' })
        })
    })
})
