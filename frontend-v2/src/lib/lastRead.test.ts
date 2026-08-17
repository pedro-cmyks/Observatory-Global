import { describe, it, expect, beforeEach, vi } from 'vitest'

// vitest runs in node: back localStorage with a Map (workbench.test.ts convention).
const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
    getItem: (k: string) => backing.get(k) ?? null,
    setItem: (k: string, v: string) => void backing.set(k, String(v)),
    removeItem: (k: string) => void backing.delete(k),
    clear: () => backing.clear(),
})

import { touchLastRead, hoursSince, LAST_READ_KEY } from './lastRead'

describe('lastRead', () => {
    beforeEach(() => localStorage.clear())

    it('first visit: returns null previous, stores now', () => {
        expect(touchLastRead(1_000_000)).toBeNull()
        expect(localStorage.getItem(LAST_READ_KEY)).toBe('1000000')
    })

    it('second visit: returns the previous mark, advances the store', () => {
        touchLastRead(1_000_000)
        expect(touchLastRead(70_600_000)).toBe(1_000_000)
    })

    it('hoursSince rounds to one decimal; null previous → null, never 0', () => {
        expect(hoursSince(1_000_000, 69_400_000)).toBe(19)
        expect(hoursSince(null, 69_400_000)).toBeNull()
    })

    it('garbage in storage reads as first visit', () => {
        localStorage.setItem(LAST_READ_KEY, 'NaNope')
        expect(touchLastRead(5_000)).toBeNull()
    })
})
