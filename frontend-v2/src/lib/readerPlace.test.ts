import { describe, it, expect, beforeEach, vi } from 'vitest'

// vitest runs in node: back localStorage with a Map (workbench.test.ts convention).
const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
    getItem: (k: string) => backing.get(k) ?? null,
    setItem: (k: string, v: string) => void backing.set(k, String(v)),
    removeItem: (k: string) => void backing.delete(k),
    clear: () => backing.clear(),
})

import { loadReaderPlace, saveReaderPlace, PLACE_KEY } from './readerPlace'

describe('readerPlace', () => {
    beforeEach(() => localStorage.clear())

    it('proposes from locale region when nothing is stored, flagged as proposed', () => {
        expect(loadReaderPlace('es-CO')).toEqual({ country: 'CO', proposed: true })
    })

    it('a stored choice wins over locale and is not "proposed"', () => {
        saveReaderPlace('VE')
        expect(loadReaderPlace('es-CO')).toEqual({ country: 'VE', proposed: false })
    })

    it('no locale region and nothing stored → honest null, never a guess', () => {
        expect(loadReaderPlace('es')).toEqual({ country: null, proposed: false })
        expect(loadReaderPlace(undefined)).toEqual({ country: null, proposed: false })
    })

    it('clearing returns to the locale proposal', () => {
        saveReaderPlace('VE'); saveReaderPlace(null)
        expect(loadReaderPlace('es-CO')).toEqual({ country: 'CO', proposed: true })
    })

    it('stored garbage is ignored, not served', () => {
        localStorage.setItem(PLACE_KEY, 'not-a-country-code')
        expect(loadReaderPlace('es-CO')).toEqual({ country: 'CO', proposed: true })
    })
})
