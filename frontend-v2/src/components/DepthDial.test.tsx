import { describe, it, expect, vi } from 'vitest'
import { buildDialStops, handleDialSelect } from './DepthDial'

// vitest corre en node sin jsdom, así que el componente se testea por su
// modelo puro (la convención del repo — PrintersMarks.test.tsx): el render
// mapea buildDialStops 1:1 a <button aria-pressed> y onClick delega en
// handleDialSelect. Las aserciones del plan se mantienen en espíritu.

describe('DepthDial', () => {
    it('tres paradas, la activa marcada con aria-pressed', () => {
        const stops = buildDialStops('observar')
        expect(stops).toHaveLength(3)
        expect(stops.map(s => s.position)).toEqual(['leer', 'observar', 'construir'])
        expect(stops[1].ariaPressed).toBe(true)
        expect(stops[0].ariaPressed).toBe(false)
        expect(stops[2].ariaPressed).toBe(false)
        // La clave de copy es la del catálogo — nunca un literal suelto.
        expect(stops.map(s => s.copyKey)).toEqual(['dial.leer', 'dial.observar', 'dial.construir'])
    })

    it('click en parada inactiva dispara onSelect; en la activa, no', () => {
        const onSelect = vi.fn()
        handleDialSelect('leer', 'construir', onSelect)
        expect(onSelect).toHaveBeenCalledWith('construir')
        onSelect.mockClear()
        handleDialSelect('leer', 'leer', onSelect)
        expect(onSelect).not.toHaveBeenCalled()
    })
})
